"""
Tests for UnifiedCollectService - 统一采集服务测试
====================================================

测试覆盖：
1. 任务创建流程
2. 数据采集流程
3. 标准化流程
4. 服务层同步流程
5. 完整任务执行流程
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.unified_collect_service import (
    UnifiedCollectService,
    CollectionProgress,
    CollectMode,
)
from app.services.serving_layer_sync import ServingLayerSync
from app.services.role_identifier import RoleIdentifier, RoleIdentificationResult

from app.models.sync import CollectTask
from app.repositories.tech_element_repository import TechElementRepository
from app.models.tech_element import TechElement, TechDirection, TalentTechTag
from app.models.venue import Venue, VenueTechBinding, VenueSubTask
from app.models.raw_data import RawWork, RawAuthor, RawInstitution, AuthorTechBelong
from app.models.standardized import StdAuthor, StdSchool
from app.models.talent import Talent
from app.models.school import School
from app.models.country import Country
from app.models.enums import RoleType


# ============ Fixtures ============

@pytest.fixture
def mock_session():
    """Create mock session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_fetchers():
    """Create mock data fetchers."""
    work_fetcher = AsyncMock()
    work_fetcher.fetch_works_from_venue = AsyncMock()

    author_fetcher = AsyncMock()
    author_fetcher.fetch_authors_by_ids = AsyncMock()

    institution_fetcher = AsyncMock()
    institution_fetcher.fetch_institutions_by_ids = AsyncMock()

    return {
        "work": work_fetcher,
        "author": author_fetcher,
        "institution": institution_fetcher,
    }


@pytest.fixture
def sample_raw_work():
    """Sample raw work data."""
    return RawWork(
        openalex_work_id="W123456",
        raw_json="{}",
        title="Test Paper",
        publication_year=2023,
        author_ids=json.dumps(["A1", "A2"]),
    )


@pytest.fixture
def sample_raw_author():
    """Sample raw author data."""
    return RawAuthor(
        openalex_author_id="A1",
        raw_json="{}",
        display_name="Test Author",
        works_count=20,
        cited_by_count=200,
        h_index=8,
    )


# ============ CollectionProgress Tests ============

class TestCollectionProgress:
    """测试 CollectionProgress 数据类"""

    def test_initial_state(self):
        """测试初始状态"""
        progress = CollectionProgress(task_id=1)

        assert progress.task_id == 1
        assert progress.status == "pending"
        assert progress.total_venues == 0
        assert progress.completed_venues == 0
        assert progress.errors == []

    def test_progress_update(self):
        """测试进度更新"""
        progress = CollectionProgress(task_id=1)

        progress.total_venues = 4
        progress.completed_venues = 2
        progress.total_works = 100
        progress.total_authors = 50

        assert progress.completed_venues == 2
        assert progress.total_works == 100

    def test_error_tracking(self):
        """测试错误追踪"""
        progress = CollectionProgress(task_id=1)

        progress.errors.append("API timeout")
        progress.errors.append("Rate limit exceeded")

        assert len(progress.errors) == 2
        assert "API timeout" in progress.errors


# ============ UnifiedCollectService Unit Tests ============

class TestUnifiedCollectServiceUnit:
    """UnifiedCollectService 单元测试"""

    def test_collect_mode_enum(self):
        """测试采集模式枚举"""
        assert CollectMode.FULL.value == "full"
        assert CollectMode.INCREMENTAL.value == "incremental"

    def test_time_window_full_mode(self, mock_session):
        """测试全量采集时间窗口"""
        service = UnifiedCollectService(mock_session)

        start, end = service._get_time_window("full")

        assert start.year == 2020  # FULL_COLLECTION_START_YEAR
        assert end <= datetime.utcnow()

    def test_time_window_incremental_mode(self, mock_session):
        """测试增量采集时间窗口"""
        service = UnifiedCollectService(mock_session)

        last_collect = datetime.utcnow() - timedelta(days=7)
        start, end = service._get_time_window("incremental", last_collect)

        # 增量模式应该从上次采集时间往前推30天
        expected_start = last_collect - timedelta(days=30)
        assert start.date() == expected_start.date()

    def test_log_tracking(self, mock_session):
        """测试日志追踪"""
        service = UnifiedCollectService(mock_session)

        service._add_log("info", "Task started")
        service._add_log("warning", "Rate limit approaching")
        service._add_log("error", "API failed", {"error": "timeout"})

        assert len(service._logs) == 3
        assert service._logs[0]["level"] == "info"
        assert service._logs[2]["details"]["error"] == "timeout"


