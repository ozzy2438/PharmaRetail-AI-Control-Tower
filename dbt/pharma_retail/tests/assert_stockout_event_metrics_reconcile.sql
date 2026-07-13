with unit_prices as (
    select
        store_id,
        product_id,
        avg(average_unit_price) as reference_unit_price
    from {{ ref('mart_sales_daily') }}
    where units_sold > 0
        and average_unit_price > 0
    group by store_id, product_id
),

expected as (
    select
        events.stockout_event_id,
        sum(
            snapshots.expected_demand * coalesce(
                unit_prices.reference_unit_price,
                5 + mod(abs(hash(snapshots.store_id, snapshots.product_id, 'stockout-price-v1')), 12)
            )
        ) as estimated_lost_sales,
        max(case snapshots.ground_truth_root_cause
            when 'SUPPLIER_DELAY' then 'SUPPLIER_DELAY'
            when 'PROMOTION_UPLIFT' then 'PROMO_UPLIFT'
            when 'UNEXPECTED_DEMAND_SPIKE' then 'DEMAND_SPIKE'
            else 'REPLENISHMENT_GAP'
        end) as likely_root_cause
    from {{ ref('fct_stockout_event') }} as events
    inner join {{ ref('fct_inventory_snapshot') }} as snapshots
        on events.store_id = snapshots.store_id
        and events.product_id = snapshots.product_id
        and snapshots.snapshot_date between events.stockout_start_date and events.stockout_end_date
    left join unit_prices
        on snapshots.store_id = unit_prices.store_id
        and snapshots.product_id = unit_prices.product_id
    group by events.stockout_event_id
),

actual as (
    select
        stockout_event_id,
        stockout_days,
        estimated_lost_sales,
        severity,
        likely_root_cause
    from {{ ref('fct_stockout_event') }}
)

select actual.stockout_event_id
from actual
inner join expected
    on actual.stockout_event_id = expected.stockout_event_id
where abs(actual.estimated_lost_sales - expected.estimated_lost_sales) > 0.01
    or actual.likely_root_cause != expected.likely_root_cause
    or actual.severity != case
        when actual.stockout_days >= 5 or actual.estimated_lost_sales >= 500 then 'CRITICAL'
        when actual.stockout_days >= 3 or actual.estimated_lost_sales >= 250 then 'HIGH'
        else 'MEDIUM'
    end
