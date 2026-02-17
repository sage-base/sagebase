"""BigQueryクライアント.

GCSクライアントパターンを踏襲し、Gold Layerテーブルの作成・管理を行う。
"""

import logging

from typing import TYPE_CHECKING, Any

from src.infrastructure.bigquery.schema import BQTableDef, to_bigquery_schema


try:
    from google.api_core.exceptions import Conflict, Forbidden, NotFound
    from google.auth.exceptions import RefreshError
    from google.cloud import bigquery
    from google.cloud.exceptions import GoogleCloudError

    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False
    if TYPE_CHECKING:
        from google.api_core.exceptions import Conflict, Forbidden, NotFound
        from google.auth.exceptions import RefreshError
        from google.cloud import bigquery
        from google.cloud.exceptions import GoogleCloudError
    else:
        GoogleCloudError = Exception
        Forbidden = Exception
        NotFound = Exception
        Conflict = Exception
        RefreshError = Exception
        bigquery = None

from src.infrastructure.exceptions import (
    AuthenticationError,
    StorageError,
)


logger = logging.getLogger(__name__)


class BigQueryClient:
    """BigQuery Gold Layerテーブル管理クライアント."""

    def __init__(
        self,
        project_id: str,
        dataset_id: str = "sagebase_gold",
        location: str = "asia-northeast1",
    ) -> None:
        self.client: Any

        if not HAS_BIGQUERY:
            raise StorageError(
                "Google Cloud BigQuery library not installed. "
                "Install with: uv add google-cloud-bigquery"
            )

        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location

        try:
            self.client = (
                bigquery.Client(project=project_id, location=location)
                if bigquery
                else None
            )
        except RefreshError as e:
            logger.error(f"BigQuery authentication failed: {e}")
            raise AuthenticationError(
                service="BigQuery",
                reason="認証トークンの有効期限が切れています",
                solution="以下のコマンドを実行して再認証してください:\n"
                "  gcloud auth application-default login",
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise StorageError(
                "Failed to initialize BigQuery client",
                {"project_id": project_id, "error": str(e)},
            ) from e

    @property
    def _dataset_ref(self) -> str:
        return f"{self.project_id}.{self.dataset_id}"

    def ensure_dataset(self) -> None:
        """データセットを作成する（存在する場合はスキップ）."""
        dataset = bigquery.Dataset(self._dataset_ref) if bigquery else None
        if dataset is None:
            raise StorageError("BigQuery library not available")

        dataset.location = self.location
        try:
            self.client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Dataset {self._dataset_ref} is ready")
        except Forbidden as e:
            logger.error(f"Permission denied creating dataset: {e}")
            raise StorageError(
                f"Permission denied creating dataset '{self.dataset_id}'",
                {"dataset_id": self.dataset_id, "error": str(e)},
            ) from e
        except GoogleCloudError as e:
            logger.error(f"Failed to create dataset: {e}")
            raise StorageError(
                f"Failed to create dataset '{self.dataset_id}'",
                {"dataset_id": self.dataset_id, "error": str(e)},
            ) from e

    def create_table(self, table_def: BQTableDef) -> None:
        """テーブルを作成する（存在する場合はスキップ）."""
        table_ref = f"{self._dataset_ref}.{table_def.table_id}"
        schema = to_bigquery_schema(table_def)

        table = bigquery.Table(table_ref, schema=schema) if bigquery else None
        if table is None:
            raise StorageError("BigQuery library not available")

        table.description = table_def.description

        try:
            self.client.create_table(table, exists_ok=True)
            logger.info(f"Table {table_ref} is ready")
        except Forbidden as e:
            logger.error(f"Permission denied creating table: {e}")
            raise StorageError(
                f"Permission denied creating table '{table_def.table_id}'",
                {"table_id": table_def.table_id, "error": str(e)},
            ) from e
        except GoogleCloudError as e:
            logger.error(f"Failed to create table: {e}")
            raise StorageError(
                f"Failed to create table '{table_def.table_id}'",
                {"table_id": table_def.table_id, "error": str(e)},
            ) from e

    def create_all_tables(self, table_defs: list[BQTableDef]) -> None:
        """全テーブルを一括作成する."""
        self.ensure_dataset()
        for table_def in table_defs:
            self.create_table(table_def)
        logger.info(f"All {len(table_defs)} tables created successfully")
