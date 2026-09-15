# PIE-121: Human-Readable Benefit Reasoning — Implementation Plan

> **Privacy:** This file lives in `ai-docs/`, which is **gitignored and not
> uploaded to GitHub**. Use it for local agent handoffs only; do not copy into
> `.ai/` or commit it.

**Ticket:** Format Dates as Human-Readable and Remove Python Object
Representations\
**Branch:** `pie-121-humanize-span-messages`\
**PR:** [#11928](https://github.com/ourtilt/tilt-repo/pull/11928)\
**Status (2026-09-15):** ~95% complete on branch; gap-fill commit landed; CI
re-running after main merge.

---

## Executive summary

Most of this ticket is **already implemented** on
`pie-121-humanize-span-messages`. Do **not** create a new
`backend/benefits/utils/formatting.py` — the shared utilities live in
**`backend/benefits/rules/reasoning_format.py`**, with canonical date formatting
delegated to **`backend/benefits/rules/checks/messages.format_leave_date`**
(Django `date_format(value, "F j, Y")` → e.g. "August 19, 2024").

The remaining work is **verification, small gaps, and PR merge readiness** — not
a greenfield rewrite.

---

## Architecture (what exists today)

### Central formatting module

| Helper                                    | Purpose                                                              |
| ----------------------------------------- | -------------------------------------------------------------------- |
| `format_leave_date(date)`                 | Re-exports `checks.messages.format_leave_date`                       |
| `format_effective_date(date)`             | Hides sentinel dates as "Not applicable"                             |
| `format_leave_date_range(start, end)`     | "October 10, 2023 to December 4, 2023"                               |
| `format_span_range(span)`                 | Span-like objects; handles `date.min` unknown spans                  |
| `format_span_list(spans)`                 | Newline-separated ranges                                             |
| `format_span_output_message(desc, spans)` | Final spans reasoning (Approved/Continuous/Intermittent prefixes)    |
| `format_expression_result(desc, result)`  | Non-boolean expression results (dates, spans, timedeltas)            |
| `format_duration(timedelta)`              | "105 days" (no `0:00:00`)                                            |
| `days_to_weeks_phrase(days)`              | "6 weeks" when divisible by 7                                        |
| `is_sentinel_date(date)`                  | `year < 1900`                                                        |
| `should_suppress_reason(message)`         | Filters intermediate messages containing `0001-01-01` / `9999-12-31` |
| 100+ `format_*_message()` helpers         | Program-specific copy in `reasoning_format.py`                       |

### Framework choke points (already wired)

1. **`BaseRule.__call_compute`** (`backend/benefits/rules/__init__.py`
   ~L641–666)\
   Non-boolean expression results automatically go through
   `format_expression_result()`.

2. **`BaseRule.spans()`** (~L2271–2277)\
   Final span output uses `format_span_output_message()` via `_final_reason()`.

3. **`BaseRule.reason()`** (~L723–734)\
   Calls `should_suppress_reason()` to drop sentinel-date noise.

4. **`benefits/services/results.py`**\
   Filters internal categories (`paycalc_item_template_overrides`,
   `approval_document_config`) and internal message patterns from user-facing
   reasoning.

### Legacy FMLA

`backend/legacy/fmla.py` uses `_format_long_date()` (same Django format) in
`_hire_date_eligibility_message()`. Gap-fill commit updated hire-date copy;
tests updated in `backend/legacy/tests/test_fmla.py`.

### Frontend companion work (same PR)

- `frontend/client/utils/date-span-processor/date-span-processor.ts` — prefers
  structured `result.spans` VM data; falls back to legacy regex parsing of
  reasoning text.
- `frontend/client/utils/benefit-span-reasoning/format-empty-span-summary.ts` —
  updated for human-readable span summaries.
- Mocks updated in `__mocks__/AdminPDP/benefitData.ts`,
  `formattedBenefitsForDisplay.ts`.

---

## Issue-by-issue status

| Issue                                   | Ticket ask                          | Actual status                                                                                                                                                |
| --------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **A** ISO dates                         | `strftime("%B %-d, %Y")` everywhere | ✅ Done via Django `date_format("F j, Y")` + `format_leave_date` at call sites                                                                               |
| **B** Raw `datetime.date(...)` in spans | `format_span_list` utility          | ✅ Done via `format_span_output_message`, `format_expression_result`, span helpers                                                                           |
| **C** Raw `Decimal(...)`                | Format or hide                      | ⚠️ Partial — `paycalc_item_template_overrides` filtered as internal; `_format_expression_value` still uses `str()` for Decimal (shows `10.00`, not `$10.00`) |
| **D** Raw `<Span ...>` repr             | Span formatters                     | ✅ Done via `_is_span_like` + `format_span_range`                                                                                                            |
| **E** Raw timedelta `0:00:00`           | `format_duration`                   | ✅ Done; company policy min-time-off uses `format_company_policy_min_time_off_not_met_message`                                                               |
| Sentinels                               | "Not determined" / omit             | ✅ `is_sentinel_date`, `should_suppress_reason`, `format_effective_date`                                                                                     |
| Duration units lowercase                | weeks not WEEK                      | ✅ `format_company_policy_min_time_off_not_met_message`, `days_to_weeks_phrase`                                                                              |
| Shared utility                          | New formatting.py                   | ✅ **`reasoning_format.py`** (do not duplicate)                                                                                                              |

---

## Remaining work (ordered)

### Phase 1 — Verify branch completeness (read-only audit)

Run these greps on `pie-121-humanize-span-messages` and confirm **zero hits in
production reasoning paths** (tests/comments OK):

```bash
# Raw Python reprs in reason() paths (exclude tests)
rg 'datetime\.date\(|Decimal\(|<Span ' backend/benefits/rules --glob '!**/tests/**'

# ISO dates in f-string reason calls (should be none)
rg 'self\.reason\(f["\']' backend/benefits/rules --glob '!**/tests/**'

# Unformatted expression descriptions still embedding dates
rg '\d{4}-\d{2}-\d{2}' backend/benefits/rules --glob '!**/tests/**' --glob '!**/reasoning_format.py'
```

Manual spot-check categories in a real leave evaluation:

- `reasoning.spans`
- `reasoning.eligible` / tenure messages
- `reasoning.max_duration`
- Legacy FMLA `eligibility_desc` via API/serializer

### Phase 2 — Close known gaps

1. **Decimal formatting in `_format_expression_value`** (`reasoning_format.py`
   ~L426–442)\
   Add explicit `Decimal` handling if expression results ever surface to users:
   ```python
   from decimal import Decimal
   if isinstance(value, Decimal):
       return f"${value:.2f}"  # or locale-aware if project has a money helper
   ```
   Low priority while `paycalc_item_template_overrides` stays internal-only.

2. **`should_suppress_reason` vs human-readable sentinels**\
   Suppression keys off ISO strings (`0001-01-01`). After humanization,
   intermediate reasons should not contain ISO dates anyway. Confirm no
   regressions where formatted "Not applicable" messages get dropped
   incorrectly.

3. **Frontend regex fallback** (`date-span-processor.ts`)\
   Legacy regex expects `(YYYY,M,D)` tuples in reasoning text. Human-readable
   copy uses structured `result.spans` first — verify multi-span paycalc
   splitting still works when only reasoning text is available (edge case).
   Tests exist in `date-span-processor.test.ts`; extend if a gap is found.

4. **`Suggested: {reason}` in `__init__.py` L4114**\
   Audit whether suggestion text can contain raw reprs from upstream.

### Phase 3 — Test & CI

Follow `@.ai/rules/testing/testing-standards.mdc`:

```bash
# Backend (from repo root, use project venv/docker as usual)
pytest backend/benefits/rules/tests/test_reasoning_format.py -q
pytest backend/benefits/rules/tests/test_base_classes.py -q -k reasoning
pytest backend/legacy/tests/test_fmla.py -q -k hire

# Frontend
npm test -- --testPathPattern='date-span-processor|format-empty-span-summary|EligibleBenefitsSection'
```

Fix any failing assertions on the branch; re-run full PR checks via
`gh pr checks 11928`.

### Phase 4 — PR merge

- Resolve any CI failures (recent main merges may have introduced conflicts).
- Confirm frontend mock data matches new reasoning shape.
- Request review; merge #11928.

---

## Files reference (ticket vs reality)

| Ticket said                                  | Actually changed / use instead                                         |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| `backend/benefits/utils/formatting.py` (new) | **`backend/benefits/rules/reasoning_format.py`** (exists, 2300+ lines) |
| `backend/benefits/rules/__init__.py`         | ✅ Framework hooks + span/denial/max-duration messages                 |
| `backend/legacy/fmla.py`                     | ✅ `_hire_date_eligibility_message`, `_format_long_date`               |
| `backend/benefits/rules/checks/employee.py`  | ✅ Uses `messages.tenure_before_leave_return` (lowercase units)        |
| State rule files (CA, OR, WA, …)             | ✅ Bulk-updated across ~40 rule files on branch                        |
| `checks/messages.py`                         | ✅ `format_leave_date`, tenure messages, hours-worked dates            |

---

## Conventions for new/edited copy

1. **Never** interpolate raw `date`, `Span`, `timedelta`, or `Decimal` into
   `self.reason()` / `describe()` strings.
2. **Prefer** an existing `format_*_message()` in `reasoning_format.py`; add a
   new one only when copy is genuinely program-specific (see module docstring).
3. **Do not** add pass-through aliases that only rename existing helpers.
4. **Use** `format_expression_result()` only via the framework (or tests
   documenting expected output).
5. **Sentinel dates:** return `None` from
   `format_minimum_effective_date_message` etc. to omit, or "Not applicable" /
   dedicated unknown-span messages.
6. **i18n:** wrap user-facing strings in `_()`; `%` formatting with named
   placeholders.
7. **Tests:** one behavior per test, assert full expected string (see
   `test_reasoning_format.py`).

---

## Acceptance criteria checklist

- [ ] No `YYYY-MM-DD` in user-facing reasoning
- [ ] No `datetime.date(...)` reprs
- [ ] No `Decimal(...)` reprs in visible reasoning
- [ ] No `<Span ...>` reprs
- [ ] No `0:00:00` timedelta noise
- [ ] Sentinel dates show "Not applicable" / omitted / "No leave periods" —
      never January 1, 0001
- [ ] Duration units lowercase in user copy
- [ ] Shared helpers in `reasoning_format.py` (not duplicated)
- [ ] Backend + frontend tests green
- [ ] PR #11928 merged

---

## Out of scope

- Rewriting all eligibility check `desc` strings (separate humanization effort
  may exist).
- Changing non-reasoning logs, admin output, or test assertion comments with ISO
  dates.
- Creating `backend/benefits/utils/formatting.py` (would duplicate
  `reasoning_format.py`).

---

## Agent handoff prompt

Copy everything below into a **new Cursor session** to continue this work:

```
Also read AGENTS.local.md if present.

Implement/verify PIE-121 (human-readable benefit reasoning) following the plan at:
  ai-docs/pie-121-human-readable-reasoning-plan.md
(that directory is gitignored — local only, not on GitHub)

Context:
- Branch: pie-121-humanize-span-messages
- PR: #11928 (mostly complete; verify + merge)
- Shared formatters: backend/benefits/rules/reasoning_format.py
- Date format: checks/messages.format_leave_date → Django "F j, Y"
- Do NOT create backend/benefits/utils/formatting.py

Your tasks:
1. Check out pie-121-humanize-span-messages and read the plan.
2. Run the Phase 1 audit greps; fix any remaining raw reprs/ISO dates in reasoning paths.
3. Close Phase 2 gaps if found (Decimal in _format_expression_value, frontend regex edge cases).
4. Run Phase 3 tests; fix failures.
5. Confirm gh pr checks 11928 pass; summarize remaining blockers for merge.

Follow @.ai/README.md, @.ai/rules/backend/backend-quality-standards.mdc, and @.ai/rules/testing/testing-standards.mdc.
Do not commit unless I ask.
```

---

## Revision history

| Date       | Author       | Notes                         |
| ---------- | ------------ | ----------------------------- |
| 2026-09-15 | Cursor agent | Initial plan; branch/PR audit |
