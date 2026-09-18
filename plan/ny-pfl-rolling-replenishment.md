# NY PFL rolling replenishment and DBL/PFL combined-cap recovery

**Status:** Ready for implementation/review; continue the staged work already in
the worktree.  Do not reset or discard the staged changes.

**Scope:** Fix NY PFL entitlement and shared NY DBL/PFL cap behavior when prior
usage ages out of a rolling 52-week window, including the BKE/Programs-tab error
reported in the attached testing notes.

## Problem and acceptance criteria

The reported scenario is:

1. NY DBL is used for 20 weeks from 2026-08-03 through 2026-12-20.
2. NY PFL is used for 6 weeks from 2027-02-01 through 2027-04-25.
3. A later 12-week PFL request runs from 2027-07-26 through 2027-10-17.

The 26-week combined cap correctly allows no PFL at the start of the later
request while all 20 DBL weeks remain in the applicable rolling window. Once
the earliest DBL usage ages out, the remaining 6 PFL weeks must become payable,
provided they remain inside the PFL entitlement period that began with the first
PFL use. The result must expose the recovered span instead of returning the
combined-cap exhaustion error for the entire request.

The implementation is complete only when all of the following hold:

- Prior PFL usage is counted against the 12-week PFL bank using the configured
  rolling-back tracking method and replenishes day-by-day after it ages out.
- Prior DBL and PFL usage are counted together against the 26-week combined cap
  using one deterministic rolling-back window. A DBL usage day that leaves the
  window can reopen combined headroom without resetting the PFL annual bank.
- The first payable day is defined and tested with inclusive date semantics;
  the statutory/product interpretation must be agreed in the PR before code is
  finalized. The current staged regression expects 2027-08-04 for DBL beginning
  2026-08-03; retain that expectation only if it matches the BKE contract.
- PFL never exceeds the remaining 12-week bank, the combined 26-week bank, the
  request schedule, or applicable parental/bonding dates.
- A leave that never reaches replenishment remains fully capped; a leave that
  crosses replenishment returns separate pre/post spans with no accidental
  coverage before the recovery date.
- The behavior is correct for tracked and untracked templates, intermittent
  schedules, mixed DBL/PFL tracking-template configuration, and persisted
  entitlement rows.
- Existing NY DBL behavior, PFL eligibility gates, reasoning text, and Programs
  tab accommodation checks do not regress.

## Evidence and repository findings

- The prior session's changes are staged in:
  - `backend/benefits/rules/new_york/combined_cap.py`
  - `backend/benefits/rules/new_york/pfl.py`
  - `backend/benefits/rules/new_york/tests/test_pfl.py`
- The staged work already adds a shared-cap replenishment date, a schedule split
  in `NewYorkPFL._calculate_spans`, full-bank sizing for tracked PFL, and the
  Christian Castorena DBL/PFL regression test.
- `BaseBenefitRule.calculate_spans()` applies `get_tracked_max_duration()` and
  then invokes `SpanLimiter`; therefore a combined cap caused by DBL cannot be
  delegated to the PFL bank alone. The schedule must remain available for a
  mid-leave split, while the PFL bank still enforces its own rolling usage.
- `for_full_entitlement()` intentionally suppresses only the rule's own prior
  usage. Shared-cap reads must continue to include the other NY program.
- The FMLA sibling-replenishment implementation in
  `backend/benefits/rules/fmla.py` is the closest established pattern for
  splitting pre/post-replenishment spans.
