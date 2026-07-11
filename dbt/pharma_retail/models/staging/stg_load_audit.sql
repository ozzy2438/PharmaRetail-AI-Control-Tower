-- Typed, renamed passthrough of RAW.LOAD_AUDIT: surfaces the Phase 2 data
-- ingestion audit trail inside the dbt layer for pipeline-health monitoring.
with source as (
    select * from {{ source('raw', 'load_audit') }}
),

renamed as (
    select
        load_id,
        table_name,
        source_file,
        file_sha256,
        source_row_count,
        loaded_row_count,
        row_count_match,
        null_counts,
        duplicate_row_count,
        load_status,
        error_message,
        started_at,
        completed_at
    from source
)

select * from renamed
