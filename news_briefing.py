#!/usr/bin/env python3
"""
Daily News Briefing — RSS 수집 + Resend 이메일 자동 발송
GitHub Actions cron으로 매일 오전 7시(KST) 실행
"""

import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

try:
    import feedparser
except ImportError:
    raise SystemExit("feedparser 미설치: pip install feedparser")

# ─── 설정 ─────────────────────────────────────────────────────────────────────

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
FROM_EMAIL     = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")
_to_override   = os.environ.get("TO_OVERRIDE", "").strip()
TO_EMAILS      = [_to_override] if _to_override else ["cmkim0316@gmail.com", "sergeykwon@gmail.com"]

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
DATE_STR = NOW.strftime("%Y년 %m월 %d일 (%a)").replace(
    "Mon","월").replace("Tue","화").replace("Wed","수").replace(
    "Thu","목").replace("Fri","금").replace("Sat","토").replace("Sun","일")

# ─── RSS 피드 정의 ─────────────────────────────────────────────────────────────

FEEDS = {
    "kr_general": [
        ("연합뉴스",  "https://www.yonhapnewstv.co.kr/feed/"),
        ("KBS 뉴스",  "https://news.kbs.co.kr/rss/rss.do?source=NETWORK_NEWS"),
        ("SBS 뉴스",  "https://news.sbs.co.kr/news/rss/rss.do?pNo=00&menuTypeCd=RECENT"),
        ("조선일보",  "https://www.chosun.com/arc/outboundfeeds/rss/"),
    ],
    "kr_stock": [
        ("한국경제",   "https://www.hankyung.com/feed/all-news"),
        ("매일경제",   "https://www.mk.co.kr/rss/30100061/"),
        ("이데일리",   "https://www.edaily.co.kr/rss/economy.xml"),
        ("KBS 경제",  "https://news.kbs.co.kr/rss/rss.do?source=NETWORK_NEWS&category=economy"),
    ],
    "kr_legal": [
        ("법률신문",   "https://www.lawtimes.co.kr/api/rss"),
        ("법률저널",   "https://www.lec.co.kr/rss/allNews.xml"),
        ("헤럴드법률", "https://biz.heraldcorp.com/rss/010000000000.xml"),
    ],
    "en_politics": [
        ("NPR Politics",  "https://feeds.npr.org/1001/rss.xml"),
        ("BBC US",        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
        ("Reuters US",    "https://feeds.reuters.com/Reuters/PoliticsNews"),
        ("PBS NewsHour",  "https://www.pbs.org/newshour/feeds/rss/politics"),
    ],
    "en_economy": [
        ("Yahoo Finance",   "https://finance.yahoo.com/news/rssindex"),
        ("CNBC Markets",    "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
        ("Reuters Business","https://feeds.reuters.com/reuters/businessNews"),
        ("Investopedia",    "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline"),
    ],
    "en_legal": [
        ("SCOTUSblog",    "https://www.scotusblog.com/feed/"),
        ("Above the Law", "https://abovethelaw.com/feed/"),
        ("Law360",        "https://www.law360.com/rss/articles"),
    ],
    "en_bar": [
        ("Law School Toolbox", "https://lawschooltoolbox.com/feed/"),
        ("JD Advising",        "https://jdadvising.com/feed/"),
        ("BARBRI Blog",        "https://www.barbri.com/blog/feed/"),
        ("Themis Bar Review",  "https://www.themisbar.com/blog/feed/"),
    ],
}

SECTION_TITLES = {
    "kr_general":  "1/ 오늘의 주요 국내외 뉴스",
    "kr_stock":    "2/ 국내외 주식 시장 뉴스",
    "kr_legal":    "3/ 국내외 법률 관련 최신 뉴스",
    "en_politics": "1/ U.S. Politics",
    "en_economy":  "2/ U.S. Economy &amp; Stock Market",
    "en_legal":    "3/ U.S. Legal News",
    "en_bar":      "4/ BAR Exam &#8212; Helpful Articles",
}

# ─── 유틸리티 ──────────────────────────────────────────────────────────────────

def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200] + "…" if len(text) > 200 else text

def fetch_feed(name: str, url: str, max_items: int = 3) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        feed = feedparser.parse(raw)
        items = []
        for entry in feed.entries[:max_items]:
            title   = strip_tags(entry.get("title", "")).strip()
            summary = strip_tags(entry.get("summary") or entry.get("description", ""))
            link    = entry.get("link", url)
            if title:
                items.append({"headline": title, "summary": summary, "url": link})
        print(f"  [{name}] {len(items)} articles fetched")
        return items
    except Exception as e:
        print(f"  [{name}] SKIP — {e}")
        return []

def collect_news(section: str, per_feed: int = 2) -> list[dict]:
    items = []
    for name, url in FEEDS[section]:
        items.extend(fetch_feed(name, url, per_feed))
        if len(items) >= 4:
            break
    return items[:4]

# ─── HTML 빌더 ─────────────────────────────────────────────────────────────────

def news_items_html(items: list[dict]) -> str:
    if not items:
        return '<div class="news-item"><div class="news-summary">뉴스를 가져오지 못했습니다.</div></div>'
    out = ""
    for item in items:
        headline = item["headline"].replace("<", "&lt;").replace(">", "&gt;")
        summary  = item["summary"].replace("<", "&lt;").replace(">", "&gt;")
        url      = item["url"]
        out += f"""
      <div class="news-item">
        <div class="news-headline">{headline}</div>
        <div class="news-summary">{summary}</div>
        <a href="{url}" class="read-full">Read Full &rarr;</a>
      </div>"""
    return out

def build_html(news: dict[str, list[dict]]) -> str:
    def section(key: str) -> str:
        return f"""
  <div class="section">
    <div class="section-title">{SECTION_TITLES[key]}</div>
    {news_items_html(news[key])}
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f9;margin:0;padding:0}}
  .wrapper{{max-width:700px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
  .header{{background:linear-gradient(135deg,#1a237e,#283593);padding:32px 36px}}
  .header h1{{color:#fff;margin:0;font-size:22px;font-weight:700}}
  .header p{{color:#90caf9;margin:6px 0 0;font-size:13px}}
  .divider{{height:6px;background:linear-gradient(90deg,#1a237e,#42a5f5)}}
  .lang-header{{background:#f0f4ff;padding:12px 36px;border-bottom:2px solid #e3e8ff}}
  .lang-header span{{font-size:13px;font-weight:700;color:#1a237e}}
  .section{{padding:24px 36px;border-bottom:1px solid #f0f0f0}}
  .section:last-of-type{{border-bottom:none}}
  .section-title{{font-size:15px;font-weight:700;color:#1a237e;margin:0 0 14px;padding-left:12px;border-left:4px solid #1a237e}}
  .news-item{{background:#f8f9fc;border-radius:8px;padding:14px 16px;margin-bottom:10px}}
  .news-item:last-child{{margin-bottom:0}}
  .news-headline{{font-size:13.5px;font-weight:700;color:#1a1a2e;margin:0 0 6px}}
  .news-summary{{font-size:12.5px;color:#555;line-height:1.6;margin:0 0 8px}}
  .read-full{{display:inline-block;font-size:11.5px;color:#1565c0;text-decoration:none;font-weight:600;background:#e3f2fd;padding:3px 10px;border-radius:12px}}
  .footer{{background:#f8f9fc;padding:20px 36px;text-align:center;color:#999;font-size:11px}}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>&#128240; Daily News Briefing</h1>
    <p>{DATE_STR} &nbsp;|&nbsp; &#127472;&#127479; 한국어 + &#127482;&#127480; English</p>
  </div>
  <div class="divider"></div>

  <div class="lang-header"><span>&#127472;&#127479; 한국어 섹션</span></div>
  {section("kr_general")}
  {section("kr_stock")}
  {section("kr_legal")}

  <div class="divider"></div>

  <div class="lang-header"><span>&#127482;&#127480; English Section</span></div>
  {section("en_politics")}
  {section("en_economy")}
  {section("en_legal")}
  {section("en_bar")}

  <div class="footer">
    Daily News Briefing &nbsp;|&nbsp; {DATE_STR}<br>
    Sent to {", ".join(TO_EMAILS)}
  </div>
</div>
</body>
</html>"""

# ─── 이메일 발송 ───────────────────────────────────────────────────────────────

def send_email(subject: str, html: str) -> None:
    import sys
    print(f"  FROM : {FROM_EMAIL}")
    print(f"  TO   : {TO_EMAILS}")
    payload = {
        "from": FROM_EMAIL,
        "to": TO_EMAILS,
        "subject": subject,
        "html": html,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            print(f"✅ 발송 완료! id={json.loads(body).get('id')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ Resend HTTP {e.code}: {body}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 네트워크 오류: {type(e).__name__}: {e}")
        sys.exit(1)

# ─── 메인 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== Daily News Briefing — {DATE_STR} ===\n")

    sections = list(FEEDS.keys())
    news: dict[str, list[dict]] = {}

    for sec in sections:
        print(f"[{sec}] 뉴스 수집 중...")
        news[sec] = collect_news(sec)
        print(f"  → {len(news[sec])}개 수집 완료\n")

    print("이메일 HTML 빌드 중...")
    html = build_html(news)

    subject = f"📰 Daily News Briefing — {DATE_STR}"
    print(f"발송 중: {subject}")
    send_email(subject, html)
