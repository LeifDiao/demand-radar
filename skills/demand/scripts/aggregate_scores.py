#!/usr/bin/env python3
"""多评委评分聚合 —— 输入 N 个评委的 7 项评分卡，输出聚合分 + 分歧标记 + 加权裁决。

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
"""
import sys, json, argparse, statistics

DIMS = ["痛点强度", "普遍性", "现有替代", "付费意愿", "市场规模", "竞争", "可触达性"]


def weight(dim):
    if "付费" in dim:
        return 2.0
    if "痛点" in dim:
        return 1.5
    return 1.0


def match_dim(name):
    name = (name or "").strip()
    for d in DIMS:           # 精确匹配优先
        if name == d:
            return d
    for d in DIMS:           # 再认「canonical 是给定名的子串」(如 现有替代缺口→现有替代)
        if d in name:        # 不做反向(name in d)，避免「竞」错配进「竞争」
            return d
    return name


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

    rows, weighted_sum, weighted_max = [], 0.0, 0.0
    for d, scores in by_dim.items():
        med = statistics.median(scores)
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
