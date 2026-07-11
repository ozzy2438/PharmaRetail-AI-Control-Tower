-- Source-to-staging row-count reconciliation for returns. See
-- assert_stg_uci_sales_matches_source_count.sql for the same check on sales.
with staging_count as (
    select count(*) as cnt from {{ ref('stg_uci_returns') }}
),

source_count as (
    select count(*) as cnt from {{ source('raw', 'uci_returns') }}
)

select
    staging_count.cnt as staging_row_count,
    source_count.cnt as source_row_count
from staging_count, source_count
where staging_count.cnt != source_count.cnt
