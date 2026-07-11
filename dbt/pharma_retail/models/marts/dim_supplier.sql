{{ config(tags=['phase4'], post_hook=phase4_supplier_hooks()) }}

with supplier_numbers as (
    select row_number() over (order by seq4()) as supplier_number
    from table(generator(rowcount => 30))
)

select
    'SUP' || lpad(supplier_number, 3, '0') as supplier_id,
    'Supplier ' || lpad(supplier_number, 3, '0') as supplier_name,
    case mod(supplier_number - 1, 5)
        when 0 then 'NATIONAL'
        when 1 then 'NSW & ACT'
        when 2 then 'VIC & TAS'
        when 3 then 'QLD'
        when 4 then 'SA, WA & NT'
    end as service_region,
    3 + mod(supplier_number, 5) as contracted_lead_time_days,
    'ops+' || lower('sup' || lpad(supplier_number, 3, '0')) || '@example.invalid'
        as contact_email,
    true as is_active
from supplier_numbers
