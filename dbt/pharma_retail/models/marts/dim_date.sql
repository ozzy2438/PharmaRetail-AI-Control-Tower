-- Standalone calendar dimension, generated (not sourced from RAW) so it can
-- join to any date-grained fact table, now or in a later phase. Spans a
-- fixed range wide enough to cover the UCI data (2009-2011) plus headroom
-- for future synthetic operational facts.
with spine as (
    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('2009-01-01' as date)",
            end_date="cast('2031-01-01' as date)"
        )
    }}
),

enriched as (
    select
        date_day,
        to_char(date_day, 'YYYYMMDD')::number as date_key,
        year(date_day) as year,
        quarter(date_day) as quarter,
        month(date_day) as month,
        monthname(date_day) as month_name,
        day(date_day) as day_of_month,
        dayofweek(date_day) as day_of_week,
        dayname(date_day) as day_name,
        case when dayofweek(date_day) in (0, 6) then true else false end as is_weekend
    from spine
)

select * from enriched
