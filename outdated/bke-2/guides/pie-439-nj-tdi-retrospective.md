# PIE-439 NJ TDI retrospective ([#11218](https://github.com/ourtilt/tilt-repo/pull/11218))

Case study for BKE 2.0 lane PRs. Read the
[playbook](./lane-topology-pr-playbook.md) for actionable checklists; this page
is the narrative of what landed and what reviewers pushed back on.

---

## Goal

Ship NJ Temporary Disability Insurance on the BKE 2.0 lane path (catalog
topology + BFF routing), scoped to the golden L&C doc. Flag
`enableBKENewJerseyTDI` stays off until rollout.

---

## What went well

### Catalog structure

- `nj-tdi.bank.yaml`: 26 weeks, `eventBased`, protection pay (state sets
  dollars; we track duration)
- `nj-tdi.topology.yaml` rev 5: `own-disability` + `pregnancy-disability` lanes,
  7-day standard wait, nine server scenarios for Rule Studio
- Lane gates: `workingState`, `hasMetNjEarnings`, `isContinuous`,
  `isNonWorkRelated` (own-disability only)

### Product alignment in writing

- Earnings: platform `hasMetNjEarnings` carries $310/week OR $15,500; YAML does
  not hardcode dollars
- COVID/PHE: explicitly blocked on missing survey facts, not "out of scope
  forever"
- Continuous-only encoded on lane path (`isContinuous` lever)

### Pragmatic gaps documented

- **22-day retro wait**: topology keeps 7-day wait; Django overlay
  (`nj_tdi_waiting`) zeroes wait at 22+ calendar days (option A). Scenario
  `own-disability-22-plus-days` documents expected overlay behavior
- **NJ FLI seam**: `recoveryEnd` lever seeded for future bonding; bonding lanes
  live in future `nj-fli`
- Post-merge note: run `store_custom_waiting_period_config_data` per env for
  PaycalcItem baseline

### Engineering follow-through

- Deleted redundant `nj-tdi.rule.yaml` once lanes owned eligibility (matches WA
  PFML)
- Fixed changelog wording: FLI seam is deferred design, not "schema cannot
  express"
- Final commit rewired shadow + Rule Studio through topology-aware evaluate
  after rebase regression

### Test coverage called out in PR

- `test_lanes.py` NJ lever matrix (~313 lines added on branch)
- `test_nj_tdi_waiting.py`, `test_nj_tdi_recovery.py`
- Existing `NewJerseyTDI` waiting-period tests still pass (28 total cited in PR
  comments)

---

## What drew review friction

### BKE 1.0 ↔ 2.0 coupling (dmwyatt, blocking theme)

**Problem**

```python
# nj_tdi_recovery.py (BKE 2.0 catalog)
from benefits.rules.new_jersey.tdi import NewJerseyTDI
rule = NewJerseyTDI(None)
bonding_start = rule.get_global_bonding_min_start_date(leave)

# new_jersey/tdi.py (BKE 1.0 legacy)
from benefits.rules.catalog.nj_tdi_waiting import nj_tdi_waiting_days_for_spans
```

Legacy TDI is dark in prod, but the PR made both versions depend on each other
across package boundaries.

**Reviewer ask:** leave 1.0 alone, or delete it in a **separate** PR. Do not
entangle.

**Lesson for PIE-468 / PIE-447:** extract shared math to a neutral helper, or
keep SQL-only V1 levers and document LS/med-cert gaps. NY PFL already follows
the SQL lever approach for `recoveryEnd`.

### Med-cert extension via legacy instance method

Motivation was parity with `get_global_bonding_min_start_date` including
accepted med certs. Implementation reached through a `NewJerseyTDI(None)`
instance instead of copying/extracting the pure date logic.

**Better shapes**

1. `benefits/rules/new_jersey/tdi_recovery_dates.py` with functions both paths
   call
2. V1 SQL lever for standard 6/8-week window only; extended recovery LS-handled
   (NY PFL V1)

### Rebase regression (caught by author)

After merging `bke-integration`, shadow evaluation and leave-derived Rule Studio
paths still used WA-default routing levers and skipped the 22-day overlay. Fixed
in commit `a2ddc51`.

**Lesson:** after every rebase onto `bke-integration`, run the topology routing
tests and grep for hard-coded WA paths.

---

## Migration chain on the branch

| Migration | Purpose                                                                          |
| --------- | -------------------------------------------------------------------------------- |
| 0047      | NJ routing levers (`workingState`, `hasMetNjEarnings`, `pregnancyDisability`, …) |
| 0048      | `isContinuous`                                                                   |
| 0049      | `isNonWorkRelated`                                                               |
| 0050      | `recoveryEnd` (SQL from EDD + birth_type)                                        |
| 0051      | Update `recoveryEnd` lever description                                           |

When other lane PRs land on the same base, expect renumbering (NY PFL used
`0048` for NY levers after `0047_seed_work_state_lever` from integration).

---

## Locked decisions table (copy pattern for other PRs)

| Item              | Decision                                                                              |
| ----------------- | ------------------------------------------------------------------------------------- |
| Non-work-related  | Own-disability requires `isNonWorkRelated is true`; unanswered/work-related → no lane |
| 22-day retro wait | Option A: Django overlay + dynamic waiting_period_config; topology stays 7-day        |
| recoveryEnd / FLI | Lever on TDI path; bonding in future `nj-fli` topology                                |
| COVID / PHE       | Not on survey V1; changelog only                                                      |
| Earnings          | Platform `hasMetNjEarnings`; L&C golden $310 / $15,500                                |

---

## How to validate (Rule Studio)

From PR author comments:

1. Open New Jersey → NJ Temporary Disability Insurance (lanes)
2. Use **Server scenarios**, not WA persona chips
3. Negative cases: earnings, not-in-NJ, intermittent, work-related → no active
   lanes
4. `own-disability-22-plus-days` expects Django retro overlay, not raw
   `--evaluate` wait policy alone

---

## Follow-up items if revising the PR

- [ ] Decouple `nj_tdi_recovery` from `NewJerseyTDI` class
- [ ] Move waiting math out of `benefits.rules.catalog` or stop importing it
      from `tdi.py`
- [ ] Consider deleting legacy `NewJerseyTDI` in a follow-up PR if prod will
      never use BKE 1.0 path again
