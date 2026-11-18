# Staffing brief: 2026Q2

_Generated 2026-11-18 16:45 by the staffing monitor agent (`claude-sonnet-5-5`). Read-only; every number below comes from a query listed in the evidence appendix._

## Summary
I found no state-wide change in 2026Q2. Most of the large facility HPRD drops in the detection list look like reporting artifacts, not real staffing changes. The artifacts fall into three groups. Zero-hour periods (Jones Co MS, Community First IL, Meadville TCU PA, plus Maplewood NY, Imperial Manor CA, Poway CA and Providence Torrance CA, which I only checked at monthly level and did not record separately). Dropped job categories (Sequoias SF, Good Shepherd Bethlehem). Labor-type reclassification (River Walk, with contract share going to 100% at flat HPRD). Eleven facilities are newly in reporting gap, including 4 in MO. The one facility I'd follow up as a possible real change is Fairview OK, which fell from 3.05 to 1.10 HPRD with 82 low days and agency hours only. It needs payroll verification first. MO stays at 2.49 HPRD with a persistent 98-facility watchlist, a steady staffing-demand market. PR and the other flagged small states show noise only. Tweeten MN's "improvement" is a reversal of a Q1 artifact. I'd re-run detection after the next PBJ refresh and add a zero-hour-day filter to the artifact screen.

**Signals detected:** 125 facilities with HPRD down 0.75+, 104 with contract share up 15+ points (of 14,443 facilities with a previous quarter), 11 new reporting gaps, 12 states past thresholds.
**Findings:** 0 high, 3 medium, 9 low.

## Findings
### 1. [MEDIUM] Fairview Fellowship Home For Senior Citizens (375427)
**Fairview (OK) HPRD fell from 3.05 to 1.10 in 2026Q2 with 82 low-staffing days, while contract share jumped from 34.6% to 100%.**

Census was stable (69.4 to 69.9) and 91 days were reported. The drop is a step change on April 1. Contract HPRD stayed at about 1.0 to 1.16, while RN, LPN and CNA hours fell by about two thirds (LPN 0.79 to 0.34, CNA 2.33 to 0.79). That pattern looks like employee payroll hours missing from the submission, so only agency hours remain. It is probably not a real 100% agency conversion. A real loss of employee staff can't be ruled out, and it would be a 1-star home with 93% turnover running agency-only, which is a strong staffing-demand signal.

*Recommended action:* Check with the facility or the CMS PBJ submission whether employee hours were submitted for April to June. If they were, treat this as an urgent agency-demand lead.

*Evidence:* Q3, Q11, Q13

### 2. [MEDIUM] Data quality: new reporting gaps (11 facilities) and zero-hour days
**11 facilities newly fell into reporting gaps (HPRD 0.03 to 0.50), 4 of them in MO, and many other big "drops" show zero-hour days.**

Every one of the gap facilities reported 91 days with a stable census, and most had a normal prior HPRD (for example Bethany Home WI went from 4.25 to 0.03, Rolling Fields PA from 3.58 to 0.04, Maple Lawn MO from 3.61 to 0.39). These are missing payroll submissions. Similar zero-hour spells (May and June at Maplewood NY, April at Providence Torrance, June at Poway, Imperial Manor) show up just below the 0.5 cutoff and stay in state figures. The detection list's biggest HPRD drops are largely artifacts, which suggests a late-quarter submission lag in this load.

*Recommended action:* Re-run the detection after the next PBJ refresh. Consider a zero-hour-day count as a second artifact filter alongside the 0.5 HPRD gap rule.

*Evidence:* Q16, Q12

### 3. [MEDIUM] MO
**MO is flat at 2.49 HPRD (2.47 in 2026Q1), with 77.2% of facilities below 3.0 and a watchlist of 98 (up from 92), the largest of any flagged state.**

There is no state-wide move. HPRD, the share below 3.0 and contract share (4.5%) have barely changed since 2024Q2 (2.42, 78.6%, 7.6%). The 98 watchlist facilities are a persistent structural level, so MO is a steady staffing-demand market. Four of the quarter's new reporting-gap facilities are in MO and are excluded from the state figures, which could understate the true low-staffing picture.

*Recommended action:* Treat MO as a persistently understaffed market for planning. Don't call it a new change. Re-check the watchlist count once MO submissions are resolved.

*Evidence:* Q8, Q16

### 4. [LOW] Jones Co Rest Home (255336)
**Jones Co Rest Home (MS) HPRD dropped from 4.01 to 1.28 with 61 low days, because zero nursing hours were reported for all of May and June.**

April HPRD was 3.91. May and June show 0.0 nurse hours every day (61 days) while census held at about 118 residents. A 122-bed home with no nursing hours is not plausible, so this is a missing-payroll artifact. The quarter average of 1.28 stays above the 0.5 reporting-gap cutoff, so the pipeline does not exclude it, and it counts as a watchlist facility.

*Recommended action:* Exclude from staffing-change counts. Re-check after the next PBJ resubmission. Don't treat as a staffing-demand lead.

*Evidence:* Q6, Q11

