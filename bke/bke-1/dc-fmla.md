# BKE: DC FMLA (#11119)

PR: https://github.com/ourtilt/tilt-repo/pull/11119\
Sibling: [DC PFL](./dc-pfl.md) (#11120)

Learnings from the DC FMLA review cycle (shared V1 rules also apply to PFL).

## Birthing parental (product — Jon Nall, 2026-08-05)

Full detail:
[dc-birthing-product-decisions.md](./dc-birthing-product-decisions.md).

- **Separate banks:** up to **16 weeks medical** + up to **16 weeks family**
  (not federal FMLA’s single 12-week combined cap).
- **Routine birthing span:** ~**6 wk vaginal / 8 wk C-section postpartum** is
  what is generally **approved** for recovery absent complications — **not** a
  6/8-week medical bank cap. Complications can draw more from the 16-week
  medical bank.
- **Pre-EDD:** medical reason only; med cert required. Postpartum recovery may
  need med cert unless policy waives routine pregnancies
  (`birthingMedCertDocRequired`). Parallel to federal FMLA cert gating.
- **Engineering fix (retest):** add birthing recovery **END** boundary on
  `DCFMLAMedical` (MN PFML pattern); keep **16-week** `get_base_max_duration`.

## Collected vs uncollected (V1 bright line)

- If a statute slice needs data we do **not** collect in V1, **do not stub it**
  — omit that slice and track as non-code follow-through (see MN PFML / Dustin’s
  CT PFML story notes).
- Do **not** keep a `*_data_seams.py` module once every accessor reads real
  collected fields. Naming the file “seams” after activation invites the
  confusion we’re trying to avoid.
- Out of scope for DC benefits (do not wire LXP-529 leave-type columns for
  these): military QE, safe/DV, military caregiving, organ/bone marrow donor,
  bereavement.

## DC FMLA employer threshold

- Source of truth: `Policy.has_met_dc_employer_threshold` (nullable boolean).
- Onboarding: `DC.has_20_employees` syncs onto that policy field on publish
  (null-guarded, DC-only).
- **Do not use US headcount** (`employees_in_usa` / `employee_count`) as a proxy
  for DC worksite coverage.
- Nullability semantics:
  - `None` (unanswered) → **missing** (`eligible=None` / “Missing …”), not
    silent deny.
  - `False` → determined ineligible.
  - `True` → meets coverage.
- Implement like `has_met_fmla_employer_threshold`: put
  `company.policy.has_met_dc_employer_threshold` on the Check `reqs` path
  **and** read the same path in `result`. That keeps Missing detection and the
  boolean read aligned (avoids `Requirement.get(leave, "company.policy")` vs
  `get_policy()` divergence).
- Note: `_is_empty(False)` is `False` in this codebase, so an explicit `False`
  on `reqs` is **not** treated as missing. Still gate `None` via `Requirement`
  on the field itself; use `is True` in the result lambda.

## DC FMLA tracking method

Resolved via `Benefit.for_dc_fmla()` in `benefits/models.py` (same pattern as
federal `for_fmla()`), wired from `Benefit.for_company()` for DC medical +
family UUIDs. `BenefitService.retrieve_benefit()` and the rule’s
`get_tracking_method()` both use this path — BenefitService does not call into
rules directly (archmatters review, 2026-07-21).

Logic:

- Prefer `policy.us_dc_fmla_tracking` when set (`FMLA_ELIGIBILITY_TRACKING`
  map).
- Else keep template `tracking_method` if present.
- Else default `TrackingMethod.ROLLING_FORWARD_24`.
- **Does not** fall back to federal `fmla_eligibility_rule`.

**Enablement follow-through:** persistence resolves tracking from the
**template**, not the rule. Prod DC FMLA templates must carry
`ROLLING_FORWARD_24`.

Tests: `test_retrieve_dc_fmla_benefit_*` in `test_benefits.py`.

## PR / merge hygiene

- `#11120` (PFL) **merged first** (2026-07-21). `#11119` (FMLA) rebased onto
  `main`; resolved `helpers.py` add/add by keeping both helper sets. See
  [dc-pfl.md](./dc-pfl.md).
- Update PR description merge note: drop “merge FMLA first” — PFL is already on
  `main`.
- Stale PR comment “Seams-first” should be edited to collected-data framing.
- Prefer plain pytest functions + one-line docstrings per
  `.ai/rules/testing/testing-standards.mdc` for new tests (classes are
  legacy/acceptable to leave unless touching that file heavily).

## Review reply shortcuts

- Unanswered threshold → Missing: yes, deliberate; deny-on-null was the earlier
  conservative mistake.
- Renamed/removed `_data_seams`: accessors folded into
  `checks.company.meets_dc_employer_coverage` + inline tracking default in
  `fmla.py`.

## Self-review pass (2026-07-14)

- Docstring/`needs_manual_approval` framing: status-hold flag, not “manual
  approval” product workflow.
- Onboarding sync documents newest-`StateConfiguration` convention; null
  `has_20_employees` must not overwrite Policy (test added).
- Tracking bank ends: full medical, full family, exhausted family; fixed
  misleading partial-family docstring.
- Missing one-line test docstrings filled in.
- Pushed as `Tighten DC FMLA framing, bank-end tests, and onboarding sync docs.`

## Self-review pass (2026-07-21)

- `Benefit.for_dc_fmla()` + BenefitService tests (archmatters tracking comment).
- Onboarding publish tests: absent `DC` key; newest row omits `DC` key.
- Merged `main` after PFL (#11120); `helpers.py` conflict resolved.
- Pushed as `tweaks: updates` + merge commit.
