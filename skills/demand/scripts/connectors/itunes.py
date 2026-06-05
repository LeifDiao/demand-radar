#!/usr/bin/env python3
"""App Store 连接器 —— iTunes 官方 Search API + 评论 RSS（免费，无需 key，非爬虫）。

用法:
  python3 itunes.py search "<app名或关键词>" [--limit N] [--country us]
      -> 找 app id、评分、评分数、价格（竞品供给侧硬指标）
  python3 itunes.py reviews <app_id> [--pages N] [--country us]
      -> 真实用户评论 + 星级（痛点 + 付费用户吐槽）

输出 JSON 到 stdout。
"""
import sys, json, argparse
import urllib.parse, urllib.request, urllib.error

SEARCH = "https://itunes.apple.com/search"
RSS = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "demand-radar/0.1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def do_search(term, limit, country):
    url = SEARCH + "?" + urllib.parse.urlencode(
        {"term": term, "entity": "software", "limit": min(limit, 50), "country": country})
    d = _get(url)
    apps = []
    for r in d.get("results", []):
        apps.append({
            "id": r.get("trackId"),
            "name": r.get("trackName"),
            "seller": r.get("sellerName"),
            "rating": r.get("averageUserRating"),
            "rating_count": r.get("userRatingCount"),
            "price": r.get("formattedPrice"),
            "genres": r.get("genres"),
            "url": r.get("trackViewUrl"),
        })
    return {"source": "appstore_search", "term": term, "count": len(apps), "apps": apps}


def do_reviews(app_id, pages, country):
    out = []
    for p in range(1, pages + 1):
        url = RSS.format(country=country, page=p, app_id=app_id)
        try:
            d = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            break
        entries = d.get("feed", {}).get("entry", [])
        # 第 1 个 entry 是 app 元信息，从第 2 个起才是评论
        for e in entries[1:] if p == 1 else entries:
            if "im:rating" not in e:
                continue
            out.append({
                "rating": int(e["im:rating"]["label"]),
                "title": e.get("title", {}).get("label", ""),
                "text": e.get("content", {}).get("label", "")[:600],
                "version": e.get("im:version", {}).get("label", ""),
                "author": e.get("author", {}).get("name", {}).get("label", ""),
            })
    return {"source": "appstore_reviews", "app_id": app_id, "count": len(out), "reviews": out}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("term"); s.add_argument("--limit", type=int, default=5); s.add_argument("--country", default="us")
    r = sub.add_parser("reviews"); r.add_argument("app_id"); r.add_argument("--pages", type=int, default=3); r.add_argument("--country", default="us")
    a = ap.parse_args()
    try:
        res = do_search(a.term, a.limit, a.country) if a.cmd == "search" else do_reviews(a.app_id, a.pages, a.country)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        res = {"source": "appstore", "error": str(e)}
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
