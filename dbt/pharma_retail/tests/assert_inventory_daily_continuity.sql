with snapshots as (
    select
        *,
        lag(closing_stock) over (
            partition by store_id, product_id order by snapshot_date
        ) as prior_closing_stock
    from {{ ref('fct_inventory_snapshot') }}
)

select *
from snapshots
where prior_closing_stock is not null
    and opening_stock != prior_closing_stock
