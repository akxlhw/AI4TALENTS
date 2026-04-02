"""
End-to-End Data Flow Tests - 数据联动生效端到端测试
======================================================

核心测试目标：
验证采集任务完成后，整个系统的数据联动是否正确生效。

测试场景：
- TC-E2E-001: 完整采集流程数据联动
- TC-E2E-002: 角色识别正确性验证
- TC-E2E-003: 数据一致性验证
"""
import pytest
from datetime import datetime
import json

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.models.tech_element import TechElement, TechDirection, TalentTechTag
from app.models.venue import Venue, VenueTechBinding
from app.models.raw_data import AuthorTechBelong
from app.models.standardized import StdAuthor, StdSchool
from app.models.talent import Talent, RoleProfile
from app.models.school import School
from app.models.enums import RoleType, VisibilityStatus

from app.repositories.tech_element_repository import TechElementRepository
from app.services.serving_layer_sync import ServingLayerSync
from app.services.role_identifier import RoleIdentifier


# ============ Test Data Setup ============

@pytest.fixture
async def e2e_setup(test_session: AsyncSession):
    """创建端到端测试所需的基础数据"""
    # 创建技术要素
    tech_element = TechElement(
        element_code="E2E-AI",
        element_name="人工智能",
        element_name_en="Artificial Intelligence",
        is_enabled=True,
    )
    test_session.add(tech_element)
    await test_session.flush()

    # 创建技术方向
    tech_direction = TechDirection(
        tech_element_id=tech_element.tech_element_id,
        direction_code="E2E-ML",
        direction_name="机器学习",
        is_enabled=True,
    )
    test_session.add(tech_direction)

    # 创建Venue
    venue = Venue(
        venue_code="E2E-NEURIPS",
        venue_name="NeurIPS",
        venue_type="conference",
        openalex_source_id="S-E2E",
        is_enabled=True,
    )
    test_session.add(venue)
    await test_session.flush()

    # 创建Venue绑定
    binding = VenueTechBinding(
        venue_id=venue.venue_id,
        tech_element_id=tech_element.tech_element_id,
        is_enabled=True,
    )
    test_session.add(binding)

    await test_session.commit()

    return {
        "tech_element": tech_element,
        "tech_direction": tech_direction,
        "venue": venue,
    }


