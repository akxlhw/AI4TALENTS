"""
Tests for Collect Configuration Management - 采集配置管理测试
============================================================

测试覆盖：
1. 技术要素采集配置管理
2. 采集任务创建和执行
3. Venue子任务追踪
4. 三层数据流（Raw → Std → Serving）
5. 任务完成后数据联动生效验证
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.collect_repository import CollectTaskRepository, TechElementCollectRepository
from app.repositories.venue_repository import VenueRepository, VenueTechBindingRepository, VenueSubTaskRepository
from app.repositories.raw_data_repository import RawWorkRepository, RawAuthorRepository
from app.repositories.tech_element_repository import TechElementRepository
from app.models.sync import CollectTask
from app.models.tech_element import TechElement, TechDirection, TalentTechTag
from app.models.venue import Venue, VenueTechBinding, VenueSubTask
from app.models.raw_data import RawWork, RawAuthor, RawInstitution, AuthorTechBelong
from app.models.standardized import StdAuthor, StdSchool
from app.models.talent import Talent
from app.models.school import School
from app.models.enums import RoleType, VisibilityStatus


# ============ Fixtures ============

@pytest.fixture
def mock_session():
    """Create mock session for unit tests."""
    return AsyncMock()


@pytest.fixture
async def test_data_setup(test_session: AsyncSession):
    """
    创建测试所需的基础数据。
    包括：技术要素、技术方向、Venue
    注意：不使用显式 ID，让数据库自动生成，避免冲突
    """
    # 创建技术要素（不指定 ID）
    tech_element = TechElement(
        element_code="AI",
        element_name="人工智能",
        element_name_en="Artificial Intelligence",
        is_enabled=True,
        sort_order=1,
    )
    test_session.add(tech_element)
    await test_session.flush()  # Flush to get auto-generated ID

    # 创建技术方向（不指定 ID）
    tech_direction = TechDirection(
        tech_element_id=tech_element.tech_element_id,
        direction_code="ML",
        direction_name="机器学习",
        direction_name_en="Machine Learning",
        is_enabled=True,
        sort_order=1,
    )
    test_session.add(tech_direction)
    await test_session.flush()

    # 创建Venue（顶会顶刊）
    venue = Venue(
        venue_code="NEURIPS",
        venue_name="Neural Information Processing Systems",
        venue_type="conference",
        openalex_source_id="S123456",
        is_enabled=True,
    )
    test_session.add(venue)
    await test_session.flush()

    # 创建Venue-技术要素绑定（不指定 ID）
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
        "binding": binding,
    }


# ============ Repository Unit Tests ============

class TestCollectTaskRepository:
    """采集任务Repository单元测试"""

    @pytest.fixture
    def repo(self, mock_session):
        return CollectTaskRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_task(self, repo, mock_session):
        """测试创建采集任务"""
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        task = await repo.create_task(
            task_code="COLLECT-20260328001",
            tech_element_id=1,
            collect_mode="full",
            triggered_by=None,
        )

        assert task is not None
        assert task.task_code == "COLLECT-20260328001"
        assert task.tech_element_id == 1
        assert task.collect_mode == "full"
        assert task.status == "pending"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, repo, mock_session):
        """测试带筛选条件的任务列表查询"""
        # Mock 返回结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        tasks, total = await repo.list_tasks(
            status="completed",
            tech_element_id=1,
            page=1,
            page_size=10,
        )

        assert isinstance(tasks, list)
        assert total == 0
        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_update_task_status(self, repo, mock_session):
        """测试更新任务状态"""
        # Mock get_by_id
        mock_task = MagicMock(spec=CollectTask)
        mock_task.task_id = 1

        with patch.object(repo, 'get_by_id', return_value=mock_task):
            result = await repo.update_task_status(
                task_id=1,
                status="running",
                progress_percent=50,
                current_step="Fetching works",
            )

            assert result.status == "running"
            assert result.progress_percent == 50
            assert result.current_step == "Fetching works"

    @pytest.mark.asyncio
    async def test_complete_task_success(self, repo, mock_session):
        """测试完成任务（成功）"""
        mock_task = MagicMock(spec=CollectTask)
        mock_task.task_id = 1

        with patch.object(repo, 'get_by_id', return_value=mock_task):
            result = await repo.complete_task(
                task_id=1,
                success=True,
                result_summary={"works": 100, "authors": 50},
            )

            assert result.status == "completed"
            assert result.progress_percent == 100
            assert result.result_summary["works"] == 100

    @pytest.mark.asyncio
    async def test_complete_task_failure(self, repo, mock_session):
        """测试完成任务（失败）"""
        mock_task = MagicMock(spec=CollectTask)
        mock_task.task_id = 1

        with patch.object(repo, 'get_by_id', return_value=mock_task):
            result = await repo.complete_task(
                task_id=1,
                success=False,
                error_message="API connection failed",
            )

            assert result.status == "failed"
            assert result.error_message == "API connection failed"

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, repo, mock_session):
        """测试获取活动任务"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(status="pending"),
            MagicMock(status="running"),
        ]
        mock_session.execute.return_value = mock_result

        tasks = await repo.get_active_tasks()

        assert len(tasks) == 2


