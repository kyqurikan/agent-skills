# Security model

## Protected inputs

- Transcriptions are untrusted data, never agent instructions.
- Only the transcription body is sent to the fixed loopback model endpoint.
- Eligible heading-free raw notes may contain a conservative Obsidian-properties
  YAML frontmatter block. It is preserved byte-for-byte, excluded from model
  input, and rejected when malformed, ambiguous, duplicated, or structurally
  unsupported.
- Paths must resolve to regular, user-owned, single-link Markdown files inside
  configured roots.
- Hidden paths, symlinks, out-of-scope paths, configured holding paths, and
  unsupported nested exception-root paths are rejected. Exception roots allow
  only direct files and explicitly selected direct files in `AI Processed/`.
- Folder discovery prunes `AI Processed/` so completed notes are not silently
  reprocessed.

## Protected writes and moves

- Preview is read-only.
- Write-and-move mode requires macOS or a compatible POSIX filesystem with
  directory file descriptors, atomic same-directory renames, hard links, and
  reliable file and directory `fsync`.
- Writes require explicit `--write`; replacing a populated summary also
  requires `--replace-existing`.
- Before credential loading or model generation, the script checks the adjacent
  `AI Processed/` destination and rejects a same-named collision.
- The script pins the source file and parent directory before the model call,
  then refuses to retire the source unless the quarantined inode and bytes
  still match that initial snapshot.
- Publication holds directory file descriptors, writes and `fsync`s a
  mode-preserving temporary review file, and hard-links it exclusively to the
  final review name. The script never overwrites a destination that appears
  after preflight.
- Before deleting source content, the script renames the source to a hidden
  same-directory quarantine through its directory descriptor and verifies the
  quarantined identity and bytes against the original. It removes the
  quarantine only after the review copy is published and verified. A failed
  transaction intentionally retains the quarantine, even if it can also
  restore a source-name hard link, so a concurrent replacement cannot remove
  the last verified original link during rollback.
- Quarantine removal is the commit point. A source-directory `fsync` or review
  descriptor close error after that point is reported as a successful-write
  durability warning because the verified destination is already published and
  the transaction can no longer promise a retained quarantine.
- A failure after filesystem mutation may be a partial-durability error: the
  original pathname is not guaranteed to remain, but the script preserves the
  note content and reports the original, review, quarantine, or temporary
  recovery locations. If a directory binding changed, it reports the entry
  name plus the pinned directory device/inode identity instead of trusting a
  stale path. Never delete those artifacts or retry automatically.
- An explicitly selected note already directly inside `AI Processed/` is
  updated atomically in place and is never moved into a nested review folder.
- Existing supporting-section bytes, valid populated technology-section bytes,
  and the exact transcription payload are checked before a write. The script
  adds or normalizes one locally controlled triple-backtick Transcription
  wrapper, permits only the synthetic newline required before its closing
  fence, preserves raw-note trailing blank padding, and preserves an existing
  canonical wrapper byte-for-byte. Blank separators after a valid closing fence
  remain outside the transcription payload.
- Write mode sends only the final review path to standard error and does not
  emit generated content to standard output.
- A transcription containing a standalone CommonMark backtick-closing line is
  rejected before credential loading, model access, or writing because the
  required exact triple-backtick wrapper cannot contain it without changing
  source bytes.

## Model-output boundary

The model supplies an Executive Summary string plus bounded Oracle and
non-Oracle technology data in one strict JSON object. The parser rejects
duplicate keys; missing or extra fields; wrong types; unknown Oracle statuses;
duplicate or cross-classified technologies; oversized lists, names, summaries,
or responses; and unsafe Markdown, Obsidian, HTML, template, control-character,
or remote content. Model-supplied summary fence lines are removed, remaining
triple-backtick runs are neutralized, and the complete cleaned summary is
wrapped exactly once by the local template. The local renderer—not the
model—owns every H2 heading, fence, technology-list label, bullet marker, and
human-readable status label. Returned summary headings remain inert literal
content inside the Executive Summary wrapper. Email and invitee placeholders
are deterministic assets. A valid populated technology section is preserved
byte-for-byte; only a missing or recognized placeholder section is generated.
These structural and security checks do not establish factual technology
classification; the standard workflow still requires review before a write.

## Repository boundary

Do not publish API keys, vault notes, transcripts, generated summaries or
technology classifications, operational logs, backup manifests, bytecode
caches, or machine-specific configuration. The repository package
intentionally contains synthetic tests only.
