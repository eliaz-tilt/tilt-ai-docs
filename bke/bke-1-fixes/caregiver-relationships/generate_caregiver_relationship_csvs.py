#!/usr/bin/env python3
"""Generate LC caregiver-relationship test matrices from in-repo allow-lists.

Run from repo root:
  python3 ai-docs/bke-1-fixes/caregiver-relationships/generate_caregiver_relationship_csvs.py
"""

from __future__ import annotations

import csv
from pathlib import Path

# Mirrors Leave.CaregiverRelationshipType labels (legacy/models.py).
SURVEY_LABELS: dict[str, str] = {
    "SPOUSE": "Spouse",
    "DOMESTIC_PARTNER": "Domestic Partner",
    "PARENT": "Parent",
    "STEP_PARENT": "Step-Parent",
    "PARENT_IN_LAW": "Parent-in-Law",
    "LEGAL_GUARDIAN": "Legal Guardian",
    "CHILD": "Child",
    "STEP_CHILD": "Step-Child",
    "CHILD_IN_LAW": "Child-in-Law",
    "FOSTER_CHILD": "Foster Child",
    "LEGAL_CUSTODY": "Someone you have legal custody of",
    "CHILD_U18": "Child (Under 18)",
    "STEP_CHILD_U18": "Step-Child (Under 18)",
    "CHILD_IN_LAW_U18": "Child-in-Law (Under 18)",
    "FOSTER_CHILD_U18": "Foster Child (Under 18)",
    "LEGAL_CUSTODY_U18": "Someone you have legal custody of (Under 18)",
    "CHILD_O18": "Child (Over 18)",
    "STEP_CHILD_O18": "Step-Child (Over 18)",
    "CHILD_IN_LAW_O18": "Child-in-Law (Over 18)",
    "FOSTER_CHILD_O18": "Foster Child (Over 18)",
    "LEGAL_CUSTODY_O18": "Someone you have legal custody of (Over 18)",
    "SIBLING": "Sibling",
    "STEP_SIBLING": "Step-Sibling",
    "SIBLING_DOMESTIC_PARTNER": "Sibling's Domestic Partner",
    "STEP_SIBLING_DOMESTIC_PARTNER": "Step-Sibling's Domestic Partner",
    "SIBLING_IN_LAW": "Sibling-in-Law",
    "HALF_SIBLING": "Half-Sibling",
    "GRANDPARENT": "Grandparent",
    "STEP_GRANDPARENT": "Step-Grandparent",
    "SPOUSE_GRANDPARENT": "Spouse's Grandparent",
    "GRANDPARENT_SPOUSE": "Grandparent's Spouse or Domestic Partner",
    "GRANDCHILD": "Grandchild",
    "STEP_GRANDCHILD": "Step-Grandchild",
}

FIELDNAMES = [
    "benefit",
    "state",
    "leave_type",
    "relationship_api_value",
    "survey_label",
    "covered_by_rule",
    "expected_bke_result",
    "how_rule_enforces",
    "lc_testing_notes",
    "code_source",
]

