{{ config(tags=['phase4']) }}

with dates as (
    select
        date_day as snapshot_date,
        row_number() over (order by date_day) as day_index
    from {{ ref('dim_date') }}
    where date_day between '2026-01-01'::date and '2026-03-31'::date
),

deliveries as (
    select
        store_id,
        product_id,
        actual_delivery_date,
        sum(delivered_qty) as received_qty
    from {{ ref('int_supplier_orders') }}
    group by store_id, product_id, actual_delivery_date
),

daily as (
    select
        scope.store_id,
        scope.region,
        scope.product_id,
        scope.supplier_id,
        scope.is_discontinued,
        scope.initial_stock,
        scope.scenario_number,
        scope.ground_truth_root_cause,
        dates.snapshot_date,
        dates.day_index,
        coalesce(deliveries.received_qty, 0) as received_qty,
        2 + mod(
            abs(hash(scope.store_id, scope.product_id, dates.snapshot_date, 'demand-v1')),
            7
        ) as base_demand
    from {{ ref('int_operational_scope') }} as scope
    cross join dates
    left join deliveries
        on scope.store_id = deliveries.store_id
        and scope.product_id = deliveries.product_id
        and dates.snapshot_date = deliveries.actual_delivery_date
)

select
    *,
    case
        when ground_truth_root_cause = 'PROMOTION_UPLIFT'
            and snapshot_date between '2026-01-20'::date and '2026-02-02'::date
            then ceil(base_demand * 1.75)
        when ground_truth_root_cause = 'UNEXPECTED_DEMAND_SPIKE'
            and snapshot_date between '2026-02-08'::date and '2026-02-14'::date
            then base_demand * 4
        else base_demand
    end as expected_demand,
    ground_truth_root_cause = 'COLD_CHAIN_INCIDENT'
        and snapshot_date = '2026-02-15'::date as force_writeoff,
    ground_truth_root_cause = 'PRODUCT_RECALL'
        and snapshot_date >= '2026-02-20'::date as recall_active,
    ground_truth_root_cause = 'INVENTORY_DISCREPANCY'
        and snapshot_date = '2026-02-10'::date as discrepancy_active
from daily
