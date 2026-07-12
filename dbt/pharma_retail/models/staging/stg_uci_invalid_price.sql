with source as (
    select * from {{ source('raw', 'uci_invalid_price') }}
),

typed as (
    select
        cast(invoice as varchar) as invoice_number,
        cast(stock_code as varchar) as stock_code,
        cast(description as varchar) as product_description,
        cast(quantity as number(38, 0)) as quantity,
        cast(invoice_date as timestamp_ntz) as invoice_date,
        cast(invoice_date as date) as invoice_date_day,
        cast(price as float) as unit_price,
        cast(customer_id as varchar) as customer_id,
        cast(country as varchar) as country,
        cast(is_customer_identified as boolean) as is_customer_identified,
        cast(quarantine_reason as varchar) as quarantine_reason,
        cast(_source_file as varchar) as _source_file,
        cast(_loaded_at as timestamp_ntz) as _loaded_at
    from source
)

select * from typed
