# Clipboard Health Staffing Project: Metric Glossary

These are the definitions used by the staffing pipeline (`clipboard_health_pipeline`, dbt project `clipboard_health`), the staffing dashboard, and this assistant. Where a project definition differs from CMS's own calculation, the difference is stated.

## HPRD (hours per resident day)
HPRD is total direct-care nurse hours divided by total resident-days. It is always a weighted measure: hours and resident-days are summed first, then divided. A simple average of daily or facility HPRDs is never used, because it gives a 30-bed facility the same weight as a 300-bed facility.

- Facility-quarter HPRD = sum of nurse hours across the quarter / sum of daily MDS census across the quarter (`MART_FACILITY_QUARTER.HPRD`).
- State-quarter HPRD = sum of nurse hours for all facilities in the state / sum of their resident-days (`MART_STATE_QUARTER.HPRD`).
- National HPRD = the same calculation across all facilities.

Resident-days come from the daily MDS census (`MDSCENSUS` in the PBJ file). Days with zero census are dropped before any calculation, as in the original Data Analyst project.

## Nurse hours used in this project
Nurse hours = RN hours + LPN hours + CNA hours (`HRS_RN + HRS_LPN + HRS_CNA`), each including both employee and contract hours.

This is narrower than CMS's "total nurse staffing" in the PBJ public use file exclusion rules, which also counts RN Director of Nursing, RN and LPN with administrative duties, Medication Aide/Technician, and Nurse Aide in Training hours. Director of Nursing and administrative hours are loaded but are not part of project HPRD. Because of this, project HPRD is slightly lower than a figure computed with every CMS nursing category.

Data cleaning: Director of Nursing hours are capped at 24 per day, because the Data Analyst project found entries above 24 hours in a single day.

## Contract share
Contract share = contract nurse hours / total nurse hours, where contract nurse hours = RN contract + LPN contract + CNA contract hours (`HRS_RN_CTR + HRS_LPN_CTR + HRS_CNA_CTR`). In PBJ, "contract" covers agency and contract staff who are not on the facility's payroll; CMS requires facilities to report their hours along with employee hours.

A facility with zero nurse hours gets a contract share of 0. State and national contract shares are weighted the same way as HPRD: sum contract hours, sum nurse hours, then divide.

## Reporting gap (IS_REPORTING_GAP)
A facility-quarter is flagged as a reporting gap when its quarter HPRD is below 0.5 (dbt variable `reporting_gap_hprd`). Real nursing homes do not staff at under half an hour of nursing care per resident per day, so these records almost certainly have missing payroll submissions rather than real staffing levels.

Reporting-gap facilities are excluded from all national, state, and percentage figures by default. This matches the published dashboard, `MART_STATE_QUARTER` (which already excludes them), and the pipeline's regression test. About 20 facilities were flagged in Q2 2024 and 14 in Q2 2026. Including them lowers national HPRD slightly (for example 3.29 instead of 3.30 for Q2 2024).

## Below 3.0 HPRD (BELOW_REFERENCE)
`BELOW_REFERENCE` is TRUE when a facility's quarter HPRD is under 3.0 (dbt variable `hprd_reference`). The 3.0 line is an analysis reference carried over from the Data Analyst project. It is not a federal or state regulatory requirement. The percentage of facilities below 3.0 is the share of non-reporting-gap facilities with `BELOW_REFERENCE` TRUE.

## Low-staffing day
A low-staffing day is a facility-day with daily HPRD under 1.5 (dbt variable `low_day_hprd`), counted in `FCT_FACILITY_DAY.IS_LOW_DAY`. `MART_FACILITY_QUARTER.DAYS_BELOW_LOW_THRESHOLD` counts them per facility per quarter.

## Watchlist facility
A watchlist facility has 10 or more low-staffing days in a quarter (`DAYS_BELOW_LOW_THRESHOLD >= 10`). `MART_STATE_QUARTER.WATCHLIST_FACILITIES` counts them by state, excluding reporting-gap facilities.

## Quarter-over-quarter change
`MART_FACILITY_QUARTER.HPRD_CHANGE` and `CONTRACT_SHARE_CHANGE` compare a facility's quarter with its previous loaded quarter (`PREV_QUARTER`). The loaded quarters are 2024Q2, 2025Q3, 2025Q4, 2026Q1 and 2026Q2, so the change into 2025Q3 is measured against 2024Q2, which is five quarters apart, not one.

## Quarters loaded and data sources
Quarters are written like `2024Q2`. The pipeline loads PBJ Daily Nurse Staffing for 2024Q2 (to reconcile with the Data Analyst project) and 2025Q3 through 2026Q2, plus the latest monthly CMS Provider Information snapshot (star ratings, ownership, certified beds, location). Questions about other quarters cannot be answered from this data.

## Data quality checks
- Row counts: the rows loaded into Snowflake must equal the rows in each source file. This test exists because an Excel export in the first version of the project silently cut the data off at 1,048,575 rows.
- Daily plausibility: a warning-level test flags facility-days with negative hours or more than 24 nursing hours per resident (247 facility-days across 5 quarters, fewer than 1 in 25,000). They are kept but reviewed rather than silently dropped.
- Regression: Q2 2024 must reproduce the published dashboard: national HPRD 3.30, 34% of facilities below 3.0, and 7.7% contract share.

## Tables (Snowflake CLIPBOARD_HEALTH.MARTS)
- `FCT_FACILITY_DAY`: one row per facility per day with residents present.
- `DIM_FACILITY`: one row per facility: name, city, state, ownership type, certified beds, overall and staffing star ratings.
- `MART_FACILITY_QUARTER`: one row per facility per quarter: weighted HPRD, contract share, reporting-gap and below-3.0 flags, low-staffing days, quarter-over-quarter change, facility attributes.
- `MART_STATE_QUARTER`: one row per state per quarter (reporting gaps excluded): HPRD, share below 3.0, contract share, share with no contract staff, watchlist count.
- `MART_STATE_DAY`: one row per state per day, for trend lines.
