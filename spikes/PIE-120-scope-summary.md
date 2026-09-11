# PIE-120: Humanize Missing Data Messages

## What we're fixing

When required data is missing, benefit and document rules show messages like
`Missing expected_due_date` or `Missing EE hire date`. These use internal field
names and abbreviations. PIE-120 replaces them with plain, actionable sentences.

The messages are built in one place (`BaseRule` in
`backend/benefits/rules/__init__.py`) and then surfaced through API reasoning,
`reasons_ineligible`, Admin plan UI, and document suggestions.

---

## How big is this?

Mostly backend, with a small frontend pass.

| Area                                              | Scale                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------- |
| Framework changes                                 | 4 code paths in `__init__.py`                                             |
| Check definitions (`Requirement.desc`)            | ~75 instances across checks modules (plus 7 in `leaves/services/checks/`) |
| Direct `require()` in state/document rules        | ~274 production calls across ~46 files                                    |
| `require()` calls missing a `description=`        | 26 (will fall back to Python function names)                              |
| `Checkable` usages (fixed by updating checks)     | ~486                                                                      |
| Backend tests that assert `"Missing "` strings    | ~30 files                                                                 |
| Frontend sites that detect missing data by string | 2 (`EligibleBenefitsSection.tsx`, `suggestedBenefits.ts`)                 |

Changing the message format in `require()` alone is not enough. Without updating
descriptions, users would still see things like
`expected_due_date has not been provided.`

---

## Where messages come from

Four places in `BaseRule` produce text starting with `Missing`:

1. **`require()`** (~line 742): `Missing {description}` when a required value is
   empty. Multiple arguments add a `(variable N)` suffix.
2. **`__call_compute()`** (~line 593): `Missing {description} (result)` when an
   expression returns `None`.
3. **`get_result_for()`** (~line 1055): `Missing result for {RuleName}` when a
   dependency result is absent.
4. **Schedule helper** (~line 3769): `Missing schedule time including {date}`.

Most humanization work targets (1) and (2). The others may be a follow-up.

### How the pieces connect

- `Requirement(value, desc)` describes a value that must be present.
- `requires(*reqs)` loops over requirements and calls `require()`.
- `Checkable` (in `checks/base.py`) runs a check, calls `describe()`, then
  `requires(*check.reqs)`.

You do **not** need to edit every `requires()` call. Updating `Requirement.desc`
in the check functions fixes all rules that use that check via `Checkable`.

Both `BaseBenefitRule` and `BaseDocumentRule` share this machinery. Document
rules can produce messages like `Missing published paycalc` through the same
path.

### Checks files with `Requirement` definitions

- `checks/employee.py` (19)
- `checks/leave.py` (13)
- `checks/paycalc.py` (4)
- `checks/benefit.py` (3)
- `checks/schedule.py` (2)
- `checks/company.py` (uses `Requirement.get()` in 4 places)

`checks/dependent.py` does not use `Requirement`; it uses `get_result_for()`
instead.

---

## Spike questions answered

### Q1: Is all reasoning on the MissingValue path meant for end users?

**No.**

`MissingValue` is how the rule engine aborts an expression when data is
incomplete. The reasoning string recorded before the exception is not always
shown to users.

**Surfaces that do show missing-data text to users:**

| Surface                        | Where it reads from          | How it finds missing data                          |
| ------------------------------ | ---------------------------- | -------------------------------------------------- |
| `reasons_ineligible`           | `reasoning.eligible`         | `startswith("Missing ")` when `passed` is null     |
| Benefit reasoning API          | Most categories              | Filtered, but keeps most eligible/awake/spans text |
| Admin PDP yellow tooltip       | `reasoning.spans`            | Case-insensitive `.includes('missing')`            |
| Leave Management "Not Applied" | `reasoning.spans` (fallback) | Same substring check in `suggestedBenefits.ts`     |
| Document suggestions           | `reasoning.required`         | `startswith("Missing")`                            |

**Examples that are not straightforward user copy:**

