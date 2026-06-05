#!/usr/bin/env python3
"""Demand Radar 报告生成器 —— 结构化 report.json -> dashboard 式自包含 HTML。

布局：左侧栏（品牌 + 区块导航 + 裁决卡）+ 主区分区块。
视觉：信号网格 / 蓝图风（与 Demand Radar 落地页同家族）——纸白网格底 + 墨黑 +
信号绿点缀，Space Grotesk 标题 + IBM Plex Mono 数据标签，锐角 + 靶角锁定母题。
7 个评分维度归成 3 类（需求真实性 / 商业潜力 / 竞争格局）渲染成 3 张分类 scorecard。
报告语言跟随 report.json 的 "lang" 字段（zh / en，单语言）。

用法:
  python3 generate_report.py --report report.json --output report.html [--open]
"""
import sys, json, argparse, re, html, datetime, webbrowser, os

VCOLOR = {
    "Go": "#1E8C5A", "可以做": "#1E8C5A",
    "有条件做": "#B07C32", "Conditional": "#B07C32", "Conditional Go": "#B07C32",
    "转向": "#C0673A", "Pivot": "#C0673A",
    "别做": "#B0463B", "No-go": "#B0463B", "No-Go": "#B0463B", "Don't build": "#B0463B",
}
SRC_COLOR = {"硬": "#0E8C63", "行为": "#5C7184", "意见": "#888E96", "分析师": "#B07C32",
             "hard": "#0E8C63", "behavioral": "#5C7184", "opinion": "#888E96", "analyst": "#B07C32"}
PRIO = {"高": "high", "中": "medium", "低": "low",
        "high": "high", "medium": "medium", "low": "low",
        "High": "high", "Medium": "medium", "Low": "low"}
CAT_COLOR = ["#0E8C63", "#B07C32", "#5C7184"]  # 需求 / 商业 / 格局

STR = {
    "zh": {"product": "需求验证", "nav_overview": "概览", "nav_detail": "深入",
           "verdict": "结论", "actions": "该怎么做", "scores": "评分卡", "details": "详情", "data": "分析流程 & 数据",
           "you_asked": "你问的需求", "confidence": "置信度", "weighted": "加权得分",
           "cats": ["需求真实性", "商业潜力", "竞争格局"],
           "contra": "上下证据对账", "redteam": "红队最致命弱点", "altmap": "现有替代方案地图",
           "alt_cur": "用户现在怎么凑合", "alt_gap": "缺口 / 机会点", "notverified": "我们没能验证的部分",
           "flow": "流程", "sources": "数据源", "evidence": "证据附录",
           "st_agents": "采集/评审 agent", "st_ev": "证据条数", "st_sig": "已验证信号", "st_round": "搜索轮次",
           "default_flow": "框定 → 选源 → 多 agent 并行采集 → 三角验证(≥2源) → 3 评委独立打分 → 红队证伪 → 闭环重评 → 报告",
           "hint_scores": "7 维 · 付费意愿 ×2 · 红队闭环后终评", "hint_actions": "可执行的下一步",
           "hint_verdict": "你的需求成不成立 · 为什么", "hint_details": "证据支撑的关键发现 · 矛盾 · 红队 · 替代方案",
           "hint_data": "怎么得出的 · 全量证据可溯源",
           "foot": "每条结论可在「分析流程 & 数据」里溯源"},
    "en": {"product": "Demand validation", "nav_overview": "Overview", "nav_detail": "Deep dive",
           "verdict": "Verdict", "actions": "What to do", "scores": "Scorecard", "details": "Details", "data": "Method & data",
           "you_asked": "Your demand", "confidence": "Confidence", "weighted": "Weighted",
           "cats": ["Demand reality", "Business potential", "Landscape"],
           "contra": "Two-pillar reconciliation", "redteam": "Red-team's most lethal flaw", "altmap": "Current alternatives map",
           "alt_cur": "How users cope today", "alt_gap": "Gap / opportunity", "notverified": "What we could NOT verify",
           "flow": "Flow", "sources": "Sources", "evidence": "Evidence appendix",
           "st_agents": "collector/judge agents", "st_ev": "evidence items", "st_sig": "verified signals", "st_round": "search rounds",
           "default_flow": "Frame → source → parallel collectors → triangulate(≥2) → 3 judges → red-team → closed-loop re-score → report",
           "hint_scores": "7 axes · willingness-to-pay ×2 · post red-team", "hint_actions": "Concrete next steps",
           "hint_verdict": "Does your demand hold up · and why", "hint_details": "Evidence-backed findings · contradictions · red-team · alternatives",
           "hint_data": "How we got here · every claim traceable",
           "foot": "Every claim is traceable in “Method & data”."},
}


