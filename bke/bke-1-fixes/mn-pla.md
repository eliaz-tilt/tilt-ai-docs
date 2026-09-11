Minnesota Parental Leave Act - Testing with BKE 1.0 and Prior to Path to SaaS
data points only\
Error or Flag	Area / Test IDs	Status	What Failed / Issue Identified	Business /
Compliance Impact	Ongoing Discussion Needed	LQM Notes Flagged	Pregnancy
incapacity vs. prenatal appointments	Started / Review Required	BKE needs to
distinguish between certified pregnancy incapacity (which reduces the bank) and
prenatal appointments (which are protected but do not reduce the
bank).	Incorrect deductions could reduce available post-birth
entitlement.	Confirm how leave reason data drives eligibility and bank
calculations. Validate prenatal appointment carve-out handling.	"Presented to
BKE team and discussions are required to how support could be provided as we do
not currently collect any pre-birth intermittent leave reasons (such as for
incap or treatments), thus being a blocker for any immediate automation support.

Discussed in BKE Garage here" Error	Reduced schedule calculations	Started /
Review Required	Reduced schedule scenarios appear to cap MN PLA at 12 weeks /
240 hours instead of extending based on the employee’s normal
schedule.	Part-time and reduced schedule employees may receive incorrect
entitlement calculations.	Validate week-to-hour conversion logic and how MN PLA
should display entitlement (hours vs. days vs. weeks).	Being discussed in BKE
Garage here Flagged	Delivery date changes / leave re-segmentation	Review
Required	Identified an opportunity to standardize expected behavior across state
leave entitlements when a delivery date changes after leave has begun. Different
programs may handle pre-birth and post-birth leave segmentation differently, and
expected BKE behavior should be consistently defined.	Inconsistent handling
across leave programs could lead to varying entitlement recommendations, leave
segment classifications, and user expectations when delivery dates change during
an active leave.	Align on a standardized approach for how BKE should handle
delivery date changes across all applicable state leave programs. Confirm
whether leave segments should be reclassified or remain tied to the original
leave timeline, based on each program's compliance requirements and an overall
product strategy.	Katerina is working on a scope ticket to present requirement
and impact with ongoing BKE work influence Error	Minnesota Parental Leave Act
pre-birth eligibility	Review Required	BKE is incorrectly recommending MN PLA for
pre-birth leave requested for non-medical reasons. Pre-birth leave that is not
related to a qualifying pregnancy-related medical incapacity should not trigger
an MN PLA entitlement recommendation.	Employees and employers may receive
incorrect MN PLA leave recommendations, resulting in leave being designated
under MN PLA when the reported absence is not eligible.	Confirm that MN PLA is
not recommended for pre-birth leave requested for non-medical reasons and is
only applied when the reported absence qualifies under the applicable
eligibility requirements.	Being discussed in BKE Garage here Flagged	Mid-leave
reason changes / entitlement re-derivation	Review Required	Need to determine how
BKE should handle leave reason changes that occur during an active leave. The
system should re-evaluate the applicable leave path without issuing a new
entitlement bank. A key scenario is when a leave begins under one reason (e.g.,
parental leave) and later transitions to another reason (e.g., medical leave)
due to a change in circumstances.	Incorrect handling could result in employees
receiving duplicate entitlement, losing previously used entitlement, or
requiring unnecessary creation of a new leave plan when the existing leave event
should continue.	Confirm approach for managing reason changes within the same
leave event. Determine whether BKE should update the leave reason in place while
preserving prior MN PLA usage and applying the remaining available entitlement
under the same event ceiling.	Need to have a broader conversation with the team.
Believe that this will require messaging support for v1 for now.
Flagged	Intermittent MN PLA leave recommendation	Started / Review Required	BKE
is no longer recommending MN PLA when the leave schedule is intermittent.
However, MN PLA leave may be taken intermittently with employer
approval.	Employees may not be properly identified as eligible for MN PLA
protections when intermittent leave is requested, potentially resulting in
missed statutory leave recommendations or incorrect leave handling.	Confirm
whether BKE should continue recommending MN PLA for intermittent leave scenarios
when employer approval is required. Validate how employer approval requirements
should be represented in eligibility and recommendation logic.	Being discussed
in BKE Garage here

## Engineering triage (BKE 1.0 pass)

Use this section so QA and engineering do not re-file work that is **done**,
**intentional v1**, or **blocked**.

### Open question for L&C

