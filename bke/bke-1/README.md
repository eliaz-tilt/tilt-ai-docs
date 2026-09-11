# BKE 1.0 activation PR notes

Local research for legacy Python benefit rule PRs (`backend/benefits/rules/`).

| Program              | Status                                                           | Doc                                                                                                             |
| -------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| DC FMLA              | Open [#11119](https://github.com/ourtilt/tilt-repo/pull/11119)   | [dc-fmla.md](./dc-fmla.md)                                                                                      |
| DC PFL               | Merged [#11120](https://github.com/ourtilt/tilt-repo/pull/11120) | [dc-pfl.md](./dc-pfl.md)                                                                                        |
| DC birthing parental | Retest PIE-429/430 (2026-08-05)                                  | [dc-birthing-product-decisions.md](./dc-birthing-product-decisions.md) · [fix plan](../dc-birthing-fix-plan.md) |
| MA PFML              | Open                                                             | [ma-pfml.md](./ma-pfml.md)                                                                                      |
| MA PLA               | Open                                                             | [ma-pla.md](./ma-pla.md)                                                                                        |

Reviewer lens: [../../reviewer/dustin.md](../../reviewer/dustin.md)

## DC sibling PR lesson (2026-07-21)

PFL merged before FMLA. Both touch `backend/benefits/rules/dc/tests/helpers.py`.
When the second PR lands, rebase onto `main` and keep **both** helper sets — do
not drop the merged sibling’s helpers.
