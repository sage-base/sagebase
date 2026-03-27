{{- config(materialized="incremental") -}}

{%- set source_model = "stg_government_officials" -%}
{%- set src_pk = "GOVERNMENT_OFFICIALS_HK" -%}
{%- set src_hashdiff = "GOVERNMENT_OFFICIALS_HASHDIFF" -%}
{%- set src_payload = ["name"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
