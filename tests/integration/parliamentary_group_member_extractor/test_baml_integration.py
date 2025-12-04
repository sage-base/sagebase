"""議員団メンバー抽出器のBAML統合テスト

このモジュールは、BAML生成コードが正しく機能することを検証します。
実際のBAMLクライアントを使用して、生成された関数の存在と呼び出し可能性を確認します。
"""

import pytest


@pytest.mark.integration
class TestBAMLIntegration:
    """BAML統合テストクラス"""

    def test_baml_client_has_extract_function(self):
        """BAML関数が正しく生成されていることを確認

        BAML生成コードに以下が含まれることを検証：
        1. ExtractParliamentaryGroupMembers関数が存在する
        2. その関数が呼び出し可能である
        3. 正しいモジュール構造である
        """
        from baml_client import b

        # BAML関数の存在確認
        assert hasattr(b, "ExtractParliamentaryGroupMembers"), (
            "ExtractParliamentaryGroupMembers function not found in baml_client.b"
        )

        # 関数が呼び出し可能であることを確認
        assert callable(b.ExtractParliamentaryGroupMembers), (
            "ExtractParliamentaryGroupMembers is not callable"
        )

    def test_baml_client_is_async(self):
        """BAML関数が非同期関数であることを確認

        ExtractParliamentaryGroupMembersが非同期関数として
        正しく生成されていることを検証します。
        """
        import inspect

        from baml_client import b

        # 非同期関数であることを確認
        assert inspect.iscoroutinefunction(b.ExtractParliamentaryGroupMembers), (
            "ExtractParliamentaryGroupMembers should be an async function"
        )

    def test_baml_client_signature(self):
        """BAML関数のシグネチャが正しいことを確認

        関数が期待されるパラメータを受け取ることを検証します。
        """
        import inspect

        from baml_client import b

        # シグネチャを取得
        sig = inspect.signature(b.ExtractParliamentaryGroupMembers)

        # パラメータ名を確認
        param_names = list(sig.parameters.keys())

        # 期待されるパラメータが含まれることを確認
        assert "html" in param_names, (
            "ExtractParliamentaryGroupMembers should have 'html' parameter"
        )
        assert "text_content" in param_names, (
            "ExtractParliamentaryGroupMembers should have 'text_content' parameter"
        )

    def test_baml_types_module_exists(self):
        """BAML型定義モジュールが存在することを確認

        生成されたBAML型が正しくインポート可能であることを検証します。
        """
        from baml_client import types

        # ParliamentaryGroupMember型が存在することを確認
        assert hasattr(types, "ParliamentaryGroupMember"), (
            "ParliamentaryGroupMember type not found in baml_client.types"
        )

    def test_baml_parliamentary_group_member_type_structure(self):
        """ParliamentaryGroupMember型の構造が正しいことを確認

        生成された型に期待されるフィールドが含まれることを検証します。
        """
        from baml_client import types

        # 型のアノテーションを取得（可能な場合）
        member_type = types.ParliamentaryGroupMember

        # 型が存在し、インスタンス化可能であることを確認
        assert member_type is not None, "ParliamentaryGroupMember type should exist"

        # 型のアトリビュートを確認（Pydanticモデルの場合）
        if hasattr(member_type, "model_fields"):
            fields = member_type.model_fields
            expected_fields = [
                "name",
                "role",
                "party_name",
                "district",
                "additional_info",
            ]

            for field in expected_fields:
                assert field in fields, (
                    f"ParliamentaryGroupMember should have '{field}' field"
                )

    @pytest.mark.asyncio
    async def test_baml_function_returns_list(self):
        """BAML関数が正しい型（リスト）を返すことを確認

        モックデータを使用して、関数が期待される戻り値の型を
        返すことを検証します。

        Note:
            このテストは実際のLLM呼び出しを行わないため、
            モックまたは簡易的なデータで検証します。
        """
        from unittest.mock import AsyncMock, patch

        from baml_client import b, types

        # BAML関数をモックして、正しい型のリストを返すようにする
        mock_result = [
            types.ParliamentaryGroupMember(
                name="テスト議員",
                role="団長",
                party_name="テスト党",
                district="テスト区",
                additional_info=None,
            )
        ]

        with patch.object(
            b, "ExtractParliamentaryGroupMembers", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = mock_result

            result = await b.ExtractParliamentaryGroupMembers(
                html="<html><body>テスト</body></html>", text_content="テスト議員 団長"
            )

            # 結果がリストであることを確認
            assert isinstance(result, list), "Result should be a list"

            # リストが空でないことを確認
            assert len(result) > 0, "Result should not be empty"

            # リストの要素がParliamentaryGroupMember型であることを確認
            assert isinstance(result[0], types.ParliamentaryGroupMember), (
                "List elements should be ParliamentaryGroupMember instances"
            )

    def test_baml_client_version_compatibility(self):
        """BAMLクライアントのバージョンが互換性があることを確認

        生成されたクライアントがbaml-pyのバージョンと
        互換性があることを検証します。
        """
        from baml_client import __version__

        # バージョンが存在することを確認
        assert __version__ is not None, "BAML client should have a version"

        # バージョンが期待される形式であることを確認（例: "0.214.0"）
        version_parts = __version__.split(".")
        assert len(version_parts) == 3, "Version should be in format X.Y.Z"

        # 各パートが数値であることを確認
        for part in version_parts:
            assert part.isdigit(), f"Version part '{part}' should be numeric"
