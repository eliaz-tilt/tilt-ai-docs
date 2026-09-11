# BKE rule creation guide

This guide covers **legacy Python benefit rules** in `backend/benefits/rules/` —
the engine that evaluates leave eligibility, spans, paycalc items, and tracking
in production.

---

## Mental model

A **benefit rule** is a Python class that answers, for a given leave:

1. **Awake?** — Should we evaluate at all? (feature flag, jurisdiction, etc.)
2. **Eligible?** — Does the leave qualify?
3. **Spans** — Which dates are covered?
4. **Paycalc** — Paid/unpaid/uncalculated; template overrides
5. **Tracking** — How entitlement is counted (when tracking flags are on)

Each rule binds to exactly one **`PaycalcItemTemplate`** via `benefit_uuid`.
That template row (table `paycalc_items_template`, `companyId IS NULL` for
system templates) drives title, duration caps, pay fields, and UI copy.

`RuleService` discovers rules decorated with `@rule_implementation` and runs
them on leave lifecycle events (profile changes, schedule changes, etc.) or via
`manage.py run_rules`.

---

## When you need a new rule vs. extending an existing one

| Situation                                                                    | Approach                                                                                             |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| New state/program benefit                                                    | New module under `backend/benefits/rules/<state>/`                                                   |
| Same program, different leave types need **different template titles/UUIDs** | **Child rules** sharing a base class (DC PFL, OR FLA, DC FMLA)                                       |
| Same program, **shared parent bank** with medical vs family sub-banks        | Parent rule + child sub-bank rules; parent sleeps when child exists (MA/WA PFML — PIE-328)           |
| Eligibility tweak only                                                       | Extend base class `eligible` on an existing child rule                                               |
| **L&C alignment on existing single template** (NJ FLI, NY PFL, HI FLL)       | One `@rule_implementation` rule with OR'd leave-type gates in **`eligible`** — no child split needed |

**Do not** special-case one rule in `benefits/serializers.py` to fix template
titles. Put the correct `benefit_uuid` on the rule that handles that leave type
instead.

### Single-rule vs child-rule split

| Shape                                                | When                                                           | Leave-type gate                                                    | Provisioning                                                            |
| ---------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| **Single template, multiple qualifying leave types** | NJ FLI, NY PFL, HI FLL — one `benefit_uuid`, one paycalc title | Keep in **`eligible`** (OR across parental / caregiver / military) | Existing template UUID only — **no** `construct_child_benefits`         |
| **Separate template per leave type**                 | DC PFL, WI FMLA, OR FLA — distinct titles/UUIDs                | Put in child **`awake`** when types are mutually exclusive         | `construct_child_benefits` + `USE_PARENT_BANK` rels when sharing a bank |

