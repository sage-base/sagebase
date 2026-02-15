"""SEEDファイル生成モジュール"""

from datetime import datetime
from typing import Any, TextIO

from sqlalchemy import text

from src.infrastructure.config.database import get_db_engine


class SeedGenerator:
    """データベースからSEEDファイルを生成するクラス"""

    def __init__(self):
        self.engine = get_db_engine()

    def generate_governing_bodies_seed(self, output: TextIO | None = None) -> str:
        """governing_bodiesテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT name, type, organization_code, organization_type
                    FROM governing_bodies
                    ORDER BY
                        CASE type
                            WHEN '国' THEN 1
                            WHEN '都道府県' THEN 2
                            WHEN '市町村' THEN 3
                            ELSE 4
                        END,
                        name
                """)
            )
            columns = result.keys()
            bodies = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- governing_bodies seed data",
            "",
            (
                "INSERT INTO governing_bodies "
                "(name, type, organization_code, organization_type) VALUES"
            ),
        ]

        # タイプごとにグループ化
        grouped_data: dict[str, list[dict[str, Any]]] = {}
        for body in bodies:
            body_type = body["type"]
            if body_type not in grouped_data:
                grouped_data[body_type] = []
            grouped_data[body_type].append(body)

        first_group = True
        for type_name, bodies_list in grouped_data.items():
            if not first_group:
                lines.append("")
            lines.append(f"-- {type_name}")

            for i, body in enumerate(bodies_list):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                name = body["name"].replace("'", "''")
                type_val = body["type"].replace("'", "''")

                # organization_codeとorganization_typeの処理
                org_code = (
                    f"'{body['organization_code']}'"
                    if body.get("organization_code")
                    else "NULL"
                )
                org_type = (
                    f"'{body['organization_type'].replace(chr(39), chr(39) * 2)}'"
                    if body.get("organization_type")
                    else "NULL"
                )

                # 最後の要素かどうかチェック（全体での最後）
                is_last = (
                    type_name == list(grouped_data.keys())[-1]
                    and i == len(bodies_list) - 1
                )

                comma = "" if is_last else ","
                lines.append(f"('{name}', '{type_val}', {org_code}, {org_type}){comma}")

            first_group = False

        lines.append("ON CONFLICT (name, type) DO NOTHING;")

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_conferences_seed(self, output: TextIO | None = None) -> str:
        """conferencesテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        c.name,
                        c.governing_body_id,
                        gb.name as governing_body_name,
                        gb.type as governing_body_type
                    FROM conferences c
                    LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
                    ORDER BY
                        CASE
                            WHEN gb.type IS NULL THEN 0
                            WHEN gb.type = '国' THEN 1
                            WHEN gb.type = '都道府県' THEN 2
                            WHEN gb.type = '市町村' THEN 3
                            ELSE 4
                        END,
                        COALESCE(gb.name, ''),
                        c.name
                """)
            )
            columns = result.keys()
            conferences = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- conferences seed data",
            "",
            ("INSERT INTO conferences (name, governing_body_id) VALUES"),
        ]

        # 開催主体ごとにグループ化
        grouped_data: dict[str, dict[str, Any]] = {}
        for conf in conferences:
            if conf["governing_body_id"] is None:
                key = "_NO_GOVERNING_BODY_"
                grouped_data[key] = {
                    "body_name": None,
                    "body_type": None,
                    "body_id": None,
                    "conferences": [],
                }
            else:
                key = f"{conf['governing_body_type']}_{conf['governing_body_name']}"
                if key not in grouped_data:
                    grouped_data[key] = {
                        "body_name": conf["governing_body_name"],
                        "body_type": conf["governing_body_type"],
                        "body_id": conf["governing_body_id"],
                        "conferences": [],
                    }
            grouped_data[key]["conferences"].append(conf)

        first_group = True
        group_keys: list[str] = list(grouped_data.keys())
        for group_idx, (_key, data) in enumerate(grouped_data.items()):
            body_name = data["body_name"]
            body_type = data["body_type"]
            confs = data["conferences"]

            if not first_group:
                lines.append("")
            if body_name:
                lines.append(f"-- {body_name} ({body_type})")
            else:
                lines.append("-- 開催主体未設定")

            for i, conf in enumerate(confs):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                conf_name = conf["name"].replace("'", "''")

                # 最後の要素かどうかチェック（全体での最後）
                is_last = group_idx == len(group_keys) - 1 and i == len(confs) - 1

                comma = "" if is_last else ","

                # governing_body_idの処理
                if body_name:
                    body_name_escaped = body_name.replace("'", "''")
                    body_type_escaped = body_type.replace("'", "''")
                    governing_body_part = (
                        f"(SELECT id FROM governing_bodies WHERE name = "
                        f"'{body_name_escaped}' AND type = '{body_type_escaped}')"
                    )
                else:
                    governing_body_part = "NULL"

                lines.append(f"('{conf_name}', {governing_body_part}){comma}")

            first_group = False

        lines.append("ON CONFLICT (name, governing_body_id, term) DO NOTHING;")

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_political_parties_seed(self, output: TextIO | None = None) -> str:
        """political_partiesテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT name, members_list_url
                    FROM political_parties
                    ORDER BY name
                """)
            )
            columns = result.keys()
            parties = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- political_parties seed data",
            "",
            "INSERT INTO political_parties (name, members_list_url) VALUES",
        ]

        for i, party in enumerate(parties):
            # SQLインジェクション対策のため、シングルクォートをエスケープ
            name = party["name"].replace("'", "''")
            members_url = (
                f"'{party['members_list_url'].replace(chr(39), chr(39) * 2)}'"
                if party.get("members_list_url")
                else "NULL"
            )
            comma = "" if i == len(parties) - 1 else ","
            lines.append(f"('{name}', {members_url}){comma}")

        lines.append("ON CONFLICT (name) DO NOTHING;")

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_parliamentary_groups_seed(self, output: TextIO | None = None) -> str:
        """parliamentary_groupsテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        pg.name,
                        pg.url,
                        pg.description,
                        pg.is_active,
                        pg.political_party_id,
                        gb.name as governing_body_name,
                        gb.type as governing_body_type,
                        pp.name as party_name
                    FROM parliamentary_groups pg
                    JOIN governing_bodies gb ON pg.governing_body_id = gb.id
                    LEFT JOIN political_parties pp ON pg.political_party_id = pp.id
                    ORDER BY gb.name, pg.name
                """)
            )
            columns = result.keys()
            groups = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- parliamentary_groups seed data",
            "",
            (
                "INSERT INTO parliamentary_groups "
                "(name, governing_body_id, url, description, is_active, "
                "political_party_id) VALUES"
            ),
        ]

        # 開催主体ごとにグループ化
        grouped_data: dict[str, dict[str, Any]] = {}
        for group in groups:
            key = f"{group['governing_body_name']} ({group['governing_body_type']})"
            if key not in grouped_data:
                grouped_data[key] = {
                    "governing_body_name": group["governing_body_name"],
                    "governing_body_type": group["governing_body_type"],
                    "groups": [],  # type: list[dict[str, Any]]
                }
            grouped_data[key]["groups"].append(group)

        first_group = True
        group_keys: list[str] = list(grouped_data.keys())
        for group_idx, (key, data) in enumerate(grouped_data.items()):
            body_name: str = data["governing_body_name"]
            body_type: str = data["governing_body_type"]
            groups_list: list[dict[str, Any]] = data["groups"]

            if not first_group:
                lines.append("")
            lines.append(f"-- {key}")

            for i, group in enumerate(groups_list):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                name: str = group["name"].replace("'", "''")
                body_name_escaped: str = body_name.replace("'", "''")
                body_type_escaped: str = body_type.replace("'", "''")

                # 最後の要素かどうかチェック（全体での最後）
                is_last = group_idx == len(group_keys) - 1 and i == len(groups_list) - 1
                comma = "" if is_last else ","

                # NULL値の処理
                url = (
                    f"'{group['url'].replace(chr(39), chr(39) * 2)}'"
                    if group.get("url")
                    else "NULL"
                )
                description = (
                    f"'{group['description'].replace(chr(39), chr(39) * 2)}'"
                    if group.get("description")
                    else "NULL"
                )
                is_active = "true" if group.get("is_active", True) else "false"

                # governing_body_idのサブクエリ
                governing_body_part = (
                    f"(SELECT id FROM governing_bodies "
                    f"WHERE name = '{body_name_escaped}' "
                    f"AND type = '{body_type_escaped}')"
                )

                # political_party_idの処理
                if group.get("party_name"):
                    party_name_escaped = group["party_name"].replace("'", "''")
                    party_id_part = (
                        f"(SELECT id FROM political_parties "
                        f"WHERE name = '{party_name_escaped}')"
                    )
                else:
                    party_id_part = "NULL"

                lines.append(
                    f"('{name}', {governing_body_part}, "
                    f"{url}, {description}, {is_active}, "
                    f"{party_id_part}){comma}"
                )

            first_group = False

        lines.append(
            "ON CONFLICT (name, governing_body_id) DO UPDATE SET "
            "url = EXCLUDED.url, "
            "description = EXCLUDED.description, "
            "is_active = EXCLUDED.is_active, "
            "political_party_id = EXCLUDED.political_party_id;"
        )

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_meetings_seed(self, output: TextIO | None = None) -> str:
        """meetingsテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT m.conference_id, m.date, m.url,
                           m.gcs_pdf_uri, m.gcs_text_uri,
                           c.name as conference_name,
                           gb.name as governing_body_name,
                           gb.type as governing_body_type
                    FROM meetings m
                    JOIN conferences c ON m.conference_id = c.id
                    JOIN governing_bodies gb ON c.governing_body_id = gb.id
                    ORDER BY m.date DESC, gb.name, c.name
                """)
            )
            columns = result.keys()
            meetings = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- meetings seed data",
            "",
            (
                "INSERT INTO meetings "
                "(conference_id, date, url, gcs_pdf_uri, gcs_text_uri) VALUES"
            ),
        ]

        for i, meeting in enumerate(meetings):
            comma = "," if i < len(meetings) - 1 else ""

            # 会議体名をエスケープ
            conf_name_escaped = meeting["conference_name"].replace("'", "''")
            body_name_escaped = meeting["governing_body_name"].replace("'", "''")
            body_type_escaped = meeting["governing_body_type"].replace("'", "''")

            # 日付フォーマット
            date_str = (
                meeting["date"].strftime("%Y-%m-%d") if meeting["date"] else "NULL"
            )

            # URLとGCS URIの処理
            url = (
                f"'{meeting['url'].replace(chr(39), chr(39) + chr(39))}'"
                if meeting["url"]
                else "NULL"
            )
            gcs_pdf_uri = (
                f"'{meeting['gcs_pdf_uri'].replace(chr(39), chr(39) + chr(39))}'"
                if meeting["gcs_pdf_uri"]
                else "NULL"
            )
            gcs_text_uri = (
                f"'{meeting['gcs_text_uri'].replace(chr(39), chr(39) + chr(39))}'"
                if meeting["gcs_text_uri"]
                else "NULL"
            )

            lines.append(
                f"((SELECT c.id FROM conferences c "
                f"JOIN governing_bodies gb ON c.governing_body_id = gb.id "
                f"WHERE c.name = '{conf_name_escaped}' "
                f"AND gb.name = '{body_name_escaped}' "
                f"AND gb.type = '{body_type_escaped}'), "
                f"'{date_str}', {url}, {gcs_pdf_uri}, {gcs_text_uri}){comma}"
            )

        lines.append(";")

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_politicians_seed(self, output: TextIO | None = None) -> str:
        """politiciansテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        p.name,
                        p.prefecture,
                        p.furigana,
                        p.district,
                        p.profile_page_url,
                        pp.name as party_name
                    FROM politicians p
                    LEFT JOIN political_parties pp ON p.political_party_id = pp.id
                    ORDER BY pp.name, p.name
                """)
            )
            columns = result.keys()
            politicians = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- politicians seed data",
            "",
            (
                "INSERT INTO politicians "
                "(name, political_party_id, prefecture, furigana, "
                "district, profile_page_url) VALUES"
            ),
        ]

        # 政党ごとにグループ化
        grouped_data: dict[str, list[dict[str, Any]]] = {}
        for politician in politicians:
            party_name = politician["party_name"] or "_無所属_"
            if party_name not in grouped_data:
                grouped_data[party_name] = []
            grouped_data[party_name].append(politician)

        first_group = True
        group_keys: list[str] = list(grouped_data.keys())
        for group_idx, (party_name, politicians_list) in enumerate(
            grouped_data.items()
        ):
            if not first_group:
                lines.append("")
            if party_name != "_無所属_":
                lines.append(f"-- {party_name}")
            else:
                lines.append("-- 無所属")

            for i, politician in enumerate(politicians_list):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                name = politician["name"].replace("'", "''")

                # 最後の要素かどうかチェック（全体での最後）
                is_last = (
                    group_idx == len(group_keys) - 1 and i == len(politicians_list) - 1
                )
                comma = "" if is_last else ","

                # NULL値の処理
                prefecture = (
                    f"'{politician['prefecture'].replace(chr(39), chr(39) * 2)}'"
                    if politician.get("prefecture")
                    else "NULL"
                )
                furigana = (
                    f"'{politician['furigana'].replace(chr(39), chr(39) * 2)}'"
                    if politician.get("furigana")
                    else "NULL"
                )
                if politician.get("district"):
                    d = politician["district"].replace("'", "''")
                    district = f"'{d}'"
                else:
                    district = "NULL"
                profile_page_url = (
                    f"'{politician['profile_page_url'].replace(chr(39), chr(39) * 2)}'"
                    if politician.get("profile_page_url")
                    else "NULL"
                )

                # political_party_idの処理
                if party_name != "_無所属_":
                    party_name_escaped = party_name.replace("'", "''")
                    party_id_part = (
                        f"(SELECT id FROM political_parties "
                        f"WHERE name = '{party_name_escaped}')"
                    )
                else:
                    party_id_part = "NULL"

                lines.append(
                    f"('{name}', {party_id_part}, {prefecture}, {furigana}, "
                    f"{district}, {profile_page_url}){comma}"
                )

            first_group = False

        lines.append(";")

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_election_members_seed(self, output: TextIO | None = None) -> str:
        """election_membersテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        em.election_id,
                        em.politician_id,
                        em.result,
                        em.votes,
                        em.rank,
                        e.term_number,
                        gb.name AS governing_body_name,
                        gb.type AS governing_body_type,
                        p.name AS politician_name
                    FROM election_members em
                    JOIN elections e ON em.election_id = e.id
                    JOIN governing_bodies gb ON e.governing_body_id = gb.id
                    JOIN politicians p ON em.politician_id = p.id
                    ORDER BY
                        CASE gb.type
                            WHEN '国' THEN 1
                            WHEN '都道府県' THEN 2
                            WHEN '市町村' THEN 3
                            ELSE 4
                        END,
                        gb.name,
                        e.term_number,
                        em.rank ASC NULLS LAST,
                        p.name
                """)
            )
            columns = result.keys()
            members = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- election_members seed data",
            "",
            (
                "INSERT INTO election_members "
                "(election_id, politician_id, result, votes, rank) VALUES"
            ),
        ]

        # 開催主体+回次ごとにグループ化
        grouped_data: dict[str, dict[str, Any]] = {}
        for member in members:
            key = (
                f"{member['governing_body_type']}_{member['governing_body_name']}"
                f"_{member['term_number']}"
            )
            if key not in grouped_data:
                grouped_data[key] = {
                    "body_name": member["governing_body_name"],
                    "body_type": member["governing_body_type"],
                    "term_number": member["term_number"],
                    "members": [],
                }
            grouped_data[key]["members"].append(member)

        first_group = True
        group_keys: list[str] = list(grouped_data.keys())
        for group_idx, (_key, data) in enumerate(grouped_data.items()):
            body_name: str = data["body_name"]
            body_type: str = data["body_type"]
            term_number: int = data["term_number"]
            members_list: list[dict[str, Any]] = data["members"]

            if not first_group:
                lines.append("")
            lines.append(f"-- {body_name} ({body_type}) 第{term_number}回")

            for i, member in enumerate(members_list):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                politician_name = member["politician_name"].replace("'", "''")
                result_val = member["result"].replace("'", "''")

                # 開催主体IDはサブクエリで取得（ネスト）
                body_name_escaped = body_name.replace("'", "''")
                body_type_escaped = body_type.replace("'", "''")
                election_id_part = (
                    f"(SELECT id FROM elections WHERE governing_body_id = "
                    f"(SELECT id FROM governing_bodies WHERE name = "
                    f"'{body_name_escaped}' AND type = '{body_type_escaped}') "
                    f"AND term_number = {term_number})"
                )

                # politician_idはサブクエリで取得
                politician_id_part = (
                    f"(SELECT id FROM politicians WHERE name = '{politician_name}')"
                )

                # NULL値の処理
                votes = str(member["votes"]) if member["votes"] is not None else "NULL"
                rank = str(member["rank"]) if member["rank"] is not None else "NULL"

                # 最後の要素かどうかチェック
                is_last = (
                    group_idx == len(group_keys) - 1 and i == len(members_list) - 1
                )
                comma = "" if is_last else ","

                lines.append(
                    f"({election_id_part}, {politician_id_part}, "
                    f"'{result_val}', {votes}, {rank}){comma}"
                )

            first_group = False

        lines.append(
            "ON CONFLICT (election_id, politician_id) DO UPDATE SET "
            "result = EXCLUDED.result, "
            "votes = EXCLUDED.votes, "
            "rank = EXCLUDED.rank;"
        )

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_elections_seed(self, output: TextIO | None = None) -> str:
        """electionsテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        e.id,
                        e.governing_body_id,
                        e.term_number,
                        e.election_date,
                        e.election_type,
                        gb.name as governing_body_name,
                        gb.type as governing_body_type
                    FROM elections e
                    JOIN governing_bodies gb ON e.governing_body_id = gb.id
                    ORDER BY
                        CASE gb.type
                            WHEN '国' THEN 1
                            WHEN '都道府県' THEN 2
                            WHEN '市町村' THEN 3
                            ELSE 4
                        END,
                        gb.name,
                        e.term_number
                """)
            )
            columns = result.keys()
            elections = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- elections seed data",
            "",
            (
                "INSERT INTO elections "
                "(id, governing_body_id, term_number, election_date, election_type) "
                "VALUES"
            ),
        ]

        # 開催主体ごとにグループ化
        grouped_data: dict[str, dict[str, Any]] = {}
        for election in elections:
            key = f"{election['governing_body_type']}_{election['governing_body_name']}"
            if key not in grouped_data:
                grouped_data[key] = {
                    "body_name": election["governing_body_name"],
                    "body_type": election["governing_body_type"],
                    "elections": [],
                }
            grouped_data[key]["elections"].append(election)

        first_group = True
        group_keys: list[str] = list(grouped_data.keys())
        for group_idx, (_key, data) in enumerate(grouped_data.items()):
            body_name: str = data["body_name"]
            body_type: str = data["body_type"]
            elections_list: list[dict[str, Any]] = data["elections"]

            if not first_group:
                lines.append("")
            lines.append(f"-- {body_name} ({body_type})")

            for i, election in enumerate(elections_list):
                election_id = election["id"]
                term_number = election["term_number"]

                # 日付フォーマット
                date_str = (
                    election["election_date"].strftime("%Y-%m-%d")
                    if election["election_date"]
                    else "NULL"
                )

                # election_typeの処理
                if election.get("election_type"):
                    etype = election["election_type"].replace("'", "''")
                    election_type = f"'{etype}'"
                else:
                    election_type = "NULL"

                # 開催主体IDはサブクエリで取得
                body_name_escaped = body_name.replace("'", "''")
                body_type_escaped = body_type.replace("'", "''")
                governing_body_part = (
                    f"(SELECT id FROM governing_bodies WHERE name = "
                    f"'{body_name_escaped}' AND type = '{body_type_escaped}')"
                )

                # 最後の要素かどうかチェック
                is_last = (
                    group_idx == len(group_keys) - 1 and i == len(elections_list) - 1
                )
                comma = "" if is_last else ","

                lines.append(
                    f"({election_id}, {governing_body_part}, {term_number}, "
                    f"'{date_str}', {election_type}){comma}"
                )

            first_group = False

        lines.append(
            "ON CONFLICT (governing_body_id, term_number) DO UPDATE SET "
            "election_date = EXCLUDED.election_date, "
            "election_type = EXCLUDED.election_type;"
        )
        lines.append("")
        lines.append("-- Reset sequence to max id + 1")
        lines.append(
            "SELECT setval('elections_id_seq', "
            "(SELECT COALESCE(MAX(id), 0) + 1 FROM elections), false);"
        )

        result = "\n".join(lines) + "\n"
        if output:
            output.write(result)
        return result

    def generate_parliamentary_group_memberships_seed(
        self, output: TextIO | None = None
    ) -> str:
        """parliamentary_group_membershipsテーブルのSEEDファイルを生成する.

        ユニーク制約がないため、個別INSERT + WHERE NOT EXISTS
        パターンで冪等性を確保する。
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        pgm.politician_id,
                        pgm.parliamentary_group_id,
                        pgm.start_date,
                        pgm.end_date,
                        pgm.role,
                        p.name AS politician_name,
                        pg.name AS group_name,
                        gb.name AS governing_body_name,
                        gb.type AS governing_body_type,
                        e.term_number
                    FROM parliamentary_group_memberships pgm
                    JOIN politicians p ON pgm.politician_id = p.id
                    JOIN parliamentary_groups pg
                        ON pgm.parliamentary_group_id = pg.id
                    JOIN governing_bodies gb ON pg.governing_body_id = gb.id
                    LEFT JOIN elections e
                        ON e.governing_body_id = gb.id
                        AND e.election_date = pgm.start_date
                    ORDER BY
                        pgm.start_date,
                        gb.name,
                        pg.name,
                        p.name
                """)
            )
            columns = result.keys()
            memberships = [dict(zip(columns, row, strict=False)) for row in result]

        lines = [
            (
                f"-- Generated from database on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            "-- parliamentary_group_memberships seed data",
            ("-- ユニーク制約がないため、個別INSERT + WHERE NOT EXISTSで冪等性を確保"),
            "",
        ]

        # start_date（選挙回次）ごとにグループ化
        grouped_data: dict[str, dict[str, Any]] = {}
        for membership in memberships:
            start_date_str = membership["start_date"].strftime("%Y-%m-%d")
            term = membership.get("term_number")
            key = f"{start_date_str}_{term}"
            if key not in grouped_data:
                grouped_data[key] = {
                    "start_date": start_date_str,
                    "term_number": term,
                    "memberships": [],
                }
            grouped_data[key]["memberships"].append(membership)

        for _key, data in grouped_data.items():
            start_date_str = data["start_date"]
            term_number = data["term_number"]
            members_list: list[dict[str, Any]] = data["memberships"]

            if term_number:
                lines.append(f"-- 第{term_number}回 ({start_date_str})")
            else:
                lines.append(f"-- {start_date_str}")

            for membership in members_list:
                politician_name = membership["politician_name"].replace("'", "''")
                group_name = membership["group_name"].replace("'", "''")
                body_name = membership["governing_body_name"].replace("'", "''")
                body_type = membership["governing_body_type"].replace("'", "''")

                # end_dateの処理
                end_date_val = (
                    f"'{membership['end_date'].strftime('%Y-%m-%d')}'"
                    if membership.get("end_date")
                    else "NULL"
                )

                # roleの処理
                role_val = (
                    f"'{membership['role'].replace(chr(39), chr(39) * 2)}'"
                    if membership.get("role")
                    else "NULL"
                )

                # サブクエリ部品
                politician_sub = (
                    f"(SELECT id FROM politicians WHERE name = '{politician_name}')"
                )
                group_sub = (
                    f"(SELECT id FROM parliamentary_groups "
                    f"WHERE name = '{group_name}' "
                    f"AND governing_body_id = "
                    f"(SELECT id FROM governing_bodies "
                    f"WHERE name = '{body_name}' "
                    f"AND type = '{body_type}'))"
                )

                insert_stmt = (
                    "INSERT INTO parliamentary_group_memberships "
                    "(politician_id, parliamentary_group_id, "
                    "start_date, end_date, role)"
                )
                lines.append(insert_stmt)
                lines.append(
                    f"SELECT {politician_sub}, {group_sub}, "
                    f"'{start_date_str}', {end_date_val}, {role_val}"
                )
                lines.append(
                    f"WHERE NOT EXISTS ("
                    f"SELECT 1 FROM parliamentary_group_memberships "
                    f"WHERE politician_id = {politician_sub} "
                    f"AND parliamentary_group_id = {group_sub} "
                    f"AND start_date = '{start_date_str}'"
                    f");"
                )

            lines.append("")

        result_str = "\n".join(lines) + "\n"
        if output:
            output.write(result_str)
        return result_str


def generate_all_seeds(output_dir: str = "database") -> None:
    """すべてのSEEDファイルを生成する"""
    import os

    generator = SeedGenerator()

    # ディレクトリが/で終わっている場合は削除
    output_dir = output_dir.rstrip("/")

    # governing_bodies
    path = os.path.join(output_dir, "seed_governing_bodies_generated.sql")
    with open(path, "w") as f:
        generator.generate_governing_bodies_seed(f)
        print(f"Generated: {path}")

    # elections
    path = os.path.join(output_dir, "seed_elections_generated.sql")
    with open(path, "w") as f:
        generator.generate_elections_seed(f)
        print(f"Generated: {path}")

    # conferences
    path = os.path.join(output_dir, "seed_conferences_generated.sql")
    with open(path, "w") as f:
        generator.generate_conferences_seed(f)
        print(f"Generated: {path}")

    # political_parties
    path = os.path.join(output_dir, "seed_political_parties_generated.sql")
    with open(path, "w") as f:
        generator.generate_political_parties_seed(f)
        print(f"Generated: {path}")

    # parliamentary_groups
    path = os.path.join(output_dir, "seed_parliamentary_groups_generated.sql")
    with open(path, "w") as f:
        generator.generate_parliamentary_groups_seed(f)
        print(f"Generated: {path}")

    # meetings
    path = os.path.join(output_dir, "seed_meetings_generated.sql")
    with open(path, "w") as f:
        generator.generate_meetings_seed(f)
        print(f"Generated: {path}")

    # politicians
    path = os.path.join(output_dir, "seed_politicians_generated.sql")
    with open(path, "w") as f:
        generator.generate_politicians_seed(f)
        print(f"Generated: {path}")

    # election_members
    path = os.path.join(output_dir, "seed_election_members_generated.sql")
    with open(path, "w") as f:
        generator.generate_election_members_seed(f)
        print(f"Generated: {path}")

    # parliamentary_group_memberships
    path = os.path.join(
        output_dir, "seed_parliamentary_group_memberships_generated.sql"
    )
    with open(path, "w") as f:
        generator.generate_parliamentary_group_memberships_seed(f)
        print(f"Generated: {path}")


if __name__ == "__main__":
    generate_all_seeds()
