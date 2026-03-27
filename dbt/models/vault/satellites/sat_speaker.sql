{{- config(materialized="incremental") -}}

{%- set source_model = "stg_speakers" -%}
{%- set src_pk = "SPEAKERS_HK" -%}
{%- set src_hashdiff = "SPEAKERS_HASHDIFF" -%}
{%- set src_payload = ["name", "type", "political_party_name", "position", "is_politician", "politician_id", "matching_confidence", "matching_reason", "is_manually_verified", "name_yomi", "government_official_id"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
