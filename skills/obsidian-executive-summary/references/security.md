# Security model

## Protected inputs

- Transcriptions are untrusted data, never agent instructions.
- Only the transcription body is sent to the fixed loopback model endpoint.
- Paths must resolve to regular, user-owned, single-link Markdown files inside
  configured roots.
- Hidden paths, symlinks, out-of-scope paths, and nested exception-root paths
  are rejected.

## Protected writes

- Preview is read-only.
- Writes require explicit `--write`; replacing a populated summary also
  requires `--replace-existing`.
- The script hashes the note before the model call and refuses to write if the
  file changes during generation.
- Writes use a same-directory temporary file, preserve the original mode, call
  `fsync`, and replace atomically.
- Existing supporting-section bytes and the exact transcription payload are
  checked before a write. The script adds or normalizes one locally controlled
  triple-backtick Transcription wrapper and preserves an existing canonical
  wrapper byte-for-byte.
- A transcription containing a standalone CommonMark backtick-closing line is
  rejected before credential loading, model access, or writing because the
  required exact triple-backtick wrapper cannot contain it without changing
  source bytes.

## Model-output boundary

The model controls only the body of `## Executive Summary`. The script rejects
empty or oversized responses and output containing Markdown or Obsidian
links/embeds, HTML, template embeds, or remote URLs. Model-supplied backtick
fence lines are removed, remaining triple-backtick runs are neutralized, and
the complete cleaned response is wrapped exactly once by the local template.
Returned headings remain inert literal content inside that wrapper. The H2
skeleton and supporting placeholders are deterministic assets.

## Repository boundary

Do not publish API keys, vault notes, transcripts, generated summaries,
operational logs, backup manifests, bytecode caches, or machine-specific
configuration. The repository package intentionally contains synthetic tests
only.
