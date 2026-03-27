{{- config(materialized="incremental") -}}

{%- set source_model = "stg_proposal_judges" -%}
{%- set src_pk = "LINK_PROPOSAL_JUDGE_HK" -%}
{%- set src_hashdiff = "PROPOSAL_JUDGES_HASHDIFF" -%}
{%- set src_payload = ["approve", "parliamentary_group_id", "source_type", "source_group_judge_id", "is_defection"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
