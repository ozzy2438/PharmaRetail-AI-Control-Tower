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
        -- See stg_uci_sales.sql: NUMBER, not FLOAT, so SUM(line_return_value)
        -- reconciles exactly between staging and the grouped mart totals.
        cast(quantity * price as number(18, 4)) as line_return_value,
        customer_id,
        country,
        is_customer_identified,
        _load_id,
        _loaded_at
    from source
)

select * from renamed