When `pre_birth_time_reason` is **nesting (non-medical)**, should an **accepted
med cert** that only covers pre-EDD time still drive **MN PLA** spans before the
due date, or should MPLA follow **MN PFML / federal FMLA** and treat nesting as
non-medical pre-birth (complications modeled by switching the survey to
**medical** pre-birth)? Code change in this repo assumes **survey nesting wins**
unless L&C says otherwise.

### Row status

| Spreadsheet issue                               | Engineering status                                  | Ticket / note                                                                                 |
| ----------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Pre-birth non-medical MN PLA                    | **Done on main** — verify in QA                     | PIE-446 (#11226); MPLA NEST + stale cert parity ships with **#11344** (shared nesting helper) |
| Pregnancy incapacity vs prenatal appointments   | **Blocked** — no intermittent pre-birth reason data | Messaging / disclaimers (Kat); not BKE rules v1                                               |
| Reduced schedule / 12 wk vs 240 hr              | **Intentional v1**                                  | PIE-463 (#11249); Garage/L&C before re-enabling reduced-schedule spans                        |
| Intermittent MN PLA                             | **Intentional v1**                                  | PIE-463; employer approval descoped — messaging only                                          |
| Delivery date re-segmentation                   | **Blocked** — product scope                         | Katerina cross-program ticket                                                                 |
| Mid-leave reason changes                        | **Blocked** — messaging v1                          | No bank re-derivation in this pass                                                            |
| FMLA broken when survey → nesting (Slack below) | **Separate fix** — not MN PLA                       | PR #11344 (federal FMLA)                                                                      |

### QA retest checklist (MN PLA)

- [ ] Birthing parental, leave starts before EDD, **nesting**, **no** med cert →
      MPLA spans **from due date only** (PIE-446).
- [ ] Same scenario with a **stale pre-EDD med cert** after survey changed
      medical → nesting → confirm against L&C (MPLA NEST parity if merged).
- [ ] Intermittent or reduced/partial-day schedule → **no MPLA spans**;
      reasoning mentions intermittent/reduced (PIE-463); expect **messaging**
      not auto-recommendation for employer-approved intermittent.
- [ ] Federal **FMLA** nesting scenario (Christian leave plan) → validate via
      **#11344**, not MN PLA rules.

### Related MN PFML (not PLA)

- Partial-day intermittent MN PFML → merge/rebase **PIE-469** / PR **#11269**
  (Dustin). Same change is **ported on `mn-pla-bke-fixes`** for QA convenience
  until #11269 lands; do not maintain a third duplicate branch.

Extra context:

Christian Castorena  [11:51 AM] Leave Plan: Here State Leave: MN PLA :dulynoted:
BKE Testing Q:

Hey @Kat(erina) and @dustin!

Curious as I just reviewed the MN MPLA rule ticket and noticed my open question
was still floating around. Did we apply any logic around how prenatal
appointments are covered under MN MPLA but do not deduct from the 12 weeks of
MPLA?

I was thinking about birthing parents who may request intermittent leave prior
to their expected delivery date for prenatal appointments. I also understand we
are extremely limited in collecting any reason for intermittent absences, which
makes it difficult to determine whether pre-birth time is being reported for
prenatal appointments versus pregnancy-related incapacity.

I built an intermittent MN PLA leave scenario and noticed that any intermittent
absences are currently drawing down from the 12 weeks of MPLA. My thought is
that if those pre-birth intermittent absences were for prenatal appointments,
the employee would otherwise still be entitled to the full 12-week
balance. (edited)  28 repliesChristian Castorena  [11:52 AM] I’m thinking this
may need to be a disclaimer for HR but curious to how we approach such
:letmethinkaboutit: Katerina Marcotte  [11:53 AM] y'all have time to chat about
this? [11:53 AM]i'm about to be available Christian Castorena  [11:53 AM] Give
me 1 minute and happy to! Katerina Marcotte  [11:53 AM] sounds good [11:53
AM]i'll ping you all when i'm done Dustin Wyatt  [11:53 AM] sure. [11:54 AM]I
think I implemented MN MPLA like 4 years ago, so I'll be rusty [11:54 AM](ok,
that just what it feels like) Katerina Marcotte  [11:54 AM] we've been through
so much Christian Castorena  [11:54 AM] Free whenever! Dustin Wyatt  [11:55 AM]
well, I'm going to make a cup of tea since Kat is rudely making us wait [11:55
AM]brb Katerina Marcotte  [12:07 PM] gimme just one more minute to be rude!
Christian Castorena  [12:28 PM] Not sure if I missed a call or huddle but do let
me know if anything was needed on my end! Katerina Marcotte  [12:29 PM] you did
not, i got pulled into another conversation Dustin Wyatt  [12:29 PM] do I have
15-30 minutes to get some lunch? Katerina Marcotte  [12:29 PM] probably Dustin
Wyatt  [12:29 PM] or should we chat first? [12:29 PM]ok, I'm lunchin'. Just ping
me if we need to chat sooner! Katerina Marcotte  [12:58 PM] so so sorry folks!
convo has finished, i still have free time for the next half hour. are y'all
still available? Dustin Wyatt  [12:59 PM] i have never been more available [1:01
PM]I even refreshed my memory some about what I implemented and open questions I
have now. So I'm not only available, I'm ready Katerina Marcotte  [1:05 PM] wow!
[1:05 PM]let's huddle! Christian Castorena  [1:07 PM] @Kat(erina), can you
resend the huddle request? I was typing and think I accidentally declined
:sweat_smile: Katerina Marcotte  [1:08 PM] suuuuure Christian Castorena  [1:09
PM] https://meet.google.com/ixx-ugtb-nuxmeet.google.comMeetReal-time meetings by
Google. Using your browser, share your video, desktop, and presentations with
teammates and customers.

