{{- config(materialized="incremental") -}}

{%- set source_model = "stg_proposals" -%}
{%- set src_pk = "PROPOSALS_HK" -%}
{%- set src_hashdiff = "PROPOSALS_HASHDIFF" -%}
{%- set src_payload = ["title", "detail_url", "status_url", "meeting_id", "votes_url", "conference_id", "proposal_category", "proposal_type", "governing_body_id", "session_number", "proposal_number", "external_id", "deliberation_status", "deliberation_result", "submitted_date", "voted_date"] -%}
{%- set src_eff = "load_date" -%}
{%- set src_ldts = "load_date" -%}
{%- set src_source = "record_source" -%}

{{ automate_dv.sat(src_pk=src_pk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model) }}