- The NY Workers' Compensation Board states that PFL is up to 12 weeks in a
  52-week period and that combined DBL/PFL cannot exceed 26 weeks in a 52-week
  period: [DBL guidance](https://www.wcb.ny.gov/content/main/DisabilityBenefits/what-are-disability-benefits.jsp)
  and [PFL bonding guidance](https://paidfamilyleave.ny.gov/bonding-leave-birth-child).

## Required implementation review

### 1. Make the rolling-window calculation explicit and reusable

Review `combined_cap.py` for these invariants:

- Use the same tracking method for both programs; when templates disagree,
  preserve the existing safe fallback and add/retain reasoning.
- Query only published benefit schedule days and count the correct benefit UUID.
- Define the lookback interval once, including whether its start/end are
  inclusive. Avoid a special-case `+ 1 day` unless the contract is documented
  and covered by boundary tests.
- Find the first day on which the combined cap actually has headroom, not merely
  the first day any DBL row overlaps a lookback boundary. Add a test with a
  partial/fragmented DBL schedule and a test where DBL usage does not exhaust
  the combined cap.
- Keep helpers side-effect free except for existing rule reasoning behavior.

### 2. Integrate with tracked span calculation safely

Review `pfl.py` for these invariants:

- `get_tracking_bank_duration()` remains the full 12-week PFL bank; never
  double-deduct prior PFL usage by passing a netted duration to SpanLimiter.
- If only prior PFL binds, let SpanLimiter handle rolling replenishment.
- If prior DBL binds and ages out during the request, pass the full schedule and
  split at the combined-cap recovery date. The post-recovery portion must be
  limited by the remaining PFL program bank.
- If no recovery occurs in the request, retain the full-request cap behavior.
- Preserve the normal parent/bonding end-date and intermittent full-day logic.
- Avoid ORM queries from pure date arithmetic helpers; keep data access at the
  existing utility boundary.

### 3. Validate adjacent call paths

Inspect `can_benefit_accommodate_update`, entitlement persistence, variable-time
duration calculation, and result serialization. Confirm that a zero
`get_max_duration()` at the request start does not cause a caller to reject the
leave before span calculation gets a chance to recover mid-leave. If it does,
adjust that boundary with a focused regression test rather than weakening the
combined-cap rule globally.

## Test matrix

Add or update focused pytest functions in
`backend/benefits/rules/new_york/tests/test_pfl.py` and, if shared helpers are
changed, `test_dbl.py` or a dedicated combined-cap test module.

Required cases:

1. 20 DBL weeks + 6 PFL weeks: later request is capped before aging and funds
   exactly the remaining 6 PFL weeks after aging.
2. Exact aging boundary: prior DBL starts one day before/at/after the expected
   52-week boundary; assert the first payable date explicitly.
3. Prior PFL fully exhausts the 12-week bank: no recovery from DBL aging can
   create PFL beyond the annual PFL bank.
4. Prior PFL partially uses the bank and then ages out: SpanLimiter restores the
   bank without double deduction.
5. Combined cap has positive headroom at request start: no unnecessary split or
   lost days.
6. Combined cap is exhausted and the request ends before recovery: no spans.
7. Fragmented/weekday DBL schedule: recovery is based on actual counted benefit
   days and does not treat an unbenefited calendar gap as usage.
8. Tracking methods disagree: safe fallback remains deterministic.
9. Untracked PFL and tracked PFL both preserve existing cap semantics.
10. Intermittent PFL: partial workdays remain excluded on both sides of the
    recovery split.
11. Programs-tab `can_benefit_accommodate_update` accepts a valid recovered
    post-boundary request and rejects an over-limit request.
12. NY DBL requesting its own duration after prior PFL still respects the same
    26-week combined cap.
13. Existing non-rolling/calendar-year behavior remains unchanged.

Follow repository testing rules: plain pytest functions, one behavior per test,
explicit dates, minimal fixtures, and a regression test before changing a
failing behavior where practical.

## Verification gates

Run, in order:

```bash
uv run ruff check backend/benefits/rules/new_york/combined_cap.py \
  backend/benefits/rules/new_york/pfl.py \
  backend/benefits/rules/new_york/tests/test_pfl.py
uv run pytest backend/benefits/rules/new_york/tests/test_pfl.py \
  backend/benefits/rules/new_york/tests/test_dbl.py
uv run pytest backend/benefits/rules/new_york/tests
```

If local pytest collection is blocked by the known missing WeasyPrint native
library, install the repository-documented dependency or run the same commands
in the supported dev container; do not mark the fix green based only on static
inspection. Record the exact environment and command in the handoff.

Before merge, inspect the final diff for unrelated changes, run `git diff
--check`, and review reasoning messages for PII. Do not log employee data.

## Delegated work sequence

After this plan is reviewed, use separate agents with disjoint scopes:

1. **Plan/code reviewer:** audit the staged implementation against this plan,
   especially boundary semantics and BaseBenefitRule/SpanLimiter contracts;
   return concrete defects and recommended patches, without editing.
2. **Implementation agent:** implement the agreed fixes in
   `combined_cap.py` and `pfl.py`, including any helper refactor. It may edit
   only those two files.
3. **Regression-test agent:** add/update the test matrix in `test_pfl.py`,
   `test_dbl.py`, or a new focused test file. It must not edit production code.
4. **Final reviewer:** inspect the combined diff, run lint/tests where possible,
   and report unresolved risks and exact commands/results.

Agents must read `.ai/README.md`, backend standards, and testing standards;
preserve unrelated user work; and list every changed file in their handoff.

## Handoff prompt for a fresh AI agent

```text
Continue the NY PFL rolling-replenishment fix in
/Users/ultirequiem/work/tilt-repo.

Read first:
1. ai-docs/plan/ny-pfl-rolling-replenishment.md
2. .ai/README.md
3. .ai/rules/backend/backend-quality-standards.mdc
4. .ai/rules/testing/testing-standards.mdc
5. AGENTS.md and AGENTS.local.md if present

Do not reset, discard, or overwrite the existing staged work. Audit it first:
  backend/benefits/rules/new_york/combined_cap.py
  backend/benefits/rules/new_york/pfl.py
  backend/benefits/rules/new_york/tests/test_pfl.py

The target behavior is the reported scenario: 20 weeks NY DBL from
2026-08-03 through 2026-12-20, 6 weeks NY PFL from 2027-02-01 through
2027-04-25, and a later PFL request from 2027-07-26 through 2027-10-17.
The later request must recover exactly the remaining 6 PFL weeks once prior DBL
usage leaves the rolling 52-week combined window, while never exceeding the
12-week PFL bank or 26-week combined cap.

First review the plan and staged diff. Then delegate/review in this order:
plan/code audit → production implementation → regression tests → final review.
Keep production and test write scopes disjoint. Resolve inclusive date-boundary
semantics with explicit tests. Verify tracked, untracked, intermittent,
fragmented schedule, mixed tracking-method, entitlement persistence, Programs
tab accommodation, and NY DBL reverse-cap cases.

Run ruff and the NY PFL/DBL pytest suites. If collection fails because the local
WeasyPrint native dependency is absent, use the supported repository container
or install the documented dependency, then rerun; do not claim completion from
static checks alone. Finish with the exact files changed, tests run/results,
remaining risks, and whether the staged work is ready to merge.
```
