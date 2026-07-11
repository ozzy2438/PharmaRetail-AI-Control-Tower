select *
from {{ ref('fct_promotion') }}
where start_date > end_date
    or discount_pct not between 0 and 100
    or expected_uplift < 0
    or actual_uplift < 0