def esc(s):
    return html.escape(str(s) if s is not None else "")


def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def bar_color(ratio):
    if ratio >= 0.7:
        return "#0E8C63"
    if ratio >= 0.5:
        return "#3E8C6B"
    if ratio >= 0.35:
        return "#B07C32"
    return "#B0463B"


def grade_of(pct):
    if pct >= 80:
        return "A", "#0E8C63"
    if pct >= 65:
        return "B", "#3E8C6B"
    if pct >= 50:
        return "C", "#B07C32"
    if pct >= 35:
        return "D", "#C0673A"
    return "E", "#B0463B"


def bullet_icon(text):
    t = text.strip()
    if t[:3] == "[+]":
        return _ic('<path d="M20 6 9 17l-5-5"/>'), "#0E8C63", t[3:].strip()
    if t[:3] == "[-]":
        return _ic('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'), "#B0463B", t[3:].strip()
    if t[:3] == "[~]":
        return _ic('<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>'), "#C0673A", t[3:].strip()
    return _ic('<circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/>'), "#888E96", t


BRAND_SVG = ('<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
             '<circle cx="16" cy="16" r="13" stroke="currentColor" stroke-width="1.4" opacity="0.3"/>'
             '<circle cx="16" cy="16" r="8" stroke="currentColor" stroke-width="1.4" opacity="0.5"/>'
             '<circle cx="16" cy="16" r="2.6" fill="currentColor"/>'
             '<path d="M16 16 L27 9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
             '<path d="M16 3 L16 7 M16 25 L16 29 M3 16 L7 16 M25 16 L29 16" stroke="currentColor" stroke-width="1.2" opacity="0.55"/></svg>')


def _ic(paths):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round">' + paths + '</svg>')


# 内联 SVG 图标（Lucide，描边式，任何浏览器一致渲染——不用系统 emoji）
ICON = {
    "contra": _ic('<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>'
                  '<path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>'
                  '<path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>'),
    "redteam": _ic('<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/>'
                   '<line x1="13" x2="19" y1="19" y2="13"/><line x1="16" x2="20" y1="16" y2="20"/>'
                   '<line x1="19" x2="21" y1="21" y2="19"/><polyline points="14.5 6.5 18 3 21 3 21 6 17.5 9.5"/>'
                   '<line x1="5" x2="9" y1="14" y2="18"/><line x1="7" x2="4" y1="17" y2="20"/><line x1="3" x2="5" y1="19" y2="21"/>'),
    "altmap": _ic('<path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894'
                  'l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618'
                  'a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z"/><path d="M15 5.764v15"/><path d="M9 3.236v15"/>'),
    "notverified": _ic('<path d="m13.5 8.5-5 5"/><path d="m8.5 8.5 5 5"/><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'),
}


