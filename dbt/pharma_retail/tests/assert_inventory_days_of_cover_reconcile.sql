with expected as (
    select
        store_id,
        product_id,
        snapshot_date,
        case
            when avg(expected_demand) over (
                partition by store_id, product_id
                order by snapshot_date
                rows between 6 preceding and current row
            ) > 0 then round(
                closing_stock / avg(expected_demand) over (
                    partition by store_id, product_id
                    order by snapshot_date
                    rows between 6 preceding and current row
                ),
                2
            )
            else 0.0
        end as days_of_cover
    from {{ ref('fct_inventory_snapshot') }}
)

select
    expected.store_id,
    expected.product_id,
    expected.snapshot_date
from expected
inner join {{ ref('fct_inventory_snapshot') }} as actual
    on expected.store_id = actual.store_id
    and expected.product_id = actual.product_id
    and expected.snapshot_date = actual.snapshot_date
where abs(expected.days_of_cover - actual.days_of_cover) > 0.01
