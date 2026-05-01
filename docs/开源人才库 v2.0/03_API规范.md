# 开源人才子系统 - API 规范 (v2.0.0)

> Base Path: `/api/v1/open-source`
> Auth: Bearer Token

---

## 1. 仓库配置层（Repo Config�?
### 1.1 创建仓库绑定
```
POST /open-source/repo-configs
```

**Request**:
```json
{
  "repo_full_name": "pytorch/pytorch",
  "display_name": "PyTorch",
  "description": "Tensors and Dynamic neural networks",
  "tech_element": "ai",
  "tech_direction_id": null,
  "language": "Python",
  "notes": "AI 框架核心仓库"
}
```

**Response** (201):
```json
{
  "repo_config_id": 1,
  "repo_full_name": "pytorch/pytorch",
  "display_name": "PyTorch",
  "description": "Tensors and Dynamic neural networks",
  "tech_element": "ai",
  "tech_direction_id": null,
  "language": "Python",
  "stars_count": 0,
  "is_active": true,
  "collect_enabled": true,
  "notes": "AI 框架核心仓库",
  "created_by": null,
  "created_at": "2026-04-30T12:00:00",
  "updated_at": "2026-04-30T12:00:00"
}
```

**错误**:
- 400: `Invalid tech_element: xxx. Must be one of: ai, data_science, networks, robotics, security, systems`
- 400: `Repository 'xxx' already exists`

### 1.2 列出仓库绑定
```
GET /open-source/repo-configs?page=1&page_size=50&tech_element=ai&is_active=true&collect_enabled=true
```