def render(d):
    L = STR["en" if str(d.get("lang", "zh")).lower().startswith("en") else "zh"]
    vc = VCOLOR.get(d.get("verdict", ""), "#847F72")
    pct = d.get("weighted_pct")
    sc_items = d.get("scorecard", [])

    # ── sidebar ──
    nav_links = [("verdict", L["verdict"]), ("actions", L["actions"]),
                 ("scores", L["scores"]), ("details", L["details"]), ("data", L["data"])]
    nav = "".join(f'<a class="nav-item" href="#{i}"><span class="nav-dot"></span>{esc(t)}</a>' for i, t in nav_links)
    side_pct = f'<div class="side-pct" style="color:{vc}">{pct}%</div>' if pct is not None else ""
    sidebar = (f'<aside class="sidebar"><div class="brand"><span class="brand-mark">{BRAND_SVG}</span>'
               f'<div><div class="brand-name">Demand <span class="brand-accent">Radar</span></div>'
               f'<div class="brand-version">{esc(L["product"])}</div></div></div>'
               f'<nav class="nav">{nav}</nav>'
               f'<div class="side-card"><div class="side-label">{esc(L["you_asked"])}</div>'
               f'<div class="side-q">{esc(d.get("question",""))}</div>'
               f'<div class="side-verdict" style="background:{vc}">{esc(d.get("verdict","—"))}</div>{side_pct}</div></aside>')

    def section(sid, title, hint, body):
        h = f'<span class="section-hint">{esc(hint)}</span>' if hint else ""
        return f'<section class="section" id="{sid}"><div class="section-header"><div class="section-title">{esc(title)}</div>{h}</div>{body}</section>'

    # ── 结论 hero ──
    tldr = ""
    for p in d.get("tldr_points", []):
        ic, col, txt = bullet_icon(p)
        tldr += f'<li><span class="ic" style="color:{col}">{ic}</span><span>{inline(txt)}</span></li>'
    pills = ""
    if d.get("confidence"):
        pills += f'<span class="pill">{L["confidence"]} {esc(d.get("confidence"))}</span>'
    one_liner = f'<div class="one-liner">{inline(d.get("one_liner",""))}</div>' if d.get("one_liner") else ""
    big = (f'<div class="hero-grade lock"><div class="grade-num" style="color:{vc}">{pct}<span class="grade-pct">%</span></div>'
           f'<div class="grade-label" style="color:{vc}">{esc(d.get("verdict","—"))}</div>'
           f'<div class="grade-sub">{esc(L["weighted"])}</div></div>') if pct is not None else \
          (f'<div class="hero-grade lock"><div class="grade-label" style="color:{vc}">{esc(d.get("verdict","—"))}</div></div>')
    tldr_ul = f'<ul class="tldr">{tldr}</ul>' if tldr else ""
    mm = d.get("method", {})
    meta_bits = ""
    for k, lab in [("agents", L["st_agents"]), ("evidence_count", L["st_ev"]),
                   ("signals_verified", L["st_sig"]), ("rounds", L["st_round"])]:
        if mm.get(k) is not None:
            meta_bits += f'<span><b>{esc(mm[k])}</b> {esc(lab)}</span>'
    hero_meta = f'<div class="hero-meta">{meta_bits}</div>' if meta_bits else ""
    hero_body = (f'<div class="hero"><div class="hero-left">'
                 f'<div class="verdict-sub">{inline(d.get("verdict_sub",""))}</div>'
                 f'{one_liner}<div class="answer">{inline(d.get("answer",""))}</div>'
                 f'<div class="pills">{pills}</div>'
                 f'{tldr_ul}{hero_meta}</div>'
                 f'<div class="hero-right">{big}</div></div>')
    verdict_sec = section("verdict", L["verdict"], L["hint_verdict"], hero_body)

    # ── 该怎么做 ──
    sug = ""
    for a in d.get("actions", []):
        pr = PRIO.get(a.get("priority", ""), "")
        pill = f'<span class="priority-pill priority-{pr}">{esc(a.get("priority",""))}</span>' if pr else ""
        sug += (f'<div class="suggestion"><div class="suggestion-head">{pill}'
                f'<span class="suggestion-title">{inline(a.get("title",""))}</span></div>'
                f'<div class="suggestion-body">{inline(a.get("detail",""))}</div></div>')
    actions_sec = section("actions", L["actions"], L["hint_actions"], f'<div class="suggestions">{sug}</div>') if sug else ""

    # ── 评分（7 维归 3 类）──
    cards = ""
    if sc_items:
        groups = [(L["cats"][0], sc_items[0:3]), (L["cats"][1], sc_items[3:5]), (L["cats"][2], sc_items[5:7])]
        for ci, (cname, items) in enumerate(groups):
            items = [x for x in items if x]
            if not items:
                continue
            ratio = sum((x.get("score", 0) / (x.get("max") or 5)) for x in items) / len(items)
            cpct = round(ratio * 100)
            g, gcol = grade_of(cpct)
            dims = ""
            for x in items:
                mx = x.get("max", 5); s = x.get("score", 0); r = s / mx if mx else 0
                dims += (f'<div class="sc-dim"><div class="sc-dim-row"><span class="sc-dim-name">{esc(x.get("dim",""))}</span>'
                         f'<span class="sc-dim-score">{s}/{mx}</span></div>'
                         f'<div class="sc-dim-bar"><div class="sc-dim-fill" style="width:{round(r*100)}%;background:{bar_color(r)}"></div></div></div>')
            cards += (f'<div class="scorecard" style="--cat:{CAT_COLOR[ci]}">'
                      f'<div class="sc-head"><span class="sc-name">{esc(cname)}</span>'
                      f'<span class="sc-grade" style="background:{gcol}">{g}</span></div>'
                      f'<div class="sc-num" style="color:{gcol}">{cpct}</div>'
                      f'<div class="sc-dims">{dims}</div></div>')
    head_pct = f'{pct}%' if pct is not None else ""
    scores_sec = section("scores", f'{L["scores"]}', f'{L["hint_scores"]}{("  ·  "+head_pct) if head_pct else ""}',
                         f'<div class="scorecards">{cards}</div>') if cards else ""

    # ── 详情 ──
    detail = ""
    for f in d.get("findings", []):
        chips = "".join(f'<span class="chip">{esc(e)}</span>' for e in f.get("evidence_ids", []))
        detail += (f'<div class="card"><div class="card-label"><span class="label-dot"></span>{inline(f.get("title",""))}</div>'
                   f'<div class="card-body">{inline(f.get("body",""))}</div><div class="chips">{chips}</div></div>')
    if d.get("contradictions"):
        detail += f'<div class="card cross"><div class="card-label">{ICON["contra"]}{esc(L["contra"])}</div><div class="card-body">{inline(d["contradictions"])}</div></div>'
    if d.get("red_team"):
        detail += f'<div class="card danger"><div class="card-label">{ICON["redteam"]}{esc(L["redteam"])}</div><div class="card-body">{inline(d["red_team"])}</div></div>'
    alt = "".join(f'<tr><td>{inline(a.get("current",""))}</td><td>{inline(a.get("gap",""))}</td></tr>' for a in d.get("alternatives", []))
    if alt:
        detail += (f'<div class="card wide"><div class="card-label">{ICON["altmap"]}{esc(L["altmap"])}</div>'
                   f'<table class="alt"><thead><tr><th>{esc(L["alt_cur"])}</th><th>{esc(L["alt_gap"])}</th></tr></thead><tbody>{alt}</tbody></table></div>')
    details_sec = section("details", L["details"], L["hint_details"], f'<div class="card-grid">{detail}</div>') if detail else ""

    # ── 分析流程 & 数据 ──
    m = d.get("method", {})
    stats = ""
    for k, lab in [("agents", L["st_agents"]), ("evidence_count", L["st_ev"]),
                   ("signals_verified", L["st_sig"]), ("rounds", L["st_round"])]:
        if m.get(k) is not None:
            stats += f'<div class="stat"><div class="stat-n">{esc(m[k])}</div><div class="stat-l">{esc(lab)}</div></div>'
    srcs = "".join(f'<span class="chip">{esc(x)}</span>' for x in m.get("sources", []))
    srcs_div = f'<div class="kv"><strong>{esc(L["sources"])}：</strong>{srcs}</div>' if srcs else ""
    flow = m.get("flow") or L["default_flow"]
    ev_rows = ""
    for e in d.get("evidence", []):
        col = SRC_COLOR.get(e.get("source_type", ""), "#A6A192")
        tag = f'<span class="tag" style="background:{col}">{esc(e.get("source_type",""))}</span>'
        link = f'<a href="{esc(e.get("url",""))}" target="_blank">↗</a>' if e.get("url") else ""
        ev_rows += (f'<tr><td class="eid">{esc(e.get("id",""))}</td><td>{esc(e.get("platform",""))}{tag}</td>'
                    f'<td>{esc(e.get("claim",""))}<div class="q">“{esc((e.get("quote") or "")[:240])}”</div></td>'
                    f'<td class="ed">{esc(e.get("date",""))} {link}</td></tr>')
    ev_block = (f'<h3 class="ev-h">{esc(L["evidence"])} · {len(d.get("evidence",[]))}</h3>'
                f'<div class="ev-wrap"><table class="evidence"><tbody>{ev_rows}</tbody></table></div>') if ev_rows else ""
    data_body = (f'<div class="card lock"><div class="stats">{stats}</div>'
                 f'<div class="kv"><strong>{esc(L["flow"])}：</strong>{esc(flow)}</div>{srcs_div}{ev_block}</div>')
    data_sec = section("data", L["data"], L["hint_data"], data_body)

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    topbar = (f'<div class="topbar"><div class="crumb"><strong>Demand Radar</strong> / {esc(L["product"])}</div>'
              f'<div class="crumb-meta">{ts}</div></div>')
    nv = "".join(f"<li>{inline(x)}</li>" for x in d.get("not_verified", []))
    nv_block = (f'<div class="nv-final"><div class="nv-head">{ICON["notverified"]}{esc(L["notverified"])}</div>'
                f'<ul class="nv">{nv}</ul></div>') if nv else ""
    foot = f'<div class="foot">Demand Radar · {ts} · {esc(L["foot"])}</div>'
    main = f'<main class="main">{topbar}{verdict_sec}{actions_sec}{scores_sec}{details_sec}{data_sec}{nv_block}{foot}</main>'
    return CSS + f'<div class="app">{sidebar}{main}</div>{SPY_JS}</body></html>'