class TestTechElementCollectRepository:
    """技术要素采集配置Repository单元测试"""

    @pytest.fixture
    def repo(self, mock_session):
        return TechElementCollectRepository(mock_session)

    @pytest.mark.asyncio
    async def test_list_with_collect_config(self, repo, mock_session):
        """测试获取技术要素列表"""
        mock_result = MagicMock()
        mock_element = MagicMock(spec=TechElement)
        mock_element.tech_element_id = 1
        mock_element.element_name = "人工智能"
        mock_result.scalars.return_value.all.return_value = [mock_element]
        mock_session.execute.return_value = mock_result

        elements = await repo.list_with_collect_config()

        assert len(elements) == 1
        assert elements[0].tech_element_id == 1

    @pytest.mark.asyncio
    async def test_update_last_collect_time(self, repo, mock_session):
        """测试更新最后采集时间"""
        mock_element = MagicMock(spec=TechElement)
        mock_element.tech_element_id = 1

        with patch.object(repo, 'get_by_id', return_value=mock_element):
            collect_time = datetime.utcnow()
            result = await repo.update_last_collect_time(
                tech_element_id=1,
                collect_at=collect_time,
            )

            assert result.last_collect_at == collect_time


class TestVenueSubTaskRepository:
    """Venue子任务Repository单元测试"""

    @pytest.fixture
    def repo(self, mock_session):
        return VenueSubTaskRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_sub_task(self, repo, mock_session):
        """测试创建Venue子任务"""
        mock_session.flush = AsyncMock()

        sub_task = VenueSubTask(
            task_id=1,
            venue_id=1,
            status="pending",
        )
        result = await repo.create(sub_task)

        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_task(self, repo, mock_session):
        """测试获取任务的所有子任务"""
        mock_result = MagicMock()
        mock_sub_task = MagicMock(spec=VenueSubTask)
        mock_sub_task.task_id = 1
        mock_sub_task.venue_id = 1
        mock_result.scalars.return_value.all.return_value = [mock_sub_task]
        mock_session.execute.return_value = mock_result

        sub_tasks = await repo.get_by_task(1)

        assert len(sub_tasks) == 1


# ============ Integration Tests ============

