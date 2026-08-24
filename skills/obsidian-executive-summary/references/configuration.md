# Configuration

The published skill has no built-in vault path. Set these variables in the
agent or project environment before using it:

- `OBSIDIAN_SUMMARY_ALLOWED_ROOTS` — required list of absolute directories,
  separated by the platform path separator (`:` on macOS/Linux). Notes may be
  located anywhere beneath these roots.
- `OBSIDIAN_SUMMARY_EXCEPTION_ROOTS` — optional list of absolute directories.
  Direct Markdown files are eligible. A direct file in an exception root's
  `AI Processed/` subfolder is eligible only when explicitly selected for
  in-place reprocessing; every other nested exception path is rejected.
- `OBSIDIAN_SUMMARY_HOLDING_PREFIX` — optional case-insensitive path-component
  prefix rejected beneath standard roots. Defaults to `to be tagged fy`.
- `OCI_GENAI_GATEWAY_API_KEY` — optional per-run credential override.

Example shell configuration:

```bash
export OBSIDIAN_SUMMARY_ALLOWED_ROOTS="/absolute/path/to/vault/sales-current:/absolute/path/to/vault/sales-archive"
export OBSIDIAN_SUMMARY_EXCEPTION_ROOTS="/absolute/path/to/vault/review-staging"
export OBSIDIAN_SUMMARY_HOLDING_PREFIX="to be reviewed"
export OCI_GENAI_GATEWAY_API_KEY="replace-with-a-runtime-secret"
```

The exact environment configuration mechanism depends on the agent host. Do
not commit real paths or credentials to a public repository. Folder and batch
discovery must prune directories named `AI Processed` before collecting
Markdown files.

## Filesystem requirements

Write-and-move mode requires macOS or a compatible POSIX filesystem with
directory file descriptors, atomic same-directory renames, hard links, and
file and directory `fsync`. The source and its adjacent `AI Processed/`
directory must support those operations. Do not use this write workflow on
Windows or a filesystem that does not provide these durability primitives.

## Review destination

Preview is read-only and reports the planned review destination. A cleanly
successful approved `--write` publishes the updated note at
`<source-directory>/AI Processed/<source-name>`. Before publication, it
quarantines and verifies the original source; after publication is durable, it
removes that quarantine. The script creates the adjacent review directory when
needed and never overwrites an existing destination. A directly selected note
whose parent is already named `AI Processed` is updated in place.

If a same-named review file already exists, processing stops before credential
loading or model generation and leaves both files unchanged. Replacing a
populated Executive Summary requires explicit approval and
`--replace-existing` in addition to `--write`. A valid populated technology
section is preserved byte-for-byte; a missing or recognized placeholder
technology section is generated during the write.

After publication begins, a failed durability or cleanup step may leave the
preserved content at a review, quarantine, temporary, or original path. The
script intentionally retains a verified quarantine after a failed transaction,
even when a source-name link was restored. The error identifies the recovery
locations that require inspection. If a source
or review directory was renamed, it reports the recovery entry name and pinned
directory device/inode identity because the old pathname is no longer trusted.
Do not assume the original pathname still exists, delete recovery artifacts, or
retry until those locations have been checked.

Quarantine removal is the commit point. A source-directory `fsync` or review
descriptor close error reported after that point is a successful-write
durability warning: verify the published destination, but do not classify the
item as a failed transaction or expect a quarantine artifact.

## Stored credential alternative

When `OCI_GENAI_GATEWAY_API_KEY` is absent, the script reads
`.secrets/gateway-api-key` relative to the skill directory. Create both the
directory and file as the current user, with modes `0700` and `0600`
respectively. The loader rejects symlinks, multiple hard links, non-owner
files, oversized values, and group/world permissions.

Never commit `.secrets/`. The skill-local and repository `.gitignore` rules
exclude it.

## Endpoint boundary

The endpoint and model are intentionally fixed:

- Endpoint: `http://127.0.0.1:8088/v1/chat/completions`
- Model: `cohere.command-a-03-2025`
- User prompt prefix: `generate an executive summary`

The endpoint response must be one bounded JSON object with exactly
`executive_summary`, `oracle_and_oracle_cloud_technologies`, and
`non_oracle_technologies`. Oracle technology items contain exactly a
`technology` name and one of the statuses `customer_used`, `oracle_pitched`,
or `both`; non-Oracle items are technology-name strings. The script validates
that schema and renders the Markdown headings, fences, labels, status wording,
and bullet syntax locally.

The selected transcription and bearer credential are sent to whichever local
process owns port `8088`. Verify that process before summarizing sensitive
notes.