SPY_JS = """<script>
(function(){var items=[].slice.call(document.querySelectorAll('.nav-item'));
var map={};items.forEach(function(a){map[a.getAttribute('href').slice(1)]=a;});
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){
items.forEach(function(a){a.classList.remove('active');});if(map[e.target.id])map[e.target.id].classList.add('active');}});},
{rootMargin:'-20% 0px -70% 0px'});
document.querySelectorAll('.section').forEach(function(s){io.observe(s);});})();
</script>"""

CSS = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Demand Radar · 需求验证报告</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
 --bg-page:#F8F9F6;--card:#FCFDFB;--card-2:#F3F5F0;--soft:#ECEFEA;--side:#F2F4EF;
 --ink:#14171C;--text-2:#3C4148;--text-3:#5C626B;--text-4:#888E96;--text-5:#AEB3B9;
 --line:rgba(20,23,28,0.075);--line-2:rgba(20,23,28,0.05);--line-major:rgba(20,23,28,0.09);--hair:rgba(20,23,28,0.12);
 --accent:#0E8C63;--accent-deep:#0A7351;--accent-soft:rgba(14,140,99,0.10);--accent-line:rgba(14,140,99,0.28);
 --signal:#0E8C63;--signal-soft:rgba(14,140,99,0.08);--signal-line:rgba(14,140,99,0.30);
 --go:#1E8C5A;--amber:#B07C32;--terra:#C0673A;--nogo:#B0463B;--slate:#5C7184;
 --shadow:0 1px 0 rgba(20,23,28,0.03),0 12px 30px rgba(20,23,28,0.06);
 --shadow-h:0 2px 4px rgba(20,23,28,0.05),0 20px 44px rgba(20,23,28,0.10);
 --mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;
 --disp:'Space Grotesk',-apple-system,'PingFang SC','Hiragino Sans GB',system-ui,sans-serif;
 --serif:'Space Grotesk',-apple-system,'PingFang SC','Hiragino Sans GB',system-ui,sans-serif;
 --sans:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI','PingFang SC','Hiragino Sans GB',system-ui,sans-serif;
}
*{box-sizing:border-box}html{scroll-behavior:smooth}html,body{margin:0;padding:0}
body{font-family:var(--sans);background-color:var(--bg-page);color:var(--ink);line-height:1.62;-webkit-font-smoothing:antialiased;
 background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px),linear-gradient(var(--line-major) 1px,transparent 1px),linear-gradient(90deg,var(--line-major) 1px,transparent 1px);
 background-size:32px 32px,32px 32px,160px 160px,160px 160px;background-position:-1px -1px;background-attachment:fixed}
