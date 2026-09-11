# DC birthing leave — fix plan (PIE-429 / PIE-430 retest)

**Reported by:** Jon Nall (CT, IL) — plan
[10362](https://admin.ourtilt.dev/plan/?planId=10362&tab=PROGRAMS&subTab=leaveMap)\
**Investigated:** 2026-08-05 (dev)\
**Plan revised:** 2026-08-05 (Jon Slack answers incorporated)\
**Product decisions:**
[bke-1/dc-birthing-product-decisions.md](./bke-1/dc-birthing-product-decisions.md)

---

## Summary

| Issue                                       | Expected (Jon)                                                                           | Actual on plan 10362   | Fix                                    |
| ------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------- | -------------------------------------- |
| DC FMLA medical **span** (routine birthing) | ~6/8 wk **postpartum**, then family bonding                                              | ~16 wk medical span    | Fix 1: END boundary on `DCFMLAMedical` |
| DC FMLA medical **bank**                    | **16 wk** (not 6/8)                                                                      | 16 wk template ✓       | **No bank change**; no Fix 1b          |
| DC FMLA family                              | Up to **16 wk** bonding after medical                                                    | ~3 wk (cascade)        | Fixed by Fix 1                         |
| DC PFL                                      | **12 wk** from start (disability + bonding); +2 wk pre-EDD med → **14 max**; EOB pending | 6 wk; Unpaid section   | Fix 2 template backfill                |
| DC PFL vs FMLA timing                       | **Concurrent** — PFL covers pregnancy disability + bonding                               | PFL 6 wk from template | Fix 2; rule code largely OK            |

**Resolved (Jon, 2026-08-05):** Q3 PFL concurrent from leave start. Q4: 16 wk
medical bank + cert-gated pre-EDD; routine **span** 6/8 postpartum, not bank
cap.

---

## Product decisions (locked)

See
**[dc-birthing-product-decisions.md](./bke-1/dc-birthing-product-decisions.md)**
for full text.

### DC PFL

- Runs from leave/EDD start for **12 weeks**, covering **medical (disability)
  and bonding**.
- **+2 weeks** pre-birth when medically necessary (med cert) → **up to 14
  weeks**.
- All PFL time **pending until EOB** — Tilt is not the decision maker.

### DC FMLA

- **16 weeks medical bank** + **16 weeks family bank** (separate, unlike federal
  12 wk combined).
- **Routine approval:** ~6/8 wk **postpartum recovery span** by delivery method
  — **not** a 6/8 wk bank cap.
- Pre-EDD: medical reason + med cert. Postpartum recovery: med cert unless
  policy waives routine (`birthingMedCertDocRequired`).
- Federal FMLA parallel for cert gating; DC has larger separate banks.

---

## Dev verification (plan 10362)

**Leave 11566** — birthing vaginal, EDD/start **2026-09-01**, return
**2027-01-19**

```
Today                          After fixes (routine, no pre-EDD, no complications)
─────────────────────────────────────────────────────────────────────────────────────
DCFMLAMedical  ~16 wk         ~6 wk postpartum from EDD (medical bank still 16 wk)
DCFMLAFamily   ~3 wk          up to 16 wk bonding after medical ends
DCPFLParental  ~6 wk          12 wk from EDD in Paid section (+ EOB pending)
```

---

## Fix 1 — DC FMLA routine birthing span split (END boundary)

**File:** `backend/benefits/rules/dc/fmla.py`\
**Reference:** MN PFML
`_BirthingRecoveryBankMixin.get_birthing_recovery_max_end_date`
(`minnesota/pfml.py`)

### What to change

**Add** `get_birthing_recovery_max_end_date` on **`DCFMLAMedical`** — anchors
routine postpartum medical span at **EDD + standard recovery − 1 day** (6/8 wk).

**Do not** reduce `get_base_max_duration` to 6/8 for birthing — **medical bank
stays 16 weeks** (Jon: program offers 16 wk medical; 6/8 is routine approval,
not bank cap).

```python
@rules.rule_implementation
class DCFMLAMedical(DCFMLABaseClass):
    # ...

    @leave_type_register(types=[Leave.LeaveType.PARENTAL])
    @span_date_requirement(req_type=DateRequirementType.END, order=DateBoundary.CONFINING)
    def get_birthing_recovery_max_end_date(self, leave: Leave) -> date:
        if not leave.is_parental_birthing:
            return date.max
        self.require(leave.expected_due_date, description="expected_due_date")
        self.require(leave.birth_type, description="birth delivery method")
        self.reason("Routine medical recovery ends after standard pregnancy-disability period")
        recovery_end = leave.expected_due_date + self.get_standard_pregnancy_disability_duration(leave)
        return recovery_end - timedelta(days=1)
```

- **`DCFMLAFamily`:** unchanged (16 wk bank; bonding after medical via
  `get_dependency_min_start_date`).
- **Pre-EDD medical:** existing START + med cert; draws **medical bank** without
  shortening postpartum window (END boundary).
- **Complications beyond routine 6/8:** can use more of 16 wk medical bank —
  **follow-up** (med-cert extension; CT-style `get_max_document_duration`).
- **Docstring:** routine 6/8 postpartum span vs 16 wk medical bank vs 16 wk
  plain medical leaves.

### Fix 1b — **not required**

Previous plan registered `DC_FMLA_MEDICAL_BENEFIT_UUID` in
`VARIABLE_TIME_BENEFIT_RULE_PATHS` because we assumed a 6/8 wk bank. Jon
confirmed **16 wk medical bank** — template tracking is correct. **Do not add**
variable-duration registration unless we later change bank sizing.

### `birth_type`

- `None` / invalid → **Missing**
- Without `birth_type`, Family dependency may not wait for medical recovery
  (existing `MissingValue` fallback) — QA note

### Tests — `backend/benefits/rules/dc/tests/test_fmla.py`

| Item                                                     | Action                                                                                                             |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| All birthing/surrogate tests + fixture                   | Set `birth_type`                                                                                                   |
| **`test_max_duration`**                                  | Family → 16 wk; Medical plain → 16 wk; **Medical birthing → still 16 wk bank**; birthing no `birth_type` → Missing |
| `test_birthing_parental_medical_and_family_sequential`   | ~6 wk postpartum medical span + 16 wk family                                                                       |
| `test_birthing_pre_edd_family_spans_start_after_medical` | Pre-EDD med (with cert) + full 6 wk postpartum; family after recovery end                                          |
| `TestDCFMLAMedicalLateBirthConfirmation`                 | `birth_type` + END boundary                                                                                        |
| `test_surrogate_parental_medical_eligible`               | `birth_type` + span assertion                                                                                      |

### Tracking tests — `test_dc_fmla_tracking_persisted.py`

- **Keep** plain MEDICAL 16 wk bank tests.
- **Add** birthing routine: only ~6/8 wk **consumed** from 16 wk bank on
  continuous leave.
- **Add** pre-EDD birthing: postpartum portion still 6/8 from EDD; pre-EDD draws
  bank separately.
- **No** `test_durations.py` VARIABLE_TIME entry for DC FMLA medical.

### Follow-up (not this PR)

- Align postpartum med cert with `Policy.birthing_med_cert_doc_required`
  (federal FMLA pattern) if DC FMLA should waive cert for routine continuous
  bonding.
- Complications / extended medical beyond 6/8 routine recovery.

---

## Fix 2 — DC PFL template backfill (all environments)

**Rule code:** largely OK — 12 wk base + 2 wk doc extension + EOB already in
`pfl.py`.

### Backfill — `ensure_dc_pfl_template_config()`

Replace duplicate `ensure_dc_pfl_tracking_method()` calls in
`provision_child_benefits()`:

1. All **`DC_PFL_TEMPLATE_UUIDS`** — **parent medical row first** (bank anchor).
2. `max_duration=12` when drifted.
3. Pay placeholders for Leave Map: `pay_per_period=120`, etc. (UI grouping
   comment).
4. `tracking_method=ROLLING_FORWARD_SUNDAY`.

**Required tests:** `test_construct_child_benefits.py`

### Retest — DC PFL on plan 10362

- **12 weeks** from EDD/leave start (Paid section after backfill).
- EOB approval path on all PFL paycalc items (pending until EOB — product
  workflow).
- With pre-EDD med cert: up to **14 weeks** total (verify existing
  `test_parental_pre_birth_time_*`).

---

## Expected end state (plan 10362 — **locked**)

Vaginal, continuous from EDD, no complications, no pre-EDD:

```
|---- DC PFL (paid, 12 wk, EOB pending) -------------------|
|---- DC FMLA Medical (routine ~6 wk postpartum) --|
                                                  |-- DC FMLA Family (≤16 wk bonding) --…|
```

- DC FMLA: ~6 wk routine medical span + up to 16 wk family (16+16 banks).
- DC PFL: 12 wk concurrent from start (disability + bonding within PFL).
- Federal FMLA: unchanged.

---

## Implementation checklist

### Code

- [ ] `dc/fmla.py` — `get_birthing_recovery_max_end_date` on `DCFMLAMedical`;
      docstring; **keep** 16 wk `get_base_max_duration`
- [ ] `test_fmla.py` — birth_type on birthing tests; END boundary assertions;
      bank stays 16 wk
- [ ] `test_dc_fmla_tracking_persisted.py` — birthing consumption from 16 wk
      bank
- [ ] `construct_child_benefits.py` — `ensure_dc_pfl_template_config()` + wire
      into `provision_child_benefits()`
- [ ] `test_construct_child_benefits.py` — required

### Post-deploy (all envs)

- [ ] `construct_child_benefits --live-run`
- [ ] Verify parent `max_duration=12` + pay placeholders (all 3 UUIDs)
- [ ] `run_rules --leaves 11566 --ignore-checks` + **paycalc rebuild** on plan
      10362
- [ ] Leave Map: FMLA medical ~6 wk + family ≤16 wk; PFL 12 wk Paid; EOB on PFL

### Docs

- [x] `dc-birthing-product-decisions.md` — Jon answers
- [x] `dc-fmla.md` / `dc-pfl.md` — birthing sections
- [x] `dc-fmla-pfl-qa-handoff.md` — retest expectations

---

## Review log

| Pass | Date       | Key changes                                                                                                               |
| ---- | ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| 1–3  | 2026-08-05 | Engineering review iterations                                                                                             |
| 4    | 2026-08-05 | **Jon answers: 16 wk FMLA banks; routine 6/8 span via END boundary; PFL 12+2 concurrent; Fix 1b dropped; Q3/Q4 resolved** |

**Bottom line:** Implement Fix 1 (END boundary only, 16 wk bank unchanged) + Fix
2 (template backfill). Retest plan 10362 against locked end-state diagram above.
