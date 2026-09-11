# PR body + reviewer guide checklist

For lane-topology PRs targeting `bke-integration`. Copy structure from
[`.github/pull_request_template.md`](../../../.github/pull_request_template.md)
and add a short **Reviewer guide** section at the bottom (see
[#11119](https://github.com/ourtilt/tilt-repo/pull/11119) examples).

---

## Required sections

1. **Issue Link** — full Jira URL
   (`https://ourtilt.atlassian.net/browse/PIE-XXX`) for auto-linking
2. **Checklist** — flags, tests, docstrings, breaking API (usually N/A)
3. **Description** — what ships in catalog + BFF + migrations
4. **Motivation** — why lane path, why now, link to L&C doc
5. **Observability** — usually "no new monitors; flag off"
6. **Rollback plan** — disable flag, revert PR, re-import catalog if needed
7. **Testing** — commands that actually ran + post-deploy steps
8. **Performance** — usually negligible for routing/lever SQL
9. **Visual changes** — N/A for backend-only

---

## Lane PR extras (beyond template)

Add these subsections in Description or Motivation:

### Locked decisions table

Product/engine choices reviewers should not re-litigate in review. Example rows:
earnings fact vs hardcoded thresholds, overlay option A vs catalog-only wait,
Missing vs deny for NULL facts.

### Semantics changes vs legacy BKE 1.0

Even when intentional, list deltas (tracking method, intermittent cap, caregiver
matching, earnings NULL behavior). NJ FLI PR table is a good model.

### Out of scope / deferred

Three buckets:

- Not in L&C program at all
- In L&C but blocked on survey/platform facts
- In L&C but deferred to another topology/PR

### Post-merge / per-environment

Template seeds, management commands, flag rollout order, catalog import command.

---

## Reviewer guide (one short block)

Write like notes to a coworker, not an AI checklist:

- What logic is subtle (Missing vs deny, overlay vs YAML wait, migration
  renumbering)
- Where tests prove the important behavior
- Merge order with sibling PRs if any
- What you intentionally did **not** do

Avoid file laundry lists unless one file is the whole story (`lanes.py` topology
routing).

---

## Anti-patterns in PR prose

| Oversell                       | Say instead                                                              |
| ------------------------------ | ------------------------------------------------------------------------ |
| "Replaces legacy rule in prod" | "Shadow/Rule Studio path; legacy asleep when flag on"                    |
| "Routes to manual review"      | "Sets legacy status-hold flag; no prod hold without ApprovalMethod data" |
| "Schema cannot express X"      | "Deferred to overlay" / "Blocked on facts" / "Lives in other topology"   |
| "Fully implements L&C"         | "V1 on collected facts; see out-of-scope table"                          |

See also [`../../reviewer/dustin.md`](../../reviewer/dustin.md) for BKE 1.0
activation PR wording.
