with staging_count as (
    select count(*) as row_count from {{ ref('stg_product') }}
),

source_count as (
    select count(*) as row_count from {{ source('raw', 'product_seed') }}
)

select
    staging_count.row_count as staging_row_count,
    source_count.row_count as source_row_count
from staging_count
cross join source_count
where staging_count.row_count != source_count.row_count
