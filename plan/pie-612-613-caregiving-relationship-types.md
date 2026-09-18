# PIE-612 + PIE-613: Add Missing Caregiving Relationship Types

> **Privacy:** This file lives in `AI-docs/`, which is **not committed to GitHub**. Use for local agent handoffs only.

**Status:** Not implemented (verified 2026-09-16)  
**Tickets:**
- PIE-612 — Paycalc item template dropdowns
- PIE-613 — Leave survey dropdowns

**Estimated effort:** ~3–4 days (one PR recommended)  
**Branch:** `pie-612-613-caregiving-relationship-types`

---

## Executive summary

Both tickets add the same **11 relationship concepts** expanding to **12 enum values** (domestic partner's child splits U18/O18). None exist today in `Leave.CaregiverRelationshipType`, `ECaregiverRelationship`, or the frontend mapping layers.

**Single PR approach:** Ship shared enum/migration once, then wire both surfaces:
1. **PIE-612** — Paycalc item templates (`PayCalcItemModal` via `caregiverRelationshipMapByType`)
2. **PIE-613** — Leave survey (`CaregiverTypeStep` via `getRelationshipOptionsForType` + `SURVEY_RELATIONSHIP_LABELS`)

> **Note on "Add parent" in PIE-612 Jira text:** `PARENT` already exists under the Parent caregiver type. Treat as Jira UI noise unless PM confirms a new relationship is intended.

---

## Verification: not implemented

| Location | Current state |
|----------|---------------|
| `Leave.CaregiverRelationshipType` | Ends at `STEP_GRANDCHILD` |
| Nested sub-enums | No new values |
| `ECaregiverRelationship` | Ends at `STEP_GRANDCHILD` |
| `caregiverRelationshipMapByType[OTHER]` | **Missing** |
| `requiresCaregiverRelationship(OTHER)` | **`false`** — survey shows free-text only |
| `SURVEY_RELATIONSHIP_LABELS` | No new entries |
| `hi-fll.drl` | `RECIPROCAL_BENEFICIARY` commented — "BLOCKED: needs leave-survey addition" |

---

## New relationship inventory (12 enum values)

### Spouse (`ECaregiverType.SPOUSE`)

| Paycalc label | Survey label | Enum key | "My" in survey? |
|---------------|--------------|----------|-----------------|
| Civil Union Partner | My Civil Union Partner | `CIVIL_UNION_PARTNER` | Yes |
| Person sharing (or having shared within the last year) a mutual residence and a committed relationship | *(same — no My)* | `MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP` | **No** |
| Reciprocal Beneficiary (Hawaii-specific legal status) | *(same — no My)* | `RECIPROCAL_BENEFICIARY` | **No** |

### Child (`CHILD_U18` / `CHILD_O18`)

| Paycalc label | Survey label | Enum key |
|---------------|--------------|----------|
| Domestic Partner's Child (Under 18) | My Domestic Partner's Child | `DOMESTIC_PARTNER_CHILD_U18` |
| Domestic Partner's Child (Over 18) | My Domestic Partner's Child | `DOMESTIC_PARTNER_CHILD_O18` |

> Survey collapses child U18/O18 labels to `"My Domestic Partner's Child"` (same pattern as `CHILD_U18` → `"My Child"`); age handled by checkbox.

### Grandchild (`ECaregiverType.GRANDCHILD`)

| Paycalc label | Survey label | Enum key |
|---------------|--------------|----------|
| Domestic Partner's Grandchild | My Domestic Partner's Grandchild | `DOMESTIC_PARTNER_GRANDCHILD` |

> Ticket prose groups grandchild under "Child"; code places it under `GRANDCHILD` type (with `GRANDCHILD`, `STEP_GRANDCHILD`). Confirm with PM if needed.

### Other (`ECaregiverType.OTHER`) — **new sub-relationship picker (PIE-613)**

| Paycalc + survey label (no "My") | Enum key |
|----------------------------------|----------|
| Someone related by blood or affinity whose close association is the equivalent of a family relationship | `BLOOD_AFFINITY_CLOSE_ASSOCIATION` |
| Chosen Family / Close Association Equivalent to a Family Relationship | `CHOSEN_FAMILY` |
| Someone related by blood or affinity, equivalent of a family relationship | `BLOOD_AFFINITY_FAMILY` |
| Any individual with an expectation to rely on you for care | `EXPECTATION_TO_RELY_FOR_CARE` |
| Significant personal bond that is, or is like, a family relationship | `SIGNIFICANT_PERSONAL_BOND` |
| Designated Person | `DESIGNATED_PERSON` |

---

## PIE-613: Leave survey behavior change (OTHER)

### Current behavior
- `requiresCaregiverRelationship(OTHER)` → `false`
- `CaregiverTypeStep` shows free-text `caregiverTypeOther` ("e.g., Aunt, Uncle, Cousin")
- Backend `_validate_caregiver`: OTHER requires `caregiver_type_other`, not `caregiver_relationship`
- `resolve_caregiver_relationship(leave)` returns `None` for OTHER (no relationship on leave)

### New behavior
- `requiresCaregiverRelationship(OTHER)` → **`true`**
- Show relationship `RadioCardGroup` with 6 structured options (labels without "My")
- **Replace** free-text `caregiverTypeOther` field in survey UI (hide `showOtherDescription` block)
- Require `caregiver_relationship` for OTHER on submit (frontend + backend)
- `caregiver_type_other` becomes **optional/unused for new submissions**; preserve field for legacy leaves
- `getRelationshipOptionsForType(OTHER)` returns 6 options

### Legacy / backward compatibility
- Existing leaves with `caregiver_type=OTHER` + `caregiver_type_other` text remain valid
- Do not data-migrate legacy rows
- CFRA designated-person logic: leaves with `caregiver_relationship=DESIGNATED_PERSON` now resolve a relationship (improves template matching); free-text-only OTHER leaves still resolve `None` → designated-person reasoning path unchanged

---

## Consumers matrix

| Consumer | PIE-612 | PIE-613 | Action |
|----------|---------|---------|--------|
| `PayCalcItemModal` | Primary | — | Auto via `leaves.ts` maps |
| `CaregiverTypeStep` | — | Primary | `requiresCaregiverRelationship`, `SURVEY_RELATIONSHIP_LABELS`, hide free-text |
| `leaveTypeSubmitValidation.ts` | — | Yes | OTHER requires `caregiverRelationship` not `caregiverTypeOther` |
| `stepValidation.ts` | — | Yes | OTHER drafts track `caregiverRelationship` not `caregiverTypeOther` |
| `submit.py` `_validate_caregiver` | — | Yes | OTHER requires `caregiver_relationship` |
| `LeaveDetailsFields` + `CaregiverTypeOtherField` (HR edit) | — | Yes | Show relationship picker for OTHER; hide free-text field |
| `LeavePlanner/steps/CaregiverType.tsx` | — | Yes | **Not auto** — update `showRelationshipDropdown` to include OTHER; hide free-text block |
| `LeavePlanner/useLeavePlanner.ts` | — | Yes | OTHER validation: require `caregiverRelationship` not `caregiverTypeOther` |
| `BenefitItemModal` | QA | — | Auto via maps |
| BKE `registry.py` | Auto | Auto | No change |
| `bulk_leave_import` `ACCEPTED_VALUES` | Yes | — | Add 12 display strings |
| Nested backend sub-enums | Yes | — | Spouse/Child/Grandchild types |
| `hi-fll.drl` | Follow-up | **Unblock** | Uncomment `RECIPROCAL_BENEFICIARY` in caregiver sets |
| Integration API | Out of scope | Out of scope | Hand-maintained; OTHER still has no relationship in contract |

---

## Implementation phases

### Phase 0 — PM confirmations
- [ ] `DOMESTIC_PARTNER_GRANDCHILD` under `GRANDCHILD` type (recommended)
- [ ] OTHER free-text field replaced by structured picker (recommended)
- [ ] "Add parent" in Jira — confirm not a new relationship

### Phase 1 — Backend enum + migration

**1a. Main enum** — Add 12 values to `Leave.CaregiverRelationshipType` in `backend/legacy/models.py`.

**1b. Nested sub-enums:**

| Sub-enum | New values |
|----------|------------|
| `SpouseRelationshipType` | `CIVIL_UNION_PARTNER`, `MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP`, `RECIPROCAL_BENEFICIARY` |
| `ChildUnder18RelationshipType` | `DOMESTIC_PARTNER_CHILD_U18` |
| `ChildOver18RelationshipType` | `DOMESTIC_PARTNER_CHILD_O18` |
| `GrandchildRelationshipType` | `DOMESTIC_PARTNER_GRANDCHILD` |

**1c. Migration** — `makemigrations legacy --name add_caregiving_relationship_types`

Verify all four fields altered (per `0327`):
- `leave.caregiver_relationship`
- `historicalleave.caregiver_relationship`
- `paycalcitemtemplate.caregiver_relationship`
- `historicalpaycalcitemtemplate.caregiver_relationship`

**1d. Bulk import** — Add 12 strings to `ACCEPTED_VALUES["caregiver_relationship"]` in `bulk_leave_import/config.py`. Use `(18 or older)` convention for O18 child label + `CAREGIVER_RELATIONSHIP_VALUES.update(...)` alias if needed.

### Phase 2 — Frontend shared maps

**2a.** `ECaregiverRelationship` in `frontend/client/constants/types/index.ts`

**2b.** `caregiverRelationshipMap` + `caregiverRelationshipMapByType` in `frontend/client/_types/leaves.ts`:
```typescript
[ECaregiverType.SPOUSE]: [..., CIVIL_UNION_PARTNER, MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP, RECIPROCAL_BENEFICIARY],
[ECaregiverType.CHILD_U18]: [..., DOMESTIC_PARTNER_CHILD_U18],
[ECaregiverType.CHILD_O18]: [..., DOMESTIC_PARTNER_CHILD_O18],
[ECaregiverType.GRANDCHILD]: [..., DOMESTIC_PARTNER_GRANDCHILD],
[ECaregiverType.OTHER]: [6 OTHER relationships],
```

**2c.** `CHILD_RELATIONSHIP_TO_OVER_18` in `caregiverSurveyOptions.ts` — add `DOMESTIC_PARTNER_CHILD_U18` ↔ `DOMESTIC_PARTNER_CHILD_O18`

### Phase 3 — PIE-613 Leave survey

**3a. Survey labels** — Add all 12 entries to `SURVEY_RELATIONSHIP_LABELS` in `caregiverSurveyOptions.ts`:
- Spouse/child/grandchild: `"My …"` where ticket allows
- `MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP`, `RECIPROCAL_BENEFICIARY`, all 6 OTHER: exact ticket text, **no "My"**

**3b. Enable OTHER relationship picker:**
```typescript
export const requiresCaregiverRelationship = (caregiverType: string | null | undefined): boolean => {
  if (!caregiverType) return false;
  return caregiverType !== MILITARY_SERVICE_MEMBER_TYPE;
  // OTHER now returns true
};
```

**3c. `CaregiverTypeStep.tsx` (leave survey):**
- Remove or gate `showOtherDescription` / `caregiverTypeOther` Controller block when OTHER is selected
- Relationship picker already renders when `showRelationship && relationshipOptions.length > 0` — will work once 3b is done
- Reset `caregiverTypeOther` to null when switching to OTHER (structured picker replaces free text)

**3c-ii. HR leave edit flyout:**
- `LeaveDetailsFields.tsx` — `CaregiverTypeOtherField`: hide when OTHER uses structured picker; `CaregiverRelationshipField` will auto-show via `requiresCaregiverRelationship(OTHER)`
- `LeaveDetailsFlyout.tsx` — verify both fields render correctly after change

**3c-iii. LeavePlanner** (`LeavePlanner/steps/CaregiverType.tsx`):
- Change `showRelationshipDropdown` from `!isOtherCaregiverType` to include OTHER (e.g. `caregiverType && relationshipOptions.length > 0`)
- Remove/gate free-text block for OTHER (lines 94–116)
- `useLeavePlanner.ts`: update yup schema — OTHER requires `caregiverRelationship` not `caregiverTypeOther`

**3d. Frontend validation:**
- `leaveTypeSubmitValidation.ts`: for OTHER, require `caregiverRelationship` instead of `caregiverTypeOther`
- `stepValidation.ts`: OTHER drafts push `caregiverRelationship` not `caregiverTypeOther`

**3e. Backend validation** — `backend/leaves/services/leave_survey/submit.py` `_validate_caregiver`:
```python
elif leave.caregiver_type == Leave.CaregiverLeaveType.OTHER:
    if not leave.caregiver_relationship and not leave.caregiver_type_other:
        errors["caregiver_relationship"] = ["required"]
    # New submissions use structured picker (caregiver_relationship).
    # Legacy rows with only caregiver_type_other remain valid (grandfather clause).
```
Remove standalone `caregiver_type_other` requirement for OTHER; either field satisfies validation.

### Phase 4 — PIE-612 Paycalc verification

No dedicated code changes expected — `PayCalcItemModal` auto-picks up `caregiverRelationshipMapByType`. Verify manually + tests.

### Phase 5 — HI FLL reciprocal beneficiary (same PR)

1. Uncomment `RECIPROCAL_BENEFICIARY` in `bke/bke-adapter-rules-drools/src/main/resources/rules/hi-fll.drl` (lines ~181, ~204). Remove BLOCKED comment.
2. Add `RECIPROCAL_BENEFICIARY` to `DOC_COVERED_RELATIONSHIPS` in `backend/benefits/rules/hawaii/tests/test_caregiver_relationships.py`.
3. Optionally update `HI_FLL_CAREGIVING_RELATIONSHIPS` in `fll_constants.py` for documentation parity (not imported at runtime today).
4. HI FLL paycalc templates must include `RECIPROCAL_BENEFICIARY` in `caregiver_relationship` allow-list for `_is_correct_caregiver` matching — no Python rule code change beyond tests.

### Phase 6 — Tests

| Area | File |
|------|------|
| Survey options | `caregiverSurveyOptions.test.ts` — OTHER returns 6 options; new spouse/child labels; age mapping |
| Survey UI | `CaregiverTypeStep.test.tsx` — OTHER shows relationship picker, not free text |
| Submit validation | `leaveTypeSubmitValidation.test.ts` — OTHER requires relationship |
| Backend submit | `test_submit.py` — update OTHER tests; add tests for new relationship values |
| Paycalc modal | `PayCalcItemModal.test.tsx` — new options per caregiver type |
| Serializer | `test_paycalc_item_template_serializers.py` — save new values |
| Benefit matching | `test_leave.py` — `_is_correct_caregiver` with new values |
| Bulk import | bulk import tests — `ACCEPTED_VALUES` |
| HI FLL | `test_caregiver_relationships.py`, drools compilation test |
| LeavePlanner | `CaregiverType.test.tsx`, `useLeavePlanner.test.tsx` |
| HR flyout | `LeaveDetailsFields` / flyout tests if present |
| Step validation | `formLogic/stepValidation.test.ts` |

### Phase 7 — Manual QA

**PIE-612 (paycalc templates):**
1. Spouse → 3 new relationship options
2. Child U18/O18 → domestic partner's child
3. Grandchild → domestic partner's grandchild
4. Other → 6 new options
5. Save/reload template

**PIE-613 (leave survey):**
1. Employee survey → Caregiver → Spouse → new options with correct labels (My / no My)
2. Child → domestic partner's child; age toggle maps U18↔O18
3. Grandchild → domestic partner's grandchild
4. Other → 6 structured options (no free text); submit succeeds
5. HR survey — same flows
6. Review step shows correct relationship text

**Regression:**
- Military service member flow unchanged
- Parent/sibling/etc. existing options unchanged
- Legacy OTHER leaves with free text still display correctly

---

## Acceptance criteria

### PIE-612
- [ ] All relationships in paycalc item template dropdowns under correct caregiver-type groupings
- [ ] Labels match ticket; no "My" where specified
- [ ] Values persist on `PaycalcItemTemplate.caregiver_relationship`

### PIE-613
- [ ] All relationships in leave survey under correct caregiver-type groupings
- [ ] Survey labels use "My" prefix except where ticket says not to
- [ ] OTHER shows structured relationship picker (not free text)
- [ ] Survey submit stores `caregiver_relationship` for all caregiver types including OTHER

### Shared
- [ ] Backend + frontend enums in sync (12 values)
- [ ] Migration applied
- [ ] No regression in existing flows

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| OTHER UX change breaks existing free-text flow | Legacy data preserved; only new submissions use structured picker |
| CFRA designated-person semantics shift | `DESIGNATED_PERSON` enum improves matching; free-text OTHER unchanged |
| Enum drift frontend/backend | Single PR, cross-reference comments |
| Overlapping Other option wording | Per ticket; add statute comments in code |
| Integration API OTHER has no relationship | Document; out of scope |
| Long dropdown labels | Existing pattern (`LEGAL_CUSTODY_U18`) |

---

## Out of scope

- Integration API contract extensions
- FMLA document generation relationship sets (`generate_docs.py`)
- State benefit rule whitelist updates beyond HI FLL `RECIPROCAL_BENEFICIARY`
- Data migration for existing templates or leaves
- New `ParentRelationshipType` values ("Add parent" — PARENT already exists)

---

## Implementation checklist

- [ ] Phase 0 PM confirmations
- [ ] Backend enum + nested sub-enums + migration
- [ ] Bulk import `ACCEPTED_VALUES`
- [ ] Frontend `ECaregiverRelationship` + `leaves.ts` maps
- [ ] `caregiverSurveyOptions.ts` — labels, age map, `requiresCaregiverRelationship(OTHER)`
- [ ] `CaregiverTypeStep.tsx` + HR `CaregiverTypeOtherField` + LeavePlanner — hide free text for OTHER; show relationship picker
- [ ] Frontend + backend validation updates for OTHER
- [ ] HI FLL: uncomment `RECIPROCAL_BENEFICIARY` in `hi-fll.drl` + update `test_caregiver_relationships.py`
- [ ] Tests (Phase 6)
- [ ] Manual QA (Phase 7)
- [ ] Open PR

---

## Handoff prompt (copy for a fresh AI session)

```
Implement PIE-612 + PIE-613: Add missing caregiving relationship types to paycalc item templates and leave survey.

Read first:
1. .ai/README.md and relevant rules under .ai/rules/ (frontend + backend + testing)

Branch: pie-612-613-caregiving-relationship-types (from latest main)

Add 12 CaregiverRelationshipType enum values:
- Spouse (3): CIVIL_UNION_PARTNER, MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP, RECIPROCAL_BENEFICIARY
- Child (2): DOMESTIC_PARTNER_CHILD_U18, DOMESTIC_PARTNER_CHILD_O18
- Grandchild (1): DOMESTIC_PARTNER_GRANDCHILD (under GRANDCHILD caregiver type)
- Other (6): BLOOD_AFFINITY_CLOSE_ASSOCIATION, CHOSEN_FAMILY, BLOOD_AFFINITY_FAMILY, EXPECTATION_TO_RELY_FOR_CARE, SIGNIFICANT_PERSONAL_BOND, DESIGNATED_PERSON

Backend:
- backend/legacy/models.py — main enum + nested sub-enums (Spouse/ChildUnder18/ChildOver18/Grandchild)
- Django migration (leave, historicalleave, paycalcitemtemplate, historicalpaycalcitemtemplate)
- backend/integrations/services/bulk_leave_import/config.py — ACCEPTED_VALUES
- backend/leaves/services/leave_survey/submit.py — OTHER requires caregiver_relationship (not caregiver_type_other for new flow)

Frontend shared:
- frontend/client/constants/types/index.ts — ECaregiverRelationship
- frontend/client/_types/leaves.ts — caregiverRelationshipMap + caregiverRelationshipMapByType (including OTHER)

PIE-613 (leave survey):
- caregiverSurveyOptions.ts — SURVEY_RELATIONSHIP_LABELS (My prefix except where ticket says no), requiresCaregiverRelationship(OTHER)=true, CHILD_RELATIONSHIP_TO_OVER_18 pair
- CaregiverTypeStep.tsx + LeaveDetailsFields CaregiverTypeOtherField + LeavePlanner/steps/CaregiverType.tsx — hide free text for OTHER; show relationship picker
- leaveTypeSubmitValidation.ts + stepValidation.ts + useLeavePlanner.ts — OTHER requires caregiverRelationship

PIE-612 (paycalc):
- PayCalcItemModal auto-picks up maps — verify only

HI FLL reciprocal beneficiary:
- Uncomment RECIPROCAL_BENEFICIARY in bke/bke-adapter-rules-drools/src/main/resources/rules/hi-fll.drl
- Add to backend/benefits/rules/hawaii/tests/test_caregiver_relationships.py DOC_COVERED_RELATIONSHIPS

Survey label rules:
- "My …" for: Civil Union Partner, Domestic Partner's Child/Grandchild
- NO "My" for: mutual residence, reciprocal beneficiary, all 6 Other options

Tests:
- caregiverSurveyOptions.test.ts, CaregiverTypeStep.test.tsx, leaveTypeSubmitValidation.test.ts
- backend/leaves/services/leave_survey/tests/test_submit.py (update OTHER tests)
- PayCalcItemModal.test.tsx, test_paycalc_item_template_serializers.py, test_leave.py

Do NOT:
- Remove caregiver_type_other field from model (legacy data)
- Change integration API contract
- Data-migrate existing leaves/templates

Definition of done: both ticket acceptance criteria; manual QA on paycalc templates + leave survey.

When complete, create a GitHub pull request using the GitHub CLI (gh). You may need to set an environment variable (e.g. GH_TOKEN or GITHUB_TOKEN) for the CLI to authenticate.
```
