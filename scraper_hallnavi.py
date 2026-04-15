import os, re, time, requests
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup

PREF_CODE_MAP = {
    "13": "1",   # 東京（ホールナビの都道府県コード）
    "14": "2",   # 神奈川
    "11": "11",  # 埼玉
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PachisloBot/1.0)",
    "Accept-Language": "ja,en;q=0.9",
}

def _fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"[hallnavi] fetch error {url}: {e}")
        return None

def scrape_hallnavi_events(prefecture_code="13") -> list[dict]:
    """ホールナビから明日のおすすめホール情報を取得"""
    ken = PREF_CODE_MAP.get(prefecture_code, "1")
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    results = []

    # おすすめ分析ページ
    url = f"https://hall-navi.com/osusume_list?ken={ken}"
    soup = _fetch(url)
    if not soup:
        return results

    halls = soup.select(".hall_name, .store_name, h3, .name")
    events = soup.select(".event_name, .event, .schedule_name, .tag")

    # ホール名とイベント情報をペアで抽出
    items = soup.select(".osusume_item, .hall_item, .list_item, article, .card")

    if not items:
        # フォールバック：テキストから直接抽出
        text = soup.get_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines:
            if any(k in line for k in ["マルハン","ピーアーク","楽園","ガーデン","ジアス","エスパス","キコーナ","アビバ","UNO","みとや","アイランド"]):
                results.append({
                    "event_name": line[:30],
                    "hall_name": line[:20],
                    "event_date": tomorrow,
                    "area": prefecture_code,
                    "url": url,
                    "source": "hallnavi",
                    "raw_text": line[:200],
                    "img_url": "",
                    "is_raiten": False,
                    "talent_name": "",
                })
    else:
        for item in items[:20]:
            hall = item.select_one(".hall_name, h3, .name, .title")
            hall_name = hall.get_text(strip=True) if hall else ""
            event = item.select_one(".event_name, .event, .schedule, .tag")
            event_name = event.get_text(strip=True) if event else ""
            link = item.select_one("a")
            href = "https://hall-navi.com" + link["href"] if link and link.get("href","").startswith("/") else url

            if hall_name:
                results.append({
                    "event_name": event_name or hall_name,
                    "hall_name": hall_name,
                    "event_date": tomorrow,
                    "area": prefecture_code,
                    "url": href,
                    "source": "hallnavi",
                    "raw_text": f"{hall_name} {event_name}",
                    "img_url": "",
                    "is_raiten": False,
                    "talent_name": "",
                })

    print(f"[hallnavi] 取得: {len(results)} 件（都道府県コード: {prefecture_code}）")
    return results


def scrape_hallnavi_schedule(prefecture_code="13") -> list[dict]:
    """ホールナビから取材・旧イベントスケジュールを取得"""
    ken = PREF_CODE_MAP.get(prefecture_code, "1")
    results = []

    url = f"https://hall-navi.com/serch_sche_2?area=kanto&ken={ken}"
    soup = _fetch(url)
    if not soup:
        return results

    rows = soup.select("tr, .schedule_row, .event_row")
    for row in rows[:30]:
        cells = row.select("td, .cell")
        if len(cells) >= 2:
            date_text = cells[0].get_text(strip=True) if cells else ""
            hall_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            event_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""

            # 日付パース
            event_date = ""
            dm = re.search(r"(\d{1,2})[/月](\d{1,2})", date_text)
            if dm:
                try:
                    event_date = datetime.now().replace(
                        month=int(dm.group(1)), day=int(dm.group(2))
                    ).strftime("%Y-%m-%d")
                except: pass

            if hall_text:
                results.append({
                    "event_name": event_text or hall_text,
                    "hall_name": hall_text,
                    "event_date": event_date or date.today().isoformat(),
                    "area": prefecture_code,
                    "url": url,
                    "source": "hallnavi",
                    "raw_text": f"{date_text} {hall_text} {event_text}",
                    "img_url": "",
                    "is_raiten": False,
                    "talent_name": "",
                })

    print(f"[hallnavi] スケジュール取得: {len(results)} 件")
    return results
