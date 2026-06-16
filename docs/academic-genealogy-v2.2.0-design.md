# 学术族谱人才洞察 — 完整实现方案

> 版本: v2.2.0 | 日期: 2026-06-07
> 状态: 设计已确认，待实现

---

## 1. 项目背景

AI4TALENT 智能人才库当前的合作网络是简单的无向共著图（`core_collaboration` 表），前端用 ECharts 力导向图展示 1-hop 邻居。需要升级为**学术族谱洞察**：以高影响力学者为根节点的分层合作网络 + 导师-学生传承关系推断。

**关键前提**：所有需要的数据已存在于 `raw_json` 中，无需额外采集。只需增加提取和计算逻辑。

---

## 2. 技术栈参考

- 后端: Python 3.11, FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL 14+
- 前端: React 18, TypeScript, Ant Design v5, ECharts
- 项目结构: Domain-driven (`backend/app/domains/academic/`)

---

## 3. 数据模型（新增 2 张表）

### 3.1 `genealogy_edge`（学术族谱边）

文件位置: `backend/app/domains/academic/models/genealogy.py`（新建）

```python
class GenealogyEdge(Base, TimestampMixin):
    __tablename__ = "genealogy_edge"

    edge_id = Column(Integer, primary_key=True, autoincrement=True)
    from_talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    to_talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    relationship_type = Column(String(20), nullable=False)  # advisor_student / mentor_mentee / senior_junior
    confidence_score = Column(Float, nullable=False, default=0.0)
    evidence_count = Column(Integer, nullable=False, default=0)
    shared_institution = Column(Boolean, nullable=False, default=False)
    first_year = Column(Integer, nullable=True)
    last_year = Column(Integer, nullable=True)
    source_work_ids = Column(JSON, nullable=True)  # 推断依据论文 ID 列表

    __table_args__ = (
        UniqueConstraint("from_talent_id", "to_talent_id", "relationship_type", name="uq_genealogy_pair"),
    )
```

### 3.2 `talent_influence_score`（影响力评分）

同文件 `genealogy.py`:

```python
class TalentInfluenceScore(Base, TimestampMixin):
    __tablename__ = "talent_influence_score"

    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), primary_key=True)
    h_index_score = Column(Float, nullable=False, default=0.0)      # 百分位标准化
    citation_score = Column(Float, nullable=False, default=0.0)      # log 标准化
    works_score = Column(Float, nullable=False, default=0.0)         # log 标准化
    collaboration_score = Column(Float, nullable=False, default=0.0) # 百分位标准化
    bridge_score = Column(Float, nullable=False, default=0.0)        # 百分位标准化
    composite_score = Column(Float, nullable=False, default=0.0)     # 综合加权 0-100
    tier = Column(String(10), nullable=False, default="tier4")       # tier1/tier2/tier3/tier4
    is_root = Column(Boolean, nullable=False, default=False)
    computed_at = Column(DateTime, nullable=False, server_default=func.now())
```

### 3.3 Alembic 迁移

文件: `backend/migrations/versions/050_add_genealogy.py`（新建）

- 注册到 `backend/app/model_registry.py` 中导入新模型

---

## 4. 影响力评分算法

文件位置: `backend/app/domains/academic/services/influence_service.py`（新建）

### 4.1 评分公式

```
composite_score = 0.30 * h_index_norm
                + 0.25 * citation_norm
                + 0.15 * works_norm
                + 0.15 * collab_norm
                + 0.15 * bridge_norm
```

### 4.2 标准化方法

- **h_index / collab / bridge**: 百分位排名法（`percent_rank()` over 全体学者）
- **citation / works**: log 标准化 → `score = log(value+1) / log(max_value+1) * 100`

### 4.3 分层规则

| Tier | 名称 | 条件 | 节点颜色 | 节点尺寸 |
|------|------|------|---------|---------|
| tier1 | 学术领军 | composite_score ≥ 85 | #e94560 红 | 大(28px) |
| tier2 | 中坚学者 | 60 ≤ score < 85 | #ffa726 橙 | 中(20px) |
| tier3 | 青年才俊 | 40 ≤ score < 60 | #42a5f5 蓝 | 小(16px) |
| tier4 | 新锐研究者 | score < 40 | #66bb6a 绿 | 最小(10px) |

### 4.4 桥梁中心度计算

从 `core_collaboration` 构建邻接图，计算每个节点的 betweenness centrality（可用 NetworkX 或 SQL 近似）。

### 4.5 数据来源

| 维度 | 来源字段 |
|------|---------|
| h_index | `raw_author.h_index` 或 `core_talent.h_index` |
| citation | `raw_author.cited_by_count` 或 `core_talent.cited_by_count` |
| works | `raw_author.works_count` 或 `core_talent.works_count` |
| collab | `COUNT(*) FROM core_collaboration WHERE talent_id_1=X OR talent_id_2=X` |
| bridge | 从 core_collaboration 图计算 betweenness centrality |

---

## 5. 导师-学生推断算法