[3:40 PM]I just realized when Josiah shared his screen that it was an open
question on the DE PFML ticket. image.png Dustin Wyatt  [3:41 PM] I do not know
the answer really. I just implement what I'm told! (sometimes I misunderstand
what I'm told as well) Christian Castorena  [3:43 PM] No, no! I could also be
misunderstanding.

@Kat(erina), do you perhaps any context around BKE and intermittent leaves that
require employer approval for bonding? Is the intent that BKE will recommend but
it’s at the users discretion to apply the leave entitlement or not? Christian
Castorena  [5:43 PM] Noting that I was testing intermittent bonding leave for MN
PFML and noticed that we are no longer recommending MN PLA for intermittent
bonding. But MN PLA can be taken intermittently with employer approval
:brain-scratch: image.png Katerina Marcotte  [5:47 PM] we descoped any work
related to employer approval, since that requires a company policy question.
this would be something on my list to provide messaging. Christian
Castorena  [5:52 PM] Ah okay, thanks for that notice, Kat! @Jon Nall tagging
just in case we need to give Erin or Kelly a heads up for any Path to SaaS LC
articles or Enablement item. Jon Nall (CT, IL)  [8:40 AM] Thanks @Christian -
are we tracking these decisions (and messaging needs) anywhere? Like maybe in
your Disclaimers doc?

@Kat(erina) - do we have a plan for how messaging would work? Would it be a
banner that pops up when an employee requests intermittent bonding and MN PFML
applies? I'm trying to understand how we will ensure the right people see this
information at the appropriate time. Christian Castorena  [12:52 PM]
@Kat(erina) - just retagging for fresh visibility as we are chatting about this.

This relates to scenarios where a state leave entitlement requires employer
approval. BKE should not automatically recommend the entitlement until the
required employer approval has been confirmed, particularly for bonding leave.

Christian Castorena  [12:10 PM] Leave Plan: Here State Leave: MN PLA :dulynoted:
BKE Testing Q:

MN PLA appears to be applying to any pre-birth leave prior to the EDD for
non-medical reasons. However, MN PLA does not provide leave for non-medical
reasons prior to birth. 2 repliesChristian Castorena  [12:10 PM] @Kat(erina),
I’m not sure if this is a hiccup, but when I initially tested this leave plan, I
had the plan set up with pre-birth leave as medically necessary, and MN PLA and
FMLA were applying correctly. Once I adjusted the leave survey to reflect that
the leave was not medically necessary, it looks like FMLA became broken in BKE.
:brain-scratch:

You can view the version history on the Programs tab to see that FMLA was
previously applying correctly.

Let me know if you have any thoughts here! Dustin Wyatt  [6:00 PM] This is a
demo of a change that should be merged when someone gets a chance to review. I
believe it addresses the "leave for non-medical reasons prior to birth" problem
raised here.

I'll let you know when this part is ready for
testing.pie446-mpla-pre-edd-demo.mp4

[3:40 PM]I just realized when Josiah shared his screen that it was an open
question on the DE PFML ticket. image.png Dustin Wyatt  [3:41 PM] I do not know
the answer really. I just implement what I'm told! (sometimes I misunderstand
what I'm told as well) Christian Castorena  [3:43 PM] No, no! I could also be
misunderstanding.

