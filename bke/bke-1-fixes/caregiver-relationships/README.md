# Caregiver relationship LC test matrices

CSV files for L&C / QA when exercising **caregiver** leave types on state BKE
entitlements. Each row is one scenario to run (or to expect) when other
eligibility inputs are satisfied.

## Files

| File                                             | Benefit                                        |
| ------------------------------------------------ | ---------------------------------------------- |
| `caregiver-relationships-ri-tci.csv`             | RI Temporary Caregiving Insurance              |
| `caregiver-relationships-mn-pfml-caregiving.csv` | MN PFML Paid Family (caregiving → family bank) |
| `caregiver-relationships-wi-fmla-caregiving.csv` | WI FMLA Caregiving                             |
| `caregiver-relationships-nj-fli.csv`             | NJ Paid Family Leave Insurance (FLI)           |
| `caregiver-relationships-ny-pfl.csv`             | NY Paid Family Leave                           |
| `caregiver-relationships-all-benefits.csv`       | All of the above (filter by `benefit` column)  |

## Regenerate

```bash
python3 ai-docs/bke-1-fixes/caregiver-relationships/generate_caregiver_relationship_csvs.py
```

Sources are named in the `code_source` column (rule tuples, template fixtures,
or tests).

## Column guide

- **covered_by_rule** — Yes/No/N/A for whether this relationship is on the
  allow-list (or N/A for null survey).
- **expected_bke_result** — Eligible / Ineligible / Missing / Manual when enum
  cannot represent L&C yet (MN chosen family).
- **how_rule_enforces** — Template `is_correct_caregiver` vs code `field_in`
  allow-list (important for enablement).

Import the combined CSV into Google Sheets or use a per-state file for a single
entitlement test pass.
