#!/usr/bin/env python3
"""Hacker News 连接器 —— 通过 Algolia 官方 API 搜索（免费，无需 key，非爬虫）。

用法:
  python3 hn_algolia.py "<query>" [--tags comment|story] [--limit N] [--days N]

输出 JSON 到 stdout:
  {source, query, count, items:[{type,text,url,points,num_comments,author,created,hn_url}]}
"""
import sys, json, argparse, re, datetime
import urllib.parse, urllib.request, urllib.error

API = "https://hn.algolia.com/api/v1/search"

_ENT = {"&#x27;": "'", "&#39;": "'", "&quot;": '"', "&amp;": "&",
        "&#x2F;": "/", "&gt;": ">", "&lt;": "<", "&#62;": ">", "&#60;": "<"}


def clean(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in _ENT.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def fetch(query, tags, limit, days):
    params = {"query": query, "tags": tags, "hitsPerPage": str(min(limit, 100))}
    if days:
        cutoff = int((datetime.datetime.utcnow() - datetime.timedelta(days=days)).timestamp())
        params["numericFilters"] = f"created_at_i>{cutoff}"
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "demand-radar/0.1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--tags", default="(story,comment)", help="story / comment / (story,comment)")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--days", type=int, default=0, help="只取最近 N 天，0=不限")
    a = ap.parse_args()
    try:
        d = fetch(a.query, a.tags, a.limit, a.days)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(json.dumps({"source": "hackernews", "query": a.query, "error": str(e)}, ensure_ascii=False))
        return
    items = []
    for h in d.get("hits", []):
        text = clean(h.get("comment_text") or h.get("story_text") or h.get("title"))
        if not text:
            continue
        items.append({
            "type": "comment" if h.get("comment_text") else "story",
            "text": text[:500],
            "url": h.get("url") or h.get("story_url"),
            "points": h.get("points"),
            "num_comments": h.get("num_comments"),
            "author": h.get("author"),
            "created": h.get("created_at"),
            "hn_url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
        })
    print(json.dumps({"source": "hackernews", "query": a.query,
                      "count": len(items), "items": items}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
