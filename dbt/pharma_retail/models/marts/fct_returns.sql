-- Daily returns fact at (date_day, country) grain, mirroring fct_sales_daily.
with returns as (
    select * from {{ ref('int_returns_daily') }}
),

dates as (
    select date_day from {{ ref('dim_date') }}
),

joined as (
    select
        dates.date_day,
        returns.country,
        returns.return_invoice_count,
        returns.total_quantity_returned,
        returns.total_return_value
    from returns
    inner join dates
        on returns.invoice_date_day = dates.date_day
)

select * from joined
