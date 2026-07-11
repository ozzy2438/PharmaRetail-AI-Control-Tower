{{ config(tags=['phase4'], post_hook=phase4_scoped_hooks('ground_truth_root_cause')) }}

with promoted as (
    select *
    from {{ ref('int_operational_scope') }}
    where ground_truth_root_cause = 'PROMOTION_UPLIFT'
)

select
    md5(store_id || '|' || product_id || '|PROMO-2026-01') as promotion_id,
    product_id,
    store_id,
    region,
    '2026-01-20'::date as start_date,
    '2026-02-02'::date as end_date,
    10 + mod(abs(hash(store_id, product_id, 'discount-v1')), 21) as discount_pct,
    0.35::number(5, 4) as expected_uplift,
    0.75::number(5, 4) as actual_uplift,
    ground_truth_root_cause
from promoted
