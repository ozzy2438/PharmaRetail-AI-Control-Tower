{% macro phase4_governance_enabled() %}
    {{ return(var('phase4_governance_enabled', 'false') | string | lower == 'true') }}
{% endmacro %}

{% macro phase4_access_grants() %}
    {# MARTS is a managed-access schema. Only its owner (ADMIN), not the dbt
       object owner, can grant consumer access. The post-build admin step runs
       infra/snowflake/phase4_model_grants.sql instead. #}
    {{ return([]) }}
{% endmacro %}

{% macro phase4_scoped_hooks(mask_column=none) %}
    {% if not phase4_governance_enabled() %}
        {{ return([]) }}
    {% endif %}
    {% set relation = '{{ this }}' %}
    {% set hooks = phase4_access_grants() %}
    {% do hooks.append(
        'alter table ' ~ relation
        ~ ' add row access policy '
        ~ 'PHARMARETAIL_AI_CONTROL_TOWER.GOVERNANCE.OPERATIONAL_STORE_REGION_POLICY '
        ~ 'on (store_id, region)'
    ) %}
    {% if mask_column is not none %}
        {% do hooks.append(
            'alter table ' ~ relation ~ ' modify column ' ~ mask_column
            ~ ' set masking policy '
            ~ 'PHARMARETAIL_AI_CONTROL_TOWER.GOVERNANCE.SENSITIVE_TEXT_MASK'
        ) %}
    {% endif %}
    {{ return(hooks) }}
{% endmacro %}

{% macro phase4_supplier_hooks() %}
    {% if not phase4_governance_enabled() %}
        {{ return([]) }}
    {% endif %}
    {% set relation = '{{ this }}' %}
    {% set hooks = phase4_access_grants() %}
    {% do hooks.append(
        'alter table ' ~ relation ~ ' modify column contact_email set masking policy '
        ~ 'PHARMARETAIL_AI_CONTROL_TOWER.GOVERNANCE.SENSITIVE_TEXT_MASK'
    ) %}
    {{ return(hooks) }}
{% endmacro %}
