# 前端中英文切换（i18n）设计 — V5.1.1

**日期**：2026-08-30
**状态**：已确认
**范围**：前端 only（后端接口消息、数据库内容不翻）

## 已确认决策

| 决策点 | 结论 |
|--------|------|
| 覆盖范围 | 框架 + 全局骨架 + 高频用户页面（V5.1.1）；管理后台/系统配置页后续版本迁移 |
| 技术选型 | react-i18next |
| 翻译边界 | UI 文案全译 + 前端枚举展示双译；数据库业务内容与后端消息保持原文 |
| 默认与持久化 | 默认中文；顶栏切换器；localStorage(`i18n_lang`) 跨会话记忆 |

## 基础设施

```
src/i18n/
  index.ts          # i18next 初始化：lng=localStorage ?? 'zh'，fallbackLng='zh'，
                    # interpolation.escapeValue=false（React 已转义）
  locales/
    zh/{ns}.json    # 命名空间：common/nav/auth/academic/openSource/lab/
    en/{ns}.json    #        competition/industry/user/taxonomy
```

- 资源全量打包（zh+en 合计数百 KB 内，不做懒加载）
- **antd 联动**：App 根组件新增 LanguageProvider（zustand 或 React state）持当前语言；`<ConfigProvider locale={lang === 'zh' ? zhCN : enUS}>` 包裹，antd 内置文案（分页/日期/确认弹窗）随语言切换
- **切换器**：MainLayout 顶栏用户区「中 / EN」分段控件（Segmented）；切换即 `i18n.changeLanguage` + localStorage 写回 + Provider 状态联动，无刷新实时生效
- 页面一律 `const { t } = useTranslation('<ns>')`；跨命名空间用 `useTranslation(['common', '<ns>'])`

## V5.1.1 覆盖清单

| 层 | 文件范围 |
|----|---------|
| 骨架 | MainLayout（导航/域切换器/收藏/反馈/更新日志/用户菜单）、Footer、登录页、legal 页 |
| 通用组件 | TalentCompareModal、ExportConfirmModal、空态/加载/错误提示、分页汇总、getErrorMessage 兜底文案 |
| 学术域 | 首页、搜索页（含筛选栏）、人才详情、院校页 |
| 开源域 | 搜索页（含洞察面板标题层）、人才详情 |
| 实验室域 | 列表、详情、师承树节点标签 |
| 竞赛域 | 搜索页、详情 |
| 行业域 | 人才列表、详情 |
| 用户区 | 我的收藏、意见反馈 |

**枚举双译**：候选人状态（new/connected/terminated）、角色标签、学位层级、评分等级等前端展示映射全部改走 i18n；`domainThemes`/`theme/index.ts` 常量表中的中文标签（领域名）迁入 `taxonomy` 命名空间。

**不翻译**：数据库业务内容（人名/机构/岗位/学校）、后端 HTTPException 消息、CHANGELOG 更新日志内容（发布记录本身）、代码注释。

## 统一术语表（taxonomy 命名空间）

技术领域/要素等专有名词先定双语对照（示例）：人工智能→Artificial Intelligence、基础软件→Foundation Software、可信安全→Trusted Security、建模仿真与数学应用→Modeling & Simulation、大模型→LLM。术语表作为 `locales/{zh,en}/taxonomy.json` 单一事实源，所有页面引用不各自直译。

## 已知过渡状态（明确接受）

- 覆盖范围外页面（admin/系统配置/数据管理等）切换语言后仍显示中文——V5.2 起按域迁移消化，迁移清单登记于本文档附录
- 后端接口错误消息（如 401/403 detail）仍为中文——后续视需求做 Accept-Language 链路（不在本期）

## 测试策略

- `i18n/index` 单测：默认 zh、localStorage 恢复、changeLanguage 写回
- 切换器组件测试：点击切换后 antd ConfigProvider locale 与 i18n.language 同步
- 抽样双语言渲染断言：首页/搜索页在 en 下渲染英文关键文案（vitest）
- 既有组件测试中硬编码中文断言的，改引用 i18n key 断言或双语言兼容

## 工程纪律

- 新增页面/组件强制使用 `t()`，写入 AGENTS.md 开发 Checklist
- lint 层面后续可加自定义规则拦截新代码中的裸中文字符串（本期不强推）

## 附录：范围外迁移清单（V5.2+）

admin 用户管理/审计/数据版本、system-config 全部子页、LLM/代理/GitHub 配置页、向量生成、学术族谱/合作网络面板、竞赛/实验室/行业导入管理页。
