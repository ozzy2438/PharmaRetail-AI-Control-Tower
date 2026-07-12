{{ config(tags=['phase4']) }}

-- Stable 100-store x 30-product operating scope. Every value is derived from
-- committed dimensions plus the versioned seed below; no random() call or
-- wall-clock value is used, so regeneration is byte-for-byte deterministic.
with stores as (
    select store_id, region
    from {{ ref('dim_store') }}
),

ranked_products as (
    select
        product_id,
        is_cold_chain,
        row_number() over (order by product_id) as product_rank
    from {{ ref('dim_product') }}
),

products as (
    select *
    from ranked_products
    where product_rank <= 30
),

scoped as (
    select
        stores.store_id,
        stores.region,
        products.product_id,
        products.is_cold_chain,
        products.product_rank,
        'SUP' || lpad(mod(products.product_rank - 1, 30) + 1, 3, '0') as supplier_id,
        mod(abs(hash(stores.store_id, products.product_id, 'phase4-seed-v1')), 7) + 1
            as scenario_number,
        mod(abs(hash(products.product_id, 'discontinued-seed-v1')), 29) = 0
            as is_discontinued,
        12 + mod(abs(hash(stores.store_id, products.product_id, 'opening-seed-v1')), 20)
            as initial_stock
    from stores
    cross join products
)

select
    store_id,
    region,
    product_id,
    supplier_id,
    is_cold_chain,
    is_discontinued,
    initial_stock,
    scenario_number,
    case scenario_number
        when 1 then 'SUPPLIER_DELAY'
        when 2 then 'PROMOTION_UPLIFT'
        when 3 then 'REPLENISHMENT_FAILURE'
        when 4 then 'UNEXPECTED_DEMAND_SPIKE'
        when 5 then 'INVENTORY_DISCREPANCY'
        when 6 then 'COLD_CHAIN_INCIDENT'
        when 7 then 'PRODUCT_RECALL'
    end as ground_truth_root_cause
from scoped
