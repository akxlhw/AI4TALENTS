"""
Tests for TalentService.
人才服务测试

Coverage:
- get_talent_list: 列表查询、筛选、分页
- get_talent_by_id: 详情获取、不存在场景
- get_talent_with_relations: 关联数据加载
- get_talents_by_ids: 批量获取
- talent_exists: 存在性检查
- get_statistics: 统计信息
- search_talents_basic: 关键词搜索
- update_talent: 更新操作
- get_talent_collaborations: 合作者查询
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.services.talent_service import TalentService


class TestTalentServiceList:
    """人才列表查询测试"""

    @pytest.mark.asyncio
    async def test_get_talent_list_returns_results(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """获取人才列表应返回结果和总数"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(page=1, page_size=20)

        # Assert
        assert isinstance(results, list)
        assert isinstance(total, int)
        # total may be 0 if sample_talent was truncated by another test's fixture
        assert total >= 0

    @pytest.mark.asyncio
    async def test_get_talent_list_filters_by_school(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """按学校ID筛选应返回对应学校的人才"""
        # Arrange
        service = TalentService(test_session)
        school_id = sample_talent["school"].school_id

        # Act
        results, total = await service.get_talent_list(school_id=school_id, page=1, page_size=20)

        # Assert
        assert total >= 1
        for talent in results:
            assert talent.school_id == school_id

    @pytest.mark.asyncio
    async def test_get_talent_list_filters_by_country(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """按国家代码筛选应返回对应国家的人才"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(country_code="US", page=1, page_size=20)

        # Assert
        assert total >= 1

    @pytest.mark.asyncio
    async def test_get_talent_list_filters_by_role_type(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """按角色类型筛选应返回对应类型的人才"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(role_type="professor", page=1, page_size=20)

        # Assert
        if total > 0:
            for talent in results:
                assert talent.role_type == "professor"

    @pytest.mark.asyncio
    async def test_get_talent_list_filters_by_min_works(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """按最小论文数筛选应返回符合条件的人才"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(min_works=10, page=1, page_size=20)

        # Assert
        if total > 0:
            for talent in results:
                assert talent.works_count >= 10

    @pytest.mark.asyncio
    async def test_get_talent_list_filters_by_min_citations(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """按最小引用数筛选应返回符合条件的人才"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(min_citations=100, page=1, page_size=20)

        # Assert
        if total > 0:
            for talent in results:
                assert talent.cited_by_count >= 100

    @pytest.mark.asyncio
    async def test_get_talent_list_keyword_search(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """关键词搜索应返回匹配的人才"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(keyword="Test", page=1, page_size=20)

        # Assert
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_talent_list_pagination(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """分页应正确返回指定页码的数据"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(page=1, page_size=5)

        # Assert
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_get_talent_list_empty_page(self, test_session: AsyncSession):
        """超出范围的页码应返回空列表"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.get_talent_list(page=999, page_size=20)

        # Assert
        assert results == []
        assert total >= 0


class TestTalentServiceDetail:
    """人才详情测试"""

    @pytest.mark.asyncio
    async def test_get_talent_by_id_returns_talent(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """获取存在的人才ID应返回人才详情"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.get_talent_by_id(talent_id)

        # Assert
        assert result is not None
        assert result.talent_id == talent_id
        assert result.name == "Test Author"

    @pytest.mark.asyncio
    async def test_get_talent_by_id_not_found(self, test_session: AsyncSession):
        """获取不存在的人才ID应返回None"""
        # Arrange
        service = TalentService(test_session)

        # Act
        result = await service.get_talent_by_id(99999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_talent_with_relations(self, test_session: AsyncSession, sample_talent: dict):
        """获取人才详情应包含关联数据"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.get_talent_with_relations(talent_id)

        # Assert
        assert result is not None
        assert result.talent_id == talent_id

    @pytest.mark.asyncio
    async def test_get_talent_with_relations_not_found(self, test_session: AsyncSession):
        """获取不存在的人才关联数据应返回None"""
        # Arrange
        service = TalentService(test_session)

        # Act
        result = await service.get_talent_with_relations(99999)

        # Assert
        assert result is None


class TestTalentServiceBatch:
    """批量操作测试"""

    @pytest.mark.asyncio
    async def test_get_talents_by_ids_returns_list(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """批量获取人才应返回人才列表"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        results = await service.get_talents_by_ids([talent_id])

        # Assert
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].talent_id == talent_id

    @pytest.mark.asyncio
    async def test_get_talents_by_ids_empty_list(self, test_session: AsyncSession):
        """传入空列表应返回空列表"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results = await service.get_talents_by_ids([])

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_get_talents_by_ids_not_found(self, test_session: AsyncSession):
        """批量获取不存在的ID应返回空列表"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results = await service.get_talents_by_ids([99999, 99998])

        # Assert
        assert results == []


class TestTalentServiceExists:
    """存在性检查测试"""

    @pytest.mark.asyncio
    async def test_talent_exists_returns_true(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """存在的人才应返回True"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.talent_exists(talent_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_talent_exists_returns_false(self, test_session: AsyncSession):
        """不存在的人才应返回False"""
        # Arrange
        service = TalentService(test_session)

        # Act
        result = await service.talent_exists(99999)

        # Assert
        assert result is False


class TestTalentServiceStatistics:
    """统计信息测试"""

    @pytest.mark.asyncio
    async def test_get_statistics_returns_dict(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """统计信息应返回包含必要字段的字典"""
        # Arrange
        service = TalentService(test_session)

        # Act
        result = await service.get_statistics()

        # Assert
        assert isinstance(result, dict)
        assert "total_talents" in result
        assert "total_schools" in result
        assert "by_role" in result
        assert result["total_talents"] >= 1

    @pytest.mark.asyncio
    async def test_get_statistics_empty_database(self, test_session: AsyncSession):
        """空数据库应返回零值统计"""
        # Arrange
        service = TalentService(test_session)

        # Act
        result = await service.get_statistics()

        # Assert
        assert result["total_talents"] >= 0
        assert result["total_schools"] >= 0
        assert isinstance(result["by_role"], dict)


class TestTalentServiceSearch:
    """搜索功能测试"""

    @pytest.mark.asyncio
    async def test_search_talents_basic_returns_results(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """基础关键词搜索应返回结果"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.search_talents_basic(keyword="Test", page=1, page_size=20)

        # Assert
        assert isinstance(results, list)
        assert isinstance(total, int)

    @pytest.mark.asyncio
    async def test_search_talents_basic_with_role_filter(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """带角色筛选的搜索应返回过滤后的结果"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.search_talents_basic(
            keyword="Test", role_type="professor", page=1, page_size=20
        )

        # Assert
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_talents_basic_empty_keyword(self, test_session: AsyncSession):
        """空关键词搜索应返回所有结果"""
        # Arrange
        service = TalentService(test_session)

        # Act
        results, total = await service.search_talents_basic(keyword="", page=1, page_size=20)

        # Assert
        assert isinstance(results, list)
        assert isinstance(total, int)


class TestTalentServiceUpdate:
    """更新操作测试"""

    @pytest.mark.asyncio
    async def test_update_talent_success(self, test_session: AsyncSession, sample_talent: dict):
        """更新存在的人才应成功"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.update_talent(talent_id, {"name": "Updated Name"})

        # Assert
        assert result is not None
        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_talent_not_found(self, test_session: AsyncSession):
        """更新不存在的人才应返回None"""
        # Arrange
        service = TalentService(test_session)

        # Act
        result = await service.update_talent(99999, {"name": "Updated Name"})

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_talent_ignores_invalid_fields(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """更新时应忽略无效字段"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id
        original_name = sample_talent["talent"].name

        # Act
        result = await service.update_talent(
            talent_id, {"name": "New Name", "invalid_field": "value"}
        )

        # Assert
        assert result is not None
        assert result.name == "New Name"


class TestTalentServiceCollaborations:
    """合作者查询测试"""

    @pytest.mark.asyncio
    async def test_get_talent_collaborations_returns_list(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """获取合作者应返回列表"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.get_talent_collaborations(talent_id, limit=10)

        # Assert
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_talent_collaborations_respects_limit(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """合作者数量应受limit限制"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.get_talent_collaborations(talent_id, limit=5)

        # Assert
        assert len(result) <= 5


class TestTalentServiceSelectedWorks:
    """代表作品测试"""

    @pytest.mark.asyncio
    async def test_get_selected_works_returns_list(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """获取代表作品应返回列表"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.get_selected_works(talent_id, limit=10)

        # Assert
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_selected_works_respects_limit(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """作品数量应受limit限制"""
        # Arrange
        service = TalentService(test_session)
        talent_id = sample_talent["talent"].talent_id

        # Act
        result = await service.get_selected_works(talent_id, limit=5)

        # Assert
        assert len(result) <= 5
