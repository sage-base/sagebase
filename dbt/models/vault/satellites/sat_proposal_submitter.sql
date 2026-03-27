{{- config(materialized="incremental") -}}

{%- set source_model = "stg_proposal_submitters" -%}
{%- set src_pk = "LINK_PROPOSAL_SUBMITTER_HK" -%}
{%- set src_hashdiff = "PROPOSAL_SUBMITTERS_HASHDIFF" -%}
{%- set src_payload = ["submitter_type", "parliamentary_group_id", "conference_id", "raw_name", "is_representative", "display_order"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
