-- Generated from database on 2026-02-15 01:55:09
-- meetings seed data

INSERT INTO meetings (conference_id, date, url, gcs_pdf_uri, gcs_text_uri) VALUES
((SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '産業交通水道委員会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), '2025-03-25', 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6077&schedule_id=1&is_search=false&view_years=2025', NULL, 'gs://sagebase-scraped-minutes/scraped/2025/03/25/6077_1.txt'),
((SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), '2025-03-24', 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6076&schedule_id=1&is_search=false&view_years=2025', NULL, 'gs://sagebase-scraped-minutes/scraped/2025/03/24/6076_1.txt')
;
