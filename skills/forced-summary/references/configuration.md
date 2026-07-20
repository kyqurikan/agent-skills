# Configuration

The published skill has no built-in vault path. Set these variables in the
agent or project environment before using it:

- `OBSIDIAN_SUMMARY_ALLOWED_ROOTS` — required list of absolute directories,
  separated by the platform path separator (`:` on macOS/Linux). Notes may be
  located anywhere beneath these roots.
- `OBSIDIAN_SUMMARY_EXCEPTION_ROOTS` — optional list of absolute directories.
  Direct Markdown files are eligible. A direct file in an exception root's
  `AI Processed/` subfolder is eligible only for explicit reprocessing; every
  other nested exception path is rejected.
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
not commit real paths or credentials to a public repository. Batch discovery
must prune directories named `AI Processed` before collecting Markdown files.

## Review destination

A successful `--write` publishes the updated note at
`<source-directory>/AI Processed/<source-name>` and then removes the unchanged
source. The script creates the adjacent review directory when needed. It never
overwrites an existing destination. A directly selected note whose parent is
already named `AI Processed` is updated in place.

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

The selected transcription and bearer credential are sent to whichever local
process owns port `8088`. Verify that process before summarizing sensitive
notes.
