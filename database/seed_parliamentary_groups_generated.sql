-- Generated from database on 2026-03-10 15:48:04
-- parliamentary_groups seed data

INSERT INTO parliamentary_groups (name, governing_body_id, url, description, is_active, chamber) VALUES
ON CONFLICT (name, governing_body_id, chamber) DO UPDATE SET url = EXCLUDED.url, description = EXCLUDED.description, is_active = EXCLUDED.is_active;
