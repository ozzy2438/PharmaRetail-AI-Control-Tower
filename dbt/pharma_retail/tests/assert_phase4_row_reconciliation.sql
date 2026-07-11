with actual as (
    select 'operational_scope' as model_name, count(*) as row_count
    from {{ ref('int_operational_scope') }}
    union all
    select 'inventory_snapshot', count(*) from {{ ref('fct_inventory_snapshot') }}
    union all
    select 'supplier_delivery', count(*) from {{ ref('fct_supplier_delivery') }}
    union all
    select 'incident', count(*) from {{ ref('fct_incident') }}
),

expected as (
    select 'operational_scope' as model_name, 3000 as row_count
    union all select 'inventory_snapshot', 270000
    union all select 'supplier_delivery', 39000
    union all select 'incident', 3000
)

select actual.*
from actual
inner join expected using (model_name)
where actual.row_count != expected.row_count
