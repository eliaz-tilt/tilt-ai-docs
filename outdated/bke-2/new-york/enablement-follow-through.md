# NY PFL BKE 2.0 — post-merge enablement checklist (PIE-468)

Use this when turning on `enableBKENewYorkPFL` for a company. Shadow/flyout
today; legacy still authoritative until rollout stage is explicitly advanced.

## Before flag-on

1. **BKE catalog deployed** — `ny-pfl` topology and banks (`ny-pfl-continuous`,
   `ny-pfl-intermittent`, `ny-pfl-jp`, `ny-dbl-pfl-combined`) imported to the
   BKE service the BFF calls.
2. **Migration 0047 applied** — NY routing levers seeded in prod Django DB.
3. **Prod paycalc templates** — confirm NY PFL template `trackingMethod` aligns
   with BKE `rollingBack` when lane path becomes authoritative (legacy defaults
   to `ROLLING_FORWARD` until flag flips). Mismatch causes exhaustion window
   disagreements between legacy history and lane fold.
4. **Rollout stage documented** — shadow-only (read-only fold + flyout) vs
   legacy asleep (authoritative lane path). Today: flag on → legacy `NewYorkPFL`
   sleeps; fold still not persisted from evaluate.

## Flag

- **`enableBKENewYorkPFL`** — company-scoped; separate from `enableBkeLanes` (WA
  demo path).
- **`enableBkeLanes`** — must **not** route non-WA leaves; NY uses its own flag.

## Routing prerequisites

- Leave must have a **historical profile snapshot** with resolvable
  `workingState = NY`. Absent snapshot → no lane topology (legacy only).

## Follow-up tickets (V1 gaps)

| Item                           | Why                                                                                             |
| ------------------------------ | ----------------------------------------------------------------------------------------------- |
| Tenure / in-flight DBL parity  | Lever `nyPflTenureMet` vs legacy `_get_tenure_date` (med-cert extensions, same-leave DBL spans) |
| Birthing recovery window       | `recoveryEnd` vs actual DBL span end                                                            |
| Birthing parent DBL skip       | Topology limitation #3 in changelog                                                             |
| Combined cap same-leave DBL    | In-flight DBL debits combined pool only after legacy tracking writes                            |
| In loco parentis               | Manual routing only in V1                                                                       |
| Private/self-insured elections | Open L&C #3                                                                                     |
| 2026 max weekly benefit        | Open L&C #4; pay remains uncalculated on banks                                                  |

## Verification after flag-on

1. NY leave → plan-details flyout returns `mode: lanes`, `topologyCode: ny-pfl`.
2. `run_rules` shadow tally includes NY leaves when flag on (no abort of legacy
   loop).
3. Legacy `NewYorkPFL.evaluate` → asleep for flagged company.
4. Non-NY leave (e.g. CA) with only `enableBkeLanes` → no lane shadow (not
   `wa-pfml`).
