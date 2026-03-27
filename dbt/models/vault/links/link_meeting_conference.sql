{{- config(materialized="incremental") -}}

{%- set source_model = "stg_meetings" -%}
{%- set src_pk = "LINK_MEETING_CONFERENCE_HK" -%}
{%- set src_fk = ["MEETINGS_HK", "CONFERENCES_HK"] -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.link(src_pk=src_pk, src_fk=src_fk, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
