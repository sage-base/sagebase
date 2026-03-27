{{- config(materialized="incremental") -}}

{%- set source_model = "stg_parliamentary_group_memberships" -%}
{%- set src_pk = "LINK_PG_MEMBERSHIP_HK" -%}
{%- set src_fk = ["PARLIAMENTARY_GROUPS_HK", "POLITICIANS_HK"] -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.link(src_pk=src_pk, src_fk=src_fk, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
