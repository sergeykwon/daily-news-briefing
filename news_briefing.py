#!/usr/bin/env python3
"""
Daily News Briefing — RSS 수집 + Resend 이메일 자동 발송
매일 오전 7:30 KST (GitHub Actions cron)
"""

import os, json, re, urllib.request, urllib.error, sys
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

KST      = timezone(timedelta(hours=9))
NOW      = datetime.now(KST)
DATE_STR = NOW.strftime("%Y년 %m월 %d일 (%a)").replace(
    "Mon","월").replace("Tue","화").replace("Wed","수").replace(
    "Thu","목").replace("Fri","금").replace("Sat","토").replace("Sun","일")

# ─── RSS 피드 정의 ─────────────────────────────────────────────────────────────
# (name, url, max_items)

FEEDS = {
    # ── 국내 뉴스 ──────────────────────────────────────────────────────────────
    "kr_politics": [
        ("동아일보 정치",     "https://rss.donga.com/politics.xml",        3),
        ("KBS 정치",         "https://news.kbs.co.kr/rss/rss.do?source=NETWORK_NEWS&category=politics", 3),
        ("한겨레 정치",       "https://www.hani.co.kr/rss/politics/",       3),
    ],
    "kr_economy": [
        ("한국경제",          "https://www.hankyung.com/feed/economy",      3),
        ("매일경제 경제",      "https://www.mk.co.kr/rss/30100041/",        3),
        ("동아일보 경제",      "https://rss.donga.com/economy.xml",         3),
    ],
    "kr_society": [
        ("동아일보 사회",      "https://rss.donga.com/society.xml",         3),
        ("KBS 사회",          "https://news.kbs.co.kr/rss/rss.do?source=NETWORK_NEWS&category=society", 3),
        ("한겨레 사회",        "https://www.hani.co.kr/rss/society/",       3),
    ],
    "kr_sports": [
        ("동아일보 스포츠",    "https://rss.donga.com/sports.xml",          3),
        ("KBS 스포츠",        "https://news.kbs.co.kr/rss/rss.do?source=NETWORK_NEWS&category=sports", 3),
        ("네이버 스포츠",      "https://sports.news.naver.com/news/rss.nhn", 3),
    ],

    # ── 국내외 주식/크립토 ─────────────────────────────────────────────────────
    "kr_market": [
        ("한국경제 증권",      "https://www.hankyung.com/feed/finance",     4),
        ("연합인포맥스",       "https://news.einfomax.co.kr/rss/allArticle.xml", 4),
        ("매일경제 증권",      "https://www.mk.co.kr/rss/30100061/",        4),
        ("뉴스핌 증권",        "https://www.newspim.com/rss/S0201",         3),
    ],
    "kr_stocks": [
        ("한국경제 종목",      "https://www.hankyung.com/feed/finance",     5),
        ("이데일리 종목",      "https://www.edaily.co.kr/rss/stock.xml",    5),
        ("머니투데이 종목",    "https://www.mt.co.kr/rss/stock.xml",        4),
        ("팍스넷",            "https://paxnet.co.kr/rss/news.xml",          4),
    ],
    "kr_crypto": [
        ("코인데스크코리아",   "https://www.coindeskkorea.com/feed/",        4),
        ("토큰포스트",         "https://tokenpost.kr/rss",                   4),
        ("블록미디어",         "https://www.blockmedia.co.kr/feed",          4),
        ("디센터",            "https://decenter.kr/rss",                    3),
    ],

    # ── 국내 법률 ─────────────────────────────────────────────────────────────
    "kr_legal": [
        ("법률신문",          "https://www.lawtimes.co.kr/api/rss",         3),
        ("법률저널",          "https://www.lec.co.kr/rss/allNews.xml",      3),
        ("로앤비 판례",        "https://www.lawnb.com/Info/RssFeed",         3),
    ],

    # ── 미국 뉴스 ─────────────────────────────────────────────────────────────
    "en_politics": [
        ("NPR Politics",      "https://feeds.npr.org/1001/rss.xml",         3),
        ("BBC US",            "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", 3),
        ("Reuters Politics",  "https://feeds.reuters.com/Reuters/PoliticsNews", 3),
    ],
    "en_economy": [
        ("Yahoo Finance",     "https://finance.yahoo.com/news/rssindex",    3),
        ("CNBC Economy",      "https://www.cnbc.com/id/20910258/device/rss/rss.html", 3),
        ("Reuters Business",  "https://feeds.reuters.com/reuters/businessNews", 3),
    ],
    "en_society": [
        ("AP News",           "https://rsshub.app/apnews/topics/apf-topnews", 3),
        ("Reuters World",     "https://feeds.reuters.com/reuters/worldNews", 3),
        ("ESPN",              "https://www.espn.com/espn/rss/news",         3),
    ],

    # ── 미국 주식/크립토 ──────────────────────────────────────────────────────
    "en_market": [
        ("Yahoo Finance",     "https://finance.yahoo.com/news/rssindex",    4),
        ("CNBC Markets",      "https://www.cnbc.com/id/100003114/device/rss/rss.html", 4),
        ("MarketWatch",       "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/", 4),
        ("Seeking Alpha",     "https://seekingalpha.com/market_currents.xml", 3),
    ],
    "en_stocks": [
        ("Yahoo Finance",     "https://finance.yahoo.com/news/rssindex",    5),
        ("Motley Fool",       "https://www.fool.com/feeds/index.aspx",      5),
        ("Investopedia",      "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline", 4),
        ("Barron's",          "https://www.barrons.com/feed/rss/wsj-com-all", 4),
    ],
    "en_crypto": [
        ("CoinDesk",          "https://www.coindesk.com/arc/outboundfeeds/rss/", 4),
        ("CoinTelegraph",     "https://cointelegraph.com/rss",              4),
        ("Decrypt",           "https://decrypt.co/feed",                   4),
        ("The Block",         "https://www.theblock.co/rss.xml",            3),
    ],

    # ── 미국 법률 & BAR ───────────────────────────────────────────────────────
    "en_legal": [
        ("SCOTUSblog",        "https://www.scotusblog.com/feed/",           3),
        ("Above the Law",     "https://abovethelaw.com/feed/",              3),
        ("Law360",            "https://www.law360.com/rss/articles",        3),
    ],
    "en_bar": [
        ("Law School Toolbox","https://lawschooltoolbox.com/feed/",         3),
        ("JD Advising",       "https://jdadvising.com/feed/",               3),
        ("BARBRI Blog",       "https://www.barbri.com/blog/feed/",           3),
    ],
}

