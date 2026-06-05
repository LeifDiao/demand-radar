#!/usr/bin/env python3
"""Reddit 连接器 —— 优先用 PRAW 官方 OAuth（稳，免费授权，非爬虫）；
没配凭证时回退到公开 .json 端点（会限流，仅兜底）。

PRAW 凭证（环境变量，去 reddit.com/prefs/apps 免费申请）:
  REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT

用法:
  python3 reddit.py "<query>" [--limit N] [--subreddit all] [--sort relevance]

输出 JSON 到 stdout。
"""
import os, sys, json, argparse
import urllib.parse, urllib.request, urllib.error

UA = os.environ.get("REDDIT_USER_AGENT", "demand-radar/0.1 (by u/anon)")


def via_praw(query, limit, subreddit, sort):
    import praw
    r = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=UA,
    )
    out = []
    for p in r.subreddit(subreddit).search(query, sort=sort, limit=limit):
        out.append({
            "subreddit": str(p.subreddit), "title": p.title,
            "text": (p.selftext or "")[:600], "ups": p.score,
            "num_comments": p.num_comments,
            "url": f"https://reddit.com{p.permalink}", "created": p.created_utc,
        })
    return {"source": "reddit", "mode": "praw", "query": query, "count": len(out), "items": out}


def via_json(query, limit, subreddit, sort):
    base = f"https://www.reddit.com/r/{subreddit}/search.json" if subreddit != "all" else "https://www.reddit.com/search.json"
    url = base + "?" + urllib.parse.urlencode(
        {"q": query, "limit": limit, "sort": sort, "restrict_sr": "1" if subreddit != "all" else "0"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.load(resp)
    out = []
    for c in d.get("data", {}).get("children", []):
        p = c["data"]
        out.append({
            "subreddit": p.get("subreddit"), "title": p.get("title"),
            "text": (p.get("selftext") or "")[:600], "ups": p.get("ups"),
            "num_comments": p.get("num_comments"),
            "url": "https://reddit.com" + p.get("permalink", ""), "created": p.get("created_utc"),
        })
    return {"source": "reddit", "mode": "json", "query": query, "count": len(out), "items": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--subreddit", default="all")
    ap.add_argument("--sort", default="relevance", help="relevance/hot/top/new/comments")
    a = ap.parse_args()

    has_creds = os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET")
    try:
        if has_creds:
            try:
                res = via_praw(a.query, a.limit, a.subreddit, a.sort)
            except ImportError:
                res = via_json(a.query, a.limit, a.subreddit, a.sort)
                res["note"] = "有凭证但 praw 未安装，回退 .json（pip install praw 可启用稳定模式）"
        else:
            res = via_json(a.query, a.limit, a.subreddit, a.sort)
            res["note"] = "未配 PRAW 凭证，用公开 .json（可能限流）。配 REDDIT_CLIENT_ID/SECRET 更稳。"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        res = {"source": "reddit", "query": a.query, "error": str(e),
               "hint": "Reddit 限流，稍后重试或配 PRAW 凭证"}
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
