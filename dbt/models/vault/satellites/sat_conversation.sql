{{- config(materialized="incremental") -}}

{%- set source_model = "stg_conversations" -%}
{%- set src_pk = "CONVERSATIONS_HK" -%}
{%- set src_hashdiff = "CONVERSATIONS_HASHDIFF" -%}
{%- set src_payload = ["minutes_id", "speaker_id", "speaker_name", "comment", "sequence_number", "chapter_number", "sub_chapter_number", "is_manually_verified"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
