select *
from {{ ref('fct_supplier_delivery') }}
where order_date > expected_delivery_date
    or order_date > actual_delivery_date
    or lead_time_days != datediff(day, order_date, actual_delivery_date)
    or late_delivery_flag != (actual_delivery_date > expected_delivery_date)
