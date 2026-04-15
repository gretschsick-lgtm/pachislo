import os, re, time, tweepy
from datetime import datetime, date

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
    return any(k in text for k in [
        "イベント","来店","全台","旧イベ","設定","特日","ガチ日","周年","記念",
        "アツ","熱","取材","狙い","推し","快便","明日の","月イチ","ゾロ目",
        "新装","特定日","抽選","収録","実践","スケジュール","予告",
        "明日","今日","気になる","注目","OPEN","オープン","来店"
    ])

def _is_raiten(text):
    return any(k in text for k in [
        "来店","来場","ゲスト","取材","収録","実践来店",
        "いそまる","よしき","じゃんじゃん","れんじろう","じゅりそん","るいべえ",
        "木村魚拓","沖ヒカル","松本バッチ","青山りょう","水樹あや","倖田柚希",
        "ガリぞう","嵐","ayasi","兎味ペロリナ","大崎一万発","スロパチガール",
        "ガイモン","工藤らぎ","神谷玲子","ゆり姉","あゆあゆ","クワーマン",
        "sasuke","タカハシカゴ","てつ","まいたけ","ちゅんげー","マッティー",
        "橘リノ","あしなっくす","こしあん","ほしまみ","シーナ"
    ])

def _extract_event_name(text):
    for pat in [r"【([^】]{2,20})】", r"「([^」]{2,20})」",
                r"(全台[^\s　。！]{0,10})", r"(旧イベ[^\s　。！]{0,10})",
                r"(周年[^\s　。！]{0,10})", r"(月イチ[^\s　。！]{0,10})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return text[:20].strip()

def _extract_talent(text):
    known = [
        "いそまる","よしき","じゃんじゃん","れんじろう","じゅりそん","るいべえ",
        "木村魚拓","沖ヒカル","松本バッチ","青山りょう","水樹あや","倖田柚希",
        "ガリぞう","嵐","ayasi","兎味ペロリナ","大崎一万発","スロパチガール",
        "ガイモン","工藤らぎ","神谷玲子","ゆり姉","あゆあゆ","クワーマン",
        "sasuke","タカハシカゴ","てつ","まいたけ","ちゅんげー","マッティー",
        "橘リノ","あしなっくす","こしあん","ほしまみ","シーナ"
    ]
    for name in known:
        if name in text: return name
    for pat in [r"(?:来店|来場)[：:]\s*([^\s　\n！。、]{2,15})",
                r"【来店】([^\s　\n！。【】]{2,15})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return "(来店者不明)"

def _extract_hall(text):
    for pat in [
        r"(マルハン[^\s　。！\n、]{1,15})", r"(ピーアーク[^\s　。！\n、]{1,15})",
        r"(ガーデン[^\s　。！\n、]{1,10})", r"(キコーナ[^\s　。！\n、]{1,10})",
        r"(楽園[^\s　。！\n、]{1,10})", r"(ダイナム[^\s　。！\n、]{1,10})",
        r"(エスパス[^\s　。！\n、]{1,10})", r"(ジアス[^\s　。！\n、]{1,10})",
        r"(123[^\s　。！\n、]{1,10})", r"(メッセ[^\s　。！\n、]{1,10})",
        r"(アイランド[^\s　。！\n、]{1,10})", r"(エクスアリーナ[^\s　。！\n、]{1,10})",
        r"(プレサス[^\s　。！\n、]{1,10})", r"(パラッツォ[^\s　。！\n、]{1,10})",
        r"(ニラク[^\s　。！\n、]{1,10})", r"(ベルシティ[^\s　。！\n、]{1,10})",
        r"(PIA[^\s　。！\n、]{1,10})", r"(Dステ[^\s　。！\n、]{1,10})",
        r"(第一プラザ[^\s　。！\n、]{1,10})", r"(ラカータ[^\s　。！\n、]{1,10})",
        r"(ガイア[^\s　。！\n、]{1,10})", r"(UNO[^\s　。！\n、]{1,10})",
        r"(アビバ[^\s　。！\n、]{1,10})", r"(ベガスベガス[^\s　。！\n、]{1,10})",
        r"(ゴードン[^\s　。！\n、]{1,10})", r"(メガフェイス[^\s　。！\n、]{1,10})",
        r"(やすだ[^\s　。！\n、]{1,10})", r"(吉兆[^\s　。！\n、]{1,10})",
        r"(グランキコーナ[^\s　。！\n、]{1,10})", r"(ユーコーラッキー[^\s　。！\n、]{1,10})",
        r"(SAP[^\s　。！\n、]{1,10})", r"(BIGディッパー[^\s　。！\n、]{1,10})",
        r"(みとや[^\s　。！\n、]{1,10})", r"(アミューズ[^\s　。！\n、]{1,10})",
        r"(フジヤマ[^\s　。！\n、]{1,10})",
    ]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return ""

# ════════════════════════════════════════════════════════════
# スクレイピング対象アカウント（上位20件に絞る）
# 月約3,600リクエスト → 無料プラン15,000の範囲内
# ════════════════════════════════════════════════════════════
TARGET_ACCOUNTS = [
    "paapsaward",        # PAA：毎日全国来店・取材100件以上まとめ（最強）
    "PAA_pmportal",      # PAAぱちんこメディアポータル
    "chanoma_777",       # 茶の間：毎日来店・イベントまとめ
    "slot_channel_",     # スロちゃん：関東全域まとめ屋
    "touslot",           # 東スロ：東京・神奈川・埼玉予想まとめ
    "slo1_tyousataiZ",   # スロイベ調査隊Z関東
    "kata_sainokuni",    # 塊：埼玉・東京中心
    "kachigumimax",      # Makotoパチスロ案内人
    "ainavipachislot",   # AIナビ関東版
    "ikechinpachislo",   # いけちん：関東データまとめ
    "slot_ogikiti",      # 荻吉@スロ
    "slotdekatu",        # ペカ男爵
    "slotterguild",      # スロッターギルド
    "999999Q9Q",         # ココイチ：東京マルハン情報
    "ibentoan",          # 朧：スロットイベント案内
    "slotchousatai",     # 関東スロパチ調査隊
    "emepka",            # カリスマ：関東全国ホール情報
    "karasuro_7",        # カラスロ@神奈川（毎日神奈川まとめ）
    "norakobu",          # ノライーヌこぶへい：神奈川超詳細まとめ
    "p_info_kanto",      # 関東パチスロ情報局P-info
]

def _get_client():
    return tweepy.Client(
        bearer_token=os.environ.get("X_BEARER_TOKEN",""),
        wait_on_rate_limit=False
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
        time.sleep(0.5)
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
