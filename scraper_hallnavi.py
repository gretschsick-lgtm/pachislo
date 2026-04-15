import re, time, requests
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ja,en;q=0.9",
}

HALLNAVI_KEN = {
    "13": "13",  # 東京
    "14": "14",  # 神奈川
    "11": "11",  # 埼玉
}

HALL_KEYWORDS = [
    "マルハン","ピーアーク","楽園","ガーデン","ジアス","エスパス","キコーナ",
    "アビバ","UNO","みとや","アイランド","PIA","SAP","ゴードン","プレサス",
    "メガフェイス","やすだ","BIGディッパー","ラカータ","パラッツォ","123",
    "ニラク","アミューズ","ダイナム","ベルシティ","Dステ","第一プラザ",
    "エクスアリーナ","ライブガーデン","メガガイア","スーパーD","フジヤマ",
    "ゴールド","ベガス","グランパ","ウエスタン","メッセ","オーパ","レッドロック",
    "スパークル","キング","プライム","アサヒ","ジャラン","出玉王","大王",
    "オリエント","グランド","三ノ輪","新橋","上尾","北越谷","みずほ台",
]

def _get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"[hallnavi] fetch error: {e}")
        return None

def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def _make_event(hall_name, event_name, event_date, url, raw_text=""):
    return {
        "event_name":  event_name or hall_name,
        "hall_name":   hall_name,
        "event_date":  event_date,
        "area":        "",
        "url":         url,
        "source":      "hallnavi",
        "raw_text":    raw_text or f"{hall_name} {event_name}",
        "img_url":     "",
        "is_raiten":   False,
        "talent_name": "",
    }

def scrape_hallnavi(prefecture_code="13") -> list[dict]:
    ken = HALLNAVI_KEN.get(prefecture_code, prefecture_code)
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    results = []

    # ① おすすめ分析ページ
    url1 = f"https://hall-navi.com/osusume_list?ken={ken}"
    soup1 = _get(url1)
    if soup1:
        for tag in soup1.find_all(["h2","h3","h4","a","td","li","div","span"]):
            text = _clean(tag.get_text())
            if len(text) < 3 or len(text) > 50:
                continue
            if any(k in text for k in HALL_KEYWORDS):
                results.append(_make_event(
                    hall_name=text,
                    event_name=text,
                    event_date=tomorrow,
                    url=url1,
                ))
        print(f"[hallnavi] おすすめ: {len(results)} 件")

    time.sleep(1)

    # ② 取材スケジュール（関東）
    url2 = f"https://hall-navi.com/serch_sche_2?area=kanto&ken={ken}"
    soup2 = _get(url2)
    before = len(results)
    if soup2:
        for row in soup2.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            date_text  = _clean(cells[0].get_text()) if cells else ""
            hall_text  = _clean(cells[1].get_text()) if len(cells) > 1 else ""
            event_text = _clean(cells[2].get_text()) if len(cells) > 2 else ""

            if not hall_text or not any(k in hall_text for k in HALL_KEYWORDS):
                continue

            ev_date = tomorrow
            m = re.search(r"(\d{1,2})[/月](\d{1,2})", date_text)
            if m:
                try:
                    ev_date = datetime.now().replace(
                        month=int(m.group(1)),
                        day=int(m.group(2))
                    ).strftime("%Y-%m-%d")
                except Exception:
                    pass

            results.append(_make_event(
                hall_name=hall_text,
                event_name=event_text,
                event_date=ev_date,
                url=url2,
                raw_text=f"{date_text} {hall_text} {event_text}",
            ))
        print(f"[hallnavi] スケジュール: {len(results)-before} 件")

    # 重複除去
    seen, unique = set(), []
    for ev in results:
        key = (ev["hall_name"], ev["event_date"])
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    print(f"[hallnavi] 合計（重複除去後）: {len(unique)} 件")
    return unique
