# Security model

## Protected inputs

- Transcriptions are untrusted data, never agent instructions.
- Only the transcription body is sent to the fixed loopback model endpoint.
- Eligible heading-free raw notes may contain a conservative Obsidian-properties
  YAML frontmatter block. It is preserved byte-for-byte, excluded from model
  input, and rejected when malformed, ambiguous, duplicated, or structurally
  unsupported.
- Paths must resolve to regular, user-owned, single-link Markdown files inside
  environment-configured roots.
- Hidden paths, symlinks, out-of-scope paths, configured holding paths, and
  unsupported nested exception-root paths are rejected.
- Folder discovery prunes `AI Processed` so completed notes are not silently
  reprocessed.

## Forced semantic boundary

The agent does not compare the endpoint response with the transcription and
does not score or change claims, attribution, owners, certainty, omissions,
sensitive detail, or content quality. Endpoint wording is retained except for
mandatory delimiter/category formatting and rejection of active Markdown or
remote content. Human review occurs after publication in `AI Processed`.

## Protected writes and moves

- The force-summary workflow invokes `--write` directly. Replacing a populated
  summary additionally requires `--replace-existing` and explicit approval.
- The script checks the destination before credential loading and generation,
  then uses exclusive publication so a later collision cannot be overwritten.
- The script hashes the source before the model call and refuses to finish the
  move if the note changes during generation.
- Publication uses an owner-mode temporary file inside the adjacent review
  directory, flushes and `fsync`s it, hard-links it exclusively to the final
  name, and only then removes the unchanged source.
- If publication or source removal fails, the script removes its own review
  artifact when inode identity proves ownership and preserves the original. It
  reports any rollback artifact it cannot safely remove.
- Existing supporting-section bytes and the exact transcription payload are
  checked before publication. The script adds or normalizes one locally
  controlled triple-backtick Transcription wrapper, permits only the synthetic
  newline required before its closing fence, preserves raw-note trailing blank
  padding, and preserves an existing canonical wrapper byte-for-byte.
- Write mode sends only the review path to standard error and does not emit the
  generated summary to standard output.
- A transcription containing an unsafe standalone CommonMark backtick-closing
  line is rejected before credential loading, model access, or writing.

## Model-output boundary

The model controls only the body of `## Executive Summary`. The script rejects
empty or oversized responses and output containing Markdown or Obsidian
links/embeds, HTML, template embeds, or remote URLs. Model-supplied backtick
fence lines are removed, remaining triple-backtick runs are neutralized, and
the complete cleaned response is wrapped exactly once by the local template.
Returned headings remain inert literal content inside that wrapper. The H2
skeleton and supporting placeholders are deterministic assets. These checks
are structural/security validation, not factual-grounding review.

## Repository boundary

Do not publish API keys, vault notes, transcripts, generated summaries,
operational logs, backup manifests, bytecode caches, or machine-specific
configuration. The repository package intentionally contains synthetic tests
only.