@Kat(erina), do you perhaps any context around BKE and intermittent leaves that
require employer approval for bonding? Is the intent that BKE will recommend but
it’s at the users discretion to apply the leave entitlement or not? Christian
Castorena  [5:43 PM] Noting that I was testing intermittent bonding leave for MN
PFML and noticed that we are no longer recommending MN PLA for intermittent
bonding. But MN PLA can be taken intermittently with employer approval
:brain-scratch: image.png Katerina Marcotte  [5:47 PM] we descoped any work
related to employer approval, since that requires a company policy question.
this would be something on my list to provide messaging. Christian
Castorena  [5:52 PM] Ah okay, thanks for that notice, Kat! @Jon Nall tagging
just in case we need to give Erin or Kelly a heads up for any Path to SaaS LC
articles or Enablement item. Jon Nall (CT, IL)  [8:40 AM] Thanks @Christian -
are we tracking these decisions (and messaging needs) anywhere? Like maybe in
your Disclaimers doc?

@Kat(erina) - do we have a plan for how messaging would work? Would it be a
banner that pops up when an employee requests intermittent bonding and MN PFML
applies? I'm trying to understand how we will ensure the right people see this
information at the appropriate time. Christian Castorena  [12:52 PM]
@Kat(erina) - just retagging for fresh visibility as we are chatting about this.

This relates to scenarios where a state leave entitlement requires employer
approval. BKE should not automatically recommend the entitlement until the
required employer approval has been confirmed, particularly for bonding leave

PIE-469: Recommend MN PFML intermittent leave on partial days #11269 Draft
dmwyatt wants to merge 3 commits into main from
dmwyatt/PIE-469/mn-pfml-intermittent-partial-days +68 -209 Lines changed: 68
additions & 209 deletions Conversation0 (0) Commits3 (3) Checks13 (13) Files
changed4 (4) Draft PIE-469: Recommend MN PFML intermittent leave on partial
days#11269 dmwyatt wants to merge 3 commits into main from
dmwyatt/PIE-469/mn-pfml-intermittent-partial-days Conversation @dmwyatt dmwyatt
commented last week PR Details Issue Link :
https://ourtilt.atlassian.net/browse/PIE-469

Checklist

Involves feature flags? (Name and behavior with flag ON/OFF) Tests for
backend/frontend have been updated/added Docstrings have been created and
updated where necessary Breaking API change? If yes, increment
backend/API_COMPAT_VERSION Not adding a flag. The behavior remains gated by the
existing enableBKEMinnesotaPFML / MN PFML tracking flags; this PR changes what
those already-flagged rules recommend.

Description:

Remove the whole-day filter from MinnesotaPFML.calculate_spans so intermittent
MN PFML is recommended on exactly the intermittency reported, partial days
included. full_day_leave_schedule had no other caller, so it and its unit tests
are removed too.

Motivation:

QA (Christian) found MN PFML was not recommended on intermittent absences
shorter than a full scheduled shift. Leave & Compliance and Product then
reversed the earlier "whole-day increment" decision: MN allows intermittent
leave in whatever increment the employer uses for other leave types (down to the
minute), and LC prefers we impose no full-day restriction, especially since we
do not capture a per-employer increment policy. This also drops the dependency
on capturing that increment setting, so it is off the critical path. The benefit
is tracked with a minute bank that already drains each day by its actual leave
minutes, so a partial day now consumes only its hours rather than being dropped.
The 7-day qualifying-event gate is unchanged and continuous leaves are
unaffected.

Observability

No monitor. This is a rule-recommendation change with no runtime signal to alert
on. Rollback Plan Revert this PR.

Testing Repro steps: on a company with MN PFML enabled, create an intermittent
leave (is_leave_continuous = False) whose reported schedule mixes full-shift
days and partial-shift days (e.g. a half day). Open the leave's Benefit
Suggestions panel and confirm MN PFML is now recommended on the partial days as
well as the full days, and that the partial days drain the entitlement by their
actual hours. Automated:
benefits/rules/minnesota/tests/pfml/test_intermittent_policy.py covers mixed
full/partial bonding, partial medical (with the 7-day gate), and an all-partial
leave. No post-deployment steps beyond the above. Performance Negligible; the
change removes a per-evaluation WorkSchedule build and partial-day scan for
intermittent MN PFML leaves. No new queries.

Visual Changes/Screenshots None. Backend rule logic only; the effect surfaces as
additional recommended spans in the Benefit Suggestions panel (see Testing).
