import os
import store
import scraper
import poster
from datetime import date, datetime

PREF_CODE  = os.environ.get("PREF_CODE") or os.environ.get("PREFECTURE_CODE", "13")
PREF_HINT  = os.environ.get("PREF_HINT") or os.environ.get("PREFECTURE_HINT", "東京")
POST_TYPE  = os.environ.get("POST_TYPE", "yokoku")
DRY_RUN    = os.environ.get("DRY_RUN", "false").lower() == "true"
PAGES      = int(os.environ.get("SCRAPE_PAGES", "5"))

print("━"*60)
print(f"🎰 パチンコBot  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"   地域: {PREF_HINT}（コード: {PREF_CODE}）  POST_TYPE: {POST_TYPE}  DRY_RUN: {DRY_RUN}")
print("━"*60)

def _post_or_dry(tweet_text, image_path=None, label=""):
    if DRY_RUN:
        print(f"[DRY_RUN] {label}: {tweet_text[:80]}...")
        return {"tweet_id": "dry", "url": "", "tweet_text": tweet_text}
    result = poster.post(tweet_text, image_path)
    store.save_post({**result, "type": label})
    return result

def step_scrape():
    print("\n" + "─"*52)
    print(f"📡 [STEP 1] スクレイピング開始（{PREF_HINT}）")
    events = scraper.scrape_events(PREF_CODE, PAGES)
    try:
        from scraper_hallnavi import scrape_hallnavi
        hn_events = scrape_hallnavi(prefecture_code=PREF_CODE)
        events = events + hn_events
    except Exception as e:
        print(f"[hallnavi] スキップ: {e}")
    raiten = scraper.scrape_all_raiten(PREF_CODE, PREF_HINT)
    store.save_events(events, prefecture=PREF_HINT)
    store.save_raiten(raiten, prefecture=PREF_HINT)
    print(f"  → イベント {len(events)} 件 / 来店 {len(raiten)} 件 をDBに保存")
    return events, raiten

def step_yokoku():
    print("\n" + "─"*52)
    print(f"🔍 [予告] 明日のアツいイベント投稿（{PREF_HINT}）")
    today = date.today().isoformat()
    analysis = store.get_hot_events(today, prefecture=PREF_HINT)
    stats = analysis.get("data_stats", {})
    print(f"  蓄積データ: {stats.get('total_events',0)} 件 / {stats.get('days_accumulated',0)} 日分")

    # 来店ツイート
    raiten_list = store.get_today_raiten(today, prefecture=PREF_HINT)
    if raiten_list:
        prompt = poster.build_raiten_prompt(raiten_list, pref_hint=PREF_HINT)
        tweet_text = poster.generate(prompt)
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
        try:
            import images
            image_path = images.get_raiten_image(raiten_list[0], pref_hint=PREF_HINT)
        except Exception as e:
            print(f"[images] 来店画像スキップ: {e}")
            image_path = None
        _post_or_dry(tweet_text, image_path, label=f"来店_{PREF_HINT}")

    # イベント予告ツイート
    prompt = poster.build_yokoku_prompt(analysis, pref_hint=PREF_HINT)
    tweet_text = poster.generate(prompt)
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."
    try:
        import images
        dummy_event = {"hall_name": "", "event_name": ""}
        image_path = images.get_event_image(dummy_event, analysis=analysis, pref_hint=PREF_HINT)
    except Exception as e:
        print(f"[images] イベント画像スキップ: {e}")
        image_path = None
    _post_or_dry(tweet_text, image_path, label=f"予告_{PREF_HINT}")

def step_matome():
    print("\n" + "─"*52)
    print(f"📊 [まとめ] 本日のまとめ投稿（{PREF_HINT}）")
    today = date.today().isoformat()
    matome = store.get_today_matome(today, prefecture=PREF_HINT)
    prompt = poster.build_matome_prompt(matome, pref_hint=PREF_HINT)
    tweet_text = poster.generate(prompt)
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."
    _post_or_dry(tweet_text, None, label=f"まとめ_{PREF_HINT}")

def main():
    step_scrape()
    if POST_TYPE == "yokoku":
        step_yokoku()
    elif POST_TYPE == "matome":
        step_matome()
    print("\n" + "━"*60)
    print("✅ 完了！")
    print("━"*60)

if __name__ == "__main__":
    main()
