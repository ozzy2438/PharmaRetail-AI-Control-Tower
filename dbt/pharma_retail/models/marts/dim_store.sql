-- Standalone store dimension from the synthetic Australian seed. Prepared
-- and tested here, ready for the synthetic store-keyed operational fact
-- tables (inventory, stockout, promotion) planned in a later phase; not
-- joined to the UCI-based sales facts in this phase (see README.md).
select
    store_id,
    store_name,
    state,
    postcode,
    latitude,
    longitude,
    region
from {{ ref('stg_store') }}
