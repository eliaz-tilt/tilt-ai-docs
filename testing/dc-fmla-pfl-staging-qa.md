# DC FMLA / DC PFL — staging QA runbook

**Tickets:** PIE-429 (DC FMLA), PIE-430 (DC PFL)\
**Environment:** `admin.ourtilt.cloud` / company subdomain on staging\
**Audience:** QA engineers running manual tests (and agents helping with setup)

---

## Before you start — read this

| Test scope                 | Can you use **HR policy UI only**?              | What else is required                                                      |
| -------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------- |
| **DC FMLA** (PIE-429)      | **Yes** — legacy Benefits / policy builder      | Tilt admin publish (plan + pay calc), flags                                |
| **DC PFL** (PIE-430)       | **No** — legacy policy has no PFML tax question | **Onboarding state config UI** _or_ Django admin (see below)               |
| **Benefits visible to HR** | N/A                                             | Must **publish pay calc** in Tilt admin (plan publish alone is not enough) |

**Important:** “Under Review” after the employee approves is **normal**. A Tilt
admin must still publish the plan, then publish the pay calc.

---

## URLs and access

| What                          | URL                                                | Who                   |
| ----------------------------- | -------------------------------------------------- | --------------------- |
| Tilt admin (LSM)              | https://admin.ourtilt.cloud                        | Tilt admin / LSM      |
| Company flags                 | https://admin.ourtilt.cloud/admin/flags/           | Tilt admin            |
| Django admin (fallback setup) | https://api.ourtilt.cloud/django-admin/            | Staff (`is_staff`)    |
| Onboarding — State Leave      | `https://<company-subdomain>/onboarding/states`    | HR (needs flag below) |
| Legacy policy builder         | HR → Benefits → States (or policy onboarding flow) | HR                    |

Example staging company from eng setup: **The DC Test Company**
(`thedccompany.com`).

---

## Part 1 — One-time company setup (ops / eng before QA)

Use this checklist once per test company. QA can verify each item before testing
leaves.

### 1.1 Feature flags

Enable on the **test company** at https://admin.ourtilt.cloud/admin/flags/

| Flag                               | Everyone = Yes?    | Per company?          | Required for                                     |
| ---------------------------------- | ------------------ | --------------------- | ------------------------------------------------ |
| `enableBKEDCFMLA`                  | **Yes** (required) | Not sufficient alone  | DC FMLA rules to run                             |
| `enableBKEDCPFL`                   | **Yes** (required) | Not sufficient alone  | DC PFL rules to run                              |
| `enableDCFmlaTracking`             | No                 | **Yes** — add company | DC FMLA tracking / Leave Tracker                 |
| `enableDCPflTracking`              | No                 | **Yes** — add company | DC PFL tracking / Leave Tracker                  |
| `enableOnboardingAndPolicyBuilder` | Either             | **Yes** — add company | HR UI at `/onboarding/states` (PFL tax question) |
| `enableBKEAutoCreatePaycalcs`      | Optional           | Per company           | Auto pay calc drafts (ABC tasks)                 |

**QA note:** If DC benefits show **Not Eligible** with no reasoning about flags,
confirm `enableBKEDCFMLA` / `enableBKEDCPFL` have **Everyone = Yes**.
Company-only enablement does **not** wake BKE rules.

**Verify:** Open a test leave in Tilt admin → plan sidebar → DC FMLA (Family or
Medical) should appear under **Eligible** (not asleep) when employee works in
DC.

---

### 1.2 Company policy — legacy HR UI (enough for **DC FMLA**)

Impersonate HR → open company **policy / Benefits → States** and confirm:

- [ ] Working state includes **District of Columbia**
- [ ] US headcount / FMLA 50+ questions answered **Yes**
- [ ] **Did you have 20+ employees working in D.C.…?** → **Yes**
      (`hasMetDcEmployerThreshold`)
- [ ] **How do you define the 24-month D.C. FMLA…?** → e.g. **24-month period
      measured forward** (`usDcFmlaTracking`) — only visible when
      `enableBKEDCFMLA` is on and DC is a working state
- [ ] Organization is **not** a public agency / school
- [ ] Company is **private** (`is_public_company = false` — usually “None of the
      above” on FMLA public/school question)

**Verify:** Tilt admin plan sidebar on a DC caregiver leave → **DC Family and
Medical Leave Act (Family)** = Eligible.

---

### 1.3 DC PFL tax contribution — **not** on legacy policy UI

This is the step QA often misses. Legacy policy **cannot** set the PFML tax
answer.

Choose **one** path:

#### Path A — HR UI (preferred if flag is on)

**Requires:** `enableOnboardingAndPolicyBuilder` on the company.

1. Log in as HR on the company subdomain.
2. Go to **`/onboarding/states`**\
   (alternate: **Settings → General → Edit** on State Leave section, if HR
   Policies V2 is enabled — same page).
3. Select **District of Columbia**.
4. Answer **both** questions:
   - **20+ employees in D.C. for 20+ workweeks** → **Yes**
   - **Contributing employer payroll taxes for D.C. PFML** → **Yes**
5. Click **Continue** / save the step.

**Verify:** Tilt admin plan sidebar → **DC Paid Family Leave** moves from
Missing/Not Eligible to **Eligible** (for caregiver / medical / parental leaves
in DC).

#### Path B — Django admin (when onboarding UI is not available)

**Requires:** Staff access to https://api.ourtilt.cloud/django-admin/

1. **Onboarding profile:** `onboarding/onboardingprofile` → create or confirm
   row linked to test company.
2. **State configuration:** `onboarding/stateconfiguration` → create/update for
   that profile:

```json
{
    "DC": {
        "has_20_employees": true,
        "contributes_pfml_payroll_taxes": true
    }
}
```

**Verify:** Same as Path A — DC PFL Eligible on plan sidebar.

---

### 1.4 Paycalc templates (ops — usually already on staging)

If benefits are eligible in sidebar but **missing from pay calc**, ask eng/ops
to confirm platform templates in Django admin (`legacy/paycalcitemtemplate`,
company = `-`):

| Benefit         | UUID                                   |
| --------------- | -------------------------------------- |
| DC FMLA Family  | `9177efa7-8501-4a0b-b869-ee21d0772b5c` |
| DC FMLA Medical | `26020214-feca-47c8-a76e-bd24928d74bb` |
| DC PFL          | `f4b8c3ad-d425-4a83-a82d-3d0e1f60638a` |

For **caregiver + spouse** PFL tests: template `caregiver_relationship` should
be **empty** (all allowed) or include **SPOUSE**.

---

### 1.5 Test employees (HR or Django admin)

Per employee used in the test matrix:

- [ ] Hire date ~2023, home + work state **DC**
- [ ] Hours worked last 12 months ≥ **1000**
- [ ] Salary entered (**Annually**, e.g. $75k)
- [ ] Enrolled: health, STD, LTD
- [ ] **Not** HR Admin / Payroll / Contractor
- [ ] Working days: 7 values Sun–Sat in minutes, e.g. `0,480,480,480,480,480,0`
- [ ] Pay schedule created (**Org Settings → Pay Periods**) and selected on
      leave form

Suggested matrix:

| Employee       | Leave type         | Primary benefits to verify               |
| -------------- | ------------------ | ---------------------------------------- |
| Caregiver test | Caregiver (Spouse) | DC FMLA **Family**, DC PFL, Federal FMLA |
| Medical test   | Medical            | DC FMLA **Medical**, DC PFL              |
| Parental test  | Parental           | DC FMLA **Family**, DC PFL               |

---

## Part 2 — Per-leave test flow (QA executes)

Repeat for each row in the test matrix.

### 2.1 Submit leave

1. **HR impersonation** → create/submit leave for employee.
2. Fill DC-specific fields (caregiver relationship, pay schedule, pay stubs if
   form requires PDFs for DC).
3. **Employee impersonation** → approve leave.

**Expected after employee approval:** HR dashboard stage = **Under Review** (not
Active). This is correct.

---

### 2.2 Tilt admin — publish plan

1. Log in to **admin.ourtilt.cloud** (not impersonating).
2. Find leave → open plan.
3. Sidebar → confirm expected benefits under **Eligible** / **Not Eligible**
   (see matrix below).
4. Review **Programs** / **Leave map** if ABC created a pay calc draft.
5. Click **Publish** in plan header.

**Expected:** HR dashboard stage = **Active** / **On-Leave**.

**Still expected:** HR **Benefits** tab may show **“No benefits”** — pay calc
not published yet.

---

### 2.3 Tilt admin — review and publish pay calc

If ABC ran, you may have a task: _“ABC has created a new pay calc draft”_.

1. Open plan → **Pay Calc** tab.
2. Confirm lines look reasonable (example for continuous caregiver 7/16–7/30
   return):

| Pay calc line           | Typical dates                    | Keep?                              |
| ----------------------- | -------------------------------- | ---------------------------------- |
| DC FMLA (Family)        | 7/16 – 7/29                      | Yes                                |
| Employee Wages (Salary) | Before / after leave pay periods | Yes (not shown in HR Benefits tab) |