- `Missing result for WashingtonPFMLPaidBenefit` (internal rule names)
- `Missing approval_document_config` (filtered out as internal)
- `Found result for …` and feature-flag rollout strings (filtered)
- `_final_reason()` messages like `Deferred to benefit template` (internal span
  logic)
- `Missing definitive FMLA eligibility when 50/75 rule is enforced`
  (intentional, uses `_final_reason`)

Also note: `get_reasons_ineligible` only looks at the `eligible` category.
Missing data recorded under `awake`, `spans`, or `required` follows different UI
paths.

**Takeaway:** Treat `require()` and the `(result)` path as user-facing by
default. Audit the other `Missing*` paths separately; some need better copy,
some should stay internal.

---

### Q2: Do we have to touch every `requires()` call and every `Requirement`?

**No for `requires()`. Yes for content, if we want complete coverage.**

| If we only change…              | What unvisited code still does                                                        |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| Framework format string         | New suffix, old bad labels (`expected_due_date has not been provided.`)               |
| Checks layer only               | Fixes ~486 `Checkable` paths; leaves ~46 rule files with direct `require()` untouched |
| Framework + checks + rule audit | Meets acceptance criteria                                                             |

**Fallback today:** if `require()` gets no `description=`, it uses the
expression's `describe()` text, or the Python function name. That is how you get
`Missing blank_require_description` in tests.

**`Requirement` without `desc`:** falls back to the check's main `desc`, which
is usually an eligibility sentence, not a missing-field label.

**Plan (Option A from the ticket):**

1. Change the format in `require()` and the `(result)` path.
2. Rewrite `Requirement.desc` in all checks modules (and decide on
   `leaves/services/checks/`).
3. Audit direct `require()` calls in ~46 rule files.
4. Add `desc` to `Requirement.get()` calls that lack it.
5. Skip individual `requires()` call sites.

---

### Q3: Do callers need custom descriptions? How do we prevent regressions?

**Yes, for good UX.** The framework does not require human descriptions today.

With a format like `{description} has not been provided.`:

- Good: `Requirement(leave.expected_due_date, "The expected due date")`
- Bad: `self.require(leave.expected_due_date)` with no description (function
  name becomes the label)
- Bad: `Requirement(leave.leave_type)` with no desc (eligibility wording, not a
  field label)

**Test gaps:**

- No repo-wide check that every `require()` has a readable description.
- `DEBUG` already requires `desc_false` on `Check`, but not `Requirement.desc`.
- Many rule tests lock in exact `"Missing …"` strings and will need updates.

**Suggested guardrails:**

1. DEBUG-time validation on `Requirement.desc` (same idea as `Check`).
2. Optional CI script for `require()` without `description=`, or `Requirement` /
   `Requirement.get` without `desc`.
3. Extend `test_missing_data` patterns from `checks/tests/test_employee.py` to
   other check modules.
4. Do not try to cover every state rule in unit tests; lean on checks-layer
   tests plus spot checks from the rewrite table.

---

### Q4: Does the frontend need a new way to detect missing-data reasoning?

**Yes**, if we drop the `Missing` prefix.

**Backend:**

- `get_reasons_ineligible` in `results.py` uses `startswith("Missing ")`.
- `get_reasons_suggested` in `documents/serializers.py` uses
  `startswith("Missing")`.
- `_normalize_ineligible_reason` strips `(variable N)` suffixes.

**Frontend:**

- `formatMissingReasoningStrings` in `EligibleBenefitsSection.tsx` filters
  `reasoning.spans` with `.includes('missing')`.
- `formatMissingSpanReasons` in `suggestedBenefits.ts` does the same for the
  "Not Applied" copy.

**Important split:**

- Missing data in `reasoning.eligible` becomes `reasonsIneligible` (ineligible
  sidebar, HR drawer, etc.).
- Missing data in `reasoning.spans` drives the yellow "Missing Requirements"
  tooltip on eligible benefits with no paycalc items.

