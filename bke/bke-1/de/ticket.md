PIE-458

1

DE PFML: implement in the BKE 2.0 rules engine per current L&C spec (in-scope
requirements)

In Progress

Agents

Improve Story

Description

Goal Implement Delaware Paid Family and Medical Leave (DE PFML) in the BKE 2.0
rules engine (lane topology path), matching the current L&C spec captured below.
DE PFML benefits begin 1/1/2026 and apply to covered absences on or after that
date. Scoped to the in-scope requirements below; policy-gated / manual / post-V1
provisions are called out under Out of scope.

Benefit UUID (income replacement): 1ecd3694-c82a-4b82-88a9-dbf93923aa53. Job
Protection UUID: DE_PFML_JOB_PROTECTION_BENEFIT_UUID
(a83faefc-f953-497b-bb77-de15d4fa855b) — one-time JP parent template create
still required per env before construct_child_benefits.

L&C sources:

Delaware PFML - Leave Logic

Tilt State Leave & Benefit Sheet

Behavior orientation: similar to WA PFML / ME PFML (paid leave with concurrent
job protection). Key DE-specific differences: tiered employer coverage by
Delaware employee count (10–24 employees = parental only; 25+ = all four
qualifying reasons); caregiving limited to parent/child/spouse (FMLA scope);
non-parental reasons individually capped at 6 weeks per 24-month period plus a
12-week annual ceiling; workers' comp recipients excluded from
own-serious-health-condition; intermittent parental requires employer approval;
minimum intermittent increment is 1 full workday.

PR: https://github.com/ourtilt/tilt-repo/pull/11231

In scope (V1) Awake gates (flag, works in DE, start ≥ 1/1/2026, employer ≥ 10 DE
employees via deEmployerTier)

Tiered employer coverage (10–24 = parental only; 25+ = all four reasons)

Employee eligibility: DE work, 12-month tenure, 1,250 hours, not
seasonal/casual/contractor (isNotDePfmlExcluded)

Qualifying reasons: parental/bonding, own serious health condition, caregiving
(parent/child/spouse), military exigency — gated by tier

Workers' comp exclusion for own serious health condition (Leave column +
fail-closed lever; survey UI follow-up)

Continuous spans; V1 parental windowed from childBirth (see OOS for post-V1
medical/date-shift work)

Independent measured-forward periods (parental 12 mo;
medical/caregiving/exigency 24 mo each) + 12-week annual ceiling
(independentWindow)

Per-reason 6-week / 24-month caps + 12-week annual ceiling; deny for exhaustion

Job protection benefit running concurrently

Reviewer reasoning strings

Acceptance criteria 1–10 (topology scenarios + DE lever tests)

Out of scope / policy-gated / post-V1 Product-confirmed post-V1 (2026-07-22)
Pre-birth → medical split — days before birth on medical bank/lane; parental
from birth

Birthing-parent medical 6–8 weeks post EDD/ADD — Product clarification; not
implemented in current V1 catalog

EDD → ADD date-shift re-anchoring (awareness brief / FMLA-like benefit status
shifts) — treat as post-V1 until Product reopens

10–24 tier + pre-birth: pre-birth days are ineligible for DE PFML (no exception)

From L&C / Product OOS for V1 SaaS 60% DE wages per quarter — V1 relies on
workingState is DE + onboarding deEmployerTier; no separate wage-share fact

Voluntary 10–24 tier extension to non-parental reasons (needs company policy
setting) [intake: policy]

Tier-change notifications / org-settings disclaimers when headcount/tier updates
(ops/help-text; not engine automation)

Accurate intermittent vs reduced-schedule increment split — V1 allows both under
DE PFML; finer increment rules later

Same-employer-couples combined 12-week/52-week cap (employer option) [intake:
policy]

Intermittent parental employer-approval toggle (needs company policy setting)
[intake: policy] — lane gate + fail-closed placeholder lever exist for AC7

Public-sector exclusion (Title 29 §5903(17)a / Title 14) beyond
is_de_pfml_excluded if a dedicated field is needed [data / manual]

Private-plan option (not in L&C; confirm)

Workers' comp survey UI — backend field + submit validation done; UI collection
is a follow-up (until then unanswered → medical fails closed)

Deploy / ops (not blocking catalog PR) One-time JP parent PaycalcItemTemplate
create + construct_child_benefits --live-run per environment

Enable enableBKEDelawarePFML per rollout plan

Resolved open questions

# 

Item

Resolution

Independent measured-forward per leave type

Done — independentWindow: true on paid leaf banks under shared de-pfml-annual

Employer tier source / timing

Manual company policy us_de_pfml_coverage_tier → deEmployerTier; quarterly
upgrade/downgrade clocks are ops guidance, not V1 engine

Job Protection UUID

Provisioned as DE_PFML_JOB_PROTECTION_BENEFIT_UUID

Workers' comp data path

Dedicated Leave column + lever; survey UI still follow-up

Acceptance criteria (in scope) Parental, birth, continuous 12 weeks, birthing
parent; employer 15 DE employees; 12+ mo & 1,250+ hrs; works in DE. Expected:
eligible; parental auto-applied from date of birth; no medical period.

Own serious health condition; employer 20 DE employees (10–24 tier); otherwise
eligible. Expected: not eligible; parental-only tier.

Caregiving (child); employer 30 DE employees; med cert provided. Expected:
eligible; up to 6 weeks / 24-month; subject to 12-week annual ceiling.

Medical; employee receiving workers' comp. Expected: not eligible; WC exclusion.

Medical; 6 weeks already used in last 24 months for own condition. Expected:
24-month medical entitlement exhausted; no spans.

Parental + caregiving same application year; 10 weeks parental used; requests 4
weeks caregiving. Expected: only 2 weeks available (12-week annual ceiling);
spans limited to 2 weeks.

Intermittent parental; employer has not approved. Expected: not eligible for
intermittent parental; approval required.

Tenure 10 months. Expected: not eligible; 12-month tenure not met.

Leave start 12/15/2025 (before launch). Expected: not eligible; DE PFML not yet
in effect.

Non-birthing parent, adoption, within 1 year of placement. Expected: eligible;
auto-applied from placement date.

Definition of done DE PFML implemented in BKE 2.0 (topology + banks/spans +
tracking + job protection) covering in-scope requirements.

In-scope acceptance criteria (1–10) pass.

Spec/code deltas or deferred items documented under Out of scope (including
Product 2026-07-22 post-V1 date-shift / pre-birth medical).

Rule flag enabled for configured testing companies once in-scope criteria pass;
otherwise parked pending direction and flag not flipped.