**Response**:
```json
{
  "data": [...],
  "total": 35,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

### 1.3 获取单个配置
```
GET /open-source/repo-configs/{repo_config_id}
```

### 1.4 更新配置
```
PUT /open-source/repo-configs/{repo_config_id}
```

**Request** (所有字段可�?:
```json
{
  "display_name": "PyTorch Framework",
  "tech_element": "ai",
  "is_active": true,
  "collect_enabled": false
}
```

### 1.5 删除配置
```
DELETE /open-source/repo-configs/{repo_config_id}
```

**Response** (200):
```json
{ "message": "Deleted" }
```

---

## 2. 开发�?
### 2.1 列表开发�?```
GET /open-source/developers?q={keyword}&language=Python&min_stars=100&location=Beijing&company=Microsoft&page=1&page_size=20
```

**Response** (PaginatedResponse):
```json
{
  "data": [
    {
      "developer_id": 1,
      "github_login": "xxx",
      "name": "xxx",
      "bio": "...",
      "location": "Beijing",
      "company": "Microsoft",
      "avatar_url": "https://...",
      "total_stars_received": 15000,
      "primary_languages": ["Python", "C++"],
      "tech_tags": ["ai", "deep-learning"],
      "is_visible": true
    }
  ],
  "total": 128,
  "page": 1,
  "page_size": 20,
  "total_pages": 7
}
```

### 2.2 开发者详�?```
GET /open-source/developers/{developer_id}
```

**Response** (OSDeveloperDetail):
```json
{
  "developer_id": 1,
  "github_login": "xxx",
  "github_id": 12345,
  "name": "xxx",
  "bio": "...",
  "location": "Beijing",
  "company": "Microsoft",
  "blog_url": "https://xxx.github.io",
  "email": "xxx@example.com",
  "avatar_url": "...",
  "followers_count": 5000,
  "following_count": 200,
  "public_repos_count": 80,
  "total_stars_received": 15000,
  "total_forks_received": 3000,
  "primary_languages": ["Python", "C++"],
  "tech_tags": ["ai", "deep-learning"],
  "repositories": [...],
  "language_skills": [...],
  "contributions": [...],
  "similar_developers": [...]
}
```

### 2.3 开发者仓�?```
GET /open-source/developers/{developer_id}/repositories?page=1&page_size=20&sort_by=stars
```

### 2.4 开发者贡�?```
GET /open-source/developers/{developer_id}/contributions
```

### 2.5 开发者语言
```
GET /open-source/developers/{developer_id}/languages
```

### 2.6 对比开发�?```
POST /open-source/developers/compare
```

**Request**:
```json
{ "developer_ids": [1, 2, 3] }
```

### 2.7 相似推荐
```
GET /open-source/developers/{developer_id}/recommend?limit=10
```

---

## 3. 搜索

搜索统一�?`/search/v2/talents?domain=opensource`，由 `OSSearchService` 处理�?
**模式**:
- `keyword`: ILIKE 匹配 name/bio/company/location
- `semantic`: pgvector 余弦相似�?- `hybrid`: RRF 融合（默认）

---

## 4. 收藏

### 4.1 添加收藏
```
POST /open-source/favourites
```

**Request**:
```json
{ "developer_id": 1, "notes": "重点候选人" }
```

### 4.2 列出收藏
```
GET /open-source/favourites?page=1&page_size=20&keyword=xxx
```

### 4.3 更新收藏
```
PUT /open-source/favourites/{developer_id}
```

**Request**:
```json
{ "notes": "更新备注", "followup_status": "contacted" }
```

### 4.4 删除收藏
```
DELETE /open-source/favourites/{developer_id}
```

### 4.5 获取收藏 IDs
```
GET /open-source/favourites/ids
```

**Response**:
```json
{ "developer_ids": [1, 3, 5] }
```

---

## 5. 人才�?
### 5.1 创建�?```
POST /open-source/talent-pools
```

**Request**:
```json
{ "pool_name": "AI 算法�?, "pool_type": "custom", "scope_desc": "人工智能方向候选人" }
```

### 5.2 列表�?```
GET /open-source/talent-pools
```

### 5.3 添加成员
```
POST /open-source/talent-pools/{pool_id}/members/{developer_id}
```

### 5.4 移除成员
```
DELETE /open-source/talent-pools/{pool_id}/members/{developer_id}
```

### 5.5 成员列表
```
GET /open-source/talent-pools/{pool_id}/members?page=1&page_size=20
```

---

## 6. 采集任务

### 6.1 启动采集
```
POST /open-source/collect/tasks
```

**模式 A - 从绑定仓库采集（推荐�?*:
```json
{
  "tech_elements": ["ai", "systems"],
  "contributors_per_repo": 30
}
```

**模式 B - 手动配置采集**:
```json
{
  "orgs": ["microsoft", "google"],
  "topics": ["machine-learning"],
  "min_stars": 100,
  "max_repos": 50,
  "languages": ["Python"],
  "contributors_per_repo": 30
}
```

**Response**:
```json
{ "task_id": 42, "status": "pending", "message": "Collection task created successfully." }
```

### 6.2 获取任务状�?```
GET /open-source/collect/tasks/{task_id}
```

**Response**:
```json
{
  "task_id": 42,
  "status": "running",
  "progress_percent": 45,
  "current_step": "采集开发者信�?,
  "total_records": 120,
  "processed_records": 54,
  "error_message": null,
  "created_at": "2026-04-30T12:00:00",
  "started_at": "2026-04-30T12:01:00",
  "completed_at": null
}
```

### 6.3 取消任务
```
POST /open-source/collect/tasks/{task_id}/cancel
```

---

## 7. 统计

### 7.1 统计面板
```
GET /open-source/stats
```

**Response** (OSStatsResponse):
```json
{
  "total_developers": 1280,
  "total_repositories": 5600,
  "total_organizations": 120,
  "active_developers_30d": 450,
  "language_distribution": { "Python": 600, "Go": 300, "Rust": 200 },
  "tech_element_distribution": { "ai": 400, "systems": 350, "security": 200 }
}
```

### 7.2 Trending
```
GET /open-source/trending?period=7d&limit=10
```

---

## 8. JD 匹配

```
POST /open-source/jd-match
```

**Request**:
```json
{
  "jd_text": "招聘资深 Python 后端工程师，要求熟悉 FastAPI、PostgreSQL、Docker...",
  "domain": "opensource",
  "filters": { "min_stars": 50, "language": "Python" },
  "top_k": 20
}
```

**Response**:
```json
{
  "results": [
    {
      "developer_id": 1,
      "name": "xxx",
      "github_login": "xxx",
      "match_score": 85.5,
      "tech_score": 90,
      "activity_score": 80,
      "reason": "5 �?Python 经验，主导过大型后端项目，熟�?FastAPI �?PostgreSQL"
    }
  ],
  "total": 20,
  "query_summary": "Python 后端工程�?
}
```

---

## 9. 嵌入管理

### 9.1 嵌入状�?```
GET /open-source/embeddings/status
```

**Response**:
```json
{
  "total_developers": 1280,
  "embedded_count": 800,
  "pending_count": 480,
  "dimension": 1536,
  "model_name": "text-embedding-3-large"
}
```

### 9.2 批量生成嵌入
```
POST /open-source/embeddings/generate
```

**Request**:
```json
{ "batch_size": 50 }
```

### 9.3 单人生成嵌入
```
POST /open-source/embeddings/generate/{developer_id}
```
