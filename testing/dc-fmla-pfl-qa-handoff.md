# DC FMLA / PFL — QA handoff (Eliaz + QA tester)

**Tickets:** PIE-429 (DC FMLA), PIE-430 (DC PFL)\
**Staging:** https://admin.ourtilt.cloud

Use this doc in two ways:

1. **Section A** — copy/paste into Slack for the QA tester (non-technical).
2. **Section B** — Eliaz setup checklist before handing off (flags, Django,
   company policy).

---

## A. Slack message for QA (copy below)

---

Hey — some setup notes for DC leave testing so you can run through everything on
your own.

I’ll handle all the backend setup (new test company + flags). You shouldn’t need
Django or anything technical — just HR login, employee login, and Tilt admin
when it’s time to publish.

**Two companies you can use:**

1. **The DC Test Company** — already set up (`thedccompany.com`). Example
   employees: `folk@`, `cargiver@`
2. **A fresh company I’m creating for you** — I’ll send you the name + HR login
   once it’s ready

Both should work the same way for testing.

---

**What you’ll be testing**

- DC FMLA (family + medical leaves)
- DC Paid Family Leave (PFL)
- That benefits show up correctly after a leave is approved and published

---

**How to run one full test (same steps every time)**

1. **Log in as HR** → create and submit a leave for the employee
   - Caregiver (spouse), Medical, or Parental — try each type if you can
   - Make sure a pay schedule is selected on the form

2. **Log in as the employee** → approve the leave
   - After this, HR may show **“Under Review”** — that’s normal, not a bug

