"""Privacy compliance service."""

from __future__ import annotations

from datetime import datetime

from app.domains.shared.services.user_service import UserService

# Privacy policy text (Chinese) - version bound to APP_VERSION
PRIVACY_POLICY_TEXT = """# 隐私政策

## 1. 引言

AI4TALENT 智能人才库（以下简称"本平台"）是由您的组织内部运营的人才发现平台。本隐私政策旨在向您说明我们如何收集、使用、存储和保护您的个人信息，以及您享有的相关权利。

## 2. 【红线条款】人才数据使用限制

> **本条款为平台核心约束，请务必仔细阅读。**

本平台展示的所有人才数据（包括但不限于姓名、所属机构、研究方向、发表论文、联系方式等）**仅供用户所在组织内部的人才发现、研究评估与人才画像参考使用**。

**您明确承诺并同意：**

1. **严禁**直接通过系统中的邮箱、电话、社交媒体等任何渠道向人才本人发起招聘邀约、商业 solicitation 或任何未经人才本人同意的联系行为；
2. **严禁**将平台人才数据以任何方式提供给第三方招聘机构、猎头公司或人力资源服务商；
3. **严禁**将人才数据用于商业营销、数据贩卖、算法训练数据集构建等任何超出本平台服务目的的用途；
4. **严禁**对人才数据进行大规模自动化爬取、镜像或建立竞争性数据库。

**违规后果**：一经发现，平台有权立即暂停或永久封禁您的账号，并保留追究法律责任的权利。

## 3. 我们收集哪些信息

### 3.1 账号信息
- 用户名、电子邮箱、工号、部门、密码哈希
- 用户角色（普通用户/管理员/超级管理员）

### 3.2 使用行为信息
- 搜索关键词、筛选条件、浏览记录
- 收藏、导出、对比等操作记录
- 默认视图偏好、列设置等功能偏好

### 3.3 设备与日志信息
- IP 地址、浏览器类型、操作系统
- 操作时间戳（用于安全审计与异常检测）

## 4. 我们如何使用您的信息

- **提供服务**：人才搜索、推荐、匹配、收藏管理
- **安全审计**：账号安全监控、异常行为检测
- **产品改进**：基于去标识化数据的算法优化与功能改进
- **权限管理**：基于学校/国家/技术领域的三维数据访问控制

## 5. 数据共享与第三方
- **除法律法规要求外**，我们不会向任何第三方出售、出租或以其他方式披露您的个人信息

## 6. 数据存储与安全

- 数据存储于中国大陆境内的服务器
- 采用 HTTPS 加密传输、bcrypt 密码哈希等行业标准安全措施
- 定期备份与灾难恢复机制

## 7. 您的权利

- **查阅与更正**：通过"个人信息"页面查看和修改您的账号信息
- **删除**：联系管理员删除您的账号及关联数据
- **撤回同意**：在"个人信息"页面撤回隐私政策同意，撤回后账号将被禁用
- **注销账号**：请联系系统管理员处理账号注销

## 8. 本地存储与 Cookie

- **必要类**：JWT Token（维持登录状态）
- **功能类**：视图偏好、列设置、主题选择
- **分析类**：（当前未启用，启用前将重新征求您的同意）

## 9. 未成年人保护

本平台仅面向组织内部成年员工开放，不主动收集未成年人个人信息。

## 10. 政策更新

我们可能会根据法律法规变化或产品功能更新不时修订本政策。重大变更将通过平台公告或邮件通知您。

**当前版本**：v2.1.0
**最后更新日期**：2026-05-25
**如有疑问，请联系系统管理员韩观振 h00445028**
"""

TERMS_OF_USE_TEXT = """# 用户协议

## 1. 账号注册与使用

1.1 您必须使用真实有效的组织邮箱和工号注册账号。
1.2 账号仅限本人使用，不得转让、借用或共享。
1.3 您有责任保管好自己的账号密码，因密码泄露导致的损失由您自行承担。

## 2. 【核心条款】人才数据使用限制

> **本章节为平台最核心的法律约束，请仔细阅读并严格遵守。**

2.1 **数据用途限制**：平台展示的人才数据（包括但不限于姓名、机构、研究方向、联系方式等）**仅供您所在组织内部的人才发现、研究评估与人才画像参考使用**。

2.2 **禁止直接联系**：您**承诺并保证**不会将平台展示的任何人才联系方式（包括但不限于电子邮箱、电话、社交媒体账号）用于：
- 直接向人才本人发起招聘邀约或职位推荐
- 向人才发送商业 solicitation、营销信息或问卷调查
- 任何未经人才本人事先明确同意的联系行为

2.3 **禁止数据外传**：您**承诺并保证**不会将平台人才数据以任何形式提供给：
- 第三方招聘机构、猎头公司或人力资源服务商
- 外部合作伙伴或关联公司
- 任何非本平台授权的个人或组织

2.4 **禁止竞争性使用**：您**承诺并保证**不会：
- 对平台人才数据进行大规模自动化爬取、抓取或镜像
- 基于平台数据建立竞争性人才数据库或服务
- 将数据用于算法训练、模型构建等超出本平台服务目的的范围

2.5 **数据来源说明**：您理解并同意，平台展示的人才数据来源于公开学术数据库和开源社区，平台仅提供数据聚合、检索与可视化服务，**不对数据的招聘可用性做任何授权或保证**。

2.6 **违规后果**：违反上述 2.2-2.4 条任一条款的，平台有权：
- 立即暂停或永久封禁您的账号
- 保留追究您法律责任的权利
- 向您的组织通报违规情况

## 3. 知识产权

3.1 平台本身的代码、界面设计、算法逻辑等知识产权归平台运营方所有。
3.2 人才数据的相关权利归数据原始发布方所有，平台仅做合法范围内的引用与展示。

## 4. 免责声明

4.1 平台按"现状"提供服务，不保证数据的完整性、准确性或实时性。
4.2 因不可抗力、第三方服务中断等原因导致的服务不可用，平台不承担责任。
4.3 因您违反本协议或隐私政策导致的任何纠纷或损失，由您自行承担。

## 5. 协议变更与终止

5.1 平台有权根据需要修订本协议，修订后将在平台公告。
5.2 如您不同意修订后的协议，应停止使用平台服务并联系管理员注销账号。
5.3 平台保留因运营需要终止服务的权利，终止前将提前通知用户。

**当前版本**：v2.1.0
**生效日期**：2026-05-25
"""


class PrivacyService:
    """Service for privacy compliance operations."""

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    async def update_privacy_consent(
        self,
        user_id: int,
        policy_version: str,
        terms_version: str,
        storage_consent_level: str,
        accepted: bool = True,
    ) -> bool:
        """Update user's privacy consent record."""
        now = datetime.now() if accepted else None
        return await self.user_service.update_privacy_consent_and_commit(
            user_id=user_id,
            privacy_policy_accepted_at=now,
            privacy_policy_version=policy_version if accepted else None,
            terms_of_use_accepted_at=now,
            terms_of_use_version=terms_version if accepted else None,
            storage_consent_level=storage_consent_level,
        )

    async def get_privacy_consent_status(self, user_id: int) -> dict | None:
        """Get user's privacy consent status."""
        return await self.user_service.get_privacy_consent_status(user_id)

    @staticmethod
    def get_privacy_policy_text() -> str:
        """Return privacy policy text."""
        return PRIVACY_POLICY_TEXT

    @staticmethod
    def get_terms_of_use_text() -> str:
        """Return terms of use text."""
        return TERMS_OF_USE_TEXT
