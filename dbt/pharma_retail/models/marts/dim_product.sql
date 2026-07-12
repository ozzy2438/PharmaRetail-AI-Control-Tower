{{ config(post_hook=phase4_access_grants()) }}

-- Standalone product dimension from the synthetic catalog. Prepared and
-- tested here, ready for the synthetic product-keyed operational fact
-- tables (inventory, stockout, promotion) planned in a later phase; not
-- joined to the UCI-based sales facts in this phase (see README.md).
select
    product_id,
    product_name,
    brand,
    category,
    pack_size,
    is_cold_chain,
    is_regulated
from {{ ref('stg_product') }}