class TestE2EDataFlow:
    """端到端数据流测试"""

    @pytest.mark.asyncio
    async def test_e2e_001_std_to_serving_flow(
        self,
        test_session: AsyncSession,
        e2e_setup
    ):
        """
        TC-E2E-001: 标准化层到服务层数据流

        验证：
        1. 标准化层数据正确存储
        2. 服务层正确同步
        3. Talent表有正确的技术标签
        """
        # 创建采集任务
        task = CollectTask(
            task_code="E2E-001",
            tech_element_id=e2e_setup["tech_element"].tech_element_id,
            collect_mode="full",
            status="completed",
            triggered_at=datetime.utcnow(),
        )
        test_session.add(task)
        await test_session.flush()

        # ========== Phase 1: 标准化层 ==========
        std_school = StdSchool(
            openalex_institution_id="I-E2E-STANFORD",
            name_normalized="Stanford University",
            country_code="US",
            source_task_id=task.task_id,
        )
        test_session.add(std_school)
        await test_session.flush()

        std_author = StdAuthor(
            openalex_author_id="A-E2E-PROF001",
            name_normalized="Zhang Wei",
            name_original="Wei Zhang",
            works_count=50,
            cited_by_count=1500,
            h_index=18,
            std_school_id=std_school.std_school_id,
            source_task_id=task.task_id,
            cs_concepts_score=0.8,  # CS background score
        )
        test_session.add(std_author)
        await test_session.flush()

        # 创建技术归属
        tech_belong = AuthorTechBelong(
            openalex_author_id="A-E2E-PROF001",
            std_author_id=std_author.std_author_id,
            tech_element_id=e2e_setup["tech_element"].tech_element_id,
            source_venue_id=e2e_setup["venue"].venue_id,
            source_task_id=task.task_id,  # Required for sync
            work_count_in_venue=10,
        )
        test_session.add(tech_belong)
        await test_session.commit()

        # ========== Phase 2: 服务层同步 ==========
        sync = ServingLayerSync(test_session)
        stats = await sync.sync_all_for_task(
            task_id=task.task_id,
            tech_element_id=e2e_setup["tech_element"].tech_element_id,
            default_tech_direction_id=e2e_setup["tech_direction"].tech_direction_id,
        )
        await test_session.commit()

        # ========== Phase 3: 验证结果 ==========
        # 验证同步统计
        assert stats["authors_synced"] >= 1, "应该同步至少1个作者"

        # 验证Talent创建
        result = await test_session.execute(
            select(Talent).where(Talent.source_record_id == "A-E2E-PROF001")
        )
        talent = result.scalar_one_or_none()

        assert talent is not None, "Talent应该被创建"
        assert talent.name == "Zhang Wei"
        assert talent.role_type == RoleType.PROFESSOR.value, "角色应该是教授"
        assert talent.works_count == 50
        assert talent.h_index == 18

        # 验证技术标签创建
        result = await test_session.execute(
            select(TalentTechTag).where(
                TalentTechTag.talent_id == talent.talent_id
            )
        )
        tag = result.scalar_one_or_none()

        assert tag is not None, "技术标签应该被创建"
        assert tag.tech_element_id == e2e_setup["tech_element"].tech_element_id

        # 验证技术要素统计
        tech_repo = TechElementRepository(test_session)
        stats = await tech_repo.get_element_stats(
            e2e_setup["tech_element"].tech_element_id
        )

        assert stats["talent_count"] >= 1, "人才统计应该有数据"

    @pytest.mark.asyncio
    async def test_e2e_002_role_identification(
        self,
        test_session: AsyncSession,
        e2e_setup
    ):
        """
        TC-E2E-002: 角色识别正确性验证

        验证：
        1. 教授识别准确
        2. 学生识别准确
        3. 毕业生识别准确
        """
        # 创建任务
        task = CollectTask(
            task_code="E2E-002",
            tech_element_id=e2e_setup["tech_element"].tech_element_id,
            collect_mode="full",
            status="completed",
            triggered_at=datetime.utcnow(),
        )
        test_session.add(task)
        await test_session.flush()

        # 测试不同角色
        test_cases = [
            ("A-E2E-PROF", "Professor Test", 60, 2000, 25, RoleType.PROFESSOR),
            ("A-E2E-STUDENT", "Student Test", 5, 30, 2, RoleType.STUDENT),
            ("A-E2E-GRAD", "Graduate Test", 12, 150, 5, RoleType.GRADUATE),
        ]

        sync = ServingLayerSync(test_session)

        for author_id, name, works, cited, h_idx, expected_role in test_cases:
            # 创建标准化作者
            std_author = StdAuthor(
                openalex_author_id=author_id,
                name_normalized=name,
                works_count=works,
                cited_by_count=cited,
                h_index=h_idx,
                source_task_id=task.task_id,
                cs_concepts_score=0.8,  # CS background score
            )
            test_session.add(std_author)
            await test_session.flush()

            # 同步到服务层
            talent, is_new = await sync.sync_author_to_talent(std_author)

            # 验证角色
            assert talent.role_type == expected_role.value, \
                f"{name} 应该是 {expected_role.value}，实际是 {talent.role_type}"

            # 验证RoleProfile
            profile_result = await test_session.execute(
                select(RoleProfile).where(RoleProfile.talent_id == talent.talent_id)
            )
            profile = profile_result.scalar_one_or_none()
            assert profile is not None, "RoleProfile应该被创建"

        await test_session.commit()

    @pytest.mark.asyncio
    async def test_e2e_003_statistics_consistency(
        self,
        test_session: AsyncSession,
        e2e_setup
    ):
        """
        TC-E2E-003: 统计一致性验证

        验证：
        1. 技术要素统计与实际数据一致
        2. 国家分布统计正确
        """
        # 创建任务
        task = CollectTask(
            task_code="E2E-003",
            tech_element_id=e2e_setup["tech_element"].tech_element_id,
            collect_mode="full",
            status="completed",
            triggered_at=datetime.utcnow(),
        )
        test_session.add(task)
        await test_session.flush()

        # 创建多个作者
        for i in range(3):
            std_author = StdAuthor(
                openalex_author_id=f"A-E2E-STAT-{i}",
                name_normalized=f"Author {i}",
                works_count=20 + i * 5,
                cited_by_count=300 + i * 100,
                h_index=10 + i * 2,
                source_task_id=task.task_id,
                cs_concepts_score=0.8,  # CS background score
            )
            test_session.add(std_author)
            await test_session.flush()

            # 创建技术归属
            tech_belong = AuthorTechBelong(
                openalex_author_id=f"A-E2E-STAT-{i}",
                std_author_id=std_author.std_author_id,
                tech_element_id=e2e_setup["tech_element"].tech_element_id,
                source_venue_id=e2e_setup["venue"].venue_id,
            )
            test_session.add(tech_belong)

        await test_session.commit()

        # 同步
        sync = ServingLayerSync(test_session)
        result = await test_session.execute(
            select(StdAuthor).where(StdAuthor.source_task_id == task.task_id)
        )
        for author in result.scalars().all():
            await sync.sync_author_to_talent(author)
            # 创建技术标签
            belong_result = await test_session.execute(
                select(AuthorTechBelong).where(
                    AuthorTechBelong.std_author_id == author.std_author_id
                )
            )
            belongs = belong_result.scalars().all()
            if belongs:
                talent_result = await test_session.execute(
                    select(Talent).where(Talent.std_author_id == author.std_author_id)
                )
                talent = talent_result.scalar_one_or_none()
                if talent:
                    await sync.sync_talent_tech_tags(
                        talent, list(belongs),
                        e2e_setup["tech_direction"].tech_direction_id
                    )

        await test_session.commit()

        # 验证统计
        tech_repo = TechElementRepository(test_session)
        stats = await tech_repo.get_element_stats(
            e2e_setup["tech_element"].tech_element_id
        )

        assert stats["talent_count"] >= 3, "应该有3个人才"

        # 验证人才列表
        talents, total = await tech_repo.get_talent_list(
            element_id=e2e_setup["tech_element"].tech_element_id,
        )

        assert total >= 3, "人才列表应该有3条数据"


class TestRoleIdentifierE2E:
    """角色识别端到端测试"""

    @pytest.mark.asyncio
    async def test_professor_identification(self):
        """测试教授识别"""
        result = RoleIdentifier.identify(
            works_count=60,
            cited_by_count=3000,
            h_index=25
        )

        assert result.role_type == RoleType.PROFESSOR.value
        assert result.confidence >= 0.90

    @pytest.mark.asyncio
    async def test_student_identification(self):
        """测试学生识别"""
        result = RoleIdentifier.identify(
            works_count=5,
            cited_by_count=30,
            h_index=2
        )

        assert result.role_type == RoleType.STUDENT.value
        assert result.confidence >= 0.75

    @pytest.mark.asyncio
    async def test_graduate_identification(self):
        """测试毕业生识别"""
        result = RoleIdentifier.identify(
            works_count=15,
            cited_by_count=150,
            h_index=5
        )

        # 应该是毕业生或教授，取决于具体规则
        assert result.role_type in [
            RoleType.GRADUATE.value,
            RoleType.PROFESSOR.value,
        ]
