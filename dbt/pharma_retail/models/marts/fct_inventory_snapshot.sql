{{ config(tags=['phase4'], post_hook=phase4_scoped_hooks('ground_truth_root_cause')) }}

{% set anchor_available = "(inputs.initial_stock + inputs.received_qty)" %}
{% set anchor_sold = "case when inputs.is_discontinued or inputs.recall_active or inputs.force_writeoff then 0 else least(inputs.expected_demand, " ~ anchor_available ~ ") end" %}
{% set anchor_adjustment = "case when inputs.recall_active or inputs.force_writeoff then -(" ~ anchor_available ~ " - (" ~ anchor_sold ~ ")) when inputs.discrepancy_active then -least(3, " ~ anchor_available ~ " - (" ~ anchor_sold ~ ")) else 0 end" %}
{% set recursive_available = "(inventory.closing_stock + inputs.received_qty)" %}
{% set recursive_sold = "case when inputs.is_discontinued or inputs.recall_active or inputs.force_writeoff then 0 else least(inputs.expected_demand, " ~ recursive_available ~ ") end" %}
{% set recursive_adjustment = "case when inputs.recall_active or inputs.force_writeoff then -(" ~ recursive_available ~ " - (" ~ recursive_sold ~ ")) when inputs.discrepancy_active then -least(3, " ~ recursive_available ~ " - (" ~ recursive_sold ~ ")) else 0 end" %}

with recursive open_orders as (
    -- An order remains open until its deterministic actual delivery date. The
    -- full ordered quantity is therefore visible as on-order stock before its
    -- receipt is reflected in received_qty.
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

inputs_with_open_orders as (
    select
        inputs.*,
        open_orders.on_order_qty
    from {{ ref('int_inventory_daily_inputs') }} as inputs
    inner join open_orders
        on inputs.store_id = open_orders.store_id
        and inputs.product_id = open_orders.product_id
        and inputs.snapshot_date = open_orders.snapshot_date
),

inventory (
    store_id,
    region,
    product_id,
    supplier_id,
    snapshot_date,
    day_index,
    is_discontinued,
    ground_truth_root_cause,
    expected_demand,
    opening_stock,
    received_qty,
    on_order_qty,
    sold_qty,
    adjustment_qty,
    closing_stock
) as (
    select
        inputs.store_id,
        inputs.region,
        inputs.product_id,
        inputs.supplier_id,
        inputs.snapshot_date,
        inputs.day_index,
        inputs.is_discontinued,
        inputs.ground_truth_root_cause,
        inputs.expected_demand,
        inputs.initial_stock as opening_stock,
        inputs.received_qty,
        inputs.on_order_qty,
        {{ anchor_sold }} as sold_qty,
        {{ anchor_adjustment }} as adjustment_qty,
        {{ anchor_available }} - ({{ anchor_sold }}) + ({{ anchor_adjustment }})
            as closing_stock
    from inputs_with_open_orders as inputs
    where inputs.day_index = 1

    union all

    select
        inputs.store_id,
        inputs.region,
        inputs.product_id,
        inputs.supplier_id,
        inputs.snapshot_date,
        inputs.day_index,
        inputs.is_discontinued,
        inputs.ground_truth_root_cause,
        inputs.expected_demand,
        inventory.closing_stock as opening_stock,
        inputs.received_qty,
        inputs.on_order_qty,
        {{ recursive_sold }} as sold_qty,
        {{ recursive_adjustment }} as adjustment_qty,
        {{ recursive_available }} - ({{ recursive_sold }}) + ({{ recursive_adjustment }})
            as closing_stock
    from inventory
    inner join inputs_with_open_orders as inputs
        on inventory.store_id = inputs.store_id
        and inventory.product_id = inputs.product_id
        and inputs.day_index = inventory.day_index + 1
),

inventory_with_coverage as (
    select
        *,
        avg(expected_demand) over (
            partition by store_id, product_id
            order by snapshot_date
            rows between 6 preceding and current row
        ) as rolling_average_demand
    from inventory
)

select
    md5(store_id || '|' || product_id || '|' || snapshot_date) as inventory_snapshot_id,
    snapshot_date,
    store_id,
    region,
    product_id,
    supplier_id,
    is_discontinued,
    ground_truth_root_cause,
    expected_demand,
    opening_stock,
    received_qty,
    on_order_qty,
    sold_qty,
    adjustment_qty,
    closing_stock,
    case
        when rolling_average_demand > 0 then round(closing_stock / rolling_average_demand, 2)
        else 0.0
    end as days_of_cover
from inventory_with_coverage