### 5. [LOW] Community First Medical Center (145548)
**Community First (IL) HPRD fell from 6.06 to 2.11 with 61 low days because nursing hours went to about zero from May 1.**

April HPRD was 5.95. May shows 0.04 and June 0.0, with census steady at 8 to 10 residents. This is a hospital-based unit with a very small census, and the quarter flows through as if it were a real decline. Zero hours across 61 days with residents present is a reporting stop, not a staffing change.

*Recommended action:* Log as a reporting artifact. Re-check after the next PBJ refresh.

*Evidence:* Q2, Q11

### 6. [LOW] Meadville Medical Ctr TCU (395894)
**Meadville TCU (PA) HPRD fell from 10.60 to 2.22 with 65 low days, alongside a census jump from 17.9 to 25.0 and zero hours reported from May.**

This is a 32-bed transitional care unit, which is a special unit. April HPRD was 9.14. May has 27 zero-hour days, and June has 30 zero-hour days while census rose to 33.5. Zero hours combined with a census swing point to a reporting artifact, not a real staffing collapse.

*Recommended action:* Log as a reporting artifact. Exclude TCU units from staffing-demand screening.

*Evidence:* Q1, Q12

### 7. [LOW] Sequoias San Francisco Convalescent Hospital (056071)
**Sequoias SF (CA) HPRD fell from 4.30 to 1.04 with 79 low days, because LPN and CNA hours dropped to 0.0 from April 1.**

Census was stable (38.5 to 36.0) and all 91 days were reported. RN HPRD held at about 1.0 (0.98 to 1.14), while LPN went from 0.43 to 0.0 and CNA from 2.75 to 0.0. A home keeping RNs but having no LPNs or aides is not plausible. This looks like missing job categories in the submission. The same pattern shows at Good Shepherd Bethlehem, where CNA hours vanished.

*Recommended action:* Treat as a reporting artifact and verify the PBJ job-category mapping. Don't count it as demand.

*Evidence:* Q4, Q11, Q13

### 8. [LOW] Good Shepherd Home-Bethlehem (396108)
**Good Shepherd Bethlehem (PA) HPRD fell from 4.62 to 2.08, driven by CNA hours collapsing from 2.45 to 0.03 in April.**

Census was stable (58.5 to 57.5), 91 days were reported, and the facility has a 5-star overall rating. RN and LPN levels were unchanged (RN 1.29 to 1.46 against 1.38 in January). Only the CNA category vanished, on April 1, and it stays near zero. That is a submission or job-category mapping error, not a real loss of aides. The 0 low days also suggests the daily threshold is not catching this.

*Recommended action:* Log as an artifact. Confirm CNA mapping in the next PBJ submission.

*Evidence:* Q17, Q18

### 9. [LOW] River Walk Care Center (555658)
**River Walk (CA) shows contract share of 100% (from 0.0%) in 2026Q2, but HPRD is flat at 3.98 (vs 4.07).**

Contract share was 1.0 in every month from April, with 0 low days and 91 days reported. Census was stable (88.7 to 93.4), and the monthly HPRD range of 3.93 to 4.10 shows no change in care hours. Total hours didn't change, so this is a labor-type reclassification of employee hours as contract in the payroll feed, not a switch to agency staffing. Similar artifacts inflate the 104 big-contract-rise count.

*Recommended action:* Don't treat as agency demand. Flag for contract-classification review.

*Evidence:* Q7, Q12

### 10. [LOW] Flandreau Santee Sioux Tribe Care Center (43A139)
**Flandreau (SD) HPRD of 2.41 against 6.34 in 2025Q4, with contract share at 100% and 15 low days, but monthly HPRD is climbing back (1.89, 2.36, 2.89).**

Contract share was 1.0 in every month, and employee CNA hours were absent in April (CNA 0.48) before returning (1.47, then 2.42). That looks like employee payroll being submitted late or in stages, not a real move to agency. The 2026Q1 quarter is also missing from the loaded data, so the quarter-over-quarter comparison spans two quarters. The 15 low days are concentrated in April and May.

*Recommended action:* Log as a reporting artifact. Re-check June-level HPRD next quarter and find out why 2026Q1 is missing.

*Evidence:* Q5, Q13

### 11. [LOW] Tweeten Lutheran Health Care Center (245429)
**Tweeten (MN) HPRD "rose" 2.64 to 3.45, but this reverses a 2026Q1 crash to 0.80 (88 low days) and returns to its normal range.**

HPRD was 3.24 to 3.74 in earlier quarters, then 0.73 to 0.90 in January to March, then 3.10 in April. The monthly series then climbs to 4.08 in June. The Q1 drop was a one-quarter artifact, so this isn't a real improvement. Contract share rose from 20.3% to 37.8% while census slipped from 35.6 to 29.5. The facility is an SFF Candidate with a 1-star rating and 91.8% turnover, so the staffing level and agency use may be real signals.

*Recommended action:* Don't report as an improvement. Monitor the rising contract share (a possible agency-demand lead) and re-check next quarter.

*Evidence:* Q14, Q12

### 12. [LOW] PR
**PR HPRD rose to 3.29 from 2.97 and the share below 3.0 fell from 50.0% to 12.5%, but this is only 8 facilities.**

