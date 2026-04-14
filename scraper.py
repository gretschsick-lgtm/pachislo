import os, re, time, requests, tweepy
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "ja-JP,ja;q=0.9"}

def _parse_date(text):
    now = datetime.now()
    for fmt, pat in [("%Y年%m月%d日",r"\d{4}年\d{1,2}月\d{1,2}日"),("%m月%d日",r"\d{1,2}月\d{1,2}日"),("%Y/%m/%d",r"\d{4}/\d{1,2}/\d{1,2}"),("%m/%d",r"\d{1,2}/\d{1,2}")]:
        m = re.search(pat, text)
        if m:
            try:
                dt = datetime.strptime(m.group(), fmt)
                if dt.year == 1900: dt = dt.replace(year=now.year)
                return dt.strftime("%Y-%m-%d")
            except ValueError: pass
    return ""

def scrape_events(prefecture_code="13", max_pages=5):
    results = []
    for page in range(1, max_pages+1):
        url = f"https://www.hall-navi.jp/event/list/?pref={prefecture_code}&page={page}"
        print(f"[scraper] イベント取得: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".eventList__item, .event-card, .p-event-list__item") or soup.find_all(["li","article"], class_=re.compile(r"event", re.I))
            for card in cards:
                item = _parse_event_card(card)
                if item: results.append(item)
            time.sleep(1.2)
        except Exception as e:
            print(f"[scraper] エラー: {e}"); break
    print(f"[scraper] イベント {len(results)} 件")
    return results

def _parse_event_card(card):
    try:
        def txt(sel):
            el = card.select_one(sel)
            return el.get_text(strip=True) if el else ""
        hall_name = txt(".hallName, .hall-name") or ""
        event_name = txt(".eventName, .event-name") or (card.find(["h2","h3","h4"]) or type('',(),{'get_text':lambda s,**k:''})()).get_text("")
        date_el = card.select_one(".eventDate, .event-date") or card.find(class_=re.compile(r"date", re.I))
        event_date = _parse_date(date_el.get_text() if date_el else "")
        area_el = card.select_one(".area, .prefecture")
        area = area_el.get_text(strip=True) if area_el else ""
        link = card.find("a", href=True)
        url = ("https://www.hall-navi.jp" + link["href"]) if link else ""
        if not event_name and not hall_name: return None
        return dict(event_name=event_name, hall_name=hall_name, event_date=event_date, area=area, url=url, source="hall-navi")
    except Exception: return None

def scrape_raiten_hall_navi(prefecture_code="13", max_pages=3):
    results = []
    for page in range(1, max_pages+1):
        url = f"https://www.hall-navi.jp/raiten/?pref={prefecture_code}&page={page}"
        print(f"[scraper] 来店取得: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".raitenList__item, .raiten-card, .p-raiten-list__item") or soup.find_all(["li","article"], class_=re.compile(r"raiten|visit", re.I))
            for card in cards:
                item = _parse_raiten_card(card)
                if item:
                    item["source"] = "hall-navi"
                    results.append(item)
            time.sleep(1.2)
        except Exception as e:
            print(f"[scraper] 来店エラー: {e}"); break
    print(f"[scraper] ホールナビ来店 {len(results)} 件")
    return results

def _parse_raiten_card(card):
    try:
        talent_el = card.select_one(".talentName,.talent-name,.visitorName") or card.find(class_=re.compile(r"talent|visitor", re.I)) or card.find(["h2","h3","h4","strong"])
        hall_el = card.select_one(".hallName,.hall-name") or card.find(class_=re.compile(r"hall", re.I))
        date_el = card.select_one(".raitenDate,.visitDate") or card.find(class_=re.compile(r"date", re.I))
        img_el = card.find("img")
        link_el = card.find("a", href=True)
        talent_name = talent_el.get_text(strip=True) if talent_el else ""
        hall_name = hall_el.get_text(strip=True) if hall_el else ""
        visit_date = _parse_date(date_el.get_text() if date_el else "")
        img_url = (img_el.get("src") or img_el.get("data-src","")) if img_el else ""
        if img_url.startswith("/"): img_url = "https://www.hall-navi.jp" + img_url
        detail_url = ("https://www.hall-navi.jp" + link_el["href"]) if link_el else ""
        if not talent_name and not hall_name: return None
        return dict(talent_name=talent_name, hall_name=hall_name, visit_date=visit_date, img_url=img_url, detail_url=detail_url, raw_text=card.get_text(" ",strip=True)[:200])
    except Exception: return None

def scrape_raiten_x(prefecture_hint="東京"):
    bearer = os.environ.get("X_BEARER_TOKEN","")
    if not bearer:
        print("[scraper] X_BEARER_TOKEN なし → X検索スキップ")
        return []
    client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)
    start = datetime.now() - timedelta(days=3)
    results = []
    for keyword in ["来店 パチンコ","来店 スロット","来店イベント ホール"]:
        query = f"{keyword} {prefecture_hint} -is:retweet lang:ja"
        try:
            resp = client.search_recent_tweets(query=query, max_results=10, start_time=start, tweet_fields=["created_at","text","author_id","attachments"], expansions=["attachments.media_keys","author_id"], media_fields=["url","type"], user_fields=["name"])
            if not resp.data: continue
            media_map = {m.media_key: m for m in (resp.includes or {}).get("media",[])}
            user_map = {u.id: u for u in (resp.includes or {}).get("users",[])}
            for tweet in resp.data:
                if any(ex in tweet.text for ex in ["RT @","来店しました","行ってきた"]): continue
                item = _parse_raiten_tweet(tweet, media_map, user_map)
                if item: results.append(item)
            time.sleep(1)
        except tweepy.TweepyException as e:
            print(f"[scraper] X API エラー: {e}"); break
    print(f"[scraper] X来店 {len(results)} 件")
    return results

def _parse_raiten_tweet(tweet, media_map, user_map):
    text = tweet.text
    talent_name = ""
    for pat in [r"([^\s　、。！]+(?:選手|さん|プロ|氏)?)(?:が|の)?来店",r"来店[：:]\s*([^\s　\n！。、]{2,15})",r"【来店】([^\s　\n！。【】]{2,15})"]:
        m = re.search(pat, text)
        if m: talent_name = m.group(1).strip(); break
    hall_name = ""
    for pat in [r"([^\s　\n]{2,15}(?:パチンコ|スロット|ホール|店))(?:に|で)?来店",r"【([^\】]{2,15}(?:パチンコ|スロット|ホール|店))】"]:
        m = re.search(pat, text)
        if m: hall_name = m.group(1).strip(); break
    visit_date = _parse_date(text)
    if not visit_date and tweet.created_at: visit_date = tweet.created_at.strftime("%Y-%m-%d")
    img_url = ""
    if tweet.attachments and tweet.attachments.get("media_keys"):
        for mk in tweet.attachments["media_keys"]:
            media = media_map.get(mk)
            if media and media.type == "photo": img_url = media.url or ""; break
    author = user_map.get(tweet.author_id)
    return dict(talent_name=talent_name or "(来店者不明)", hall_name=hall_name or (author.name if author else ""), visit_date=visit_date, img_url=img_url, detail_url=f"https://x.com/i/web/status/{tweet.id}", raw_text=text[:200], source="x-search")

def scrape_all_raiten(prefecture_code="13", prefecture_hint="東京"):
    hall_navi = scrape_raiten_hall_navi(prefecture_code)
    x_results = scrape_raiten_x(prefecture_hint)
    all_events = hall_navi + x_results
    seen, unique = set(), []
    for ev in all_events:
        key = (ev.get("hall_name","").replace(" ",""), ev.get("talent_name","").replace(" ",""))
        if key not in seen and key != ("",""): seen.add(key); unique.append(ev)
    print(f"[scraper] 来店合計（重複除去後）{len(unique)} 件")
    return unique