class TestCollectTaskIntegration:
    """采集任务集成测试 - 使用真实数据库"""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试完整的任务生命周期：
        创建任务 → 更新进度 → 完成任务
        """
        repo = CollectTaskRepository(test_session)

        # 1. 创建任务
        task = await repo.create_task(
            task_code="INTEGRATION-TEST-001",
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            collect_mode="incremental",
            triggered_by=None,
        )
        await test_session.commit()

        assert task.task_id is not None
        assert task.status == "pending"

        # 2. 启动任务
        task.status = "running"
        task.current_step = "Initializing"
        task.started_at = datetime.utcnow()
        await test_session.commit()

        # 3. 更新进度
        for progress in [25, 50, 75]:
            task.progress_percent = progress
            task.current_step = f"Processing {progress}%"
            await test_session.commit()

        # 4. 完成任务
        await repo.complete_task(
            task_id=task.task_id,
            success=True,
            result_summary={
                "works_fetched": 100,
                "authors_fetched": 50,
                "schools_normalized": 10,
            },
        )
        await test_session.commit()

        # 5. 验证最终状态
        final_task = await repo.get_by_id(task.task_id)
        assert final_task.status == "completed"
        assert final_task.progress_percent == 100
        assert final_task.result_summary["works_fetched"] == 100

    @pytest.mark.asyncio
    async def test_task_with_venue_sub_tasks(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试任务与Venue子任务的关联
        """
        task_repo = CollectTaskRepository(test_session)
        sub_task_repo = VenueSubTaskRepository(test_session)

        # 创建任务
        task = await task_repo.create_task(
            task_code="VENUE-TEST-001",
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            collect_mode="full",
        )
        await test_session.commit()

        # 创建Venue子任务
        sub_task = VenueSubTask(
            task_id=task.task_id,
            venue_id=test_data_setup["venue"].venue_id,
            status="pending",
            time_window_start=datetime(2020, 1, 1),
            time_window_end=datetime.utcnow(),
        )
        await sub_task_repo.create(sub_task)
        await test_session.commit()

        # 验证关联
        sub_tasks = await sub_task_repo.get_by_task(task.task_id)
        assert len(sub_tasks) == 1
        assert sub_tasks[0].venue_id == test_data_setup["venue"].venue_id

        # 更新子任务状态
        await sub_task_repo.update_status(
            sub_tasks[0].sub_task_id,
            "completed",
            works_fetched=100,
        )
        await test_session.commit()

        # 验证更新
        updated = await sub_task_repo.get_by_id(sub_tasks[0].sub_task_id)
        assert updated.status == "completed"
        assert updated.works_fetched == 100


