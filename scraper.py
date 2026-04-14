import os, re, time, tweepy
from datetime import datetime, date, timedelta

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

def _is_event(text):
    return any(k in text for k in ["イベント","来店","全台","旧イベ","設定","特日","ガチ日","周年","記念","アツ","熱","取材","狙い","推し","快便","明日の"])

def _is_raiten(text):
    return any(k in text for k in ["来店","来場","ゲスト","タレント","プロ","選手","取材"])

def _extract_event_name(text):
    for pat in [r"【([^】]{2,20})】", r"「([^」]{2,20})」",
                r"(全台[^\s　。！]{0,10})", r"(旧イベ[^\s　。！]{0,10})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return text[:20].strip()

def _extract_talent(text):
    for pat in [r"([^\s　、。！]+(?:選手|さん|プロ|氏))(?:が|の)?(?:来店|来場)",
                r"(?:来店|来場)[：:]\s*([^\s　\n！。、]{2,15})",
                r"【来店】([^\s　\n！。【】]{2,15})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return "(来店者不明)"

def _extract_hall(text):
    for pat in [r"(マルハン[^\s　。！\n]{1,15})", r"(ピーアーク[^\s　。！\n]{1,15})",
                r"(ガーデン[^\s　。！\n]{1,10})", r"(キコーナ[^\s　。！\n]{1,10})",
                r"(楽園[^\s　。！\n]{1,10})", r"(ダイナム[^\s　。！\n]{1,10})",
                r"(エスパス[^\s　。！\n]{1,10})", r"(アビバ[^\s　。！\n]{1,10})",
                r"(ジアス[^\s　。！\n]{1,10})", r"(UNO[^\s　。！\n]{1,10})",
                r"(123[^\s　。！\n]{1,10})", r"(メッセ[^\s　。！\n]{1,10})",
                r"(ピーアーク[^\s　。！\n]{1,10})", r"(楽園[^\s　。！\n]{1,10})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return ""

# スクレイピング対象アカウント
TARGET_ACCOUNTS = [
    "chanoma_777", "kata_sainokuni", "karasuro_7", "1_take6",
    "touslot", "slot_channel_", "kachigumimax", "ainavipachislot",
    "999999Q9Q", "endo1maruhan", "maruhan_yokoham", "dynamjp", "pachislotenchou",
]

def _get_client():
    return tweepy.Client(
        bearer_token=os.environ.get("X_BEARER_TOKEN",""),
        wait_on_rate_limit=True
    )

def _fetch_user_tweets(client, username: str) -> list[dict]:
    results = []
    try:
        user = client.get_user(username=username, user_fields=["id"])
        if not user.data: return []
        uid = user.data.id

        resp = client.get_users_tweets(
            id=uid,
            max_results=20,
            tweet_fields=["created_at","text","attachments"],
            expansions=["attachments.media_keys"],
            media_fields=["url","type"],
            exclude=["retweets","replies"],
        )
        if not resp.data: return []

        media_map = {m.media_key: m for m in (resp.includes or {}).get("media", [])}

        for tweet in resp.data:
            text = tweet.text
            if not _is_event(text): continue

            event_date = _parse_date(text)
            if not event_date:
                event_date = tweet.created_at.strftime("%Y-%m-%d") if tweet.created_at else date.today().isoformat()

            img_url = ""
            if tweet.attachments and tweet.attachments.get("media_keys"):
                for mk in tweet.attachments["media_keys"]:
                    media = media_map.get(mk)
                    if media and media.type == "photo":
                        img_url = media.url or ""
                        break

            results.append({
                "event_name": _extract_event_name(text),
                "hall_name": _extract_hall(text) or username,
                "event_date": event_date,
                "area": "",
                "url": f"https://x.com/{username}/status/{tweet.id}",
                "source": "x-api",
                "raw_text": text[:200],
                "img_url": img_url,
                "is_raiten": _is_raiten(text),
                "talent_name": _extract_talent(text) if _is_raiten(text) else "",
            })
        print(f"[scraper] {username}: {len(results)} 件")
        time.sleep(1)
    except tweepy.TweepyException as e:
        print(f"[scraper] {username} エラー: {e}")
    return results

def scrape_events(prefecture_code="13", max_pages=5) -> list[dict]:
    client = _get_client()
    results = []
    for account in TARGET_ACCOUNTS:
        for item in _fetch_user_tweets(client, account):
            if not item.get("is_raiten"):
                results.append(item)
    seen, unique = set(), []
    for ev in results:
        key = (ev.get("hall_name",""), ev.get("event_date",""))
        if key not in seen: seen.add(key); unique.append(ev)
    print(f"[scraper] イベント合計: {len(unique)} 件")
    return unique

def scrape_all_raiten(prefecture_code="13", prefecture_hint="東京") -> list[dict]:
    client = _get_client()
    results = []
    for account in TARGET_ACCOUNTS:
        for item in _fetch_user_tweets(client, account):
            if item.get("is_raiten"):
                results.append({
                    "talent_name": item.get("talent_name","(来店者不明)"),
                    "hall_name": item.get("hall_name",""),
                    "visit_date": item.get("event_date",""),
                    "img_url": item.get("img_url",""),
                    "detail_url": item.get("url",""),
                    "raw_text": item.get("raw_text",""),
                    "source": "x-api",
                })
    seen, unique = set(), []
    for ev in results:
        key = (ev.get("hall_name",""), ev.get("talent_name",""))
        if key not in seen: seen.add(key); unique.append(ev)
    print(f"[scraper] 来店合計: {len(unique)} 件")
    return unique
