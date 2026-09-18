# PIE-612: Add Missing Caregiving Relationship Types to Paycalc Item Templates

> **Privacy:** This file lives in `AI-docs/`, which is **not committed to GitHub**. Use for local agent handoffs only.

**Status:** Not implemented (verified 2026-09-16)  
**Ticket:** PIE-612 — Add missing caregiving relationship types to paycalc item templates  
**Related:** PIE-613 — same relationships for leave survey (separate ticket; shares enum work)  
**Estimated effort:** ~1.5–2.5 days

---

## Executive summary

Paycalc item template caregiver-relationship dropdowns are driven by a shared enum and mapping layer. The ticket describes **11 relationship concepts** that expand to **12 enum values** (domestic partner's child splits into U18/O18). None of these exist today in `Leave.CaregiverRelationshipType`, `ECaregiverRelationship`, or `caregiverRelationshipMap` / `caregiverRelationshipMapByType`.

**Scope (this ticket):** Paycalc item template UI dropdowns and the shared enum/label layer they depend on.  
**Out of scope (PIE-613):** Leave survey labels (`caregiverSurveyOptions.ts`), survey validation, and `requiresCaregiverRelationship` behavior for `OTHER`.

**Approach:** Add canonical enum values on backend + frontend, wire them into `caregiverRelationshipMap` and `caregiverRelationshipMapByType`, update nested backend sub-enums used by legacy leave forms, run Django migration, update bulk-import `ACCEPTED_VALUES`, add tests. Paycalc UI (`PayCalcItemModal`) picks up options automatically via existing `caregiverRelationshipMapByType` plumbing.

**Blast radius note:** Updating `leaves.ts` also affects `BenefitItemModal`, HR Leave Details, and LeavePlanner — new non-OTHER options will appear there once maps ship. This is acceptable for PIE-612; survey `OTHER` sub-options remain gated until PIE-613.

---

## Verification: not implemented

Searched 2026-09-16 for proposed keys (`CIVIL_UNION_PARTNER`, `RECIPROCAL_BENEFICIARY`, `DESIGNATED_PERSON`, `CHOSEN_FAMILY`, `DOMESTIC_PARTNER_CHILD_U18`, etc.) — **no matches** in application code.

| Location | Current state |
|----------|---------------|
| `backend/legacy/models.py` `CaregiverRelationshipType` | Ends at `STEP_GRANDCHILD`; no new values |
| Nested sub-enums (`SpouseRelationshipType`, `ChildUnder18RelationshipType`, etc.) | Same — no new values |
| `frontend/client/constants/types/index.ts` `ECaregiverRelationship` | Ends at `STEP_GRANDCHILD` |
| `frontend/client/_types/leaves.ts` maps | No new entries; `OTHER` has no `caregiverRelationshipMapByType` entry |
| `bke/.../hi-fll.drl` | `RECIPROCAL_BENEFICIARY` commented out with note "BLOCKED: needs leave-survey addition" |

---

## New relationship inventory

### Under Spouse (`ECaregiverType.SPOUSE`)

| Display label (paycalc — no "My" prefix) | Enum key |
|------------------------------------------|----------|
| Civil Union Partner | `CIVIL_UNION_PARTNER` |
| Person sharing (or having shared within the last year) a mutual residence and a committed relationship | `MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP` |
| Reciprocal Beneficiary (Hawaii-specific legal status) | `RECIPROCAL_BENEFICIARY` |

### Under Child (`ECaregiverType.CHILD_U18` / `CHILD_O18`)

| Display label | Enum key | Caregiver type |
|---------------|----------|----------------|
| Domestic Partner's Child (Under 18) | `DOMESTIC_PARTNER_CHILD_U18` | `CHILD_U18` |
| Domestic Partner's Child (Over 18) | `DOMESTIC_PARTNER_CHILD_O18` | `CHILD_O18` |

### Under Grandchild (`ECaregiverType.GRANDCHILD`)

| Display label | Enum key |
|---------------|----------|
| Domestic Partner's Grandchild | `DOMESTIC_PARTNER_GRANDCHILD` |

> Ticket prose groups "Domestic partner's grandchild" under "Child", but code pattern places grandchild relationships under `GRANDCHILD` type (alongside `GRANDCHILD`, `STEP_GRANDCHILD`). Confirm with PM if they insist on `CHILD_U18`/`CHILD_O18` instead.

### Under Other (`ECaregiverType.OTHER`) — new `caregiverRelationshipMapByType` entry

| Display label (no "My" prefix) | Enum key |
|--------------------------------|----------|
| Someone related by blood or affinity whose close association is the equivalent of a family relationship | `BLOOD_AFFINITY_CLOSE_ASSOCIATION` |
| Chosen Family / Close Association Equivalent to a Family Relationship | `CHOSEN_FAMILY` |
| Someone related by blood or affinity, equivalent of a family relationship | `BLOOD_AFFINITY_FAMILY` |
| Any individual with an expectation to rely on you for care | `EXPECTATION_TO_RELY_FOR_CARE` |
| Significant personal bond that is, or is like, a family relationship | `SIGNIFICANT_PERSONAL_BOND` |
| Designated Person | `DESIGNATED_PERSON` |

**Total: 12 new enum values** (3 spouse + 2 child age-split + 1 grandchild + 6 other).

> The six "Other" options use overlapping statutory language. Keep them as separate enums per ticket; consider adding source-statute comments in code for maintainers.

---

## Consumers matrix

| Consumer | Auto-updates? | Action for PIE-612 |
|----------|---------------|-------------------|
| `PayCalcItemModal.tsx` | Via `leaves.ts` maps | **Primary target** — verify QA |
| `BenefitItemModal` / `AdvancedSettingsSection` | Via `leaves.ts` maps | QA only |
| `BenefitDataPanel` / BKE rules catalog | Via `registry.py` introspecting `CaregiverRelationshipType.choices` | No code change |
| `leave_survey_serializers.py` | Uses `CaregiverRelationshipType.choices` | API accepts new values; survey UI blocked for OTHER until PIE-613 |
| `bulk_leave_import` `CAREGIVER_RELATIONSHIP_VALUES` | Derived from choices | Auto-updates |
| `bulk_leave_import` `ACCEPTED_VALUES["caregiver_relationship"]` | **Hardcoded set** | **Must add new display strings** |
| Legacy leave form `CAREGIVER_RELATIONSHIP_OPTIONS` | Uses nested sub-enums | **Must update sub-enums** (see Phase 1b) |
| `mapFormDataToFields.tsx` | Consumes backend form API | No frontend change; depends on sub-enums |
| HR `LeaveDetailsFields` | Via `getRelationshipOptionsForType` → `getSurveyRelationshipLabel` | New options appear but labels fall back to raw enum keys unless `getSurveyRelationshipLabel` gains a `caregiverRelationshipMap` fallback (Phase 2d) |
| LeavePlanner `CaregiverType.tsx` | Via `caregiverRelationshipMap` / `caregiverRelationshipMapByType` directly | New options + labels auto-update from `leaves.ts` |
| Integration API contract | Hand-maintained | Out of scope; partners cannot set new values until contract extended |
| FMLA doc generation / `generate_docs.py` | Hardcoded frozensets | Out of scope until leaves store new values |
| BKE rules (`hi-fll.drl`, state whitelists) | Hardcoded | Out of scope; uncomment HI `RECIPROCAL_BENEFICIARY` after PIE-613 |

---

## Pre-implementation decisions

| # | Decision | Recommendation |
|---|----------|----------------|
| 1 | `DOMESTIC_PARTNER_GRANDCHILD` caregiver type | **`GRANDCHILD`** (default); confirm with PM |
| 2 | Age mapping for `DOMESTIC_PARTNER_CHILD` | U18/O18 pair; add to `mapChildRelationshipForAge` in PIE-612 (HR leave edit uses it) |
| 3 | `OTHER` relationships in paycalc | Add `caregiverRelationshipMapByType[OTHER]` — PayCalcItemModal has no `requiresCaregiverRelationship` guard |
| 4 | Nested backend sub-enums | **Update in PIE-612** — legacy leave forms won't show new grouped options without them |
| 5 | BKE / benefit rules | No rule changes in PIE-612 |
| 6 | Django migration | **Required** for all four fields (see Phase 1) |

---

## Architecture (how dropdowns work today)

```
PayCalcItemTemplatesPage → PayCalcItemModal (isTemplate=true)
  └─ selected caregiver types (ECaregiverType[])
       └─ flatMap caregiverRelationshipMapByType[type]
            └─ caregiverRelationshipMap.get(enum) → display label

Backend PaycalcItemTemplate.caregiver_relationship
  └─ ArrayField(TextChoices=CaregiverRelationshipType)
       └─ matched at runtime via _is_correct_caregiver() in checks/leave.py
```

Key files:

| Layer | File |
|-------|------|
| Backend enum (source of truth) | `backend/legacy/models.py` — `Leave.CaregiverRelationshipType` |
| Backend nested sub-enums | `backend/legacy/models.py` — `SpouseRelationshipType`, `ChildUnder18RelationshipType`, `ChildOver18RelationshipType`, `GrandchildRelationshipType` |
| Backend template model | `backend/legacy/models.py` — `PaycalcItemTemplate.caregiver_relationship` |
| Legacy form choices | `backend/legacy/services/leaves/forms.py` — `CAREGIVER_RELATIONSHIP_OPTIONS` |
| Backend matching | `backend/benefits/rules/checks/leave.py` — `_is_correct_caregiver` |
| BKE catalog (auto) | `backend/benefits/rules/catalog/registry.py` |
| Bulk import labels | `backend/integrations/services/bulk_leave_import/config.py` |
| Frontend enum | `frontend/client/constants/types/index.ts` — `ECaregiverRelationship` |
| Frontend labels + grouping | `frontend/client/_types/leaves.ts` |
| Age toggle mapping | `frontend/client/screens/Shared/LeaveSurvey/Steps/Caregiver/caregiverSurveyOptions.ts` — `mapChildRelationshipForAge` |
| Paycalc template modal | `frontend/client/components/PlanCalendar/PayCalcItemModal.tsx` |
| Applied benefit modal | `frontend/client/screens/Shared/LeaveManagement/.../AdvancedSettingsSection.tsx` |

---

## Implementation phases

### Phase 0 — Confirm `DOMESTIC_PARTNER_GRANDCHILD` placement

Default: `caregiverRelationshipMapByType[GRANDCHILD]`. If PM wants it under Child types, add to both `CHILD_U18` and `CHILD_O18` arrays (no age variant).

### Phase 1a — Backend main enum + migration

1. Add 12 values to `Leave.CaregiverRelationshipType` in `backend/legacy/models.py` (grouped comments matching existing style).
2. Generate migration:
   ```bash
   python manage.py makemigrations legacy --name add_caregiving_relationship_types
   ```
3. Verify migration alters all four fields (per `0327` pattern):
   - `leave.caregiver_relationship`
   - `historicalleave.caregiver_relationship`
   - `paycalcitemtemplate.caregiver_relationship`
   - `historicalpaycalcitemtemplate.caregiver_relationship`

**Do not** add data migrations unless product requests backfilling existing templates.

### Phase 1b — Backend nested sub-enums

Add new values to the grouped sub-enums in `backend/legacy/models.py`:

| Sub-enum | New values |
|----------|------------|
| `SpouseRelationshipType` | `CIVIL_UNION_PARTNER`, `MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP`, `RECIPROCAL_BENEFICIARY` |
| `ChildUnder18RelationshipType` | `DOMESTIC_PARTNER_CHILD_U18` |
| `ChildOver18RelationshipType` | `DOMESTIC_PARTNER_CHILD_O18` |
| `GrandchildRelationshipType` | `DOMESTIC_PARTNER_GRANDCHILD` |

No `OtherRelationshipType` exists; OTHER sub-relationships live only in the main enum + frontend `caregiverRelationshipMapByType[OTHER]`.

### Phase 1c — Bulk import `ACCEPTED_VALUES`

Add all 12 new display strings to the hardcoded `ACCEPTED_VALUES["caregiver_relationship"]` set in `backend/integrations/services/bulk_leave_import/config.py` (lines 110–139). Use existing bulk-import conventions for O18 child labels: `(18 or older)` not `(Over 18)` — add alias overrides in `CAREGIVER_RELATIONSHIP_VALUES.update(...)` if needed (same pattern as existing child O18 entries). `CAREGIVER_RELATIONSHIP_VALUES` auto-derives from choices but validation runs against `ACCEPTED_VALUES` first.

### Phase 2 — Frontend enum + maps

1. Add matching keys to `ECaregiverRelationship` in `frontend/client/constants/types/index.ts`.
2. Update `caregiverRelationshipMap` in `frontend/client/_types/leaves.ts` with exact display strings from ticket (paycalc style — no "My").
3. Update `caregiverRelationshipMapByType`:
   ```typescript
   [ECaregiverType.SPOUSE]: [..., CIVIL_UNION_PARTNER, MUTUAL_RESIDENCE_COMMITTED_RELATIONSHIP, RECIPROCAL_BENEFICIARY],
   [ECaregiverType.CHILD_U18]: [..., DOMESTIC_PARTNER_CHILD_U18],
   [ECaregiverType.CHILD_O18]: [..., DOMESTIC_PARTNER_CHILD_O18],
   [ECaregiverType.GRANDCHILD]: [..., DOMESTIC_PARTNER_GRANDCHILD],
   [ECaregiverType.OTHER]: [all 6 OTHER relationships],
   ```
4. Add `DOMESTIC_PARTNER_CHILD_U18` ↔ `DOMESTIC_PARTNER_CHILD_O18` to the `CHILD_RELATIONSHIP_TO_OVER_18` map in `caregiverSurveyOptions.ts` (HR leave edit age toggle uses `mapChildRelationshipForAge`).

### Phase 2d — HR label fallback (scoped, not full PIE-613)

`LeaveDetailsFields` builds options via `getRelationshipOptionsForType` → `getSurveyRelationshipLabel`, which reads `SURVEY_RELATIONSHIP_LABELS` and falls back to the raw enum key. To avoid raw keys in HR edit UI for new non-OTHER relationships, update `getSurveyRelationshipLabel` to fall back to `caregiverRelationshipMap.get(relationship)` before the raw enum:

```typescript
export const getSurveyRelationshipLabel = (relationship: ECaregiverRelationship): string =>
  SURVEY_RELATIONSHIP_LABELS[relationship]
  ?? caregiverRelationshipMap.get(relationship)
  ?? relationship;
```

Full `"My …"` survey labels for new relationships remain **PIE-613**; paycalc-style labels are acceptable interim for HR edit.

### Phase 3 — Tests

| Test area | File | What to add |
|-----------|------|-------------|
| Map completeness | New test near `leaves.ts` or in `PayCalcItemModal.test.tsx` | All new enum keys have labels and appear under expected caregiver types |
| Age mapping | `caregiverSurveyOptions.test.ts` | `mapChildRelationshipForAge` for `DOMESTIC_PARTNER_CHILD_U18`/`_O18` |
| Paycalc modal | `PayCalcItemModal.test.tsx` | Select `OTHER` + `SPOUSE` → relationship options include new values; update snapshots if DOM changes |
| Backend serializer | `backend/legacy/serializers/tests/test_paycalc_item_template_serializers.py` | Save template with new `caregiver_relationship` values |
| Bulk import | Integration bulk-import tests | New labels pass `ACCEPTED_VALUES` validation |
| Benefit matching | `backend/benefits/rules/checks/tests/test_leave.py` | Template + leave with same new value → `_is_correct_caregiver` passes |

### Phase 4 — Manual QA

1. Admin → Paycalc Item Template create/edit → **Spouse** → 3 new relationship options.
2. **Child under 18** / **Child 18+** → domestic partner's child options.
3. **Grandchild** → domestic partner's grandchild.
4. **Other** → 6 new relationship options (paycalc only; survey still gated).
5. Save template; reload; confirm values persist.
6. Applied benefit modal shows same options.
7. Spot-check HR Leave Details edit shows new relationships with paycalc-style labels (not raw enum keys) for non-OTHER types.

---

## Acceptance criteria (from ticket)

- [ ] All listed relationships appear in paycalc item template caregiver-relationship dropdowns under the correct caregiver-type grouping.
- [ ] Labels match ticket text; options marked "should not have My attached" use exact phrasing without a "My" prefix.
- [ ] Values persist on `PaycalcItemTemplate.caregiver_relationship` and round-trip through API.
- [ ] No regression in existing relationship options or template save/load.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Frontend/backend enum drift | Same PR; cross-reference comment between files |
| `DOMESTIC_PARTNER_GRANDCHILD` placement ambiguity | Phase 0 PM confirmation |
| HI FLL `RECIPROCAL_BENEFICIARY` blocked in BKE until PIE-613 | Document in PR; template can store value |
| HR/LeavePlanner show new options before survey ships | Acceptable for non-OTHER; OTHER gated by `requiresCaregiverRelationship` |
| Paycalc templates with OTHER relationships won't match leaves until PIE-613 | Document asymmetry |
| Long labels in dropdown UX | Existing pattern (`LEGAL_CUSTODY_U18`) |
| Overlapping "Other" option wording | Per ticket; add statute comments in code |

---

## Out of scope (PIE-612)

- Leave survey UI and `SURVEY_RELATIONSHIP_LABELS` — **PIE-613**
- `requiresCaregiverRelationship(OTHER)` behavior change — **PIE-613**
- BKE rule whitelist updates (`hi-fll.drl`, state benefit rules)
- Integration API contract extensions
- FMLA document generation relationship sets
- Data migration to add new relationships to existing templates

---

## Implementation checklist

- [ ] Confirm `DOMESTIC_PARTNER_GRANDCHILD` caregiver-type placement
- [ ] Add `CaregiverRelationshipType` values in `models.py`
- [ ] Update nested sub-enums (`SpouseRelationshipType`, `ChildUnder18/Over18`, `GrandchildRelationshipType`)
- [ ] Run and commit Django migration (all 4 fields)
- [ ] Update bulk-import `ACCEPTED_VALUES["caregiver_relationship"]`
- [ ] Add `ECaregiverRelationship` values in `constants/types/index.ts`
- [ ] Update `caregiverRelationshipMap` and `caregiverRelationshipMapByType` in `leaves.ts`
- [ ] Add `CHILD_RELATIONSHIP_TO_OVER_18` pair + `getSurveyRelationshipLabel` fallback in `caregiverSurveyOptions.ts`
- [ ] Add/update tests per Phase 3
- [ ] Manual QA on PayCalc Item Template modal
- [ ] Open PR

---

## Branch

`pie-612-caregiving-relationship-paycalc-templates`

---

## Handoff prompt (copy for a fresh AI session)

```
Implement PIE-612: Add missing caregiving relationship types to paycalc item templates.

Read first:
1. The implementation plan for this ticket (local agent docs — not in the repo)
2. .ai/rules/frontend/frontend-quality-standards.mdc
3. .ai/rules/backend/backend-quality-standards.mdc
4. .ai/rules/testing/testing-standards.mdc

Prerequisites:
- Branch from latest main: pie-612-caregiving-relationship-paycalc-templates
- Confirm DOMESTIC_PARTNER_GRANDCHILD maps under GRANDCHILD (not CHILD) unless PM says otherwise

Scope:
- 12 new CaregiverRelationshipType enum values (3 spouse + 2 child U18/O18 + 1 grandchild + 6 other)
- Backend: main enum, nested sub-enums (Spouse/ChildUnder18/ChildOver18/Grandchild), Django migration (leave, historicalleave, paycalcitemtemplate, historicalpaycalcitemtemplate)
- Bulk import: add new labels to ACCEPTED_VALUES["caregiver_relationship"] in bulk_leave_import/config.py
- Frontend: ECaregiverRelationship, caregiverRelationshipMap, caregiverRelationshipMapByType (including new OTHER entry), mapChildRelationshipForAge for DOMESTIC_PARTNER_CHILD_U18/O18

Do NOT touch (PIE-613 / follow-up):
- Leave survey SURVEY_RELATIONSHIP_LABELS or requiresCaregiverRelationship(OTHER)
- BKE rule whitelists (hi-fll.drl RECIPROCAL_BENEFICIARY stays commented)
- Integration API contract

Key files:
- backend/legacy/models.py
- backend/integrations/services/bulk_leave_import/config.py
- frontend/client/constants/types/index.ts
- frontend/client/_types/leaves.ts
- frontend/client/screens/Shared/LeaveSurvey/Steps/Caregiver/caregiverSurveyOptions.ts (CHILD_RELATIONSHIP_TO_OVER_18 pair + getSurveyRelationshipLabel fallback)
- frontend/client/components/PlanCalendar/PayCalcItemModal.tsx (verify only — auto-picks up maps)

Tests:
- test_paycalc_item_template_serializers.py (save new values)
- caregiverSurveyOptions.test.ts (age mapping)
- PayCalcItemModal.test.tsx (dropdown options)
- test_leave.py (_is_correct_caregiver with new values)
- bulk import ACCEPTED_VALUES

Definition of done: acceptance criteria in plan; manual QA on paycalc item template modal.

When complete, create a GitHub pull request using the GitHub CLI (gh). You may need to set an environment variable (e.g. GH_TOKEN or GITHUB_TOKEN) for the CLI to authenticate.
```
