"""Settle the Q2 2026 national HPRD: is it 3.37 or 3.38?

Prints the exact national weighted HPRD per quarter, excluding reporting-gap facilities
(the convention the pipeline's regression test uses), to 4 decimals.

  python3 check_numbers.py
"""
from db import run_sql

result = run_sql(
    """
    select quarter,
           count(*)                                         as facilities,
           round(sum(nurse_hrs) / sum(resident_days), 4)    as hprd_excl_gaps,
           round(avg(iff(below_reference, 1.0, 0.0)), 4)    as pct_below_3,
           round(sum(contract_hrs) / sum(nurse_hrs), 4)     as contract_share
    from marts.mart_facility_quarter
    where not is_reporting_gap
    group by quarter
    order by quarter
    """
)
print(" | ".join(result["columns"]))
for row in result["rows"]:
    print(" | ".join(str(v) for v in row))
