#!/usr/bin/env python3
"""
Daily News Briefing — Resend Email Sender
Run: python3 send_briefing.py
Or schedule with cron: 0 7 * * * /usr/bin/python3 /path/to/send_briefing.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime

RESEND_API_KEY = "re_FpfZnb39_DQ45GyUTAkKnY2FTW8dCKZwX"
FROM_EMAIL = "onboarding@resend.dev"   # Replace with your verified domain email
TO_EMAILS = ["cmkim0316@gmail.com", "sergeykwon@gmail.com"]

def search_web(query: str) -> str:
    """Placeholder: In production, integrate a news API (NewsAPI, GDELT, etc.)"""
    return ""

def build_html(date_str: str, news_data: dict) -> str:
    kr_general = news_data.get("kr_general", [])
    kr_stock   = news_data.get("kr_stock", [])
    kr_legal   = news_data.get("kr_legal", [])
    en_politics = news_data.get("en_politics", [])
    en_economy  = news_data.get("en_economy", [])
    en_legal    = news_data.get("en_legal", [])
    en_bar      = news_data.get("en_bar", [])

    def items_html(items):
        html = ""
        for item in items:
            html += f"""
      <div class="news-item">
        <div class="news-headline">{item['headline']}</div>
        <div class="news-summary">{item['summary']}</div>
        <a href="{item['url']}" class="read-full">Read Full &rarr;</a>
      </div>"""
        return html

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f4f6f9; margin:0; padding:0; }}
  .wrapper {{ max-width:700px; margin:30px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,.08); }}
  .header {{ background:linear-gradient(135deg,#1a237e,#283593); padding:32px 36px; }}
  .header h1 {{ color:#fff; margin:0; font-size:22px; font-weight:700; }}
  .header p {{ color:#90caf9; margin:6px 0 0; font-size:13px; }}
  .lang-badge {{ display:inline-block; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:700; margin-bottom:18px; }}
  .badge-kr {{ background:#e8f5e9; color:#2e7d32; }}
  .badge-en {{ background:#e3f2fd; color:#1565c0; }}
  .section {{ padding:28px 36px; border-bottom:1px solid #f0f0f0; }}
  .section-title {{ font-size:15px; font-weight:700; color:#1a237e; margin:0 0 16px; padding-left:12px; border-left:4px solid #1a237e; }}
  .news-item {{ background:#f8f9fc; border-radius:8px; padding:14px 16px; margin-bottom:10px; }}
  .news-headline {{ font-size:13.5px; font-weight:700; color:#1a1a2e; margin:0 0 6px; }}
  .news-summary {{ font-size:12.5px; color:#555; line-height:1.6; margin:0 0 8px; }}
  .read-full {{ display:inline-block; font-size:11.5px; color:#1565c0; text-decoration:none; font-weight:600; background:#e3f2fd; padding:3px 10px; border-radius:12px; }}
  .divider {{ height:6px; background:linear-gradient(90deg,#1a237e,#42a5f5); }}
  .footer {{ background:#f8f9fc; padding:20px 36px; text-align:center; color:#999; font-size:11px; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>&#128240; Daily News Briefing</h1>
    <p>{date_str} &nbsp;|&nbsp; &#127472;&#127479; 한국어 + &#127482;&#127480; English</p>
  </div>
  <div class="divider"></div>

  <div class="section">
    <span class="lang-badge badge-kr">&#127472;&#127479; 한국어</span>
    <div class="section-title">1/ 오늘의 주요 국내외 뉴스</div>
    {items_html(kr_general)}
  </div>

  <div class="section">
    <div class="section-title">2/ 국내외 주식 시장 뉴스</div>
    {items_html(kr_stock)}
  </div>

  <div class="section">
    <div class="section-title">3/ 국내외 법률 관련 최신 뉴스</div>
    {items_html(kr_legal)}
  </div>

  <div class="divider"></div>

  <div class="section">
    <span class="lang-badge badge-en">&#127482;&#127480; English</span>
    <div class="section-title">1/ U.S. Politics</div>
    {items_html(en_politics)}
  </div>

  <div class="section">
    <div class="section-title">2/ U.S. Economy &amp; Stock Market</div>
    {items_html(en_economy)}
  </div>

  <div class="section">
    <div class="section-title">3/ U.S. Legal News</div>
    {items_html(en_legal)}
  </div>

  <div class="section">
    <div class="section-title">4/ BAR Exam &#8212; Helpful Articles</div>
    {items_html(en_bar)}
  </div>

  <div class="footer">
    Daily News Briefing &nbsp;|&nbsp; {date_str}<br>
    Sent to {", ".join(TO_EMAILS)}
  </div>
</div>
</body>
</html>"""


