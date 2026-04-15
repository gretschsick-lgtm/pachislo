import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path("data/events.db")

HALL_KEYWORDS = [
    "マルハン","ピーアーク","楽園","ガーデン","ジアス","エスパス","キコーナ",
    "グランキコーナ","アビバ","UNO","みとや","アイランド","PIA","SAP",
    "ゴードン","プレサス","メガフェイス","やすだ","BIGディッパー","ビッグディッパー",
    "ラカータ","パラッツォ","123","ニラク","アミューズ","ダイナム","ベルシティ",
    "Dステ","Dステーション","スーパーDステ","第一プラザ","エクスアリーナ",
    "エクス・アリーナ","ライブガーデン","メガガイア","ガイアネクスト","ガイア",
    "アイオン","スーパーライブガーデン","メガガーデン","スマートガーデン",
    "フジヤマ","ベガスベガス","グランパ","ウエスタン","メッセ",
    "オーパ","レッドロック","スパークル","キングNo.1","キング世田谷","キング会館",
    "オーシャン","阿佐ヶ谷オーシャン","大山オーシャン","練馬オーシャン",
    "トワーズ","アサヒ","ジャラン","出玉王","大王","ユーコーラッキー",
    "タイガー","吉兆","ヒロキ","セブンS","フルハウス","ドラゴン","ARROW",
    "ハリウッド","コトブキ","アラジン","エランドール","サンパレス","有楽町DUO",
    "グランドホール","キューデン","パンドラ","ビッグパンドラ","せんげん台DUO",
    "オータ","一番舘","アスカ","マルホン","サンラッキー","シーサイド","ノア",
    "タイガー7","スクランブル","プライム","パールショップともえ",
    "上尾UNO","北越谷UNO","みずほ台UNO","上福岡UNO","北上尾UNO","朝霞UNO",
    "新橋UNO","三ノ輪UNO","みとやJP","EXA","FACE","SHIRON","SHIROYAMA",
]

def _is_hall_name(name):
    if not name or len(name) < 2:
        return False
    return any(k in name for k in HALL_KEYWORDS)

def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_tables(conn)
    return conn

