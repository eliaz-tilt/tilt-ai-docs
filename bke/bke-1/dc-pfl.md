# BKE: DC PFL (#11120) — merged

PR: https://github.com/ourtilt/tilt-repo/pull/11120 (merged to `main`
2026-07-21)\
Branch was: `eliaz/dc-pfl-seams`\
Sibling: [DC FMLA](./dc-fmla.md) (#11119, open)

**Merge order note:** PFL landed **before** FMLA (opposite of the original
plan). FMLA rebased onto `main` and took the combined `helpers.py` (schedule
helpers + `set_dc_contributes_pfml_payroll_taxes`).

## Birthing parental (product — Jon Nall, 2026-08-05)

Full detail:
[dc-birthing-product-decisions.md](./dc-birthing-product-decisions.md).

- PFL covers **pregnancy disability and bonding** — runs from leave/EDD start,
  **not** bonding-only after DC FMLA medical.
- **12 weeks** base; **+2 weeks** pre-birth when medically necessary (med cert)
  → up to **14 weeks** total (`get_max_document_duration` in `pfl.py`).
- All PFL time **pending until EOB** — Tilt is not the decision maker; EOB
  approval method is already wired (`EXPLANATION_OF_BENEFITS_STATE`).
- Retest template bug: parent bank `max_duration=6` on dev → 12-week spans fail;
  Fix via `construct_child_benefits` backfill (see fix plan).

## Goal

Ship DC Paid Family Leave V1 using **only collected data**. Do not stub
uncollected statute slices. Do not keep a `*_data_seams.py` module once every
check reads a real field.

Shared V1 bright line (same as DC FMLA / MA PFML / MA PLA):

- Collected → wire it.
- Uncollected → omit; track as non-code follow-through.
- Out of scope forever for these PRs (do not wire LXP-529 leave-type columns):
  military QE, safe/DV, military caregiving, organ/bone marrow donor,
  bereavement.

## What shipped

| Piece                                   | Behavior                                                                                          |
| --------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Tax contribution                        | Onboarding `StateConfiguration.configurations["DC"].contributes_pfml_payroll_taxes` at eval time  |
| Nullability                             | Explicit `true` → eligible; explicit `false` → ineligible; absent/`null`/no profile → **Missing** |
| Intermittent / reduced parental bonding | Sets `PaycalcItem.needs_manual_approval=True` (status-hold flag only)                             |
| Tracking                                | Rule default `ROLLING_FORWARD_SUNDAY`; shared 12-week bank covered by persisted-entitlement tests |
| Caregiver                               | Unsupported relationship (e.g. sibling-in-law not on template) → deny, not expand survey enum     |

**Not shipped / dropped**

- Data-seams module (`dc_pfl_data_seams.py` removed).
- New `Policy` field / migration for tax contribution (read onboarding JSON
  instead).
- “Majority in DC” seam (duplicated existing logic).
- Product “route to a human” workflow for intermittent bonding.

## Tax contribution eligibility

Source path (evaluation-time only; no Policy sync):

```text
company.onboarding_profile → StateConfiguration.objects.active()
  → newest by updated_at
  → configurations["DC"]["contributes_pfml_payroll_taxes"]
```

Semantics (aligned with DC FMLA employer threshold):

| Stored answer                                         | Panel / eligibility                                      |
| ----------------------------------------------------- | -------------------------------------------------------- |
| `true`                                                | Eligible                                                 |
| `false`                                               | Determined ineligible                                    |
| Missing key, `null`, no config, no onboarding profile | **Missing** — “Missing DC PFML payroll tax contribution” |

Implementation notes:

- Gate with
  `if answer is None: rule.require(None, description="DC PFML payroll tax contribution")`.
- Do **not** assume `require(False)` treats `False` as missing —
  `_is_empty(False)` is `False` in this codebase.
- Absent config as silent deny was wrong: non-onboarded / legacy companies would
  look determined ineligible.

### StateConfiguration caveats

- `.active()` excludes soft-deletes only — there is **no** publish/draft state.
  Don’t call it “published” in docs or PRs.
- Multiple active rows per profile are allowed by the model; we take newest
  `updated_at`. Convention is one row; a newer row without a `DC` key can shadow
  an older row that has one — call that out if questioning the query.

## `needs_manual_approval` framing

Intermittent or reduced-schedule **parental** leave sets:

```python
PaycalcItem.needs_manual_approval = True
```

via `paycalc_item_template_overrides`.

**Important:** that flag is only read by the **legacy status engine**, which is
**off in prod today**, so this alone produces **no hold** and is **not** a
product route-to-human workflow. Matching the sibling DC FMLA pattern is fine in
code; descriptions must not say “routes to manual review.”

If we want a real prod hold on intermittent bonding, it has to come from
`ApprovalMethodRule` / `ApprovalMethodOverride` data — follow-through, not this
PR.

Do not re-export `needs_manual_approval` from package `__all__` (helper
predicate stays module-local / tests import from `pfl.py`).

## Shared 12-week bank (tracking tests)

Persisted-entitlement coverage in `test_dc_pfl_tracking_persisted.py`:

| Scenario               | Expectation                |
| ---------------------- | -------------------------- |
| No prior usage         | Full 12 weeks available    |
| 10 weeks prior medical | 2 weeks remain for bonding |
| 12 weeks prior medical | 0 remaining                |

Flag: `FLAG_ENABLE_DC_PFL_TRACKING` for the tracking path under test.

## Key files

- `backend/benefits/rules/dc/pfl.py` — rule, tax check, manual-approval flag
- `backend/benefits/rules/dc/tests/helpers.py` — shared schedule helpers +
  `set_dc_contributes_pfml_payroll_taxes`
- `backend/benefits/rules/dc/tests/test_pfl.py` — eligibility / Missing /
  manual-approval / caregiver
- `backend/benefits/rules/dc/tests/test_dc_pfl_tracking_persisted.py` — shared
  bank

## Merge hygiene

`#11119` and `#11120` both add `backend/benefits/rules/dc/tests/helpers.py`.
**PFL merged first** (#11120, 2026-07-21). FMLA (#11119) rebases onto `main` and
keeps the combined file:

- `set_tracked_leave_schedule` / `count_covered_weekdays` (FMLA tracking tests)
- `set_dc_contributes_pfml_payroll_taxes` (PFL tax tests)

## Dustin approval (final review, 2026-07-21)

All feedback addressed. Highlights he called out explicitly:

- Tax Missing-vs-deny gate (`None` → Missing, explicit `false` → ineligible) —
  easy to get subtly wrong
- Seams module gone; collected fields only; caregiver deny-not-expand-enum
- Framing: status-hold flag, not “manual review” workflow
- Shared-bank tracking tests cover no-prior / partial / exhausted ends
- `helpers.py` add/add conflict expected when the second PR lands (happened on
  FMLA rebase)

## Follow-through (non-code / later)

- Real intermittent-bonding hold via `ApprovalMethodRule` /
  `ApprovalMethodOverride` if product wants a prod hold.
- LXP-529 leave-type serialization for out-of-scope leave types (not this PR).
- Confirm prod templates / flags for enablement when rolling out.

## Review reply shortcuts

- Unanswered tax → Missing (not deny): yes — otherwise every non-onboarded DC
  company silently fails eligibility.
- “Published” config: misnomer; `.active()` = not soft-deleted.
- “Manual review”: only the status-hold flag; no human workflow in product
  today.
- Caregiver unsupported relationship: deny vs expanding enum — deny is
  intentional.

## Self-review pass (2026-07-14)

- Rule docstring now states Missing-vs-deny + status-hold framing.
- Added Missing coverage for an explicit `null` tax key (not only deleted
  config).
- Pushed as `Tighten DC PFL docs and Missing coverage for null tax answers.`