a{color:var(--accent-deep);text-decoration:none}
code{background:var(--soft);padding:1px 6px;border-radius:3px;font-size:.88em;font-family:var(--mono)}
.app{display:grid;grid-template-columns:236px 1fr;min-height:100vh}
/* sidebar */
.sidebar{background:var(--side);border-right:1px solid var(--line-2);padding:24px 16px;position:sticky;top:0;height:100vh;overflow-y:auto;display:flex;flex-direction:column;gap:24px}
.brand{display:flex;align-items:center;gap:11px;padding:2px 6px}
.brand-mark{width:32px;height:32px;color:var(--accent);flex:none;display:flex}
.brand-name{font-family:var(--serif);font-size:17px;font-weight:600;letter-spacing:-.3px}
.brand-accent{color:var(--accent-deep)}
.brand-version{font-size:10px;color:var(--text-4);letter-spacing:.5px;margin-top:1px}
.nav{display:flex;flex-direction:column;gap:2px}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:9px;font-size:13px;font-weight:500;color:var(--text-3);cursor:pointer;transition:all .15s}
.nav-item:hover{background:var(--soft);color:var(--ink)}
.nav-item.active{background:var(--accent-soft);color:var(--accent-deep);font-weight:600}
.nav-dot{width:6px;height:6px;border-radius:50%;background:currentColor;opacity:.45;flex:none}
.nav-item.active .nav-dot{opacity:1}
.side-card{margin-top:auto;background:var(--card-2);border:1px solid var(--line-2);border-radius:12px;padding:15px}
.side-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text-5);margin-bottom:6px}
.side-q{font-family:var(--serif);font-size:15px;font-weight:600;color:var(--ink);line-height:1.3;margin-bottom:12px}
.side-verdict{display:inline-block;color:#fff;font-size:13px;font-weight:700;padding:4px 13px;border-radius:8px;font-family:var(--serif)}
.side-pct{font-family:var(--serif);font-size:30px;font-weight:600;margin-top:8px;line-height:1}
/* main */
.main{padding:32px 52px 80px;min-width:0;width:100%}
.topbar{display:flex;justify-content:space-between;align-items:center;padding-bottom:18px;margin-bottom:30px;border-bottom:1px solid var(--line-2)}
.crumb{font-size:12.5px;color:var(--text-4)}.crumb strong{color:var(--text-2);font-weight:600}
.crumb-meta{font-size:11px;color:var(--text-5)}
.section{margin-bottom:46px;scroll-margin-top:24px}
.section-header{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:16px}
.section-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.4px;color:var(--text-3);display:flex;align-items:center;gap:10px}
.section-title::before{content:"";width:18px;height:1px;background:linear-gradient(90deg,var(--accent),transparent)}
.section-hint{font-size:11px;color:var(--text-5);letter-spacing:.3px}
/* hero */
.hero{background:radial-gradient(ellipse at 12% 16%,rgba(217,119,87,.10) 0%,transparent 55%),linear-gradient(168deg,var(--card) 0%,var(--card-2) 100%);
 border:1px solid var(--line-2);border-radius:18px;padding:30px 34px;display:grid;grid-template-columns:1fr auto;gap:34px;align-items:center;box-shadow:var(--shadow)}
