with expected as (
    select
        inputs.store_id,
        inputs.product_id,
        inputs.snapshot_date,
        coalesce(sum(iff(
            orders.order_date <= inputs.snapshot_date
            and orders.actual_delivery_date > inputs.snapshot_date,
            orders.ordered_qty,
            0
        )), 0) as on_order_qty
    from {{ ref('int_inventory_daily_inputs') }} as inputs
    left join {{ ref('int_supplier_orders') }} as orders
        on inputs.store_id = orders.store_id
        and inputs.product_id = orders.product_id
    group by inputs.store_id, inputs.product_id, inputs.snapshot_date
),

actual as (
    select store_id, product_id, snapshot_date, on_order_qty
    from {{ ref('fct_inventory_snapshot') }}
)

select
    coalesce(expected.store_id, actual.store_id) as store_id,
    coalesce(expected.product_id, actual.product_id) as product_id,
    coalesce(expected.snapshot_date, actual.snapshot_date) as snapshot_date
from expected
full outer join actual
    on expected.store_id = actual.store_id
    and expected.product_id = actual.product_id
    and expected.snapshot_date = actual.snapshot_date
where expected.store_id is null
    or actual.store_id is null
    or expected.on_order_qty != actual.on_order_qty
