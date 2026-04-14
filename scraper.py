import os, re, time, requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ja-JP,ja;q=0.9",
}

# ════════════════════════════════════════════
# スクレイピング対象Xアカウント
# ════════════════════════════════════════════
HALL_X_ACCOUNTS = [
    # イベント・来店まとめ系
    "chanoma_777",       # 来店・取材情報毎日まとめ
    "kata_sainokuni",    # 埼玉・東京の狙い目
    "karasuro_7",        # 神奈川の明日のアツい店
    "1_take6",           # 神奈川ホール調査・予想
    "touslot",           # 東京・神奈川・埼玉まとめ
    "slot_channel_",     # 関東全域情報まとめ
    "kachigumimax",      # 全国ホール分析×来店×取材
    "ainavipachislot",   # AIナビ関東版
    "999999Q9Q",         # 東京マルハン情報
    # ホール公式・店員
    "endo1maruhan",      # マルハン新宿東宝ビル店員
    "maruhan_yokoham",   # マルハンメガシティ横浜町田
    "dynamjp",           # ダイナム公式
    "pachislotenchou",   # マルハン店長系
]

def _parse_date(text):
    now = datetime.now()
    for fmt, pat in [
        ("%Y年%m月%d日", r"\d{4}年\d{1,2}月\d{1,2}日"),
        ("%m月%d日",     r"\d{1,2}月\d{1,2}日"),
        ("%Y/%m/%d",    r"\d{4}/\d{1,2}/\d{1,2}"),
        ("%m/%d",       r"\d{1,2}/\d{1,2}"),
    ]:
        m = re.search(pat, text)
        if m:
            try:
                dt = datetime.strptime(m.group(), fmt)
                if dt.year == 1900: dt = dt.replace(year=now.year)
                return dt.strftime("%Y-%m-%d")
            except ValueError: pass
    return ""

def _is_event_tweet(text):
    keywords = ["イベント","来店","全台","旧イベ","設定","特日","ガチ日","周年","記念","サービス","アツ","熱","取材","狙い","推し","快便","明日"]
    return any(k in text for k in keywords)

def _is_raiten_tweet(text):
    keywords = ["来店","来場","ゲスト","タレント","プロ","選手","取材"]
    return any(k in text for k in keywords)

def _extract_event_name(text):
    for pat in [r"【([^】]{2,20})】", r"「([^」]{2,20})」",
                r"(全台[^\s　。！]{0,10})", r"(旧イベ[^\s　。！]{0,10})",
                r"(周年[^\s　。！]{0,10})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return text[:20].strip()

def _extract_talent_name(text):
    for pat in [r"([^\s　、。！]+(?:選手|さん|プロ|氏|女王))(?:が|の)?(?:来店|来場)",
                r"(?:来店|来場)[：:]\s*([^\s　\n！。、]{2,15})",
                r"【来店】([^\s　\n！。【】]{2,15})",
                r"ゲスト[：:]\s*([^\s　\n！。、]{2,15})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return "(来店者不明)"

def _extract_hall_name(text):
    """ツイートからホール名を抽出"""
    patterns = [
        r"(マルハン[^\s　。！\n]{1,15})",
        r"(ピーアーク[^\s　。！\n]{1,15})",
        r"(ガーデン[^\s　。！\n]{1,10})",
        r"(キコーナ[^\s　。！\n]{1,10})",
        r"(楽園[^\s　。！\n]{1,10})",
        r"(ダイナム[^\s　。！\n]{1,10})",
        r"(エスパス[^\s　。！\n]{1,10})",
        r"(アビバ[^\s　。！\n]{1,10})",
        r"(ジアス[^\s　。！\n]{1,10})",
        r"(UNO[^\s　。！\n]{1,10})",
        r"(123[^\s　。！\n]{1,10})",
        r"(メッセ[^\s　。！\n]{1,10})",
    ]
    halls = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            halls.append(m.group(1).strip())
    return halls[0] if halls else ""

def scrape_x_account(username: str) -> list[dict]:
    """NitterミラーでXアカウントのツイートを取得"""
    results = []
    # 複数のNitterインスタンスを試す
    nitter_hosts = [
        "nitter.poast.org",
        "nitter.privacydev.net",
        "nitter.1d4.us",
    ]
    soup = None
    for host in nitter_hosts:
        url = f"https://{host}/{username}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                break
        except Exception:
            continue

    if not soup:
        print(f"[scraper] {username} 全Nitter失敗")
        return []

    tweets = soup.select(".timeline-item")
    for tweet in tweets[:30]:
        text_el = tweet.select_one(".tweet-content")
        if not text_el: continue
        text = text_el.get_text(" ", strip=True)
        if not _is_event_tweet(text): continue

        date_el = tweet.select_one(".tweet-date a")
        date_str = date_el.get("title","") if date_el else ""
        event_date = _parse_date(date_str) or _parse_date(text) or date.today().isoformat()

        img_el = tweet.select_one(".attachments img")
        img_url = img_el.get("src","") if img_el else ""
        if img_url.startswith("/"): img_url = f"https://{nitter_hosts[0]}" + img_url

        link_el = tweet.select_one(".tweet-date a")
        tweet_url = f"https://x.com/{username}/status/" + (link_el["href"].split("/")[-1] if link_el else "")

        hall_name = _extract_hall_name(text) or username

        results.append({
            "event_name": _extract_event_name(text),
            "hall_name": hall_name,
            "event_date": event_date,
            "area": "",
            "url": tweet_url,
            "source": "x-scrape",
            "raw_text": text[:200],
            "img_url": img_url,
            "is_raiten": _is_raiten_tweet(text),
            "talent_name": _extract_talent_name(text) if _is_raiten_tweet(text) else "",
        })

    print(f"[scraper] {username}: {len(results)} 件")
    time.sleep(1.5)
    return results

def scrape_events(prefecture_code="13", max_pages=5) -> list[dict]:
    results = []
    for account in HALL_X_ACCOUNTS:
        items = scrape_x_account(account)
        for item in items:
            if not item.get("is_raiten"):
                results.append(item)
    # 重複除去
    seen, unique = set(), []
    for ev in results:
        key = (ev.get("hall_name",""), ev.get("event_date",""))
        if key not in seen:
            seen.add(key)
            unique.append(ev)
    print(f"[scraper] イベント合計: {len(unique)} 件")
    return unique

def scrape_all_raiten(prefecture_code="13", prefecture_hint="東京") -> list[dict]:
    results = []
    for account in HALL_X_ACCOUNTS:
        items = scrape_x_account(account)
        for item in items:
            if item.get("is_raiten"):
                results.append({
                    "talent_name": item.get("talent_name","(来店者不明)"),
                    "hall_name": item.get("hall_name",""),
                    "visit_date": item.get("event_date",""),
                    "img_url": item.get("img_url",""),
                    "detail_url": item.get("url",""),
                    "raw_text": item.get("raw_text",""),
                    "source": "x-scrape",
                })
    seen, unique = set(), []
    for ev in results:
        key = (ev.get("hall_name",""), ev.get("talent_name",""))
        if key not in seen:
            seen.add(key)
            unique.append(ev)
    print(f"[scraper] 来店合計: {len(unique)} 件")
    return unique
