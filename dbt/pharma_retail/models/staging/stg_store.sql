with source as (
    select * from {{ source('raw', 'store_seed') }}
),

typed as (
    select
        cast(store_id as varchar) as store_id,
        cast(store_name as varchar) as store_name,
        cast(state as varchar) as state,
        cast(postcode as varchar) as postcode,
        cast(latitude as float) as latitude,
        cast(longitude as float) as longitude,
        cast(region as varchar) as region,
        cast(postcode_available_flag as boolean) as postcode_available_flag,
        cast(_source_file as varchar) as _source_file,
        cast(_loaded_at as timestamp_ntz) as _loaded_at
    from source
)

select * from typed
