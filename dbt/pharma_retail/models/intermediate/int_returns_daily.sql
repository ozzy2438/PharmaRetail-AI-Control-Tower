{{ config(tags=['intermediate_foundation']) }}

with mapped_returns as (
    {{ map_uci_lines('stg_uci_returns', 'returns') }}
),

aggregated as (
    select
        store_id,
        product_id,
        invoice_date_day as date,
        sum(abs(quantity)) as returned_units,
        sum(abs(line_return_value)) as return_value,
        count(distinct invoice_number) as return_transaction_count,
        -- Compatibility aliases retained for the existing date/country MARTS.
        invoice_date_day,
        min(country) as country,
        count(distinct invoice_number) as return_invoice_count,
        sum(abs(quantity)) as total_quantity_returned,
        sum(abs(line_return_value)) as total_return_value
    from mapped_returns
    group by store_id, product_id, invoice_date_day
)

select * from aggregated
