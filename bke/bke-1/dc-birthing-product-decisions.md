# DC birthing parental — product decisions (Jon Nall, 2026-08-05)

Source: Slack thread on PIE-429 / PIE-430 retest (plan 10362). Canonical product
answers for DC FMLA + DC PFL birthing logic. Implementation plan:
[../dc-birthing-fix-plan.md](../dc-birthing-fix-plan.md).

---

## DC PFL (Paid Family Leave)

**Q:** Should PFL run 12 weeks from leave/EDD start (overlapping FMLA), or only
after medical / during bonding?

**Answer (Jon):**

- PFL **covers both medical (pregnancy disability) and bonding** — it should
  cover the pregnancy disability period, not bonding-only.
- **Base:** 12 weeks from the leave / disability period (concurrent with FMLA
  medical + bonding on the calendar — PFL is one paid program spanning
  disability + bonding).
- **Pre-birth medical:** up to **2 additional weeks** when pre-birth time is
  medically necessary → **up to 14 weeks total**.
- **Approval:** all DC PFL time remains **pending until an EOB (Explanation of
  Benefits) document** is received. **Tilt is not the decision maker** for DC
  PFL — the state/insurer decides via EOB.

**Code alignment (already largely present):**

| Behavior                      | Where                                                                  |
| ----------------------------- | ---------------------------------------------------------------------- |
| 12-week base                  | Template + `DCPFLParental` span limiter                                |
| +2 wk pre-birth with med cert | `DCPFLBase.get_max_document_duration`                                  |
| EOB approval method           | `DCPFLBase.approval_document_config` → `EXPLANATION_OF_BENEFITS_STATE` |
| Paid Leave Map band           | Template `pay_per_period` backfill (Fix 2)                             |

**Retest expectation (plan 10362, vaginal, continuous from EDD, no pre-EDD):**
DC PFL **12 weeks from EDD/leave start** in the Paid section (after template
backfill), overlapping DC FMLA medical then family spans.

---

## DC FMLA (Family and Medical Leave Act)

**Q:** Is the 6/8-week cap postpartum-only from EDD with cert-gated pre-EDD
separate, or does pre-EDD stack on top?

**Answer (Jon):**

- DC FMLA offers up to **16 weeks of medical leave** and up to **16 weeks of
  family leave** — **separate banks**, not a combined 12-week cap like federal
  FMLA.
- Routine pregnancy is **not bank-capped at 6–8 weeks** — that is what is
  **generally approved** for recovery based on delivery method when there are
  **no complications**, not the maximum medical entitlement.
- **Engineering interpretation:** the **medical bank stays 16 weeks**; the
  **routine birthing span** on continuous leave should apply ~**6 wk vaginal / 8
  wk C-section postpartum** to the medical portion, then **up to 16 wk bonding**
  on the family bank — matching Jon's original retest report.
- **Pre-birth:** must be for a **medical reason**; **med cert required** for DC
  FMLA to apply (existing `get_parental_min_start_date` / med-cert path).
- **Postpartum recovery:** may also require med cert unless the customer policy
  has **“No”** to requiring med cert for routine pregnancies
  (`Policy.birthing_med_cert_doc_required` / federal FMLA pattern). Similar to
  **federal FMLA** setup (except federal is 12 weeks total across reasons).

**Code implications:**

| Concept                                  | Implementation                                                                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 16 wk medical **bank**                   | Keep `get_base_max_duration` → 16 wk on `DCFMLAMedical` (do **not** reduce bank to 6/8)                                   |
| Routine **postpartum span** 6/8 from EDD | Add `get_birthing_recovery_max_end_date` on `DCFMLAMedical` (MN PFML END-boundary pattern)                                |
| Pre-EDD medical within medical bank      | Existing START boundary + med cert                                                                                        |
| 16 wk family bonding after medical       | Existing `DCFMLAFamily.get_dependency_min_start_date`                                                                     |
| Complications beyond 6/8 routine         | Can draw additional weeks from **16 wk medical bank** — follow-up med-cert extension logic (CT-style) if needed           |
| Tracking bank 16 wk medical              | Template `max_duration=16` is **correct** — **no** `VARIABLE_TIME_BENEFIT_RULE_PATHS` entry needed for birthing bank size |

**Federal FMLA parallel:** birthing split (disability then bonding), med cert
for pre-birth medical time, optional med cert for routine recovery per policy.
DC difference: **16 + 16 week banks** vs federal **12 week combined**.

---

## Surrogate

Jon did not address separately. Code treats surrogate as birthing
(`is_parental_birthing` / `BIRTHING_PARENTAL_ROLES`). Assume same routine
recovery span + 16 wk medical bank unless product says otherwise.

---

## Related docs

- [dc-fmla.md](./dc-fmla.md) — employer threshold, tracking method
- [dc-pfl.md](./dc-pfl.md) — tax contribution, shared 12-week bank
- [dc-fmla-pfl-qa-handoff.md](../../testing/dc-fmla-pfl-qa-handoff.md) — QA
  tables
