-- Typed, renamed passthrough of RAW.DIM_PRODUCT_SEED. Flags are cast to
-- boolean for cleaner downstream usage; they remain illustrative scenario
-- flags, not validated regulatory/clinical classifications (see
-- contracts/dim_product.yml).
with source as (
    select * from {{ source('raw', 'dim_product_seed') }}
),

renamed as (
    select
        product_id,
        product_name,
        brand,
        category,
        pack_size,
        cold_chain_flag::boolean as is_cold_chain,
        regulated_product_flag::boolean as is_regulated,
        _load_id,
        _loaded_at
    from source
)

select * from renamed
