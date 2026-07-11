-- Typed, renamed passthrough of RAW.UCI_RETURNS. One row per deduplicated,
-- valid-price UCI Online Retail invoice line classified as a return.
with source as (
    select * from {{ source('raw', 'uci_returns') }}
),

renamed as (
    select
        invoice as invoice_number,
        stock_code,
        description as product_description,
        quantity,
        invoice_date,
        cast(invoice_date as date) as invoice_date_day,
        price as unit_price,
        quantity * price as line_return_value,
        customer_id,
        country,
        is_customer_identified,
        _load_id,
        _loaded_at
    from source
)

select * from renamed
