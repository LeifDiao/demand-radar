#!/usr/bin/env python3
"""多评委评分聚合 —— 输入 N 个评委的 7 项评分卡，输出聚合分 + 分歧标记 + 加权裁决 + 需求状态分类。

为什么用脚本：3 个 agent 各打一份分，聚合是确定性数学（中位数、极差、加权），
交给代码做可复现、不会算错，还能自动标出评委分歧大的维度（需人工复核）。

用法:
  python3 aggregate_scores.py judges.json [--out agg.json]

judges.json 结构（每个评委一份）:
  [{"judge":"j1","scores":[
      {"dim":"痛点强度","score":4,"confidence":"中","evidence_ids":["E1"]},
      ... 共 7 维
   ]}, ...]

权重: 付费意愿 ×2，痛点强度 ×1.5，其余 ×1（与 validation-framework.md E 节一致）。
裁决档: >=70% Go / 50-70% 有条件做 / 30-50% 转向 / <30% 别做。

第 6 维是「差异化楔子」（红海里你有没有别人没占的切口），不是「有没有竞争」——
竞争存在本身是需求被验证的证据，计入付费意愿/市场规模，不在这里扣分。
详见 validation-framework.md「竞争如何计分」。
"""
import sys, json, argparse, statistics

DIMS = ["痛点强度", "普遍性", "现有替代", "付费意愿", "市场规模", "差异化楔子", "可触达性"]
# 评委可能用的别名 -> canonical（含旧维度名「竞争空白」向后兼容）
ALIASES = {
    "竞争": "差异化楔子", "竞争空白": "差异化楔子", "差异化空间": "差异化楔子",
    "楔子": "差异化楔子", "切口": "差异化楔子",
    "替代缺口": "现有替代", "现有替代缺口": "现有替代", "现有替代方案": "现有替代",
    "付费": "付费意愿", "市场": "市场规模", "市场规模+趋势": "市场规模",
    "普遍": "普遍性", "频率": "普遍性", "可触达": "可触达性",
}
DEMAND_DIMS = ["痛点强度", "普遍性", "现有替代"]   # 需求真实度由这三维派生


def weight(dim):
    if "付费" in dim:
        return 2.0
    if "痛点" in dim:
        return 1.5
    return 1.0


def match_dim(name):
    name = (name or "").strip()
    if name in DIMS:                 # 精确匹配优先
        return name
    if name in ALIASES:              # 别名表
        return ALIASES[name]
    for d in DIMS:                   # canonical 是给定名的子串（如 现有替代缺口→现有替代）
        if d in name:
            return d
    for a, c in ALIASES.items():     # 别名是给定名的子串（如「差异化楔子(切口)」）
        if a in name:
            return c
    return name


def demand_state(med_by_dim):
    """从已聚合的中位数派生需求状态标签（确定性，供报告 demand_tags 参考）。
    竞争状态轴需竞品数量等证据，由模型在报告里补；这里只给能从分数算出的两轴。"""
    demand = [med_by_dim[d] for d in DEMAND_DIMS if d in med_by_dim]
    out = {}
    if demand:
        pct = round(100 * (sum(demand) / len(demand)) / 5)
        out["demand_reality_pct"] = pct
        out["demand_reality"] = ("伪需求" if pct < 30 else "弱需求" if pct < 50
                                 else "真实需求" if pct < 75 else "强刚需")
    if "差异化楔子" in med_by_dim:
        w = med_by_dim["差异化楔子"]
        out["wedge_score"] = w
        out["opportunity"] = ("无楔子" if w < 1 else "仅细分有缝" if w < 3 else "有楔子")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("judges")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    with open(a.judges, encoding="utf-8") as f:
        judges = json.load(f)
    if isinstance(judges, dict):
        judges = judges.get("judges", [judges])

    # 收集每个维度各评委的分
    by_dim = {}
    for j in judges:
        for s in j.get("scores", []):
            d = match_dim(s.get("dim", ""))
            by_dim.setdefault(d, []).append(float(s.get("score", 0)))

    rows, weighted_sum, weighted_max, med_by_dim = [], 0.0, 0.0, {}
    for d, scores in by_dim.items():
        med = statistics.median(scores)
        med_by_dim[d] = med
        spread = max(scores) - min(scores)
        w = weight(d)
        weighted_sum += med * w
        weighted_max += 5 * w
        rows.append({
            "dim": d, "median": round(med, 1), "spread": spread,
            "n_judges": len(scores), "weight": w,
            "disagreement": spread >= 2,  # 评委分歧大，报告里要标注
            "raw": scores,
        })

    pct = round(100 * weighted_sum / weighted_max, 1) if weighted_max else 0
    verdict = ("Go" if pct >= 70 else "有条件做" if pct >= 50 else "转向" if pct >= 30 else "别做")

    out = {
        "weighted_pct": pct,
        "verdict": verdict,
        "demand_state": demand_state(med_by_dim),
        "weighted_sum": round(weighted_sum, 1),
        "weighted_max": round(weighted_max, 1),
        "n_judges": len(judges),
        "dimensions": sorted(rows, key=lambda r: r["weight"], reverse=True),
        "flags": [r["dim"] for r in rows if r["disagreement"]],
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    print(txt)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
    if out["flags"]:
        print(f"\n⚠️ 评委分歧大的维度（需复核）: {', '.join(out['flags'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
