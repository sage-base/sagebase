{{- config(materialized="incremental") -}}

{%- set source_model = "stg_election_members" -%}
{%- set src_pk = "LINK_ELECTION_MEMBER_HK" -%}
{%- set src_hashdiff = "ELECTION_MEMBERS_HASHDIFF" -%}
{%- set src_payload = ["result", "votes", "rank"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