# ============ Service Integration Tests ============

class TestUnifiedCollectServiceIntegration:
    """UnifiedCollectService 集成测试"""

    @pytest.fixture
    async def setup_data(self, test_session: AsyncSession):
        """Setup test data"""
        # 创建国家
        country = Country(
            country_code="US",
            country_name_cn="美国",
            country_name_en="United States",
            is_active=True,
        )
        test_session.add(country)

        # 创建技术要素
        tech_element = TechElement(
            element_code="AI",
            element_name="人工智能",
            element_name_en="Artificial Intelligence",
            is_enabled=True,
        )
        test_session.add(tech_element)
        await test_session.flush()

        # 创建技术方向
        tech_direction = TechDirection(
            tech_element_id=tech_element.tech_element_id,
            direction_code="ML",
            direction_name="机器学习",
            is_enabled=True,
        )
        test_session.add(tech_direction)

        # 创建Venue
        venue = Venue(
            venue_code="TEST-VENUE",
            venue_name="Test Conference",
            venue_type="conference",
            openalex_source_id="S123456",
            is_enabled=True,
        )
        test_session.add(venue)
        await test_session.flush()

        # 创建绑定
        binding = VenueTechBinding(
            venue_id=venue.venue_id,
            tech_element_id=tech_element.tech_element_id,
            is_enabled=True,
        )
        test_session.add(binding)

        await test_session.commit()

        return {
            "country": country,
            "tech_element": tech_element,
            "tech_direction": tech_direction,
            "venue": venue,
            "binding": binding,
        }

    @pytest.mark.asyncio
    async def test_create_task_flow(
        self,
        test_session: AsyncSession,
        setup_data
    ):
        """
        测试任务创建流程

        验证：
        1. 任务正确创建
        2. VenueSubTask 正确创建
        3. 时间窗口正确设置
        """
        service = UnifiedCollectService(test_session)

        # 创建任务
        task = await service.create_task(
            tech_element_id=setup_data["tech_element"].tech_element_id,
            mode="full",
            triggered_by=1,
        )

        assert task.task_id is not None
        assert task.tech_element_id == setup_data["tech_element"].tech_element_id
        assert task.collect_mode == "full"
        assert task.status == "pending"

        # 验证 VenueSubTask 创建
        from app.repositories.venue_repository import VenueSubTaskRepository
        sub_task_repo = VenueSubTaskRepository(test_session)
        sub_tasks = await sub_task_repo.get_by_task(task.task_id)

        assert len(sub_tasks) == 1
        assert sub_tasks[0].venue_id == setup_data["venue"].venue_id
        assert sub_tasks[0].status == "pending"

    @pytest.mark.asyncio
    async def test_get_task_progress(
        self,
        test_session: AsyncSession,
        setup_data
    ):
        """测试获取任务进度"""
        service = UnifiedCollectService(test_session)

        # 创建任务
        task = await service.create_task(
            tech_element_id=setup_data["tech_element"].tech_element_id,
            mode="incremental",
        )

        # 获取进度
        progress = await service.get_task_progress(task.task_id)

        assert progress["task_id"] == task.task_id
        assert progress["status"] == "pending"
        assert progress["progress_percent"] == 0

    @pytest.mark.asyncio
    async def test_get_default_tech_direction(
        self,
        test_session: AsyncSession,
        setup_data
    ):
        """测试获取默认技术方向"""
        service = UnifiedCollectService(test_session)

        direction_id = await service._get_default_tech_direction(
            setup_data["tech_element"].tech_element_id
        )

        assert direction_id == setup_data["tech_direction"].tech_direction_id

    @pytest.mark.asyncio
    async def test_execute_task_with_orchestrator(
        self,
        test_session: AsyncSession,
        setup_data
    ):
        """测试使用 CollectionOrchestrator 执行任务

        注意：这个测试验证 execute_task 方法的执行流程，
        但不实际调用 OpenAlex API（fetchers 是 mock 的）。
        """
        from app.services.collect.orchestrator import CollectionOrchestrator
        from unittest.mock import AsyncMock

        # 创建 mock fetchers
        mock_work_fetcher = AsyncMock()
        mock_work_fetcher.fetch_works_from_venue = AsyncMock(return_value=AsyncMock(fetched=0))
        mock_work_fetcher.get_work_count_from_venue = AsyncMock(return_value=0)  # 返回整数而非 AsyncMock

        mock_author_fetcher = AsyncMock()
        mock_author_fetcher.fetch_authors_by_ids = AsyncMock(return_value=AsyncMock(fetched=0))

        mock_institution_fetcher = AsyncMock()
        mock_institution_fetcher.fetch_institutions_by_ids = AsyncMock(return_value=AsyncMock(fetched=0))

        # 创建任务
        service = UnifiedCollectService(test_session)
        task = await service.create_task(
            tech_element_id=setup_data["tech_element"].tech_element_id,
            mode="incremental",
        )
        await test_session.commit()

        # 使用 orchestrator 执行（带 mock fetchers）
        orchestrator = CollectionOrchestrator(
            test_session,
            work_fetcher=mock_work_fetcher,
            author_fetcher=mock_author_fetcher,
            institution_fetcher=mock_institution_fetcher
        )
        progress = await orchestrator.execute_task(task.task_id)

        # 验证执行结果
        assert progress.status == "completed"
        assert len(progress.errors) == 0  # 没有错误

        # 验证任务状态已更新
        from sqlalchemy import select
        from app.models.sync import CollectTask
        result = await test_session.execute(
            select(CollectTask).where(CollectTask.task_id == task.task_id)
        )
        updated_task = result.scalar_one_or_none()
        assert updated_task.status == "completed"
        assert updated_task.started_at is not None
        assert updated_task.completed_at is not None


