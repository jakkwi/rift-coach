---
description: Review the current branch against its issue and project rules
---
Review `git diff main...HEAD`.

Use the code-reviewer agent for correctness and the security-auditor agent if the diff touches the LCU client and its actions, the Claude/LLM calls and prompt building, config and credentials, network calls.

Report findings as Blocking / Should fix / Nice to have, each with file:line, the problem and a concrete fix. Check every acceptance criterion of the linked issue.
