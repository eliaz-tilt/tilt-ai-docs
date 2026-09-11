# PIE-468: NY PFL lane topology (BKE 2.0) — PR description

Use this as the GitHub PR body when opening `pie-468/ny-pfl` →
`bke-integration`.

**BKE 2.0 guides:** [playbook](../guides/lane-topology-pr-playbook.md) ·
[PIE-439 retrospective](../guides/pie-439-nj-tdi-retrospective.md) (coupling
mistakes to avoid)

## NY PFL vs PIE-439 lessons (self-audit)

| PIE-439 mistake                                    | NY PFL status                                                                                 |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `catalog` imports `NewJerseyTDI` for `recoveryEnd` | **OK** — `recoveryEnd` is SQL in migration `0048`; no legacy class import                     |
| Legacy rule imports `catalog.*` waiting helper     | **OK** — `NewYorkPFL` does not import catalog overlays                                        |
| Rebase leaves WA-default shadow/Rule Studio path   | **Verify after each rebase** — `topology_code` + NY lever maps in `lanes.py` / `bke_views.py` |
| Migration number collision on `0047`               | **Resolved** — NY levers in `0048` after `0047_seed_work_state_lever`                         |

## Summary

- Implements **NY PFL lane topology** (`ny-pfl`) for shadow evaluation and the
  plan-details flyout — not a full replacement of the legacy eligibility engine.
- Routes NY leaves to `ny-pfl` when `enableBKENewYorkPFL` is on; legacy
  `NewYorkPFL` **sleeps** on that flag.
- Routes WA leaves to `wa-pfml` when `workingState = WA` and `enableBkeLanes` is
  on. Other jurisdictions and leaves without a profile snapshot do not enter
  lane shadow.
- Seeds NY routing levers in migration `0047` (`workingState`,
  `eeNyWorkScheduleDetails`, `isContinuous`, `birthingParent`, `recoveryEnd`,
  `nyPflTenureMet`).
- Mirrors prior NY PFL template usage onto continuous, intermittent, and
  job-protection banks so shared 12-week pool debits stay aligned.

## What this does **not** do (V1 scope)

- Does not calculate pay dollars (67% AWW cap remains uncalculated; banks use
  protection role pay).
- Does not persist fold output — flyout/shadow is read-only; add-to-plan posts
  drafts through the normal paycalc endpoint.
- Does not wire in loco parentis auto-routing (manual / LS).
- Does not handle private/self-insured plan elections (open L&C question).

## Semantics changes vs legacy (call out for reviewers)

| Area                   | Legacy (`NewYorkPFL`)                                                                                    | Lane path (V1)                                                                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Tenure / DBL           | `_get_tenure_date` includes **in-flight DBL spans** from the same evaluation (incl. med-cert extensions) | `nyPflTenureMet` lever uses **prior published NY DBL entitlement use dates** only   |
| Birthing bonding start | After actual DBL span end                                                                                | `recoveryEnd` = EDD + 6/8 weeks (standard window); complications LS-handled         |
| Combined cap           | Legacy DBL + PFL on same leave via rule dependency                                                       | In-flight DBL on same leave not in combined-cap ledger until legacy writes tracking |
| Tracking method        | Default `ROLLING_FORWARD` on template                                                                    | BKE banks use `rollingBack` per L&C                                                 |

## V1 limitations (from topology changelog)

1. `recoveryEnd` uses standard 6/8 weeks from EDD — not actual NY DBL span end.
2. `nyPflTenureMet` uses prior published NY DBL use dates — not in-flight DBL
   spans.
3. Birthing parent skipping DBL — future iteration.
4. In loco parentis — manual / not auto-routed.
5. Private/self-insured plan elections — open question.
6. Pay dollar cap 2026 — open question; banks use protection role pay only.

## Test plan

- [ ] `just test backend/benefits/rules/catalog/tests/test_lanes.py`
- [ ] `./gradlew :bke-bootstrap:test --tests NyPflTopologyAcceptanceTest` (or
      repo equivalent)
- [ ] `just test backend/benefits/rules/new_york/tests/test_pfl.py::TestNewYorkPFL::test_asleep_when_bke_v2_flag_enabled`
- [ ] Manual: NY leave with `enableBKENewYorkPFL` on → flyout shows lanes mode;
      legacy rule asleep
- [ ] Manual: CA leave with `enableBkeLanes` on → no WA topology shadow

## Enablement follow-through

See [enablement-follow-through.md](./enablement-follow-through.md).

## Test results

- `NyPflTopologyAcceptanceTest`: **11/11 passed**
  (`./gradlew :bke-bootstrap:test --tests NyPflTopologyAcceptanceTest --rerun-tasks`)
- `test_lanes.py`: **51 tests** (includes 3 new topology-routing tests + 2
  `nyPflTenureMet` NULL tests). Full suite requires tilt Postgres
  (`just test backend/benefits/rules/catalog/tests/test_lanes.py`); not run here
  — port 5432 conflict with unrelated local container.
- `test_asleep_when_bke_v2_flag_enabled`: included in `test_lanes.py` run above.
