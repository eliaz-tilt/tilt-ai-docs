# PIE-121: Format Dates as Human-Readable and Remove Python Object Representations — Work Plan

**Status:** In progress on branch `pie-121-humanize-span-messages` (~70% complete)  
**Ticket:** [PIE-121](https://ourtilt.atlassian.net/browse/PIE-121) (#11928)  
**Before/after reference:** `ai-docs/plan/pie-121-message-before-after.csv`  
**Related (separate scope — do not conflate):**
- **PIE-120** (#11928 follow-on): Humanize `"Missing …"` messages — depends on PIE-121 merging first
- **PIE-504** (#11927): Fix incorrect spans summary / max-duration narration bugs (partially addressed here)

**Merge constraint:** Ship backend + frontend detection updates in one PR. Admin PDP empty-span tooltips and Leave Management "Not Applied" copy depend on new span headline patterns.

**Estimated remaining effort:** ~2–3 days (gap-fill + describe() leak + tests + legacy FMLA).

---

## Executive summary

**Current state (verified 2026-09-11): MOSTLY DONE on `pie-121-humanize-span-messages`.**

The framework layer is in place:

| Layer | Status | Location |
|-------|--------|----------|
| Shared formatting helpers | ✅ Done | `backend/benefits/rules/reasoning_format.py` (~2,250 lines) |
| Date primitive | ✅ Done | `checks/messages.py:format_leave_date` → `"F j, Y"` via Django `date_format` |
| Span output choke point | ✅ Done | `__init__.py:spans()` → `format_span_output_message` |
| Expression result formatting | ✅ Done | `__call_compute` → `format_expression_result` for non-bool results |
| Max-duration / schedule / denial copy | ✅ Done | `filter_schedule_days_to_spans`, denial helpers, `get_result_for` messages |
| Sentinel date suppression | ✅ Done | `should_suppress_reason`, `format_minimum/maximum_effective_*` |
| Frontend empty-span filter | ✅ Done | `format-empty-span-summary.ts` recognizes new headline prefixes |

**Remaining gaps (must fix before merge):**

| Issue | Sites | Priority |
|-------|-------|----------|
| **A** ISO dates in paycalc quarter labels | `california/base.py:51,56,68` | High — user-facing `paycalc` category |
| **A/B** ISO dates in hours-worked reasoning | `checks/employee.py:621,626` | High — `eligible` category |
| **D** `describe()` leaks into final spans summary | 10 rule files + framework fix | High — causes `"FMLA eligible date = …"` instead of `"Approved leave period: …"` |
| **E** Hardcoded entitlement strings | `fmla.py`, `hawaii/fll_tracking.py`, `new_york/combined_cap.py`, `colorado/fca.py`, `colorado/famli.py`, `delaware/pfml.py` | Medium |
| **A** ISO dates in drain-down summary | `services/rules.py:1487-1489` | Medium — paycalc item reasoning |
| **B** ISO dates in legacy FMLA eligibility | `legacy/fmla.py:624,629` | Medium — separate pipeline from benefit rules |
| **C** Paycalc operator arithmetic strings | `__init__.py:829-990` | Low — developer-style; `paycalc` category is user-facing but messages are numeric not `Decimal(...)` |
| Tests asserting old formats | ~10–15 files | Required before merge |

**Out of scope (confirmed):**

- PIE-120 `"Missing …"` copy — do not change `require()` format strings in this PR
- `paycalc_item_template_overrides` / `approval_document_config` categories — already `INTERNAL_ONLY_CATEGORIES` in `results.py`
- DB backfill of persisted reasoning — forward-only; old rows remain until re-evaluated
- `leaves/services/checks/` — `WorkflowRequirement` pipeline, not benefit rules

---

## Handoff prompt (copy for a fresh AI session)

```
Implement PIE-121: Format Dates as Human-Readable and Remove Python Object Representations.

Read first:
1. ai-docs/plan/pie-121-humanize-span-messages.md (this plan — full context)
2. ai-docs/plan/pie-121-message-before-after.csv (before/after examples)
3. .ai/rules/backend/backend-quality-standards.mdc
4. .ai/rules/testing/testing-standards.mdc

Branch: pie-121-humanize-span-messages (continue existing work; rebase onto latest main)

Do NOT touch:
- PIE-120 "Missing …" message format in require() / __call_compute (line ~634)
- INTERNAL_MESSAGE_PATTERNS entries unless adding a new internal-only pattern
- checks/company.py _final_reason "Missing definitive FMLA eligibility…"

Implementation order:
Phase 0 (verify) → Phase 2 (describe() leak) → Phase 3 (remaining gaps by type) → Phase 4 (legacy FMLA) → Phase 5 (tests) → Phase 6 (guardrails)

Definition of done: all acceptance criteria checklist passes; pytest backend/benefits/ green; frontend tests green.

Key files already done — reuse, do not recreate:
- backend/benefits/rules/reasoning_format.py
- backend/benefits/rules/checks/messages.py:format_leave_date
```

---

## Background

### What users see today (remaining bad patterns)

| Issue | Current | Target |
|-------|---------|--------|
| A: ISO dates | `sum wages for quarter 2022-01-01 = 5906.23` | `Total wages for Q1 2022 = $5,906.23` (or similar) |
| A: ISO dates | `…returning to work on 2024-08-19` | `…returning to work on August 19, 2024` |
| B: date repr | `hired 1997-12-15, a year or more past` | `hired on December 15, 1997 (more than one year ago)` |
| D: describe leak | `FMLA eligible date = October 10, 2023` (final spans line) | `Approved leave period: October 10, 2023 to December 4, 2023.` |
| E: duration | `12/26 weeks of leave time allowed.` | `12 weeks of leave time are allowed.` / `26 weeks of leave time are allowed.` |
| E: timedelta noise | `Maximum duration 105 days, 0:00:00` | `Maximum leave duration: 105 days.` (already fixed in framework; verify no stragglers) |

### Where messages surface

| Surface | Category | Notes |
|---------|----------|-------|
| Admin PDP yellow tooltip | `spans` | `format-empty-span-summary.ts` filters `Approved leave period:` headlines |
| Leave Management "Not Applied" | `spans` (fallback) | Same filter patterns |
| Benefit reasoning API | All non-internal categories | `get_user_facing_reasoning()` in `results.py` |
| HR sidebar ineligibility | `eligible` | Tenure/hours messages |
| Paycalc breakdown | `paycalc` | Quarter wage sums — **user-facing**, not internal |

### Architecture (already built)

```
format_leave_date(date)          # checks/messages.py — canonical date primitive
        ↓
reasoning_format.py              # format_span_*, format_duration, format_expression_result, …
        ↓
BaseRule.__call_compute()        # non-bool → format_expression_result
BaseRule.spans()                 # final → format_span_output_message
BaseRule.reason()                # manual copy in calculate_spans / state rules
        ↓
get_user_facing_reasoning()      # filters INTERNAL_ONLY_CATEGORIES + INTERNAL_MESSAGE_PATTERNS
```

**Naming rule** (from `reasoning_format.py` module docstring): prefer shared `format_*` helpers at call sites. Add state-prefixed names only when message text is genuinely program-specific. Do not add pass-through aliases.

---

## Phase 0 — Verify branch state

1. Confirm on `pie-121-humanize-span-messages`; rebase onto latest `main`.
2. Run `pytest backend/benefits/rules/tests/test_reasoning_format.py` — should pass.
3. Run full `pytest backend/benefits/` — expect failures only in files listed in Phase 5.
4. Skim `git log --oneline main..HEAD` — framework commits through `7a2ea5462a` are the baseline.

---

## Phase 1 — Framework (DONE — do not redo)

Already merged on this branch:

- `reasoning_format.py` with span, date, duration, schedule, denial, dependency, parental, med-cert, and state-program helpers
- `__init__.py` wiring: `format_expression_result`, `format_span_output_message`, effective-date helpers, max-duration helpers, `should_suppress_reason`
- `company_policy.py`, `wages.py`, most state rule files converted to `format_*` helpers
- `frontend/client/utils/benefit-span-reasoning/format-empty-span-summary.ts` updated for new headline prefixes

**Do not** create `backend/benefits/utils/formatting.py` — the ticket's suggested path was superseded by `reasoning_format.py` + `checks/messages.py:format_leave_date`.

---

## Phase 2 — Fix `describe()` leak into spans summary (Issue D)

### Problem

`BaseRule.describe()` mutates `self.__description` on the rule instance. When `span_date_requirement` methods call `self.describe("FMLA eligible date")` during `calculate_spans()`, the final `spans()` output uses the leaked label:

```
FMLA eligible date = October 10, 2023 to December 4, 2023
```

instead of:

```
Approved leave period: October 10, 2023 to December 4, 2023.
```

Documented in `test_span_budget_multi_block.py:138-168`. Eight shipped rules affected: FMLA, DC FMLA, NJ FLA, WI FMLA (×2), WA PFML, CO FCA, DE PFML job protection.

### Fix (framework — preferred)

In `BaseRule.spans()` (`__init__.py` ~2249):

```python
spans_summary_label = self.description  # save BEFORE calculate_spans mutates it
# ... calculate_spans ...
self._final_reason(
    format_span_output_message(
        spans_summary_label,  # use saved label, not self.description
        spans,
        contains_unknown=self._contains_unknown_span(spans),
    )
)
```

**Wait** — the leak happens because `describe()` is called *during* `calculate_spans`, which runs *after* the label is saved. The save must happen at the **start** of `spans()`, before any `calculate_spans` call, and the saved value must be the expression name (`"spans"`), not whatever `describe()` sets later.

Correct approach:

```python
def spans(self, leave: Leave) -> Sequence[Span]:
    spans_summary_label = "spans"  # fixed label; ignore describe() mutations on this instance
    ...
```

OR save `self.__description` at method entry and restore after `calculate_spans` returns.

### Rule files with `describe()` in date-requirement methods (verify still emit correct intermediate reasoning)

These `describe()` calls are **correct** for intermediate `format_expression_result` lines (e.g. `CFRA eligible date = January 1, 2024`). Only the **final** spans summary line must not use the leaked label.

| File | Line | describe() text |
|------|------|-----------------|
| `fmla.py` | 149 | `FMLA eligible date` |
| `dc/fmla.py` | 126 | `DC FMLA eligible date` |
| `new_jersey/fla.py` | 478 | `NJ FLA eligible date` |
| `wisconsin/fmla.py` | 301, 654 | `WI FMLA eligible date`, `WI FMLA Bonding dependent start date` |
| `washington/pfml.py` | 1559, 1861 | WA PFML date labels |
| `colorado/fca.py` | 240 | `CO FCA eligible date` |
| `delaware/pfml.py` | 493 | `Delaware PFML job protection eligible date` |
| `california/cfra.py` | 92 | `CFRA eligible date` |
| `vermont/pfla.py` | 378 | `VT PFLA eligible date` |
| `oregon/fla.py` | 98 | `FLA dependent start date` |

### Tests

- Update `test_span_budget_multi_block.py:168` — expect `Approved leave period:` (or `Continuous leave period:`), not `startswith("spans = ")`.
- Update `test_span_budget_multi_block.py:131-134` — expect `exceeds the maximum allowed duration`, not `startswith("Max Duration exceeded")`.

---

## Phase 3 — Remaining gap fixes by issue type

### Issue A — ISO dates in paycalc quarter labels

**File:** `backend/benefits/rules/california/base.py`

Add to `reasoning_format.py`:

```python
def format_quarter_label(qstart: date) -> str:
    """Format a calendar quarter start date for paycalc reasoning."""
    return str(_("Q%(quarter)s %(year)s") % {
        "quarter": (qstart.month - 1) // 3 + 1,
        "year": qstart.year,
    })
```

Update lines 51, 56, 68:

```python
# Before
rule.describe(f"sum wages for quarter {qstart}")
# After
rule.describe(format_quarter_wages_description(qstart))  # e.g. "Total wages for Q1 2022"
```

Also update `require()` description on line 56 for PIE-120 compatibility later.

**Tests:** `california/tests/test_base.py` — 16 assertion lines with `2021-10-01` etc.

### Issue A/B — Hours-worked reasoning dates

**File:** `backend/benefits/rules/checks/employee.py:620-627`

Add helpers to `checks/messages.py` (tenure-adjacent copy belongs here, not `reasoning_format.py`):

```python
def hours_not_reached_before_return_message(hours: int, return_date: date) -> str:
    return str(_(
        "The employee does not reach %(hours)s hours before returning to work on %(date)s."
    ) % {"hours": hours, "date": format_leave_date(return_date)})

def hours_reached_on_date_message(hours: int, eligible_date: date) -> str:
    return str(_(
        "The employee has worked at least %(hours)s hours on %(date)s."
    ) % {"hours": hours, "date": format_leave_date(eligible_date)})
```

**Tests:** `checks/tests/test_employee.py:687,704`

### Issue A — Drain-down ISO dates

**File:** `backend/benefits/services/rules.py:1487-1489`

```python
# Before
f"Drained from {parent_title} ({span.start.isoformat()} – {span.end.isoformat()})"
# After
f"Drained from {parent_title} ({format_leave_date_range(span.start, span.end)})"
```

Import `format_leave_date_range` from `reasoning_format.py`.

### Issue E — Hardcoded entitlement / remaining-balance strings

| File | Lines | Fix |
|------|-------|-----|
| `fmla.py` | 568, 774, 898 | `format_leave_time_allowed_weeks_message(12)` / `(26)` |
| `new_york/dbl.py` | 91 | `format_leave_time_allowed_weeks_message(26)` |
| `new_york/combined_cap.py` | 133 | `format_benefit_exhausted_by_prior_usage_message(benefit_name)` |
| `new_york/combined_cap.py` | 149-158 | `format_remaining_benefit_duration_message` or `format_prior_leave_remaining_message` |
| `hawaii/fll_tracking.py` | 143, 159-187 | `format_leave_time_allowed_weeks_message(4)` + remaining helpers |
| `colorado/fca.py` | 227 | `format_leave_time_allowed_weeks_message(12)` |
| `colorado/famli.py` | 356 | `format_leave_time_allowed_weeks_message(12)` |
| `delaware/pfml.py` | 777-779 | `format_prior_leave_remaining_message` |

### Issue C — Paycalc operator arithmetic (optional / low priority)

**File:** `backend/benefits/rules/__init__.py:829-990`

`str(Decimal)` renders as `5906.23`, not `Decimal('5906.23')`. The ticket's `Decimal('10.00')` example is from `paycalc_item_template_overrides` category which is **already internal-only**.

If time permits, add `format_money(value: Decimal) -> str` using `utils/currency.py` patterns and use in `add`/`multiply`/etc. reasoning. **Not blocking** for acceptance criteria — verify no `Decimal(` substring appears in user-facing categories via grep.

### Issue D — Invalid config messages

**File:** `backend/benefits/rules/__init__.py:1897,1943`

```python
# Before
f"Invalid result for waiting_period_config: {waiting_period_config}"
# After — use format_invalid_spans_message pattern or dedicated helper; these categories are near-internal
```

Check whether these land in user-facing output. `approval_document_config` is `INTERNAL_ONLY_CATEGORIES`. `waiting_period_config` may be user-facing — add `format_invalid_waiting_period_config_message()` if needed.

---

## Phase 4 — Legacy FMLA eligibility_desc (Issue A/B)

**File:** `backend/legacy/fmla.py`

Separate from benefit-rules pipeline but user-visible in leave/plan flows (`leaves/services/checks/leave.py` surfaces `eligibility_desc`).

| Line | Current | Target |
|------|---------|--------|
| 624 | `[hired 1997-12-15, a year or more past]` | `[hired on December 15, 1997 (more than one year ago)]` |
| 629 | `[hired 1997-12-15, which is only N months ago]` | `[hired on December 15, 1997 (only N months ago)]` |

Use `format_leave_date` from `checks/messages.py` (import lazily if needed to avoid cycles).

**Optional adjacent cleanup** (same file, lower priority):
- Line 641-642: `1,250 hours requirement={has_worked_more}` — can expose `None`
- Lines 346, 350: raw `{leave.leave_type}` enum values

---

## Phase 5 — Test updates

### Backend tests to update

| File | What changes |
|------|--------------|
| `california/tests/test_base.py` | 16 paycalc quarter ISO strings → `Q1 2022` style |
| `rules/tests/test_span_budget_multi_block.py` | Spans summary + max-duration assertions |
| `services/tests/test_results.py:134` | Denial string → `format_all_benefit_time_denied_message` copy |
| `checks/tests/test_employee.py` | Hours-worked date assertions |
| `delaware/tests/test_pfml.py` | Any remaining entitlement string assertions |
| `washington/tests/test_pfml.py` | Span reasoning assertions if any old format remains |
| `rules/tests/test_fmla_leave_scenarios.py` | FMLA entitlement strings |

### Frontend tests / mocks (update stale fixtures)

| File | What changes |
|------|--------------|
| `frontend/client/__mocks__/AdminPDP/benefitData.ts` | Replace `datetime.date(...)` reasoning with humanized copy |
| `frontend/client/__mocks__/formattedBenefitsForDisplay.ts` | Same |
| `frontend/client/utils/date-span-processor/date-span-processor.test.ts` | Keep regex fallback tests for **historical** rows; add cases for new format |
| `EligibleBenefitsSection.test.tsx` | Update MA PFML reasoning fixture |

### Verification commands

```bash
# No raw patterns in production reasoning strings
rg 'datetime\.date\(|Decimal\(|<Span |spans = ' backend/benefits/rules --glob '!**/tests/**'
rg '%Y-%m-%d' backend/benefits/rules backend/legacy/fmla.py --glob '!**/tests/**'

# Full suite
pytest backend/benefits/
pnpm test --filter format-empty-span-summary  # or equivalent frontend test command
```

---

## Phase 6 — Guardrails

1. Add `test_no_raw_date_reprs_in_reasoning_helpers` if not already covered — parametrize `format_expression_result` for `date`, `Span`, `timedelta`, `Decimal`.
2. Consider a lightweight lint/grep in CI (optional): fail if `self.reason(f"` contains `{` followed by a date variable without `format_leave_date` wrapper. Defer if noisy.
3. Document in PR description: forward-only humanization; persisted `Result.reasoning` rows unchanged until re-evaluation.

---

## Acceptance criteria checklist

- [ ] No `YYYY-MM-DD` dates in user-facing benefit reasoning (use Month Day, Year)
- [ ] No `datetime.date(...)` representations in reasoning
- [ ] No `Decimal(...)` representations in user-facing reasoning categories
- [ ] No `<Span ...>` or `spans =` representations in reasoning
- [ ] No raw `0:00:00` timedelta formatting in reasoning
- [ ] Sentinel dates (`0001-01-01`, `date.max`) shown as "Not applicable" or omitted
- [ ] Duration units lowercase in user-facing copy (`weeks` not `WEEK`)
- [ ] Shared formatting via `reasoning_format.py` + `format_leave_date` (no duplicate utilities)
- [ ] Final spans summary uses `Approved leave period:` / `Continuous leave period:` — not leaked `describe()` labels
- [ ] `pytest backend/benefits/` green
- [ ] Frontend empty-span and date-span-processor tests green
- [ ] `legacy/fmla.py` hire-date copy humanized

---

## PIE-120 coordination

| Area | PIE-121 (this PR) | PIE-120 | Conflict? |
|------|-------------------|---------|-----------|
| `require()` / `Missing …` | Unchanged | Owns humanization | None |
| `reasoning_format.py` | Owns | Reuse helpers only | Coordinate new shared helpers |
| CA `require(..., quarter {qstart})` | Fix label now | Will become `Missing pay history for Q1 2022` later | Independent — both benefit from quarter formatter |
| `checks/employee.py` | `rule.reason()` ISO dates | `Requirement.desc` rewrites | Different code paths |
| `test_results.py` | Update denial fixture | Will add `is_missing_data_message()` | Low conflict |

**Merge order:** PIE-121 first, then PIE-120 rebases onto it.

---

## Review log

| Round | Reviewer | New findings | Resolution |
|-------|----------|--------------|------------|
| 1 | Explore agent (gap audit) | Initial inventory of A–E gaps, test scope, PIE-120 boundaries | Incorporated into phases 2–5 |
| 2 | Plan self-review | `describe()` save-at-entry insufficient — leak happens during `calculate_spans` | Fixed approach in Phase 2: use fixed `"spans"` label or save/restore around `calculate_spans` |
| 2 | Plan self-review | Do not create `backend/benefits/utils/formatting.py` | Documented in Phase 1 — use existing modules |
| 2 | Plan self-review | Paycalc `Decimal(...)` is internal-only category | Downgraded Issue C priority; noted in acceptance criteria |
| 2 | Plan self-review | Frontend `format-empty-span-summary.ts` already updated | Marked Phase 1 done; Phase 5 covers mocks only |

---

## Files to modify (remaining work summary)

| File | Phase | Change |
|------|-------|--------|
| `backend/benefits/rules/__init__.py` | 2 | Fix spans summary label leak |
| `backend/benefits/rules/reasoning_format.py` | 3 | Add `format_quarter_wages_description` (and optional money formatter) |
| `backend/benefits/rules/california/base.py` | 3 | Quarter label formatting |
| `backend/benefits/rules/checks/messages.py` | 3 | Hours-worked messages |
| `backend/benefits/rules/checks/employee.py` | 3 | Wire hours-worked helpers |
| `backend/benefits/services/rules.py` | 3 | Drain-down date range |
| `backend/benefits/rules/fmla.py` | 3 | Entitlement helpers |
| `backend/benefits/rules/new_york/combined_cap.py` | 3 | Entitlement helpers |
| `backend/benefits/rules/new_york/dbl.py` | 3 | Entitlement helpers |
| `backend/benefits/rules/hawaii/fll_tracking.py` | 3 | Entitlement helpers |
| `backend/benefits/rules/colorado/fca.py` | 3 | Entitlement helpers |
| `backend/benefits/rules/colorado/famli.py` | 3 | Entitlement helpers |
| `backend/benefits/rules/delaware/pfml.py` | 3 | Remaining-balance helper |
| `backend/legacy/fmla.py` | 4 | Hire-date copy |
| ~10 test files | 5 | Assertion updates |
| 3 frontend mock files | 5 | Stale fixture copy |
