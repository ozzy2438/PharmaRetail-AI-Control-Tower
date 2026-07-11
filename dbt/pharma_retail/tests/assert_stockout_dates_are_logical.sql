select *
from {{ ref('fct_stockout_event') }}
where stockout_start_date > stockout_end_date
    or stockout_days != datediff(day, stockout_start_date, stockout_end_date) + 1
