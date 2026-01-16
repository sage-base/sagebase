"""Role-Name Mapping Service

役職-人名マッピング抽出サービスのInfrastructure層実装。
"""

from src.infrastructure.external.role_name_mapping.baml_role_name_mapping_service import (  # noqa: E501
    BAMLRoleNameMappingService,
)


__all__ = ["BAMLRoleNameMappingService"]
