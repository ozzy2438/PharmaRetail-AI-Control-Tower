-- Typed, renamed passthrough of RAW.UCI_SALES. One row per deduplicated,
-- valid-price, non-return UCI Online Retail invoice line.
with source as (
    select * from {{ source('raw', 'uci_sales') }}
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
        -- RAW.PRICE is FLOAT (Phase 2, not changed here). Rounding each
        -- line to 4 decimal places and summing as NUMBER (exact decimal
        -- arithmetic) instead of FLOAT keeps SUM(line_revenue) associative,
        -- so a row-by-row total and a grouped-then-summed total agree
        -- exactly instead of drifting by floating-point summation noise.
        cast(quantity * price as number(18, 4)) as line_revenue,
        customer_id,
        country,
        is_customer_identified,
        _load_id,
        _loaded_at
    from source
)

select * from renamed
