#!/usr/bin/env python3
"""证据三角验证 —— 按模型已标注的 signal 分组，数独立平台数，套 ≥2 源规则给置信度。

为什么用脚本：「一个信号被几个独立源支持」是死规则，交给代码强制执行，
防止模型嘴软把单源线索说成已验证。模型负责给每条证据打 signal 标签（语义判断），
脚本负责数数和定级（确定性）。

用法:
  python3 triangulate.py evidence.json [--out tri.json]

evidence.json:
  {"evidence":[
     {"id":"E1","signal":"Notion 太复杂","platform":"HN","source_type":"行为","url":"..."},
     ...
  ]}

定级（与 validation-framework.md C 节一致）:
  1 源 = 线索(待验证)  |  2 源 = 中(成立)  |  >=3 源且含硬证据 = 高(强成立)
"""
import sys, json, argparse


def grade(platforms, has_hard):
    n = len(platforms)
    if n >= 3 and has_hard:
        return "高"
    if n >= 2:
        return "中"
    return "线索"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    with open(a.evidence, encoding="utf-8") as f:
        data = json.load(f)
    ev = data.get("evidence", data if isinstance(data, list) else [])

    groups = {}
    for e in ev:
        sig = (e.get("signal") or "未分组").strip()
        g = groups.setdefault(sig, {"platforms": set(), "ids": [], "has_hard": False})
        if e.get("platform"):
            g["platforms"].add(e["platform"])
        g["ids"].append(e.get("id"))
        if e.get("source_type") == "硬":
            g["has_hard"] = True

    rows = []
    for sig, g in groups.items():
        plats = sorted(g["platforms"])
        rows.append({
            "signal": sig,
            "n_sources": len(plats),
            "platforms": plats,
            "has_hard_evidence": g["has_hard"],
            "evidence_ids": g["ids"],
            "confidence": grade(plats, g["has_hard"]),
        })
    rows.sort(key=lambda r: (-r["n_sources"], r["confidence"]))

    out = {
        "total_signals": len(rows),
        "verified": [r for r in rows if r["confidence"] != "线索"],
        "leads_only": [r for r in rows if r["confidence"] == "线索"],
        "signals": rows,
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    print(txt)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
    print(f"\n已验证信号 {len(out['verified'])} 个，单源线索 {len(out['leads_only'])} 个",
          file=sys.stderr)


if __name__ == "__main__":
    main()
