with model_totals as (
    select
        coalesce(sum(returned_units), 0) as returned_units,
        coalesce(sum(return_value), 0) as return_value
    from {{ ref('int_returns_daily') }}
),

staging_totals as (
    select
        coalesce(sum(abs(quantity)), 0) as returned_units,
        coalesce(sum(abs(line_return_value)), 0) as return_value
    from {{ ref('stg_uci_returns') }}
)

select *
from model_totals
cross join staging_totals
where model_totals.returned_units != staging_totals.returned_units
    or abs(model_totals.return_value - staging_totals.return_value) > 0.01
