{{ config(tags=['phase4'], post_hook=phase4_scoped_hooks('ground_truth_root_cause')) }}

with stockout_days as (
    select
        *,
        case
            when lag(snapshot_date) over (
                partition by store_id, product_id order by snapshot_date
            ) = dateadd(day, -1, snapshot_date) then 0
            else 1
        end as new_event
    from {{ ref('fct_inventory_snapshot') }}
    where closing_stock = 0
        and expected_demand > 0
        and not is_discontinued
),

islands as (
    select
        *,
        sum(new_event) over (
            partition by store_id, product_id
            order by snapshot_date
            rows between unbounded preceding and current row
        ) as event_number
    from stockout_days
),

events as (
    select
        store_id,
        region,
        product_id,
        supplier_id,
        event_number,
        min(snapshot_date) as stockout_start_date,
        max(snapshot_date) as stockout_end_date,
        sum(expected_demand - sold_qty) as estimated_lost_units,
        max(ground_truth_root_cause) as ground_truth_root_cause
    from islands
    group by store_id, region, product_id, supplier_id, event_number
)

select
    md5(store_id || '|' || product_id || '|' || stockout_start_date) as stockout_event_id,
    store_id,
    region,
    product_id,
    supplier_id,
    stockout_start_date,
    stockout_end_date,
    datediff(day, stockout_start_date, stockout_end_date) + 1 as stockout_days,
    estimated_lost_units,
    ground_truth_root_cause
from events