.verdict-sub{font-family:var(--serif);font-size:21px;font-weight:500;line-height:1.4;color:var(--ink);margin-bottom:12px;letter-spacing:-.2px;max-width:60ch}
.one-liner{color:var(--text-3);font-size:13.5px;margin-bottom:12px;max-width:72ch}
.answer{font-size:15.5px;line-height:1.82;color:var(--text-2);margin-bottom:14px;max-width:72ch}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:2px}
.pill{background:var(--accent-soft);border:1px solid var(--accent-line);color:var(--accent-deep);font-size:11.5px;padding:3px 12px;border-radius:20px;font-weight:600}
.tldr{list-style:none;padding:16px 0 0;margin:14px 0 0;border-top:1px solid var(--line)}
.tldr li{display:flex;gap:11px;margin:9px 0;font-size:14px;color:var(--text-2)}
.tldr .ic{font-weight:800;flex:none;width:14px}
.hero-right{text-align:center}
.hero-grade .grade-num{font-family:var(--serif);font-size:72px;font-weight:600;line-height:1;letter-spacing:-2px;filter:drop-shadow(0 0 24px currentColor)}
.grade-num .grade-pct{font-size:30px}
.hero-grade .grade-label{font-family:var(--serif);font-size:20px;font-weight:600;margin-top:6px}
.grade-sub{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--text-4);margin-top:6px}
/* scorecards */
.scorecards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.scorecard{background:var(--card);border:1px solid var(--line-2);border-radius:14px;padding:20px 20px 18px;position:relative;overflow:hidden;box-shadow:var(--shadow);transition:all .2s}
.scorecard:hover{transform:translateY(-2px);box-shadow:var(--shadow-h)}
.scorecard::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:var(--cat)}
.sc-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.sc-name{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--text-3)}
.sc-grade{color:#fff;font-size:11px;font-weight:800;padding:2px 8px;border-radius:5px}
.sc-num{font-family:var(--serif);font-size:34px;font-weight:600;line-height:1;margin-bottom:14px}
.sc-dims{display:flex;flex-direction:column;gap:9px}
.sc-dim-row{display:flex;justify-content:space-between;font-size:12px}
.sc-dim-name{color:var(--text-2);font-weight:500}.sc-dim-score{color:var(--text-4);font-weight:700}
.sc-dim-bar{height:3px;background:var(--soft);border-radius:999px;overflow:hidden;margin-top:4px}
.sc-dim-fill{height:100%;border-radius:999px}
/* cards */
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:13px}
.card-grid .card.cross,.card-grid .card.danger,.card-grid .card.caution,.card-grid .card.wide{grid-column:1/-1}
.card{background:var(--card);border:1px solid var(--line-2);border-radius:14px;padding:20px 22px;box-shadow:var(--shadow)}
.card.cross{background:var(--card-2);border-left:3px solid var(--accent)}
.card.danger{background:rgba(176,70,59,.06);border-color:rgba(176,70,59,.20)}
.card.caution{background:var(--soft);border:1px dashed var(--line)}
.card-label{font-size:13px;font-weight:700;color:var(--ink);margin-bottom:8px;display:flex;align-items:center;gap:7px}
.label-dot{width:6px;height:6px;border-radius:50%;background:var(--accent);flex:none}
.card-body{font-size:14px;line-height:1.7;color:var(--text-2)}
.chips{margin-top:9px}
.chip{display:inline-block;background:var(--accent-soft);color:var(--accent-deep);font-size:11px;padding:2px 9px;border-radius:12px;margin:2px 4px 2px 0;font-weight:600}
.nv{margin:6px 0 0;padding-left:20px;font-size:13.5px;color:var(--text-3)}.nv li{margin:5px 0}
/* suggestions */
.suggestions{display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:13px}
.suggestion{background:var(--card);border:1px solid var(--line-2);border-radius:14px;padding:19px 22px;box-shadow:var(--shadow);transition:all .18s}
.suggestion:hover{box-shadow:var(--shadow-h)}
.suggestion-head{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.priority-pill{font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;text-transform:uppercase;letter-spacing:.5px}
.priority-high{background:rgba(190,90,55,.16);color:#BE5A37}
.priority-medium{background:rgba(176,124,50,.16);color:#9A6A1E}
.priority-low{background:rgba(92,113,132,.16);color:#5C7184}
.suggestion-title{font-size:15px;font-weight:700;color:var(--ink);flex:1;min-width:0}
.suggestion-body{font-size:13.5px;color:var(--text-2);line-height:1.66}
/* tables */
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}
th,td{border-bottom:1px solid var(--line-2);padding:8px 10px;text-align:left;vertical-align:top}
th{color:var(--text-4);font-weight:600;font-size:12px}
.alt td{font-size:13.5px}
/* data section */
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.stat{background:var(--card-2);border:1px solid var(--line-2);border-radius:11px;padding:13px 18px;text-align:center;flex:1;min-width:88px}
.stat-n{font-family:var(--serif);font-size:24px;font-weight:600;color:var(--ink)}
.stat-l{font-size:11px;color:var(--text-4)}
.kv{font-size:13px;color:var(--text-3);margin:8px 0}
.ev-h{font-size:12px;color:var(--text-4);font-weight:700;letter-spacing:.5px;margin:20px 0 6px;text-transform:uppercase}
.evidence .eid{font-weight:700;color:var(--text-4)}
.evidence .q{color:var(--text-4);font-size:12px;margin-top:3px}
.evidence .ed{white-space:nowrap;color:var(--text-4)}
.tag{color:#fff;font-size:10px;padding:1px 6px;border-radius:8px;margin-left:5px}
.foot{color:var(--text-5);font-size:12px;margin-top:34px;padding-top:18px;border-top:1px solid var(--line-2)}
/* responsive */
@media (max-width:780px){
 .app{grid-template-columns:1fr}
 .sidebar{position:static;height:auto;flex-direction:row;flex-wrap:wrap;align-items:center;gap:14px;border-right:none;border-bottom:1px solid var(--line-2)}
 .nav{flex-direction:row;flex-wrap:wrap}.side-card{margin-top:0;flex:1;min-width:200px}
 .main{padding:24px 20px 60px}
 .hero{grid-template-columns:1fr}.hero-right{text-align:left}
 .scorecards,.card-grid,.suggestions{grid-template-columns:1fr}
}
/* ── blueprint / signal-grid theme ── */
svg{flex:none}
.brand-version,.side-label,.nav-item,.section-hint,.crumb,.crumb-meta,.grade-sub,.sc-name,.sc-grade,.stat-l,.ev-h,.foot,.chip,.pill,.priority-pill,.tag,.evidence .eid,.evidence .ed,.kv,.crumb strong,th{font-family:var(--mono)}
.brand-name,.side-q,.verdict-sub,.grade-num,.sc-num,.stat-n,.card-label,.suggestion-title{font-family:var(--disp);letter-spacing:-.2px}
.hero,.scorecard,.card,.suggestion,.stat,.side-card,.ev-wrap{border-radius:3px}
.pill,.chip,.sc-grade,.priority-pill,.side-verdict,.tag{border-radius:2px}
.nav-item{border-radius:0;font-size:12px;letter-spacing:.3px}
.main{counter-reset:sec}
.section{counter-increment:sec}
.section-header{align-items:baseline;border-bottom:1px solid var(--line-2);padding-bottom:11px;margin-bottom:20px}
.section-title{font-family:var(--disp);font-size:20px;font-weight:600;color:var(--ink);letter-spacing:-.3px;text-transform:none;display:flex;align-items:baseline;gap:11px}
.section-title::before{content:counter(sec,decimal-leading-zero);font-family:var(--mono);font-size:12.5px;font-weight:600;color:var(--signal);background:none;width:auto;height:auto;flex:none}
.section-hint{font-family:var(--mono);font-size:11px;color:var(--text-4)}
.tldr .ic{display:inline-flex;align-items:center;flex:none;width:15px;margin-top:3px}
.tldr .ic svg{width:15px;height:15px;display:block}
/* details: calmer + readable measure */
.card-body{max-width:78ch}
.card-label{gap:8px}
.card-label svg{width:16px;height:16px;flex:none;color:var(--signal)}
.card.cross{background:var(--card);border-left:3px solid var(--slate)}
.card.cross .card-label svg{color:var(--slate)}
.card.danger{background:var(--card);border-color:var(--line-2);border-left:3px solid var(--nogo)}
.card.danger .card-label svg{color:var(--nogo)}
/* full-width callout cards (对账/红队): body must FILL the card, not cap at 78ch and leave a void on wide screens */
.card.cross .card-body,.card.danger .card-body{max-width:none;columns:2 26rem;column-gap:38px}
/* quiet 'not verified' footnote, after the data section */
.nv-final{margin-top:30px;padding:15px 18px;border:1px dashed var(--line);border-radius:3px}
.nv-final .nv-head{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:11px;letter-spacing:.6px;color:var(--text-4);text-transform:uppercase}
.nv-final .nv-head svg{width:14px;height:14px;flex:none;color:var(--text-5)}
.nv-final .nv{margin:9px 0 0;padding-left:18px;font-size:12.5px;color:var(--text-4)}
.nv-final .nv li{margin:4px 0}
.hero{background:radial-gradient(ellipse at 12% 16%,rgba(14,140,99,.07) 0%,transparent 55%),linear-gradient(168deg,var(--card) 0%,var(--card-2) 100%);border-color:var(--hair)}
.scorecard::before{height:2px}
.chip{background:var(--signal-soft);color:var(--accent-deep)}
.pill{background:var(--signal-soft);border-color:var(--accent-line);color:var(--accent-deep)}
.nav-item.active{background:var(--signal-soft);color:var(--accent-deep)}
.side-card{background:var(--card);border-color:var(--hair)}
/* hero quantified readout */
.hero-meta{display:flex;flex-wrap:wrap;gap:6px 16px;font-family:var(--mono);font-size:11px;color:var(--text-4);letter-spacing:.4px;margin:14px 0 0;padding-top:13px;border-top:1px solid var(--line-2)}
.hero-meta b{color:var(--signal);font-weight:600}
/* corner-bracket lock motif */
.lock{position:relative}
.lock::before,.lock::after{content:"";position:absolute;width:13px;height:13px;pointer-events:none;z-index:2}
.lock::before{top:-1px;left:-1px;border-top:1.6px solid var(--signal);border-left:1.6px solid var(--signal)}
.lock::after{bottom:-1px;right:-1px;border-bottom:1.6px solid var(--signal);border-right:1.6px solid var(--signal)}
</style></head><body>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    with open(a.report, encoding="utf-8") as f:
        d = json.load(f)
    with open(a.output, "w", encoding="utf-8") as f:
        f.write(render(d))
    print(f"报告已生成: {a.output}")
    if a.open:
        webbrowser.open("file://" + os.path.abspath(a.output))


if __name__ == "__main__":
    main()