`IBenefitResultVM` already has a `missing_data` boolean in types, but nothing in
the UI reads it yet.

**If we remove the prefix without updating detection:**

- Messages that no longer contain the word "missing" will disappear from the
  yellow tooltip.
- `reasonsIneligible` paths keep working only if we update
  `get_reasons_ineligible` to match the new format.

**Options to decide on:**

1. Structured reasoning (`kind: "missing_data"`) or wire up the existing
   `missing_data` flag.
2. Dual-match during migration (old prefix + new sentence pattern).
3. Point the eligible-section tooltip at `reasonsIneligible` instead of scanning
   spans.

At minimum, update `get_reasons_ineligible`, `get_reasons_suggested`,
`formatMissingReasoningStrings`, and `formatMissingSpanReasons` together.

---

## Suggested implementation phases

### Phase 1: Framework

- New message format in `require()`; drop `(variable N)` suffix (or merge
  multi-field messages per ticket notes).
- Humanize the `(result)` path in `__call_compute()`.
- Update `get_reasons_ineligible()` detection.
- Update `get_reasons_suggested()` in document serializers.
- Fix tests in `test_results.py` and `test_serializers.py`.

### Phase 2: Checks layer

- Rewrite `Requirement.desc` in employee, leave, paycalc, benefit, schedule,
  company checks.
- Fill in missing `desc` on `Requirement.get()` calls.
- Confirm whether `leaves/services/checks/` is in scope.
- Reuse phrasing from `checks/messages.py` where it helps.

### Phase 3: Rule file audit

- ~46 files with direct `require()` outside checks.
- Start with the 26 calls that have no `description=`.
- Then snake_case labels, `EE` jargon, and document rules.

### Phase 4: Frontend

- `EligibleBenefitsSection.tsx` and `suggestedBenefits.ts`.
- Optionally wire `missing_data` on the benefit result type.
- Update mocks and tests that hardcode `"Missing "` strings.

### Phase 5: Guardrails

- DEBUG validation for `Requirement.desc`.
- Optional CI grep for unlabeled `require()` calls.

### Likely follow-ups

- `Missing result for {RuleName}` from `get_result_for()`.
- `Missing schedule time including {iso-date}`.
- Rules Builder `missing_data_point` catalog entries (engineering gaps, not
  runtime copy).
- Deduping duplicate messages across states (can happen during Phase 3).

---

## Acceptance criteria checklist

| Criterion                              | Where it gets done                      |
| -------------------------------------- | --------------------------------------- |
| No internal variable names in messages | Phases 2 and 3                          |
| No `EE` abbreviation                   | Phases 2 and 3                          |
| Complete sentences                     | Phase 1 format + Phases 2 and 3 content |
| Consolidate duplicate messages         | Phase 2 shared copy + Phase 3 dedup     |
| `get_reasons_ineligible()` still works | Phase 1                                 |
| No `(variable N)` suffixes             | Phase 1                                 |

---

## Files to know

```
backend/benefits/rules/__init__.py
backend/benefits/rules/checks/base.py
backend/benefits/services/results.py
backend/benefits/serializers.py
backend/documents/serializers.py
frontend/.../EligibleBenefitsSection.tsx
frontend/client/utils/suggestedBenefits.ts
```

---

## Decisions before we start

1. Structured metadata (`missing_data` flag or `ReasoningEntry.kind`) vs.
   matching on a new sentence pattern?
2. Should the Admin PDP tooltip use `reasonsIneligible` or `missing_data`
   instead of scanning spans?
3. Are `get_result_for` and schedule missing messages in scope for this ticket?
4. Should missing `Requirement.desc` fail in DEBUG, or only warn?
5. Is `leaves/services/checks/` part of the same description pass?

---

## Recommendation

Use **Option A** from the ticket: update descriptions at the source plus a
central format change in `require()`. A centralized field-name mapping layer
would duplicate what `Requirement.desc` already does and would still miss direct
`require()` calls in state rules.
