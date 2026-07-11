{{ config(tags=['phase4']) }}

with order_numbers as (
    select seq4() as order_number
    from table(generator(rowcount => 13))
),

orders as (
    select
        scope.store_id,
        scope.region,
        scope.product_id,
        scope.supplier_id,
        scope.ground_truth_root_cause,
        order_numbers.order_number,
        dateadd(day, order_numbers.order_number * 7, '2026-01-03'::date) as expected_delivery_date,
        45 + mod(
            abs(hash(scope.store_id, scope.product_id, order_numbers.order_number, 'order-qty-v1')),
            31
        ) as ordered_qty
    from {{ ref('int_operational_scope') }} as scope
    cross join order_numbers
),

delivery_logic as (
    select
        *,
        dateadd(
            day,
            case
                when ground_truth_root_cause = 'SUPPLIER_DELAY'
                    then 2 + mod(order_number, 3)
                else 0
            end,
            expected_delivery_date
        ) as actual_delivery_date,
        case
            when ground_truth_root_cause = 'REPLENISHMENT_FAILURE'
                and order_number in (4, 5, 6) then 0
            when ground_truth_root_cause = 'SUPPLIER_DELAY'
                then greatest(0, ordered_qty - 5 - mod(order_number, 8))
            else ordered_qty
        end as delivered_qty
    from orders
)

select
    md5(store_id || '|' || product_id || '|' || order_number) as delivery_id,
    store_id,
    region,
    product_id,
    supplier_id,
    dateadd(
        day,
        -(3 + mod(abs(hash(supplier_id, 'lead-time-v1')), 5)),
        expected_delivery_date
    ) as order_date,
    expected_delivery_date,
    actual_delivery_date,
    ordered_qty,
    delivered_qty,
    datediff(
        day,
        dateadd(
            day,
            -(3 + mod(abs(hash(supplier_id, 'lead-time-v1')), 5)),
            expected_delivery_date
        ),
        actual_delivery_date
    ) as lead_time_days,
    actual_delivery_date > expected_delivery_date as late_delivery_flag,
    iff(actual_delivery_date <= expected_delivery_date and delivered_qty >= ordered_qty, 1, 0)
        as otif,
    ground_truth_root_cause
from delivery_logic
