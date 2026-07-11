-- Typed, renamed passthrough of RAW.DIM_STORE_SEED.
with source as (
    select * from {{ source('raw', 'dim_store_seed') }}
),

renamed as (
    select
        store_id,
        store_name,
        state,
        postcode,
        cast(latitude as float) as latitude,
        cast(longitude as float) as longitude,
        region,
        _load_id,
        _loaded_at
    from source
)

select * from renamed