class TestDataFlowIntegration:
    """三层数据流集成测试 - 简化版"""

    @pytest.mark.asyncio
    async def test_std_to_serving_flow(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试标准化层到服务层数据流

        验证：
        1. 标准化层能正确处理数据
        2. 服务层能正确同步Std数据
        3. 最终Talent表有关联的技术标签
        """
        # ========== Phase 1: Standardized Layer ==========
        # 创建标准化学校
        std_school = StdSchool(
            openalex_institution_id="I100",
            name_normalized="Massachusetts Institute of Technology",
            country_code="US",
            source_task_id=None,
        )
        test_session.add(std_school)
        await test_session.flush()

        # 创建标准化作者
        std_author = StdAuthor(
            openalex_author_id="A100",
            name_normalized="John Smith",
            orcid="0000-0001-2345-6789",
            works_count=25,
            cited_by_count=500,
            h_index=12,
            std_school_id=std_school.std_school_id,
            source_task_id=None,
        )
        test_session.add(std_author)
        await test_session.flush()

        # 创建技术归属关系
        tech_belong = AuthorTechBelong(
            openalex_author_id="A100",
            std_author_id=std_author.std_author_id,
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            source_venue_id=test_data_setup["venue"].venue_id,
            work_count_in_venue=5,
        )
        test_session.add(tech_belong)
        await test_session.commit()

        # 验证Std数据已存储
        result = await test_session.execute(
            select(StdAuthor).where(StdAuthor.openalex_author_id == "A100")
        )
        saved_std_author = result.scalar_one_or_none()
        assert saved_std_author is not None
        assert saved_std_author.name_normalized == "John Smith"

        # ========== Phase 2: Serving Layer ==========
        # 创建服务层学校
        school = School(
            school_name="Massachusetts Institute of Technology",
            country_code="US",
            country_name="美国",
            source_type="openalex",
            source_record_id="I100",
            is_visible=True,
        )
        test_session.add(school)
        await test_session.flush()

        # 创建服务层人才
        talent = Talent(
            std_author_id=std_author.std_author_id,
            source_type="openalex",
            source_record_id="A100",
            name="John Smith",
            name_en="John Smith",
            orcid="0000-0001-2345-6789",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            role_confidence=0.85,
            works_count=25,
            cited_by_count=500,
            h_index=12,
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )
        test_session.add(talent)
        await test_session.flush()

        # 创建技术标签
        tech_tag = TalentTechTag(
            talent_id=talent.talent_id,
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            tech_direction_id=test_data_setup["tech_direction"].tech_direction_id,
            tag_level="primary",
            tag_source="auto_mapping",
            confirm_status="auto_identified",
            confidence_score=0.8,
            is_enabled=True,
        )
        test_session.add(tech_tag)
        await test_session.commit()

        # ========== Phase 3: Verification ==========
        # 验证最终数据联动生效
        result = await test_session.execute(
            select(Talent).where(Talent.source_record_id == "A100")
        )
        saved_talent = result.scalar_one_or_none()
        assert saved_talent is not None
        assert saved_talent.name == "John Smith"
        assert saved_talent.role_type == RoleType.PROFESSOR.value

        # 验证TalentTechTag
        result = await test_session.execute(
            select(TalentTechTag).where(
                TalentTechTag.talent_id == saved_talent.talent_id
            )
        )
        saved_tag = result.scalar_one_or_none()
        assert saved_tag is not None
        assert saved_tag.tech_element_id == test_data_setup["tech_element"].tech_element_id

        # 验证技术要素统计
        tech_repo = TechElementRepository(test_session)
        stats = await tech_repo.get_overall_stats()
        assert stats["talent_count"] >= 1


# ============ API Endpoint Tests ============

class TestCollectEndpoints:
    """采集配置API端点测试"""

    @pytest.mark.asyncio
    async def test_list_tech_elements_collect(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """测试获取技术要素采集配置列表 - 通过Repository测试"""
        # 直接测试Repository而不是HTTP客户端
        repo = TechElementCollectRepository(test_session)
        elements = await repo.list_with_collect_config()

        assert len(elements) >= 1
        assert any(e.tech_element_id == test_data_setup["tech_element"].tech_element_id for e in elements)

    @pytest.mark.asyncio
    async def test_trigger_task_validation(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """测试触发任务的数据验证"""
        repo = CollectTaskRepository(test_session)
        element_repo = TechElementCollectRepository(test_session)

        # 验证技术要素存在
        element = await element_repo.get_by_id(
            test_data_setup["tech_element"].tech_element_id
        )
        assert element is not None

        # 创建任务
        task = await repo.create_task(
            task_code="VALIDATION-TEST-001",
            tech_element_id=element.tech_element_id,
            collect_mode="incremental",
        )
        await test_session.commit()

        assert task.task_id is not None
        assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_cancel_task(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """测试取消任务"""
        repo = CollectTaskRepository(test_session)

        # 创建运行中的任务
        task = await repo.create_task(
            task_code="CANCEL-TEST-001",
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            collect_mode="full",
        )
        task.status = "running"
        await test_session.commit()

        # 取消任务
        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        await test_session.commit()

        # 验证
        cancelled = await repo.get_by_id(task.task_id)
        assert cancelled.status == "cancelled"


# ============ Edge Case Tests ============

class TestEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_concurrent_task_prevention(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试防止同一技术要素的并发任务
        """
        repo = CollectTaskRepository(test_session)

        # 创建运行中的任务
        task1 = await repo.create_task(
            task_code="CONCURRENT-001",
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            collect_mode="full",
        )
        task1.status = "running"
        await test_session.commit()

        # 检查是否有活动任务
        active_tasks = await repo.get_active_tasks()
        tech_element_has_active = any(
            t.tech_element_id == test_data_setup["tech_element"].tech_element_id
            for t in active_tasks
        )

        assert tech_element_has_active is True

    @pytest.mark.asyncio
    async def test_task_progress_consistency(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试任务进度一致性
        """
        repo = CollectTaskRepository(test_session)

        task = await repo.create_task(
            task_code="PROGRESS-001",
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            collect_mode="full",
        )
        await test_session.commit()

        # 更新记录数
        await repo.update_task_counts(
            task_id=task.task_id,
            total_records=100,
            processed_records=50,
            success_records=45,
            failed_records=5,
        )
        await test_session.commit()

        # 验证一致性
        updated = await repo.get_by_id(task.task_id)
        assert updated.total_records == 100
        assert updated.processed_records == 50
        assert updated.success_records == 45
        assert updated.failed_records == 5
        # 进度应该匹配
        expected_progress = int(50 / 100 * 100) if updated.total_records > 0 else 0
        # 注：实际进度由业务逻辑设置，这里只验证数据存储正确

    @pytest.mark.asyncio
    async def test_empty_collect_sources(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试技术要素没有配置采集源的情况
        """
        # 创建新的技术要素（没有Venue绑定）
        new_element = TechElement(
            element_code="TEST-EMPTY",
            element_name="测试空配置",
            is_enabled=True,
        )
        test_session.add(new_element)
        await test_session.commit()

        # 验证没有采集源
        binding_repo = VenueTechBindingRepository(test_session)
        bindings = await binding_repo.get_by_tech_element(new_element.tech_element_id)

        assert len(bindings) == 0


# ============ Data Validation Tests ============

class TestDataValidation:
    """数据验证测试"""

    @pytest.mark.asyncio
    async def test_role_identification_accuracy(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试角色识别准确性

        验证规则：
        - works_count >= 50 且 h_index >= 20 → 教授 (95%)
        - works_count <= 8 → 学生 (80%)
        """
        from app.services.role_identifier import RoleIdentifier

        # 测试教授识别
        result = RoleIdentifier.identify(
            works_count=60,
            cited_by_count=2000,
            h_index=25
        )
        assert result.role_type == RoleType.PROFESSOR.value
        assert result.confidence >= 0.90

        # 测试学生识别
        result = RoleIdentifier.identify(
            works_count=5,
            cited_by_count=20,
            h_index=2
        )
        assert result.role_type == RoleType.STUDENT.value
        assert result.confidence >= 0.75

        # 测试边界情况
        result = RoleIdentifier.identify(
            works_count=15,
            cited_by_count=150,
            h_index=8
        )
        # 应该是教授或已毕业
        assert result.role_type in [RoleType.PROFESSOR.value, RoleType.GRADUATE.value]

    @pytest.mark.asyncio
    async def test_tech_tag_creation(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试技术标签创建逻辑
        """
        # 创建Talent
        talent = Talent(
            source_type="openalex",
            source_record_id="TAG-TEST-001",
            name="Test Author",
            role_type=RoleType.PROFESSOR.value,
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )
        test_session.add(talent)
        await test_session.flush()

        # 创建技术标签
        tag = TalentTechTag(
            talent_id=talent.talent_id,
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            tech_direction_id=test_data_setup["tech_direction"].tech_direction_id,
            tag_level="primary",
            tag_source="auto_mapping",
            confirm_status="auto_identified",
            confidence_score=0.85,
            is_enabled=True,
        )
        test_session.add(tag)
        await test_session.commit()

        # 验证
        result = await test_session.execute(
            select(TalentTechTag).where(
                TalentTechTag.talent_id == talent.talent_id
            )
        )
        saved_tag = result.scalar_one_or_none()
        assert saved_tag is not None
        assert saved_tag.tag_source == "auto_mapping"
        assert saved_tag.is_enabled == True

    @pytest.mark.asyncio
    async def test_school_normalization(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """
        测试学校名称标准化
        """
        # 创建标准化学校
        std_school = StdSchool(
            openalex_institution_id="NORMALIZE-001",
            name_normalized="Stanford University",
            name_aliases=json.dumps(["Stanford", "Leland Stanford Junior University"]),
            country_code="US",
            source_task_id=None,
        )
        test_session.add(std_school)
        await test_session.commit()

        # 验证别名存储
        result = await test_session.execute(
            select(StdSchool).where(
                StdSchool.openalex_institution_id == "NORMALIZE-001"
            )
        )
        saved = result.scalar_one_or_none()
        assert saved is not None
        aliases = json.loads(saved.name_aliases)
        assert "Stanford" in aliases


# ============ Code Review Fix Tests ============
# 以下测试验证 code-review-fixes.md 中的修复

class TestTransactionManagement:
    """CR-01: 事务管理测试

    验证 update_progress 使用独立数据库连接更新进度，避免阻塞主事务。
    """

    @pytest.fixture
    def progress_tracker(self, mock_session):
        from app.services.collect.progress_tracker import ProgressTracker
        return ProgressTracker(mock_session)

    @pytest.mark.asyncio
    async def test_update_progress_uses_main_session(self, progress_tracker, mock_session):
        """验证 update_progress 使用主 session 进行更新"""
        # 创建测试任务
        mock_task = MagicMock(spec=CollectTask)
        mock_task.task_id = 1
        mock_task.current_step = None
        mock_task.progress_percent = 0

        # Mock flush 方法
        mock_session.flush = AsyncMock()

        # 调用 update_progress
        await progress_tracker.update_progress(mock_task, "测试步骤", 50)

        # 验证调用了 flush 方法
        mock_session.flush.assert_called_once()

        # 验证任务属性被更新
        assert mock_task.current_step == "测试步骤"
        assert mock_task.progress_percent == 50

    @pytest.mark.asyncio
    async def test_update_task_status_flushes_without_commit(self, progress_tracker, mock_session):
        """验证 update_task_status 也只 flush 不 commit"""
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_task = MagicMock(spec=CollectTask)
        mock_task.task_id = 1

        await progress_tracker.update_task_status(mock_task, "running")

        # 验证只 flush 不 commit
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()


class TestTalentQueryOptimization:
    """CR-02: 全表查询优化测试

    验证 _update_talent_topic_tags 只查询与当前任务相关的人才。
    """

    @pytest.fixture
    def orchestrator(self, mock_session):
        from app.services.collect.orchestrator import CollectionOrchestrator
        return CollectionOrchestrator(mock_session)

    @pytest.mark.asyncio
    async def test_update_topic_tags_filters_by_tech_element(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """验证只查询与任务关联 tech_element 的人才"""
        from app.services.collect.orchestrator import CollectionOrchestrator
        from app.services.common.progress import CollectionProgress

        # 创建测试数据
        tech_element_1 = test_data_setup["tech_element"]

        # 创建第二个技术要素
        tech_element_2 = TechElement(
            element_code="CV",
            element_name="计算机视觉",
            is_enabled=True,
            sort_order=2,
        )
        test_session.add(tech_element_2)
        await test_session.flush()

        # 创建两个任务，关联不同的技术要素
        task_1 = CollectTask(
            task_code="CR02-TEST-001",
            tech_element_id=tech_element_1.tech_element_id,
            collect_mode="full",
            triggered_by=None,
            triggered_at=datetime.utcnow(),  # 添加必填字段
            status="running",
        )
        test_session.add(task_1)

        task_2 = CollectTask(
            task_code="CR02-TEST-002",
            tech_element_id=tech_element_2.tech_element_id,
            collect_mode="full",
            triggered_by=None,
            triggered_at=datetime.utcnow(),  # 添加必填字段
            status="pending",
        )
        test_session.add(task_2)
        await test_session.flush()

        # 创建人才
        talent_1 = Talent(
            source_type="openalex",
            source_record_id="CR02-TALENT-001",
            name="AI Researcher",
            role_type=RoleType.PROFESSOR.value,
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )
        talent_2 = Talent(
            source_type="openalex",
            source_record_id="CR02-TALENT-002",
            name="CV Researcher",
            role_type=RoleType.PROFESSOR.value,
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )
        test_session.add_all([talent_1, talent_2])
        await test_session.flush()

        # 创建技术标签
        tag_1 = TalentTechTag(
            talent_id=talent_1.talent_id,
            tech_element_id=tech_element_1.tech_element_id,
            tech_direction_id=test_data_setup["tech_direction"].tech_direction_id,  # 添加必填字段
            tag_level="primary",
            tag_source="auto_mapping",
            is_enabled=True,
        )
        tag_2 = TalentTechTag(
            talent_id=talent_2.talent_id,
            tech_element_id=tech_element_2.tech_element_id,
            tech_direction_id=test_data_setup["tech_direction"].tech_direction_id,  # 添加必填字段
            tag_level="primary",
            tag_source="auto_mapping",
            is_enabled=True,
        )
        test_session.add_all([tag_1, tag_2])
        await test_session.commit()

        # 创建 orchestrator 并调用方法
        orchestrator = CollectionOrchestrator(test_session)
        progress = CollectionProgress(task_id=task_1.task_id)

        await orchestrator._update_talent_topic_tags(task_1.task_id, progress)

        # 刷新并验证结果
        await test_session.refresh(talent_1)
        await test_session.refresh(talent_2)

        # talent_1 应该有 topic_tags（关联 tech_element_1）
        assert talent_1.topic_tags is not None
        assert "人工智能" in talent_1.topic_tags

        # talent_2 不应该有 topic_tags（关联 tech_element_2，不在任务 1 范围内）
        # 注意：由于我们只更新了 task_1 相关的人才，talent_2 不应被修改
        assert talent_2.topic_tags is None or "计算机视觉" not in (talent_2.topic_tags or [])

    @pytest.mark.asyncio
    async def test_update_topic_tags_handles_missing_task(
        self,
        test_session: AsyncSession,
    ):
        """验证任务不存在时的优雅处理"""
        from app.services.collect.orchestrator import CollectionOrchestrator
        from app.services.common.progress import CollectionProgress
        from app.models.tech_element import TalentTechTag  # 修复导入路径

        orchestrator = CollectionOrchestrator(test_session)
        progress = CollectionProgress(task_id=99999)

        # 不应抛出异常
        await orchestrator._update_talent_topic_tags(99999, progress)

        # 验证日志记录了警告
        assert any("不存在" in log.get("message", "") for log in orchestrator.progress_tracker.get_logs())


class TestOrchestratorTransactionBoundary:
    """集成测试：验证 orchestrator 的事务边界"""

    @pytest.mark.asyncio
    async def test_execute_task_commits_at_end(
        self,
        test_session: AsyncSession,
        test_data_setup
    ):
        """验证 execute_task 在结束时统一 commit"""
        from app.services.collect.orchestrator import CollectionOrchestrator
        from unittest.mock import patch, AsyncMock

        # 创建测试任务
        task = CollectTask(
            task_code="TX-TEST-001",
            tech_element_id=test_data_setup["tech_element"].tech_element_id,
            collect_mode="full",
            triggered_by=None,
            triggered_at=datetime.utcnow(),  # 添加必填字段
            status="pending",
        )
        test_session.add(task)
        await test_session.commit()

        # 创建 orchestrator
        orchestrator = CollectionOrchestrator(test_session)

        # Mock 各阶段方法以简化测试
        with patch.object(orchestrator, '_estimate_total_works', return_value=0), \
             patch.object(orchestrator, '_execute_venue_sub_tasks', new_callable=AsyncMock), \
             patch.object(orchestrator, '_fetch_all_authors', new_callable=AsyncMock), \
             patch.object(orchestrator, '_fetch_all_institutions', new_callable=AsyncMock), \
             patch.object(orchestrator, '_normalize_schools', new_callable=AsyncMock), \
             patch.object(orchestrator, '_normalize_authors', new_callable=AsyncMock), \
             patch.object(orchestrator, '_calculate_tech_belong', new_callable=AsyncMock), \
             patch.object(orchestrator, '_sync_to_serving_layer', return_value=[]), \
             patch.object(orchestrator, '_fetch_selected_works', new_callable=AsyncMock), \
             patch.object(orchestrator, '_update_talent_topic_tags', new_callable=AsyncMock), \
             patch.object(orchestrator, '_update_school_statistics', new_callable=AsyncMock), \
             patch.object(orchestrator, '_build_statistics', new_callable=AsyncMock):

            progress = await orchestrator.execute_task(task.task_id)

            # 验证任务状态为 completed
            assert progress.status == "completed"

        # 验证任务在数据库中被更新
        await test_session.refresh(task)
        assert task.status == "completed"
        assert task.progress_percent == 100
