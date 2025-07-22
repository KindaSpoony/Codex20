## GitHub Workflow: GPT Autonomous Agent

This repository includes an automated workflow that responds to issues, pull requests and pushes to the `main` branch. The workflow maintains a small JSON file (`state.json`) so each run can access prior context. When triggered, it sends the current GitHub event payload along with the last saved state to ChatGPT (via the `openai-chatgpt-action`).

ChatGPT returns a short recommendation which is evaluated by the workflow's reflex arc. Depending on the text it may request human review, add a comment to the relevant issue or pull request, or simply log the output. After each run, the new state and the generated response are committed back to the repository so subsequent runs have a history to reference.

The intent is to provide continuous, introspective feedback on repository activity while still allowing human oversight whenever GPT signals that review is necessary.
