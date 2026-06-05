# Demand Radar

> **A Claude Code plugin that validates whether a demand is real — before you build it.** Frame a falsifiable hypothesis, fan out parallel agents across two evidence pillars, score it on 7 axes with source triangulation, run an adversarial red-team that *tries to kill your idea*, and ship an answer-first HTML report with a clear verdict: **Go / Conditional / Pivot / No-go.** Zero login, no scrapers.

🌏 [中文版](./README_zh.md) · 📖 [Methodology](./docs/METHODOLOGY.md) · 🖥 [Live page](https://leifdiao.github.io/demand-radar/) · ⚖️ [License](./LICENSE)

> **中文简介：** 一款 Claude Code 插件，在你动手做之前帮你验证「这个需求到底是不是真的」。把模糊想法逼成可证伪假设，并行派多个 agent 从两根证据支柱采集，套 7 项评分卡 + 来源三角验证，再让一个对抗红队*专门证伪*，最后产出一份「答案优先」的 HTML 报告，给出明确裁决：**可以做 / 有条件做 / 转向 / 别做**。全程零登录、不写爬虫。完整中文文档 → [README_zh.md](./README_zh.md)

---

## Why this exists

You have a product idea. Before writing a line of code, you want to know: **is this demand real, how big is it, who has it, what do they use today, and will they pay?** Most founders either guess, or drown in scattered Google tabs and confirmation bias.

The tools that exist are either single-source (Reddit-only pain miners) or generic "deep research" with no validation framework and no devil's advocate. **Demand Radar packages multi-source evidence collection + a demand scorecard + an adversarial red-team into one repeatable run** — and it's built to *fight your confirmation bias*, not feed it.

---

## Key features

**🎯 Real evidence, two pillars.** Every verdict stands on both **top-down** (industry reports, market size, growth, capital signals) and **bottom-up** (Hacker News, App Store / Google Play reviews, search demand, social). When the two disagree — "analysts say the market is huge but nobody's complaining" — that contradiction *is* the finding.

**🔴 An adversarial red-team, by design.** You have confirmation bias; the red-team doesn't. A dedicated agent's only KPI is to **kill your hypothesis** — fake demand, saturated, declining, nobody pays, can't reach them, sample bias. Any "Go" has to survive it. In testing it pulled a verdict from *Conditional (55%)* down to *Pivot (40%)* by surfacing a buyer-mismatch the optimistic read had missed.

**📐 A 7-axis scorecard with hard rules.** Pain intensity · prevalence · current-alternative gap · **willingness to pay** (weighted ×2) · market size & trend · competition/whitespace · reachability. A signal counts as *verified* only when **≥2 independent sources** confirm it — single-source stays a "lead." Three independent judge agents score in parallel; disagreements are flagged, not averaged away.

**📋 Answer-first reports, not analyst dumps.** The report opens with **your question → a plain-language verdict → what to do next**. Scores, details, and the full method/evidence trail come after, collapsed. Every claim cites an evidence ID you can click to trace.

**🔒 Zero login, no scrapers, no keys.** Official free APIs (Hacker News, iTunes; Google Play optional, needs a pip library) + web search only. Nothing to register, no OAuth, no anti-bot games. Reports render to a single self-contained HTML file.

**🌐 Speaks your language.** Ask in English → English report. 用中文问 → 中文报告.

> **中文要点：**
> - **🎯 双支柱证据**：自上而下（行业报告/市场规模/资本）+ 自下而上（HN/应用商店评论/搜索/社交），上下矛盾本身就是关键发现
> - **🔴 内置对抗红队**：唯一 KPI 是*杀死你的假设*，任何「可以做」都要先扛住它（实测把「有条件做 55%」拉到「转向 40%」）
> - **📐 7 项评分卡 + 硬规则**：付费意愿 ×2；信号需 ≥2 独立源才算「已验证」；3 评委并行打分，分歧标红不和稀泥
> - **📋 答案优先**：报告开头就是「你的问题 → 大白话裁决 → 该怎么做」，分析过程和证据折叠在后面，每条结论可点击溯源
> - **🔒 零登录、不写爬虫**：只用免费官方 API + 网页搜索，无需注册/OAuth/key
> - **🌐 跟你的语言走**：英文问出英文报告，中文问出中文报告
>
> 完整中文版 → [README_zh.md](./README_zh.md)

---

## What the report includes

Run `/demand <your idea>` and get a single-file, answer-first HTML report:

1. **Verdict** — Go / Conditional / Pivot / No-go, with a plain-language answer to "is my demand real, and why," plus a confidence level.
2. **What to do next** — concrete, pastable action cards (change your buyer, narrow the niche, run a pre-sale), prioritized. The part founders actually use.
3. **Scorecard** — 7 axes with visual bars, post-red-team final scores, and the weighted percentage.
4. **Details** — key findings, the two-pillar reconciliation, the red-team's most lethal flaw, a current-alternatives map, and an explicit **"what we could NOT verify"** section. No over-promising.
5. **Method & sources** — collapsed at the bottom: agent count, evidence count, the full pipeline, and a clickable evidence appendix.

---

## Install

**Step 1** — Add the marketplace:

```
/plugin marketplace add LeifDiao/demand-radar
```

**Step 2** — Install the plugin:

```
/plugin install demand-radar@demand-radar-marketplace
```

**Alternative (local):**

```bash
git clone https://github.com/LeifDiao/demand-radar.git ~/demand-radar
claude --plugin-dir ~/demand-radar
```

---

## Use

```
/demand a simpler Notion for small remote teams
```

1. Demand Radar turns your idea into a falsifiable hypothesis (ICP / job / current workaround / the claim / Go criteria) — it'll ask if anything's unclear.
2. It fans out parallel collector agents across both pillars (real searches + free APIs).
3. It triangulates evidence, runs 3 independent judges, then the red-team.
4. The report opens in your browser.

---

## Requirements

- **Claude Code** with plugin support
- **Python 3** (for the connectors and report generator — standard library only)
- Optional: `pip install google-play-scraper` to enable Google Play reviews
- No API key, no build step, no server

---

## How it works

**Two-layer model — the model judges, scripts enforce:**

1. **Evidence** — parallel agents collect from official free APIs + web search, each item tagged with a `signal` and a source type (hard / behavioral / opinion / analyst). `triangulate.py` enforces the **≥2-independent-sources** rule deterministically.
2. **Scoring** — three judge agents (neutral / optimistic / strict) score the 7 axes independently; `aggregate_scores.py` takes the median, flags disagreements, and computes the weighted verdict. The red-team then re-scores in a closed loop.

**Anti-bias mechanisms:**

- **Adversarial red-team** before any verdict is final
- **Triangulation** — single-source signals can't masquerade as verified
- **Forced "what we couldn't verify"** section — "not found" is never written as "doesn't exist"
- **Opinion ≤ lead** — "I'd buy it" never supports a willingness-to-pay conclusion on its own

👉 [Read the full Methodology](./docs/METHODOLOGY.md)

---

## Project structure

```
demand-radar/
├── .claude-plugin/
│   ├── plugin.json                   # plugin manifest
│   └── marketplace.json              # marketplace entry
├── skills/demand/                    # invoked as /demand-radar:demand
│   ├── SKILL.md                      # frame → fan-out → triangulate → judge → red-team → report
│   ├── references/                   # validation framework, source playbook, red-team checklist, templates
│   └── scripts/
│       ├── connectors/               # hn_algolia · itunes · play_reviews (free APIs) · reddit (best-effort)
│       ├── triangulate.py            # ≥2-source confidence rule
│       ├── aggregate_scores.py       # multi-judge median + disagreement flags + weighted verdict
│       └── generate_report.py        # report.json → answer-first HTML
└── docs/
    ├── index.html                    # landing page
    ├── sample-report.html            # example report
    └── METHODOLOGY.md / METHODOLOGY_zh.md
```

Zero runtime dependencies (Google Play reviews optional).

---

## License

Demand Radar is released under **CC BY-NC 4.0**:

- ✅ **Free** for personal, educational, research, and any non-commercial use
- ✅ **Forking, modifying, sharing** is welcome — please attribute the original repo and indicate changes
- ❌ **Commercial use** (bundling into paid products, paid SaaS hosting, selling reports based on the scoring) requires a separate license

**For commercial licensing**, contact: **leifdiao@gmail.com**

See [LICENSE](./LICENSE) for full terms, including the 中文版说明.

---

*Built for people who want to know if the demand is real — before they build it.*