3. If wrong → delete draft or remove bad lines.
4. Click **Publish** on pay calc.

**Expected:** HR leave drawer → **Benefits** tab shows DC FMLA (and PFL if
eligible). Employee wages lines do **not** appear as “benefits.”

---

### 2.4 Pass / fail criteria by leave type

| Leave type    | Should be Eligible                                      | Should be Not Eligible |
| ------------- | ------------------------------------------------------- | ---------------------- |
| **Caregiver** | DC FMLA **Family**, Federal FMLA, DC PFL (if 1.3 done)  | DC FMLA **Medical**    |
| **Medical**   | DC FMLA **Medical**, Federal FMLA, DC PFL (if 1.3 done) | DC FMLA **Family**     |
| **Parental**  | DC FMLA **Family**, DC PFL (if 1.3 done)                | —                      |

**Pass:** Published pay calc includes expected benefit lines; HR Benefits tab
shows them after pay calc publish; tracking tabs show usage when tracking flags
are on.

**Fail:** Log sidebar **Not Eligible** tooltip text + screenshot; note which
setup step was skipped.

---

## Part 3 — Troubleshooting (QA cheat sheet)

| What you see                                  | Likely cause                                          | What to do                                   |
| --------------------------------------------- | ----------------------------------------------------- | -------------------------------------------- |
| **Under Review** after employee approved      | Normal `APPROVED_EMPLOYEE`                            | Tilt admin → **Publish plan**                |
| **On-Leave** but **No benefits** in HR drawer | Pay calc still draft                                  | Tilt admin → **Pay Calc → Publish**          |
| DC FMLA OK, **DC PFL Missing**                | No `StateConfiguration` PFML tax answer               | Part **1.3** (onboarding UI or Django admin) |
| DC PFL Not Eligible (not Missing)             | Template caregiver list, public employer, or tax = No | Check sidebar tooltip; see 1.4 / policy      |
| No DC benefits at all                         | BKE flags not Everyone = Yes                          | Part **1.1**                                 |
| Pay Schedule “Not Set” on admin plan          | Calendar not on profile                               | Re-save leave with schedule or fix profile   |
| 100% plan steps incomplete                    | Normal before docs/steps generated                    | Not a blocker for pay calc QA                |

Hover the **warning icon** next to **Not Eligible** benefits in Tilt admin for
exact BKE reason text — paste into bug tickets.

---

## Part 4 — What QA cannot do UI-only today (known gaps)

Document these in test plans so QA knows when to escalate to eng/ops:

1. **DC PFL tax answer** — not on legacy Benefits → States; needs
   `/onboarding/states` (with `enableOnboardingAndPolicyBuilder`) or Django
   admin.
2. **Paycalc templates** — not created by app deploy; ops maintains platform
   templates in Django admin.
3. **BKE flags** — must be **Everyone = Yes**; different from tracking flags
   (per company).
4. **Two publishes** — plan publish and pay calc publish are separate steps by
   design.

No code fix is required for DC FMLA QA if Part 1.1–1.2 and 2.x are followed. DC
PFL QA **requires** Part 1.3 explicitly.

---

## Part 5 — Reference (for eng / agents)

- Rules: `backend/benefits/rules/dc/fmla.py`, `backend/benefits/rules/dc/pfl.py`
- PFL tax gate:
  `StateConfiguration.configurations.DC.contributes_pfml_payroll_taxes` only
  (`pfl.py`)
- HR benefits API: `published_paycalc` only
  (`backend/tracking/services/benefits.py`)
- Merged PRs: `#11119` (DC FMLA), `#11120` (DC PFL)

---

## QA sign-off checklist (copy into test run)

```
Company: _______________  Date: _______________  Tester: _______________

Setup
[ ] enableBKEDCFMLA + enableBKEDCPFL — Everyone = Yes
[ ] enableDCFmlaTracking + enableDCPflTracking — on company
[ ] Legacy policy: DC working state, 20+, FMLA 50+, usDcFmlaTracking
[ ] DC PFL: StateConfiguration OR /onboarding/states (PFML tax = Yes)
[ ] Templates verified (or eng confirmed)

Leaves
[ ] Caregiver — submit → EE approve → publish plan → publish pay calc → Benefits tab OK
[ ] Medical   — submit → EE approve → publish plan → publish pay calc → Benefits tab OK
[ ] Parental  — submit → EE approve → publish plan → publish pay calc → Benefits tab OK

Notes:
```