# ============ ServingLayerSync Tests ============

class TestServingLayerSync:
    """服务层同步测试"""

    @pytest.fixture
    async def setup_sync_data(self, test_session: AsyncSession):
        """Setup data for sync tests"""
        # 创建国家
        country = Country(
            country_code="US",
            country_name_cn="美国",
            country_name_en="United States",
            is_active=True,
        )
        test_session.add(country)
        await test_session.flush()

        # 创建技术要素和方向
        tech_element = TechElement(
            element_code="SYNC-TEST",
            element_name="同步测试",
            is_enabled=True,
        )
        test_session.add(tech_element)
        await test_session.flush()

        tech_direction = TechDirection(
            tech_element_id=tech_element.tech_element_id,
            direction_code="SYNC-DIR",
            direction_name="同步方向",
            is_enabled=True,
        )
        test_session.add(tech_direction)
        await test_session.flush()

        # 创建标准化学校
        std_school = StdSchool(
            openalex_institution_id="I-SYNC",
            name_normalized="Sync Test University",
            country_code="US",
            source_task_id=1,
        )
        test_session.add(std_school)
        await test_session.flush()

        # 创建标准化作者
        std_author = StdAuthor(
            openalex_author_id="A-SYNC",
            name_normalized="Sync Test Author",
            works_count=30,
            cited_by_count=500,
            h_index=16,  # h_index >= 15 with works >= 30 triggers professor
            std_school_id=std_school.std_school_id,
            source_task_id=1,
            cs_concepts_score=0.8,  # CS background score
        )
        test_session.add(std_author)
        await test_session.flush()

        await test_session.commit()

        return {
            "country": country,
            "tech_element": tech_element,
            "tech_direction": tech_direction,
            "std_school": std_school,
            "std_author": std_author,
        }

    @pytest.mark.asyncio
    async def test_sync_author_to_talent_new(
        self,
        test_session: AsyncSession,
        setup_sync_data
    ):
        """测试同步新作者到 Talent"""
        sync = ServingLayerSync(test_session)

        talent, is_new = await sync.sync_author_to_talent(
            setup_sync_data["std_author"],
            update_existing=True,
        )

        assert is_new is True
        assert talent.name == "Sync Test Author"
        assert talent.source_record_id == "A-SYNC"
        assert talent.role_type in [
            RoleType.PROFESSOR.value,
            RoleType.STUDENT.value,
            RoleType.GRADUATE.value,
        ]

    @pytest.mark.asyncio
    async def test_sync_author_to_talent_update(
        self,
        test_session: AsyncSession,
        setup_sync_data
    ):
        """测试更新现有作者"""
        sync = ServingLayerSync(test_session)

        # 第一次同步（创建）
        talent1, is_new1 = await sync.sync_author_to_talent(
            setup_sync_data["std_author"],
        )
        await test_session.commit()

        # 更新标准化作者
        setup_sync_data["std_author"].works_count = 40
        setup_sync_data["std_author"].h_index = 15
        await test_session.commit()

        # 第二次同步（更新）
        talent2, is_new2 = await sync.sync_author_to_talent(
            setup_sync_data["std_author"],
            update_existing=True,
        )

        assert is_new2 is False
        assert talent2.talent_id == talent1.talent_id
        assert talent2.works_count == 40
        assert talent2.h_index == 15

    @pytest.mark.asyncio
    async def test_sync_school_to_school(
        self,
        test_session: AsyncSession,
        setup_sync_data
    ):
        """测试同步学校"""
        sync = ServingLayerSync(test_session)

        school, is_new = await sync.sync_school_to_school(
            setup_sync_data["std_school"],
        )

        assert school is not None
        assert school.school_name == "Sync Test University"
        assert school.source_record_id == "I-SYNC"

    @pytest.mark.asyncio
    async def test_sync_talent_tech_tags(
        self,
        test_session: AsyncSession,
        setup_sync_data
    ):
        """测试同步技术标签"""
        sync = ServingLayerSync(test_session)

        # 创建Talent
        talent = Talent(
            source_type="openalex",
            source_record_id="A-TAG-TEST",
            name="Tag Test Author",
            role_type=RoleType.PROFESSOR.value,
        )
        test_session.add(talent)
        await test_session.flush()

        # 创建技术归属
        belong = AuthorTechBelong(
            openalex_author_id="A-SYNC",  # Required field
            std_author_id=setup_sync_data["std_author"].std_author_id,
            tech_element_id=setup_sync_data["tech_element"].tech_element_id,
            source_venue_id=1,
            work_count_in_venue=5,
        )
        test_session.add(belong)
        await test_session.flush()

        # 同步标签
        count = await sync.sync_talent_tech_tags(
            talent,
            [belong],
            setup_sync_data["tech_direction"].tech_direction_id,
        )

        assert count == 1

        # 验证标签创建
        result = await test_session.execute(
            select(TalentTechTag).where(
                TalentTechTag.talent_id == talent.talent_id
            )
        )
        tag = result.scalar_one_or_none()
        assert tag is not None
        assert tag.tech_element_id == setup_sync_data["tech_element"].tech_element_id