3. **Log in to Tilt admin** (https://admin.ourtilt.cloud) — ping me if you need
   access
   - Open the leave → check the sidebar: you should see DC benefits listed as
     eligible
   - Click **Publish** on the plan → leave should go **Active / On-Leave**

4. **Still in Tilt admin** → open the **Pay Calc** tab
   - Review the draft (DC FMLA line + wage lines is usually correct)
   - Click **Publish** on the pay calc
   - **This step is required** — without it, HR will show **“No benefits”** even
     when the person is on leave

5. **Back as HR** → open the leave drawer → **Benefits** tab
   - You should now see DC FMLA (and PFL where applicable)

---

**What “good” looks like**

| Leave type              | Benefits you should see                                                                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Caregiver               | DC FMLA (Family), DC PFL, Federal FMLA                                                                                                                          |
| Medical                 | DC FMLA (Medical), DC PFL, Federal FMLA                                                                                                                         |
| Parental (birthing)     | DC FMLA (Medical) ~6/8 wk routine postpartum span, DC FMLA (Family) ≤16 wk bonding, DC PFL 12 wk from start (Paid; EOB pending). +2 wk PFL pre-EDD if med cert. |
| Parental (non-birthing) | DC FMLA (Family), DC PFL                                                                                                                                        |

Employee wage lines on the pay calc are expected — they just don’t show in the
Benefits tab.

**Birthing parental (post-fix, Jon 2026-08-05):**

- **DC FMLA Medical:** routine ~6 wk vaginal / 8 wk C-section **postpartum
  span** (16 wk medical **bank** still exists for complications).
- **DC FMLA Family:** up to 16 wk bonding starting after medical recovery ends.
- **DC PFL:** **12 wk from leave/EDD start** (covers disability + bonding); up
  to **14 wk** with pre-birth medical time + med cert. All PFL **pending until
  EOB** — Tilt is not the decision maker.
- After template backfill, **rebuild paycalc** on the plan — `run_rules` alone
  does not refresh Leave Map rows.
- Missing `birth_type` on birthing leave → Medical may show Missing; Family
  bonding may not wait for medical recovery until birth type is set.

---

**If something looks wrong (usually not a product bug)**

- **“Under Review” after employee approves** → plan still needs to be published
  in Tilt admin
- **On leave but “No benefits”** → pay calc still needs to be published (step 4
  above)
- **DC PFL missing or not eligible** → ping me — that’s company setup on my
  side, not something you fix
- **Not sure why something failed?** → screenshot the leave in Tilt admin
  (especially the sidebar) and send it over

---

**What I’ll have done before you start**

- Flags turned on for both companies
- Company policy set (DC state, employer size questions, etc.)
- DC PFL setup (the part that isn’t in the normal policy screen)
- Test employees with hire date, salary, hours, pay schedule

You focus on the leave flow + publish steps above. If anything blocks you, just
ping me with a screenshot.

---

## B. Eliaz setup checklist (do this before QA starts)

Run this for **each** company the QA tester will use:

- [ ] The DC Test Company (`thedccompany.com`)
- [ ] New QA company (fill in: `_______________`)

When done, send QA the company URL, HR login, and employee logins for caregiver
/ medical / parental tests.

---

### B.1 Feature flags

**Where:** https://admin.ourtilt.cloud/admin/flags/

| Flag                               | How to set                                                 | Why                                             |
| ---------------------------------- | ---------------------------------------------------------- | ----------------------------------------------- |
| `enableBKEDCFMLA`                  | **Everyone = Yes**                                         | DC FMLA rules won’t run if this is company-only |
| `enableBKEDCPFL`                   | **Everyone = Yes**                                         | DC PFL rules won’t run if this is company-only  |
| `enableDCFmlaTracking`             | Add **each test company**                                  | DC FMLA tracking / Leave Tracker                |
| `enableDCPflTracking`              | Add **each test company**                                  | DC PFL tracking / Leave Tracker                 |
| `enableBKEAutoCreatePaycalcs`      | Add **each test company** (recommended)                    | Auto pay calc drafts so QA gets ABC tasks       |
| `enableOnboardingAndPolicyBuilder` | Optional — add company if QA will use `/onboarding/states` | Not required if you set PFL in Django (B.3)     |

**Important:** `enableBKEDCFMLA` and `enableBKEDCPFL` must have **Everyone =
Yes**. Per-company enablement alone does nothing for these two.

**Verify:** Impersonate HR → submit a test leave → Tilt admin plan sidebar → DC
FMLA and DC PFL should not be “asleep.”

---

### B.2 Company policy (HR UI or impersonation)

Impersonate HR → **Benefits → States** (legacy policy builder) and set:

- [ ] Working state includes **District of Columbia**
- [ ] FMLA 50+ employees = **Yes**
- [ ] **20+ employees working in D.C.** = **Yes**
- [ ] **24-month D.C. FMLA tracking period** = e.g. **24-month period measured
      forward**
- [ ] Not a public agency / school board
- [ ] Private employer (not `is_public_company`)

This covers **DC FMLA**. It does **not** cover DC PFL tax — do B.3 next.

**Verify:** Tilt admin on a DC caregiver leave → **DC Family and Medical Leave
Act (Family)** = Eligible.

---

### B.3 DC PFL setup (Django — QA cannot do this in legacy policy UI)

Legacy policy has **no** “contributing PFML payroll taxes” question. Set it in
Django so QA never has to.

**Where:** https://api.ourtilt.cloud/django-admin/

1. `onboarding/onboardingprofile` → create or link profile to the test company
2. `onboarding/stateconfiguration` → set configurations for that profile:

```json
{
    "DC": {
        "has_20_employees": true,
        "contributes_pfml_payroll_taxes": true
    }
}
```

**Verify:** Tilt admin plan sidebar on caregiver / medical / parental leave →
**DC Paid Family Leave** = Eligible (not Missing).

---

### B.4 Pay schedule + test employees

Per company, before QA runs leaves:

**Org settings**

- [ ] Pay schedule / pay periods created (**Org Settings → Pay Periods**)

**Each test employee** (caregiver, medical, parental — at least one each)

- [ ] Hire date ~2023
- [ ] Home + work state **DC**
- [ ] Hours worked last 12 months ≥ **1000**
- [ ] Salary (**Annually**, e.g. $75k)
- [ ] Enrolled: health, STD, LTD
- [ ] Not HR Admin / Payroll / Contractor
- [ ] Working days: e.g. `0,480,480,480,480,480,0` (Sun–Sat minutes)

Send QA the employee emails and which leave type each is for.

---

### B.5 Platform paycalc templates (staging — usually already OK)

Only check if benefits are **Eligible** in sidebar but **missing from pay
calc**.

Django admin → `legacy/paycalcitemtemplate` (company = `-`):

| Benefit         | UUID                                   |
| --------------- | -------------------------------------- |
| DC FMLA Family  | `9177efa7-8501-4a0b-b869-ee21d0772b5c` |
| DC FMLA Medical | `26020214-feca-47c8-a76e-bd24928d74bb` |
| DC PFL          | `f4b8c3ad-d425-4a83-a82d-3d0e1f60638a` |

For caregiver + spouse: template `caregiver_relationship` empty or includes
**SPOUSE**.

---

### B.6 Handoff sign-off (Eliaz)

Before messaging QA:

- [ ] Both companies pass B.1–B.4
- [ ] Spot-check: one caregiver leave in Tilt admin sidebar shows DC FMLA
      Family + DC PFL Eligible **before** publish
- [ ] QA has Tilt admin access (or you’ll publish for them — clarify in Slack)
- [ ] Slack message (Section A) sent with company URLs + logins

---

## Quick reference — who does what

| Task                                   | Eliaz    | QA tester |
| -------------------------------------- | -------- | --------- |
| Flags (`enableBKEDCFMLA`, etc.)        | ✓        |           |
| Django StateConfiguration (PFL tax)    | ✓        |           |
| Company policy (DC 20+, FMLA tracking) | ✓        |           |
| Test employees + pay schedule          | ✓        |           |
| Submit leave / employee approve        |          | ✓         |
| Publish plan + pay calc in Tilt admin  | ✓ or QA* | ✓         |
| Verify HR Benefits tab                 |          | ✓         |

\*Give QA Tilt admin access if they should publish themselves; otherwise you
publish after they submit + approve.

---

## Related

- Full technical runbook:
  [dc-fmla-pfl-staging-qa.md](./dc-fmla-pfl-staging-qa.md)
