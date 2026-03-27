{{- config(materialized="incremental") -}}

{%- set source_model = "stg_speakers" -%}
{%- set src_pk = "SPEAKERS_HK" -%}
{%- set src_nk = "id" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.hub(src_pk=src_pk, src_nk=src_nk, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
