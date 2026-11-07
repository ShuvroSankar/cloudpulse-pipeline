{# DuckDB and BigQuery disagree on a few functions; these macros hide the difference. #}

{% macro p95_over(column, partition_by) -%}
  {{ return(adapter.dispatch('p95_over', 'cloudpulse')(column, partition_by)) }}
{%- endmacro %}

{% macro default__p95_over(column, partition_by) -%}
  quantile_cont({{ column }}, 0.95) over (partition by {{ partition_by }})
{%- endmacro %}

{% macro bigquery__p95_over(column, partition_by) -%}
  percentile_cont({{ column }}, 0.95) over (partition by {{ partition_by }})
{%- endmacro %}


{% macro safe_div(numerator, denominator) -%}
  {{ return(adapter.dispatch('safe_div', 'cloudpulse')(numerator, denominator)) }}
{%- endmacro %}

{% macro default__safe_div(numerator, denominator) -%}
  ({{ numerator }}) / nullif({{ denominator }}, 0)
{%- endmacro %}

{% macro bigquery__safe_div(numerator, denominator) -%}
  safe_divide({{ numerator }}, {{ denominator }})
{%- endmacro %}


{% macro type_double() -%}
  {{ return(adapter.dispatch('type_double', 'cloudpulse')()) }}
{%- endmacro %}

{% macro default__type_double() -%}double{%- endmacro %}

{% macro bigquery__type_double() -%}float64{%- endmacro %}