With 8 facilities, a single facility's move changes the state number a lot, and the series is volatile (4.12, 2.48, 3.01, 2.97, 3.29). The one-facility swing (50.0% to 12.5% equals 4 facilities to 1) is small-sample noise. SD (3.12 vs 3.04, watchlist 3 vs 4) and the other flagged states (DC, HI, OR, VA, CT, WY, MT, AK, ME) have small moves under 0.35 HPRD.

*Recommended action:* No action. Treat small-state moves as noise unless they persist for 2+ quarters.

*Evidence:* Q10, Q9

## Run details
- Stop reason: finished; tool calls: 34 (limit 40); tokens: 408,357 in / 11,121 out (budget 800,000)

## Evidence appendix

**Q1** (4 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '395894' order by f.quarter
```

**Q2** (5 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '145548' order by f.quarter
```

**Q3** (5 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '375427' order by f.quarter
```

**Q4** (5 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '056071' order by f.quarter
```

**Q5** (4 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '43A139' order by f.quarter
```

**Q6** (5 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '255336' order by f.quarter
```

**Q7** (5 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '555658' order by f.quarter
```

**Q8** (5 rows)
```sql
select quarter, facilities, round(hprd, 2) as hprd,
                       round(pct_facilities_below_reference * 100, 1) as pct_below_3,
                       round(contract_share * 100, 1) as contract_pct, watchlist_facilities
                from marts.mart_state_quarter where state = 'MO' order by quarter
```

**Q9** (5 rows)
```sql
select quarter, facilities, round(hprd, 2) as hprd,
                       round(pct_facilities_below_reference * 100, 1) as pct_below_3,
                       round(contract_share * 100, 1) as contract_pct, watchlist_facilities
                from marts.mart_state_quarter where state = 'SD' order by quarter
```

**Q10** (5 rows)
```sql
select quarter, facilities, round(hprd, 2) as hprd,
                       round(pct_facilities_below_reference * 100, 1) as pct_below_3,
                       round(contract_share * 100, 1) as contract_pct, watchlist_facilities
                from marts.mart_state_quarter where state = 'PR' order by quarter
```

**Q11** (27 rows)
```sql
select ccn, date_trunc('month', work_date) m, count(*) days, round(avg(census),1) census, round(sum(nurse_hrs)/nullif(sum(census),0),2) hprd, round(sum(contract_hrs)/nullif(sum(nurse_hrs),0),2) cshare, sum(is_low_day) low_days, round(avg(nurse_hrs),1) avg_hrs from marts.fct_facility_day where quarter in ('2026Q1','2026Q2') and ccn in ('255336','056071','375427','145548','43A139') group by 1,2 order by 1,2
```

**Q12** (57 rows)
```sql
select ccn, date_trunc('month', work_date) m, count(*) days, round(avg(census),1) census, round(sum(nurse_hrs)/nullif(sum(census),0),2) hprd, round(sum(contract_hrs)/nullif(sum(nurse_hrs),0),2) cshare, sum(is_low_day) low_days, round(avg(nurse_hrs),1) avg_hrs, sum(case when nurse_hrs=0 then 1 else 0 end) zero_days from marts.fct_facility_day where quarter in ('2026Q1','2026Q2') and ccn in ('056499','555301','055258','335098','555919','245429','335572','396108','555658','395894') group by 1,2 order by 1,2
```

**Q13** (15 rows)
```sql
select ccn, date_trunc('month', work_date) m, round(sum(rn_hrs)/sum(census),2) rn_hprd, round(sum(lpn_hrs)/sum(census),2) lpn_hprd, round(sum(cna_hrs)/sum(census),2) cna_hprd, round(sum(contract_hrs)/sum(census),2) contract_hprd from marts.fct_facility_day where quarter in ('2026Q1','2026Q2') and ccn in ('056071','375427','43A139') group by 1,2 order by 1,2
```

**Q14** (5 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '245429' order by f.quarter
```

**Q16** (20 rows)
```sql
select f.ccn, f.state, f.provider_name, f.quarter, round(f.hprd,2) hprd, f.days_reported, round(f.avg_census,1) census, f.is_reporting_gap from marts.mart_facility_quarter f where f.ccn in ('115262','175323','195632','265733','265430','265237','265149','365794','375246','395619','525538') and f.quarter in ('2026Q1','2026Q2') order by f.ccn, f.quarter
```

**Q17** (6 rows)
```sql
select date_trunc('month', work_date) m, round(avg(census),1) census, round(sum(rn_hrs)/sum(census),2) rn_hprd, round(sum(lpn_hrs)/sum(census),2) lpn_hprd, round(sum(cna_hrs)/sum(census),2) cna_hprd, round(sum(rn_don_hrs)/sum(census),2) don_hprd, sum(is_low_day) low_days, min(daily_hprd) min_d, max(daily_hprd) max_d from marts.fct_facility_day where ccn='396108' and quarter in ('2026Q1','2026Q2') group by 1 order by 1
```

**Q18** (5 rows)
```sql
select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '396108' order by f.quarter
```
