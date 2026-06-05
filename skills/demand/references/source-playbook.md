# 选源 Playbook —— 不同需求类型挖哪些源

先判断需求类型，再选源。每个源生成 2-4 个搜索变体，中英都要，竞品名进 query。

## 需求类型 → 源优先级

| 需求类型 | 自上而下（权威） | 自下而上（社区/评论） |
|---|---|---|
| **B2B SaaS / 工具** | Gartner/IDC/Forrester、融资数据、竞品财报、定价页 | HN、r/SaaS·r/startups、G2 摘要、Product Hunt |
| **消费 App / 小程序** | Statista、QuestMobile、应用商店榜单 | App Store/Google Play 评论、小红书、TikTok、Reddit |
| **实体 / 电商** | 行业报告、海关/统计局、Trends | Amazon 评论（付费版）、Reddit、社交种草 |
| **内容 / 创作者** | 平台官方数据、MCN 报告 | YouTube/B站评论、创作者社区、Discord |
| **通用 / 不确定** | 先 WebSearch 行业综述定盘子 | HN + Reddit + 应用商店评论打底 |

## 搜索变体设计（每个源 2-4 个）

围绕 hypothesis 的不同侧面，不要只换同义词：

1. **痛点变体**：`<场景> frustrating OR "pain" OR "hate that"`、`<产品> 太难用 OR 吐槽`
2. **替代方案变体**：`<job> alternative OR "instead of" OR "I use"`、`<竞品> vs`
3. **付费信号变体**：`<方案> worth it OR pricing OR "would pay"`、`<品类> 值不值`
4. **市场规模变体**：`<品类> market size OR CAGR OR forecast 2025`
5. **趋势变体**：`<品类> growing OR declining OR trend`、Google Trends 对比

## 搜索过滤技巧（降噪）

- `site:reddit.com` / `site:news.ycombinator.com` / `site:v2ex.com` 限定真实社区
- `-site:csdn.net -"广告" -"推广" -"通稿"` 排 SEO 垃圾和通稿
- `"评测" OR "对比" OR "体验"` 聚焦真实评价
- 中国产品至少一个变体专搜中文社区（知乎/小红书/V2EX/即刻），避免英文源偏差

## 连接器速查

| 源 | 命令 | 拿到什么 |
|---|---|---|
| Hacker News | `python3 scripts/connectors/hn_algolia.py "<query>"` | 评论/帖子 + 分数 + URL |
| App Store 查找 | `python3 scripts/connectors/itunes.py search "<app名>"` | app id + 评分 + 评分数 |
| App Store 评论 | `python3 scripts/connectors/itunes.py reviews <app_id>` | 真实评论 + 星级 |
| Google Play | `python3 scripts/connectors/play_reviews.py "<包名>"` | 评论 + 星级 |
| Reddit | `python3 scripts/connectors/reddit.py "<query>"` | 帖子 + 赞/评论数 |
| 权威报告/趋势 | WebSearch + WebFetch | 市场规模/增长/资本 |

## 反偏误提醒

- 别只搜支持假设的词。每个源至少留一个变体专搜**反面**（「为什么没人用」「失败」「已经够用」）。
- 竞品差评比好评信息量大，优先挖 1-3 星评论里的缺口。
- 沉默市场（to B、老年、蓝领）社区讨论少，不等于没需求，需靠自上而下支柱补。
