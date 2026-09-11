# BKE: MA PFML (#11135)

PR: https://github.com/ourtilt/tilt-repo/pull/11135\
Branch: `eliaz/ma-pfml-seams`\
Sibling: [MA PLA](./ma-pla.md) (#11136)

## Goal

Ship MA PFML V1 using **only collected data**. Do not stub uncollected statute
slices. Do not keep a `*_data_seams.py` module once accessors read real fields.

## What shipped

| Piece                           | Behavior                                                                                                  |
| ------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Private plan exclusion          | Onboarding `MA.administration_mode`                                                                       |
| Nullability                     | `UNIFORM_PRIVATE` → ineligible; unanswered/`null`/no profile → **Missing**; state/mixed → pass this check |
| Earnings                        | `historical_profile.has_met_ma_earnings` via `leave.field` (None → Missing)                               |
| Parental windows                | `expected_due_date`                                                                                       |
| Intermittent / reduced parental | Sets `PaycalcItem.needs_manual_approval` (status-hold only)                                               |
| Tracking default                | `ROLLING_FORWARD` when template unset                                                                     |

**Deleted:** `pfml_data_seams.py` (including the premature `delivery_anchor`
wrapper).

## Private-plan / Missing

Unanswered administration mode must **not** silently pass as “not private.” That
would green-light state MA PFML for every non-onboarded MA company.

Gate:
`if answer is None: rule.require(None, description="MA PFML administration mode")`.

Eligible fixture sets `UNIFORM_STATE` so baseline tests stay green.

## Framing

Do not say “routes to manual review.” Same DC pattern: status-hold flag; legacy
status engine off in prod → no hold today. Follow-through:
ApprovalMethodRule/Override.

## Not in V1

- 30× weekly-benefit earnings prong
- Prior-employer days against the combined cap
- Private-plan leave-year tracking override
- Employer intermittent approval field

Out of scope leave types: military QE, safe/DV, military caregiving, organ/bone
marrow donor, bereavement.

## Self-review pass (2026-07-14)

- Dropped seams module; Missing for unanswered administration_mode
- Status-hold framing; removed `needs_manual_approval` from `__all__`
- 90 tests passed (`test_pfml.py` + `test_ma_pfml_private_plan.py`)
