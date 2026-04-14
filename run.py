"""
run.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
毎日の自動実行エントリーポイント
"""

import os
import sys
from datetime import date, datetime

import store
import scraper
import images
import poster

PREF_CODE  = os.environ.get("PREFECTURE_CODE",  "13")
PREF_HINT  = os.environ.get("PREFECTURE_HINT",  "東京")
PAGES      = int(os.environ.get("SCRAPE_PAGES", "5"))
DRY_RUN    = os.environ.get("DRY_RUN", "false").lower() == "true"

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
    print("📡 [STEP 1] スクレイピング開始")
    events = scraper.scrape_events(PREF_CODE, PAGES)
    if events:
        store.save_events(events)
    raiten = scraper.scrape_all_raiten(PREF_CODE, PREF_HINT)
    if raiten:
        store.save_raiten(raiten)
    print(f"  → イベント {len(events)} 件 / 来店 {len(raiten)} 件 をDBに保存")


def step_event_post():
    print(f"\n{SEP}")
    print("🔍 [STEP 2] 過去データ分析 → 通常イベント投稿")
    analysis = store.get_hot_events(TODAY, lookback_days=90)
    stats = analysis["data_stats"]
    print(f"  蓄積データ: {stats['total_events']} 件 / {stats['days_accumulated']} 日分")
    if stats["total_events"] == 0:
        print("  ⚠️ データ未蓄積 → 初回は分析スキップ")
        return
    tweet_text = poster.generate(poster.build_event_prompt(analysis))
    target = next(iter(analysis["upcoming"]), None) or next(iter(analysis["overall_hot"]), None)
    image_path = images.get_event_image(target) if target else None
    _post_or_dry(tweet_text, image_path, label="通常イベント")


def step_raiten_post():
    print(f"\n{SEP}")
    print("🌟 [STEP 3] 来店チェック")
    today_raiten = store.get_today_raiten(TODAY)
    if not today_raiten:
        print("  📭 本日の来店なし → スキップ")
        return
    print(f"  🎉 本日の来店: {len(today_raiten)} 件")
    tweet_text = poster.generate(poster.build_raiten_prompt(today_raiten))
    best = sorted(today_raiten, key=lambda r: (bool(r.get("img_url")), r.get("talent_name","") != "(来店者不明)"), reverse=True)[0]
    image_path = images.get_raiten_image(best)
    _post_or_dry(tweet_text, image_path, label="来店イベント")


def main():
    print(f"\n{SEP2}")
    print(f"🎰 パチンコBot  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   地域: {PREF_HINT}（コード: {PREF_CODE}）  DRY_RUN: {DRY_RUN}")
    print(SEP2)
    step_scrape()
    step_event_post()
    step_raiten_post()
    print(f"\n{SEP2}")
    print("✅ 完了！")
    print(SEP2)


if __name__ == "__main__":
    main()
