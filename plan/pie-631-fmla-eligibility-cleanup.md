# PIE-631: FMLA Eligibility Message Cleanup — Work Plan

**Status:** Ready to execute — revised after 3 pageant review rounds
(2026-09-15)\
**Assumes:** PIE-115 / #11995 merged on `main`\
**Ticket:** [PIE-631](https://ourtilt.atlassian.net/browse/PIE-631)\
**Parent:** PIE-115 — plain-language FMLA eligibility messages (#11995)\
**Reviewer follow-up:** @dmwyatt (deferred cleanup from PR review)\
**Primary code:** `backend/legacy/fmla.py`

**Estimated effort:** ~3–5 days (reason codes + persistence change + tests; +1–2
days if backfill command included)

---

## Executive summary

**Current state (verified 2026-09-15):** PIE-115 shipped
`build_eligibility_messages()`, persisted `eligibility_reasons` +
`eligibility_desc` in `fmla_reasons` JSON via `FMLAReasoning.to_dict()`.
Formatter helpers (`_location_eligibility_message`,
`_hire_date_eligibility_message`, etc.) re-inspect `leave`/`profile`/`policy`
instead of mapping from criterion outcomes. Several formatter fallbacks are
unreachable from the `is_leave_fmla_eligible()` pipeline.

**Goal:** Make criterion tests the single source of eligibility narrative truth;
stop persisting redundant `eligibility_desc`; optionally refresh stale
bracket-format `fmla_reasons` on existing leaves/plans.

**Approach:**

1. Add discrete **reason codes** (+ minimal interpolation context) on
   `FMLAReasoning`, set in `test_*` functions.
2. Refactor `build_eligibility_messages()` to map `code + context → sentence`
   (no leave/profile re-derivation).
3. **Stop persisting** `eligibility_desc`; assemble at read sites from heading +
   `eligibility_reasons`.
4. **Optional Phase 4:** idempotent `refresh_fmla_reasons` management command
   with `--dry-run`.

**Merge constraint:** Ship Phases 1–3 as **one PR**. Backfill command may be
same PR or fast follow-up (see decision table).

---

## Handoff prompt (copy for a fresh AI session)

```
Implement PIE-631: FMLA eligibility message cleanup (PIE-115 follow-up).

Read first:
1. ai-docs/plan/pie-631-fmla-eligibility-cleanup.md (this plan — includes pageant review fixes)
2. .ai/rules/backend/backend-quality-standards.mdc
3. .ai/rules/testing/testing-standards.mdc

Prerequisites:
- PIE-115 (#11995) merged on main; rebase onto latest main.
- Record pre-implementation decisions table (13 rows) in PR description.
- Ship Phases 1–4 in one PR (backfill command included).

Do NOT touch:
- backend/benefits/rules/fmla.py (benefits rules engine)
- designation_desc / med-cert copy / FMLA PDF templates
- check_employee_count() wiring (deleted in PIE-115)

Implementation order:
Phase 0 → Phase 1 (reason codes in test_*) → Phase 2 (pure code→sentence map) →
Phase 3 (stop persisting eligibility_desc; fmla_reasons_persisted_equal; PlanAdminOutputSerializer inject;
create_plan_from_leave snapshot; ensure_* ValueError handling) →
Phase 4 (refresh_fmla_reasons command with --dry-run default)

Critical gates (do not skip):
- fmla_reasons_persisted_equal() for update_leave_fmla (NOT __eq__)
- PlanAdminOutputSerializer injects eligibilityDesc on read (not leave serializers)
- Military vs OTHER branching in test_leave_type_fmla_eligible
- COMPANY_NO_POLICY emits one code, not two

Definition of done: acceptance criteria checklist in plan; pytest test_fmla.py + test_checks.py green.

Branch: pie-631-fmla-eligibility-cleanup
```

---

## Background

### What PIE-115 shipped

| Addition                                                   | Location                            |
| ---------------------------------------------------------- | ----------------------------------- |
| `build_eligibility_messages()`                             | End of `is_leave_fmla_eligible()`   |
| `eligibility_reasons: list[str]` on `FMLAReasoning`        | Persisted in `fmla_reasons` JSON    |
| `eligibility_desc` = heading + blank line + joined reasons | Persisted in `fmla_reasons` JSON    |
| Plain-language criterion copy                              | Removed bracket notation from tests |

### Production readers audit (post-review)

| Consumer                                                    | Uses `eligibility_desc`?                      | Uses `eligibility_reasons`? | Uses boolean flags?                              |
| ----------------------------------------------------------- | --------------------------------------------- | --------------------------- | ------------------------------------------------ |
| `backend/leaves/services/checks/leave.py` (`is_fmla_leave`) | **Yes** — workflow check `desc` via `gettext` | No                          | `leave.fmla` for result                          |
| `frontend/client/_mocks_/AdminPDP/planData.ts`              | Mock only                                     | Mock only                   | —                                                |
| Leave/Plan serializers (`fmla_reasons` JSON field)          | Pass-through persisted dict                   | Pass-through                | `fmla` boolean                                   |
| `backend/documents/services/fmla.py`                        | No                                            | No                          | `hire_date_eligible`, `work_time_eligible`, etc. |
| `backend/notifications/services/messages.py`                | No                                            | No                          | `designation_desc`, flags                        |
| `backend/legacy/serializers/users.py`                       | Clears to `""` for boolean preview only       | No                          | `test_company` + `is_profile_fmla_eligible`      |

**Only production prose reader:** `is_fmla_leave` workflow check.

### Architecture today

```
test_company ──────────────┐
test_leave_type ───────────┤
test_work_hours ───────────┼→ FMLAReasoning (booleans)
test_hire_date ────────────┤
test_location ─────────────┘
        ↓
build_eligibility_messages()  ← re-reads leave/profile/policy for copy
        ↓
eligibility_reasons + eligibility_desc
        ↓
FMLAReasoning.to_dict() → leave.fmla_reasons / plan.fmla_reasons (persisted)
        ↓
is_fmla_leave check reads eligibility_desc from persisted JSON
```

### Target architecture

```
test_*() → sets boolean + reason_code (+ minimal context dict)
        ↓
build_eligibility_messages(codes, context) → eligibility_reasons only
        ↓
to_dict() persists reasons + codes + booleans; NOT eligibility_desc
        ↓
assemble_eligibility_desc(reasoning, leave) at read sites
```

---

## Pre-implementation decisions (record in PR description)

| #  | Decision                       | **Recommended choice**                                                        | Rationale                                                                                               |
| -- | ------------------------------ | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1  | Reason code shape              | **`str` enum per criterion + shared `eligibility_message_context: dict`**     | Hire-date and company copy need formatted dates/counts; avoid re-reading leave in formatter             |
| 2  | Persist reason codes?          | **Yes** — include in `to_dict()`                                              | Enables future read-site assembly from codes alone; aids debugging stale rows                           |
| 3  | Persist `eligibility_reasons`? | **Yes** — keep as source of truth for prose                                   | Workflow check and API can use list without re-running eligibility                                      |
| 4  | API `eligibilityDesc` field    | **Assemble on read in serializer** (optional inject)                          | Admin PDP mock + external clients may expect camelCase key; field becomes computed, not stored          |
| 5  | Stale bracket data             | **Ship backfill command in same PR** (Phase 4) with `--dry-run` default       | Phases 1–3 alone do not rewrite stale `eligibility_reasons` prose                                       |
| 6  | `len(to_dict())` assertions    | **Replace with key-set assertions**                                           | Brittle exact-count tests (15/16) break when fields added/removed                                       |
| 7  | Heading assembly needs `leave` | **Pass `leave` only to heading helper**                                       | Leave type display label not stored in `fmla_reasons`                                                   |
| 8  | Change detection               | **`fmla_reasons_persisted_equal()`, not `__eq__`**                            | `update_leave_fmla` compares reasoning objects; legacy `eligibility_desc` in JSON causes spurious saves |
| 9  | Plan snapshot on create        | **Snapshot `fmla_reasoning.to_dict()` in `create_plan_from_leave`**           | Today copies stale `leave.fmla_reasons` even after fresh `ensure_*` compute                             |
| 10 | Backfill plans                 | **Always resync `plan` from refreshed leave**; optional `--resync-plans-only` | Plans can drift from leave (`update_leave_fmla` does not sync plan)                                     |
| 11 | `ValueError` in `ensure_*`     | **Catch like `update_leave_fmla`**                                            | `create_plan_from_leave` can crash on missing hire date today                                           |
| 12 | API `eligibilityDesc`          | **Required: inject in `PlanAdminOutputSerializer`**                           | Admin PDP reads plan payload; leave serializers exclude `fmla_reasons`                                  |
| 13 | Context persistence            | **String-only values in `eligibility_message_context`**                       | Nested dates in dict bypass `_dict_value` ISO formatting                                                |

---

## Reason code design

### Enum: `FMLAEligibilityReasonCode` (in `backend/legacy/fmla.py`)

**Company** (from `test_company` / `_company_eligibility_reasons` logic):

| Code                           | Message template                                                                   |
| ------------------------------ | ---------------------------------------------------------------------------------- |
| `COMPANY_NO_POLICY`            | The employer does not have an FMLA policy configured.                              |
| `COMPANY_PUBLIC_AGENCY`        | The employer is a government agency (automatically meets size requirement).        |
| `COMPANY_SCHOOL`               | The employer is a public or private school (automatically meets size requirement). |
| `COMPANY_THRESHOLD_MET`        | The employer meets the FMLA size requirement.                                      |
| `COMPANY_THRESHOLD_NOT_MET`    | The employer does not meet the FMLA size requirement.                              |
| `COMPANY_EMPLOYEE_COUNT_USA`   | The employer has {count} employees in the U.S.                                     |
| `COMPANY_EMPLOYEE_COUNT_TOTAL` | The employer has {count} total employees.                                          |

Company emits **two** reason entries (verdict + count line) **except**
`COMPANY_NO_POLICY`, which emits **one** entry only (no count line).

**Leave type** (`test_leave_type_fmla_eligible`):

| Code                    | Context   | Message                                          |
| ----------------------- | --------- | ------------------------------------------------ |
| `LEAVE_TYPE_QUALIFYING` | `{label}` | `{label} leave is a qualifying FMLA leave type.` |
| `LEAVE_TYPE_MILITARY`   | —         | Military leave does not qualify for FMLA.        |
| `LEAVE_TYPE_OTHER`      | —         | This leave type does not qualify for FMLA.       |

**Work hours** (`test_work_hours`):

| Code                  | When                                                                      |
| --------------------- | ------------------------------------------------------------------------- |
| `WORK_HOURS_MET`      | `has_worked_more == YES`                                                  |
| `WORK_HOURS_NOT_MET`  | `has_worked_more == NO`                                                   |
| `WORK_HOURS_NOT_SURE` | `has_worked_more == NOT_SURE`                                             |
| `WORK_HOURS_UNKNOWN`  | `has_worked_more is None` or missing profile → `eligibility_unknown=True` |

**Hire date** (`test_hire_date` — preconditions enforced by raises):

| Code                            | Context                                  |
| ------------------------------- | ---------------------------------------- |
| `HIRE_DATE_ELIGIBLE`            | `{hire_date_formatted}`                  |
| `HIRE_DATE_AFTER_LEAVE`         | `{hire_date_formatted}`                  |
| `HIRE_DATE_UNDER_ONE_MONTH`     | `{hire_date_formatted}`                  |
| `HIRE_DATE_INSUFFICIENT_TENURE` | `{hire_date_formatted}`, `{diff_months}` |

Remove unreachable `return ""` guard in `_hire_date_eligibility_message`.

**Location** (`test_location`):

| Code                  | When                                                    |
| --------------------- | ------------------------------------------------------- |
| `LOCATION_ELIGIBLE`   | US + passes 50/75 or rule not enforced                  |
| `LOCATION_NON_US`     | `home_country` not US (None treated as US in test)      |
| `LOCATION_50_75_FAIL` | `enforce_fmla_50_and_75_rule` and not worksite eligible |

Remove unreachable final fallback
`"The employee's work location is not FMLA eligible."` — `LOCATION_50_75_FAIL`
covers the remaining false path.

### `FMLAReasoning` new fields

```python
# Ordered list matching eligibility_reasons output order
eligibility_reason_codes: list[str]
# Shared interpolation values keyed by criterion
eligibility_message_context: dict[str, Any]  # hire_date, diff_months, employee_count, count_type, leave_type_label
```

Set codes in `test_*`; `build_eligibility_messages()` only reads
`reasoning.eligibility_reason_codes` + `eligibility_message_context`.

---

## Implementation order

| Step | Phase                              | Deliverable                                              | Gate                                      |
| ---- | ---------------------------------- | -------------------------------------------------------- | ----------------------------------------- |
| 0    | Prerequisites + audit              | Branch, serializer audit, decision log                   | PIE-115 on main                           |
| 1    | Reason codes                       | Enum + set in `test_*` + persist in `to_dict()`          | Unit tests for code assignment            |
| 2    | Formatter refactor                 | Pure `code → sentence` map; delete re-derivation helpers | `test_build_eligibility_messages_*` green |
| 3    | Stop persisting `eligibility_desc` | `assemble_eligibility_desc()` + read-site wiring         | `test_checks.py` + `test_fmla.py` green   |
| 4    | Optional backfill                  | `refresh_fmla_reasons` command                           | Dry-run + spot-check leaves               |

**Do not merge until steps 1–3 complete.**

---

## Phase 0: Prerequisites

- [ ] Confirm PIE-115 (#11995) merged on `main`
- [ ] Rebase `pie-631-fmla-eligibility-cleanup` onto latest `main`
- [ ] Record decisions table in PR description
- [ ] Serializer audit: grep `eligibility_desc` / `eligibilityDesc` across
      backend + frontend
- [ ] Note: exact `len(reasoning.to_dict())` assertions in `test_fmla.py` (lines
      ~168–311) must be updated

**Files to read before coding:**

```
backend/legacy/fmla.py
backend/leaves/services/checks/leave.py
backend/legacy/services/leaves/fmla.py          # update_leave_fmla
backend/legacy/services/plans.py                # ensure_leave_fmla_reasons_exists
backend/legacy/views/plans.py                 # generate_documents guard
backend/legacy/tests/test_fmla.py
backend/leaves/services/checks/tests/test_checks.py
frontend/client/__mocks__/AdminPDP/planData.ts
```

---

## Phase 1: Reason codes on `FMLAReasoning`

### 1.1 Add `FMLAEligibilityReasonCode` enum + context helpers

- Place in `backend/legacy/fmla.py` (same module as `FMLAReasoning`)
- Add `eligibility_reason_codes` and `eligibility_message_context` to
  `FMLAReasoning.__annotations__`
- Initialize in `__init__`: empty list / empty dict
- Include in `to_dict()` / `_internal_value` deserialization

### 1.2 Set codes in criterion tests

| Function                        | Sets                                                                                                                                                                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_company`                  | Company verdict code + count code; context: `employee_count`, `count_type`                                                                                                                                                      |
| `test_leave_type_fmla_eligible` | Leave type code; context: `leave_type_label` when qualifying; **branch `MILITARY` vs `OTHER` vs qualifying** (today only formatter distinguishes military)                                                                      |
| `test_work_hours`               | Work hours code                                                                                                                                                                                                                 |
| `test_hire_date`                | Hire date code; context: `hire_date_formatted`, `diff_months`; **branch order:** `hire_date > expected_leave_date` before `diff_months == 0` before insufficient tenure (mirror `_hire_date_eligibility_message` lines 281–296) |
| `test_location`                 | Location code                                                                                                                                                                                                                   |

**Context population rule:** `test_*` functions capture values they already
compute (e.g. `diff_months` in `test_hire_date`) — do not add new leave/profile
reads beyond what the test already does. **All context values must be
JSON-serializable strings/ints** (pre-format dates before storing in context).

### 1.3 Tests (new)

Add focused tests asserting code assignment per scenario (can extend
`_run_eligibility_checks` helper tests):

- threshold met / not met / school / public / no policy
- military vs other vs qualifying leave type
- work hours YES / NO / NOT_SURE / unknown
- hire date eligible / after leave / under 1 month / N months
- location US / non-US / 50-75 fail

**Phase 1 gate:**

```bash
pytest backend/legacy/tests/test_fmla.py -k "eligibility" -q
```

---

## Phase 2: Refactor `build_eligibility_messages()`

### 2.1 Create `ELIGIBILITY_MESSAGE_TEMPLATES: dict[str, Callable[[dict], str]]`

Pure mapping from code → sentence using `eligibility_message_context` only.

### 2.2 Rewrite `build_eligibility_messages()`

```python
def build_eligibility_messages(
    *, reasoning: FMLAReasoning, leave: Leave, policy: Policy | None
) -> list[str]:
    """Build ordered eligibility_reasons from reason codes. Does not set eligibility_desc."""
    return [
        ELIGIBILITY_MESSAGE_TEMPLATES[code](reasoning.eligibility_message_context)
        for code in reasoning.eligibility_reason_codes
    ]
```

- `_eligibility_heading()` stays (needs `leave` for type label +
  `reasoning.is_eligible()`)
- **Delete** (or reduce to thin wrappers used only by tests during migration):
  - `_company_eligibility_reasons`
  - `_leave_type_eligibility_message`
  - `_work_hours_eligibility_message`
  - `_hire_date_eligibility_message` (including `_hire_date_tenure_months` if
    only used here)
  - `_location_eligibility_message`

### 2.3 Update `is_leave_fmla_eligible()`

```python
reasoning.eligibility_reasons = build_eligibility_messages(
    reasoning=reasoning, leave=leave, policy=policy
)
# Do NOT set reasoning.eligibility_desc here
```

### 2.4 Unreachable code removal

| Removed guard                                        | Why unreachable                                                              |
| ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| `_hire_date_eligibility_message` `return ""`         | `test_hire_date` raises if hire_date / profile / expected_leave_date missing |
| `_location_eligibility_message` generic fallback     | All `location_eligible=False` paths covered by NON_US or 50_75_FAIL codes    |
| `_hire_date_tenure_months` None guards post-refactor | Tenure computed in `test_hire_date` only                                     |

Add explicit tests that each code path is reachable (negative test: assert
removed fallbacks are not in output).

**Phase 2 gate:**

```bash
pytest backend/legacy/tests/test_fmla.py -k "build_eligibility" -q
```

---

## Phase 3: Stop persisting `eligibility_desc`

### 3.1 Add assembly helper

```python
def assemble_eligibility_desc(*, reasoning: FMLAReasoning, leave: Leave) -> str:
    """Compose multi-line prose from heading + persisted reasons. Not stored."""
    if not reasoning.eligibility_reasons:
        # Backward compat: legacy rows may only have eligibility_desc
        return reasoning.eligibility_desc or ""
    heading = _eligibility_heading(reasoning=reasoning, leave=leave)
    return f"{heading}\n\n" + "\n".join(reasoning.eligibility_reasons)
```

### 3.2 Exclude `eligibility_desc` from persistence + fix change detection

**3.2a `to_dict()` exclusion**

```python
EXCLUDED_FROM_PERSISTENCE = frozenset({"eligibility_desc"})
DERIVED_ATTRS = frozenset({"eligibility_desc"})  # also excluded from __eq__
```

- **Do not** set `reasoning.eligibility_desc` in `is_leave_fmla_eligible()`
  after Phase 3
- On `FMLAReasoning.__init__` from dict: optionally skip hydrating
  `eligibility_desc` from stored JSON (stale derived state)

**3.2b `fmla_reasons_persisted_equal()` helper**

Compare normalized `to_dict()` output, ignoring:

- `determined_at` (always changes on recompute)
- `eligibility_desc` (derived; may exist on legacy rows only)

**Switch `update_leave_fmla()` to use this helper**, not `FMLAReasoning.__eq__`:

```python
if not fmla_reasons_persisted_equal(base_reasoning, new_reasoning):
    leave.fmla_reasons = new_reasoning.to_dict()
```

**3.2c Update `FMLAReasoning.__eq__`**

Exclude `DERIVED_ATTRS` from comparison so unit tests comparing
designation/boolean fields remain stable.

**New tests:**

- `test_update_leave_fmla_skips_save_when_only_eligibility_desc_differs`
- `test_fmla_reasons_persisted_equal_ignores_determined_at_and_eligibility_desc`
- Update `test_reasoning_eq` (line ~1246) for new fields / excluded attrs

### 3.3 Update read site: `backend/leaves/services/checks/leave.py`

```python
from legacy.fmla import FMLAReasoning, assemble_eligibility_desc

def is_fmla_leave(...):
    desc = "No reasoning available"
    if leave.fmla_reasons:
        reasoning = FMLAReasoning(leave.fmla_reasons)
        assembled = assemble_eligibility_desc(reasoning=reasoning, leave=leave)
        if assembled:
            desc = _(assembled)
    ...
```

### 3.4 API serializer backward compatibility (**required**)

**Key facts from audit:**

- DB stores snake_case keys; `CamelCaseJSONRenderer` camelizes HTTP responses
  (`eligibilityDesc`, `eligibilityReasons`)
- **Only `PlanAdminOutputSerializer`** exposes `fmla_reasons` to admin clients
  (Admin PDP mock reads plan payload)
- Leave create/patch serializers **exclude** `fmla_reasons` — do not inject
  there
- No production code reads `eligibility_reasons` from storage; only
  `eligibility_desc` (workflow check) — until Phase 3 switches check to assembly

Implementation — shared utility in `backend/legacy/fmla.py` or
`legacy/serializers/utils.py`:

```python
def enrich_fmla_reasons_for_api(fmla_reasons: dict, leave: Leave) -> dict:
    if not fmla_reasons:
        return fmla_reasons
    reasoning = fmla.FMLAReasoning(fmla_reasons)
    if "eligibility_desc" not in fmla_reasons:
        return {
            **fmla_reasons,
            "eligibility_desc": assemble_eligibility_desc(reasoning=reasoning, leave=leave),
        }
    return fmla_reasons
```

Apply in **`PlanAdminOutputSerializer.to_representation`** (needs `obj.leave`
for heading assembly).

**Caveat:** Plan snapshot `fmla_reasons` + live `leave` for heading can diverge
if leave type changed post-plan-creation. Document as known limitation;
backfill + forward fix (Phase 3.7) mitigates.

### 3.5 Update tests

| File                                                      | Changes                                                                                                                                                                                           |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/legacy/tests/test_fmla.py`                       | Assert `eligibility_desc` not in `to_dict()`; use `assemble_eligibility_desc()` for full prose assertions; replace `len(to_dict())` with `assert "eligibility_desc" not in d` + key subset checks |
| `backend/leaves/services/checks/tests/test_checks.py`     | Populate `eligibility_reasons` list instead of/in addition to `eligibility_desc`; assert assembled desc in workflow output                                                                        |
| `backend/leaves/services/tests/test_leave_eligibility.py` | Update fixture `fmla_reasons` setup                                                                                                                                                               |
| `frontend/client/__mocks__/AdminPDP/planData.ts`          | Document that `eligibilityDesc` is computed on API read (optional: remove from mock if serializer injects)                                                                                        |

### 3.7 Forward fix: `create_plan_from_leave` snapshot

**Problem:** `ensure_leave_fmla_reasons_exists` recomputes but only persists
when empty; `create_plan_from_leave` snapshots `leave.fmla_reasons`, not fresh
`fmla_reasoning.to_dict()`.

**Fix:**

```python
fmla_reasoning = ensure_leave_fmla_reasons_exists(leave=leave)
# ...
fmla_reasons=leave.fmla_reasons or (fmla_reasoning.to_dict() if fmla_reasoning else {}),
```

Prefer `fmla_reasoning.to_dict()` when computation succeeded (even if leave had
stale non-empty JSON).

**Update** `test_create_plan_from_leave` if it asserts stale partial dicts
survive.

**Acceptance:** New plan from leave with stale non-empty `fmla_reasons` gets
fresh `plan.fmla_reasons`.

### 3.8 Align `ensure_leave_fmla_reasons_exists` error handling

Wrap `is_leave_fmla_eligible` in `try/except ValueError` (match
`update_leave_fmla`); return stored reasoning or `None` on failure. Prevents
`create_plan_from_leave` crash on missing hire date.

**New test:** `test_create_plan_from_leave_survives_missing_hire_date`

### 3.9 Clean up dummy `eligibility_desc = ""` assignments

These clear desc for boolean-only preview paths — verify still needed after
refactor:

- `backend/legacy/serializers/users.py` (lines ~374, 906, 1041)
- `backend/legacy/views/users.py` (line ~782)

**Phase 3 gate:**

```bash
pytest backend/legacy/tests/test_fmla.py backend/leaves/services/checks/tests/test_checks.py -q
```

---

## Phase 4: Stale data refresh (optional but recommended)

### 4.1 Management command: `refresh_fmla_reasons`

```
backend/legacy/management/commands/refresh_fmla_reasons.py
```

**Arguments:**

| Flag              | Purpose                                                             |
| ----------------- | ------------------------------------------------------------------- |
| `--dry-run`       | Print counts + sample diffs; default **True** for safety            |
| `--execute`       | Actually persist (mutually exclusive with dry-run default)          |
| `--company-id`    | Scope to company                                                    |
| `--leave-id`      | Scope to single leave                                               |
| `--include-plans` | Also update `plan.fmla_reasons` for associated plans (default True) |

**Logic per leave:**

1. Skip if leave has no `historical_profile` (log warning)
2. Run `is_leave_fmla_eligible(leave=leave)` inside `try/except ValueError` —
   **do not clear** existing `fmla_reasons` on failure (match
   `update_leave_fmla`)
3. Compare via `fmla_reasons_persisted_equal()` (ignore `determined_at`,
   `eligibility_desc`)
4. If changed: update `leave.fmla`, `leave.fmla_reasons`
5. If `leave.plan_id`: compare normalized `plan.fmla_reasons` vs new leave dict;
   update `plan.fmla` + `plan.fmla_reasons` when different (mirror
   `get_task_tag_for_fmla_doc_generation`)
6. Idempotent: second run produces no writes

**Additional flags:**

| Flag                  | Purpose                                                |
| --------------------- | ------------------------------------------------------ |
| `--plan-id`           | Spot-check single plan                                 |
| `--resync-plans-only` | Skip leave recompute; copy leave → plan when divergent |

**Stale detection heuristic** (for dry-run reporting):

- `eligibility_reasons` contains `[` (bracket notation)
- `eligibility_desc` present but `eligibility_reasons` empty
- `eligibility_reason_codes` missing (post-Phase 1)

**Dry-run output buckets:** `leaves_updated`, `plans_updated`,
`plans_resynced_from_leave`, `skipped_prerequisites`, `skipped_no_profile`

**Affected populations** (from ticket):

| Path                                 | Rewrites today?             | After command                       |
| ------------------------------------ | --------------------------- | ----------------------------------- |
| `update_leave_fmla()`                | Yes, when reasoning changes | Unchanged                           |
| `ensure_leave_fmla_reasons_exists()` | Only if empty               | Unchanged — command is separate     |
| `PlanViewSet.generate_documents()`   | Only if empty               | Unchanged                           |
| `create_plan_from_leave()`           | Snapshots leave             | Refreshed leaves → better snapshots |
| Draft / rejected / stale approved    | **No**                      | **Command target**                  |

### 4.2 Command tests

- Dry-run does not save
- Execute updates leave + plan
- Idempotent second execute
- `--leave-id` scopes correctly
- Leaves missing required fields skipped without crash

**Phase 4 gate:**

```bash
pytest backend/legacy/management/commands/tests/test_refresh_fmla_reasons.py -q
```

---

## Acceptance criteria checklist

| Criterion                                              | How to verify                                                                                  |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `eligibility_desc` not persisted in new `fmla_reasons` | `assert "eligibility_desc" not in reasoning.to_dict()`                                         |
| `is_fmla_leave` displays correct multi-line prose      | `test_checks.py::test_is_fmla_leave` with `eligibility_reasons` fixture                        |
| Formatter uses reason codes, not leave re-inspection   | Code review + no `leave.historical_profile` reads in `build_eligibility_messages`              |
| Unreachable formatter guards removed                   | Grep confirms deletion; explicit reachability tests per code                                   |
| Stale data decision documented                         | PR description + Phase 4 command or explicit "no backfill"                                     |
| Backfill command (if added)                            | Dry-run default, idempotent, leave + plan                                                      |
| No regression                                          | `pytest backend/legacy/tests/test_fmla.py backend/leaves/services/checks/tests/test_checks.py` |

---

## Files to modify

```
# Phase 1–3 (required)
backend/legacy/fmla.py
backend/leaves/services/checks/leave.py
backend/legacy/tests/test_fmla.py
backend/leaves/services/checks/tests/test_checks.py
backend/leaves/services/tests/test_leave_eligibility.py

# Phase 3 (required)
backend/legacy/serializers/plans.py     # PlanAdminOutputSerializer enrich
backend/legacy/services/plans.py        # create_plan_from_leave snapshot fix
backend/legacy/services/leaves/fmla.py  # fmla_reasons_persisted_equal in update_leave_fmla
frontend/client/__mocks__/AdminPDP/planData.ts

# Phase 3 (cleanup verify)
backend/legacy/serializers/users.py
backend/legacy/views/users.py

# Phase 4 (optional)
backend/legacy/management/commands/refresh_fmla_reasons.py
backend/legacy/management/commands/tests/test_refresh_fmla_reasons.py
```

---

## Verification commands

```bash
# Core regression
pytest backend/legacy/tests/test_fmla.py -q
pytest backend/leaves/services/checks/tests/test_checks.py -q

# Grep guards
rg 'eligibility_desc' backend/legacy/fmla.py backend/leaves/services/checks/leave.py
rg '_location_eligibility_message|_hire_date_eligibility_message' backend/legacy/fmla.py  # should be gone post-Phase 2

# Persistence check (manual / test)
python -c "
from legacy.fmla import FMLAReasoning
r = FMLAReasoning()
r.eligibility_desc = 'should not persist'
assert 'eligibility_desc' not in r.to_dict()
"

# Backfill dry-run (Phase 4)
python manage.py refresh_fmla_reasons --dry-run --company-id=<id>
```

---

## Risks and mitigations

| Risk                                                     | Mitigation                                                                                                       |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| API clients read `fmlaReasons.eligibilityDesc` from JSON | **Required** `PlanAdminOutputSerializer` inject (Phase 3.4)                                                      |
| Stale bracket `eligibility_reasons` on old leaves        | Phase 4 backfill; assembly fallback to legacy `eligibility_desc` if reasons empty                                |
| `test_hire_date` raises → no hire-date line in reasons   | Intentional; callers catch `ValueError` (`update_leave_fmla`, `ensure_*`, backfill)                              |
| `len(to_dict())` test breakage                           | Replace with semantic assertions                                                                                 |
| `update_leave_fmla` spurious saves                       | `fmla_reasons_persisted_equal()` (Phase 3.2b) — **not** raw `__eq__`                                             |
| First deploy writes when new code fields appear          | Expected one-time migration when `eligibility_reason_codes` added; distinct from desc false-positive             |
| Plan/leave heading vs reasons mismatch                   | Document limitation; Phase 3.7 + backfill mitigate                                                               |
| `leave.fmla` null vs "undetermined" heading              | Pre-existing; out of scope — `is_fmla_leave` uses boolean, heading can say "could not be determined"             |
| Additional persist paths                                 | `leave_states.py:71`, `get_task_tag_for_fmla_doc_generation` — all use `to_dict()`; fixed centrally by Phase 3.2 |

---

## Out of scope

| Item                                   | Notes                          |
| -------------------------------------- | ------------------------------ |
| `backend/benefits/rules/fmla.py`       | Benefits rules engine messages |
| `designation_desc` / med-cert copy     | Separate concern               |
| FMLA eligibility notice PDF template   | Separate concern               |
| `check_employee_count()` wiring        | Deleted in PIE-115             |
| Changing when `update_leave_fmla` runs | Status gating unchanged        |

---

## Rollback plan

Revert the PR. No migrations. Legacy `fmla_reasons` rows retain
`eligibility_desc` key; `assemble_eligibility_desc` fallback keeps workflow
checks working on old data.

---

## Review checklist (plan author)

- [x] Production readers audited (3-agent pageant, 2026-09-15)
- [x] Reason code taxonomy covers all PIE-115 test scenarios
- [x] Serializer/API risk documented (`PlanAdminOutputSerializer` only)
- [x] `__eq__` / `update_leave_fmla` → concrete `fmla_reasons_persisted_equal()`
      gate
- [x] Handoff prompt included
- [x] Pageant review rounds incorporated

---

## Pageant review log (3 rounds, 2026-09-15)

### Round 1 — Implementation gap review ([265eb205](265eb205-cfbb-472c-8e4c-8dfd9cc886e5))

| Severity | Finding                                                                | Resolution                                   |
| -------- | ---------------------------------------------------------------------- | -------------------------------------------- |
| Critical | `__eq__` must be fixed before merge                                    | Phase 3.2b/c + tests                         |
| Critical | Serializer scope wrong (`LeaveOutputSerializer` has no `fmla_reasons`) | Phase 3.4 → `PlanAdminOutputSerializer` only |
| Critical | Company "always 2 codes" wrong for no-policy                           | Reason code design corrected                 |
| Medium   | Military/OTHER branching missing from `test_leave_type`                | Phase 1.2 explicit branch                    |
| Medium   | Hire-date sub-code ordering unspecified                                | Phase 1.2 branch order documented            |
| Medium   | `_run_eligibility_checks` still unpacks tuple                          | Added to Phase 3.5 test updates              |

### Round 2 — Consumer audit ([c94c6613](c94c6613-d976-43aa-95cf-7cddae698775))

| Finding                                                                  | Resolution                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------- |
| Only `checks/leave.py` reads `eligibility_desc` for logic — **verified** | Unchanged                                               |
| No production reader of `eligibility_reasons`                            | Assembly uses persisted list; codes are forward-looking |
| `leave_states.py:71` persist path missing                                | Added to risks table                                    |
| CamelCase via renderer, not serializer                                   | Documented in Phase 3.4                                 |
| Integration API does not expose `fmla_reasons`                           | Out of scope confirmed                                  |

### Round 3 — Equality / backfill / plan snapshot ([39c622ad](39c622ad-e477-461c-a49c-687f7df908bc))

| Finding                                                       | Resolution              |
| ------------------------------------------------------------- | ----------------------- |
| `create_plan_from_leave` snapshots stale `leave.fmla_reasons` | Phase 3.7 forward fix   |
| `ensure_*` lacks `ValueError` handling                        | Phase 3.8               |
| Backfill must resync plans + `--resync-plans-only`            | Phase 4 expanded        |
| Stale detection heuristic                                     | Phase 4 dry-run buckets |
