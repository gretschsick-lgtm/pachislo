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
        r"(フジヤマ[^\s　。！\n、]{1,10})", r"(ラカータ[^\s　。！\n、]{1,10})",
    ]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return ""

# ════════════════════════════════════════════════════════════
# スクレイピング対象アカウント 総計約120件
# ════════════════════════════════════════════════════════════
TARGET_ACCOUNTS = [

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【情報まとめ系・関東全域】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "paapsaward",        # PAA：全国来店・取材情報毎日まとめ（超優良）
    "PAA_pmportal",      # PAAぱちんこメディアポータル
    "chanoma_777",       # 茶の間：来店・イベント毎日まとめ
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
    "MH_Tencho0220",     # 元マルハン店長いっぺー
    "slotchousatai",     # 関東スロパチ調査隊
    "emepka",            # カリスマ：関東全国ホール情報
    "youbun_help",       # スロット養分救済カレンダー
    "p_info_kanto",      # 関東パチスロ情報局P-info
    "hikari_pachi777",   # ひかりパチスロ日和：明日の来店まとめ
    "onigiri_slot",      # おにぎりスロット：東京・神奈川まとめ

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【神奈川専門まとめ系】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "karasuro_7",        # カラスロ@神奈川（毎日神奈川まとめ）
    "1_take6",           # Take6：神奈川ホール調査・配信
    "norakobu",          # ノライーヌこぶへい：神奈川超詳細まとめ
    "slokatsudon",       # スロかつ丼：神奈川ホール期待度まとめ
    "slot_pro_megan",    # スロプロ眼鏡：抽選人数まとめ

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【スロパチステーション演者・取材班】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "SloPachi_Sta",      # スロパチステーション取材班公式
    "isomaru_sps1",      # いそまる
    "yoshiki_sps",       # よしき
    "janjan_sps",        # じゃんじゃん
    "renjiro_sps",       # れんじろう
    "jurison_sps",       # じゅりそん
    "ruibee_sps",        # るいべえ

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【きむちゃんねる・人気演者】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "kimuragyotakuG",    # 木村魚拓
    "okihikaranai",      # 沖ヒカル
    "matsumotobatch",    # 松本バッチ
    "Aoyama_Ryo",        # 青山りょう
    "mizukiaya777",      # 水樹あや
    "anotherarashi",     # 嵐
    "ayasi0530",         # ayasi
    "perolina_usami",    # 兎味ペロリナ
    "garizo2",           # ガリぞう
    "yu_zukizuki",       # 倖田柚希
    "kimu_channel",      # きむちゃんねる公式

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【東京 エスパス日拓各店公式】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "kabupa777",         # エスパス新宿歌舞伎町（かぶぱ）
    "espace_kabuki",     # エスパス新宿歌舞伎町【公式】
    "espaceakihabara",   # エスパス秋葉原駅前（エスパだっちゃ）
    "akibaespace",       # エスパス秋葉原駅前【公式】
    "espaceseibu1",      # エスパス西武新宿駅前
    "espace_sby1",       # エスパス渋谷本館
    "shibuyaekimae0",    # エスパス渋谷駅前新館
    "espace_ueno1214",   # エスパス上野新館
    "ueno_honkan0821",   # エスパス上野本館（ぱんちゃん）
    "ESPACE_akasaka1",   # エスパス赤坂見附駅前

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【東京 楽園・その他ホール公式】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "rakuen_kamata",     # 楽園蒲田
    "rakuenikebukuro",   # 楽園池袋
    "ooyama_rakuen",     # 楽園ハッピーロード大山
    "ishikawa_rakuen",   # 楽園大山 店長石川
    "akiba_island",      # アイランド秋葉原
    "MaruhanOfficial",   # マルハン公式
    "maruhan_toho",      # マルハン新宿東宝ビル
    "endo1maruhan",      # マルハン店員エンドウ
    "maruhankamata",     # マルハン蒲田
    "maruhan_hino",      # マルハン日野
    "pachislotenchou",   # マルハン店長系
    "dynamjp",           # ダイナム公式
    "hirokiwest66666",   # ヒロキ蒲田西口
    "hiroki_higashi2",   # ヒロキ東口
    "kicona_yodamaru",   # キコーナ淀川丸
    "PS_garden_ch",      # ガーデン公式ch
    "3too9_kamata_39",   # 蒲田系ホール

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【神奈川 ホール公式】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "kawasaki_rakuen",   # 楽園川崎店【公式】
    "rakuen_sagami",     # 楽園相模原店【公式】
    "shinjo_stage",      # ピーアーク神奈川公式（相模大野・新城・相模原）
    "sagamihara0429",    # ピーアーク相模原
    "sagachan_park",     # ピーアーク相模大野アンバサダー
    "ZIATH_Ofuna",       # ジアス大船【公式】
    "singardentotuka",   # 新！ガーデン戸塚【公式】
    "maruhan_yokoham",   # マルハンメガシティ横浜
    "kanagawa_kicona",   # キコーナ神奈川
    "Kicona_ebina",      # キコーナ海老名
    "KNakamachidai",     # キコーナ中山台

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【埼玉 ガーデン系列公式】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "gardenkitayono",    # ガーデン北与野
    "garden_yono",       # ガーデン与野
    "gardenkitatoda",    # ガーデン北戸田
    "KawagutiAngyo",     # 新！ガーデン川口安行【公式】
    "g_nishiurawa",      # 新！ガーデン西浦和【公式】
    "g_kasukabe",        # 新！ガーデン春日部【公式】
    "GARDENgashimiya",   # ガーデン東大宮
    "g_higashiurawa",    # ガーデン東浦和【公式】
    "Smart_G_Musaura",   # スマートガーデン武蔵浦和【公式】
    "2288g_yashio_28",   # 新！ガーデン八潮【公式】

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 【埼玉 ピーアーク・その他ホール公式】
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "park_saitama",      # ピーアーク埼玉公式
    "P_Ark_Soka",        # ピーアーク草加店長
    "PKawaguchi30785",   # PIA川口【公式】
    "SAPsouka",          # SAP草加【公式】
    "p_megatoko",        # メガトーコー
]

# 重複除去
TARGET_ACCOUNTS = list(dict.fromkeys(TARGET_ACCOUNTS))

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
