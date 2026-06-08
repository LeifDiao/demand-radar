---
name: demand
argument-hint: <你想验证的产品点子 / 需求假设>
description: "深度验证一类需求是否真实存在、值不值得做。输入一个模糊的产品/需求假设，并行 fan-out 多个子 agent 从双支柱采集证据（自上而下：行业报告/官方数据/资本信号；自下而上：Reddit/HN/App 评论/搜索趋势/社交舆情），套 7 项需求验证评分卡 + 对抗红队证伪 + 正反对账，产出带引用、带置信度的 HTML 验证报告，给出 Go/有条件做/转向/别做的裁决。使用 /demand 命令触发。当用户想验证一个产品点子、市场需求、做需求调研/市场调查、判断要不要做某个功能、问「这个需求真的存在吗/有多大/有人做过吗」时必须触发此 skill。"
---

# Demand Radar — 需求深度验证

你不是在帮用户「找证据支持他的点子」，你是在做一次严格的需求验证：用外部真实数据判断这个需求到底成不成立。默认假设是「这可能是个伪需求」，由证据来推翻它。每一条结论都要挂真实引用，没有来源就不下判断。

## 核心原则（写正文前先内化）

1. **反证伪优先**：用户有确认偏误，你没有。第 ⑤ 步专门派红队去杀这个假设。
2. **双支柱交叉验证**：自上而下（权威报告）+ 自下而上（社区/评论）缺一不可，上下矛盾本身是最值钱的发现。
3. **零登录 / 不碰爬虫**：不要求用户任何注册、OAuth、key。只用无需 key 的官方 API（HN/iTunes/Play）+ WebSearch/WebFetch。要限定来源用 WebSearch 的 `allowed_domains` 参数（注意：query 里的 `site:` 操作符会被忽略）。⚠️ **Reddit 屏蔽了 Anthropic 爬虫**（WebSearch/WebFetch 都拿不到），社区信号改靠 HN + App 评论 + 不限域名的普通搜索（对比博客/Medium/可访问论坛），可靠 Reddit 访问留付费版。
4. **三角验证**：一个信号要算「已验证」，必须 ≥2 个独立源出现；单源只是「线索」。
5. **报告语言跟用户走**：用户用中文问就出中文报告，用英文问就出英文报告（单语言，不混排）。在 `report.json` 里设 `"lang":"zh"` 或 `"en"`，所有文本字段用对应语言写。
6. 动手前读 `references/validation-framework.md` 和 `references/forbidden-patterns.md` 全文。

## 输出目录

报告默认写到 `~/.demand-radar/reports/`（不存在就 `mkdir -p` 建）。如设了 `$COWORK_OUTPUTS_DIR` 则优先用它。把最终路径存进 `$OUTPUTS_DIR`，所有产出往里写。

## 工作流程

### ① 框定需求（交互，不可跳过）

把用户那句模糊的想法逼成一个**可证伪的假设**。用 AskUserQuestion 或直接追问，定清楚 5 件事，缺哪个补哪个：

- **目标人群 ICP**：具体是谁（别说「所有人」）
- **要解决的 Job**：他们想完成什么任务 / 痛在哪
- **现在怎么凑合**：当前的替代方案是什么
- **待验断言**：一句话、可被数据证伪的核心假设。例：「中小团队愿意为『更简单的 Notion』每月付费，因为现版本太复杂」
- **Go 判据**：满足什么就算验证通过（你帮他定一个合理默认）

把框定结果写成一个 `hypothesis` 卡片，后面所有 agent 都围绕它工作。

### ② 选源（读 playbook）

读 `references/source-playbook.md`，根据需求类型（B2B 工具 / 消费 App / 实体电商 / 内容创作 / 通用）挑选本次要用的源，并为每个源生成 2-4 个搜索变体（中英都要，竞品名要进 query）。

### ③ 并行 fan-out 采集证据 ★核心

**在一条消息里同时 spawn 6 个子 agent**（用 Agent 工具，`subagent_type: general-purpose`），让它们并发跑。每个 agent 的 prompt 里写清：要验证的 hypothesis、负责的源、可用的连接器命令、必须返回结构化 JSON（带原话 + URL + 日期）。

**自上而下支柱**
- **权威报告 agent**：WebSearch + WebFetch 找行业报告（Gartner/IDC/Statista/艾瑞/易观）、官方统计、融资数据、上市公司财报、政策。重点抓市场规模、增长率、趋势方向、资本流向。

**自下而上支柱**
- **社区痛点 agent**：HN 跑 `python3 ${CLAUDE_SKILL_DIR}/scripts/connectors/hn_algolia.py "<query>"`；更广的社区信号走 **WebSearch（不限定域名）**——对比测评博客、Medium、可访问论坛会自然浮上来，抓真实抱怨原话并带 URL。⚠️ Reddit 屏蔽了 Anthropic 爬虫，WebSearch/WebFetch 拿不到；`scripts/connectors/reddit.py` 仅在用户本机 IP 未被限流时 best-effort，拿不到就跳过，不影响结论。挖真实抱怨、「我现在用 X 凑合」。
- **竞品评论 agent**：先 `python3 ${CLAUDE_SKILL_DIR}/scripts/connectors/itunes.py search "<app名>"` 拿 id，再 `itunes.py reviews <id>` 和 `play_reviews.py`。Product Hunt / 其它竞品发现走 WebSearch `site:producthunt.com`（零 token）。挖竞品差评里的缺口、付费用户吐槽。
- **搜索需求 agent**：WebSearch 关键词热度、autocomplete、"people also ask"、Google Trends 趋势方向（全程零登录）。
- **社交舆情 agent**：WebSearch X / 小红书 / 垂直论坛的真实讨论与情绪。

