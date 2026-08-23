# 系统迭代更新记录（更新日志）设计

**日期**：2026-08-23
**状态**：已确认
**范围**：前端 only，零后端改动

## 背景与目标

系统已迭代至 V5.0.0，`CHANGELOG.md` 按 Keep a Changelog 规范持续维护，但只有开发者看得到。目标：让**管理员和普通用户**都能在系统内查看版本迭代历史，"看清来时路"。

## 已确认的决策

| 决策点 | 选择 |
|--------|------|
| 数据源 | 解析 `CHANGELOG.md`（前端构建期 vite `?raw` 打包，单一事实源，零双份维护） |
| 入口 | 导航栏「意见反馈」旁新增「更新日志」按钮 + 右侧抽屉时间线；所有登录用户可见 |
| 粒度 | 全量原文，按版本折叠（默认展开最新版） |
| 新版本提醒 | 入口按钮小红点（localStorage 已读标记 vs 最新版本号），打开即消 |

## 数据流

```
CHANGELOG.md（Keep a Changelog 格式）
  → vite 构建期 import ... from '../../../CHANGELOG.md?raw'（打包进产物）
  → parseChangelog() 纯函数解析
      releases: { version, date | null, sections: { [group: string]: string[] } }[]
      [Unreleased] 段跳过不展示
  → ChangelogDrawer 渲染（antd Drawer + Timeline + Collapse）
  → 红点比对：localStorage('changelog_last_seen') !== releases[0].version
```

## 组件清单

| 文件 | 职责 |
|------|------|
| `frontend/src/utils/changelog.ts` | 解析器纯函数 + 类型；`parseChangelog(raw): ChangelogRelease[]`；容错：任何段落解析失败跳过该段，整体失败返回 `[]` |
| `frontend/src/components/ChangelogDrawer.tsx` | 抽屉组件。纵向 Timeline，每版一张卡片：版本号徽标（最新版高亮 Tag "最新"）+ 日期 + 按 Added/Changed/Fixed/Removed/Security 分组渲染条目列表（保持分组原文顺序）；最新一版默认展开、其余 Collapse 折叠；长内容抽屉内滚动 |
| `frontend/src/utils/changelog.test.ts` | 解析器单测：真实 CHANGELOG 片段、无日期版本、空分组、[Unreleased] 跳过、解析容错 |
| `frontend/src/App.tsx`（导航布局处） | 「意见反馈」旁加「更新日志」按钮（Badge 红点 + HistoryOutlined 图标），点击开抽屉；打开时写入已读版本号 |

版本号来源：解析结果的第一个 release（不依赖 health 接口，避免异步竞态）。

## 交互细节

- 抽屉宽 ~520px，标题「更新日志」+ 副标题当前版本号
- 时间线节点用版本号，卡片含日期与分组内容
- 分组标题用带色 Tag：Added=green、Changed=blue、Fixed=orange、其余=default
- 条目文本保留原文（含加粗/链接等 markdown 记号的按纯文本显示即可——条目以中文功能描述为主，不引入 markdown 渲染引擎）

## 错误处理

- 解析返回空数组 → 抽屉显示"暂无更新记录"空态（Empty）
- CHANGELOG 未打包（理论不可能，构建期导入）→ 构建即失败，无运行时分支

## 测试

- 解析器单测覆盖：正常解析（版本数、分组、条目数）、[Unreleased] 跳过、无日期版本容错、畸形输入返回空数组
- 组件冒烟测试：渲染出最新版本号与分组 Tag
- 验证：tsc / eslint / vitest / npm run build 全绿

## 不做的事

- ❌ 后端接口 / 数据库表 / 管理员编辑（CHANGELOG.md 随代码发布即同步）
- ❌ 登录弹窗打扰（用户主动查看 + 入口红点提示）
- ❌ markdown 渲染引擎依赖
- ❌ 逐 commit 粒度（CHANGELOG 版本粒度即发布粒度）

## 风险与对策

| 风险 | 对策 |
|------|------|
| CHANGELOG 格式漂移导致解析退化 | 格式已两年稳定（Keep a Changelog + 发布脚本约束）；解析器容错跳过异常段；单测用真实片段锁定行为 |
| 前后端版本短暂不一致（前端新于后端） | 更新日志展示的是前端产物内嵌数据，与页面本身版本天然一致，无此问题 |