# ============ RoleIdentifier Tests ============

class TestRoleIdentifier:
    """角色识别测试"""

    def test_identify_professor_high_confidence(self):
        """测试高置信度教授识别"""
        result = RoleIdentifier.identify(
            works_count=60,
            cited_by_count=3000,
            h_index=25
        )

        assert result.role_type == RoleType.PROFESSOR.value
        assert result.confidence >= 0.90

    def test_identify_professor_medium_confidence(self):
        """测试中等置信度教授识别

        Note: Professor requires either:
        - h_index >= 25, OR
        - works >= 50 && cited >= 2000, OR
        - works >= 30 && h_index >= 15
        """
        result = RoleIdentifier.identify(
            works_count=35,
            cited_by_count=800,
            h_index=16  # Works >= 30 && h_index >= 15 triggers professor
        )

        assert result.role_type == RoleType.PROFESSOR.value
        assert result.confidence >= 0.80

    def test_identify_student(self):
        """测试学生识别"""
        result = RoleIdentifier.identify(
            works_count=5,
            cited_by_count=30,
            h_index=2
        )

        assert result.role_type == RoleType.STUDENT.value
        assert result.confidence >= 0.75

    def test_identify_graduated(self):
        """测试已毕业识别"""
        result = RoleIdentifier.identify(
            works_count=12,
            cited_by_count=150,
            h_index=5
        )

        # 已毕业或教授，取决于具体规则
        assert result.role_type in [
            RoleType.GRADUATE.value,
            RoleType.PROFESSOR.value,
        ]

    def test_identify_with_reason(self):
        """测试识别原因"""
        result = RoleIdentifier.identify(
            works_count=50,
            cited_by_count=1000,
            h_index=20
        )

        assert result.reason is not None
        assert len(result.reason) > 0