The ghost "Not Eligible" row problem (DC PFL #11455) only applies to **multiple
child rules** that all wake on the same leave. A single rule with an OR'd
`eligible` produces at most one result row.

**Shared infrastructure:** NJ/NY/HI L&C PRs all touch `checks/leave.py`
(`resolve_caregiver_relationship`, `is_statutory_caregiver`). Land that file
from whichever PR merges first; the others rebase. Add unit tests in
`checks/tests/test_leave.py` once — propagate to sibling PRs if needed.

---

## File layout checklist

For a new state benefit `foo`:

```
backend/benefits/rules/<state>/foo.py       # rule classes
backend/benefits/rules/<state>/__init__.py  # export module (from .foo import *)
backend/benefits/rules/<state>/tests/test_foo.py
backend/config/platform_uuids.py            # stable UUID constants
backend/config/settings.py                  # BKE_FLAG_FOR_* (and FLAG_ENABLE_*_TRACKING if needed)
backend/tracking/services/base.py           # register UUIDs → should_track_* when tracking ships
```

Ensure the state package is imported from `backend/benefits/rules/__init__.py`
(or an aggregator) so `@rule_implementation` registration runs at startup.

---

## Minimal rule skeleton

```python
from django.conf import settings
from benefits.rules import BaseBenefitRule, rule_implementation
from benefits.rules.checks import employee, flag, leave
from benefits.rules.checks.base import Checkable
from config.platform_uuids import MY_BENEFIT_UUID

class MyBenefitBase(BaseBenefitRule):
    """Shared docstring: awake, eligibility, duration, approval, paycalc."""

    flag_enabled = Checkable(flag.for_everyone, settings.BKE_FLAG_FOR_MY_BENEFIT)
    employee_works_in = Checkable(employee.works_in_state, "XX")

    awake = BaseBenefitRule.and_expressions(flag_enabled, employee_works_in)
    paycalc = BaseBenefitRule.uncalculated  # or .unpaid


@rule_implementation
class MyBenefitMedical(MyBenefitBase):
    benefit_uuid = MY_BENEFIT_MEDICAL_UUID

    leave_is_medical = Checkable(leave.is_type, Leave.LeaveType.MEDICAL)
    # Leave-type gate in awake (see "Awake vs eligible" below)
    awake = BaseBenefitRule.and_expressions(
        MyBenefitBase.awake,
        leave_is_medical,
    )
    eligible = MyBenefitBase.common_eligible
```

### Required pieces

| Piece                  | Purpose                                      |
| ---------------------- | -------------------------------------------- |
| `@rule_implementation` | Registers class with `RuleService`           |
| `awake`                | Expression; if false, rule sleeps            |
| `eligible`             | Expression; if false, ineligible             |
| `benefit_uuid`         | Links to `PaycalcItemTemplate.uuid`          |
| `paycalc`              | `uncalculated`, `unpaid`, or calculated path |

Optional but common:

- `@leave_type_register` + `@span_date_requirement` on date methods
- `get_tracking_method()` when tracking behavior differs from template default
- `approval_document_config()` for med cert / EOB routing
- `dependencies = (OtherRule,)` when span dates depend on another rule's result

---

## Pattern A: One child rule per leave-type template (preferred for distinct titles)

**Examples:** `backend/benefits/rules/dc/pfl.py`,
`backend/benefits/rules/oregon/fla.py`, `backend/benefits/rules/dc/fmla.py`

Structure:

1. **`FooBase(BaseBenefitRule)`** — shared logic, **no** `@rule_implementation`,
   **no** `benefit_uuid`
2. **`FooMedical`, `FooCaregiving`, `FooParental`** — each
   `@rule_implementation` with its own `benefit_uuid` and leave-type gate in
   **`awake`** (not `eligible`; see below)

Why this pattern:

- `rule.get_benefit()` resolves the correct template for the whole pipeline
  (caregiver checks, span limiter, tracking, paycalc item creation, serialized
  titles)
- No serializer hacks or post-`evaluate()` benefit overrides
- Each rule appears independently in BKE results

```python
class DCPFLBase(BaseBenefitRule):
    # shared geo/flag awake, spans, approval, tracking — NOT @rule_implementation
    ...

@rule_implementation
class DCPFLMedical(DCPFLBase):
    benefit_uuid = DC_PFL_BENEFIT_UUID
    awake = BaseBenefitRule.and_expressions(DCPFLBase.awake, leave_is_medical)
    eligible = DCPFLBase.dc_pfl_common_eligible

@rule_implementation
class DCPFLCaregiving(DCPFLBase):
    benefit_uuid = DC_PFL_CAREGIVER_BENEFIT_UUID
    awake = BaseBenefitRule.and_expressions(DCPFLBase.awake, leave_is_caregiver)
    eligible = BaseBenefitRule.and_expressions(
        DCPFLBase.dc_pfl_common_eligible,
        caregiver_type_matches,  # real eligibility gate stays in eligible
    )
```

### Awake vs eligible for child rules

When child rules split on **mutually exclusive** leave types (medical /
caregiving / parental), put the leave-type check in **`awake`**, not `eligible`.

| Layer             | What belongs here                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------- |
| **Base `awake`**  | Shared jurisdiction gates: feature flag, works-in-state, lives-in-country                         |
| **Child `awake`** | Leave-type gate (`leave.is_type`) so only the matching child wakes                                |
| **`eligible`**    | Real qualification checks: tenure, hours, employer coverage, caregiver relationship, state config |

**Why it matters:**

1. The results API (`ResultViewSet`) returns only **awake** results — asleep
   siblings never reach the client.
2. Ineligible awake results with `" = False"` reasoning become
   `reasonsIneligible` and show in Admin **Not Eligible** (`PlanBenefitsCard`).
3. If leave-type is in `eligible`, all siblings wake on every leave; the two
   non-matching ones surface as ghost "Not Eligible" rows.

**Precedents:**

| Shape                                    | Leave-type check | Why                                                                                                                                   |
| ---------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Wisconsin FMLA** (`wisconsin/fmla.py`) | `awake`          | Three mutually exclusive types — canonical pattern                                                                                    |
| **DC PFL** (`dc/pfl.py`)                 | `awake`          | Same shape as WI FMLA                                                                                                                 |
| **DC FMLA** (`dc/fmla.py`)               | `eligible`       | OK here — children **overlap** (Medical={MEDICAL,PARENTAL}, Family={CAREGIVER,PARENTAL}), so at most one sibling fails the type check |

**Employee-facing UIs** (PayMapTab, BenefitsTab, PayCalcTab) filter out
ineligible rows whose reason includes `"The leave is:"`, but **Admin
PlanBenefitsCard does not** — so the awake pattern is required for clean admin
UX too.

**Tests:** wrong leave type → `expect_asleep`, not `expect_benefit_ineligible`.
See `test_caregiving_wrong_type_asleep` in `wisconsin/tests/test_fmla.py` and
`test_child_rule_asleep_for_wrong_leave_type` in `dc/tests/test_pfl.py`.

Real eligibility failures (wrong caregiver relationship, public employer,
unanswered state config) stay in `eligible` and should still use
`expect_benefit_ineligible`.

---

## Pattern B: Parent + sub-bank children with parent suppression (PIE-328)

**Examples:** `backend/benefits/rules/massachusetts/pfml.py`,
`backend/benefits/rules/washington/pfml.py`

When a **parent template** still exists in prod and child templates are rolled
out gradually:

- Parent rules use `covering_child_sub_bank_template_exists(...)` in `awake` to
  **sleep** when the child template for this leave type exists
- Child rules reset `awake` to the base expression (they must **not** inherit
  the parent's suppression gate)
- Children get their own `benefit_uuid` (medical vs family sub-bank)

Use Pattern A instead when each leave type always has its own template and there
is no “fallback parent” behavior to preserve.

---

## Platform UUIDs

Add constants in `backend/config/platform_uuids.py`:

```python
DC_PFL_CAREGIVER_BENEFIT_UUID = UUID(
    env.str("DC_PFL_CAREGIVER_BENEFIT_UUID", default="58825c21-b759-4d63-a15c-1f206fa0ecb9"),
)
```

- Defaults must match prod/dev template rows once provisioned
- Env overrides exist for emergencies; checked-in default is the source of truth
  for scripts like `developer/scripts/get-benefit.sh`

---

## PaycalcItemTemplate provisioning

Rules **require** matching `PaycalcItemTemplate` rows. Missing templates cause
silent failures (see pitfalls below).

### `construct_child_benefits` (preferred for multi-template / shared banks)

Command: `backend/benefits/management/commands/construct_child_benefits.py`

- Clones child templates from a parent when missing (idempotent on `child_uuid`)
- Wires `PaycalcItemTemplateRel` rows (`USE_PARENT_BANK`, etc.)
- **Dry-run by default**; commit with `--live-run`

```bash
# Local / dev pod
python manage.py construct_child_benefits          # dry-run, rolls back
python manage.py construct_child_benefits --live-run
```

Add specs to `CHILD_TEMPLATE_SPECS` and `RELATIONSHIP_SPECS` — do not rely on
“someone created it in admin” unless documented in a runbook.

**RI / DC PFL note:** child rows may already exist in an environment. The
command skips creation when `child_uuid` exists but still creates missing rels.

**DC PFL tracking_method:** Persisted entitlement tracking
(`calculate_family_forward`) reads `family.parent.tracking_method` from the
**PaycalcItemTemplate** row (`other.tracking_method`), not the rule's
`get_tracking_method()`. DC PFL uses `ROLLING_FORWARD_SUNDAY` in both places.
`construct_child_benefits` backfills `other.tracking_method` on the medical
parent and sibling templates when unset (run `--live-run` after deploy). New
clones inherit from the parent once the parent is backfilled.

### Inspecting templates in dev/stage/prod

```bash
eval $(op signin)   # 1Password for readonly DB password
./developer/scripts/get-benefit.sh dev DC_PFL
```

Or via kubectl (uses pod DB credentials):

```bash
kubectl exec -n dev deploy/tilt-services-django -- python manage.py shell -c "
from legacy.models import PaycalcItemTemplate, PaycalcItemTemplateRel
for t in PaycalcItemTemplate.objects.filter(title__icontains='DC Paid Family'):
    print(t.uuid, t.title)
"
```

### Shared 12-week (or N-week) bank

For separate templates that share one entitlement pool:

1. Pick a **parent** template (usually medical)
2. Create **child** templates for other leave types
3. Add `PaycalcItemTemplateRel` with `behavior=USE_PARENT_BANK` (child → parent)
4. Register **all** UUIDs in `tracking/services/base.py` when tracking ships

Without rels, tracking treats each template as an independent bank.

---

## Feature flags

Two layers:

| Flag type | Settings constant                 | Purpose                                         |
| --------- | --------------------------------- | ----------------------------------------------- |
| BKE awake | `BKE_FLAG_FOR_*` in `settings.py` | Rule evaluates at all                           |
| Tracking  | `FLAG_ENABLE_*_TRACKING`          | Persisted entitlement / shared bank enforcement |

In tests, enable with waffle `Flag` fixtures:

```python
@pytest.fixture(autouse=True)
def enable_my_benefit(db):
    return Flag.objects.create(name=settings.BKE_FLAG_FOR_MY_BENEFIT, everyone=True)
```

Tracking tests also need the tracking flag and correctly wired template rels.

---

## Tracking registration

When adding persisted entitlement tracking, map each template UUID in
`backend/tracking/services/base.py`:

```python
MY_BENEFIT_UUID: should_track_my_benefit,
MY_BENEFIT_CAREGIVER_UUID: should_track_my_benefit,
```

Implement `should_track_my_benefit(company)` to gate on
`FLAG_ENABLE_*_TRACKING`.

Add tracking-focused tests (see
`backend/benefits/rules/dc/tests/test_dc_pfl_tracking_persisted.py`).

---

## Testing

### Conventions

- Tests live in `backend/benefits/rules/<state>/tests/`
- Shared builders → `<state>/tests/helpers.py` (avoid copy-pasting template
  fixtures)
- Use helpers from `benefits/rules/tests/__init__.py`:
  `expect_benefit_eligible`, `expect_benefit_ineligible`, `expect_asleep`, etc.

### Template fixtures

Every rule test needs `PaycalcItemTemplate` rows matching `benefit_uuid`. For
multi-template benefits, use a shared helper:

```python
# dc/tests/helpers.py
make_dc_pfl_sibling_templates(parent, sibling_specs=..., tracking_method=...)
```

Wire `USE_PARENT_BANK` rels in the helper when testing shared pools.

### What to test

- Awake vs asleep (flag off, wrong state)
- Eligible / ineligible / missing for each child rule
- Leave-type-specific gates (caregiver relationship, parental dates)
- Span behavior (duration caps, pre-birth extensions)
- Tracking pool exhaustion across leave types (when tracking flag on)

Run:

```bash
just test backend/benefits/rules/<state>/tests/
```

---

## Re-running rules on a leave (dev QA)

```bash
python manage.py run_rules --leaves 11373,11405 --ignore-checks
```

Via kubectl on dev:

```bash
kubectl exec -n dev deploy/tilt-services-django -- \
  python manage.py run_rules --leaves 11405 --ignore-checks
```

After deploying rule changes **and** ensuring templates/rels exist, re-run rules
on affected leaves to refresh paycalc items and BKE suggestions.

---

## Common pitfalls (learned the hard way)

### 1. Missing template → silent disappearance

`BenefitResult.__init__` catches `Benefit.DoesNotExist` and sets
`benefit = None`:

```python
# backend/benefits/rules/__init__.py
try:
    self.benefit = rule.get_benefit()
except Benefit.DoesNotExist:
    self.benefit = None
```

If a child template UUID is missing in an environment, the rule may evaluate but
**produce no visible suggestion**. Do not assume “prod has it” — add
`construct_child_benefits` specs and verify with `get-benefit.sh`.

### 2. Single rule + wrong template for leave type

One rule with one `benefit_uuid` always uses that template for
caregiver/parental/medical. Wrong titles and wrong caregiver-relationship config
follow. Fix: child rules (Pattern A).

### 3. Post-evaluate `benefit` override

Overriding `result.benefit` after evaluation leaves earlier steps (caregiver
checks, span limiter, tracking UUID) on the wrong template. Fix: correct
`benefit_uuid` on the child rule class.

### 4. Serializer special-casing

Avoid DCPFL-only branches in `ResultRuleSerializer`. Correct template comes from
the rule's `benefit_uuid` when child rules are modeled properly.

### 5. Shared bank without `USE_PARENT_BANK` rels

Templates can exist while rels do not (confirmed on dev for DC PFL). Tracking
with `FLAG_ENABLE_*_TRACKING` then counts three independent 12-week banks.
Always provision rels via `construct_child_benefits --live-run` or idempotent
shell/runbook.

### 6. Db dumps missing templates

Local dumps from `just db-dump dev` only contain templates present in that
environment at dump time. If templates were provisioned after the dump, local
testing fails with `DoesNotExist` until you re-dump or run provisioning locally.

### 7. MA/WA parent suppression on child rules

Child sub-bank rules must **not** inherit `not_superseded_by_children` in
`awake` — they would suppress themselves. Reset `awake` to the base expression
on children.

### 8. Onboarding / state config gates

Some rules read `StateConfiguration` (e.g. DC PFL
`contributes_pfml_payroll_taxes`). Tests need explicit setup via helpers like
`set_dc_contributes_pfml_payroll_taxes`. Unanswered config → **Missing**,
explicit `False` → **Ineligible**.

### 9. Leave-type in `eligible` on mutually exclusive child rules

Copying DC FMLA's `eligible`-based type gate works structurally but causes UX
bugs when child leave types do **not** overlap: every sibling wakes, two return
`eligible=False` with `"The leave is: … = False"`, and Admin Not Eligible shows
extra ghost rows. Put leave-type in child `awake` instead (Wisconsin FMLA / DC
PFL pattern). Keep relationship/coverage/config checks in `eligible`.

### 10. Rule `get_tracking_method` without template `other.tracking_method`

BKE span/duration logic may call `rule.get_tracking_method(leave)`, but
**persisted entitlement tracking** reads `Benefit.tracking_method` from
`PaycalcItemTemplate.other["tracking_method"]` (see `calculate_family_forward`).
If the rule hardcodes e.g. `ROLLING_FORWARD_SUNDAY` but templates lack
`other.tracking_method`, shared-bank tracking silently misbehaves. Align
template data via `construct_child_benefits` backfill (DC PFL) or set explicitly
in test helpers/fixtures.

---

## PR checklist

- [ ] Rule classes with `@rule_implementation`, `awake`, `eligible`,
      `benefit_uuid`
- [ ] Mutually exclusive child rules: leave-type gate in **`awake`**, not
      `eligible`
- [ ] Shared-bank templates: `other.tracking_method` on parent (+ siblings)
      matches rule `get_tracking_method`
- [ ] UUID constants in `platform_uuids.py`
- [ ] BKE feature flag in `settings.py` (+ tracking flag if applicable)
- [ ] `construct_child_benefits` specs for new child templates and rels (or
      documented runbook with idempotent command)
- [ ] Tracking UUID registration in `tracking/services/base.py` (if tracking)
- [ ] Unit tests per child rule; tracking tests if shared bank
- [ ] Shared test helpers for template provisioning (no duplicated fixtures)
- [ ] Verified templates in dev (or `--live-run` plan attached to PR)
- [ ] No serializer one-offs for template/title selection

---

## Reference implementations

| Pattern                                                      | File                                                                           |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Child rule per leave type (mutually exclusive)               | `backend/benefits/rules/dc/pfl.py`, `backend/benefits/rules/wisconsin/fmla.py` |
| Child rule per leave type (overlapping types OK in eligible) | `backend/benefits/rules/dc/fmla.py`                                            |
| OR FLA multi-template                                        | `backend/benefits/rules/oregon/fla.py`                                         |
| DC FMLA medical/family split                                 | `backend/benefits/rules/dc/fmla.py`                                            |
| Parent suppression + sub-banks                               | `backend/benefits/rules/massachusetts/pfml.py`                                 |
| Child template provisioning                                  | `backend/benefits/management/commands/construct_child_benefits.py`             |
| DC PFL test helpers                                          | `backend/benefits/rules/dc/tests/helpers.py`                                   |
| DC PFL tracking tests                                        | `backend/benefits/rules/dc/tests/test_dc_pfl_tracking_persisted.py`            |

---

## Related commands & scripts

| Tool                                   | Use                                            |
| -------------------------------------- | ---------------------------------------------- |
| `manage.py run_rules`                  | Force re-evaluation for leaves                 |
| `manage.py construct_child_benefits`   | Provision child templates + rels               |
| `developer/scripts/get-benefit.sh`     | Read-only template inspection (dev/stage/prod) |
| `just test backend/benefits/rules/...` | Run rule tests in Docker                       |
