select *
from {{ ref('fct_inventory_snapshot') }}
where is_discontinued
    and sold_qty != 0