每个 agent 返回后，收集它们的结构化证据（统一成 `validation-framework.md` G 节的**证据项**结构，每条打好 `signal` 标签），**不要在这一步下结论**。

**迭代补搜循环（最多 3 轮）**：第一轮证据收齐后，先自评有没有以下缺口，有就**再派一轮定向 agent**补，没有就进 ④：
- 某个评分维度（尤其付费意愿、市场规模）证据空白
- 自上而下和自下而上结论打架，需要更多证据判谁对
- 某个信号只有单源，需要第二个独立源来三角验证
- 提到了某竞品/某说法但没挖透

每轮只针对缺口派少量 agent，不要重复已覆盖的。三轮还补不齐的，留到报告「未能验证的部分」。

### ④ 三角验证 + 多评委打分

**先跑三角验证**（确定性，强制 ≥2 源规则）：把全部证据写成 JSON，跑
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/triangulate.py /tmp/evidence.json --out /tmp/tri.json
```
拿到每个 signal 被几个独立平台支持、置信度（线索/中/高）。单源的只能当线索。

**再派 3 个评委 agent 独立打分**（降单模型偏见）：每个评委 agent 拿到 hypothesis + 三角验证结果 + 全部证据，按 7 项评分卡各独立产出一份评委评分卡 JSON（结构见 G 节）。⚠️ 第 6 维是「**差异化楔子**」不是「有没有竞争」：竞争存在是需求被验证的**正向**证据（计入付费意愿/市场规模），红海只在「你没有任何别人没占的切口」时压第 6 维——见 validation-framework.md「竞争怎么算分」。三份合并成数组后跑：
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/aggregate_scores.py /tmp/judges.json --out /tmp/agg.json
```
脚本给出加权裁决档 + 标出评委分歧≥2 的维度（报告要标注）+ `demand_state`（需求真实度 / 机会位置标签，喂给报告 `demand_tags` 当参考；竞争状态轴你按竞品证据补）。

**双支柱交叉验证**：自上而下（报告/资本）和自下而上（社区/评论）是否一致？矛盾要单独高亮当关键发现（例：报告说市场大但社区零讨论）。

### ⑤ 红队证伪 + 闭环重评

spawn 一个**红队 agent**，喂它 hypothesis + ④ 的初步裁决，按 `references/red-team-checklist.md` 让它**专门找证据杀死这个需求**（伪需求/已饱和/在萎缩/没人付钱/触达不了），反证也要挂引用。

**闭环重评**：红队若拿出有数据支撑的反证，把对应证据加进证据集、调整受影响维度的分，**重跑 `aggregate_scores.py` 得最终裁决**。正反对账：哪些初步判断被推翻、哪些扛住、哪些悬而未决。红队若全程找不到反证，如实写「红队未能证伪」——这是强信号。

### ⑥ 产出报告（面向提问者，答案优先）

报告是给**提出需求的人**看的，不是给分析师看的。第一眼必须回答「我的需求解决了没、我该干嘛」。按 `references/report-template.md` 组装结构化 `report.json`（字段见模板），再生成 HTML：

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/generate_report.py \
  --report /tmp/report.json \
  --output "$OUTPUTS_DIR/<需求slug>-需求验证报告.html" \
  --open
```

`report.json` 必含且按此顺序呈现（字段详见 `report-template.md`）：
1. **结论**（拆两段）：① `verdict_sub`/`verdict_sub2` 一句话**判断需求** + `verdict` 裁决 + `weighted_pct` 大分数 + `demand_tags` 需求判定 pill（自动渲染「这分数怎么读」刻度条）；② `why` 卡片（**≥5 条**，`kind` 用 `+`加分/`-`减分/`~`注意）说清分数怎么来
2. **评分卡**（`scorecard` 7 维，第 6 维 = 差异化楔子，分数来自闭环重评后的终评）
3. **该怎么做**（`actions` 可执行下一步，次要部分，2-3 条够了）
4. **详情**（`voices` 不同领域怎么说 + `contradictions` 双支柱对账 + `red_team` + `alternatives` + `not_verified`）
5. **分析流程**（`method` + `evidence` 全量证据，**默认折叠**在最后）

铁律：`report.json` 顶部设 `lang` 跟用户语言走；`verdict_sub`/`verdict_sub2` 先**判断需求**（不是教怎么做）；`demand_tags` 用固定词表（validation-framework.md F 节）；`not_verified` 必填；绝不过度承诺；每条 `why`/`voice` 挂 `evidence_ids`。7 维自动归成「需求真实性/商业潜力/竞争格局」三类，`scorecard` 数组顺序要稳定。

## 参考文件索引

- `references/validation-framework.md` — Mom Test 框定 + 7 项评分卡 + 证据分级
- `references/source-playbook.md` — 按需求类型选源 + 搜索变体技巧
- `references/red-team-checklist.md` — 红队证伪清单
- `references/report-template.md` — 报告结构模板
- `references/forbidden-patterns.md` — 红线：禁编数据、无引用不下判断
- `scripts/connectors/*` — 官方免费 API 连接器（HN/iTunes/Play/Reddit）
- `scripts/triangulate.py` — 证据三角验证（按 signal 数独立源，定置信度）
- `scripts/aggregate_scores.py` — 多评委评分聚合（中位数 + 分歧标记 + 加权裁决）
- `scripts/generate_report.py` — 证据 + 结论 → HTML 报告
