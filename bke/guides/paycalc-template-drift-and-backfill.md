# Paycalc template drift and provisioning backfill

## Summary

State benefits are configured twice: once in **Python rule code** and once in
**`PaycalcItemTemplate` rows**. QA failures often mean **the rules are fine but
the database templates are stale or wrong**.

`construct_child_benefits` creates child templates and relationships, but it is
**idempotent on existing UUIDs** — it does not repair drift. Fixes require
explicit **backfill** (`ensure_*_template_config`) plus
`python manage.py construct_child_benefits --live-run` in each environment.

---

## Benefit backfill coverage

| Benefit     | Template pattern                           | Backfill in command                                                    | Notes                                                                                                   |
| ----------- | ------------------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **DC PFL**  | Parent + cloned children                   | `ensure_dc_pfl_template_config()`                                      | 12-week bank, `waiting_period=0`, parental `PARENTAL_BONDING` — see PR #11597                           |
| **DC FMLA** | Standalone medical/family UUIDs            | `ensure_dc_fmla_template_config()`                                     | Titles, `WORKING_DAYS`, `MEDCERT` — see PR #11597                                                       |
| **MA PFML** | Parent + paid/JP family & medical children | `ensure_child_template_specs_config()`                                 | Spec `max_duration` (12 family / 20 medical), `leave_types`, family `PARENTAL_BONDING`                  |
| **DE PFML** | Parent + paid/JP children                  | `ensure_child_template_specs_config()` + `verify_de_template_config()` | Caregiving `caregiver_relationship`, per-child `tracking_method`; verify warns on missing JP parent     |
| **HI FLL**  | Single template (`HI_FAMLI_BENEFIT_UUID`)  | `ensure_standalone_benefit_template_config()`                          | 4-week bank, `waiting_period=0`, `MEDCERT`                                                              |
| **MA PLA**  | Single template                            | `ensure_standalone_benefit_template_config()`                          | `waiting_period=0`; duration is rule-driven per `expected_children`                                     |
| **NJ FLI**  | Single template (`NJ_PFL_BENEFIT_UUID`)    | `ensure_standalone_benefit_template_config()`                          | 12-week bank, `waiting_period=0`, `PARENTAL_BONDING`, title **New Jersey Family Leave Insurance (FLI)** |
| **NY PFL**  | Single template                            | `ensure_standalone_benefit_template_config()`                          | 12-week bank backfill; waiting period remains template-driven                                           |

WA PFML and MN PFML child rows are also corrected by
`ensure_child_template_specs_config()` via the shared `CHILD_TEMPLATE_SPECS`
loop.

---

## When to suspect template drift

- Unit/rule tests pass with fixtures, but **admin or leave maps** show wrong
  behavior on dev/staging.
- Someone re-ran `construct_child_benefits` and **nothing changed**.
- The benefit uses **cloned child templates** or **pre-existing standalone
  rows**.

---

## Fix pattern

1. Add or extend `ensure_*_template_config()` in `construct_child_benefits.py`.
2. Call it from `provision_child_benefits()` so `--live-run` applies backfill.
3. Add tests that start from **drifted existing rows**, not ideal fixtures.
4. Document `construct_child_benefits --live-run` in PR for QA.

---

## Case study: DC PFL (2026)

Root cause: idempotent clone skip + inherited `benefit_type` / `waiting_period`
/ wrong `max_duration`. Fix in
[#11597](https://github.com/ourtilt/tilt-repo/pull/11597).

Remaining states (MA PFML, DE PFML, HI FLL, NJ FLI, NY PFL, MA PLA) use the
generic backfill added in the follow-up PR from `main`.

---

## Quick reference

| Item                 | Location                                                                      |
| -------------------- | ----------------------------------------------------------------------------- |
| Provisioning command | `backend/benefits/management/commands/construct_child_benefits.py`            |
| Backfill tests       | `backend/benefits/management/commands/tests/test_construct_child_benefits.py` |
| Platform UUIDs       | `backend/config/platform_uuids.py`                                            |