文件位置: `backend/app/domains/academic/services/genealogy_service.py`（新建）

### 5.1 数据提取

从 `raw_work.raw_json` 的 `authorships` 数组提取：

```json
{
  "authorships": [
    {
      "author": {"id": "https://openalex.org/A123", "display_name": "张教授"},
      "author_position": "last",           // first / middle / last
      "institutions": [{"id": "https://openalex.org/I456", "display_name": "清华大学"}],
      "is_corresponding": true
    },
    {
      "author": {"id": "https://openalex.org/A789", "display_name": "李同学"},
      "author_position": "first",
      "institutions": [{"id": "https://openalex.org/I456", "display_name": "清华大学"}]
    }
  ],
  "publication_year": 2022,
  "cited_by_count": 42
}
```

### 5.2 推断信号

对每篇论文中出现的 **last-author + first-author** 对，累加置信度：

| 信号 | 条件 | 加分 |
|------|------|------|
| 位置模式 | A(last) + B(first) | +0.30 |
| 同机构 | 两人 institutions 有交集 | +0.15 |
| 多次重复 | 同一对出现 ≥ 3 篇（每多 1 篇 +0.05，上限 +0.20） | +0.20 |
| 时间跨度 | 合作跨越 ≥ 3 年 | +0.10 |
| 角色差异 | A(role=professor) + B(role=student/graduate) | +0.15 |

理论最高置信度: 0.30 + 0.15 + 0.20 + 0.10 + 0.15 = 0.90

### 5.3 推断流程

```
1. 遍历 raw_work，按 openalex_work_id 分批（batch_size=500）
2. 对每篇论文:
   a. 提取 authorships 中的 position, institution, author_id
   b. 映射 openalex_author_id → core_talent.talent_id（通过 std_author 关联）
   c. 找到 last-author 和 first-author
   d. 如果 talent_id 存在，累加到 (from=last, to=first) 对的置信度
3. 批次结束后:
   a. 对所有累积的 (from, to) 对，计算最终置信度
   b. relationship_type 判定:
      - confidence ≥ 0.65 且 role 差异 = professor+student → advisor_student
      - confidence ≥ 0.65 且同机构 → mentor_mentee
      - 其他 → senior_junior
   c. confidence < 0.30 的丢弃
   d. 批量 upsert 到 genealogy_edge
```

### 5.4 展示规则

- 置信度 ≥ 0.75：实线 + 橙色（默认显示）
- 置信度 0.50-0.74：实线 + 浅橙色（默认显示）
- 置信度 < 0.50：虚线 + 灰色（默认隐藏，用户可切换显示）

---

## 6. Sync Pipeline 集成

### 6.1 集成位置

在 `backend/app/domains/academic/services/collect/orchestrator.py` 的现有 12 阶段流水线中：

```
Phase 8:  获取代表作品（现有）
Phase 8.5: 计算影响力评分（新增）
Phase 8.6: 推断学术族谱（新增）
Phase 9:  更新技术标签（现有）
```

### 6.2 也支持独立触发

通过 `POST /api/v1/talents/genealogy/sync` API 独立触发，复用 `collaboration_service.py` 中的 `sync_all_collaborations()` 类似模式（分批处理 RawWork）。

---

## 7. API 设计

文件位置: `backend/app/domains/academic/api/genealogy.py`（新建）

### 7.1 族谱网络查询

```
GET /api/v1/talents/{talent_id}/genealogy
```

参数:
- `depth`: int = 2 (跳数, 1-3)
- `min_confidence`: float = 0.5
- `relationship_type`: str | null (null=全部, advisor_student, mentor_mentee, senior_junior)
- `tier_filter`: str | null (null=全部, tier1, tier2, tier3, tier4)

响应:
```json
{
  "root_talent": {
    "talent_id": 123,
    "name": "张教授",
    "institution": "清华大学",
    "composite_score": 92.5,
    "tier": "tier1",
    "h_index": 68,
    "cited_by_count": 12340,
    "is_root": true
  },
  "nodes": [
    {
      "talent_id": 456,
      "name": "李教授",
      "institution": "北京大学",
      "composite_score": 72.3,
      "tier": "tier2",
      "h_index": 35,
      "cited_by_count": 5600,
      "is_root": false
    }
  ],
  "links": [
    {
      "source": 123,
      "target": 456,
      "type": "advisor_student",
      "confidence": 0.85,
      "shared_institution": true,
      "evidence_count": 5,
      "first_year": 2015,
      "last_year": 2023
    }
  ],
  "stats": {
    "total_nodes": 42,
    "total_links": 58,
    "tier_distribution": {"tier1": 3, "tier2": 12, "tier3": 18, "tier4": 9}
  }
}
```

### 7.2 同步触发

```
POST /api/v1/talents/genealogy/sync
```

触发影响力评分计算 + 族谱推断。支持进度查询（复用现有 progress 模式）。

### 7.3 影响力排名

```
GET /api/v1/talents/genealogy/influence-ranking
```

