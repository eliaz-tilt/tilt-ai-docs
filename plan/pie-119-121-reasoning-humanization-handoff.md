# PIE-119 + PIE-121: Benefit Reasoning Humanization — Agent Handoff

> **Privacy:** `ai-docs/` is gitignored and **not on GitHub**. Local agent handoffs only.

| Jira | Title | Scope |
|------|-------|-------|
| [PIE-119](https://ourtilt.atlassian.net/browse/PIE-119) | Format Dates as Human-Readable and Remove Python Object Representations | **Cross-cutting mechanics:** ISO dates, `datetime.date(...)`, `Decimal(...)`, `<Span ...>`, `0:00:00` timedeltas, sentinel dates, lowercase duration units, shared formatters |
| [PIE-121](https://ourtilt.atlassian.net/browse/PIE-121) | Humanize `reasoning.spans` messages | **Copy + UX:** readable span output (7A–7H), law abbreviation expansion, title-case leave types, filter/simplify debug-only intermediate steps, `rule_display_name` instead of `<class '...'>` |

**These are related but distinct tickets.** PIE-121 depends on PIE-119’s formatting primitives. **Both are implemented in one branch/PR** — do not split into a second PR from `main`.

---

## Existing work (do not redo)

| Asset | Location |
|-------|----------|
| **Branch** | `pie-121-humanize-span-messages` |
| **PR** | [#11928](https://github.com/ourtilt/tilt-repo/pull/11928) → `main` |
| **Shared formatters** | `backend/benefits/rules/reasoning_format.py` (~2,300 lines) |
| **Date primitive** | `backend/benefits/rules/checks/messages.format_leave_date` → Django `"F j, Y"` |
| **Framework hooks** | `backend/benefits/rules/__init__.py`: `format_expression_result`, `format_span_output_message`, `should_suppress_reason`, schedule/max-duration/denial helpers |
| **User-facing filter** | `backend/benefits/services/results.py`: `get_user_facing_reasoning()`, `INTERNAL_ONLY_CATEGORIES`, `INTERNAL_MESSAGE_PATTERNS` |
| **Structured spans API** | `Result.spans` migration; frontend prefers structured spans over regex parsing |
| **Frontend** | `date-span-processor.ts`, `format-empty-span-summary.ts`, mocks/tests updated |
| **Scope** | ~79 files, +4,113 / −985 lines vs `main` |

**`main` and `pie-631-fmla-eligibility-cleanup` do NOT contain this work.** Always branch from / checkout `pie-121-humanize-span-messages`.

---

## Ticket mapping: what PR #11928 already covers

### PIE-119 (mechanics) — largely ✅ on branch

| Issue | Status on branch |
|-------|------------------|
| A: ISO `YYYY-MM-DD` | ✅ Framework + most rules; ❌ **Maine PFML** 3 leaks (see below) |
| B: Raw `datetime.date(...)` tuples | ✅ `format_span_output_message`, `format_expression_result` |
| C: Raw `Decimal(...)` | ✅ Filtered via `INTERNAL_ONLY_CATEGORIES` for paycalc overrides; expression path uses readable numeric strings |
| D: Raw `<Span ...>` | ✅ `format_span_range` / `_is_span_like` |
| E: Raw `0:00:00` timedeltas | ✅ `format_duration`, company policy min-time-off helper |
| Sentinels `0001-01-01` | ✅ `is_sentinel_date`, `should_suppress_reason`, omit/`Not applicable` helpers |
| Lowercase duration units | ✅ `tenure_before_leave_return`, `days_to_weeks_phrase` |
| Shared utility | ✅ `reasoning_format.py` (not `benefits/utils/formatting.py`) |

### PIE-121 (spans copy 7A–7H) — largely ✅ on branch

| Subcategory | Status on branch |
|-------------|------------------|
| **7A** Span list output | ✅ `format_span_output_message` — Approved/Continuous/Intermittent prefixes |
| **7B** Law-specific eligible/start/end | ✅ `expand_law_abbreviations`, `format_expression_result` on expression results |
| **7C** Max duration / leave length | ✅ `format_max_duration_*`, `format_remaining_duration_subtract_message`, weeks helpers |
| **7D** Parental/birth messages | ✅ Many `format_*` helpers in `reasoning_format.py`; global disability/bonding wired in `__init__.py` |
| **7E** Schedule/calendar | ✅ `format_schedule_block_*`, denial/document schedule helpers |
| **7F** Tenure/eligibility in spans | ✅ DBL/tenure helpers; sentinel suppression for min effective date noise |
| **7G** Document-related | ✅ `format_document_schedule_adjustment_message`, med-cert copy |
| **7H** Other/misc | ✅ Company policy increments, copying spans, OFLA/PDL messages, `rule_display_name` |
| `<class '...'>` leak | ✅ `rule_display_name()` + dependency message helpers |
| Filter debug intermediates | ✅ `should_suppress_reason` + `results.py` internal patterns |

---

## Remaining work (agent must do)

### 1. CRITICAL — Maine PFML ISO dates

**File:** `backend/benefits/rules/maine/pfml.py` (~L527–553)

Replace raw `date` in `%` formatting with existing helpers:

```python
# Before (leaks 2026-05-01)
% {"start_date": start_date}

# After
from benefits.rules.reasoning_format import (
    format_earliest_start_is_due_date_message,
    format_medical_pre_birth_start_on_leave_date_message,
    format_parental_bonding_must_end_by_message,
)
self.reason(format_medical_pre_birth_start_on_leave_date_message(start_date))
self.reason(format_earliest_start_is_due_date_message(leave.expected_due_date))
self.reason(format_parental_bonding_must_end_by_message(end_date))
```

Add/update tests in `backend/benefits/rules/maine/tests/` if present.

### 2. Verification audit (on feature branch)

```bash
git checkout pie-121-humanize-span-messages
git pull --ff-only origin pie-121-humanize-span-messages

# Should return ZERO hits in production reasoning paths after Maine fix:
rg 'datetime\.date\(|Decimal\(|<Span |<class ' backend/benefits/rules --glob '!**/tests/**'
rg '\.isoformat\(\)' backend/benefits/rules --glob '!**/tests/**'
rg 'self\.reason\(f["\']' backend/benefits/rules --glob '!**/tests/**'
rg '0:00:00' backend/benefits/rules --glob '!**/tests/**'
```

Spot-check serialized API output:

```bash
pytest backend/benefits/rules/tests/test_reasoning_format.py -q
pytest backend/benefits/rules/tests/test_base_classes.py -q -k reasoning
pytest backend/benefits/services/tests/test_results.py -q
pytest backend/benefits/tests/test_serializers.py -q -k reasoning
pytest backend/legacy/tests/test_fmla.py -q -k hire

# Frontend
npm test -- --testPathPattern='date-span-processor|format-empty-span-summary|EligibleBenefitsSection'
```

Optional: assert no `\d{4}-\d{2}-\d{2}` in `get_user_facing_reasoning()` output in an integration test.

### 3. Update PR #11928 description

Use the **PR body template** at the bottom of this doc. Run:

```bash
gh pr edit 11928 --title "PIE-119/121: Humanize benefit reasoning dates and span messages" --body "$(cat <<'EOF'
...template...
EOF
)"
```

Only run `gh pr edit` if the user asks you to update the PR.

### 4. Merge readiness

```bash
gh pr checks 11928
```

Fix any failing checks. Rebase onto `main` if needed:

```bash
git fetch origin main && git merge origin/main
```

---

## PR body template (two tickets)

Copy into PR #11928:

```markdown
# PR Details

**Issue Links:**
- [PIE-119](https://ourtilt.atlassian.net/browse/PIE-119) — Format dates/decimals/timedeltas; remove Python object reprs from benefit reasoning
- [PIE-121](https://ourtilt.atlassian.net/browse/PIE-121) — Rewrite `reasoning.spans` (and related) messages for end-user readability (7A–7H)

**Product copy review (before/after):** `ai-docs/plan/pie-121-message-before-after.csv` (local; not in repo)

**Checklist**
- [ ] Involves feature flags? (Name and behavior with flag ON/OFF)
- [x] Tests for backend/frontend updated/added
- [x] Docstrings created/updated where necessary
- [ ] **Breaking API change?** If yes, increment `backend/API_COMPAT_VERSION`

## Summary

Humanizes benefit rule reasoning so HR admins and leave coordinators see readable dates, durations, and leave-period copy instead of Python reprs (`datetime.date(...)`, `<Span (...)>` dumps, ISO dates, `0:00:00` timedeltas, `<class '...'>` leaks).

This PR delivers **both PIE-119 and PIE-121** in one branch because span copy (121) depends on shared date/duration formatting (119).

## PIE-119 (formatting mechanics)

- Shared formatters in `backend/benefits/rules/reasoning_format.py` + `checks/messages.format_leave_date`
- Framework: `format_expression_result`, sentinel suppression, duration/decimal handling
- Internal-only categories filtered in `benefits/services/results.py`

## PIE-121 (spans copy)

- `format_span_output_message`: Approved / Continuous / Intermittent leave period headlines
- Law abbreviation expansion (CFRA → California Family Rights Act, etc.)
- `rule_display_name()` for dependency results (no Python class names)
- Schedule block, max-duration, parental, document, tenure/DBL messages via `format_*` helpers
- Debug-only intermediate reasoning suppressed or simplified

## Other

- **Structured spans:** `Result.spans` persisted; frontend prefers structured data; regex fallback for legacy rows
- **Frontend:** `format-empty-span-summary.ts`, `date-span-processor.ts`, mocks/tests updated

## Test plan

- [ ] `pytest backend/benefits/rules/tests/test_reasoning_format.py`
- [ ] Reasoning-related tests in `test_base_classes.py`
- [ ] `pytest backend/benefits/services/tests/test_results.py`
- [ ] Frontend span/reasoning tests
- [ ] Spot-check leave evaluation UI: no ISO dates, no Python reprs in reasoning panel
```

---

## Agent handoff prompt (paste into new Cursor session)

```
Also read AGENTS.local.md if present.

## Goal
Finish PIE-119 + PIE-121 on the EXISTING branch/PR — do NOT create a new PR from main.

Read the full handoff plan:
  ai-docs/pie-119-121-reasoning-humanization-handoff.md
(ai-docs/ is gitignored — local only)

## Context
- Jira: PIE-119 (date/decimal/timedelta formatting) + PIE-121 (reasoning.spans copy 7A–7H)
- Branch: pie-121-humanize-span-messages
- PR: https://github.com/ourtilt/tilt-repo/pull/11928
- Shared module: backend/benefits/rules/reasoning_format.py
- Do NOT create backend/benefits/utils/formatting.py
- main does NOT have this work

## Steps
1. git checkout pie-121-humanize-span-messages && git pull
2. Read ai-docs/pie-119-121-reasoning-humanization-handoff.md
3. Fix Maine PFML ISO date leaks (~L527-553 in maine/pfml.py) using existing format_* helpers
4. Run verification greps + tests from the plan
5. Fix any failures; rebase on main if needed
6. Update PR #11928 title/body to reference BOTH PIE-119 and PIE-121 (use template in plan) — only if I ask you to edit the PR
7. Summarize: what was fixed, CI status, anything still blocking merge

Follow @.ai/README.md, @.ai/rules/backend/backend-quality-standards.mdc, @.ai/rules/testing/testing-standards.mdc.
Do not commit unless I ask.
```

---

## Revision history

| Date | Notes |
|------|-------|
| 2026-09-15 | Initial handoff: PIE-119 vs PIE-121 clarified; maps to PR #11928 |
