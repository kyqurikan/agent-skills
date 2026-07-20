# Agent Skills

A collection of specialized skills following the open standard for agent capabilities.

## Included Skills

### 🍎 [Apple Container Skill](./skills/apple-container-skill)
Interact with the Apple Container CLI to manage containers, images, volumes, networks, and system services on macOS.
- **Key Features:** System lifecycle management, networking setup, and persistent data handling for Apple's native container runtime.

### 🛠️ [DevContainer Helper](./skills/devcontainer-helper)
Create, configure, and manage `devcontainer.json` environments.
- **Key Features:** Supports image-based, Dockerfile, and Docker Compose setups with Service Architecture Principles (sidecars over DinD), Performance Optimization (baking for speed), and automated "Features" integration with Dependabot support.

### 🎨 [UX Designer](./skills/ux-designer)
Expert UX/UI design assistant based on the "Refactoring UI" philosophy.
- **Key Features:** Logic-based design rules, strict hierarchy enforcement, complete design system tokens, Responsive Design & Robustness rules, Data-Dense Interface Principles, and Component Standards.

### 🔄 [GitHub Scrum Flow](./skills/github-scrum-flow)
Unified expert for Project Management (Scrum/Agile) and GitHub Flow enforcement.
- **Key Features:** Track orchestration, backlog hygiene, GitHub Issue synchronization, branch management, and enforcing strict PR-first workflows (Issue <-> Track <-> Branch).

### 🎙️ [MacWhisper](./skills/macwhisper)
Read-only access to [MacWhisper](https://goodsnooze.gumroad.com/l/macwhisper) transcription sessions from its local SQLite database. Zero configuration for a standard MacWhisper install.
- **Key Features:** List unprocessed recordings, fetch diarized transcripts with hallucination filtering, keyword search, processed-session state tracking, and UTC time windows for calendar enrichment.

### 📝 [Obsidian Executive Summary](./skills/obsidian-executive-summary)
Generate a structured four-section sales note from an approved Obsidian transcription using a fixed local OpenAI-compatible model endpoint.
- **Key Features:** Preview-first operation, configurable path allowlists, atomic writes, exact transcript preservation inside a deterministic fence, normalized model delimiters, deterministic supporting sections, strict credential permissions, untrusted-transcript handling, and synthetic tests.

### ⚠️ [Forced Summary](./skills/forced-summary)
Force-write the pinned local endpoint's executive-summary output into eligible Obsidian notes, then move successful notes to `AI Processed/` for human review.
- **Key Features:** Explicit opt-in, direct write-and-move batches, destination-collision preflight, atomic structural safeguards, exact transcript preservation, and deterministic supporting sections. **Warning:** Unlike Obsidian Executive Summary, this skill intentionally skips semantic grounding and content-quality review; all outputs require human review.

## Usage

These skills are designed to be dropped into your agent's skills directory.

```bash
# Example: Symlink a skill to your agent's skills location
ln -s $(pwd)/skills/apple-container-skill /path/to/agent/skills/
```
