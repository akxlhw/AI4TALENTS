"""
Collaboration service for extracting and managing co-author relationships.

优化版本：从本地 RawWork 表提取合作关系，不再重复调用 OpenAlex API
"""
import json
import logging
from typing import List, Dict, Optional, Set, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.talent import Talent
from app.models.collaboration import Collaboration
from app.models.raw_data import RawWork

logger = logging.getLogger(__name__)


class CollaborationService:
    """Service for managing collaboration data.

    从本地 RawWork 表提取合作关系，避免重复调用 OpenAlex API。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def close(self):
        """No-op for compatibility with old code."""
        pass

    def _extract_author_ids_from_raw_json(self, raw_json: str) -> List[str]:
        """从 RawWork.raw_json 提取作者 ID 列表。

        Args:
            raw_json: JSON 字符串，包含 OpenAlex work 数据

        Returns:
            作者 OpenAlex ID 列表（短格式，如 ["A123456", "A789012"]）
        """
        try:
            work_data = json.loads(raw_json)
            authorships = work_data.get("authorships", [])
            author_ids = []

            for authorship in authorships:
                author = authorship.get("author", {})
                author_id = author.get("id", "")
                if author_id:
                    # 提取短格式 ID (https://openalex.org/A123456 -> A123456)
                    short_id = author_id.split("/")[-1]
                    author_ids.append(short_id)

            return author_ids
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse raw_json: {e}")
            return []

    def _extract_publication_year(self, raw_json: str) -> Optional[int]:
        """从 RawWork.raw_json 提取发表年份。"""
        try:
            work_data = json.loads(raw_json)
            return work_data.get("publication_year")
        except (json.JSONDecodeError, KeyError):
            return None

    async def sync_all_collaborations(
        self,
        batch_size: int = 500,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        从本地 RawWork 表提取所有合作关系。

        这是推荐的主要同步方法，直接遍历已采集的论文数据，
        提取作者合作关系，无需再次调用 OpenAlex API。

        Args:
            batch_size: 每批处理的论文数量
            progress_callback: 进度回调函数 (processed, total, collaborations)

        Returns:
            Dict with sync statistics
        """
        # 1. 构建作者 OpenAlex ID -> talent_id 映射
        logger.info("正在构建作者 ID 映射...")
        talent_id_map = await self._build_talent_id_map()
        logger.info(f"已映射 {len(talent_id_map)} 位学者")

        # 2. 获取论文总数
        count_stmt = select(func.count(RawWork.raw_work_id))
        result = await self.session.execute(count_stmt)
        total_works = result.scalar() or 0

        if total_works == 0:
            logger.info("RawWork 表为空，请先执行采集任务")
            return {"total_works": 0, "processed": 0, "collaborations_created": 0, "message": "请先执行采集任务"}

        # 立即通知前端总数
        if progress_callback:
            progress_callback(0, total_works, 0)

        # 3. 遍历 RawWork 表，提取合作关系
        processed = 0
        collaborations_created = 0
        offset = 0

        # 内存缓存：记录已处理的合作关系，避免重复插入
        collab_cache: Set[Tuple[int, int]] = set()

        logger.info(f"开始处理 {total_works} 篇论文...")

        while offset < total_works:
            stmt = select(RawWork).offset(offset).limit(batch_size)
            result = await self.session.execute(stmt)
            works = result.scalars().all()

            for work in works:
                try:
                    # 从 raw_json 或 author_ids 字段获取作者列表
                    if work.author_ids:
                        author_ids = json.loads(work.author_ids)
                    elif work.raw_json:
                        author_ids = self._extract_author_ids_from_raw_json(work.raw_json)
                    else:
                        author_ids = []

                    if len(author_ids) < 2:
                        processed += 1
                        continue

                    # 获取发表年份
                    pub_year = work.publication_year
                    if not pub_year and work.raw_json:
                        pub_year = self._extract_publication_year(work.raw_json)

                    # 将作者 ID 映射到 talent_id
                    talent_ids = []
                    for aid in author_ids:
                        if aid in talent_id_map:
                            talent_ids.append(talent_id_map[aid])

                    # 建立合作关系（使用缓存）
                    count = await self._create_collaborations_with_cache(talent_ids, pub_year, collab_cache)
                    collaborations_created += count
                    processed += 1

                    # 每 50 条更新一次进度
                    if progress_callback and processed % 50 == 0:
                        progress_callback(processed, total_works, collaborations_created)

                except Exception as e:
                    logger.warning(f"处理论文 {work.openalex_work_id} 失败: {e}")
                    processed += 1

            # 每批次提交一次
            await self.session.commit()
            offset += batch_size

            # 每批处理完也更新进度
            if progress_callback:
                progress_callback(processed, total_works, collaborations_created)

            logger.info(f"已处理 {processed}/{total_works} 篇论文，创建 {collaborations_created} 条合作关系")

        return {
            "total_works": total_works,
            "processed": processed,
            "collaborations_created": collaborations_created
        }

    async def _build_talent_id_map(self) -> Dict[str, int]:
        """构建 OpenAlex 作者 ID -> talent_id 的映射。"""
        stmt = select(Talent.talent_id, Talent.source_record_id)
        result = await self.session.execute(stmt)

        id_map = {}
        for row in result.fetchall():
            talent_id, source_record_id = row
            if source_record_id:
                # 提取短格式 ID
                short_id = source_record_id.split("/")[-1]
                id_map[short_id] = talent_id

        return id_map

    async def _create_collaborations(
        self,
        talent_ids: List[int],
        publication_year: Optional[int]
    ) -> int:
        """为给定的学者列表创建两两合作关系。"""
        if len(talent_ids) < 2:
            return 0

        collaborations_created = 0

        for i in range(len(talent_ids)):
            for j in range(i + 1, len(talent_ids)):
                t1, t2 = min(talent_ids[i], talent_ids[j]), max(talent_ids[i], talent_ids[j])

                if t1 == t2:
                    continue

                # 检查合作关系是否已存在
                stmt = select(Collaboration).where(
                    and_(
                        Collaboration.talent_id_1 == t1,
                        Collaboration.talent_id_2 == t2
                    )
                )
                result = await self.session.execute(stmt)
                collab = result.scalar_one_or_none()

                if collab:
                    # 更新现有合作关系
                    collab.collaboration_count += 1
                    if publication_year:
                        if collab.first_collaboration_year:
                            collab.first_collaboration_year = min(collab.first_collaboration_year, publication_year)
                            collab.last_collaboration_year = max(collab.last_collaboration_year, publication_year)
                        else:
                            collab.first_collaboration_year = publication_year
                            collab.last_collaboration_year = publication_year
                else:
                    # 创建新的合作关系
                    collab = Collaboration(
                        talent_id_1=t1,
                        talent_id_2=t2,
                        collaboration_count=1,
                        first_collaboration_year=publication_year,
                        last_collaboration_year=publication_year,
                    )
                    self.session.add(collab)
                    collaborations_created += 1

        return collaborations_created

    async def _create_collaborations_with_cache(
        self,
        talent_ids: List[int],
        publication_year: Optional[int],
        cache: Set[Tuple[int, int]]
    ) -> int:
        """为给定的学者列表创建两两合作关系（使用内存缓存避免重复查询）。"""
        if len(talent_ids) < 2:
            return 0

        collaborations_created = 0

        for i in range(len(talent_ids)):
            for j in range(i + 1, len(talent_ids)):
                t1, t2 = min(talent_ids[i], talent_ids[j]), max(talent_ids[i], talent_ids[j])

                if t1 == t2:
                    continue

                cache_key = (t1, t2)

                if cache_key in cache:
                    # 已在缓存中，更新数据库中的记录
                    stmt = select(Collaboration).where(
                        and_(
                            Collaboration.talent_id_1 == t1,
                            Collaboration.talent_id_2 == t2
                        )
                    )
                    result = await self.session.execute(stmt)
                    collab = result.scalar_one_or_none()
                    if collab:
                        collab.collaboration_count += 1
                        if publication_year:
                            if collab.first_collaboration_year:
                                collab.first_collaboration_year = min(collab.first_collaboration_year, publication_year)
                                collab.last_collaboration_year = max(collab.last_collaboration_year, publication_year)
                            else:
                                collab.first_collaboration_year = publication_year
                                collab.last_collaboration_year = publication_year
                else:
                    # 不在缓存中，检查数据库
                    stmt = select(Collaboration).where(
                        and_(
                            Collaboration.talent_id_1 == t1,
                            Collaboration.talent_id_2 == t2
                        )
                    )
                    result = await self.session.execute(stmt)
                    collab = result.scalar_one_or_none()

                    if collab:
                        # 数据库中已存在，更新
                        collab.collaboration_count += 1
                        if publication_year:
                            if collab.first_collaboration_year:
                                collab.first_collaboration_year = min(collab.first_collaboration_year, publication_year)
                                collab.last_collaboration_year = max(collab.last_collaboration_year, publication_year)
                            else:
                                collab.first_collaboration_year = publication_year
                                collab.last_collaboration_year = publication_year
                    else:
                        # 创建新的合作关系
                        collab = Collaboration(
                            talent_id_1=t1,
                            talent_id_2=t2,
                            collaboration_count=1,
                            first_collaboration_year=publication_year,
                            last_collaboration_year=publication_year,
                        )
                        self.session.add(collab)
                        collaborations_created += 1

                    # 添加到缓存
                    cache.add(cache_key)

        return collaborations_created

    async def sync_collaborations_for_talent(
        self,
        talent: Talent,
        limit: int = 50  # 保留参数兼容性，但不再使用
    ) -> int:
        """
        为单个学者同步合作数据（从本地数据）。

        注意：推荐使用 sync_all_collaborations() 批量处理，效率更高。
        此方法保留用于单学者增量更新场景。
        """
        if not talent.source_record_id:
            return 0

        # 提取 OpenAlex 作者 ID
        openalex_id = talent.source_record_id.split("/")[-1]

        # 从 RawWork 表查找包含该作者的论文
        # 使用 author_ids 字段或 raw_json 搜索
        stmt = select(RawWork).where(
            RawWork.author_ids.contains(f'"{openalex_id}"')
        ).limit(200)

        result = await self.session.execute(stmt)
        works = result.scalars().all()

        if not works:
            logger.info(f"学者 {talent.name} 没有找到关联论文")
            return 0

        # 构建 ID 映射
        talent_id_map = await self._build_talent_id_map()

        collaborations_created = 0
        for work in works:
            try:
                if work.author_ids:
                    author_ids = json.loads(work.author_ids)
                elif work.raw_json:
                    author_ids = self._extract_author_ids_from_raw_json(work.raw_json)
                else:
                    continue

                talent_ids = []
                for aid in author_ids:
                    if aid in talent_id_map:
                        talent_ids.append(talent_id_map[aid])

                pub_year = work.publication_year
                if not pub_year and work.raw_json:
                    pub_year = self._extract_publication_year(work.raw_json)

                count = await self._create_collaborations(talent_ids, pub_year)
                collaborations_created += count
            except Exception as e:
                logger.warning(f"处理论文失败: {e}")

        await self.session.commit()
        return collaborations_created

    async def get_collaboration_network(
        self,
        talent_id: int,
        limit: int = 20
    ) -> Dict:
        """
        获取学者的合作网络数据。

        Returns:
            nodes: 节点列表（学者信息）
            links: 连接列表（合作关系）
            total: 合作者总数
        """
        from sqlalchemy.orm import selectinload

        # 获取该学者的所有合作关系
        stmt = select(Collaboration).where(
            or_(
                Collaboration.talent_id_1 == talent_id,
                Collaboration.talent_id_2 == talent_id
            )
        ).order_by(Collaboration.collaboration_count.desc()).limit(limit)

        result = await self.session.execute(stmt)
        collaborations = result.scalars().all()

        if not collaborations:
            return {"nodes": [], "links": [], "message": "暂无合作网络数据，请先在采集配置页面执行合作网络同步"}

        # 获取主学者信息（预加载 school 关系）
        main_talent_stmt = select(Talent).options(
            selectinload(Talent.school)
        ).where(Talent.talent_id == talent_id)
        main_talent_result = await self.session.execute(main_talent_stmt)
        main_talent = main_talent_result.scalar_one_or_none()

        if not main_talent:
            return {"nodes": [], "links": [], "message": "人才不存在"}

        # 收集所有合作者 ID
        collaborator_ids = set()
        for collab in collaborations:
            if collab.talent_id_1 == talent_id:
                collaborator_ids.add(collab.talent_id_2)
            else:
                collaborator_ids.add(collab.talent_id_1)

        # 批量获取合作者信息（预加载 school 关系）
        stmt = select(Talent).options(
            selectinload(Talent.school)
        ).where(Talent.talent_id.in_(collaborator_ids))
        result = await self.session.execute(stmt)
        collaborators = {t.talent_id: t for t in result.scalars().all()}

        # 构建节点列表
        nodes = [
            {
                "id": str(talent_id),
                "name": main_talent.name,
                "affiliation": main_talent.school.school_name if main_talent.school else None,
                "isMain": True,
                "collaborationCount": sum(c.collaboration_count for c in collaborations),
            }
        ]

        for collab_id in collaborator_ids:
            collab_talent = collaborators.get(collab_id)
            if collab_talent:
                # 查找合作次数
                collab_count = 0
                for c in collaborations:
                    if (c.talent_id_1 == talent_id and c.talent_id_2 == collab_id) or \
                       (c.talent_id_2 == talent_id and c.talent_id_1 == collab_id):
                        collab_count = c.collaboration_count
                        break

                nodes.append({
                    "id": str(collab_id),
                    "name": collab_talent.name,
                    "affiliation": collab_talent.school.school_name if collab_talent.school else None,
                    "isMain": False,
                    "collaborationCount": collab_count,
                })

        # 构建连接列表
        links = []
        for collab in collaborations:
            other_id = collab.talent_id_2 if collab.talent_id_1 == talent_id else collab.talent_id_1
            links.append({
                "source": str(talent_id),
                "target": str(other_id),
                "value": collab.collaboration_count,
            })

        return {
            "nodes": nodes,
            "links": links,
            "total": len(nodes) - 1,
        }

    async def generate_sample_collaborations(self, num_samples: int = 100) -> int:
        """
        生成示例合作数据（仅用于测试）。
        """
        import random

        # 获取所有学者 ID
        stmt = select(Talent.talent_id)
        result = await self.session.execute(stmt)
        talent_ids = [row[0] for row in result.fetchall()]

        if len(talent_ids) < 2:
            return 0

        collaborations_created = 0

        for _ in range(num_samples):
            t1, t2 = random.sample(talent_ids, 2)
            t1, t2 = min(t1, t2), max(t1, t2)

            # 检查是否已存在
            stmt = select(Collaboration).where(
                and_(
                    Collaboration.talent_id_1 == t1,
                    Collaboration.talent_id_2 == t2
                )
            )
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                continue

            # 创建合作关系
            collab = Collaboration(
                talent_id_1=t1,
                talent_id_2=t2,
                collaboration_count=random.randint(1, 10),
                first_collaboration_year=random.randint(2018, 2024),
                last_collaboration_year=random.randint(2022, 2025),
            )
            self.session.add(collab)
            collaborations_created += 1

        await self.session.commit()
        return collaborations_created

    async def get_sync_status(self) -> Dict:
        """
        获取当前合作网络同步状态。
        """
        # 统计合作关系数
        collab_count_stmt = select(func.count(Collaboration.collaboration_id))
        result = await self.session.execute(collab_count_stmt)
        total_collaborations = result.scalar() or 0

        # 统计有合作关系的学者数
        talents_with_collab = set()
        stmt = select(Collaboration)
        result = await self.session.execute(stmt)
        for collab in result.scalars().all():
            talents_with_collab.add(collab.talent_id_1)
            talents_with_collab.add(collab.talent_id_2)

        # 统计 RawWork 表中的论文数
        work_count_stmt = select(func.count(RawWork.raw_work_id))
        result = await self.session.execute(work_count_stmt)
        total_works = result.scalar() or 0

        return {
            "total_collaborations": total_collaborations,
            "talents_with_collaborations": len(talents_with_collab),
            "total_works": total_works,
            "last_sync": None
        }
