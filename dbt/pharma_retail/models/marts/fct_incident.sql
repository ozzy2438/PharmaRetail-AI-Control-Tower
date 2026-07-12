{{ config(tags=['phase4'], post_hook=phase4_scoped_hooks('ground_truth_root_cause')) }}

with incidents as (
    select
        *,
        dateadd(day, scenario_number * 5, '2026-02-01'::date) as incident_date
    from {{ ref('int_operational_scope') }}
)

select
    md5(store_id || '|' || product_id || '|' || ground_truth_root_cause) as incident_id,
    lower(ground_truth_root_cause) as incident_type,
    store_id,
    region,
    product_id,
    case
        when scenario_number in (6, 7) then 'CRITICAL'
        when scenario_number in (1, 3, 5) then 'HIGH'
        else 'MEDIUM'
    end as severity,
    dateadd(
        hour,
        8 + mod(abs(hash(store_id, product_id, 'detected-hour-v1')), 10),
        incident_date::timestamp_ntz
    ) as detected_at,
    case when scenario_number in (2, 4) then 'MONITORING' else 'OPEN' end as status,
    scenario_number in (1, 3, 5, 6, 7) as escalation_required,
    ground_truth_root_cause
from incidents
