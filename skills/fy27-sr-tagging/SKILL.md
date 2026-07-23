---
name: fy27-sr-tagging
description: Match Oracle Vault Sales Team FY27 Markdown notes to the SRs table in `Tag and SRs.md` using the notes' existing exact Company Name (`#Customer_...`) and CPR (`#CPR_...`) tags, then preview or add the corresponding SR Number and OppID tags beside tags stored either in YAML `tags` lists or inline body tag lines. Use when asked to run FY27 SR Tagging, sync FY27 notes with the SR table, add SR/OppID tags, audit FY27 SR tagging, or retag FY27 sales files after the table changes.
---

# FY27 SR Tagging

Use the deterministic script to correlate the SR table with FY27 sales notes. Require an exact Company Name and CPR tag pair; do not infer a match from filenames, transcript text, or fuzzy company names.

## Scope

- Default sales root: `$FY27_SALES_ROOT` when set; otherwise `~/Documents/Oracle Vault/Sales Team FY27`
- Default source table: `Tag and SRs.md` under that root
- Eligible targets: non-symlink Markdown files recursively under the sales root
- Exclusions: the source table itself and files inside hidden directories
- Source columns: `Company Name`, `SR Number`, `OppID`, and `CPR`
- Target metadata: a top-level YAML `tags` block/inline list, otherwise the first inline tag-only body line

Read [references/tagging-contract.md](references/tagging-contract.md) when the source table, note format, matching rules, or output states need interpretation.

## Workflow

1. Run a preview:

   ```bash
   python3 scripts/tag_fy27_srs.py
   ```

2. Review the summary and every reported conflict. Treat `ready` as the only state eligible for mutation. Do not weaken the matching rules to increase the match count.

3. Ask once for confirmation before writing unless the user already explicitly asked to apply, add, sync, tag, or update the files in the current request.

4. Apply the previewed rules:

   ```bash
   python3 scripts/tag_fy27_srs.py --write
   ```

5. Re-run the preview. Confirm that the prior `ready` count is now represented by `up_to_date` and that no new conflicts appeared.

Use custom fixture or alternate-vault paths only when explicitly needed:

```bash
python3 scripts/tag_fy27_srs.py \
  --sales-root "/path/to/Sales Team FY27" \
  --table "/path/to/Tag and SRs.md"
```

## Matching Rules

- Require one exact `(Company Name, CPR)` pair from the table to occur on the note's inline tag line.
- Require both `SR Number` and `OppID` to be populated in the matching table row.
- Add the table values in `SR Number` then `OppID` order. Keep `#` for body tags and follow the YAML list's existing hash/quote style for YAML tags.
- Insert missing tags immediately after the later of the matched Company Name or CPR tags, within the same metadata container.
- Preserve all other note content, whitespace, line endings, and existing tag order.
- Prefer a top-level YAML `tags` list when present; otherwise use the leading inline tag-only body line.
- Skip notes with no eligible tag container, unsupported/ambiguous YAML metadata, no exact pair, multiple matching rows, conflicting table rows, or conflicting existing SR/OppID tags.
- Never alter or remove an existing tag.
- Never modify `Tag and SRs.md`.
- Treat a repeated run as idempotent: correctly tagged notes remain unchanged.

## Interpret Results

- `ready`: exact, corroborated match; preview shows tags that would be added.
- `up_to_date`: both expected tags are already present.
- `pair_mismatch`: a table customer appears on the note, but its CPR does not agree.
- `ambiguous`: more than one complete table record matches the note.
- `source_conflict`: duplicate table keys disagree on SR Number or OppID.
- `existing_conflict`: a different SR Number or OppID-like tag is already present.
- `incomplete_source`: the table row lacks SR Number or OppID and cannot be applied.
- `metadata_error`: a YAML `tags` property exists but is duplicate, malformed, or not a list.
- `unmatched` / `no_tag_line`: no safe deterministic edit is available.

Do not write manual exceptions for skipped notes. Report the path, evidence, and state so the user can correct the note tags or source table first.
