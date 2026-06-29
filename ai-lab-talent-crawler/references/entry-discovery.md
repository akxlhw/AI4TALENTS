# 入口发现判定规则

agent 从实验室主域名出发，自主寻找人才相关页面入口。本文件定义判定规则，
帮助 agent 决定哪些链接值得跟进、哪些应跳过。

## 值得跟进的链接（人才入口信号）

链接文本或 URL 含以下关键词时，优先跟进：
- People / Faculty / Team / Members / Staff / Group
- Research Groups / Labs / 实验室 / 课题组
- PhD Students / Students / 研究员 / 博士生 / 博士后

## 应跳过的链接

- 社交媒体：twitter.com / x.com / linkedin.com / youtube.com / github.com
- 新闻/博客：/news / /blog / /press
- 文件：.pdf / .jpg / .png / .zip
- 课程/招生：/courses / /admissions / /apply
- 导航骨架：Login / Search / Accessibility / Copyright

## 探索深度限制

从主域名起算，最多跟随 5 跳：
- 第 1 跳：主域名首页
- 第 2 跳：People/Faculty 或 Research Groups 页
- 第 3 跳：具体子实验室站点（如 nlp.stanford.edu）
- 第 4 跳：子实验室的 People 页
- 第 5 跳：个人的 bio 详情页

超过 5 跳 → 停止跟进，记录到报告。

## 子实验室发现

许多 AI 实验室（如 SAIL）由多个独立子实验室组成，各有自己的站点和 People 页。
当 agent 在主站发现 "Research Groups" 或类似页面时：
1. 提取所有子实验室链接
2. 逐个跟进，找其 People 页
3. 每个子实验室的人员标注 `lab_name` = 子实验室名，`parent_lab` = 顶层实验室名

## 入口发现失败的处理

若 agent 在主域名 + 2 跳内找不到任何 People/Faculty 类页面：
- 记录到报告："未找到人才入口，主站结构可能需要人工指引"
- 标注本次采集为 "needs review"
- 输出已发现的链接清单（供人工判断哪个是入口）
