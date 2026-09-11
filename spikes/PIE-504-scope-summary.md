# PIE-504: Fix incorrect spans reasoning (correctness half)

**Jira:** [PIE-504](https://ourtilt.atlassian.net/browse/PIE-504)\
**Status (2026-09-08):** In Progress — **not implemented on `main`**\
**Related:** [PIE-121](https://ourtilt.atlassian.net/browse/PIE-121) (prose
rewrites for the same strings; implementing PIE-121 alone would ship false
statements in better English)

---

## Mission status: NOT DONE — proceed with implementation

Verified on current `main`:

| Signal                                      | Finding                                                                                                                                         |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `filter_schedule_days_to_spans` else-branch | Still emits `Max Duration exceeded` when `max_duration <= total_span_days`, including **equality** (`backend/benefits/rules/__init__.py` ~3661) |
| `spans()` summary label                     | Still uses `self.description` after `@span_date_requirement` methods mutate it (`__init__.py` ~2225)                                            |
| Reference tests                             | `test_span_budget_multi_block.py` **not on main**; exists only on reference commit `657f61cbd7`                                                 |
| Git history                                 | No commits or branches referencing PIE-504                                                                                                      |
| Jira resolution                             | `null` (open)                                                                                                                                   |

The screenshot in the ticket (WI FMLA bonding tooltip showing mislabelled
`WI FMLA eligible date = [<Span …>]` plus a false `Max Duration exceeded` line)
matches current code behavior. (Duplicate summary lines in the screenshot are
pre–PIE-118; `main` shows one mislabelled line.)

---

## What we're fixing (improvement framing)

This is a **reasoning correctness** improvement, not a span-calculation change.
Benefits that work correctly today tell reviewers they do not — the entire body
of the plan-page tooltip **"Unable to calculate spans for this benefit"** comes
from `reasoning['spans']`.

**Hard constraint:** No emitted span changes. Existing span tests must stay
green.

---

## Bug 1: "Max Duration exceeded" on an exact budget fit

### Symptom

`filter_schedule_days_to_spans` branches on `max_duration > total_span_days`. A
block that consumes the remaining budget **exactly**
(`max_duration == total_span_days`) falls into the `else`, logs
`Max Duration exceeded by leave span <start> to <end>`, then covers the block in
full. The span is correct; the sentence is wrong.

### Why this is the normal case for tracked benefits

On the whole-leave-schedule budget bypass in `calculate_spans` (~3324–3337),
`get_tracked_max_duration` returns the sum of block lengths. The final block
almost always hits equality unless min-start / max-end clamps shortened the
schedule first. PIE-121 counted **22,342** occurrences of this string in
production reasoning.

### Reproduce (minimal)

1. Benefit with `max_duration` = 6 weeks (42 days).
2. Single `LEAVE_REGULAR` block of exactly 42 days.
3. Evaluate spans → emitted span covers all 42 days, but reasoning contains
   `Max Duration exceeded…`.

### Code location

```3647:3675:backend/benefits/rules/__init__.py
if max_duration > total_span_days:
    self.reason(
        "Remaining max duration exceeds leave span length, subtracting "
        ...
    )
    max_duration -= total_span_days
    spans.append(Span(start=schedule_start, end=schedule_end))
else:
    self.reason(
        f"Max Duration exceeded by leave span {schedule_start.isoformat()} "
        f"to {schedule_end.isoformat()}."
    )
    if max_duration.days > 0:
        spans.append(
            Span(
                start=schedule_start,
                end=schedule_start + max_duration - timedelta(days=1),
            )
        )
    break
```

### Hazard (do NOT do a `>` → `>=` swap)

Changing the comparison sends the exact-fit block down the `if` branch, which
**decrements** `max_duration` to zero and **continues** the loop (the `else`
branch **breaks**). A later block can then emit a spurious
`"Max Duration exceeded"` line even when spans are already fully budgeted.
**Keep branch structure; condition the message only.**

### Proposed fix

Inside the existing `else` branch, branch on equality for messaging only:

```python
else:
    if max_duration == total_span_days:
        self.reason(
            "Leave span consumes remaining max duration exactly, "
            f"covering {schedule_start.isoformat()} to {schedule_end.isoformat()}."
        )
    else:
        self.reason(
            f"Max Duration exceeded by leave span {schedule_start.isoformat()} "
            f"to {schedule_end.isoformat()}."
        )
    if max_duration.days > 0:
        spans.append(...)  # unchanged
    break
```

**Prose note:** Coordinate wording with PIE-121 if that ticket lands first —
PIE-504 owns _truth_, PIE-121 owns _tone_. The equality message must not imply
failure.

### Frontend touchpoint

`frontend/client/utils/benefit-span-reasoning/format-empty-span-summary.ts`
(~179) treats any line containing `Max Duration exceeded` plus
`Maximum duration 0` as headline **"No benefit time remaining"**. Exact-fit fix
removes false positives from that path; no frontend change required unless we
want a positive headline for exact-fit (out of scope).

---

## Bug 2: Spans summary line mislabelled by nested `describe()`

### Symptom

The final `reasoning['spans']` summary reads like
`FMLA eligible date = [<Span (…)>, …]` instead of `spans = [<Span (…)>, …]`.

### Root cause

1. `spans()` ends with `self._final_reason(f"{self.description} = {spans}")`
   (~2225).
2. `calculate_spans` → `get_min_start_date` → `_consolidate_start_dates` invokes
   `@span_date_requirement` methods **on the same rule instance** evaluating
   `spans`.
3. Those methods call `self.describe("… eligible date")`, overwriting
   `__description` (set to `"spans"` from the method name at instance creation).
4. `_final_reason` records the summary with the leaked label.

### Post–PIE-118 note on duplicate lines

PIE-118 introduced `_final_reason`, which sets `__final_reason = True` and
**suppresses** the automatic `f"{self.__description} = {result}"` append in
`__call_compute` (~599–622). The ticket screenshot’s **two** identical
mislabelled lines reflect pre–PIE-118 behavior. On current `main`, expect
**one** mislabelled summary from `_final_reason` only.

**Exception:** `NewJerseyFLA.spans()` calls `super().spans(leave)` **twice** on
the intermittent path (`new_jersey/fla.py` ~321–334), so two mislabelled summary
lines can still appear for that rule. The label-capture fix applies to both
calls.

**Frontend:** `format-empty-span-summary.ts` filters lines matching
`/^spans = \[/` from tooltip details. After Bug 2, the summary line matches that
pattern again and is hidden from the detail list as intended.

### Typical FMLA `reasoning['spans']` tail (mental trace)

1. Tracking / budget setup (`get_tracked_max_duration`, template tracking
   method, …)
2. `get_min_start_date()` → `_consolidate_start_dates()` →
   `get_tenure_min_start_date` calls `describe("FMLA eligible date")`
   (`fmla.py:138`)
3. `"Minimum effective date …"`, `"Maximum effective start date …"`,
   `"Maximum effective end date …"`
4. `filter_schedule_days_to_spans` — on exact budget fit, false
   `"Max Duration exceeded …"`
5. **Last line:** `FMLA eligible date = [<Span …>]` (should be `spans = …`)

### Fifteen `@span_date_requirement` + `describe()` leak sites (symptom table for one bug)

All `self.describe(` inside `@span_date_requirement` methods (ticket listed 11;
four more exist on `main`):

| File                        | Leaked label                               |
| --------------------------- | ------------------------------------------ |
| `california/cfra.py:92`     | CFRA eligible date                         |
| `california/pfl.py:60`      | PFL minimum start date                     |
| `colorado/fca.py:236`       | CO FCA eligible date                       |
| `dc/fmla.py:118`            | DC FMLA eligible date                      |
| `dc/fmla.py:271`            | DC FMLA Family dependent start date        |
| `delaware/pfml.py:484`      | Delaware PFML job protection eligible date |
| `fmla.py:138`               | FMLA eligible date                         |
| `new_jersey/fla.py:478`     | NJ FLA eligible date                       |
| `oregon/fla.py:91`          | FLA dependent start date                   |
| `vermont/pfla.py:374`       | VT PFLA eligible date                      |
| `massachusetts/pfml.py:890` | MA PFML family bank dependent start date   |
| `washington/pfml.py:1533`   | WA PFML family bank dependent start date   |
| `washington/pfml.py:1835`   | Washington PFML eligible date              |
| `wisconsin/fmla.py:283`     | WI FMLA eligible date                      |
| `wisconsin/fmla.py:632`     | WI FMLA Bonding dependent start date       |

**Also fixed by label capture (not `@span_date_requirement`):**
`company_policy.py:158, 172` — `describe()` during `calculate_spans` can leak
labels like `Spans for continuous leaves (with a single time off span)`.

**Do not reword these strings for PIE-504** — fixing the summary label fixes all
of them at once. PIE-121 section 7B lists five as separate prose items; they are
one root cause.

### Proposed fix (recommended: capture label at entry)

In `BaseBenefitRule.spans()` (~2187), capture the expression label **before**
`calculate_spans` can mutate it:

```python
def spans(self, leave: Leave) -> Sequence[Span]:
    spans_summary_label = self.description  # "spans" unless rule overrides method name
    leave_schedule, work_schedule = self.get_leave_and_work_schedule_days(leave)
    ...
    spans = self.calculate_spans(...)
    self._final_reason(f"{spans_summary_label} = {spans}")
    return spans
```

**Why not only change `_final_reason` in `__call_compute`?** That path runs for
every expression in the engine — high blast radius. **Why not remove
`describe()` from the leak sites?** Those descriptions are correct for when
those methods are evaluated as standalone expressions; the bug is shared
instance state during `spans()`.

**Overrides:** Rules that override `spans()` and call `super().spans(leave)`
inherit the fix.

**Out of scope — `wages.py:50`:** Uses
`self.reason(f"{self.description} = {spans}")` instead of `_final_reason`. Wages
`calculate_spans` does not call `get_min_start_date` or `describe()`, so labels
stay `"spans"`, but `__call_compute` may still auto-append a second `spans = …`
(duplicate correct label, not mislabelled). Separate from PIE-504.

---

## Acceptance criteria checklist

| Criterion                                                            | How to verify                                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| No "Max Duration exceeded" when block consumes budget exactly        | `test_exact_fit_block_is_not_narrated_as_exceeding_the_budget` passes (xfail removed)  |
| Spans summary labelled `spans = …` regardless of nested `describe()` | `test_span_summary_line_is_labelled_spans` passes; FMLA integration spot-check         |
| No emitted span changes                                              | Span assertions in new tests + full `backend/benefits/rules/tests/` span-related suite |
| Existing span tests still pass                                       | CI / local pytest for rules tests                                                      |

---

## Test plan (bring reference tests onto branch)

Reference **test scaffolding** lives at commit **`657f61cbd7`** (not merged;
tests only, no production fixes). Cherry-pick or copy:

### 1. New file: `backend/benefits/rules/tests/test_span_budget_multi_block.py`

Three tests:

| Test                                                           | Purpose                                                                                                       |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `test_multi_block_leave_respects_span_budget`                  | Guard: multi-block trim still correct (passes today)                                                          |
| `test_exact_fit_block_is_not_narrated_as_exceeding_the_budget` | **xfail → pass** after Bug 1 fix                                                                              |
| `test_span_summary_line_is_labelled_spans`                     | **xfail → pass** after Bug 2 fix; uses minimal `RelabellingRule` with `@span_date_requirement` + `describe()` |

### 2. Extend `backend/benefits/rules/tests/test_fmla_leave_scenarios.py`

Add `TestFMLAWorkWeekSchedules.test_split_schedule_over_utilized_time` from
reference commit — tracked-path guard that emitted spans stay at 12 weeks when
schedule is split across two blocks. Documents that Bug 1 is narration-only on
the over-long path.

### 3. Update existing assertion if needed

`test_default_spans_zero_max_duration` (`test_base_classes.py` ~L1008) expects
`Max Duration exceeded` for `max_duration = 0` with a 5-week block — that is a
**true** over-budget case (0 < block length); **keep** that expectation. This is
the only test in the repo that asserts that string.

### Run commands

```bash
# Focused
pytest backend/benefits/rules/tests/test_span_budget_multi_block.py -v
pytest backend/benefits/rules/tests/test_fmla_leave_scenarios.py::TestFMLAWorkWeekSchedules::test_split_schedule_over_utilized_time -v

# Regression
pytest backend/benefits/rules/tests/test_base_classes.py -k "max_duration" -v
pytest backend/benefits/rules/tests/test_fmla.py -v
pytest backend/benefits/rules/tests/ -k "span" -v
```

Expected after fix: **4 passed, 0 xfailed** in the new/focused tests
(`test_span_budget_multi_block.py` + FMLA split-schedule test). Full regression
per run commands below must stay green. (Ticket note of “12 passed, 2 xfailed”
refers to a broader local run at reference commit, not just the new file.)

---

## Implementation sequence (single PR, ~2 files production + tests)

### Step 1 — Tests first (TDD)

1. Add `test_span_budget_multi_block.py` from `657f61cbd7` with xfails intact.
2. Add FMLA split-schedule test from reference commit.
3. Confirm: new tests show 2 xfailed, others green.

### Step 2 — Bug 1 (`__init__.py` ~3661)

Condition message in `else` branch; no comparison-operator change.

### Step 3 — Bug 2 (`__init__.py` ~2187)

Capture `spans_summary_label` at top of `spans()`; use in `_final_reason`.

### Step 4 — Remove xfails; run suites

### Step 5 — Manual QA

Reproduce WI FMLA bonding scenario from ticket screenshot:

- Tooltip should **not** claim max duration exceeded on exact-fit final block.
- Last `reasoning['spans']` line should be `spans = [<Span …>]`, not
  `WI FMLA eligible date = …`.

---

## Files to touch

| File                                                           | Change                                               |
| -------------------------------------------------------------- | ---------------------------------------------------- |
| `backend/benefits/rules/__init__.py`                           | Bug 1 message + Bug 2 label capture (~2 small edits) |
| `backend/benefits/rules/tests/test_span_budget_multi_block.py` | **Add** (from reference commit)                      |
| `backend/benefits/rules/tests/test_fmla_leave_scenarios.py`    | **Add** tracked-path guard test                      |

**Out of scope:** the fifteen `@span_date_requirement` `describe()` call sites,
`__call_compute` refactor, PIE-121 prose pass, frontend tooltip copy (unless new
strings need mock updates — unlikely).

---

## Decisions already made (don't re-litigate in implementation)

1. **Single PR** for both bugs — shared file, low risk, shared test file.
2. **Message-only fix** for Bug 1 — no branch restructuring.
3. **Label capture** for Bug 2 — not `__call_compute` change.
4. **No span logic changes** — if a test fails on span output, the test or
   understanding is wrong, not the fix.

## Open questions (optional follow-ups)

1. Should equality narration mirror the subtract wording
   (`"Remaining max duration… subtracting N days"`) for consistency? Current
   proposal uses distinct "consumes exactly" wording.
2. Does PIE-121 need a dependency note to skip rewording the fifteen labels and
   the exceeded string until PIE-504 merges?
3. Should `wages.py` adopt `_final_reason` to eliminate duplicate `spans = …`
   lines (separate ticket)?
4. Should NJ FLA intermittent double-`super().spans()` be deduplicated (separate
   ticket)?

---

## Kickoff prompt for next session

```
Implement PIE-504 using the plan in ai-docs/spikes/PIE-504-scope-summary.md.

Read that doc first. Work is NOT done on main.

Order:
1. Copy tests from git commit 657f61cbd7 (test_span_budget_multi_block.py + FMLA split-schedule test); keep xfails until fixes land.
2. Fix filter_schedule_days_to_spans: condition the else-branch message on max_duration == total_span_days (do NOT change > to >=).
3. Fix BaseBenefitRule.spans(): capture spans_summary_label before calculate_spans, use in _final_reason.
4. Remove xfails; run pytest commands in the doc.

Constraints: no emitted span changes; do not edit the describe() leak sites; minimal diff.
```