def send_email(subject: str, html: str) -> bool:
    payload = {
        "from": FROM_EMAIL,
        "to": TO_EMAILS,
        "subject": subject,
        "html": html,
    }
    data = json.dumps(payload).encode("utf-8")
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
            print(f"[OK] Email sent! Response: {body}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[ERROR] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


# ─── TODAY'S NEWS DATA ────────────────────────────────────────────────────────
# Update this dict daily (or integrate a news API for full automation)
NEWS_DATA = {
    "kr_general": [
        {
            "headline": "이 대통령, 미·중 고위급 면담",
            "summary": "스콧 베센트 미 재무장관 및 허리펑 중국 국무원 부총리와 경제·통상·국제 정세 논의 예정.",
            "url": "https://www.newspim.com/news/view/20260513000001",
        },
        {
            "headline": "삼성전자 노사 교섭 최종 결렬",
            "summary": "초기업노동조합, 사후조정 최종 결렬 선언. 노사 이견 좁히지 못해 파업 가능성 고조.",
            "url": "https://www.mt.co.kr/politics/2026/05/13/2026051222241787456",
        },
        {
            "headline": "크루즈선 한타바이러스 집단 감염 — 3명 사망",
            "summary": "MV 혼디우스 크루즈선에서 집단 감염 발생. 전 세계 보건 당국 추적 감시 돌입.",
            "url": "https://imnews.imbc.com/replay/2026/nwdesk/article/6814613_37004.html",
        },
        {
            "headline": "이란 핵협상 사실상 좌초",
            "summary": "핵·호르무즈 해협 쟁점으로 미-이란 협상 결렬 위기. 국제유가 상승세.",
            "url": "https://imnews.imbc.com/replay/2026/nwdesk/article/6814613_37004.html",
        },
    ],
    "kr_stock": [
        {
            "headline": "코스피·코스닥 시가총액 6천조 원 사상 첫 돌파",
            "summary": "1년 만에 2.7배 성장. 반도체 강세·외국인·기관 쌍끌이 매수 주도.",
            "url": "https://imnews.imbc.com/replay/2026/nwdesk/article/6818348_37004.html",
        },
        {
            "headline": "코스닥 1,212p 유지 — 외인·기관 동반 매수",
            "summary": "개장가 1,212.88. 코스피 52주 최고치 경신 흐름 지속.",
            "url": "https://kr.investing.com/indices/kosdaq",
        },
        {
            "headline": "외인, 반도체 줄이고 로봇주 매집",
            "summary": "외국인투자자들이 반도체 관련주를 줄이고 로봇 종목을 새로 매집하는 움직임 포착.",
            "url": "https://www.mt.co.kr/politics/2026/05/13/2026051222241787456",
        },
        {
            "headline": "미국 증시 소폭 상승 (5/12) — AI·에너지 주도",
            "summary": "다우 +95pt(49,704) | S&P500 7,412 | 나스닥 26,274. 인플레이션 우려로 금리인하 기대 후퇴.",
            "url": "https://finance.yahoo.com/markets/stocks/articles/stock-market-news-may-12-132000108.html",
        },
    ],
    "kr_legal": [
        {
            "headline": "헌법 개정안 본회의 투표 불성립",
            "summary": "국민의힘 불참으로 재적 2/3 정족수 미달. 6개 야당 발의 개헌안 처리 불발.",
            "url": "https://v.daum.net/v/PhKdApJ6jA",
        },
        {
            "headline": "형사재판기록 열람·등사 수수료 5월부터 전면 면제",
            "summary": "피고인 방어권·피해자 진술권 보장 강화. 이달부터 즉시 시행.",
            "url": "https://www.lawtimes.co.kr/news/articleView.html?idxno=220366",
        },
        {
            "headline": "EU 제약·의료기기 규제 대개편 — 韓 바이오 전략 재조정 불가피",
            "summary": "EU 제약·의료기기 규제 대개편. 한국 바이오 기업 전략 재조정 시급. 호건 러블스 보고서 발표.",
            "url": "https://www.kjob.news/news/488126",
        },
        {
            "headline": "법무법인 율촌, 대통령실 출신 이영상 변호사 파트너 영입",
            "summary": "대통령실 법률비서관 출신 파트너 영입. 공공·정부 자문 역량 강화.",
            "url": "https://law.asia/ko/yulchon-reappoints-yung-sang-lee-partner-korea/",
        },
    ],
    "en_politics": [
        {
            "headline": "Trump-Xi Summit: Trade & Stability in Focus",
            "summary": "Leaders meet as tariff tensions simmer. Both sides seek de-escalation but breakthroughs are unlikely.",
            "url": "https://www.washingtonpost.com/politics/2026/05/12/trump-xi-summit-economy/",
        },
        {
            "headline": "Trump: Iran Ceasefire \"On Life Support\"",
            "summary": "Trump calls Iran's proposal 'garbage'. Strait of Hormuz disruption fears spike oil prices.",
            "url": "https://www.washingtonpost.com/politics/2026/05/10/iran-response-us-proposal-war/",
        },
        {
            "headline": "2026 Midterms: Democrats Eye House Majority",
            "summary": "Trump approval slides. CNN poll: 7-in-10 expect recession. Dems have increasing odds for House.",
            "url": "https://www.cnn.com/2026/05/10/politics/midterm-elections-2026-affordability-analysis",
        },
        {
            "headline": "Kevin Warsh Confirmed as Federal Reserve Chair",
            "summary": "Senate confirms 51-45 for 4-year term. Markets watch his stance on inflation and rate policy.",
            "url": "https://www.dailypress.senate.gov/tuesday-may-12-2026/",
        },
    ],
    "en_economy": [
        {
            "headline": "Markets Inch Up — S&P 500 at 7,412 (May 12)",
            "summary": "Dow +95 pts | S&P +14 pts | Nasdaq +27 pts. AI and energy stocks lead gains.",
            "url": "https://finance.yahoo.com/markets/stocks/articles/stock-market-news-may-12-132000108.html",
        },
        {
            "headline": "April CPI Hits 3.8% — Hotter Than Expected",
            "summary": "Above 3.7% forecast. Core CPI 2.8%. Fed rate-cut timeline pushed further back.",
            "url": "https://finance.yahoo.com/economy/policy/articles/oof-federal-reserves-may-inflation-132600416.html",
        },
        {
            "headline": "Oil Spikes 3% on Iran-Hormuz Fears",
            "summary": "Crude surges as Hormuz disruption fears grow. Energy stocks outperform the broader market.",
            "url": "https://finance.yahoo.com/markets/stocks/articles/us-stock-market-today-p-101018227.html",
        },
        {
            "headline": "Americans Feel \"Stuck\" — Cost of Living #1 Concern",
            "summary": "CNN poll: high prices top financial concerns. ~70% expect a recession within the next year.",
            "url": "https://www.cnn.com/2026/05/12/politics/cost-of-living-us-financial-problem-vis",
        },
    ],
    "en_legal": [
        {
            "headline": "SCOTUS Extends Hold on Abortion Pill Ruling",
            "summary": "Justice Alito extends pause on mifepristone mail/telemedicine ban until May 14. Access continues.",
            "url": "https://www.newstribune.com/news/2026/may/12/us-supreme-court-extends-pause-on-decision/",
        },
        {
            "headline": "Voting Rights Act Ruling Shakes 2026 Midterms",
            "summary": "SCOTUS strikes majority-minority districts in Louisiana v. Callais via Equal Protection Clause.",
            "url": "https://www.scotusblog.com/2026/04/court-decides-major-voting-rights-act-case/",
        },
        {
            "headline": "Court Blocks Trump's 10% Global Tariff — Again",
            "summary": "Court of Int'l Trade invalidates 10% global import tariff after earlier Supreme Court defeat.",
            "url": "https://www.washingtonpost.com/business/2026/05/07/tariffs-trade-court-ruling-trump/",
        },
    ],
    "en_bar": [
        {
            "headline": "NextGen Bar Exam 2026: What You Need to Know",
            "summary": "Several jurisdictions adopt NextGen UBE starting July 2026. Confirm your version before prepping.",
            "url": "https://lawschooltoolbox.com/nextgen-bar-exam-2026-expert-insights-and-preparation-tips-for-law-students/",
        },
        {
            "headline": "BARBRI Ultimate Bar Prep Guide — Key Strategies",
            "summary": "Wide, shallow coverage beats deep-diving. IRAC structure is essential. 400–600 hours total.",
            "url": "https://www.barbri.com/resources/studying-for-the-bar-exam-ultimate-bar-prep-guide",
        },
        {
            "headline": "UWorld 2026 Bar Exam Study Guide",
            "summary": "Full study schedule, subject frequency chart, and exam-day tips. Mix subjects for endurance.",
            "url": "https://legal.uworld.com/bar-exam/study-guide/",
        },
    ],
}

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    now = datetime.now()
    date_str = now.strftime("%Y년 %m월 %d일")
    subject = f"📰 Daily News Briefing — {date_str}"

    print(f"Building email for {date_str}...")
    html = build_html(date_str, NEWS_DATA)

    print(f"Sending to: {', '.join(TO_EMAILS)}")
    send_email(subject, html)
