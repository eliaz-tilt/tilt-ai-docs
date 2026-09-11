Minnesota Paid Family Leave - Testing with BKE 1.0 and Prior to Path to SaaS
data points only\
Error or Flag	Area / Test IDs	Status	What Failed / Issue Identified	Business /
Compliance Impact	Ongoing Discussion Needed	LQM Notes Error	Job protection
eligibility during active leave	Review Required	System correctly withheld job
protection until the employee met the required tenure eligibility threshold.
However, once eligibility was reached mid-leave, the system appeared to apply a
new full job protection entitlement instead of limiting protection to the
employee’s remaining applicable paid benefit entitlement.	Employees may receive
more job-protected leave than allowed when eligibility is reached after paid
benefits have already started.	Confirm expected behavior when job protection
eligibility is met during an active leave. Validate that job protection duration
should align with remaining applicable paid benefit entitlement rather than
creating a new full entitlement period.	Being discussed in BKE Garage
here	Retested per Dustin's PIE-466 ticket. Discovered that when testing around
replenishment, I was receiving error messages and unable to apply both MN PFML
Paid Benefits and Job Protection (Medical) BKE sidebar recommendations.
Error	Parent bank entitlement duration / calendar day calculation	Review
Required	The system appears to calculate the expected parent bank entitlement as
11 weeks and 5 days instead of extending through the full calendar period to
include the final weekend days. The calculation does appear to reflect the
correct number of working days, but the displayed leave end date may not align
with the expected calendar duration.	Employees and employers may rely on the
leave map visualization to understand entitlement usage. If the leave map
displays a shorter duration than the employee’s actual entitlement period, such
as showing 11 weeks and 5 days instead of the full 12-week bonding entitlement,
the employee may reasonably believe additional protected leave remains
available. This could result in employees taking additional absences based on
the leave map representation, only to later discover their entitlement was
already exhausted and the additional time was not protected.	Align on how
entitlement duration should be displayed in the leave map to ensure employees
and employers have an accurate understanding of available protected leave.
Confirm whether the visual representation should reflect the full entitlement
period while maintaining the correct underlying balance calculation.	Being
discussed in BKE Garage here Error	Intermittent absence recommendations / leave
increment handling	Review Required	The system is not recommending MN Paid Leave
for intermittent absences when the absence is less than a full day. However, MN
Paid Leave may be taken intermittently in the same smallest increment that an
employer normally uses to track other types of leave. The current behavior
appears to impose a full-day restriction that is not required.	Employees may not
receive accurate MN Paid Leave recommendations for qualifying intermittent
absences, which could result in missed benefit opportunities or incorrect leave
administration.	Confirm that MN Paid Leave intermittent leave recommendations
should not be restricted to full-day absences. Advise that there should be no
additional system restrictions applied, especially since employer-specific
intermittent increment requirements are not currently captured for other types
of leave.	Being discussed in BKE Garage here Flagged	MN Paid Leave qualifying
event / entitlement recommendation timing	Review Required	The system is not
recommending MN Paid Leave entitlements until the employee has reported at least
7 days of absences to satisfy the qualifying event requirement. The LC team
believes the system should begin applying the reported absences and reflect the
MN Paid Leave entitlement as pending once the employee begins reporting
qualifying absences, rather than waiting until the full 7-day qualifying event
has been met.	Delaying entitlement recommendations until after the qualifying
event is satisfied may create unnecessary delays in claim submission, benefit
processing, and employee guidance. Employees may not have visibility into their
potential MN Paid Leave entitlement during the period when they are actively
reporting qualifying absences.	Confirm expected behavior for MN Paid Leave
entitlement recommendations before the 7-day qualifying event is satisfied.
Validate whether BKE should apply reported qualifying absences and maintain the
entitlement in a pending state until the employee meets the qualifying event
requirement, allowing for a smoother transition once eligibility is
established.	Being discussed in BKE Garage here Error	Schedule change mid-leave
(FT ↔ PT)	Review Required	Error messages are returned when attempting to update
an employee's work schedule from full-time to part-time during an active leave.
This prevents validation of whether BKE correctly re-bases the employee's
remaining FMLA and MN Paid Leave entitlement to reflect the new work
schedule.	If work schedule changes cannot be processed successfully, the system
may be unable to accurately calculate remaining leave entitlement for employees
whose permanent schedules change during an active leave, potentially resulting
in incorrect leave balances or benefit recommendations.	Investigate the source
of the error messages and confirm whether BKE supports permanent work schedule
changes during an active leave. Once resolved, validate that the remaining FMLA
and MN Paid Leave banks are appropriately re-based to the employee's new
schedule.	Being discussed in BKE Garage here Error	Pre-birth non-medical
leave	Review Required	BKE is recommending MN Paid Leave medical benefits as of
the leave start date for pre-birth leave taken for non-medical reasons. Under MN
Paid Leave, pre-birth leave should only be recommended when the absence is
related to a qualifying medical reason. Non-medical pre-birth leave should not
trigger a medical entitlement recommendation.	Employees may receive incorrect
leave recommendations and employers may be presented with inaccurate entitlement
information, resulting in improper leave visibility and benefit
administration.	Confirm that BKE does not recommend MN Paid Leave medical
benefits for pre-birth leave when the reported reason is non-medical. Validate
that medical leave recommendations are only applied when the absence is
associated with a qualifying medical reason.	"Being discussed in BKE Garage here

Context:
