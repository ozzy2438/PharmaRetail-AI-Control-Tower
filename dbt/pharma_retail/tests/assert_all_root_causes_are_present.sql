with expected as (
    select column1 as root_cause
    from values
        ('SUPPLIER_DELAY'),
        ('PROMOTION_UPLIFT'),
        ('REPLENISHMENT_FAILURE'),
        ('UNEXPECTED_DEMAND_SPIKE'),
        ('INVENTORY_DISCREPANCY'),
        ('COLD_CHAIN_INCIDENT'),
        ('PRODUCT_RECALL')
),

actual as (
    select distinct ground_truth_root_cause as root_cause
    from {{ ref('fct_incident') }}
)

select * from expected
minus
select * from actual
