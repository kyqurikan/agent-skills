# Provenance

This hardened derivative replaces the original MacWhisper skill from
`gabeosx/agent-skills` at commit
`2ce2ec5388a4da688d3692c9d213eab3345228b0`.

The security review and rewrite were performed on 2026-07-14. The derivative
removes shell-based SQLite access and implements a dependency-free, local MCP
server with bounded structured output, parameterized queries, explicit trust
boundaries, private atomic state, and synthetic regression tests.

The upstream repository did not contain a license at the reviewed commit. This
file records provenance and does not grant or imply additional licensing rights.
