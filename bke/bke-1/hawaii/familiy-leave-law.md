Hawaii Family Leave Law (HI FLL) Program Program: Hawaii Family Leave Law (HI
FLL) L&C source: Hawaii Family Leave Law Logic + Tilt State Leave & Benefit
Sheet Status: existing rule (requirements audit) Available from: not date-gated
(law is in effect; flag controls rollout)

Benefit items in this program Hawaii Family Leave Law [uuid:
a79482a8-37ab-4b47-8035-ffc57c5e7707]: job-protection (unpaid). Covers bonding
and family caregiving only — does not cover the employee's own medical
condition. Income replacement during HI FLL leave may come from HI TDI (for
pregnancy disability) or FMLA concurrently. Behavior Similar to: CFRA (job
protection for family reasons, no pay; expanded family member list). Key
differences from FMLA: HI FLL has a much higher employer size threshold (100+ HI
employees), a shorter tenure requirement (6 consecutive months vs. 12 months),
no hours requirement, and a smaller entitlement (4 weeks vs. 12 weeks). Bonding
covers birth and adoption only — foster care is not covered. The entitlement
tracking is complex: if the employer uses a non-calendar-year method, the
employee is constrained by both the employer's chosen period and the calendar
year. Orientation only; full behavior is written out below.

awake

rule flag enabled (flag currently exists: enableBKEHawaiiFamli) employee lives
in the US employee works in Hawaii employer has 100 or more employees working in
Hawaii for each working day during 20 or more calendar weeks in the current or
preceding calendar year [data]

eligible (includes all awake criteria)

Employer coverage (must be met):

employer has 100 or more employees working in Hawaii for each working day during
20 or more calendar weeks in the current or preceding calendar year [data]

Employee eligibility (all must be true):

employee lives in the US employee works in Hawaii [data] employee has been
employed by this employer for at least 6 consecutive months immediately
preceding the leave start date [data] no hours-worked requirement

Qualifying reasons:

new child bonding (newborn or adoption only; foster care is not covered under HI
FLL) within 1 year of birth or placement [data] caregiving for a covered family
member with a serious health condition; covered family members include: child,
step-child, spouse, parent, step-parent, parent-in-law, sibling, step-sibling,
grandchild, grandparent, grandparent-in-law, stepparent, legal ward, legal
guardian [data]; or reciprocal beneficiary [blocked — this Hawaii-specific
relationship needs to be added to the leave survey; a dependent ticket is
needed; this ticket is blocked by that build] qualifying military exigency
related to the military service of employee's child, spouse, reciprocal
beneficiary, sibling, grandchild, or parent in the United States Armed Forces
[data — collected in platform; subject to LS review]

Note: HI FLL does not include military caregiver leave. Note also that
"reciprocal beneficiary" is a Hawaii-specific legal status.

spans

New child bonding (non-birthing parent):

max duration: 4 weeks per entitlement period (see tracking method) earliest
start: on or after date of birth or placement latest end: within 1 year of birth
or placement continuous or intermittent: auto-applied up to 4 weeks

Birthing parent (bonding — after medical recovery):

HI FLL bonding begins after the medical disability/recovery period (covered by
HI TDI or FMLA) max duration: 4 weeks from end of recovery; within 1 year of
birth

Caregiving:

max duration: 4 weeks per entitlement period med cert required; if FMLA runs
concurrently, a complete and sufficient FMLA med cert suffices; otherwise a
non-FMLA med cert is required continuous or intermittent: both permitted

Military exigency:

subject to LS review; documentation collected in platform

All benefits:

reductions / exhaustion: if HI FLL entitlement has been exhausted for the
applicable period, no spans (deny for exhaustion)

tracking method

Complex dual-constraint tracking (see open questions):

If the employerIf employer has chosen the calendarchosen calendar year as their
HI FLL leave year method: employee may not use more than 4 weeks in a calendar
year. If the employerIf employer has chosen any other method (fixed year,
measured forward, or rolling backward): employee may not use more than 4 weeks
in either the calendar year OR the employer's chosen period — whichever is more
restrictive.

Method is a company setting [data — uses the employer's configured FMLA leave
year method].

pay

Uses the 'unpaid or uncalculated' expression (job protection; no wage
replacement).

waiting period

