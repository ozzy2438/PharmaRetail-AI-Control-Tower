with eligible_days as (
    select store_id, product_id, snapshot_date
    from {{ ref('fct_inventory_snapshot') }}
    where closing_stock = 0
        and expected_demand > 0
        and not is_discontinued
),

covered_days as (
    select
        events.store_id,
        events.product_id,
        dates.date_day as snapshot_date
    from {{ ref('fct_stockout_event') }} as events
    inner join {{ ref('dim_date') }} as dates
        on dates.date_day between events.stockout_start_date and events.stockout_end_date
)

select * from eligible_days
minus
select * from covered_days
