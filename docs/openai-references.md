# OpenAI References

This file is a short pointer list for maintainers. It does not define subagents-dispatch behavior and must not duplicate project policy.

Consult the current OpenAI documentation when platform behavior, Plugin packaging, Skills, Native Subagents, custom Agents, runtime control, model availability, or submission requirements matter:

- Plugin concepts: https://developers.openai.com/plugins/concepts/plugins
- Plugin packaging: https://developers.openai.com/plugins/build/plugins
- Skills: https://developers.openai.com/plugins/build/skills
- Plugin submission: https://developers.openai.com/plugins/deploy/submission
- Codex Subagents, including Agent management/control and custom Agent inheritance: https://developers.openai.com/codex/subagents
- Codex App Server, including thread events and token-usage notifications available to clients: https://developers.openai.com/codex/app-server
- Codex Hooks, for platform reference and historical compatibility work: https://developers.openai.com/codex/hooks
- Codex configuration reference: https://developers.openai.com/codex/config-reference
- Codex model guidance: https://developers.openai.com/codex/models

Platform surfaces can change independently of this repository. Re-check the current documentation and actual Codex behavior before changing platform-facing claims.

The existence of an App Server or Hook event does not imply that an ordinary installed Skill receives that event. Native Core does not use Plugin Hooks as lifecycle correctness authority. subagents-dispatch reports token/model/runtime facts only through evidence the active execution path can actually access.

Project behavior remains owned by the two explicit Skills under `skills/` and the canonical contracts under `contracts/`.
