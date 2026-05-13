#!/usr/bin/env python3
"""
Daily News Briefing — Marketing Brew style
매일 오전 7:30 KST (GitHub Actions cron)
"""

import os, json, re, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

try:
    import feedparser
except ImportError:
    raise SystemExit("feedparser not installed: pip install feedparser")

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("WARNING: yfinance not installed — market data skipped")

# ─── 설정 ─────────────────────────────────────────────────────────────────────

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
_from_addr     = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")
FROM_EMAIL     = f"Daily News Update <{_from_addr}>"
_to_override   = os.environ.get("TO_OVERRIDE", "").strip()
TO_EMAILS      = [_to_override] if _to_override else ["cmkim0316@gmail.com", "sergeykwon@gmail.com"]

KST      = timezone(timedelta(hours=9))
NOW      = datetime.now(KST)
DATE_KR  = NOW.strftime("%Y년 %m월 %d일 (%a)").replace(
    "Mon","월").replace("Tue","화").replace("Wed","수").replace(
    "Thu","목").replace("Fri","금").replace("Sat","토").replace("Sun","일")
DATE_EN  = NOW.strftime("%B %d, %Y")

# ─── 마켓 워치리스트 ──────────────────────────────────────────────────────────

KR_INDICES = [
    ("KOSPI",      "^KS11",    "index_kr"),
    ("KOSDAQ",     "^KQ11",    "index_kr"),
    ("USD/KRW",    "KRW=X",    "fx"),
]
KR_STOCKS = [
    ("삼성전자",   "005930.KS", "stock_kr"),
    ("SK하이닉스", "000660.KS", "stock_kr"),
    ("NAVER",      "035420.KS", "stock_kr"),
    ("카카오",     "035720.KS", "stock_kr"),
]
KR_CRYPTO = [
    ("Bitcoin",    "BTC-USD",  "crypto"),
    ("Ethereum",   "ETH-USD",  "crypto"),
]

US_INDICES = [
    ("Nasdaq",     "^IXIC",   "index_us"),
    ("S&P 500",    "^GSPC",   "index_us"),
    ("Dow Jones",  "^DJI",    "index_us"),
    ("10-Year",    "^TNX",    "rate"),
]
US_STOCKS = [
    ("Amazon",     "AMZN",    "stock_us"),
    ("Google",     "GOOGL",   "stock_us"),
    ("Apple",      "AAPL",    "stock_us"),
    ("NVTS",       "NVTS",    "stock_us"),
    ("Oracle",     "ORCL",    "stock_us"),
    ("Intel",      "INTC",    "stock_us"),
    ("NVIDIA",     "NVDA",    "stock_us"),
]
US_CRYPTO = [
    ("Bitcoin",    "BTC-USD", "crypto"),
    ("Ethereum",   "ETH-USD", "crypto"),
]

# ─── RSS 피드 ─────────────────────────────────────────────────────────────────

