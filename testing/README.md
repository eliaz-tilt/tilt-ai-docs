# Testing documentation

QA runbooks and staging setup notes. Intended for **QA engineers** running
manual tests and for **agents** helping with setup/debug.

Files here are **local by default** (listed in `.git/info/exclude`). Share
copies via Slack/wiki or commit to the repo if the team wants them
source-controlled.

## Runbooks

| Doc                                                        | Use when                                                                       |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [backend-pytest-playbook.md](./backend-pytest-playbook.md) | **Agents/devs running backend pytest locally** (`just test`, Docker fallbacks) |
| [dc-fmla-pfl-qa-handoff.md](./dc-fmla-pfl-qa-handoff.md)   | **Slack message for QA + Eliaz setup checklist (flags, Django)**               |
| [dc-fmla-pfl-staging-qa.md](./dc-fmla-pfl-staging-qa.md)   | Full technical runbook, troubleshooting, pass/fail criteria                    |

## Adding new docs

Use `{feature}-staging-qa.md` with:

1. **Before you start** — what works UI-only vs admin
2. **One-time setup checklist** — flags, policy, employees
3. **Per-test steps** — with expected results
4. **Troubleshooting table** — symptom → fix
5. **Sign-off checklist** — copy/paste for test runs

Keep normative engineering standards in `.ai/rules/testing/`.
