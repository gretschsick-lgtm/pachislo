import os
from datetime import date, datetime
import store
import scraper
import images
import poster

PREF_CODE = os.environ.get("PREFECTURE_CODE", "13")
PREF_HINT = os.environ.get("PREFECTURE_HINT", "東京")
PAGES     = int(os.environ.get("SCRAPE_PAGES", "5"))
DRY_RUN   = os.environ.get("DRY_RUN", "false").lower() == "true"
POST_TYPE = os.environ.get("POST_TYPE", "yokoku")  # yokoku or matome

SEP  = "─" * 52
SEP2 = "━" * 52
TODAY = date.today().isoformat()


def _post_or_dry(tweet_text, image_path, label):
    if DRY_RUN:
        print(f"\n🔒 DRY_RUN [{label}]")
        print(f"  文章  : {tweet_text[:80]}…")
        print(f"  画像  : {image_path or 'なし'}")
        store.save_post({"type": label, "tweet_id": "dry_run",
                         "url": "", "tweet_text": tweet_text})
    else:
        result = poster.post(tweet_text, image_path)
        result["type"] = label
        store.save_post(result)


def step_scrape():
    print(f"\n{SEP}")
    print(f"📡 [STEP 1] スクレイピング開始（{PREF_HINT}）")
    events = scraper.scrape_events(PREF_CODE, PAGES)
    if events:
        store.save_events(events, prefecture=PREF_HINT)
    raiten = scraper.scrape_all_raiten(PREF_CODE, PREF_HINT)
    if raiten:
        store.save_raiten(raiten, prefecture=PREF_HINT)
    print(f"  → イベント {len(events)} 件 / 来店 {len(raiten)} 件 をDBに保存")


def step_yokoku():
    """21時投稿：明日のイベント予告"""
    print(f"\n{SEP}")
    print(f"🔍 [予告] 明日のアツいイベント投稿（{PREF_HINT}）")
    analysis = store.get_hot_events(TODAY, lookback_days=90, prefecture=PREF_HINT)
    stats = analysis["data_stats"]
    print(f"  蓄積データ: {stats['total_events']} 件 / {stats['days_accumulated']} 日分")
    if stats["total_events"] == 0:
        print("  ⚠️ データ未蓄積 → スキップ")
        return

    tweet_text = poster.generate(poster.build_yokoku_prompt(analysis, PREF_HINT))
    target = next(iter(analysis.get("tomorrow_events", [])), None) or \
             next(iter(analysis.get("hot_halls", [])), None)
    image_path = images.get_event_image(target) if target else None
    _post_or_dry(tweet_text, image_path, label=f"予告_{PREF_HINT}")

    # 来店予告
    today_raiten = store.get_today_raiten(TODAY, prefecture=PREF_HINT)
    if today_raiten:
        print(f"\n  🌟 来店予告: {len(today_raiten)} 件")
        raiten_text = poster.generate(poster.build_raiten_prompt(today_raiten, PREF_HINT))
        best = sorted(today_raiten,
                      key=lambda r: (bool(r.get("img_url")),
                                     r.get("talent_name","") != "(来店者不明)"),
                      reverse=True)[0]
        raiten_image = images.get_raiten_image(best)
        _post_or_dry(raiten_text, raiten_image, label=f"来店予告_{PREF_HINT}")


def step_matome():
    """23時投稿：今日のアツかったイベントまとめ"""
    print(f"\n{SEP}")
    print(f"📊 [まとめ] 今日のアツかった情報（{PREF_HINT}）")
    matome = store.get_today_matome(TODAY, prefecture=PREF_HINT)
    if not matome:
        print("  ⚠️ 今日のデータなし → スキップ")
        return
    tweet_text = poster.generate(poster.build_matome_prompt(matome, PREF_HINT))
    _post_or_dry(tweet_text, None, label=f"まとめ_{PREF_HINT}")


def main():
    print(f"\n{SEP2}")
    print(f"🎰 パチンコBot  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   地域: {PREF_HINT}（コード: {PREF_CODE}）  POST_TYPE: {POST_TYPE}  DRY_RUN: {DRY_RUN}")
    print(SEP2)

    step_scrape()

    if POST_TYPE == "yokoku":
        step_yokoku()
    elif POST_TYPE == "matome":
        step_matome()

    print(f"\n{SEP2}")
    print("✅ 完了！")
    print(SEP2)


if __name__ == "__main__":
    main()