# ============ End-to-End Flow Tests ============

class TestEndToEndFlow:
    """端到端流程测试"""

    @pytest.fixture
    async def full_setup(self, test_session: AsyncSession):
        """Complete setup for end-to-end tests"""
        # 国家
        country = Country(
            country_code="US",
            country_name_cn="美国",
            is_active=True,
        )
        test_session.add(country)
        await test_session.flush()

        # 技术要素
        tech_element = TechElement(
            element_code="E2E",
            element_name="端到端测试",
            is_enabled=True,
        )
        test_session.add(tech_element)
        await test_session.flush()

        # 技术方向
        tech_direction = TechDirection(
            tech_element_id=tech_element.tech_element_id,
            direction_code="E2E-DIR",
            direction_name="端到端方向",
            is_enabled=True,
        )
        test_session.add(tech_direction)

        # Venue
        venue = Venue(
            venue_code="E2E-VENUE",
            venue_name="E2E Conference",
            venue_type="conference",
            openalex_source_id="S-E2E",
            is_enabled=True,
        )
        test_session.add(venue)
        await test_session.flush()

        # 绑定
        binding = VenueTechBinding(
            venue_id=venue.venue_id,
            tech_element_id=tech_element.tech_element_id,
            is_enabled=True,
        )
        test_session.add(binding)

        await test_session.commit()

        return {
            "country": country,
            "tech_element": tech_element,
            "tech_direction": tech_direction,
            "venue": venue,
        }

    @pytest.mark.asyncio
    async def test_complete_collection_flow(
        self,
        test_session: AsyncSession,
        full_setup
    ):
        """
        测试完整的采集流程（模拟）

        注意：这个测试不实际调用OpenAlex API，
        而是模拟数据流来验证流程正确性。
        """
        # 1. 创建任务
        service = UnifiedCollectService(test_session)
        task = await service.create_task(
            tech_element_id=full_setup["tech_element"].tech_element_id,
            mode="incremental",
            triggered_by=1,
        )
        await test_session.commit()

        assert task.status == "pending"

        # 2. 模拟Raw数据创建
        raw_work = RawWork(
            openalex_work_id="W-E2E",
            raw_json="{}",
            title="E2E Test Paper",
            publication_year=2024,
            author_ids=json.dumps(["A-E2E"]),
            source_id=full_setup["venue"].openalex_source_id,
            fetch_task_id=task.task_id,
        )
        test_session.add(raw_work)

        raw_author = RawAuthor(
            openalex_author_id="A-E2E",
            raw_json="{}",
            display_name="E2E Author",
            works_count=15,
            cited_by_count=100,
            h_index=6,
            fetch_task_id=task.task_id,
        )
        test_session.add(raw_author)
        await test_session.commit()

        # 3. 模拟标准化
        std_school = StdSchool(
            openalex_institution_id="I-E2E",
            name_normalized="E2E University",
            country_code="US",
            source_task_id=task.task_id,
        )
        test_session.add(std_school)
        await test_session.flush()

        std_author = StdAuthor(
            openalex_author_id="A-E2E",
            name_normalized="E2E Author",
            works_count=15,
            cited_by_count=100,
            h_index=6,
            std_school_id=std_school.std_school_id,
            source_task_id=task.task_id,
            cs_concepts_score=0.8,  # CS background score
        )
        test_session.add(std_author)
        await test_session.flush()

        # 4. 创建技术归属
        tech_belong = AuthorTechBelong(
            openalex_author_id="A-E2E",  # Required field
            std_author_id=std_author.std_author_id,
            tech_element_id=full_setup["tech_element"].tech_element_id,
            source_venue_id=full_setup["venue"].venue_id,
            source_task_id=task.task_id,  # Required for sync
            work_count_in_venue=1,
        )
        test_session.add(tech_belong)
        await test_session.commit()

        # 5. 同步到服务层
        sync = ServingLayerSync(test_session)
        stats = await sync.sync_all_for_task(
            task_id=task.task_id,
            tech_element_id=full_setup["tech_element"].tech_element_id,
            default_tech_direction_id=full_setup["tech_direction"].tech_direction_id,
        )
        await test_session.commit()

        # 6. 验证结果
        assert stats["authors_synced"] >= 1
        assert stats["tags_created"] >= 1

        # 验证Talent创建
        result = await test_session.execute(
            select(Talent).where(Talent.source_record_id == "A-E2E")
        )
        talent = result.scalar_one_or_none()
        assert talent is not None
        assert talent.name == "E2E Author"

        # 验证TechTag创建
        result = await test_session.execute(
            select(TalentTechTag).where(
                TalentTechTag.talent_id == talent.talent_id
            )
        )
        tag = result.scalar_one_or_none()
        assert tag is not None
        assert tag.tech_element_id == full_setup["tech_element"].tech_element_id

    @pytest.mark.asyncio
    async def test_data_consistency_after_collection(
        self,
        test_session: AsyncSession,
        full_setup
    ):
        """
        测试采集后数据一致性

        验证：
        1. Talent与StdAuthor正确关联
        2. Talent与School正确关联
        3. TalentTechTag正确创建
        4. 统计数据正确
        """
        # 创建基础数据
        std_school = StdSchool(
            openalex_institution_id="I-CONSIST",
            name_normalized="Consistency University",
            country_code="US",
            source_task_id=1,
        )
        test_session.add(std_school)
        await test_session.flush()

        std_author = StdAuthor(
            openalex_author_id="A-CONSIST",
            name_normalized="Consistency Author",
            works_count=25,
            cited_by_count=300,
            h_index=10,
            std_school_id=std_school.std_school_id,
            source_task_id=1,
            cs_concepts_score=0.8,  # CS background score
        )
        test_session.add(std_author)
        await test_session.flush()

        # 同步
        sync = ServingLayerSync(test_session)
        talent, _ = await sync.sync_author_to_talent(std_author)

        # 创建技术归属和标签
        tech_belong = AuthorTechBelong(
            openalex_author_id="A-CONSIST",  # Required field
            std_author_id=std_author.std_author_id,
            tech_element_id=full_setup["tech_element"].tech_element_id,
            source_venue_id=full_setup["venue"].venue_id,
        )
        test_session.add(tech_belong)
        await test_session.flush()

        await sync.sync_talent_tech_tags(
            talent,
            [tech_belong],
            full_setup["tech_direction"].tech_direction_id,
        )
        await test_session.commit()

        # 验证一致性
        # 1. Talent -> StdAuthor
        assert talent.std_author_id == std_author.std_author_id

        # 2. 查询技术要素下的人才
        tech_repo = TechElementRepository(test_session)
        talents, total = await tech_repo.get_talent_list(
            element_id=full_setup["tech_element"].tech_element_id,
        )

        assert total >= 1
        assert any(t.name == "Consistency Author" for t in talents)

        # 3. 验证统计
        stats = await tech_repo.get_element_stats(
            full_setup["tech_element"].tech_element_id
        )
        assert stats["talent_count"] >= 1
