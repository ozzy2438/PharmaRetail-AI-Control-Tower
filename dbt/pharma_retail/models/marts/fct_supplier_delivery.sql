{{ config(tags=['phase4'], post_hook=phase4_scoped_hooks('ground_truth_root_cause')) }}

select
    delivery_id,
    store_id,
    region,
    product_id,
    supplier_id,
    order_date,
    expected_delivery_date,
    actual_delivery_date,
    ordered_qty,
    delivered_qty,
    lead_time_days,
    late_delivery_flag,
    otif,
    ground_truth_root_cause
from {{ ref('int_supplier_orders') }}
