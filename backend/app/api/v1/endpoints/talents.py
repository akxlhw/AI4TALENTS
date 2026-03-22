"""
Talents API endpoints.
Provides talent list, detail, and filtering.
"""
import io
import csv
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.talent_repository import TalentRepository
from app.schemas.common import PaginatedResponse
from app.schemas.overview import TalentSummary, TalentDetail, SelectedWorkResponse

router = APIRouter(prefix="/talents", tags=["Talents"])


@router.get(
    "",
    response_model=PaginatedResponse[TalentSummary],
    summary="获取人才列表",
    description="分页查询人才列表，支持多种筛选条件",
)
async def list_talents(
    school_id: Optional[int] = Query(None, description="按学校ID筛选"),
    country_id: Optional[int] = Query(None, description="按国家ID筛选"),
    role_type: Optional[str] = Query(None, description="按角色类型筛选 (professor/student/graduated/unknown)"),
    min_works: Optional[int] = Query(None, description="最小论文数"),
    min_citations: Optional[int] = Query(None, description="最小引用数"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paginated list of talents.

    Supports filtering by:
    - school_id: Filter by school
    - country_id: Filter by country (via school)
    - role_type: Filter by role type
    - min_works: Minimum works count
    - min_citations: Minimum citation count
    - keyword: Search in name, English name, and title
    """
    repo = TalentRepository(session)
    talents, total = await repo.get_list(
        school_id=school_id,
        country_id=country_id,
        role_type=role_type,
        min_works=min_works,
        min_citations=min_citations,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    items = [
        TalentSummary(
            talent_id=talent.talent_id,
            name=talent.name,
            name_en=talent.name_en,
            orcid=talent.orcid,
            role_type=talent.role_type,
            role_confidence=talent.role_confidence,
            school_id=talent.school_id,
            school_name=talent.school.school_name if talent.school else None,
            current_title=talent.current_title,
            works_count=talent.works_count,
            cited_by_count=talent.cited_by_count,
            h_index=talent.h_index,
            topic_tags=talent.topic_tags or [],
        )
        for talent in talents
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{talent_id}",
    response_model=TalentDetail,
    summary="获取人才详情",
    description="返回人才的详细信息，包括研究兴趣、代表作品等",
)
async def get_talent(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed information about a specific talent.

    Returns:
    - Basic talent information
    - School affiliation
    - Research statistics
    - Role profile
    - Selected works
    """
    repo = TalentRepository(session)
    talent = await repo.get_by_id(talent_id)

    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")

    # Build selected works list
    selected_works = [
        SelectedWorkResponse(
            work_id=work.work_id,
            title=work.title,
            publication_year=work.publication_year,
            venue_name=work.venue_name,
            citation_count=work.citation_count,
            doi=work.doi,
        )
        for work in (talent.selected_works or [])
    ]

    return TalentDetail(
        talent_id=talent.talent_id,
        name=talent.name,
        name_en=talent.name_en,
        orcid=talent.orcid,
        role_type=talent.role_type,
        role_confidence=talent.role_confidence,
        school_id=talent.school_id,
        school_name=talent.school.school_name if talent.school else None,
        current_title=talent.current_title,
        works_count=talent.works_count,
        cited_by_count=talent.cited_by_count,
        h_index=talent.h_index,
        latest_active_year=talent.latest_active_year,
        topic_tags=talent.topic_tags or [],
        research_interests=talent.research_interests,
        summary=talent.summary,
        department_name=talent.department_name,
        lab_name=talent.lab_name,
        role_reason=talent.role_profile.role_reason if talent.role_profile else None,
        academic_age=talent.role_profile.academic_age if talent.role_profile else None,
        selected_works=selected_works,
    )


@router.get(
    "/{talent_id}/works",
    response_model=list[SelectedWorkResponse],
    summary="获取人才代表作品",
    description="返回人才的代表作品列表",
)
async def get_talent_works(
    talent_id: int,
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get selected works for a specific talent.

    Returns list of representative works ordered by citation count.
    """
    repo = TalentRepository(session)

    # Verify talent exists
    talent = await repo.get_by_id(talent_id, include_relations=False)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")

    works = await repo.get_selected_works(talent_id, limit=limit)

    return [
        SelectedWorkResponse(
            work_id=work.work_id,
            title=work.title,
            publication_year=work.publication_year,
            venue_name=work.venue_name,
            citation_count=work.citation_count,
            doi=work.doi,
        )
        for work in works
    ]


@router.post(
    "/export",
    summary="导出候选人",
    description="导出选中的候选人数据为CSV或Excel格式",
)
async def export_talents(
    format: str = Query("csv", description="导出格式: csv 或 xlsx"),
    talent_ids: List[int] = Query(..., description="要导出的人才ID列表"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Export selected talents to CSV or Excel format.
    """
    from openpyxl import Workbook

    repo = TalentRepository(session)

    # Fetch talents by IDs
    talents = []
    for talent_id in talent_ids:
        talent = await repo.get_by_id(talent_id)
        if talent:
            talents.append(talent)

    if not talents:
        raise HTTPException(status_code=404, detail="未找到要导出的人才")

    # Prepare data
    headers = ["ID", "姓名", "英文名", "ORCID", "角色", "学校", "职位", "论文数", "引用数", "H指数", "研究方向"]
    rows = []
    for t in talents:
        rows.append([
            t.talent_id,
            t.name,
            t.name_en or "",
            t.orcid or "",
            t.role_type,
            t.school.school_name if t.school else "",
            t.current_title or "",
            t.works_count,
            t.cited_by_count,
            t.h_index,
            ", ".join(t.topic_tags or []),
        ])

    if format == "xlsx":
        # Create Excel file
        wb = Workbook()
        ws = wb.active
        ws.title = "候选人导出"

        # Write headers
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        # Write data
        for row_idx, row in enumerate(rows, 2):
            for col_idx, value in enumerate(row, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)

        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[column].width = min(max_length + 2, 50)

        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=talents_export.xlsx"},
        )
    else:
        # Create CSV
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(rows)
        buffer.seek(0)

        return StreamingResponse(
            io.BytesIO(buffer.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=talents_export.csv"},
        )


@router.post(
    "/compare",
    summary="对比候选人",
    description="获取多个候选人的对比数据",
)
async def compare_talents(
    talent_ids: List[int] = Query(..., description="要对比的人才ID列表 (2-4个)"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Compare multiple talents (2-4) side by side.
    Returns detailed comparison data.
    """
    if len(talent_ids) < 2 or len(talent_ids) > 4:
        raise HTTPException(status_code=400, detail="请选择2-4位候选人进行对比")

    repo = TalentRepository(session)

    # Fetch talents by IDs
    talents = []
    for talent_id in talent_ids:
        talent = await repo.get_by_id(talent_id)
        if talent:
            talents.append(talent)

    if not talents:
        raise HTTPException(status_code=404, detail="未找到要对比的人才")

    # Build comparison data
    comparison_data = []
    for t in talents:
        comparison_data.append({
            "talent_id": t.talent_id,
            "name": t.name,
            "name_en": t.name_en,
            "orcid": t.orcid,
            "role_type": t.role_type,
            "school_id": t.school_id,
            "school_name": t.school.school_name if t.school else None,
            "current_title": t.current_title,
            "department_name": t.department_name,
            "lab_name": t.lab_name,
            "works_count": t.works_count,
            "cited_by_count": t.cited_by_count,
            "h_index": t.h_index,
            "latest_active_year": t.latest_active_year,
            "topic_tags": t.topic_tags or [],
            "research_interests": t.research_interests,
            "academic_age": t.role_profile.academic_age if t.role_profile else None,
        })

    return {
        "talents": comparison_data,
        "comparison_fields": [
            {"key": "name", "label": "姓名"},
            {"key": "role_type", "label": "角色"},
            {"key": "school_name", "label": "学校"},
            {"key": "current_title", "label": "职位"},
            {"key": "department_name", "label": "院系"},
            {"key": "works_count", "label": "论文数"},
            {"key": "cited_by_count", "label": "引用数"},
            {"key": "h_index", "label": "H指数"},
            {"key": "latest_active_year", "label": "最近活跃年份"},
            {"key": "academic_age", "label": "学术年龄"},
            {"key": "topic_tags", "label": "研究方向"},
        ]
    }


@router.post(
    "/collaborations/generate-sample",
    summary="生成示例合作数据",
    description="为测试目的生成随机合作数据",
)
async def generate_sample_collaborations(
    num_samples: int = Query(100, ge=10, le=1000, description="生成合作数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Generate sample collaboration data for testing.
    """
    from app.services.collaboration_service import CollaborationService

    service = CollaborationService(session)
    try:
        count = await service.generate_sample_collaborations(num_samples)
        return {"message": f"已生成 {count} 条合作数据", "count": count}
    finally:
        await service.close()


@router.get(
    "/{talent_id}/collaborations",
    summary="获取合作网络",
    description="获取学者的合作关系数据",
)
async def get_talent_collaborations(
    talent_id: int,
    limit: int = Query(20, ge=1, le=50, description="返回合作者数量限制"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get collaboration network for a talent.
    """
    from app.services.collaboration_service import CollaborationService

    repo = TalentRepository(session)

    # Verify talent exists
    talent = await repo.get_by_id(talent_id, include_relations=False)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")

    # Get collaboration network
    service = CollaborationService(session)
    try:
        network = await service.get_collaboration_network(talent_id, limit)
        return network
    finally:
        await service.close()
