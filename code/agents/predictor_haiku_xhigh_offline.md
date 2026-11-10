---
name: predictor_haiku_xhigh_offline
description: Haiku 5.5 (xhigh effort) predictor for the 2026Q3 corpus runs. Receives ONLY the bare item prompt, with no CLAUDE.md and no memory (omitClaudeMd). May use every tool at its own discretion EXCEPT internet ones (user rule 2026-10-24); internet-facing tools and tools that contact other sessions are disallowed; the launcher loads no MCP servers and no advisor. Empty body so it carries no custom system-prompt instructions.
model: claude-haiku-5-5
effort: xhigh
disallowedTools: WebSearch, WebFetch, ListAgents, SendMessage, RemoteTrigger, PushNotification, DesignSync
omitClaudeMd: true
---
