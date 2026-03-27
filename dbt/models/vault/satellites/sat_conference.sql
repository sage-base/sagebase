{{- config(materialized="incremental") -}}

{%- set source_model = "stg_conferences" -%}
{%- set src_pk = "CONFERENCES_HK" -%}
{%- set src_hashdiff = "CONFERENCES_HASHDIFF" -%}
{%- set src_payload = ["name", "governing_body_id", "term", "election_id"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