# ─── 유틸리티 ──────────────────────────────────────────────────────────────────

def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def truncate(text: str, n: int) -> str:
    return text[:n] + "…" if len(text) > n else text

def fetch_feed(name: str, url: str, max_items: int) -> list[dict]:
    headers = {
        "User-Agent": "curl/8.5.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        feed = feedparser.parse(raw)
        items = []
        for entry in feed.entries[:max_items]:
            title   = strip_tags(entry.get("title", "")).strip()
            summary = truncate(strip_tags(
                entry.get("summary") or entry.get("description", "")), 280)
            link    = entry.get("link", url)
            if title:
                items.append({"headline": title, "summary": summary, "url": link})
        print(f"  [{name}] {len(items)} articles")
        return items
    except Exception as e:
        print(f"  [{name}] SKIP — {e}")
        return []

def collect(section: str) -> list[dict]:
    items = []
    for name, url, max_items in FEEDS[section]:
        items.extend(fetch_feed(name, url, max_items))
        if len(items) >= 4:
            break
    return items[:4]

def collect_stocks(section: str, limit: int = 5) -> list[dict]:
    """주식 종목은 더 많이 수집"""
    items = []
    for name, url, max_items in FEEDS[section]:
        items.extend(fetch_feed(name, url, max_items))
        if len(items) >= limit:
            break
    return items[:limit]

# ─── HTML 빌더 ─────────────────────────────────────────────────────────────────

STYLES = """
<style>
  body{font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f9;margin:0;padding:0}
  .wrapper{max-width:720px;margin:30px auto;background:#fff;border-radius:12px;
    overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08)}
  .header{background:linear-gradient(135deg,#1a237e,#283593);padding:28px 36px}
  .header h1{color:#fff;margin:0;font-size:22px;font-weight:700}
  .header p{color:#90caf9;margin:6px 0 0;font-size:13px}
  .divider{height:5px;background:linear-gradient(90deg,#1a237e,#42a5f5)}
  .lang-header{background:#eef1fb;padding:10px 36px;border-bottom:2px solid #dde2f5}
  .lang-header span{font-size:13px;font-weight:800;color:#1a237e;letter-spacing:.3px}
  .major-section{padding:22px 36px 4px;border-bottom:2px solid #e8ecf8}
  .major-title{font-size:15px;font-weight:800;color:#1a237e;margin:0 0 14px;
    padding-left:12px;border-left:4px solid #1a237e}
  .sub-section{margin-bottom:16px}
  .sub-label{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.5px;
    text-transform:uppercase;padding:3px 10px;border-radius:12px;margin-bottom:8px}
  .sub-politics{background:#fce4ec;color:#c62828}
  .sub-economy{background:#e8f5e9;color:#2e7d32}
  .sub-society{background:#fff3e0;color:#e65100}
  .sub-sports{background:#e3f2fd;color:#1565c0}
  .sub-market{background:#e8f5e9;color:#1b5e20}
  .sub-stocks{background:#fce4ec;color:#880e4f}
  .sub-crypto{background:#ede7f6;color:#4527a0}
  .sub-legal{background:#fff8e1;color:#f57f17}
  .sub-bar{background:#e0f2f1;color:#004d40}
  .news-item{background:#f8f9fc;border-radius:8px;padding:13px 15px;margin-bottom:8px}
  .news-item.stock{border-left:3px solid #2e7d32}
  .news-item.crypto{border-left:3px solid #6a1b9a}
  .news-headline{font-size:13px;font-weight:700;color:#1a1a2e;margin:0 0 5px;line-height:1.4}
  .news-summary{font-size:12px;color:#555;line-height:1.6;margin:0 0 7px}
  .read-full{display:inline-block;font-size:11px;color:#1565c0;text-decoration:none;
    font-weight:600;background:#e3f2fd;padding:2px 9px;border-radius:10px}
  .footer{background:#f8f9fc;padding:18px 36px;text-align:center;color:#aaa;font-size:11px}
</style>
"""

def item_html(item: dict, css_class: str = "") -> str:
    h = item["headline"].replace("<","&lt;").replace(">","&gt;")
    s = item["summary"].replace("<","&lt;").replace(">","&gt;")
    cls = f'news-item {css_class}' if css_class else 'news-item'
    return f"""
      <div class="{cls}">
        <div class="news-headline">{h}</div>
        <div class="news-summary">{s}</div>
        <a href="{item['url']}" class="read-full">Read Full &rarr;</a>
      </div>"""

def items_html(items: list[dict], css_class: str = "") -> str:
    if not items:
        return '<div class="news-item"><div class="news-summary">뉴스를 가져오지 못했습니다.</div></div>'
    return "".join(item_html(i, css_class) for i in items)

def sub_section(label: str, label_class: str, items: list[dict], css_class: str = "") -> str:
    return f"""
    <div class="sub-section">
      <span class="sub-label {label_class}">{label}</span>
      {items_html(items, css_class)}
    </div>"""

def build_html(news: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
{STYLES}
</head>
<body>
<div class="wrapper">

  <!-- HEADER -->
  <div class="header">
    <h1>&#128240; Daily News Briefing</h1>
    <p>{DATE_STR} &nbsp;|&nbsp; &#127472;&#127479; 한국어 + &#127482;&#127480; English</p>
  </div>
  <div class="divider"></div>

  <!-- ===== KOREAN ===== -->
  <div class="lang-header"><span>&#127472;&#127479; 한국어 섹션</span></div>

  <!-- 1. 오늘의 주요 뉴스 -->
  <div class="major-section">
    <div class="major-title">1&#47; 오늘의 주요 국내 뉴스</div>
    {sub_section("&#128202; 정치", "sub-politics", news["kr_politics"])}
    {sub_section("&#128200; 경제", "sub-economy",  news["kr_economy"])}
    {sub_section("&#127960; 사회", "sub-society",  news["kr_society"])}
    {sub_section("&#9917; 스포츠", "sub-sports",   news["kr_sports"])}
  </div>

  <!-- 2. 주식/투자 -->
  <div class="major-section">
    <div class="major-title">2&#47; 국내외 주식 &amp; 투자 마켓</div>
    {sub_section("&#128308; 주식 시장 (코스피&#47;코스닥&#47;글로벌)", "sub-market", news["kr_market"], "stock")}
    {sub_section("&#128269; 주식 종목 상세", "sub-stocks", news["kr_stocks"], "stock")}
    {sub_section("&#129689; 크립토 &amp; 스테이블코인", "sub-crypto", news["kr_crypto"], "crypto")}
  </div>

  <!-- 3. 법률 -->
  <div class="major-section" style="border-bottom:none">
    <div class="major-title">3&#47; 법률 뉴스</div>
    {sub_section("&#9878; 법률", "sub-legal", news["kr_legal"])}
  </div>

  <div class="divider"></div>

  <!-- ===== ENGLISH ===== -->
  <div class="lang-header"><span>&#127482;&#127480; English Section</span></div>

  <!-- 1. U.S. News -->
  <div class="major-section">
    <div class="major-title">1&#47; Today&#39;s U.S. News</div>
    {sub_section("&#128202; Politics", "sub-politics", news["en_politics"])}
    {sub_section("&#128200; Economy", "sub-economy",   news["en_economy"])}
    {sub_section("&#127760; Society &amp; Sports", "sub-sports", news["en_society"])}
  </div>

  <!-- 2. Markets & Crypto -->
  <div class="major-section">
    <div class="major-title">2&#47; Markets &amp; Crypto</div>
    {sub_section("&#128308; Stock Market Overview", "sub-market", news["en_market"], "stock")}
    {sub_section("&#128269; Individual Stocks &amp; Sectors", "sub-stocks", news["en_stocks"], "stock")}
    {sub_section("&#129689; Crypto &amp; Stablecoins", "sub-crypto", news["en_crypto"], "crypto")}
  </div>

  <!-- 3. Legal & BAR -->
  <div class="major-section" style="border-bottom:none">
    <div class="major-title">3&#47; Legal &amp; BAR Exam</div>
    {sub_section("&#9878; U.S. Legal News", "sub-legal", news["en_legal"])}
    {sub_section("&#128221; BAR Exam Resources", "sub-bar", news["en_bar"])}
  </div>

  <div class="footer">
    Daily News Briefing &nbsp;|&nbsp; {DATE_STR}<br>
    Sent to: {", ".join(TO_EMAILS)}
  </div>
</div>
</body>
</html>"""

# ─── 이메일 발송 ───────────────────────────────────────────────────────────────

def send_email(subject: str, html: str) -> None:
    print(f"  FROM : {FROM_EMAIL}")
    print(f"  TO   : {TO_EMAILS}")
    payload = {"from": FROM_EMAIL, "to": TO_EMAILS, "subject": subject, "html": html}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=data,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "curl/8.5.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            print(f"✅ 발송 완료! id={json.loads(body).get('id')}")
    except urllib.error.HTTPError as e:
        print(f"❌ Resend HTTP {e.code}: {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류: {type(e).__name__}: {e}")
        sys.exit(1)

# ─── 메인 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== Daily News Briefing — {DATE_STR} ===\n")

    STOCK_SECTIONS = {"kr_stocks", "en_stocks"}
    sections = list(FEEDS.keys())
    news: dict[str, list[dict]] = {}

    for sec in sections:
        print(f"[{sec}]")
        if sec in STOCK_SECTIONS:
            news[sec] = collect_stocks(sec, limit=5)
        else:
            news[sec] = collect(sec)
        print(f"  → {len(news[sec])}개\n")

    print("HTML 빌드 중...")
    html = build_html(news)

    subject = f"📰 Daily News Briefing — {DATE_STR}"
    print(f"\n발송: {subject}")
    send_email(subject, html)
