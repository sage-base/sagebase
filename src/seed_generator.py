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

        lines.append("ON CONFLICT (name, governing_body_id) DO NOTHING;")

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
                        c.name as conference_name,
                        gb.name as governing_body_name,
                        gb.type as governing_body_type
                    FROM parliamentary_groups pg
                    JOIN conferences c ON pg.conference_id = c.id
                    JOIN governing_bodies gb ON c.governing_body_id = gb.id
                    ORDER BY gb.name, c.name, pg.name
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
                "(name, conference_id, url, description, is_active) VALUES"
            ),
        ]

        # 会議体ごとにグループ化
        grouped_data: dict[str, dict[str, Any]] = {}
        for group in groups:
            key = f"{group['governing_body_name']} - {group['conference_name']}"
            if key not in grouped_data:
                grouped_data[key] = {
                    "conference_name": group["conference_name"],
                    "governing_body_name": group["governing_body_name"],
                    "governing_body_type": group["governing_body_type"],
                    "groups": [],  # type: list[dict[str, Any]]
                }
            grouped_data[key]["groups"].append(group)

        first_group = True
        group_keys: list[str] = list(grouped_data.keys())
        for group_idx, (key, data) in enumerate(grouped_data.items()):
            conf_name: str = data["conference_name"]
            body_name: str = data["governing_body_name"]
            body_type: str = data["governing_body_type"]
            groups_list: list[dict[str, Any]] = data["groups"]

            if not first_group:
                lines.append("")
            lines.append(f"-- {key}")

            for i, group in enumerate(groups_list):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                name: str = group["name"].replace("'", "''")
                conf_name_escaped: str = conf_name.replace("'", "''")
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

                lines.append(
                    f"('{name}', "
                    f"(SELECT c.id FROM conferences c "
                    f"JOIN governing_bodies gb ON c.governing_body_id = gb.id "
                    f"WHERE c.name = '{conf_name_escaped}' "
                    f"AND gb.name = '{body_name_escaped}' "
                    f"AND gb.type = '{body_type_escaped}'), "
                    f"{url}, {description}, {is_active}){comma}"
                )

            first_group = False

        lines.append("ON CONFLICT (name, conference_id) DO NOTHING;")

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
                        p.electoral_district,
                        p.profile_url,
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
                "(name, political_party_id, position, prefecture, "
                "electoral_district, profile_url) VALUES"
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
                position = (
                    f"'{politician['position'].replace(chr(39), chr(39) * 2)}'"
                    if politician.get("position")
                    else "NULL"
                )
                prefecture = (
                    f"'{politician['prefecture'].replace(chr(39), chr(39) * 2)}'"
                    if politician.get("prefecture")
                    else "NULL"
                )
                if politician.get("electoral_district"):
                    ed = politician["electoral_district"].replace("'", "''")
                    electoral_district = f"'{ed}'"
                else:
                    electoral_district = "NULL"
                profile_url = (
                    f"'{politician['profile_url'].replace(chr(39), chr(39) * 2)}'"
                    if politician.get("profile_url")
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
                    f"('{name}', {party_id_part}, {position}, {prefecture}, "
                    f"{electoral_district}, {profile_url}){comma}"
                )

            first_group = False

        lines.append(";")

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


if __name__ == "__main__":
    generate_all_seeds()
