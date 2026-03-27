{{- config(materialized="incremental") -}}

{%- set source_model = "stg_minutes" -%}
{%- set src_pk = "LINK_MEETING_MINUTES_HK" -%}
{%- set src_fk = ["MEETINGS_HK", "MINUTES_HK"] -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.link(src_pk=src_pk, src_fk=src_fk, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
