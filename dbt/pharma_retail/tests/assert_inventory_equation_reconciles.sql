select *
from {{ ref('fct_inventory_snapshot') }}
where opening_stock + received_qty - sold_qty + adjustment_qty != closing_stock