# Allow-lists and negatives sourced from benefits rule code / tests (2026-07).
BENEFIT_SPECS: list[dict] = [
    {
        "benefit": "RI Temporary Caregiving Insurance (TCI)",
        "state": "RI",
        "how_rule_enforces": "Template caregiver_relationship via is_correct_caregiver; must match RI_TCI_CAREGIVER_RELATIONSHIPS",
        "code_source": "benefits/rules/rhode_island/tci.py RI_TCI_CAREGIVER_RELATIONSHIPS",
        "covered": [
            "SPOUSE",
            "DOMESTIC_PARTNER",
            "PARENT",
            "PARENT_IN_LAW",
            "CHILD_U18",
            "CHILD_O18",
            "STEP_CHILD_U18",
            "STEP_CHILD_O18",
            "GRANDPARENT",
            "SIBLING",
        ],
        "negative_examples": [
            ("SIBLING_IN_LAW", "Ineligible — not on RI TCI allow-list"),
            ("LEGAL_GUARDIAN", "Ineligible — not on RI TCI allow-list"),
        ],
    },
    {
        "benefit": "MN PFML Paid Family (caregiving)",
        "state": "MN",
        "how_rule_enforces": "Template caregiver_relationship via is_correct_caregiver; production template must match L&C doc set",
        "code_source": "benefits/rules/minnesota/tests/pfml/test_caregiver_relationships.py DOC_COVERED_RELATIONSHIPS",
        "covered": [
            "SPOUSE",
            "DOMESTIC_PARTNER",
            "PARENT",
            "PARENT_IN_LAW",
            "CHILD_U18",
            "CHILD_O18",
            "CHILD_IN_LAW_U18",
            "CHILD_IN_LAW_O18",
            "GRANDPARENT",
            "GRANDCHILD",
            "SIBLING",
        ],
        "negative_examples": [
            ("SIBLING_IN_LAW", "Ineligible — covered in automated test"),
        ],
        "extra_rows": [
            {
                "relationship_api_value": "(survey: chosen family)",
                "survey_label": "Chosen family (L&C)",
                "covered_by_rule": "Unknown in BKE",
                "expected_bke_result": "Manual / follow-up",
                "lc_testing_notes": "L&C doc covers chosen family; no CaregiverRelationshipType enum value yet — not automatable in BKE until survey adds a value",
            },
        ],
    },
    {
        "benefit": "WI FMLA Caregiving",
        "state": "WI",
        "how_rule_enforces": "Template caregiver_relationship via is_correct_caregiver on WI FMLA Caregiving template",
        "code_source": "benefits/rules/wisconsin/tests/test_fmla.py template_wi_fmla_caregiving fixture",
        "covered": [
            "SPOUSE",
            "DOMESTIC_PARTNER",
            "CHILD_U18",
            "CHILD_O18",
            "PARENT",
            "PARENT_IN_LAW",
        ],
        "negative_examples": [
            ("SIBLING", "Ineligible — covered in test_caregiving_ineligible_when_relationship_not_supported"),
        ],
    },
    {
        "benefit": "NJ Paid Family Leave Insurance (FLI)",
        "state": "NJ",
        "how_rule_enforces": "Code allow-list field_in (NJ_FLI_COVERED_CAREGIVER_RELATIONSHIPS), not template is_correct_caregiver",
        "code_source": "benefits/rules/new_jersey/pfl.py NJ_FLI_COVERED_CAREGIVER_RELATIONSHIPS (PIE-447 branch)",
        "covered": [
            "PARENT",
            "STEP_PARENT",
            "PARENT_IN_LAW",
            "LEGAL_GUARDIAN",
            "SPOUSE",
            "DOMESTIC_PARTNER",
            "CHILD",
            "CHILD_U18",
            "CHILD_O18",
            "STEP_CHILD",
            "STEP_CHILD_U18",
            "STEP_CHILD_O18",
            "FOSTER_CHILD",
            "FOSTER_CHILD_U18",
            "FOSTER_CHILD_O18",
            "SIBLING",
            "GRANDPARENT",
            "STEP_GRANDPARENT",
            "GRANDCHILD",
            "STEP_GRANDCHILD",
        ],
        "negative_examples": [
            ("SIBLING_IN_LAW", "Ineligible — test_ineligible_caregiver_unsupported_relationship"),
        ],
    },
    {
        "benefit": "NY Paid Family Leave (PFL)",
        "state": "NY",
        "how_rule_enforces": "Code allow-list field_in (NY_PFL_COVERED_CAREGIVER_RELATIONSHIPS)",
        "code_source": "benefits/rules/new_york/pfl.py NY_PFL_COVERED_CAREGIVER_RELATIONSHIPS (PIE-468)",
        "covered": [
            "PARENT",
            "STEP_PARENT",
            "PARENT_IN_LAW",
            "SPOUSE",
            "DOMESTIC_PARTNER",
            "CHILD",
            "STEP_CHILD",
            "SIBLING",
            "STEP_SIBLING",
            "HALF_SIBLING",
            "GRANDPARENT",
            "GRANDCHILD",
        ],
        "negative_examples": [
            ("LEGAL_GUARDIAN", "Ineligible — test_ineligible_caregiver_unsupported_relationship"),
        ],
    },
]

MISSING_ROW_NOTES = (
    "Leave type Caregiver with caregiver_relationship unset/null — expect Missing (needs data), not ineligible"
)


def _rows_for_spec(spec: dict) -> list[dict]:
    rows: list[dict] = []
    base = {
        "benefit": spec["benefit"],
        "state": spec["state"],
        "leave_type": "Caregiver",
        "how_rule_enforces": spec["how_rule_enforces"],
        "code_source": spec["code_source"],
    }

    rows.append(
        {
            **base,
            "relationship_api_value": "(null / unanswered)",
            "survey_label": "",
            "covered_by_rule": "N/A",
            "expected_bke_result": "Missing",
            "lc_testing_notes": MISSING_ROW_NOTES,
        }
    )

    for rel in spec["covered"]:
        rows.append(
            {
                **base,
                "relationship_api_value": rel,
                "survey_label": SURVEY_LABELS.get(rel, ""),
                "covered_by_rule": "Yes",
                "expected_bke_result": "Eligible",
                "lc_testing_notes": "Assumes other eligibility inputs satisfied (earnings, tenure, flags, etc.)",
            }
        )

    for rel, note in spec.get("negative_examples", []):
        rows.append(
            {
                **base,
                "relationship_api_value": rel,
                "survey_label": SURVEY_LABELS.get(rel, ""),
                "covered_by_rule": "No",
                "expected_bke_result": "Ineligible",
                "lc_testing_notes": note,
            }
        )

    for extra in spec.get("extra_rows", []):
        rows.append({**base, **extra})

    return rows


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    all_rows: list[dict] = []
    slug_by_state = {
        "RI": "ri-tci",
        "MN": "mn-pfml-caregiving",
        "WI": "wi-fmla-caregiving",
        "NJ": "nj-fli",
        "NY": "ny-pfl",
    }
    for spec in BENEFIT_SPECS:
        rows = _rows_for_spec(spec)
        all_rows.extend(rows)
        slug = slug_by_state[spec["state"]]
        per_file = out_dir / f"caregiver-relationships-{slug}.csv"
        with per_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    combined = out_dir / "caregiver-relationships-all-benefits.csv"
    with combined.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {combined.name} ({len(all_rows)} rows) and {len(BENEFIT_SPECS)} per-benefit files in {out_dir}")


if __name__ == "__main__":
    main()
