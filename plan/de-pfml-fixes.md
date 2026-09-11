# DE PFML BKE Fixes — Work Plan

**Status:** Revised after review (round 6) — ready to execute after Phase 0 CI
green + same-PR coordination\
**Context:** BKE testing (Christian Castorena) flagged five DE PFML issues
blocking further test coverage.\
**Primary code:** `backend/benefits/rules/delaware/pfml.py`\
**Regulatory reference:** Delaware PFML Duration of Benefits (§ 4.0–4.1.4) and
State confirmation email (screenshots in BKE thread)

---

## Executive summary

| Priority                             | §Issue                       | Disposition                                                                                                                       |
| ------------------------------------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Phase 0 — single deployable unit** | §Issue 2 (CI) + **§Issue 5** | [#11710](https://github.com/ourtilt/tilt-repo/pull/11710) **OPEN, CI red** — same **PR/merge batch** as §Issue 5 bonding override |
| Phase 1a / 1b (parallel)             | §Issue 3 / §Issue 1          | QE gates; exclusion display investigation                                                                                         |
| Phase 2                              | §Issue 4                     | WAD default                                                                                                                       |

**Bottom line:** Phase 0 = **CI-green MTW fixture fix** (#11710) +
**`get_global_bonding_min_start_date` override** on `DelawarePFMLPaidParental`
(§Issue 5). `copy_benefit_spans` and `de_duration_in_working_days` on paid
children **already exist on main** — do not re-land that logic. Birthing JP
regresses today when paid spans copy without the bonding fix. §Issue 1:
investigation-first; no serializer changes.

---

## Background

### DE PFML rules (encoded in `pfml.py`)

- Parental: 12w per application year (forward from first parental use)
- Non-parental: 6w each in 24-month windows (independent anchors)
- Combined annual ceiling: 12w all reasons
- Multiple qualifying events allowed
- Birthing: paid + JP concurrent from leave start (**§Issue 5 =
  `DelawarePFMLPaidParental` child only**; parent bank GENERIC unaffected)

### Architecture

```
Paid Parental child  — PARENTAL_BONDING  → bonding delay (§Issue 5)
Paid Parent bank     — GENERIC
JP Family / Medical  — GENERIC or paid-span gate; omit shared_eligible
```

### Already on main (not Phase 0 net-new logic)

- `copy_benefit_spans` on `DelawarePFMLJobProtection.calculate_spans`
  (~line 922)
- `de_duration_in_working_days = True` on paid **child** rules; `False` on
  parent bank

Phase 0 open work: **MTW test CI fixture** + **§Issue 5 bonding override**.

### Feature flags

Both `enableBKEDelawarePFML` and `enableDEPfmlTracking` required for BKE parity.

---

## Phase 0: #11710 (CI) + §Issue 5 (one PR / merge batch)

### Merge gate

- [ ] **Single PR or same merge-queue batch** (#11710 CI fixes + §Issue 5
      override)
- [ ] **CI green on latest PR head**
- [ ] Both DE PFML flags; child + JP templates provisioned in BKE env
- [ ] Mon/Tue/Fri: Paid == JP == 18 working days
- [ ] Birthing EDD = leave start: paid span == JP span == EDD

### Birthing JP regression (why same batch)

| State                                | JP Family birthing             | Paid Parental      |
| ------------------------------------ | ------------------------------ | ------------------ |
| Main today (copy spans, no §Issue 5) | Inherits paid bonding start ❌ | Post-disability ❌ |
| After §Issue 5 only                  | Matches paid ✅                | EDD ✅             |

`copy_benefit_spans` is already on main — birthing JP is **already at risk**
once paid child evaluates; §Issue 5 fixes paid start so copy produces correct
JP.

---

## Issue 2: Working-day mismatch — PR #11710 (CI blocker)

### Status: OPEN, CI red

`TestPaidAndJobProtectionWorkingDayAlignment::test_parental_paid_and_jp_match_after_mtw_medical_prior`:

```
Leave time is greater than work time on 2026-02-04
```

**CI root cause:** stale schedule from **`de_pfml_eligible_leave`** (Feb 2026),
not Aug 2026 test dates. Failing test may only soft-delete `LEAVE_REGULAR` —
**stale `WORK_REGULAR` / other rows** can still cause Feb 2026 conflict.

### Required fixture fix (prefer option 1)

1. **Delete all `ScheduleDay` rows** on the leave before MTW setup — not only
   `LEAVE_REGULAR`
2. Dedicated MTW fixture (no Feb inherit from `de_pfml_eligible_leave`)
3. Assert duration/spans only after fully isolated setup

### #11710 scope on branch (don't duplicate main)

Working-day prior usage + SpanLimiter path may still differ on branch vs main —
merge for **test + any remaining utils fixes**. Span copy / child
`de_duration_in_working_days` flags are **already on main**.

### Files

- `backend/benefits/rules/delaware/tests/test_pfml.py` (primary CI fix)
- Possibly `backend/benefits/rules/utils.py` if branch has additional prior-day
  logic

---

## Issue 5: Birthing paid starts at bonding (Phase 0 — ships with #11710)

### Mechanism

`PARENTAL_BONDING` → `get_min_start_date` →
`max(ANY EDD, BONDING post-disability) = post-disability`.

### Fix — override on `DelawarePFMLPaidParental`

**Mandatory decorators (both):**

1. `@leave_type_register(types=[Leave.LeaveType.PARENTAL])` — without
   re-registering on subclass, override may not participate in consolidation (WI
   includes this)
2. `@span_date_requirement(..., grouping=DateGrouping.BONDING)`

**Mandatory:** `self.require(leave.expected_due_date, ...)` before return (WI
pattern) — missing EDD fails cleanly.

```python
from documents.selectors import accepted_med_certs
from benefits.rules import DateGrouping, DateRequirementType, DateBoundary, leave_type_register

@leave_type_register(types=[Leave.LeaveType.PARENTAL])
@span_date_requirement(
    req_type=DateRequirementType.START,
    order=DateBoundary.NORMAL,
    grouping=DateGrouping.BONDING,
)
def get_global_bonding_min_start_date(self, leave: Leave) -> date:
    self.require(leave.expected_due_date, description="expected due date")
    if leave.is_parental_birthing and not accepted_med_certs(leave).exists():
        self.reason("DE PFML birthing parental runs from expected due date")
        return leave.expected_due_date
    return super().get_global_bonding_min_start_date(leave)
```

Reference: **WI FMLA** `get_global_bonding_min_start_date` (~549). CO FAMLI for
pre-EDD **span** split only.

### Birthing start edge cases

| Scenario                               | Expected paid start        | Fix                               |
| -------------------------------------- | -------------------------- | --------------------------------- |
| EDD = leave start, no cert (Christian) | EDD                        | Override sufficient               |
| Leave start before EDD, no cert        | EDD only (no pre-EDD paid) | Override returns EDD; confirm L&C |
| Leave start before EDD, with med cert  | Pre-EDD via cert           | CO FAMLI span split — separate    |
| Non-birthing                           | EDD                        | `super()`                         |

### Test migration — full BKE fixture stack

Tests today use `DelawarePFMLPaidBenefit` + often only
`template_de_pfml_income_replacement` / `enable_de_pfml` — **insufficient**.

**Every migrated birthing test must use:**

- `enable_de_pfml_tracking`
- `template_de_pfml_paid_children`
- `template_de_pfml_job_protection_children` (for JP span alignment)
- **`DelawarePFMLPaidParental`** (not parent bank)

**Migrate:**

- `test_pre_edd_med_cert_time_is_covered`
- `test_birthing_parental_with_med_cert_can_advance_start_date`
- `test_birthing_parental_without_med_cert_cannot_advance_start_date`

**New test:** birthing EDD = leave start — set `parental_role=BIRTHING`,
`is_pregnant=True`, birth type fields; assert `get_min_start_date == EDD`
**and** paid span start == JP span start == EDD.

---

## Issue 1: Exclusion — investigate display staleness (Phase 1b)

### Expected

Paid rules: `employee_not_excluded` in `shared_eligible` → ineligible with
exclusion reasoning.

JP rules (`DelawarePFMLJobProtectionFamily`,
**`DelawarePFMLJobProtectionMedical`**, parent
**`DelawarePFMLJobProtectionBenefit`**) omit `shared_eligible` — gate on paid
spans. After exclusion, paid has no spans → JP ineligible with **“matching paid
… has no spans”**, not exclusion text. **Tests: assert `eligible=False` + no
spans for JP — do not assert exclusion message on JP.**

Confirm **employee** exclusion, not company `de_pfml_exempt`.

### Not the bug

- Serializer pop + `validated_data_copy` → `profile_update` on
  `LeaveHrViewSet.perform_update`
- Manual rule re-run (`run_rules_on_leave_change`)
- HR **create**: `perform_create` copies `validated_data` before pop — same as
  PATCH; create-with-exclusion is lower risk than display staleness

### UI investigation — nuance refetch

`LeaveDetailsTab` **does** invalidate benefit results on HR edit success:

```81:87:frontend/client/screens/Admin/PlanDetailsPage/Tabs/LeaveDetailsTab/LeaveDetailsTab.tsx
onSuccess: (...) => {
  queryClient.invalidateQueries([QueryKeys.BenefitResults]);
```

Investigation should distinguish:

| Case                                 | Action                                                             |
| ------------------------------------ | ------------------------------------------------------------------ |
| Invalidation runs but UI still stale | Race, inactive query, different edit surface (not LeaveDetailsTab) |
| Persistence failure                  | Profile field never saved                                          |
| Ineligible section with reasons      | **WAD** — tester expects hidden                                    |
| Eligible section still shows DE PFML | Stale cache or rules didn't re-run                                 |

### `PlanBenefitsCard` filters

- **Eligible:** `benefit.eligible`
- **Ineligible:** `!eligible && reasonsIneligible?.length > 0`
- **Neither:** undetermined/asleep with empty reasons

### Save paths

| Path                                                           | Persists? | Test                                |
| -------------------------------------------------------------- | --------- | ----------------------------------- |
| HR PATCH — `LeaveHrViewSet` + `HRPartialUpdateLeaveSerializer` | ✅        | `test_leave_hr_viewsets.py`         |
| HR PUT — read-only                                             | ❌        | Confirm BKE path                    |
| HR create                                                      | ✅        | Lower priority                      |
| Survey PATCH — `PROFILE_FIELDS`                                | ✅        | New test in `backend/leaves/tests/` |

### Integration tests

1. `test_leave_hr_viewsets.py` — unmocked PATCH
2. Survey PATCH integration test
3. After PATCH, assert ineligible / no spans on:
   - `DelawarePFMLPaidParental`, `DelawarePFMLPaidBenefit`,
     `DelawarePFMLPaidMedical`
   - `DelawarePFMLJobProtectionFamily`, **`DelawarePFMLJobProtectionMedical`**,
     **`DelawarePFMLJobProtectionBenefit`**
4. Paid rules: assert exclusion in reasoning; JP: assert ineligible only

### Acceptance criteria

- [ ] HR PATCH + survey PATCH tests pass
- [ ] Paid child/parent ineligible with exclusion reasoning; JP ineligible
      without exclusion wording
- [ ] Sidebar **eligible** section empty (investigate if invalidation present
      but stale)
- [ ] Manual BKE: paycalc removal prompt for ineligible on working paycalc
- [ ] Employee exclusion (not company exempt)

---

## Issue 3: Military QE gates (Phase 1a)

### Define once on `DelawarePFML`

Add `military_qualifying_exigency` on **`DelawarePFML` base class** (WA pattern:
individual Checkables + composed expression on base, ~123–153 in
`washington/pfml.py`). Import constants from `fmla.py`.

Then AND into (**required**):

- `DelawarePFMLPaidMilitary.eligible`
- `DelawarePFMLPaidBenefit.eligible` (pre-provisioning)

JP explicit QE gate optional — paid span gate sufficient.

### R&R 15-day cap — Phase 1a merge gate

WA uses **15 calendar days** (`timedelta(days=15)`). DE paid children use
**`de_duration_in_working_days = True`** — copying WA's `get_base_max_duration`
verbatim may cap R&R at **15 working days** after SpanLimiter, not 15 calendar.

**Required before Phase 1a merge:**

- L&C decision: **calendar vs working** for DE R&R cap
- Test on **MTW schedule** with explicit assertion (not WA calendar-only test
  copy)
- Use `_is_rest_and_recuperation_qe` from `fmla.py` + cap logic aligned to
  decision

### `leave_type_details is None`

May yield **UNDETERMINED** — assert explicitly after checking framework (not
assumed ineligible).

### `time_off_reason.OTHER`

FMLA set includes it — importing wholesale **allows** it unless excluded. **L&C
gate before merge** if excluding. Document DE reg if different from FMLA.

### Tests — explicit breakage list

These **will break** when QE gates land (update before Phase 1a merge):

- **`test_family_child_covers_each_family_reason`** — military param (~2481), no
  `leave_type_details`
- **`test_military_no_prior_leave`**
- Any test using random `LeaveType.MILITARY` from conftest (~line 111 in
  `conftest.py`)

**Required:**

1. `valid_military_qe_leave` fixture
2. Update parametrized JP military test + `test_military_no_prior_leave`
3. Pin/split `de_pfml_eligible_leave` — stop `random.choice` on leave types for
   military-sensitive suites
4. Negatives: `SERVING`, **`MilitaryLeaveMilitaryType.OTHER`**,
   `leave_type_details is None`

### Acceptance criteria

- [ ] QE gates on child + parent paid rules
- [ ] R&R cap: L&C unit decision + MTW test **or** documented deferral
- [ ] Listed existing tests updated; Phase 1a CI green

---

## Issue 4: Parental application year — WAD

`test_full_usage_then_new_period_restores_entitlement` in `test_pfml.py` (~1175)
encodes Christian Leave 3 behavior. No code change unless L&C overrides.

---

## Implementation order

| Phase  | Work                                                        |
| ------ | ----------------------------------------------------------- |
| **0**  | One PR: #11710 CI fixture green + §Issue 5 bonding override |
| **1a** | §Issue 3 (parallel with 1b)                                 |
| **1b** | §Issue 1                                                    |
| **2**  | §Issue 4 WAD communication + full BKE sign-off              |

---

## Manual BKE checklist

**After Phase 0**

1. Birthing EDD = leave start — paid == JP == EDD
2. Mon/Tue/Fri medical → parental — 18 working days

**After Phase 1a**

3. Military own service + `military_type.OTHER`

**After Phase 1b**

4. Exclusion HR PATCH — eligible section empty; ineligible section / paycalc
   prompt

**After Phase 2**

5. Three-leave sequence — WAD for Leave 3

---

## Christian sign-off

| Milestone                    | Criteria                                           |
| ---------------------------- | -------------------------------------------------- |
| Partial (Phases 0 + 1a + 1b) | Items 1–4 above                                    |
| Full                         | Item 5 (§Issue 4 WAD) + L&C confirmation if needed |

---

## Out of scope

- Employer Onboarding Survey error
- Leave map calendar-day labels
- Company `de_pfml_exempt` (verify employee exclusion)
- Pre-provisioning parent-bank calendar drift

---

## References

| Resource                                     | Location                                                     |
| -------------------------------------------- | ------------------------------------------------------------ |
| DE PFML rules                                | `backend/benefits/rules/delaware/pfml.py`                    |
| WI bonding override + `@leave_type_register` | `backend/benefits/rules/wisconsin/fmla.py` ~549              |
| WA military QE on base class                 | `backend/benefits/rules/washington/pfml.py` ~123             |
| WA R&R calendar test                         | `washington/tests/test_pfml.py` ~6111                        |
| HR PATCH viewset                             | `LeaveHrViewSet` ~1304 in `legacy/views/leaves.py`           |
| HR tests                                     | `backend/legacy/views/tests/test_leave_hr_viewsets.py`       |
| Benefit invalidation                         | `LeaveDetailsTab.tsx` ~81                                    |
| WAD test                                     | `test_full_usage_then_new_period_restores_entitlement` ~1175 |
| PR #11710                                    | OPEN, CI red                                                 |

---

## Review checklist (round 6)

| Question                                    | Answer                                                                 |
| ------------------------------------------- | ---------------------------------------------------------------------- |
| `@leave_type_register` on bonding override? | **Mandatory** with BONDING `@span_date_requirement`                    |
| #11710 net-new on main?                     | **No** — CI fixture + §Issue 5; span copy/working flags already merged |
| R&R under DE working-day banks?             | **L&C calendar vs working** + MTW test — not blind WA copy             |
| JP exclusion tests?                         | `eligible=False` + no spans; **not** exclusion message                 |
| Sidebar refetch?                            | **LeaveDetailsTab invalidates** — investigate other surfaces           |
| Viewset name?                               | **`LeaveHrViewSet`**                                                   |
| Christian full sign-off?                    | Phase 2 includes §Issue 4 WAD item                                     |
