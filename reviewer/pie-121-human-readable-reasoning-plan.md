# PIE-121: Human-Readable Benefit Reasoning — Implementation Plan

> **Privacy:** This file lives in `ai-docs/`, which is listed in the repo `.gitignore` (alongside `AGENTS.local.md`) and is **not uploaded to GitHub**. Use it for local agent handoffs only; do not copy into `.ai/` or commit it.

**Ticket:** Format Dates as Human-Readable and Remove Python Object Representations  
**Branch:** `pie-121-humanize-span-messages`  
**PR:** [#11928](https://github.com/ourtilt/tilt-repo/pull/11928)  
**Status (2026-09-15):** Framework and most rule copy done on branch; **Maine PFML** still leaks ISO dates; verify CI + merge.

> **Important:** `main` does **not** include this work. Always `git checkout pie-121-humanize-span-messages` before auditing or editing.

---

## Executive summary

Most of PIE-121 is **already implemented** on `pie-121-humanize-span-messages`. Do **not** create `backend/benefits/utils/formatting.py` — shared utilities live in **`backend/benefits/rules/reasoning_format.py`**, with canonical date formatting in **`backend/benefits/rules/checks/messages.format_leave_date`** (Django `date_format(value, "F j, Y")` → e.g. "August 19, 2024").

Remaining work is **small gap fixes + verification + PR merge** — not a greenfield rewrite.

| Area | Feature branch status |
|------|----------------------|
| `reasoning_format.py` + framework hooks | ✅ Done |
| `__init__.py` span calculation / schedule-block reasoning | ✅ Done (zero `.isoformat()` on branch) |
| State rule files (~40 modules) | ✅ Done |
| Legacy FMLA `eligibility_desc` | ✅ Done (`_format_long_date`) |
| Frontend structured spans + mocks | ✅ Done |
| **Maine PFML** parental min/max start reasoning | ❌ **3 ISO date leaks** |
| Paycalc operator arithmetic reasoning | ⚠️ Uses raw `str(Decimal)` (mostly internal) |
| PR CI / merge | 🔄 In progress |

---

## Architecture (what exists on the branch)

### Central formatting module

| Helper | Purpose |
|--------|---------|
| `format_leave_date(date)` | Re-exports `checks.messages.format_leave_date` |
| `format_effective_date(date)` | Sentinel dates → **"Not applicable"** |
| `format_leave_date_range(start, end)` | "October 10, 2023 to December 4, 2023" |
| `format_span_range(span)` | Span-like objects; `date.min` → unknown-span message |
| `format_span_list(spans)` | Newline-separated ranges |
| `format_span_output_message(desc, spans)` | Final spans reasoning (Approved/Continuous/Intermittent prefixes) |
| `format_expression_result(desc, result)` | Non-boolean expression results |
| `format_duration(timedelta)` | "105 days" (no `0:00:00`) |
| `days_to_weeks_phrase(days)` | "6 weeks" when divisible by 7 |
| `is_sentinel_date(date)` | `year < 1900` |
| `should_suppress_reason(message)` | Drops messages containing `0001-01-01` / `9999-12-31` |
| 100+ `format_*_message()` helpers | Program-specific copy |

### Framework choke points (wired on branch)

1. **`BaseRule.__call_compute`** (~L664–665) — non-boolean results → `format_expression_result()`
2. **`BaseRule.spans()`** (~L2271–2277) — final output → `format_span_output_message()` via `_final_reason()`
3. **`BaseRule.reason()`** (~L731–733) — `should_suppress_reason()` filter
4. **`ResultSerializer.get_reasoning()`** → `get_user_facing_reasoning()` in `benefits/services/results.py` — API boundary; filters internal categories and debug patterns
5. **`calculate_spans()` schedule-block paths** in `__init__.py` — use `format_schedule_block_*`, `format_max_duration_*`, `format_no_overlap_*` helpers (not `.isoformat()`)

### Legacy FMLA

`backend/legacy/fmla.py` uses `_format_long_date()` for `eligibility_desc`. API `to_dict()` still uses `.isoformat()` for machine-readable JSON fields — **out of scope** unless product asks to change API date shape.

### Frontend (same PR)

- `date-span-processor.ts` — prefers structured `result.spans`; regex fallback only parses legacy `datetime.date(YYYY,M,D)` tuples
- `format-empty-span-summary.ts` — parses dates in parentheses; update tests if overlap-message format changes
- Mocks: `__mocks__/AdminPDP/benefitData.ts`, `formattedBenefitsForDisplay.ts`

---

## Issue-by-issue status (feature branch)

| Issue | Ticket ask | Branch status |
|-------|-----------|---------------|
| **A** ISO dates | Human-readable everywhere | ⚠️ **Maine PFML** still uses raw `date` in `%` formatting → ISO |
| **B** Raw `datetime.date(...)` spans | Span formatters | ✅ Done |
| **C** Raw `Decimal(...)` | Format or hide | ⚠️ `_format_expression_value` uses `str()`; `paycalc_item_template_overrides` filtered as internal |
| **D** Raw `<Span ...>` | Span formatters | ✅ Done |
| **E** Raw timedelta `0:00:00` | `format_duration` | ✅ Done |
| Sentinels | Hide / "Not applicable" | ✅ `is_sentinel_date`, `should_suppress_reason`, `format_effective_date` |
| Duration units lowercase | weeks not WEEK | ✅ tenure + company policy helpers |
| Shared utility | New formatting.py | ✅ **`reasoning_format.py`** only |

---

## Remaining work (ordered)

### Phase 0 — Checkout

```bash
git fetch origin
git checkout pie-121-humanize-span-messages
git pull --ff-only origin pie-121-humanize-span-messages
```

### Phase 1 — Audit (on feature branch only)

```bash
# Raw reprs in production reasoning (exclude tests)
rg 'datetime\.date\(|Decimal\(|<Span ' backend/benefits/rules --glob '!**/tests/**'

# ISO dates from raw date interpolation in reason() (should be zero after Maine fix)
rg 'self\.reason\(|rule\.reason\(' backend/benefits/rules --glob '!**/tests/**' -l | \
  xargs rg '\%\).*date|isoformat\(\)'

# Confirm __init__.py is clean (should return nothing on branch)
rg '\.isoformat\(\)' backend/benefits/rules/__init__.py

# Maine PFML — known remaining hits at ~L527-553
rg 'self\.reason' backend/benefits/rules/maine/pfml.py -n
```

**Manual spot-check** serialized API reasoning (not raw `result.reasoning`):

- `reasoning.spans`, `reasoning.eligible`, legacy FMLA `eligibility_desc`
- Empty-span UI via `format-empty-span-summary.ts`

### Phase 2 — Fix remaining gaps

#### 2a. Maine PFML (CRITICAL — only confirmed ISO leak on branch)

File: `backend/benefits/rules/maine/pfml.py` (~L527–553)

Replace raw `% {"start_date": start_date}` / `due_date` / `end_date` with existing helpers (same pattern as Colorado FAMLI):

| Current inline copy | Use instead |
|---------------------|-------------|
| Medical pre-birth start on leave date | `format_medical_pre_birth_start_on_leave_date_message(start_date)` |
| Earliest start is due date | `format_earliest_start_is_due_date_message(leave.expected_due_date)` |
| Parental bonding end within one year | `format_parental_bonding_must_end_by_message(end_date)` |

Add/adjust tests in `backend/benefits/rules/maine/tests/` if present.

#### 2b. Decimal in `_format_expression_value` (LOW — optional)

`reasoning_format.py` ~L426–442: add explicit `Decimal` branch if non-internal expression results need currency formatting. Do **not** use bare `$value:.2f` without confirming money conventions. Safe to defer while paycalc overrides stay internal-only per `results.py`.

#### 2c. Paycalc operator reasoning (LOW — optional)

`__init__.py` paycalc `add`/`multiply`/etc. append `"= " + str(Decimal)`. Avoids `Decimal(` repr but not centralized. Route through `_format_expression_value` only if these messages become user-visible.

#### 2d. Frontend regex fallback (document, don't necessarily fix)

If API always provides `result.spans` (serializer includes structured spans), humanized reasoning-only text is fine. Add a test documenting **degraded** behavior when `result.spans` is empty and reasoning is human-readable (multi-span paycalc splitting may not run). Confirm serializer contract in `backend/benefits/serializers.py`.

#### 2e. Refresh stale test fixtures (MEDIUM)

`backend/benefits/services/tests/test_results.py` may still use raw `<Span ...>` fixtures — update to humanized strings or scope tests to filtering behavior only.

### Phase 3 — Tests & CI

Follow `@.ai/rules/testing/testing-standards.mdc`:

```bash
pytest backend/benefits/rules/tests/test_reasoning_format.py -q
pytest backend/benefits/rules/tests/test_base_classes.py -q -k reasoning
pytest backend/benefits/services/tests/test_results.py -q
pytest backend/benefits/tests/test_serializers.py -q -k reasoning
pytest backend/legacy/tests/test_fmla.py -q -k hire

# Frontend (from frontend/client or repo frontend root per project convention)
npm test -- --testPathPattern='date-span-processor|format-empty-span-summary|EligibleBenefitsSection'
```

Optional integration assertion: serialized `reasoning` contains no `\d{4}-\d{2}-\d{2}` pattern.

```bash
gh pr checks 11928
```

### Phase 4 — Merge PR #11928

- Fix Maine PFML + any CI failures
- Confirm frontend mocks match reasoning shape
- Merge when green

---

## Conventions for new/edited copy

1. **Never** interpolate raw `date`, `Span`, `timedelta`, or `Decimal` into `self.reason()` / `describe()` strings.
2. **Prefer** existing `format_*_message()` in `reasoning_format.py`; add new ones only for genuinely program-specific copy (see module docstring — no pass-through aliases).
3. **Sentinel dates:** omit via helpers returning `None`, or use **"Not applicable"** / dedicated unknown-span messages — never January 1, 0001.
4. **i18n:** `_()` + named `%` placeholders.
5. **Tests:** one behavior per test; assert full expected string (`test_reasoning_format.py`).

---

## Acceptance criteria checklist

- [ ] No `YYYY-MM-DD` in user-facing reasoning (API via `get_user_facing_reasoning`)
- [ ] No `datetime.date(...)` reprs
- [ ] No `Decimal(...)` reprs in visible reasoning
- [ ] No `<Span ...>` reprs
- [ ] No `0:00:00` timedelta noise
- [ ] Sentinel dates → "Not applicable" / omitted / "No leave periods" — never year 0001
- [ ] Duration units lowercase in user copy
- [ ] Shared helpers in `reasoning_format.py` (no duplicate module)
- [ ] Maine PFML parental date messages humanized
- [ ] Backend + frontend tests green; PR #11928 merged

---

## Out of scope

- `FMLAReasoning.to_dict()` ISO fields (API JSON contract)
- Non-reasoning logs, admin output, test comment ISO dates
- Creating `backend/benefits/utils/formatting.py`
- Rewriting all eligibility `desc` strings (separate effort)

---

## Agent handoff prompt

Copy into a **new Cursor session**:

```
Also read AGENTS.local.md if present.

Implement/verify PIE-121 following the plan at:
  ai-docs/pie-121-human-readable-reasoning-plan.md
(ai-docs/ is gitignored — local only, not on GitHub)

Start by checking out the feature branch:
  git checkout pie-121-humanize-span-messages

Context:
- PR #11928 — mostly complete; Maine PFML is the main remaining ISO date leak
- Shared formatters: backend/benefits/rules/reasoning_format.py
- Date format: checks/messages.format_leave_date → Django "F j, Y"
- Do NOT create backend/benefits/utils/formatting.py
- main does NOT have this work — always work on pie-121-humanize-span-messages

Tasks:
1. Read the plan in ai-docs/.
2. Fix Maine PFML (~L527-553) using existing format_* helpers from reasoning_format.py.
3. Run Phase 1 audit greps; fix any other raw reprs/ISO dates found.
4. Run Phase 3 tests (including test_results.py, test_serializers.py); fix failures.
5. Confirm gh pr checks 11928 pass; summarize merge blockers.

Follow @.ai/README.md, @.ai/rules/backend/backend-quality-standards.mdc, and @.ai/rules/testing/testing-standards.mdc.
Do not commit unless I ask.
```

---

## Revision history

| Date | Author | Notes |
|------|--------|-------|
| 2026-09-15 | Cursor agent | Initial plan |
| 2026-09-15 | Cursor agent | Subagent review: corrected branch vs main; Maine PFML gap; gitignore; audit greps |
