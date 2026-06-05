#!/usr/bin/env python3
"""Google Play 评论连接器 —— 用 google-play-scraper 库（官方数据封装，非自建爬虫）。

依赖: pip install google-play-scraper
用法:
  python3 play_reviews.py "<包名 如 com.notion.id>" [--limit N] [--lang en] [--country us]

输出 JSON 到 stdout。库没装时给出友好提示而不是报错。
"""
import sys, json, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--country", default="us")
    a = ap.parse_args()

    try:
        from google_play_scraper import reviews, Sort
    except ImportError:
        print(json.dumps({
            "source": "googleplay", "package": a.package,
            "error": "google-play-scraper 未安装",
            "hint": "pip install google-play-scraper（或本次跳过 Play，用其它源）"
        }, ensure_ascii=False))
        return

    try:
        result, _ = reviews(a.package, lang=a.lang, country=a.country,
                            sort=Sort.NEWEST, count=a.limit)
    except Exception as e:
        print(json.dumps({"source": "googleplay", "package": a.package, "error": str(e)}, ensure_ascii=False))
        return

    out = [{
        "rating": r.get("score"),
        "text": (r.get("content") or "")[:600],
        "thumbs_up": r.get("thumbsUpCount"),
        "version": r.get("reviewCreatedVersion"),
        "date": str(r.get("at")),
    } for r in result]
    print(json.dumps({"source": "googleplay", "package": a.package,
                      "count": len(out), "reviews": out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