None. Caps / banks 4 weeks per entitlement period Dual constraint applies if
employer uses a non-calendar-year method: employee cannot exceed 4 weeks in
either the calendar year or the employer's chosen leave year period Documents
New child bonding: no documentation required; auto-applied Caregiving: med cert
required; FMLA med cert suffices if FMLA runs concurrently Military exigency:
documentation collected in platform; subject to LS review Interaction with other
benefits (From our BKE/technical side there is no actual interaction. This is
just noting behavior under common circumstances.)

HI TDI: HI TDI covers the employee's own disability (including pregnancy medical
recovery); HI FLL covers the bonding or caregiving portion that follows. The two
may run sequentially for birthing parents. FMLA: runs concurrently with HI FLL
when the employee is FMLA-eligible and the qualifying reason overlaps. FMLA med
cert suffices for caregiving. STD / company leave: may run concurrently when
applicable. Reasoning shown to the reviewer employer below threshold: "Employer
does not meet the minimum Hawaii employee count required for HI FLL." does not
work in Hawaii: "HI FLL applies only to employees working in Hawaii." tenure not
met (6 consecutive months): "Employee has not been employed by this employer for
6 consecutive months." foster care not covered: "HI FLL covers bonding for birth
and adoption only. Foster care placements are not a qualifying reason."
entitlement exhausted: "HI FLL entitlement for this period has already been
used." Acceptance criteria Non-birthing parent bonding, continuous 4 weeks from
placement (adoption): employer has 110 HI employees, employee worked 6+
consecutive months, works in HI. Expected: eligible; auto-applied for 4 weeks.
Bonding for foster care placement: otherwise eligible. Expected: not eligible;
reasoning explains foster care is not covered under HI FLL. Birthing parent,
bonding after medical recovery: otherwise eligible. Expected: HI FLL bonding
begins after TDI/FMLA medical recovery; up to 4 weeks available within 1 year of
EDD. Caregiving for reciprocal beneficiary, continuous 3 weeks: otherwise
eligible, med cert provided. Expected: eligible; spans cover 3 weeks from HI FLL
bank. Caregiving, FMLA running concurrently: otherwise eligible. Expected:
eligible; FMLA med cert suffices; no separate HI FLL cert required. Employee has
5 consecutive months tenure: otherwise eligible. Expected: not eligible;
reasoning explains 6-month consecutive tenure requirement. EmployersEmployer
havehas 80 HI employees: employeesemployee otherwise eligible. Expected: not
eligible; reasoning explains employer below 100-employee threshold. HI FLL
entitlement exhausted for applicable period. Expected: no spans; deny for
exhaustion. Can you provide at least one example of these interacting tracking
methods that constrain available entitlement? (2–3 would be even more helpful)
Technical Note For some reason the python module for this benefit is named
`hawaii/famli.py` and the class `HawaiiFAMLI`. I’m guessing it was a copy/paste
oversight back when it was originally written. We should fix those names while
we’re at it. Probably `hawaii/fll.py` and `HawaiiFLL`. (And the test module
should also be renamed from `test_famli.py` to `test_fll.py`.) Open questions
Dual-constraint tracking: if the employer uses a non-calendar-year leave year
method, the employee's HI FLL entitlement is constrained by both the employer's
chosen period and the calendar year. Engineering will need to confirm how to
implement this — it is more complex than standard single-period tracking.
"Reciprocal beneficiary" relationship: this Hawaii-specific legal status needs
to be added to the leave survey as a caregiving relationship option. A dependent
ticket is needed; this ticket is blocked by that build. Foster care gap: HI FLL
covers birth and adoption but not foster care. If an employee requests bonding
for a foster placement, the system should explain that foster care is not a
qualifying reason under HI FLL, though other benefits (FMLA if eligible) may
apply.

Ben Spaulding Ben Spaulding 12:50 PM Jun 25 Earlier I said "No actual
interaction", but maybe that is wrong. I need to look if we have other separate
benefits that coordinate in this way. Eliaz Bobadilla Eliaz Bobadilla 2:24 PM
Jun 25 Replace: “Employer” with “Employers” Eliaz Bobadilla Eliaz Bobadilla
2:24 PM Jun 25 Replace: “has” with “have” Eliaz Bobadilla Eliaz Bobadilla
2:24 PM Jun 25 Replace: “employee” with “employees” Ben Spaulding Ben Spaulding
12:17 PM Jun 25 Add: “Can you provide at least one example of these interacting
tracking methods that constrain available …” Ben Spaulding Ben Spaulding
12:10 PM Jun 25 @katerina@ourtilt.com What methods are "non-calendar year"? Is
that only rolling back and event, while calendar year, fixed year, and rolling
forward are "calendar year"?