FEEDS = {
    "kr_politics": [
        ("동아일보 정치",  "https://rss.donga.com/politics.xml",         3),
        ("한겨레 정치",    "https://www.hani.co.kr/rss/politics/",        3),
        ("KBS 정치",      "https://news.kbs.co.kr/rss/rss.do?source=NETWORK_NEWS&category=politics", 3),
    ],
    "kr_economy": [
        ("한국경제",       "https://www.hankyung.com/feed/economy",       3),
        ("매일경제",       "https://www.mk.co.kr/rss/30100041/",          3),
        ("동아일보 경제",  "https://rss.donga.com/economy.xml",           3),
    ],
    "kr_society": [
        ("한겨레 사회",    "https://www.hani.co.kr/rss/society/",         3),
        ("동아일보 사회",  "https://rss.donga.com/society.xml",           3),
    ],
    "kr_sports": [
        ("동아일보 스포츠","https://rss.donga.com/sports.xml",            3),
        ("KBS 스포츠",    "https://news.kbs.co.kr/rss/rss.do?source=NETWORK_NEWS&category=sports", 3),
    ],
    "kr_market_news": [
        ("한국경제 증권",  "https://www.hankyung.com/feed/finance",       4),
        ("연합인포맥스",   "https://news.einfomax.co.kr/rss/allArticle.xml", 4),
        ("뉴스핌 증권",    "https://www.newspim.com/rss/S0201",           3),
    ],
    "kr_crypto_news": [
        ("토큰포스트",     "https://tokenpost.kr/rss",                    4),
        ("블록미디어",     "https://www.blockmedia.co.kr/feed",           4),
        ("디센터",         "https://decenter.kr/rss",                     3),
    ],
    "kr_legal": [
        ("법률신문",       "https://www.lawtimes.co.kr/api/rss",          3),
        ("한국경제 사회",  "https://www.hankyung.com/feed/society",       3),
    ],
    "en_politics": [
        ("NPR Politics",  "https://feeds.npr.org/1001/rss.xml",           3),
        ("BBC US",        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", 3),
    ],
    "en_economy": [
        ("CNBC Economy",  "https://www.cnbc.com/id/20910258/device/rss/rss.html", 3),
        ("MarketWatch",   "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/", 3),
        ("NPR Economy",   "https://feeds.npr.org/1006/rss.xml",           3),
    ],
    "en_society": [
        ("BBC World",     "https://feeds.bbci.co.uk/news/world/rss.xml",  3),
        ("ESPN",          "https://www.espn.com/espn/rss/news",           3),
        ("NPR World",     "https://feeds.npr.org/1004/rss.xml",           3),
    ],
    "en_market_news": [
        ("MarketWatch",   "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/", 4),
        ("Motley Fool",   "https://www.fool.com/feeds/index.aspx",        4),
        ("Investopedia",  "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline", 3),
    ],
    "en_crypto_news": [
        ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/", 4),
        ("CoinTelegraph", "https://cointelegraph.com/rss",                 4),
        ("Decrypt",       "https://decrypt.co/feed",                       3),
    ],
    "en_legal": [
        ("SCOTUSblog",    "https://www.scotusblog.com/feed/",              3),
        ("Above the Law", "https://abovethelaw.com/feed/",                 3),
    ],
    "en_bar": [
        ("JD Advising",   "https://jdadvising.com/feed/",                  3),
        ("Law School Toolbox", "https://lawschooltoolbox.com/feed/",       3),
    ],
}

# ─── 마켓 데이터 수집 ──────────────────────────────────────────────────────────

def fmt_price(sym: str, kind: str, val: float) -> str:
    if kind == "rate":
        return f"{val:.3f}%"
    elif kind == "crypto":
        return f"${val:,.0f}"
    elif kind == "fx":
        return f"₩{val:,.1f}"
    elif kind in ("stock_kr", "index_kr"):
        return f"₩{val:,.0f}" if kind == "stock_kr" else f"{val:,.2f}"
    else:
        return f"${val:,.2f}" if kind == "stock_us" else f"{val:,.2f}"

def fetch_prices(watchlist: list) -> list[dict]:
    if not HAS_YF:
        return []
    symbols = [w[1] for w in watchlist]
    results = []
    try:
        data = yf.download(symbols, period="2d", progress=False, auto_adjust=True, threads=True)
        closes = data["Close"] if hasattr(data["Close"], "columns") else data[["Close"]].rename(columns={"Close": symbols[0]})
        for name, sym, kind in watchlist:
            try:
                col = closes[sym]
                prices = col.dropna()
                if len(prices) < 2:
                    continue
                prev = float(prices.iloc[-2])
                curr = float(prices.iloc[-1])
                chg_pct = (curr - prev) / prev * 100
                if kind == "rate":
                    chg_str = f"{(curr - prev) * 100:+.1f} bps"
                else:
                    chg_str = f"{chg_pct:+.2f}%"
                results.append({
                    "name": name, "symbol": sym, "kind": kind,
                    "price": fmt_price(sym, kind, curr),
                    "change": chg_str,
                    "up": chg_pct >= 0,
                    "chg_pct": chg_pct,
                })
                print(f"  [{sym}] {fmt_price(sym, kind, curr)} {chg_str}")
            except Exception as e:
                print(f"  [{sym}] price error: {e}")
    except Exception as e:
        print(f"  [market] download error: {e}")
    return results

# ─── RSS 수집 ─────────────────────────────────────────────────────────────────

def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", re.sub(r"&[a-z]+;", " ", text)).strip()

def fetch_feed(name: str, url: str, max_items: int) -> list[dict]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "curl/8.5.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        feed = feedparser.parse(raw)
        items = []
        for entry in feed.entries[:max_items]:
            title   = strip_tags(entry.get("title", "")).strip()
            summary = strip_tags(entry.get("summary") or entry.get("description", ""))
            if len(summary) > 260:
                summary = summary[:260] + "…"
            link = entry.get("link", url)
            if title:
                items.append({"headline": title, "summary": summary, "url": link})
        print(f"  [{name}] {len(items)} articles")
        return items
    except Exception as e:
        print(f"  [{name}] SKIP — {e}")
        return []

def collect(section: str, limit: int = 4) -> list[dict]:
    items = []
    for name, url, max_items in FEEDS[section]:
        items.extend(fetch_feed(name, url, max_items))
        if len(items) >= limit:
            break
    return items[:limit]

# ─── HTML 컴포넌트 ─────────────────────────────────────────────────────────────

CSS = """<style>
body{margin:0;padding:0;background:#f0f0f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}
.shell{max-width:640px;margin:0 auto;background:#f0f0f0}
.topbar{background:#f0f0f0;padding:8px 20px;text-align:center;font-size:11px;color:#888}
.card{background:#fff;margin:0;padding:0}
/* Header */
.hdr{background:#1a1a2e;padding:28px 32px 22px}
.hdr-title{color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;margin:0 0 4px}
.hdr-sub{color:#8892b0;font-size:13px;margin:0}
/* TOC */
.toc{background:#f8f9fc;border-bottom:2px solid #e8ecf8;padding:14px 32px}
.toc-title{font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.8px;margin:0 0 8px}
.toc-item{font-size:13px;color:#1a237e;line-height:2;display:block;text-decoration:none}
/* Lang divider */
.lang-div{background:#1a1a2e;padding:10px 32px}
.lang-div span{color:#90caf9;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
/* Section */
.section{padding:22px 32px;border-bottom:1px solid #eee}
.cat-tag{display:inline-block;font-size:10px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;padding:3px 10px;border-radius:3px;margin-bottom:12px}
.tag-pol{background:#fce4ec;color:#b71c1c}
.tag-eco{background:#e8f5e9;color:#1b5e20}
.tag-soc{background:#fff3e0;color:#e65100}
.tag-spt{background:#e3f2fd;color:#0d47a1}
.tag-mkt{background:#e8f5e9;color:#1b5e20}
.tag-cry{background:#ede7f6;color:#4527a0}
.tag-leg{background:#fff8e1;color:#f57f17}
.tag-bar{background:#e0f2f1;color:#004d40}
/* Article */
.art{margin-bottom:16px;padding-bottom:16px;border-bottom:1px dashed #eee}
.art:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.art-hl{font-size:14px;font-weight:700;color:#1a1a2e;margin:0 0 5px;line-height:1.4}
.art-sum{font-size:13px;color:#555;line-height:1.65;margin:0 0 6px}
.art-link{font-size:12px;color:#1565c0;text-decoration:none;font-weight:600}
.art-link:hover{text-decoration:underline}
/* Market table */
.mkt-box{margin:0 32px 22px;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden}
.mkt-header{background:#1a237e;color:#fff;padding:10px 16px;font-size:12px;font-weight:800;letter-spacing:.8px;text-transform:uppercase}
.mkt-subheader{background:#f0f4ff;padding:7px 16px;font-size:11px;font-weight:700;color:#1a237e;letter-spacing:.5px;border-top:1px solid #dde2f5;border-bottom:1px solid #dde2f5}
.mkt-row{display:flex;align-items:center;padding:9px 16px;border-bottom:1px solid #f5f5f5;font-size:13px}
.mkt-row:last-child{border-bottom:none}
.mkt-arrow{width:18px;font-size:11px}
.mkt-arrow.up{color:#2e7d32}
.mkt-arrow.dn{color:#c62828}
.mkt-name{flex:1;color:#333;font-weight:500}
.mkt-sym{font-size:10px;color:#999;margin-left:5px}
.mkt-price{font-weight:700;color:#1a1a2e;min-width:100px;text-align:right}
.mkt-chg{min-width:90px;text-align:right}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:11.5px;font-weight:700}
.badge.up{background:#e8f5e9;color:#1b5e20}
.badge.dn{background:#ffebee;color:#b71c1c}
.mkt-note{padding:8px 16px;font-size:10px;color:#999;background:#fafafa;border-top:1px solid #f0f0f0}
/* Footer */
.footer{background:#1a1a2e;padding:20px 32px;text-align:center}
.footer p{color:#555;font-size:11px;margin:4px 0}
</style>"""

def mkt_row_html(item: dict) -> str:
    arrow_cls = "up" if item["up"] else "dn"
    arrow     = "▲" if item["up"] else "▼"
    badge_cls = "up" if item["up"] else "dn"
    sym_tag   = f'<span class="mkt-sym">({item["symbol"]})</span>' if not item["symbol"].startswith("^") else ""
    return f"""
    <div class="mkt-row">
      <div class="mkt-arrow {arrow_cls}">{arrow}</div>
      <div class="mkt-name">{item["name"]}{sym_tag}</div>
      <div class="mkt-price">{item["price"]}</div>
      <div class="mkt-chg"><span class="badge {badge_cls}">{item["change"]}</span></div>
    </div>"""

def market_table_html(title: str, sections: list[tuple[str, list]], note: str = "") -> str:
    inner = ""
    for subheader, items in sections:
        if not items:
            continue
        rows = "".join(mkt_row_html(i) for i in items)
        inner += f'<div class="mkt-subheader">{subheader}</div>{rows}'
    note_html = f'<div class="mkt-note">* {note}</div>' if note else ""
    return f"""
  <div class="mkt-box">
    <div class="mkt-header">📊 {title}</div>
    {inner}
    {note_html}
  </div>"""

def articles_html(items: list, tag_cls: str, tag_label: str) -> str:
    if not items:
        arts = '<div class="art"><p class="art-sum">뉴스를 가져오지 못했습니다.</p></div>'
    else:
        arts = "".join(f"""
    <div class="art">
      <div class="art-hl">{i['headline'].replace('<','&lt;').replace('>','&gt;')}</div>
      <div class="art-sum">{i['summary'].replace('<','&lt;').replace('>','&gt;')}</div>
      <a href="{i['url']}" class="art-link">Continue reading →</a>
    </div>""" for i in items)
    return f"""
  <div class="section">
    <span class="cat-tag {tag_cls}">{tag_label}</span>
    {arts}
  </div>"""

def build_html(news: dict, mkt: dict) -> str:
    kr_idx  = mkt.get("kr_indices", [])
    kr_stk  = mkt.get("kr_stocks",  [])
    kr_cry  = mkt.get("kr_crypto",  [])
    us_idx  = mkt.get("us_indices", [])
    us_stk  = mkt.get("us_stocks",  [])
    us_cry  = mkt.get("us_crypto",  [])

    kr_mkt_table = market_table_html(
        "국내외 마켓 데이터",
        [
            ("국내 지수 / Korea Indices", kr_idx),
            ("국내 종목 / Korea Stocks",  kr_stk),
            ("해외 지수 / U.S. Indices",  us_idx),
            ("해외 종목 / U.S. Stocks",   us_stk),
            ("크립토 / Crypto",            kr_cry),
        ],
        "Data by Yahoo Finance. 장 마감 기준.")

    us_mkt_table = market_table_html(
        "U.S. Markets & Stocks",
        [
            ("주요 지수 / Key Indices", us_idx),
            ("주요 종목 / Stocks",      us_stk),
            ("크립토 / Crypto",         us_cry),
        ],
        "Data provided by Yahoo Finance. As of market close.")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Daily News Briefing — {DATE_KR}</title>
{CSS}
</head>
<body>
<div class="shell">
<div class="topbar">{DATE_EN} &nbsp;·&nbsp; Daily News Briefing</div>

<div class="card">

  <!-- ── HEADER ──────────────────────────────────── -->
  <div class="hdr">
    <div class="hdr-title">📰 Daily News Briefing</div>
    <div class="hdr-sub">{DATE_KR} &nbsp;|&nbsp; 🇰🇷 한국어 + 🇺🇸 English</div>
  </div>

  <!-- ── TOC ─────────────────────────────────────── -->
  <div class="toc">
    <div class="toc-title">In today's edition</div>
    <span class="toc-item">🇰🇷 오늘의 국내 주요 뉴스 — 정치 · 경제 · 사회 · 스포츠</span>
    <span class="toc-item">📈 국내외 주식 &amp; 크립토 마켓</span>
    <span class="toc-item">🇺🇸 Today's U.S. News — Politics · Economy · Society &amp; Sports</span>
    <span class="toc-item">📊 U.S. Markets, Stocks &amp; Crypto</span>
    <span class="toc-item">⚖️ Legal News &amp; BAR Exam</span>
  </div>

  <!-- ════════ 🇰🇷 KOREAN SECTION ════════ -->
  <div class="lang-div"><span>🇰🇷 한국어 섹션</span></div>

  {articles_html(news["kr_politics"], "tag-pol", "🔴 정치")}
  {articles_html(news["kr_economy"],  "tag-eco", "🟢 경제")}
  {articles_html(news["kr_society"],  "tag-soc", "🟠 사회")}
  {articles_html(news["kr_sports"],   "tag-spt", "🔵 스포츠")}

  <!-- KR 마켓 뉴스 -->
  {articles_html(news["kr_market_news"], "tag-mkt", "📈 증시 뉴스")}
  {kr_mkt_table}
  {articles_html(news["kr_crypto_news"], "tag-cry", "🟣 크립토 &amp; 스테이블코인")}

  <!-- KR 법률 -->
  {articles_html(news["kr_legal"], "tag-leg", "⚖️ 법률")}

  <!-- ════════ 🇺🇸 ENGLISH SECTION ════════ -->
  <div class="lang-div"><span>🇺🇸 English Section</span></div>

  {articles_html(news["en_politics"],    "tag-pol", "🔴 Politics")}
  {articles_html(news["en_economy"],     "tag-eco", "🟢 Economy")}
  {articles_html(news["en_society"],     "tag-spt", "🔵 Society &amp; Sports")}

  <!-- US 마켓 뉴스 + 테이블 -->
  {articles_html(news["en_market_news"], "tag-mkt", "📈 Market News")}
  {us_mkt_table}
  {articles_html(news["en_crypto_news"], "tag-cry", "🟣 Crypto &amp; Stablecoins")}

  <!-- US 법률 -->
  {articles_html(news["en_legal"], "tag-leg", "⚖️ U.S. Legal News")}
  {articles_html(news["en_bar"],   "tag-bar", "📚 BAR Exam")}

  <!-- ── FOOTER ────────────────────────────────── -->
  <div class="footer">
    <p style="color:#8892b0;font-size:13px;font-weight:700">Daily News Update</p>
    <p>Sent to: {", ".join(TO_EMAILS)}</p>
    <p>{DATE_KR}</p>
  </div>

</div><!-- /card -->
</div><!-- /shell -->
</body>
</html>"""

# ─── 이메일 발송 ───────────────────────────────────────────────────────────────

def send_email(subject: str, html: str) -> None:
    print(f"  FROM : {FROM_EMAIL}")
    print(f"  TO   : {TO_EMAILS}")
    payload = {"from": FROM_EMAIL, "to": TO_EMAILS, "subject": subject, "html": html}
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
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
    print(f"=== Daily News Briefing — {DATE_KR} ===\n")

    # 1. 마켓 데이터
    print("[마켓 데이터 수집]")
    mkt = {
        "kr_indices": fetch_prices(KR_INDICES),
        "kr_stocks":  fetch_prices(KR_STOCKS),
        "kr_crypto":  fetch_prices(KR_CRYPTO),
        "us_indices": fetch_prices(US_INDICES),
        "us_stocks":  fetch_prices(US_STOCKS),
        "us_crypto":  fetch_prices(US_CRYPTO),
    }
    print()

    # 2. 뉴스 RSS 수집
    news = {}
    for sec in FEEDS:
        print(f"[{sec}]")
        news[sec] = collect(sec)
        print(f"  → {len(news[sec])}개\n")

    # 3. HTML 빌드 + 발송
    print("HTML 빌드 중...")
    html = build_html(news, mkt)

    subject = f"📰 Daily News Briefing — {DATE_KR}"
    print(f"\n발송: {subject}")
    send_email(subject, html)