def _init_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scraped_on TEXT NOT NULL,
        event_date TEXT,
        event_name TEXT,
        hall_name TEXT,
        area TEXT,
        url TEXT,
        source TEXT DEFAULT 'x-api',
        prefecture TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS raiten (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scraped_on TEXT NOT NULL,
        visit_date TEXT,
        talent_name TEXT,
        hall_name TEXT,
        img_url TEXT,
        detail_url TEXT,
        source TEXT,
        raw_text TEXT,
        prefecture TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        posted_on TEXT NOT NULL,
        type TEXT,
        tweet_id TEXT,
        url TEXT,
        tweet_text TEXT,
        has_image INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
    CREATE INDEX IF NOT EXISTS idx_events_name ON events(event_name);
    CREATE INDEX IF NOT EXISTS idx_raiten_date ON raiten(visit_date);
    CREATE INDEX IF NOT EXISTS idx_events_pref ON events(prefecture);
    """)
    conn.commit()

def save_events(events, prefecture=""):
    today = date.today().isoformat()
    conn = get_conn()
    conn.executemany(
        "INSERT INTO events (scraped_on,event_date,event_name,hall_name,area,url,source,prefecture) VALUES (:scraped_on,:event_date,:event_name,:hall_name,:area,:url,:source,:prefecture)",
        [{"scraped_on":today,"event_date":e.get("event_date",""),"event_name":e.get("event_name",""),"hall_name":e.get("hall_name",""),"area":e.get("area",""),"url":e.get("url",""),"source":e.get("source","x-api"),"prefecture":prefecture} for e in events],
    )
    conn.commit(); conn.close()
    print(f"[store] イベント {len(events)} 件保存（{prefecture}）")

def save_raiten(events, prefecture=""):
    today = date.today().isoformat()
    conn = get_conn()
    conn.executemany(
        "INSERT INTO raiten (scraped_on,visit_date,talent_name,hall_name,img_url,detail_url,source,raw_text,prefecture) VALUES (:scraped_on,:visit_date,:talent_name,:hall_name,:img_url,:detail_url,:source,:raw_text,:prefecture)",
        [{"scraped_on":today,"visit_date":e.get("visit_date",""),"talent_name":e.get("talent_name",""),"hall_name":e.get("hall_name",""),"img_url":e.get("img_url",""),"detail_url":e.get("detail_url",""),"source":e.get("source",""),"raw_text":e.get("raw_text",""),"prefecture":prefecture} for e in events],
    )
    conn.commit(); conn.close()
    print(f"[store] 来店 {len(events)} 件保存（{prefecture}）")

def save_post(post):
    today = date.today().isoformat()
    conn = get_conn()
    conn.execute("INSERT INTO posts (posted_on,type,tweet_id,url,tweet_text,has_image) VALUES (?,?,?,?,?,?)",
        (today,post.get("type"),post.get("tweet_id"),post.get("url"),post.get("tweet_text"),int(bool(post.get("has_image")))))
    conn.commit(); conn.close()

def get_hot_events(today, lookback_days=90, prefecture=""):
    conn = get_conn()
    dt = datetime.strptime(today, "%Y-%m-%d")
    weekday = dt.weekday()
    tomorrow = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

    pref_filter = "AND prefecture = :pref" if prefecture else ""
    params_base = {"today": today, "lb": f"-{lookback_days} days", "pref": prefecture}

    all_halls = conn.execute(f"""
        SELECT hall_name, area, COUNT(*) as total_cnt,
               SUM(CASE WHEN event_date >= date(:today, '-30 days') THEN 1 ELSE 0 END) as recent_cnt,
               MAX(url) as url
        FROM events
        WHERE event_date >= date(:today, :lb)
          AND hall_name != '' AND hall_name != '不明'
          {pref_filter}
        GROUP BY hall_name
        ORDER BY recent_cnt DESC, total_cnt DESC
        LIMIT 50
    """, params_base).fetchall()

    hot_halls = [dict(r) for r in all_halls if _is_hall_name(r["hall_name"])][:3]

    tomorrow_events = conn.execute(f"""
        SELECT DISTINCT event_name, hall_name, event_date, area, url
        FROM events
        WHERE event_date = :tomorrow
          AND event_name != '' AND event_name != '不明'
          {pref_filter}
        ORDER BY hall_name
        LIMIT 5
    """, {**params_base, "tomorrow": tomorrow}).fetchall()

    today_events = conn.execute(f"""
        SELECT DISTINCT event_name, hall_name, event_date, area, url
        FROM events
        WHERE event_date = :today
          AND event_name != '' AND event_name != '不明'
          {pref_filter}
        ORDER BY hall_name
        LIMIT 5
    """, params_base).fetchall()

    weekday_hot = conn.execute(f"""
        SELECT event_name, hall_name, COUNT(*) as cnt
        FROM events
        WHERE event_date >= date(:today, :lb)
          AND event_date != ''
          AND event_name != '' AND event_name != '不明'
          AND CAST(strftime('%w', event_date) AS INTEGER) = :wd
          {pref_filter}
        GROUP BY event_name
        ORDER BY cnt DESC
        LIMIT 5
    """, {**params_base, "wd": (weekday+1)%7}).fetchall()

    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    days = conn.execute("SELECT COUNT(DISTINCT scraped_on) FROM events").fetchone()[0]
    conn.close()

    weekday_names = ["月","火","水","木","金","土","日"]
    return {
        "today": today,
        "tomorrow": tomorrow,
        "weekday": weekday_names[weekday],
        "prefecture": prefecture,
        "hot_halls": hot_halls,
        "tomorrow_events": [dict(r) for r in tomorrow_events],
        "today_events": [dict(r) for r in today_events],
        "weekday_hot": [dict(r) for r in weekday_hot],
        "data_stats": {"total_events": total, "days_accumulated": days},
    }

def get_today_raiten(today, prefecture=""):
    conn = get_conn()
    pref_filter = "AND prefecture = ?" if prefecture else ""
    params = [today, prefecture] if prefecture else [today]
    rows = conn.execute(
        f"SELECT * FROM raiten WHERE visit_date = ? {pref_filter} ORDER BY created_at DESC",
        params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_today_matome(today, prefecture=""):
    conn = get_conn()
    pref_filter = "AND prefecture = :pref" if prefecture else ""
    params = {"today": today, "pref": prefecture}

    all_halls = conn.execute(f"""
        SELECT hall_name, GROUP_CONCAT(event_name, '、') as events,
               COUNT(*) as cnt, MAX(url) as url
        FROM events
        WHERE scraped_on = :today
          AND hall_name != '' AND hall_name != '不明'
          {pref_filter}
        GROUP BY hall_name
        ORDER BY cnt DESC
        LIMIT 20
    """, params).fetchall()

    result = [dict(r) for r in all_halls if _is_hall_name(r["hall_name"])][:3]
    conn.close()
    return result
