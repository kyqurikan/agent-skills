#!/usr/bin/env python3
"""Safely add SR Number and OppID tags to Sales Team FY27 Markdown notes."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


DEFAULT_SALES_ROOT = Path(
    os.environ.get(
        "FY27_SALES_ROOT",
        Path.home() / "Documents" / "Oracle Vault" / "Sales Team FY27",
    )
)
DEFAULT_TABLE_NAME = "Tag and SRs.md"
REQUIRED_COLUMNS = ("Company Name", "SR Number", "OppID", "CPR")
TAG_BLOCK_RE = re.compile(r"^\s*(?:#[^\s#]+\s*)+$")
TAG_TOKEN_RE = re.compile(r"(?<!\S)#[^\s#]+")
YAML_TAGS_KEY_RE = re.compile(r"^(?P<indent>[ \t]*)tags[ \t]*:(?P<rhs>.*)$")
YAML_TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+[ \t]*:")
YAML_BLOCK_ITEM_RE = re.compile(
    r"^(?P<prefix>[ \t]*-[ \t]+)"
    r"(?P<scalar>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^#\s][^\s#]*)"
    r"(?P<suffix>[ \t]*(?:#.*)?)"
    r"(?P<ending>\r\n|\n|\r)?$"
)
YAML_SCALAR_RE = re.compile(
    r"^(?:\"(?P<double>[^\"\r\n]*)\"|'(?P<single>[^'\r\n]*)'|"
    r"(?P<plain>#?[A-Za-z0-9][A-Za-z0-9_/-]*))$"
)
COMPANY_RE = re.compile(r"^#Customer_[A-Za-z0-9][A-Za-z0-9_-]*$")
CPR_RE = re.compile(r"^#CPR_(?:Manager_)?[A-Za-z0-9][A-Za-z0-9_-]*$")
SR_RE = re.compile(r"^#SR[0-9]+$")
OPP_RE = re.compile(r"^#[A-Z0-9]{6}$")
UTF8_BOM = b"\xef\xbb\xbf"


class SourceError(ValueError):
    """Raised when the source table cannot be trusted."""


@dataclass(frozen=True)
class Record:
    company: str
    sr: str
    opp: str
    cpr: str
    line: int

    @property
    def key(self) -> Tuple[str, str]:
        return (self.company, self.cpr)


@dataclass(frozen=True)
class SourceIssue:
    status: str
    line: int
    detail: str


@dataclass
class Finding:
    path: str
    status: str
    detail: str
    additions: Tuple[str, ...] = ()
    original_bytes: Optional[bytes] = None
    updated_bytes: Optional[bytes] = None

    def public_dict(self) -> dict:
        result = asdict(self)
        result.pop("original_bytes", None)
        result.pop("updated_bytes", None)
        result["additions"] = list(self.additions)
        return result


@dataclass(frozen=True)
class TagEntry:
    canonical: str
    line_index: int
    raw_value: str
    quote: str = ""
    prefix: str = ""
    end_offset: int = 0


@dataclass(frozen=True)
class TagLocation:
    kind: str
    tags: Tuple[str, ...]
    line_index: int
    entries: Tuple[TagEntry, ...] = ()


def parse_markdown_row(line: str) -> Optional[List[str]]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def is_divider_row(cells: Sequence[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def validate_source_tag(value: str, pattern: re.Pattern[str], label: str, line: int) -> None:
    if not pattern.fullmatch(value):
        raise SourceError(
            f"line {line}: invalid {label} value {value!r}; expected one literal tag"
        )


def parse_source_table(
    text: str,
) -> Tuple[Dict[Tuple[str, str], Record], Set[Tuple[str, str]], List[SourceIssue]]:
    lines = text.splitlines()
    header_index: Optional[int] = None
    headers: List[str] = []

    for index, line in enumerate(lines):
        cells = parse_markdown_row(line)
        if cells and all(column in cells for column in REQUIRED_COLUMNS):
            header_index = index
            headers = cells
            break

    if header_index is None:
        raise SourceError(
            "could not find a Markdown table containing columns: "
            + ", ".join(REQUIRED_COLUMNS)
        )

    positions = {column: headers.index(column) for column in REQUIRED_COLUMNS}
    records: Dict[Tuple[str, str], Record] = {}
    conflict_keys: Set[Tuple[str, str]] = set()
    issues: List[SourceIssue] = []
    saw_divider = False

    for index in range(header_index + 1, len(lines)):
        cells = parse_markdown_row(lines[index])
        if cells is None:
            if saw_divider:
                break
            continue
        if is_divider_row(cells):
            saw_divider = True
            continue
        if not saw_divider:
            continue
        if len(cells) < len(headers):
            issues.append(
                SourceIssue(
                    "invalid_source",
                    index + 1,
                    f"row has {len(cells)} cells but header has {len(headers)}",
                )
            )
            continue

        company = cells[positions["Company Name"]]
        sr = cells[positions["SR Number"]]
        opp = cells[positions["OppID"]]
        cpr = cells[positions["CPR"]]

        if not company and not sr and not opp and not cpr:
            continue
        try:
            validate_source_tag(company, COMPANY_RE, "Company Name", index + 1)
            validate_source_tag(cpr, CPR_RE, "CPR", index + 1)
        except SourceError as exc:
            issues.append(SourceIssue("invalid_source", index + 1, str(exc)))
            continue

        if not sr or not opp:
            missing = []
            if not sr:
                missing.append("SR Number")
            if not opp:
                missing.append("OppID")
            issues.append(
                SourceIssue(
                    "incomplete_source",
                    index + 1,
                    f"{company} + {cpr}: missing {' and '.join(missing)}",
                )
            )
            continue

        try:
            validate_source_tag(sr, SR_RE, "SR Number", index + 1)
            validate_source_tag(opp, OPP_RE, "OppID", index + 1)
        except SourceError as exc:
            issues.append(SourceIssue("invalid_source", index + 1, str(exc)))
            continue

        record = Record(company=company, sr=sr, opp=opp, cpr=cpr, line=index + 1)
        prior = records.get(record.key)
        if prior is None:
            records[record.key] = record
        elif (prior.sr, prior.opp) != (record.sr, record.opp):
            conflict_keys.add(record.key)
            issues.append(
                SourceIssue(
                    "source_conflict",
                    index + 1,
                    f"{company} + {cpr}: {prior.sr}/{prior.opp} on line "
                    f"{prior.line} conflicts with {sr}/{opp}",
                )
            )

    for key in conflict_keys:
        records.pop(key, None)
    if not records and not issues:
        raise SourceError("the SR table contains no data rows")
    return records, conflict_keys, issues


def iter_markdown_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [
            name
            for name in sorted(dirs)
            if not name.startswith(".")
            and not (Path(current) / name).is_symlink()
        ]
        for name in sorted(files):
            if name.startswith(".") or not name.lower().endswith(".md"):
                continue
            path = Path(current) / name
            if not path.is_symlink():
                yield path


def canonical_yaml_tag(value: str) -> str:
    return value if value.startswith("#") else f"#{value}"


def parse_yaml_scalar(scalar: str) -> Tuple[str, str]:
    match = YAML_SCALAR_RE.fullmatch(scalar)
    if not match:
        raise ValueError(f"unsupported YAML tag value {scalar!r}")
    if match.group("double") is not None:
        return match.group("double"), '"'
    if match.group("single") is not None:
        return match.group("single"), "'"
    return match.group("plain"), ""


def split_inline_yaml_items(inside: str) -> List[Tuple[int, int]]:
    if not inside.strip():
        return []
    spans: List[Tuple[int, int]] = []
    start = 0
    quote = ""
    for index, character in enumerate(inside):
        if quote:
            if character == quote:
                quote = ""
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == ",":
            spans.append((start, index))
            start = index + 1
    if quote:
        raise ValueError("unterminated quote in inline YAML tags list")
    spans.append((start, len(inside)))
    return spans


def parse_inline_yaml_location(
    line: str, line_index: int, rhs_start: int, rhs: str
) -> TagLocation:
    body = line.rstrip("\r\n")
    rhs_body = rhs.rstrip("\r\n")
    match = re.fullmatch(r"\s*\[(?P<inside>.*)\]\s*(?:#.*)?", rhs_body)
    if not match:
        raise ValueError("tags property must be a one-line YAML list or block list")

    inside = match.group("inside")
    inside_start = rhs_start + match.start("inside")
    entries: List[TagEntry] = []
    for start, end in split_inline_yaml_items(inside):
        segment = inside[start:end]
        leading = len(segment) - len(segment.lstrip())
        scalar = segment.strip()
        if not scalar:
            raise ValueError("empty item in inline YAML tags list")
        raw_value, quote = parse_yaml_scalar(scalar)
        scalar_end = inside_start + start + leading + len(scalar)
        entries.append(
            TagEntry(
                canonical=canonical_yaml_tag(raw_value),
                line_index=line_index,
                raw_value=raw_value,
                quote=quote,
                end_offset=scalar_end,
            )
        )

    return TagLocation(
        kind="yaml_inline",
        tags=tuple(entry.canonical for entry in entries),
        line_index=line_index,
        entries=tuple(entries),
    )


def parse_block_yaml_location(
    lines: Sequence[str], key_index: int, closing_index: int
) -> TagLocation:
    entries: List[TagEntry] = []
    for index in range(key_index + 1, closing_index):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = YAML_BLOCK_ITEM_RE.fullmatch(line)
        if not match:
            if YAML_TOP_LEVEL_KEY_RE.match(line):
                break
            raise ValueError(
                f"unsupported YAML tags list syntax on frontmatter line {index + 1}"
            )
        raw_value, quote = parse_yaml_scalar(match.group("scalar"))
        entries.append(
            TagEntry(
                canonical=canonical_yaml_tag(raw_value),
                line_index=index,
                raw_value=raw_value,
                quote=quote,
                prefix=match.group("prefix"),
            )
        )

    return TagLocation(
        kind="yaml_block",
        tags=tuple(entry.canonical for entry in entries),
        line_index=key_index,
        entries=tuple(entries),
    )


def find_inline_tag_location(
    lines: Sequence[str], start: int
) -> Optional[TagLocation]:
    for index in range(start, len(lines)):
        line_without_ending = lines[index].rstrip("\r\n")
        if not line_without_ending.strip():
            continue
        if TAG_BLOCK_RE.fullmatch(line_without_ending):
            tags = tuple(
                match.group(0) for match in TAG_TOKEN_RE.finditer(line_without_ending)
            )
            return TagLocation("inline", tags, index)
        return None
    return None


def find_tag_location(
    lines: Sequence[str],
) -> Tuple[Optional[TagLocation], Optional[str]]:
    body_start = 0
    if lines and lines[0].lstrip("\ufeff").strip() == "---":
        closing_index: Optional[int] = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                closing_index = index
                break
        if closing_index is None:
            return None, "unclosed YAML frontmatter"

        body_start = closing_index + 1
        tag_keys: List[Tuple[int, re.Match[str]]] = []
        for index in range(1, closing_index):
            line_body = lines[index].rstrip("\r\n")
            match = YAML_TAGS_KEY_RE.fullmatch(line_body)
            if match and not match.group("indent"):
                tag_keys.append((index, match))

        if len(tag_keys) > 1:
            return None, "multiple top-level YAML tags properties"
        if tag_keys:
            key_index, match = tag_keys[0]
            rhs = match.group("rhs")
            try:
                if rhs.strip().startswith("["):
                    location = parse_inline_yaml_location(
                        lines[key_index],
                        key_index,
                        match.start("rhs"),
                        rhs,
                    )
                elif not rhs.strip() or rhs.lstrip().startswith("#"):
                    location = parse_block_yaml_location(
                        lines, key_index, closing_index
                    )
                else:
                    raise ValueError(
                        "tags property must be a YAML list, not a scalar value"
                    )
            except ValueError as exc:
                return None, str(exc)
            return location, None

    return find_inline_tag_location(lines, body_start), None


def looks_like_opp(tag: str) -> bool:
    return bool(
        OPP_RE.fullmatch(tag)
        and any(character.isalpha() for character in tag)
        and any(character.isdigit() for character in tag)
    )


def insert_inline_tags(
    line: str, company: str, cpr: str, additions: Sequence[str]
) -> str:
    ending = ""
    body = line
    if body.endswith("\r\n"):
        body, ending = body[:-2], "\r\n"
    elif body.endswith("\n") or body.endswith("\r"):
        body, ending = body[:-1], body[-1:]

    matches = list(TAG_TOKEN_RE.finditer(body))
    anchors = [match for match in matches if match.group(0) in {company, cpr}]
    if len(anchors) < 2:
        raise ValueError("matched company and CPR anchors are not both present")
    insertion_point = max(match.end() for match in anchors)
    inserted = "".join(f" {tag}" for tag in additions)
    return body[:insertion_point] + inserted + body[insertion_point:] + ending


def line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return "\n"


def format_yaml_addition(tag: str, anchor: TagEntry) -> str:
    value = tag if anchor.raw_value.startswith("#") else tag.removeprefix("#")
    return f"{anchor.quote}{value}{anchor.quote}"


def apply_additions(
    lines: List[str],
    location: TagLocation,
    company: str,
    cpr: str,
    additions: Sequence[str],
) -> None:
    if location.kind == "inline":
        lines[location.line_index] = insert_inline_tags(
            lines[location.line_index], company, cpr, additions
        )
        return

    anchors = [
        entry for entry in location.entries if entry.canonical in {company, cpr}
    ]
    if not any(entry.canonical == company for entry in anchors) or not any(
        entry.canonical == cpr for entry in anchors
    ):
        raise ValueError("matched company and CPR YAML anchors are not both present")

    if location.kind == "yaml_block":
        anchor = max(anchors, key=lambda entry: entry.line_index)
        ending = line_ending(lines[anchor.line_index])
        inserted = [
            f"{anchor.prefix}{format_yaml_addition(tag, anchor)}{ending}"
            for tag in additions
        ]
        lines[anchor.line_index + 1 : anchor.line_index + 1] = inserted
        return

    if location.kind == "yaml_inline":
        anchor = max(anchors, key=lambda entry: entry.end_offset)
        inserted = ", " + ", ".join(
            format_yaml_addition(tag, anchor) for tag in additions
        )
        line = lines[location.line_index]
        lines[location.line_index] = (
            line[: anchor.end_offset] + inserted + line[anchor.end_offset :]
        )
        return

    raise ValueError(f"unsupported tag location kind {location.kind!r}")


def decode_note(data: bytes) -> Tuple[str, bool]:
    has_bom = data.startswith(UTF8_BOM)
    payload = data[len(UTF8_BOM) :] if has_bom else data
    return payload.decode("utf-8"), has_bom


def encode_note(text: str, has_bom: bool) -> bytes:
    encoded = text.encode("utf-8")
    return UTF8_BOM + encoded if has_bom else encoded


def analyze_note(
    path: Path,
    relative_path: str,
    records: Mapping[Tuple[str, str], Record],
    conflict_keys: Set[Tuple[str, str]],
    companies_in_source: Set[str],
) -> Finding:
    try:
        original = path.read_bytes()
        text, has_bom = decode_note(original)
    except (OSError, UnicodeDecodeError) as exc:
        return Finding(relative_path, "read_error", str(exc))

    lines = text.splitlines(keepends=True)
    location, metadata_error = find_tag_location(lines)
    if metadata_error:
        return Finding(relative_path, "metadata_error", metadata_error)
    if location is None:
        return Finding(
            relative_path,
            "no_tag_line",
            "no YAML tags list or leading inline tag-only line",
        )

    tags = list(location.tags)
    tag_set = set(tags)
    matched_conflict_keys = [
        key for key in conflict_keys if key[0] in tag_set and key[1] in tag_set
    ]
    if matched_conflict_keys:
        evidence = ", ".join(f"{company} + {cpr}" for company, cpr in matched_conflict_keys)
        return Finding(relative_path, "source_conflict", evidence)

    matches = [record for key, record in records.items() if key[0] in tag_set and key[1] in tag_set]
    if len(matches) > 1:
        evidence = ", ".join(
            f"{record.company} + {record.cpr} -> {record.sr}/{record.opp}"
            for record in sorted(matches, key=lambda item: item.key)
        )
        return Finding(relative_path, "ambiguous", evidence)

    if not matches:
        known_companies = sorted(tag_set.intersection(companies_in_source))
        cpr_tags = sorted(tag for tag in tag_set if CPR_RE.fullmatch(tag))
        if known_companies and cpr_tags:
            return Finding(
                relative_path,
                "pair_mismatch",
                f"known customer(s) {', '.join(known_companies)} with CPR tag(s) "
                f"{', '.join(cpr_tags)} did not match one table row",
            )
        return Finding(relative_path, "unmatched", "no exact Company Name + CPR pair")

    record = matches[0]
    existing_srs = {tag for tag in tag_set if SR_RE.fullmatch(tag)}
    existing_opps = {tag for tag in tag_set if looks_like_opp(tag)}
    conflicting_srs = sorted(existing_srs - {record.sr})
    conflicting_opps = sorted(existing_opps - {record.opp})
    if conflicting_srs or conflicting_opps:
        conflicts = conflicting_srs + conflicting_opps
        return Finding(
            relative_path,
            "existing_conflict",
            f"expected {record.sr}/{record.opp}; found {' '.join(conflicts)}",
        )

    additions = tuple(
        tag for tag in (record.sr, record.opp) if tag not in tag_set
    )
    if not additions:
        return Finding(
            relative_path,
            "up_to_date",
            f"{record.company} + {record.cpr} -> {record.sr}/{record.opp}",
        )

    apply_additions(lines, location, record.company, record.cpr, additions)
    updated = encode_note("".join(lines), has_bom)
    return Finding(
        relative_path,
        "ready",
        f"{record.company} + {record.cpr} -> {record.sr}/{record.opp}",
        additions=additions,
        original_bytes=original,
        updated_bytes=updated,
    )


def atomic_write(path: Path, original: bytes, updated: bytes) -> None:
    current = path.read_bytes()
    if current != original:
        raise RuntimeError("file changed after preview; refusing to overwrite")

    original_mode = stat.S_IMODE(path.stat(follow_symlinks=False).st_mode)
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.fy27-sr-",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, original_mode, follow_symlinks=False)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or add SR Number and OppID tags using exact Company Name + CPR "
            "matches from Sales Team FY27/Tag and SRs.md."
        )
    )
    parser.add_argument(
        "--sales-root",
        type=Path,
        default=DEFAULT_SALES_ROOT,
        help=f"Sales Team FY27 directory (default: {DEFAULT_SALES_ROOT})",
    )
    parser.add_argument(
        "--table",
        type=Path,
        help=f"source Markdown table (default: <sales-root>/{DEFAULT_TABLE_NAME})",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="atomically write eligible changes; default is preview only",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable results",
    )
    parser.add_argument(
        "--details-limit",
        type=int,
        default=60,
        help="maximum non-routine details to print in text mode (default: 60)",
    )
    return parser


def resolve_inputs(args: argparse.Namespace) -> Tuple[Path, Path]:
    root = args.sales_root.expanduser().resolve()
    table = (
        args.table.expanduser().resolve()
        if args.table
        else (root / DEFAULT_TABLE_NAME).resolve()
    )
    if not root.is_dir():
        raise SourceError(f"sales root is not a directory: {root}")
    if not table.is_file():
        raise SourceError(f"source table is not a file: {table}")
    try:
        table.relative_to(root)
    except ValueError as exc:
        raise SourceError(f"source table must be inside the sales root: {table}") from exc
    if table.is_symlink():
        raise SourceError(f"source table must not be a symlink: {table}")
    return root, table


def print_text_report(
    root: Path,
    table: Path,
    findings: Sequence[Finding],
    issues: Sequence[SourceIssue],
    write_mode: bool,
    wrote: int,
    details_limit: int,
) -> None:
    counts = Counter(finding.status for finding in findings)
    print(f"Sales root: {root}")
    print(f"Source table: {table}")
    print(f"Mode: {'WRITE' if write_mode else 'PREVIEW'}")
    print("Results:")
    for status in (
        "ready",
        "up_to_date",
        "pair_mismatch",
        "ambiguous",
        "source_conflict",
        "existing_conflict",
        "unmatched",
        "no_tag_line",
        "metadata_error",
        "read_error",
        "write_error",
    ):
        if counts[status]:
            print(f"  {status}: {counts[status]}")
    for status in ("incomplete_source", "invalid_source", "source_conflict"):
        count = sum(1 for issue in issues if issue.status == status)
        if count:
            print(f"  {status} table row(s): {count}")
    if wrote:
        print(f"  written: {wrote}")

    detail_rows: List[str] = []
    for issue in issues:
        detail_rows.append(f"TABLE {issue.status} line {issue.line}: {issue.detail}")
    for finding in findings:
        if finding.status == "ready":
            action = "added" if wrote and finding.updated_bytes is None else "would add"
            detail_rows.append(
                f"{finding.status.upper()} {finding.path}: {action} "
                f"{' '.join(finding.additions)}"
            )
        elif finding.status not in {"up_to_date", "unmatched", "no_tag_line"}:
            detail_rows.append(
                f"{finding.status.upper()} {finding.path}: {finding.detail}"
            )

    if detail_rows:
        print("Details:")
        for row in detail_rows[: max(details_limit, 0)]:
            print(f"  {row}")
        if len(detail_rows) > max(details_limit, 0):
            print(f"  ... {len(detail_rows) - max(details_limit, 0)} more")


def run(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.details_limit < 0:
        parser.error("--details-limit must be zero or greater")

    try:
        root, table = resolve_inputs(args)
        table_text = table.read_text(encoding="utf-8-sig")
        records, conflict_keys, issues = parse_source_table(table_text)
    except (OSError, UnicodeDecodeError, SourceError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    companies_in_source = {key[0] for key in records}.union(
        key[0] for key in conflict_keys
    )
    findings: List[Finding] = []
    paths: Dict[str, Path] = {}
    for path in iter_markdown_files(root):
        if path.resolve() == table:
            continue
        relative = path.relative_to(root).as_posix()
        paths[relative] = path
        findings.append(
            analyze_note(
                path,
                relative,
                records,
                conflict_keys,
                companies_in_source,
            )
        )

    wrote = 0
    if args.write:
        for finding in findings:
            if finding.status != "ready":
                continue
            assert finding.original_bytes is not None
            assert finding.updated_bytes is not None
            try:
                atomic_write(
                    paths[finding.path],
                    finding.original_bytes,
                    finding.updated_bytes,
                )
            except (OSError, RuntimeError) as exc:
                finding.status = "write_error"
                finding.detail = str(exc)
                finding.additions = ()
            else:
                wrote += 1
                finding.original_bytes = None
                finding.updated_bytes = None

    counts = Counter(finding.status for finding in findings)
    payload = {
        "sales_root": str(root),
        "source_table": str(table),
        "mode": "write" if args.write else "preview",
        "written": wrote,
        "counts": dict(sorted(counts.items())),
        "source_issues": [asdict(issue) for issue in issues],
        "findings": [finding.public_dict() for finding in findings],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_text_report(
            root,
            table,
            findings,
            issues,
            args.write,
            wrote,
            args.details_limit,
        )
    return 3 if counts["write_error"] else 0


if __name__ == "__main__":
    raise SystemExit(run())
