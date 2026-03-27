{{- config(materialized="incremental") -}}

{%- set source_model = "stg_conversations" -%}
{%- set src_pk = "LINK_CONVERSATION_SPEAKER_HK" -%}
{%- set src_fk = ["CONVERSATIONS_HK", "SPEAKERS_HK"] -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.link(src_pk=src_pk, src_fk=src_fk, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
