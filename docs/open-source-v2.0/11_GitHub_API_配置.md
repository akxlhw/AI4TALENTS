# 开源人才子系统 - GitHub API 配置说明 (v2.0.0)

**文档编号**�?1  
**版本**：v2.0.0  
**状�?*：已实现  
**适用范围**：智能人才库—开源人才子系统 V2.0.0

---

## 1. 为什么需�?GitHub Token

开源人才子系统通过 GitHub REST API �?GraphQL API 采集仓库、贡献者、提交记录、PR、Issue 等数据�?*GitHub 对未认证请求的速率限制为每小时 60 �?*，无法满足采集需求。使�?Personal Access Token 后：

| 场景 | 速率限制 |
|------|---------|
| 未认�?| 60 req/hour |
| Personal Access Token | 5,000 req/hour |
| GitHub App / Enterprise | 15,000+ req/hour |

---

## 2. 配置方式

### 2.1 方式一：环境变量（推荐，生产环境）

�?`backend/.env` 文件中添加：

```bash
# GitHub API Token（多�?Token 用逗号分隔，用于轮询负载均衡）
GITHUB_TOKENS=ghp_xxxxxxxxxxxxxxxxxxxx,ghp_yyyyyyyyyyyyyyyyyyyy

# GitHub API 基础地址（企业版可修改为内部 GitHub Enterprise 地址�?GITHUB_BASE_URL=https://api.github.com

# �?Token 每小时请求上限（用于速率监控预警�?GITHUB_RATE_LIMIT=5000
```

**�?Token 轮询说明**�?- 当系统持有多�?Token 时，`GitHubClient` 会自动轮询使用，扩展总请求量
- 例如 3 �?Token = 15,000 req/hour 的理论上�?- 某个 Token 触发 403 (rate limit) 时，自动切换到下一个可�?Token

### 2.2 方式二：运行时动态配置（规划中）

未来版本支持通过系统配置页面 UI 配置 Token，写入数据库 `system_config` 表，无需重启服务。当�?版本仅支持环境变量�?
---

## 3. 如何获取 GitHub Personal Access Token

### 步骤 1：登�?GitHub 账户
访问 https://github.com/settings/tokens

### 步骤 2：创�?Token
点击 **Generate new token (classic)**，勾选以下权限：

| 权限�?| 说明 |
|--------|------|
| `repo` | 读取公开和私有仓库数据（开源子系统仅需公开仓库，但建议全选） |
| `read:user` | 读取用户公开资料 |
| `read:org` | 读取组织公开资料 |

> 注意：Fine-grained personal access tokens 目前**不推荐使�?*，因为部�?GitHub API 端点仍需�?classic token�?
### 步骤 3：保�?Token
生成�?*立即复制并保�?*，GitHub 只显示一次。将 Token 写入 `.env` 文件�?
---

## 4. 配置验证

启动后端后，访问 Swagger UI 测试 Token 有效性：

```bash
curl -H "Authorization: Bearer <your-admin-jwt>" \
  http://localhost:8003/api/v1/open-source/stats
```

或通过后端脚本直接测试 GitHub API 连通性：

```python
# backend/scripts/test_github_token.py（可手动创建�?import os
import httpx

token = os.environ["GITHUB_TOKENS"].split(",")[0]
resp = httpx.get(
    "https://api.github.com/rate_limit",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.json()["rate"])
# 预期输出包含 limit: 5000, remaining: 4999...
```

---

## 5. 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 采集任务启动后全部失�?| Token 未配置或已过�?| 检�?`.env` �?`GITHUB_TOKENS`，重新生�?Token |
| 请求返回 401 Unauthorized | Token 无效或权限不�?| 确认 Token 拥有 `repo` �?`read:user` 权限 |
| 请求返回 403 rate limit | �?Token 配额耗尽 | 增加更多 Token（逗号分隔），或减少采集并�?|
| 企业内网无法访问 api.github.com | 网络受限 | 配置代理（`PROXY_ENABLED=true`），或改�?GitHub Enterprise |

---

## 6. 安全注意事项

1. **Token 不要提交�?Git**：`.env` 已加�?`.gitignore`，务必确认无�?2. **生产环境使用专用 Token**：不要与个人开�?Token 混用，建议创建一个仅用于采集�?GitHub 账户
3. **定期轮换**：建议每 90 天更换一�?Token，GitHub 会在 Token 即将过期时发邮件提醒
4. **Token 泄露应�?*：立即在 GitHub 上删除该 Token，生成新的并更新 `.env`，重启后端服�?
---

## 7. 相关代码位置

| 文件 | 说明 |
|------|------|
| `backend/app/core/config.py:34-37` | 配置定义（`GITHUB_TOKENS`, `GITHUB_BASE_URL`, `GITHUB_RATE_LIMIT`�?|
| `backend/app/services/common/http_client.py` | HTTP 客户端工厂（支持代理配置�?|
| `backend/app/api/v1/endpoints/open_source.py` | API 路由（Token 通过 `get_current_user` 校验，与 GitHub Token 无关�?|

---

## 8. 与现有系统配置的关系

| 配置�?| 配置位置 | 开源子系统使用方式 |
|--------|---------|------------------|
| GitHub Token | `.env` �?`GITHUB_TOKENS` | 采集器读取，�?Token 轮询 |
| 代理配置 | 系统配置�?/ `.env` �?`PROXY_*` | `HttpClientFactory` 全局生效，含 GitHub 请求 |
| LLM API | 系统配置�?/ `.env` �?`LLM_*` | 嵌入生成阶段调用，与 GitHub API 独立 |
