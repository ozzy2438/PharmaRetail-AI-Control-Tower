select *
from {{ ref('int_store_product_daily') }}
where gross_sales < 0
    or returned_units < 0
    or return_rate < 0
    or has_sales_flag != (units_sold > 0)
    or has_return_flag != (returned_units > 0)
    or net_units != units_sold - returned_units
    or abs(net_sales - (gross_sales - return_value)) > 0.01
