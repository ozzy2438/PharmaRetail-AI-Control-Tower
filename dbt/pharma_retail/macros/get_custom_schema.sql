{#
  Use the model's custom schema exactly as configured (STAGING, INTERMEDIATE,
  MARTS), ignoring dbt's default "<profile_schema>_<custom_schema>"
  concatenation. This targets the real foundation schemas from
  infra/snowflake/03_database_schemas.sql instead of inventing new ones.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
