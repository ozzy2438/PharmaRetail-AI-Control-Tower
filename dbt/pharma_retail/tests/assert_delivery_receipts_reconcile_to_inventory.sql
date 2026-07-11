with delivery_receipts as (
    select
        store_id,
        product_id,
        actual_delivery_date as snapshot_date,
        sum(delivered_qty) as delivered_qty
    from {{ ref('fct_supplier_delivery') }}
    where actual_delivery_date between '2026-01-01'::date and '2026-03-31'::date
    group by store_id, product_id, actual_delivery_date
),

inventory_receipts as (
    select store_id, product_id, snapshot_date, received_qty
    from {{ ref('fct_inventory_snapshot') }}
    where received_qty > 0
)

select
    coalesce(delivery_receipts.store_id, inventory_receipts.store_id) as store_id,
    coalesce(delivery_receipts.product_id, inventory_receipts.product_id) as product_id,
    coalesce(delivery_receipts.snapshot_date, inventory_receipts.snapshot_date) as snapshot_date,
    delivery_receipts.delivered_qty,
    inventory_receipts.received_qty
from delivery_receipts
full outer join inventory_receipts
    on delivery_receipts.store_id = inventory_receipts.store_id
    and delivery_receipts.product_id = inventory_receipts.product_id
    and delivery_receipts.snapshot_date = inventory_receipts.snapshot_date
where coalesce(delivery_receipts.delivered_qty, -1) != coalesce(inventory_receipts.received_qty, -1)
