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

inventory_snapshots as (
    select store_id, product_id, snapshot_date, received_qty
    from {{ ref('fct_inventory_snapshot') }}
)

select
    delivery_receipts.store_id,
    delivery_receipts.product_id,
    delivery_receipts.snapshot_date,
    delivery_receipts.delivered_qty,
    inventory_snapshots.received_qty
from delivery_receipts
left join inventory_snapshots
    on delivery_receipts.store_id = inventory_snapshots.store_id
    and delivery_receipts.product_id = inventory_snapshots.product_id
    and delivery_receipts.snapshot_date = inventory_snapshots.snapshot_date
where delivery_receipts.delivered_qty != coalesce(inventory_snapshots.received_qty, -1)

union all

select
    inventory_snapshots.store_id,
    inventory_snapshots.product_id,
    inventory_snapshots.snapshot_date,
    delivery_receipts.delivered_qty,
    inventory_snapshots.received_qty
from inventory_snapshots
left join delivery_receipts
    on inventory_snapshots.store_id = delivery_receipts.store_id
    and inventory_snapshots.product_id = delivery_receipts.product_id
    and inventory_snapshots.snapshot_date = delivery_receipts.snapshot_date
where inventory_snapshots.received_qty > 0
    and delivery_receipts.store_id is null
