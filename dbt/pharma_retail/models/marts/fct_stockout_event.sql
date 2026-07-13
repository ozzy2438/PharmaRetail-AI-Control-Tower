{{ config(tags=['phase4'], post_hook=phase4_scoped_hooks('ground_truth_root_cause')) }}

with unit_prices as (
    -- The historical MARTS signal supplies a deterministic store-product
    -- reference price. A deterministic fallback covers pairs without sales.
    select
        store_id,
        product_id,
        avg(average_unit_price) as reference_unit_price
    from {{ ref('mart_sales_daily') }}
    where units_sold > 0
        and average_unit_price > 0
    group by store_id, product_id
),

stockout_days as (
    select
        inventory.*,
        coalesce(
            unit_prices.reference_unit_price,
            5 + mod(abs(hash(inventory.store_id, inventory.product_id, 'stockout-price-v1')), 12)
        ) as reference_unit_price,
        case inventory.ground_truth_root_cause
            when 'SUPPLIER_DELAY' then 'SUPPLIER_DELAY'
            when 'PROMOTION_UPLIFT' then 'PROMO_UPLIFT'
            when 'UNEXPECTED_DEMAND_SPIKE' then 'DEMAND_SPIKE'
            else 'REPLENISHMENT_GAP'
        end as likely_root_cause,
        case
            when lag(inventory.snapshot_date) over (
                partition by inventory.store_id, inventory.product_id order by inventory.snapshot_date
            ) = dateadd(day, -1, snapshot_date) then 0
            else 1
        end as new_event
    from {{ ref('fct_inventory_snapshot') }}
        as inventory
    left join unit_prices
        on inventory.store_id = unit_prices.store_id
        and inventory.product_id = unit_prices.product_id
    where inventory.closing_stock = 0
        and inventory.expected_demand > 0
        and not inventory.is_discontinued
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
        sum(expected_demand * reference_unit_price) as estimated_lost_sales,
        max(ground_truth_root_cause) as ground_truth_root_cause,
        max(likely_root_cause) as likely_root_cause
    from islands
    group by store_id, region, product_id, supplier_id, event_number
),

scored_events as (
    select
        *,
        datediff(day, stockout_start_date, stockout_end_date) + 1 as stockout_days,
        case
            when datediff(day, stockout_start_date, stockout_end_date) + 1 >= 5
                or estimated_lost_sales >= 500 then 'CRITICAL'
            when datediff(day, stockout_start_date, stockout_end_date) + 1 >= 3
                or estimated_lost_sales >= 250 then 'HIGH'
            else 'MEDIUM'
        end as severity
    from events
)

select
    md5(store_id || '|' || product_id || '|' || stockout_start_date) as stockout_event_id,
    store_id,
    region,
    product_id,
    supplier_id,
    stockout_start_date,
    stockout_end_date,
    stockout_days,
    estimated_lost_units,
    estimated_lost_sales,
    severity,
    ground_truth_root_cause,
    likely_root_cause
from scored_events