参数: `tech_domain_id`, `tier`, `limit`
返回影响力排名列表。

### 7.4 路由注册

在 `backend/app/api_router.py` 中注册 genealogy router。

---

## 8. 前端实现

### 8.1 新组件: GenealogyGraph

文件位置: `frontend/src/components/GenealogyGraph.tsx`（新建）

基于 ECharts graph（force layout），核心特性：

**节点样式（按 Tier）**:
- tier1: `#e94560` 红, radius=28, 星标前缀
- tier2: `#ffa726` 橙, radius=20
- tier3: `#42a5f5` 蓝, radius=16
- tier4: `#66bb6a` 绿, radius=10

**边样式（按关系类型和置信度）**:
- advisor_student: 橙色箭头线, 粗细 ∝ confidence
- collaboration: 蓝色线（来自现有 core_collaboration）
- confidence < 0.50: 虚线, 默认隐藏

**筛选面板**（Ant Design 组件）:
- Select: 关系类型（全部/导师-学生/合作/层级间）
- Slider: 置信度阈值 (0.3 - 1.0)
- Select: Tier 过滤（全部/T1/T2/T3/T4）
- RangePicker: 年份范围

**交互**:
- 悬停节点: Tooltip 卡片（评分/机构/h-index/论文数/tier）
- 点击节点: 切换为该学者的网络中心（重新请求 API）
- 缩放/拖拽: ECharts 内置

**图例**:
- 4 个 Tier 颜色说明
- 3 种关系类型说明
- 实线/虚线说明

### 8.2 集成位置

文件: `frontend/src/pages/academic/academic-talent-detail-page.tsx`

在人才详情页的合作网络区域，新增 Tab 切换：
- Tab 1: 合作网络（现有 CollaborationGraph）
- Tab 2: 学术族谱（新 GenealogyGraph）

### 8.3 API 调用

文件: `frontend/src/services/api/academic.ts`

新增:
```typescript
export const getGenealogy = (id: number, params?: Record<string, unknown>) =>
  client.get(`/talents/${id}/genealogy`, { params });

export const syncGenealogy = () =>
  client.post('/talents/genealogy/sync');

export const getInfluenceRanking = (params?: Record<string, unknown>) =>
  client.get('/talents/genealogy/influence-ranking', { params });
```

---

## 9. 关键文件清单

### 需要修改的文件

| 文件路径 | 改动内容 |
|---------|---------|
| `backend/app/domains/academic/services/collect/orchestrator.py` | 在 Phase 8 后新增 Phase 8.5/8.6 调用 |
| `backend/app/domains/academic/api/talents.py` 或新建 `api/genealogy.py` | 新增族谱 API 端点 |
| `backend/app/api_router.py` | 注册 genealogy router |
| `backend/app/model_registry.py` | 导入新模型 |
| `frontend/src/pages/academic/academic-talent-detail-page.tsx` | 新增族谱 Tab |
| `frontend/src/services/api/academic.ts` | 新增 API 调用函数 |
| `frontend/src/types/index.ts` | 新增族谱相关类型定义 |

### 需要新建的文件

| 文件路径 | 用途 |
|---------|------|
| `backend/app/domains/academic/models/genealogy.py` | GenealogyEdge + TalentInfluenceScore ORM 模型 |
| `backend/app/domains/academic/services/influence_service.py` | 影响力评分计算服务 |
| `backend/app/domains/academic/services/genealogy_service.py` | 导师-学生推断服务 |
| `backend/app/domains/academic/api/genealogy.py` | 族谱 API 路由（如不合并到 talents.py） |
| `backend/app/domains/academic/repositories/genealogy_repository.py` | 族谱数据查询层（可选） |
| `frontend/src/components/GenealogyGraph.tsx` | 分层网络图组件 |
| `backend/migrations/versions/050_add_genealogy.py` | Alembic 迁移文件 |

---

## 10. 实现顺序建议

1. **数据模型 + 迁移**: 创建 `genealogy.py` 模型，注册到 `model_registry.py`，生成 Alembic 迁移
2. **影响力评分服务**: 实现 `influence_service.py`，含标准化和加权计算
3. **族谱推断服务**: 实现 `genealogy_service.py`，含 raw_json 提取和置信度计算
4. **API 端点**: 实现族谱查询、同步触发、排名列表
5. **前端组件**: 实现 `GenealogyGraph.tsx`，集成到详情页
6. **Pipeline 集成**: 在 orchestrator 中集成 Phase 8.5/8.6

---

## 11. 验证方式

1. 运行迁移，确认两张新表创建成功
2. 触发 genealogy sync，检查 `talent_influence_score` 有数据，tier 分布合理
3. 检查 `genealogy_edge` 有推断关系，confidence_score 分布合理
4. `GET /api/v1/talents/{id}/genealogy` 返回分层节点和有向边
5. 前端族谱图渲染：节点按 tier 颜色区分，导师→学生边有箭头
6. 筛选器功能正常：关系类型、置信度、层级过滤
7. 点击节点可切换中心学者
