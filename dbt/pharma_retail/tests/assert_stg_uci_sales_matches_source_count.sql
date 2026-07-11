-- Source-to-staging row-count reconciliation. stg_uci_sales is a 1:1
-- passthrough of RAW.UCI_SALES; a mismatch means rows were silently
-- dropped or duplicated. Fails (returns a row) only on mismatch.
with staging_count as (
    select count(*) as cnt from {{ ref('stg_uci_sales') }}
),

source_count as (
    select count(*) as cnt from {{ source('raw', 'uci_sales') }}
)

select
    staging_count.cnt as staging_row_count,
    source_count.cnt as source_row_count
from staging_count, source_count
where staging_count.cnt != source_count.cnt
