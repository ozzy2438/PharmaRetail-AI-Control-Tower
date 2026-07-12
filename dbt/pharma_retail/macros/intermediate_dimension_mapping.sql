{% macro map_uci_lines(source_model, source_alias) %}
    with stores as (
        select
            store_id,
            row_number() over (order by store_id) - 1 as store_index,
            count(*) over () as store_count
        from {{ ref('stg_store') }}
    ),

    products as (
        select
            product_id,
            row_number() over (order by product_id) - 1 as product_index,
            count(*) over () as product_count
        from {{ ref('stg_product') }}
    )

    select
        stores.store_id,
        products.product_id,
        {{ source_alias }}.*
    from {{ ref(source_model) }} as {{ source_alias }}
    cross join (select max(store_count) as store_count from stores) as store_counts
    cross join (select max(product_count) as product_count from products) as product_counts
    inner join stores
        on stores.store_index = mod(
            abs(hash(
                {{ source_alias }}.invoice_number,
                {{ source_alias }}.stock_code,
                'intermediate-map-v1'
            )),
            store_counts.store_count
        )
    inner join products
        on products.product_index = mod(
            abs(hash(
                {{ source_alias }}.invoice_number,
                {{ source_alias }}.stock_code,
                'intermediate-map-v1'
            )),
            product_counts.product_count
        )
{% endmacro %}
