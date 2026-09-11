# BKE: MA PLA (#11136)

PR: https://github.com/ourtilt/tilt-repo/pull/11136\
Branch: `eliaz/ma-pla-seams`\
Sibling: [MA PFML](./ma-pfml.md) (#11135)

## Goal

Ship MA Parental Leave Act V1 on collected data only. No stubs for probationary
alternate path or adoptive age/disability gates.

## What shipped

| Piece                  | Behavior                                                                                      |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| Employer size          | `company.us_size(6)` → policy `employees_in_usa` (result also falls back to `employee_count`) |
| Size nullability       | Explicit under-6 → ineligible; unanswered `employees_in_usa` → **Missing** (via check `reqs`) |
| Leave type             | Parental; foster excluded                                                                     |
| Tenure / FT            | Full-time + 3 months                                                                          |
| Windows                | 3 weeks pre-EDD / 1 year end from due date                                                    |
| Intermittent / reduced | Sets `PaycalcItem.needs_manual_approval` (status-hold only)                                   |
| Tracking default       | `EVENT_BASED` when template unset                                                             |

## Employer size note

MA PLA uses US headcount (`us_size`), not a MA-only worksite count — that is the
collected policy field for the “6 or more employees” statute. Unlike DC FMLA’s
dedicated `has_met_dc_employer_threshold`, there is no MA-specific coverage
boolean yet.

`company.us_size` reqs only `employees_in_usa`: if that is `None`, the check
surfaces Missing even when `employee_count` is set (result-lambda fallback never
runs). Prefer setting `employees_in_usa` in fixtures/prod data.

## Framing

Do not say “routes to manual review.” Status-hold flag only; real prod hold
needs ApprovalMethod data.

## Not in V1

- Probationary-period alternate eligibility
- Adoptive child age / disability gate
- Employer intermittent-approval field

## Self-review pass (2026-07-14)

- Status-hold framing; drop `needs_manual_approval` from `__all__`
- Unanswered employer size → Missing test
- 30 tests passed
