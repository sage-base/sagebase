"""Domain DTOとPydanticモデル間の変換関数

Clean Architectureの原則に従い、Infrastructure層で
Domain層のdataclass DTOとInfrastructure層のPydanticモデル間の
変換を行います。
"""

from src.domain.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
)
from src.parliamentary_group_member_extractor.models import ExtractedMember


def dto_to_pydantic(
    dto: ExtractedParliamentaryGroupMemberDTO,
) -> ExtractedMember:
    """Domain DTO → Pydantic Model変換

    Args:
        dto: Domain層のdataclass DTO

    Returns:
        Infrastructure層のPydanticモデル
    """
    return ExtractedMember(
        name=dto.name,
        role=dto.role,
        party_name=dto.party_name,
        district=dto.district,
        additional_info=dto.additional_info,
    )


def pydantic_to_dto(
    model: ExtractedMember,
) -> ExtractedParliamentaryGroupMemberDTO:
    """Pydantic Model → Domain DTO変換

    Args:
        model: Infrastructure層のPydanticモデル

    Returns:
        Domain層のdataclass DTO
    """
    return ExtractedParliamentaryGroupMemberDTO(
        name=model.name,
        role=model.role,
        party_name=model.party_name,
        district=model.district,
        additional_info=model.additional_info,
    )
