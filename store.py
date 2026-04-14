import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path("data/events.db")

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
        source TEXT DEFAULT 'hall-navi',
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
    """)
    conn.commit()

def save_events(events):
    today = date.today().isoformat()
    conn = get_conn()
    conn.executemany(
        "INSERT INTO events (scraped_on,event_date,event_name,hall_name,area,url,source) VALUES (:scraped_on,:event_date,:event_name,:hall_name,:area,:url,:source)",
        [{"scraped_on":today,"event_date":e.get("event_date",""),"event_name":e.get("event_name",""),"hall_name":e.get("hall_name",""),"area":e.get("area",""),"url":e.get("url",""),"source":e.get("source","hall-navi")} for e in events],
    )
    conn.commit(); conn.close()
    print(f"[store] イベント {len(events)} 件保存")

def save_raiten(events):
    today = date.today().isoformat()
    conn = get_conn()
    conn.executemany(
        "INSERT INTO raiten (scraped_on,visit_date,talent_name,hall_name,img_url,detail_url,source,raw_text) VALUES (:scraped_on,:visit_date,:talent_name,:hall_name,:img_url,:detail_url,:source,:raw_text)",
        [{"scraped_on":today,"visit_date":e.get("visit_date",""),"talent_name":e.get("talent_name",""),"hall_name":e.get("hall_name",""),"img_url":e.get("img_url",""),"detail_url":e.get("detail_url",""),"source":e.get("source",""),"raw_text":e.get("raw_text","")} for e in events],
    )
    conn.commit(); conn.close()
    print(f"[store] 来店 {len(events)} 件保存")

def save_post(post):
    today = date.today().isoformat()
    conn = get_conn()
    conn.execute("INSERT INTO posts (posted_on,type,tweet_id,url,tweet_text,has_image) VALUES (?,?,?,?,?,?)",
        (today,post.get("type"),post.get("tweet_id"),post.get("url"),post.get("tweet_text"),int(bool(post.get("has_image")))))
    conn.commit(); conn.close()

def get_hot_events(today, lookback_days=90):
    conn = get_conn()
    dt = datetime.strptime(today, "%Y-%m-%d")
    weekday = dt.weekday()
    month_day = today[5:]
    weekday_hot = conn.execute("""SELECT event_name, COUNT(*) as cnt FROM events WHERE event_date >= date(:today, :lb) AND event_date != '' AND event_name != '' AND event_name != '不明' AND CAST(strftime('%w', event_date) AS INTEGER) = :wd GROUP BY event_name ORDER BY cnt DESC LIMIT 5""", {"today":today,"lb":f"-{lookback_days} days","wd":(weekday+1)%7}).fetchall()
    monthday_hot = conn.execute("""SELECT event_name, COUNT(*) as cnt FROM events WHERE substr(event_date,6) = :md AND event_name != '' AND event_name != '不明' GROUP BY event_name ORDER BY cnt DESC LIMIT 5""", {"md":month_day}).fetchall()
    overall_hot = conn.execute("""SELECT event_name, hall_name, event_date, url, COUNT(*) as cnt FROM events WHERE event_date >= date(:today, :lb) AND event_name != '' AND event_name != '不明' GROUP BY event_name ORDER BY cnt DESC LIMIT 10""", {"today":today,"lb":f"-{lookback_days} days"}).fetchall()
    upcoming = conn.execute("""SELECT DISTINCT event_name, hall_name, event_date, area, url FROM events WHERE event_date BETWEEN date(:today, '+1 day') AND date(:today, '+7 days') ORDER BY event_date LIMIT 5""", {"today":today}).fetchall()
    top_halls = conn.execute("""SELECT hall_name, COUNT(*) as cnt FROM events WHERE event_date >= date(:today, :lb) AND hall_name != '' AND hall_name != '不明' GROUP BY hall_name ORDER BY cnt DESC LIMIT 5""", {"today":today,"lb":f"-{lookback_days} days"}).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    days = conn.execute("SELECT COUNT(DISTINCT scraped_on) FROM events").fetchone()[0]
    conn.close()
    weekday_names = ["月","火","水","木","金","土","日"]
    return {"today":today,"weekday":weekday_names[weekday],"weekday_hot":[dict(r) for r in weekday_hot],"monthday_hot":[dict(r) for r in monthday_hot],"overall_hot":[dict(r) for r in overall_hot],"upcoming":[dict(r) for r in upcoming],"top_halls":[dict(r) for r in top_halls],"data_stats":{"total_events":total,"days_accumulated":days}}

def get_today_raiten(today):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM raiten WHERE visit_date = ? ORDER BY created_at DESC", (today,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
