{{- config(materialized="incremental") -}}

{%- set source_model = "stg_parliamentary_group_memberships" -%}
{%- set src_pk = "LINK_PG_MEMBERSHIP_HK" -%}
{%- set src_hashdiff = "PARLIAMENTARY_GROUP_MEMBERSHIPS_HASHDIFF" -%}
{%- set src_payload = ["start_date", "end_date", "role", "is_manually_verified"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
