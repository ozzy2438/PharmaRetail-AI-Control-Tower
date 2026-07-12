with source as (
    select * from {{ source('raw', 'product_seed') }}
),

typed as (
    select
        cast(product_id as varchar) as product_id,
        cast(product_name as varchar) as product_name,
        cast(brand as varchar) as brand,
        cast(category as varchar) as category,
        cast(pack_size as varchar) as pack_size,
        cast(cold_chain_flag as boolean) as is_cold_chain,
        cast(regulated_product_flag as boolean) as is_regulated,
        cast(_source_file as varchar) as _source_file,
        cast(_loaded_at as timestamp_ntz) as _loaded_at
    from source
)

select * from typed
