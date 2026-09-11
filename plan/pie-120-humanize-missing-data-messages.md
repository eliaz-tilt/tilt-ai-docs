# PIE-120: Humanize "Missing Data" Messages — Work Plan

**Status:** Ready to execute (assumes PIE-504 #11927 and PIE-121 #11928 are
merged)\
**Ticket:** [PIE-120](https://ourtilt.atlassian.net/browse/PIE-120)\
**Spike docs:** `ai-docs/spikes/PIE-120-scope-summary.md`,
`ai-docs/spikes/PIE-120-humanize-missing-data-messages-scope.md`\
**Related (separate scope — do not conflate):**

- **PIE-121** (#11928): Humanize span _calculation_ narration
  (`reasoning_format.py`, span reprs, dates). Also humanizes `get_result_for()`
  and schedule missing messages — **do not duplicate that work in PIE-120.**
- **PIE-504** (#11927): Fix incorrect spans summary / max-duration narration
  bugs

**Merge constraint:** Ship as **one PR** (Phases 1–4 together). Do not merge
framework format changes without frontend detection updates — Admin PDP yellow
tooltips and Leave Management "Not Applied" copy will break.

**Estimated effort:** ~1–1.5 weeks (framework + checks + rule audit + frontend +
tests).

---

## Executive summary

**Current state (verified 2026-09-09): NOT STARTED.**

The framework still emits `Missing {description}` and
`Missing {description} (result)` in `backend/benefits/rules/__init__.py` (lines
593, 742). Downstream detection still keys off the `"Missing "` prefix
(`results.py:89`, `documents/serializers.py:956–961`) and the substring
`"missing"` in two frontend files. No `has not been provided` copy exists
anywhere in the repo.

**Goal:** Replace internal/jargon missing-data copy with plain, actionable
sentences end users can act on.

**Approach:** Option A — central format change in `require()` / `(result)` path
**plus** rewrite descriptions at the source (`Requirement.desc`, direct
`require(description=…)` calls). Do **not** build a centralized field-name
mapping layer.

**Critical warning:** Changing the format string alone is not enough. Without
updating descriptions, users would still see
`expected_due_date has not been provided.`

**Verified touch surface (2026-09-09):**

| Layer                                      | Scale                                    | Notes                                                                                                        |
| ------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Framework (`__init__.py`)                  | 2 primary paths                          | `require()` ~742, `__call_compute()` ~593                                                                    |
| Checks `Requirement` / `Requirement.get`   | **48** in `benefits/rules/checks/`       | 41 `Requirement(` + 7 `Requirement.get()`; fixes ~501 `Checkable` call sites                                 |
| Direct `require()` in rules                | **274** calls in **44** production files | **~22** lack explicit `description=` (12 files; use `rg`, not AST — some rule files use Python 3.12+ syntax) |
| Downstream consumers                       | 3 backend + 2 frontend                   | Must ship in same PR as framework                                                                            |
| Backend tests with `"Missing "` assertions | **21** files under `backend/benefits`    | Mass string updates expected                                                                                 |

**Out of scope (confirmed):**

- `leaves/services/checks/` — uses `WorkflowRequirement` (different type), not
  `benefits.rules.Requirement`; does not flow through `BaseRule.require()` or
  produce `"Missing …"` reasoning.
- `checks/policy.py`, `checks/dependent.py` — Jira lists these but they have no
  `Requirement(` usages.
- `get_result_for()` / schedule helper messages — handled by **PIE-121**
  (`reasoning_format.py`) after merge.

---

## Handoff prompt (copy for a fresh AI session)

```
Implement PIE-120: Humanize "Missing Data" Messages.

Read first:
1. ai-docs/plan/pie-120-humanize-missing-data-messages.md (this plan — full context)
2. .ai/rules/backend/backend-quality-standards.mdc
3. .ai/rules/testing/testing-standards.mdc

Prerequisites:
- PIE-504 (#11927) and PIE-121 (#11928) must be merged; rebase onto latest main.
- Work in a single PR through Phase 4 before merging.

Do NOT touch:
- PIE-121 span narration in reasoning_format.py (except reuse helpers if already there)
- get_result_for() / schedule missing messages (PIE-121 scope)
- Internal messages filtered by INTERNAL_MESSAGE_PATTERNS
- checks/company.py _final_reason "Missing definitive FMLA eligibility…"

Implementation order:
Phase 0 → Phase 1 (framework + detection + tests) → Phase 2 (checks desc) → Phase 3 (rule audit) → Phase 4 (frontend) → Phase 5 (guardrails)

Definition of done: all acceptance criteria in plan checklist pass; pytest backend/benefits/ green; frontend tests updated.

Branch: pie-120-humanize-missing-data-messages
```

---

## Background

### What users see today

When required data is absent, benefit and document rules record reasoning like:

- `Missing expected_due_date` (snake_case from
  `require(description="expected_due_date")`)
- `Missing The employee works in California (variable 1)` (fallback to check
  `desc` + multi-arg suffix)

Note: `Missing EE hire date` does not appear in current code — hire-date
variants use mixed casing (`Employee's hire date`, `hire date`, etc.).

### Where messages surface (category split matters)

| Surface                                                 | `reasoning` category   | Detection today                                | PIE-120 change                  |
| ------------------------------------------------------- | ---------------------- | ---------------------------------------------- | ------------------------------- |
| `reasons_ineligible` (sidebar, HR drawer, external API) | `eligible`             | `startswith("Missing ")` when `passed` is null | `is_missing_data_message()`     |
| Benefit reasoning API                                   | Most categories        | `get_user_facing_reasoning()` filter           | Pass-through; copy changes only |
| Admin PDP yellow tooltip                                | **`spans`**            | `.includes('missing')` on spans                | Shared `isMissingDataMessage()` |
| Leave Management "Not Applied"                          | **`spans`** (fallback) | Same in `suggestedBenefits.ts`                 | Same helper                     |
| Document suggestions                                    | `required`             | `startswith("Missing")` (no trailing space!)   | `is_missing_data_message()`     |

**Important:** `get_reasons_ineligible()` only reads `eligible`. Span-category
missing data drives the yellow tooltip — not `reasonsIneligible`. That is why
frontend detection must ship with the framework change.

### Architecture

```
Requirement(value, desc)     # dataclass in __init__.py ~4187
        ↓
requires(*reqs)               # loops → require(req.value, description=req.desc) ~701
        ↓
require(*vars, description)  # empty → "Missing {description}" + MissingValue ~707

Checkable(func)               # checks/base.py
  rule.describe(check.desc, check.desc_false)
  rule.requires(*check.reqs)
  return check.result()
```

**Key insight:** Updating `Requirement.desc` in check functions fixes all rules
that use that check via `Checkable` (~501 usages). You do **not** need to edit
every `requires()` call site. The only production manual `requires()` outside
checks is `new_jersey/fla.py`.

Both `BaseBenefitRule` and `BaseDocumentRule` share this machinery.

### PIE-120 vs PIE-121 code paths in `__init__.py`

| Lines | Pattern                                  | Owner                                                |
| ----- | ---------------------------------------- | ---------------------------------------------------- |
| ~593  | `Missing {desc} (result)`                | **PIE-120**                                          |
| ~742  | `Missing {description}{extra}`           | **PIE-120**                                          |
| ~1055 | `Missing result for {RuleName}`          | **PIE-121** (`format_missing_result_message`)        |
| ~3769 | `Missing schedule time including {date}` | **PIE-121** (`format_missing_schedule_time_message`) |

After PIE-121 merges, import/reuse `reasoning_format.py` helpers for the
`(result)` path rather than creating a parallel `missing_result_message()` in
`checks/messages.py`.

### What is NOT user-facing missing-data copy

Do not rewrite:

- `Missing approval_document_config` — filtered by `INTERNAL_MESSAGE_PATTERNS`
  in `results.py:26` (Jira rewrite table row is **stale**)
- `Missing definitive FMLA eligibility when 50/75 rule is enforced` —
  intentional `_final_reason()` in `checks/company.py:119`
- `Missing result for WashingtonPFMLPaidBenefit` — internal dependency names;
  PIE-121 handles
- Feature-flag / backfill / `Found result for …` strings — already filtered

---

## Pre-implementation decisions (record in PR description)

| # | Decision                            | Choice                                                      | Rationale                                                                                               |
| - | ----------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1 | Message strategy                    | **Full-sentence `desc` + suffix helpers**                   | See "Message format strategy" below                                                                     |
| 2 | Detection strategy                  | **Dual-match** (legacy `Missing` prefix + sentence markers) | Old persisted `Result` rows keep working                                                                |
| 3 | Admin PDP yellow tooltip            | **Keep scanning `spans`; broaden matcher**                  | `reasonsIneligible` only covers `eligible`                                                              |
| 4 | `get_result_for` / schedule         | **PIE-121 only**                                            | Already in `reasoning_format.py` on #11928                                                              |
| 5 | `Requirement.desc` DEBUG validation | **Fail in DEBUG**                                           | Mirror `Check.desc_false` in `checks/base.py:69–77`                                                     |
| 6 | `leaves/services/checks/`           | **Out of scope**                                            | `WorkflowRequirement`, different pipeline                                                               |
| 7 | Multi-field grouping                | **Deferred**                                                | Jira suggests "The following information is needed: …"; keep one message per empty field for v1         |
| 8 | Structured `missing_data` flag      | **Deferred**                                                | `Result.missing_data` removed in migration 0002; `IBenefitResultVM.missing_data` is stale frontend type |

### Message format strategy

Use **two helper functions** in `checks/messages.py` (extend existing 320-line
module):

**1. `missing_data_message(description: str) -> str`** — for `require()` path.

Default: `"{description} has not been provided."`

For descriptions that need different endings, pass a **complete sentence** as
`description` and use a variant helper, OR add optional `suffix` parameter. Map
rewrite-table rows to the right pattern:

| Suffix pattern            | Example final message                                                  | When to use                                            |
| ------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------ |
| `has not been provided`   | The expected due date has not been provided.                           | Dates, counts, simple fields                           |
| `has not been specified`  | The leave type has not been specified.                                 | Enum/choice fields                                     |
| `has not been confirmed`  | It has not been confirmed whether the employee is paid hourly.         | Boolean eligibility checks                             |
| `has not been recorded`   | The employee's work hours have not been recorded.                      | Hours, history                                         |
| `has not been set up`     | No leave schedule has been set up.                                     | Schedules, calendars                                   |
| `has not been verified`   | The employee's work hours have not been verified.                      | Tenure/hours thresholds                                |
| `has not been configured` | The benefit's maximum duration unit has not been configured.           | Benefit config fields (tenure unit, max duration unit) |
| `is not available`        | The employee's profile information is not available.                   | Missing related records                                |
| `could not be determined` | Concurrent pregnancy disability leave periods could not be determined. | `(result)` path default                                |
| `could not be calculated` | Leave periods could not be calculated.                                 | `spans` `(result)` failures                            |

**2. `missing_result_message(description: str) -> str`** — for
`__call_compute()` None path.

Map known internal `describe()` labels to friendly full sentences (see
Appendix). Default fallback: `"{description} could not be determined."`

After PIE-121 merges, check whether
`reasoning_format.format_missing_result_message()` can be reused to avoid
duplication.

**`require()` implementation:**

```python
# Before (line 741-742)
extra = "" if len(vars) == 1 else f" (variable {i})"
self.__reasoning.append(f"Missing {description}{extra}")

# After — drop (variable N) suffix entirely
self.__reasoning.append(missing_data_message(description))
```

When multiple args to one `require()` call are empty, emit one message per empty
arg (same as today), without suffix.

### Detection helpers

Add to `backend/benefits/services/results.py`:

```python
MISSING_DATA_LEGACY_PREFIXES = ("Missing ", "Missing")  # docs path uses bare "Missing"

MISSING_DATA_SENTENCE_MARKERS = (
    " has not been provided.",
    " could not be determined.",
    " could not be calculated.",
    " has not been confirmed.",
    " has not been specified.",
    " has not been recorded.",
    " has not been set up.",
    " has not been verified.",
    " has not been configured.",
    " is not available.",
)

def is_missing_data_message(text: str) -> bool:
    if any(text.startswith(p) for p in MISSING_DATA_LEGACY_PREFIXES):
        return True
    return any(marker in text for marker in MISSING_DATA_SENTENCE_MARKERS)
```

- Use in `get_reasons_ineligible()` (replace `startswith("Missing ")` at line
  89).
- Export and import in `documents/serializers.py` `get_reasons_suggested()`
  (replace `SUGGESTED_KEYWORDS` Missing match).
- Mirror exact marker list in `frontend/client/utils/missingDataReasoning.ts`.

Keep `_normalize_ineligible_reason()` stripping `(variable N)` for legacy
persisted rows.

---

## Implementation order

| Step | Phase                 | Deliverable                                        | Gate                         |
| ---- | --------------------- | -------------------------------------------------- | ---------------------------- |
| 0    | Prerequisites         | Branch, decisions recorded                         | PIE-504 + PIE-121 merged     |
| 1    | Framework + detection | `require()`, `(result)`, `results.py`, serializers | pytest Phase 1 files green   |
| 2    | Checks layer          | 48 `Requirement` desc rewrites                     | `pytest checks/tests/` green |
| 3    | Rule audit            | 274 `require()` descriptions                       | No snake_case/EE in prod     |
| 4    | Frontend              | Shared helper + 2 consumers + tests                | Tooltip + Not Applied work   |
| 5    | Guardrails            | DEBUG validation, optional CI script               | —                            |

**Do not merge until steps 1–4 complete.**

---

## Phase 0: Prerequisites

- [ ] Confirm PIE-504 and PIE-121 are merged
- [ ] Rebase `pie-120-humanize-missing-data-messages` onto latest `main`
- [ ] Record decisions table in PR description
- [ ] Resolve rebase conflicts in: `results.py`, `test_results.py`,
      `test_base_classes.py` (touched by PIE-121)

**PIE-121 coordination:** PIE-121 changes non-None `__call_compute` path (~622,
`format_expression_result`) and span narration — **not** PIE-120's lines
593/742. Do not edit the wrong branch in `__call_compute`.

---

## Phase 1: Framework + detection

### 1.1 `backend/benefits/rules/__init__.py`

**`require()` (lines 707–745):**

1. `self.__reasoning.append(missing_data_message(description))`
2. Remove `(variable N)` suffix logic (lines 741–742)
3. Keep `MissingValue` raise unchanged

**`__call_compute()` (lines 583–594):**

1. Replace line 593 with `missing_result_message(self.__description)` (or
   PIE-121's `format_missing_result_message` if available)
2. Do not change boolean `describe()` / `desc_false` paths (lines 607–620)

### 1.2 `backend/benefits/rules/checks/messages.py`

Extend existing module with `missing_data_message()` and
`missing_result_message()` plus label→message map for known `(result)`
describe() strings (see Appendix).

### 1.3 `backend/benefits/services/results.py`

- Add `is_missing_data_message()` and `MISSING_DATA_SENTENCE_MARKERS`
- Update `get_reasons_ineligible()`

### 1.4 Serializers

| File                               | Change                                                                                                        |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `backend/documents/serializers.py` | `get_reasons_suggested()` → `is_missing_data_message()`                                                       |
| `backend/benefits/serializers.py`  | No code change; `ResultSerializer` exposes `reasons_ineligible` via `get_reasons_ineligible()` — fixed by 1.3 |

### 1.5 Tests

| File                                                | Action                                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `backend/benefits/rules/tests/test_base_classes.py` | Update ~25 `"Missing "` assertions                                                                |
| `backend/benefits/services/tests/test_results.py`   | Add `passed is None` + new format + legacy prefix cases (**net-new** coverage for line 89 branch) |
| `backend/documents/tests/test_serializers.py`       | Update fixtures (e.g. line ~1297)                                                                 |
| `backend/benefits/tests/test_serializers.py`        | Update `reasons_ineligible` assertions (lines ~170–211)                                           |

**Phase 1 gate:**

```bash
pytest backend/benefits/rules/tests/test_base_classes.py \
       backend/benefits/services/tests/test_results.py \
       backend/benefits/tests/test_serializers.py \
       backend/documents/tests/test_serializers.py -q
```

---

## Phase 2: Checks layer descriptions

Rewrite all **48** `Requirement` / `Requirement.get` descriptions in
`benefits/rules/checks/`.

**Do not change `Check.desc` / `desc_false`** unless a missing-data fallback
incorrectly uses the check's main `desc`.

### Files and counts

| File                 | Count                                         | Notes                                                                         |
| -------------------- | --------------------------------------------- | ----------------------------------------------------------------------------- |
| `checks/employee.py` | 19 `Requirement(`                             | High priority; add `desc` to bare `Requirement(working_state)` at **line 96** |
| `checks/leave.py`    | 13 `Requirement(` + **3** `Requirement.get()` | Add `desc` to all bare requirements                                           |
| `checks/company.py`  | 4 `Requirement.get()`                         |                                                                               |
| `checks/paycalc.py`  | 4                                             |                                                                               |
| `checks/benefit.py`  | 3                                             |                                                                               |
| `checks/schedule.py` | 2                                             |                                                                               |

### Requirements without `desc`

When `Requirement(value)` has no `desc`, `requires()` falls back to check `desc`
(eligibility sentence, often wrong for missing-data). **Add explicit `desc` to
every Requirement in `reqs` lists.**

```python
# leave.py — before
reqs=[base.Requirement(leave.leave_type)]
# after
reqs=[base.Requirement(leave.leave_type, "The leave type")]
```

### Consolidation (canonical `desc` values)

| Canonical `desc`                     | Suffix helper                 | Replaces                                            |
| ------------------------------------ | ----------------------------- | --------------------------------------------------- |
| `The employee's hire date`           | provided                      | `hire date`, `Employee's hire date`, `EE hire date` |
| `The leave start date`               | provided                      | `leave begins date`, `Leave start date`             |
| `The expected due date`              | provided                      | `expected_due_date`, `Expected due date`            |
| `The employee's work state`          | confirmed                     | All `works in: XX` variants                         |
| `The employee's profile information` | available                     | `Employee profile`                                  |
| `The leave type`                     | specified                     | `leave type`, `benefit leave type`                  |
| `No leave schedule`                  | set up (custom full sentence) | `leave schedule`, `non-generic leave schedule`      |

See **Appendix: Rewrite table** for all Jira mappings.

### Tests

Extend `checks/tests/test_employee.py` (and leave, company) to assert reasoning
strings on `MissingValue`, not just `AttributeError`:

```python
assert "The employee's hire date has not been provided." in captured_reasoning
```

**Phase 2 gate:** `pytest backend/benefits/rules/checks/tests/ -q`

---

## Phase 3: Direct `require()` audit

**274** `self.require()` calls across **44** production files.

### Order of attack

1. **~22 calls without `description=`** (12 files) — worst UX (Python function
   names). Find with:
   ```bash
   rg 'self\.require\([^)]*\)$' backend/benefits/rules --glob '*.py' | rg -v 'description='
   ```
2. Snake_case: `rg 'description="[a-z_]+"' backend/benefits/rules --glob '*.py'`
3. EE abbreviation:
   `rg 'description=".*EE' backend/benefits/rules --glob '*.py'`
4. Document rules: `documents/proof_of_bonding.py`,
   `documents/explanation_of_benefits.py`, etc.

### Style guide

| Bad                                        | Good                                            |
| ------------------------------------------ | ----------------------------------------------- |
| `description="expected_due_date"`          | `description="The expected due date"`           |
| `description="Is pregnant"`                | `description="The employee's pregnancy status"` |
| `self.require(leave.leave_type)` (no desc) | `description="The leave type"`                  |

Use shared constants where repeated across state files.

### Test strategy

- Phase 2 checks tests + spot-check: `fmla.py`, `california/pdl.py`,
  `massachusetts/pfml.py`, `new_york/pfl.py`
- Update **21** test files:
  `rg '"Missing ' backend/benefits --glob '**/test*.py' -l`

**Phase 3 gate:** No snake_case/EE in production `require(description=…)`;
intentional internal `"Missing "` strings only in `_final_reason` / comments.

---

## Phase 4: Frontend

### 4.1 Create `frontend/client/utils/missingDataReasoning.ts`

Export `MISSING_DATA_SENTENCE_MARKERS` (must match backend exactly) and:

```typescript
export function isMissingDataMessage(text: string): boolean {
    if (text.startsWith("Missing ") || text.startsWith("Missing")) return true;
    return MISSING_DATA_SENTENCE_MARKERS.some((m) => text.includes(m));
}
```

Add unit tests: legacy prefix, each marker, non-matches (`'missing wages'`,
eligibility copy with "has not been").

### 4.2 Update consumers

| File                          | Lines   | Change                                                 |
| ----------------------------- | ------- | ------------------------------------------------------ |
| `EligibleBenefitsSection.tsx` | 579–585 | Use `isMissingDataMessage`; add `?? []` for null spans |
| `suggestedBenefits.ts`        | 642–644 | Same helper in `formatMissingSpanReasons`              |

**Regression risk:** If markers are incomplete and `spans` is non-empty,
`getNotAppliedReason` (line 674–678) falls through to **all** span reasons — not
just missing-data.

### 4.3 Frontend tests

| File                                                     | Action                                                                        |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `frontend/client/utils/missingDataReasoning.test.ts`     | **New** — helper unit tests                                                   |
| `frontend/client/utils/suggestedBenefits.test.ts`        | Add humanized message cases (~173–177)                                        |
| `EligibleBenefitsSection.test.tsx`                       | Add tooltip test with `FLAG_ENABLE_BENEFIT_EXPLAINABILITY`                    |
| `DocumentsPanel.test.tsx`, `SuggestedDocuments.test.tsx` | Update mocked `reasonsSuggested` strings when document rules change (Phase 3) |

### 4.4 `missing_data` flag — do not wire

`IBenefitResultVM.missing_data` (`_types/index.ts:30`) is stale.
`Result.missing_data` was removed in migration 0002. Defer structured detection
to follow-up.

**Phase 4 gate:** Manual PDP smoke + frontend unit tests green.

---

## Phase 5: Guardrails

### 5.1 DEBUG validation on `Requirement`

In `Requirement` dataclass or `Checkable.__call__`: fail in DEBUG if `desc` is
blank or matches snake_case field name (`^[a-z][a-z0-9_]*$`).

### 5.2 Optional CI script

`scripts/check_require_descriptions.py` — flag `require()` without
`description=` (expect **~22** initially, 0 at end) and bare
`Requirement(value)`. Prefer `rg`-based check over AST (some rule files use
Python 3.12+ syntax).

---

## Acceptance criteria checklist

| Criterion                              | How to verify                                                   |
| -------------------------------------- | --------------------------------------------------------------- |
| No internal variable names in messages | No `expected_due_date has not been provided` in output          |
| No `EE` abbreviation                   | `rg 'EE ' backend/benefits/rules --glob '*.py'` in descriptions |
| Complete sentences                     | All end with `.`                                                |
| Duplicate messages consolidated        | Same field → same `desc`                                        |
| `get_reasons_ineligible()` works       | `test_results.py` legacy + new                                  |
| `get_reasons_suggested()` works        | `documents/tests/test_serializers.py`                           |
| No `(variable N)` in new messages      | New fixtures only                                               |
| Frontend yellow tooltip works          | `EligibleBenefitsSection` test + manual PDP                     |
| Leave Management "Not Applied" works   | `suggestedBenefits.test.ts`                                     |
| Legacy persisted rows work             | Dual-match tests                                                |

---

## Files to modify

```
# Phase 1
backend/benefits/rules/__init__.py
backend/benefits/rules/checks/messages.py
backend/benefits/services/results.py
backend/documents/serializers.py
backend/benefits/rules/tests/test_base_classes.py
backend/benefits/services/tests/test_results.py
backend/benefits/tests/test_serializers.py
backend/documents/tests/test_serializers.py

# Phase 2
backend/benefits/rules/checks/employee.py
backend/benefits/rules/checks/leave.py
backend/benefits/rules/checks/company.py
backend/benefits/rules/checks/paycalc.py
backend/benefits/rules/checks/benefit.py
backend/benefits/rules/checks/schedule.py
backend/benefits/rules/checks/tests/test_*.py

# Phase 3
44 production rule files under backend/benefits/rules/
21 associated test files

# Phase 4
frontend/client/utils/missingDataReasoning.ts (+ test)
frontend/client/utils/suggestedBenefits.ts
frontend/client/screens/Admin/.../EligibleBenefitsSection.tsx (+ test)

# Phase 5
backend/benefits/rules/__init__.py (Requirement validation)
scripts/check_require_descriptions.py (optional)
```

---

## Verification commands

```bash
pytest backend/benefits/rules/tests/test_base_classes.py -q
pytest backend/benefits/services/tests/test_results.py -q
pytest backend/benefits/tests/test_serializers.py -q
pytest backend/benefits/rules/checks/tests/ -q
pytest backend/documents/tests/test_serializers.py -q
# frontend: run missingDataReasoning + suggestedBenefits + EligibleBenefitsSection tests

rg '"Missing ' backend/benefits --glob '**/test*.py' -l
rg 'description="[a-z_]+"' backend/benefits/rules --glob '*.py' | rg -v test_
pytest backend/benefits/ -q --tb=no
```

### Manual smoke test

1. Leave missing `expected_due_date` + benefit requiring it (e.g. CA PDL)
2. `reasons_ineligible` → `The expected due date has not been provided.`
3. Admin PDP → eligible benefit, no paycalc, span missing data → yellow tooltip
   shows message
4. Document suggestion missing required field → `reasons_suggested` humanized

---

## Out of scope / follow-ups

| Item                                                    | Notes                                    |
| ------------------------------------------------------- | ---------------------------------------- |
| `get_result_for` / schedule messages                    | **PIE-121**                              |
| `Result.missing_data` / `IBenefitResultVM.missing_data` | Requires model + serializer + evaluation |
| Multi-field grouping message                            | Deferred per decision #7                 |
| `leaves/services/checks/` WorkflowRequirement           | Different pipeline                       |
| Rules Builder `missing_data_point` catalog              | Engineering catalog                      |
| Span calculation narration                              | **PIE-121**                              |
| Spans summary bugs                                      | **PIE-504**                              |

---

## Rollback plan

Revert the PR. No migrations. Legacy `"Missing "` strings remain readable via
dual-match detection.

---

## Review checklist (post-plan)

- [x] Counts verified against codebase (2026-09-09)
- [x] `leaves/services/checks/` excluded
- [x] Single-PR merge constraint documented
- [x] Suffix strategy documented (multiple patterns, not one-size-fits-all)
- [x] PIE-121 overlap on `get_result_for`/schedule noted
- [x] `approval_document_config` Jira row marked stale
- [x] Handoff prompt included
- [x] Rewrite table inlined in appendix

---

## Appendix: Rewrite table (from Jira PIE-120)

Use the **Canonical `desc`** column with the appropriate suffix helper from
"Message format strategy". Final message = helper output.

### Employee information

| Current (starts with `Missing`)                                    | Canonical `desc`                                                             | Suffix    | Final message                                                        |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------- |
| EE hire date / Employee's hire date / hire date                    | The employee's hire date                                                     | provided  | The employee's hire date has not been provided.                      |
| Employee profile                                                   | The employee's profile information                                           | available | The employee's profile information is not available.                 |
| Employee contract types                                            | The employee's employment type (full-time/part-time)                         | specified | …has not been specified.                                             |
| Employee is hourly                                                 | whether the employee is paid hourly                                          | confirmed | It has not been confirmed whether the employee is paid hourly.       |
| employee hours worked                                              | The employee's work hours                                                    | recorded  | The employee's work hours have not been recorded.                    |
| Employee home country                                              | The employee's home country                                                  | specified | …has not been specified.                                             |
| pregnancy status / is ee pregnant                                  | The employee's pregnancy status                                              | provided  | …has not been provided.                                              |
| The employee is pregnant (a Birthing Parent)                       | whether the employee is a birthing parent                                    | confirmed | It has not been confirmed whether the employee is a birthing parent. |
| Employee is not excluded from Delaware PFML                        | whether the employee is covered under Delaware Paid Family and Medical Leave | confirmed | It has not been confirmed whether…                                   |
| The employee is enrolled in STD benefits                           | whether the employee is enrolled in short-term disability                    | confirmed | It has not been confirmed whether…                                   |
| Colorado FAMLI earnings requirements                               | whether the employee meets Colorado FAMLI earnings requirements              | confirmed | It has not been confirmed whether…                                   |
| 1250 hours worked prior / leave's employee has at least 1250 hours | The employee's work hours                                                    | verified  | The employee's work hours have not been verified.                    |
| 1250 hours worked date                                             | The date when the employee reached 1,250 work hours                          | provided  | …has not been provided.                                              |
| has worked more / Has worked more                                  | The employee's work history                                                  | provided  | …has not been provided.                                              |
| has_met_wa_hours                                                   | whether the employee meets Washington's work hours requirement               | confirmed | It has not been confirmed whether…                                   |
| EE has met OR earnings requirement                                 | whether the employee meets Oregon's earnings requirement                     | confirmed | It has not been confirmed whether…                                   |

### Leave information

| Current                                                 | Canonical `desc`                                           | Suffix    | Final message                                      |
| ------------------------------------------------------- | ---------------------------------------------------------- | --------- | -------------------------------------------------- |
| leave begins date / Leave start date / leave start date | The leave start date                                       | provided  | The leave start date has not been provided.        |
| return to work date / Return to work date               | The expected return-to-work date                           | provided  | …has not been provided.                            |
| Expected return date                                    | The expected return date                                   | provided  | …has not been provided.                            |
| Effective start date                                    | The benefit effective start date                           | provided  | …has not been provided.                            |
| leave schedule / non-generic leave schedule             | No leave schedule                                          | custom    | No leave schedule has been set up.                 |
| is leave continuous or intermittent                     | whether the leave is continuous or intermittent            | specified | It has not been specified whether…                 |
| benefit leave type                                      | The leave type                                             | specified | The leave type has not been specified.             |
| paths to parenthood                                     | The path to parenthood (birth, adoption, etc.)             | specified | …has not been specified.                           |
| caregiver relationship matches                          | The caregiver relationship                                 | confirmed | The caregiver relationship has not been confirmed. |
| Caring for covered family member                        | whether the employee is caring for a covered family member | confirmed | It has not been confirmed whether…                 |

### Company information

| Current                                | Canonical `desc`                                                   | Suffix    |
| -------------------------------------- | ------------------------------------------------------------------ | --------- |
| Company policy FMLA employer threshold | whether the company meets the FMLA employer size requirement       | confirmed |
| 25 Washington-based employees          | Washington employee count for the company                          | confirmed |
| at least 50 employees in the US        | The company's U.S. employee count                                  | confirmed |
| total_employees_tn_100_or_more         | The company's Tennessee employee count                             | confirmed |
| Delaware PFML coverage tier            | The company's Delaware Paid Family and Medical Leave coverage tier | confirmed |

### Work location

| Current                                                           | Canonical `desc`                         | Suffix    |
| ----------------------------------------------------------------- | ---------------------------------------- | --------- |
| The employee works in: {state} / works in California (variable N) | The employee's work state                | confirmed |
| Employee worksite is FMLA eligible (50/75 rule)                   | The employee's worksite FMLA eligibility | confirmed |
| The leave is in California (variable N)                           | The leave state                          | confirmed |

### Benefit / tenure / parental

| Current                                       | Canonical `desc`                                     | Suffix                                 |
| --------------------------------------------- | ---------------------------------------------------- | -------------------------------------- |
| tenure requirement / tenure requirement unit  | The benefit's tenure requirement (unit)              | configured → "has not been configured" |
| Full time EE works 20+ hours                  | whether the employee works 20 or more hours per week | confirmed                              |
| Part time EE 175 days                         | The part-time employee's work history                | verified                               |
| expected_due_date / Leave Expected Birth Date | The expected due date / birth date                   | provided                               |
| expected_children                             | The expected number of children                      | provided                               |
| birth delivery method / birth type            | The birth delivery method / type of birth            | recorded                               |
| parental role                                 | The parental role                                    | specified                              |

### Span / calculation (`(result)` path)

| Current                                    | Final message (full sentence)                                              |
| ------------------------------------------ | -------------------------------------------------------------------------- |
| spans (result) / spans (variable 0)        | Leave periods could not be calculated.                                     |
| employee pay calendar                      | The employee's pay calendar has not been set up.                           |
| max duration unit                          | The benefit's maximum duration unit has not been configured.               |
| unit of time for minimum required time off | The minimum time off unit for intermittent leaves has not been configured. |
| get_concurrent_pdl_spans (result)          | Concurrent pregnancy disability leave periods could not be determined.     |
| approval_document_config (result)          | **Do not humanize** — internal, filtered                                   |
