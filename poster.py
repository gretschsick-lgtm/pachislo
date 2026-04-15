import os, anthropic, tweepy
from datetime import datetime, timedelta

# 演者名 → XアカウントURL 対応表（確認済み）
TALENT_URLS = {
    # ━━ スロパチステーション ━━
    "いそまる":      "https://x.com/isomaru_sps1",
    "よしき":        "https://x.com/yoshiki_sps",
    "じゃんじゃん":  "https://x.com/janjan_sps",
    "れんじろう":    "https://x.com/renjiro_sps",
    "じゅりそん":    "https://x.com/jurison_sps",
    "るいべえ":      "https://x.com/ruibee_sps",
    # ━━ きむちゃんねる系 ━━
    "木村魚拓":      "https://x.com/kimuragyotakuG",
    "沖ヒカル":      "https://x.com/okihikaranai",
    "松本バッチ":    "https://x.com/matsumotobatch",
    "青山りょう":    "https://x.com/Aoyama_Ryo",
    "水樹あや":      "https://x.com/mizukiaya777",
    "嵐":            "https://x.com/anotherarashi",
    "ayasi":         "https://x.com/ayasi0530",
    "兎味ペロリナ":  "https://x.com/perolina_usami",
    "ガリぞう":      "https://x.com/garizo2",
    "倖田柚希":      "https://x.com/yu_zukizuki",
    # ━━ 大御所・人気ライター ━━
    "ういち":        "https://x.com/UichiSch",
    "寺井一択":      "https://x.com/terai_ScooP",
    "梅屋シン":      "https://x.com/shinumeya",
    "日直島田":      "https://x.com/courage05x2",
    "しんのすけ":    "https://x.com/shinnosuke000",
    "レビン":        "https://x.com/levin_slomaga",
    "橘アンジュ":    "https://x.com/RareCoinAnju",
    "橘リノ":        "https://x.com/Rino_Tachi",
    "森本レオ子":    "https://x.com/reocopon",
    "中武一日二膳":  "https://x.com/2zen777",
    "がっきー":      "https://x.com/gacky0301",
    "フェアリン":    "https://x.com/fairrin",
    "ガル憎":        "https://x.com/garuzow",
    "ドテチン":      "https://x.com/maga_dotechin",
    "バイク修次郎":  "https://x.com/syuziro",
    "しのけん":      "https://x.com/shino_cafe777",
    # ━━ 来店頻度高い演者 ━━
    "まいたけ":      "https://x.com/maitake_gohan",
    "ちゅんげー":    "https://x.com/chunge_pachi",
    "あしなっくす":  "https://x.com/ashinax777",
    "こしあん":      "https://x.com/koshian_pachi",
    "ほしまみ":      "https://x.com/hoshimami777",
    "タカハシカゴ":  "https://x.com/takahashikago",
    "ガイモン":      "https://x.com/gaimon777",
    "工藤らぎ":      "https://x.com/ragi_kudo",
    "神谷玲子":      "https://x.com/reiko_kamiya_p",
    "くろむ":        "https://x.com/kuromu_slot",
    "ヤルヲ":        "https://x.com/yaruwo_slot",
    "天草ヤスヲ":    "https://x.com/amakusa_yasuo",
    "おゆん":        "https://x.com/oyun_pachi",
    "ゆり姉":        "https://x.com/yurineee777",
    "あゆあゆ":      "https://x.com/ayuayu_pachi",
    "クワーマン":    "https://x.com/kuwaman_slot",
    "sasuke":        "https://x.com/sasuke_pachi777",
    "シーナ":        "https://x.com/shiina_goopachi",
    "大崎一万発":    "https://x.com/ichimanbatu",
}

def generate(prompt):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role":"user","content":prompt}])
    text = msg.content[0].text.strip()
    print(f"[poster] 生成:\n{text}\n")
    return text

def _v1api():
    auth = tweepy.OAuth1UserHandler(os.environ["X_API_KEY"], os.environ["X_API_SECRET"], os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_TOKEN_SECRET"])
    return tweepy.API(auth)

def _v2client():
    return tweepy.Client(consumer_key=os.environ["X_API_KEY"], consumer_secret=os.environ["X_API_SECRET"], access_token=os.environ["X_ACCESS_TOKEN"], access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"])

def _upload_image(path):
    try:
        media = _v1api().media_upload(filename=path)
        return str(media.media_id)
    except Exception as e:
        print(f"[poster] 画像アップロード失敗: {e}")
        return None

def post(tweet_text, image_path=None):
    media_ids = None
    if image_path:
        mid = _upload_image(image_path)
        if mid: media_ids = [mid]
    try:
        resp = _v2client().create_tweet(text=tweet_text, media_ids=media_ids)
        tweet_id = resp.data["id"]
        url = f"https://x.com/i/web/status/{tweet_id}"
        print(f"[poster] 投稿完了: {url}")
        return {"tweet_id": tweet_id, "url": url, "tweet_text": tweet_text, "has_image": bool(media_ids)}
    except Exception as e:
        print(f"[poster] 投稿失敗: {e}")
        return {"tweet_id": "error", "url": "", "tweet_text": tweet_text, "has_image": False}

def build_yokoku_prompt(analysis, pref_hint="東京"):
    now = datetime.now()
    tomorrow_short = (now + timedelta(days=1)).strftime("%m月%d日")
    weekday = ["月","火","水","木","金","土","日"][now.weekday()]

    halls_txt = ""
    for i, h in enumerate(analysis.get("hot_halls", [])[:3], 1):
        halls_txt += f"  {i}. {h['hall_name']}（過去{h['total_cnt']}回 / 直近30日{h['recent_cnt']}回）\n"
    if not halls_txt: halls_txt = "  （データ蓄積中）\n"

    tomorrow_txt = ""
    for e in analysis.get("tomorrow_events", []):
        tomorrow_txt += f"  ・{e['hall_name']} 「{e['event_name']}」\n"
    tomorrow_txt = tomorrow_txt or "  （なし）"

    weekday_txt = "\n".join(f"  ・{e['event_name']}（{e['cnt']}回）" for e in analysis.get("weekday_hot", [])[:3]) or "  （データ蓄積中）"
    stats = analysis.get("data_stats", {})

    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
{pref_hint}エリアの明日 {tomorrow_short} のアツいイベント予告ツイートを作成してください。

【{pref_hint}エリアの過去データからアツいホールTOP3】
{halls_txt}
【明日 {tomorrow_short} の予告イベント】
{tomorrow_txt}
【{weekday}曜日によく開催されるアツいイベント】
{weekday_txt}
【データ蓄積】{stats.get('total_events',0)}件 / {stats.get('days_accumulated',0)}日分

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で読みやすく
- 必ず「明日{tomorrow_short}」と日付を入れる
- {pref_hint}エリアであることを明記
- アツいホール名を具体的に入れる
- URLは絶対に入れない
- ハッシュタグ3〜4個（#パチスロ #パチンコ #{pref_hint} #明日のイベント）"""

def build_matome_prompt(matome, pref_hint="東京"):
    now = datetime.now()
    today = now.strftime("%m月%d日")

    halls_txt = ""
    for i, h in enumerate(matome[:3], 1):
        halls_txt += f"  {i}. {h['hall_name']} 「{h['events']}」（{h['cnt']}件の話題）\n"
    if not halls_txt: halls_txt = "  （データなし）\n"

    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
{pref_hint}エリアの本日 {today} のアツかったイベントまとめツイートを作成してください。

【本日Xで話題になった{pref_hint}のホールTOP3】
{halls_txt}

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で読みやすく
- 必ず「本日{today}」と日付を入れる
- {pref_hint}エリアであることを明記
- 「今日アツかった」「話題になった」という表現を使う
- URLは絶対に入れない
- ハッシュタグ3〜4個（#パチスロ #パチンコ #{pref_hint} #今日のアツ台）"""

def build_raiten_prompt(raiten_list, pref_hint="東京"):
    now = datetime.now()
    tomorrow_short = (now + timedelta(days=1)).strftime("%m月%d日")

    lines = ""
    for r in raiten_list[:5]:
        talent = r['talent_name']
        hall = r['hall_name']
        url = TALENT_URLS.get(talent, "")
        url_str = f"\n    👉 {url}" if url else ""
        lines += f"  ・{talent} → {hall}{url_str}\n"

    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
{pref_hint}エリアの明日 {tomorrow_short} の来店イベント予告ツイートを作成してください。

【明日の来店情報】
{lines}

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で華やかに
- 必ず「明日{tomorrow_short}」と日付を入れる
- {pref_hint}エリアであることを明記
- 誰がどこに来るか明確に
- 来店者のXアカウントURLがある場合は必ず1つ載せる
- ホール情報のURLは載せない
- ハッシュタグ3〜4個（#来店情報 #パチスロ #{pref_hint} #パチンコ）
- ファンが行きたくなる熱量で書く"""

def build_event_prompt(analysis):
    return build_yokoku_prompt(analysis)import os, anthropic, tweepy
from datetime import datetime, timedelta

# 演者名 → XアカウントURL 対応表（確認済み）
TALENT_URLS = {
    # ━━ スロパチステーション ━━
    "いそまる":      "https://x.com/isomaru_sps1",
    "よしき":        "https://x.com/yoshiki_sps",
    "じゃんじゃん":  "https://x.com/janjan_sps",
    "れんじろう":    "https://x.com/renjiro_sps",
    "じゅりそん":    "https://x.com/jurison_sps",
    "るいべえ":      "https://x.com/ruibee_sps",
    # ━━ きむちゃんねる系 ━━
    "木村魚拓":      "https://x.com/kimuragyotakuG",
    "沖ヒカル":      "https://x.com/okihikaranai",
    "松本バッチ":    "https://x.com/matsumotobatch",
    "青山りょう":    "https://x.com/Aoyama_Ryo",
    "水樹あや":      "https://x.com/mizukiaya777",
    "嵐":            "https://x.com/anotherarashi",
    "ayasi":         "https://x.com/ayasi0530",
    "兎味ペロリナ":  "https://x.com/perolina_usami",
    "ガリぞう":      "https://x.com/garizo2",
    "倖田柚希":      "https://x.com/yu_zukizuki",
    # ━━ 大御所・人気ライター ━━
    "ういち":        "https://x.com/UichiSch",
    "寺井一択":      "https://x.com/terai_ScooP",
    "梅屋シン":      "https://x.com/shinumeya",
    "日直島田":      "https://x.com/courage05x2",
    "しんのすけ":    "https://x.com/shinnosuke000",
    "レビン":        "https://x.com/levin_slomaga",
    "橘アンジュ":    "https://x.com/RareCoinAnju",
    "橘リノ":        "https://x.com/Rino_Tachi",
    "森本レオ子":    "https://x.com/reocopon",
    "中武一日二膳":  "https://x.com/2zen777",
    "がっきー":      "https://x.com/gacky0301",
    "フェアリン":    "https://x.com/fairrin",
    "ガル憎":        "https://x.com/garuzow",
    "ドテチン":      "https://x.com/maga_dotechin",
    "バイク修次郎":  "https://x.com/syuziro",
    "しのけん":      "https://x.com/shino_cafe777",
    # ━━ 来店頻度高い演者 ━━
    "まいたけ":      "https://x.com/maitake_gohan",
    "ちゅんげー":    "https://x.com/chunge_pachi",
    "あしなっくす":  "https://x.com/ashinax777",
    "こしあん":      "https://x.com/koshian_pachi",
    "ほしまみ":      "https://x.com/hoshimami777",
    "タカハシカゴ":  "https://x.com/takahashikago",
    "ガイモン":      "https://x.com/gaimon777",
    "工藤らぎ":      "https://x.com/ragi_kudo",
    "神谷玲子":      "https://x.com/reiko_kamiya_p",
    "くろむ":        "https://x.com/kuromu_slot",
    "ヤルヲ":        "https://x.com/yaruwo_slot",
    "天草ヤスヲ":    "https://x.com/amakusa_yasuo",
    "おゆん":        "https://x.com/oyun_pachi",
    "ゆり姉":        "https://x.com/yurineee777",
    "あゆあゆ":      "https://x.com/ayuayu_pachi",
    "クワーマン":    "https://x.com/kuwaman_slot",
    "sasuke":        "https://x.com/sasuke_pachi777",
    "シーナ":        "https://x.com/shiina_goopachi",
    "大崎一万発":    "https://x.com/ichimanbatu",
}

def generate(prompt):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role":"user","content":prompt}])
    text = msg.content[0].text.strip()
    print(f"[poster] 生成:\n{text}\n")
    return text

def _v1api():
    auth = tweepy.OAuth1UserHandler(os.environ["X_API_KEY"], os.environ["X_API_SECRET"], os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_TOKEN_SECRET"])
    return tweepy.API(auth)

def _v2client():
    return tweepy.Client(consumer_key=os.environ["X_API_KEY"], consumer_secret=os.environ["X_API_SECRET"], access_token=os.environ["X_ACCESS_TOKEN"], access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"])

def _upload_image(path):
    try:
        media = _v1api().media_upload(filename=path)
        return str(media.media_id)
    except Exception as e:
        print(f"[poster] 画像アップロード失敗: {e}")
        return None

def post(tweet_text, image_path=None):
    media_ids = None
    if image_path:
        mid = _upload_image(image_path)
        if mid: media_ids = [mid]
    try:
        resp = _v2client().create_tweet(text=tweet_text, media_ids=media_ids)
        tweet_id = resp.data["id"]
        url = f"https://x.com/i/web/status/{tweet_id}"
        print(f"[poster] 投稿完了: {url}")
        return {"tweet_id": tweet_id, "url": url, "tweet_text": tweet_text, "has_image": bool(media_ids)}
    except Exception as e:
        print(f"[poster] 投稿失敗: {e}")
        return {"tweet_id": "error", "url": "", "tweet_text": tweet_text, "has_image": False}

def build_yokoku_prompt(analysis, pref_hint="東京"):
    now = datetime.now()
    tomorrow_short = (now + timedelta(days=1)).strftime("%m月%d日")
    weekday = ["月","火","水","木","金","土","日"][now.weekday()]

    halls_txt = ""
    for i, h in enumerate(analysis.get("hot_halls", [])[:3], 1):
        halls_txt += f"  {i}. {h['hall_name']}（過去{h['total_cnt']}回 / 直近30日{h['recent_cnt']}回）\n"
    if not halls_txt: halls_txt = "  （データ蓄積中）\n"

    tomorrow_txt = ""
    for e in analysis.get("tomorrow_events", []):
        tomorrow_txt += f"  ・{e['hall_name']} 「{e['event_name']}」\n"
    tomorrow_txt = tomorrow_txt or "  （なし）"

    weekday_txt = "\n".join(f"  ・{e['event_name']}（{e['cnt']}回）" for e in analysis.get("weekday_hot", [])[:3]) or "  （データ蓄積中）"
    stats = analysis.get("data_stats", {})

    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
{pref_hint}エリアの明日 {tomorrow_short} のアツいイベント予告ツイートを作成してください。

【{pref_hint}エリアの過去データからアツいホールTOP3】
{halls_txt}
【明日 {tomorrow_short} の予告イベント】
{tomorrow_txt}
【{weekday}曜日によく開催されるアツいイベント】
{weekday_txt}
【データ蓄積】{stats.get('total_events',0)}件 / {stats.get('days_accumulated',0)}日分

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で読みやすく
- 必ず「明日{tomorrow_short}」と日付を入れる
- {pref_hint}エリアであることを明記
- アツいホール名を具体的に入れる
- URLは絶対に入れない
- ハッシュタグ3〜4個（#パチスロ #パチンコ #{pref_hint} #明日のイベント）"""

def build_matome_prompt(matome, pref_hint="東京"):
    now = datetime.now()
    today = now.strftime("%m月%d日")

    halls_txt = ""
    for i, h in enumerate(matome[:3], 1):
        halls_txt += f"  {i}. {h['hall_name']} 「{h['events']}」（{h['cnt']}件の話題）\n"
    if not halls_txt: halls_txt = "  （データなし）\n"

    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
{pref_hint}エリアの本日 {today} のアツかったイベントまとめツイートを作成してください。

【本日Xで話題になった{pref_hint}のホールTOP3】
{halls_txt}

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で読みやすく
- 必ず「本日{today}」と日付を入れる
- {pref_hint}エリアであることを明記
- 「今日アツかった」「話題になった」という表現を使う
- URLは絶対に入れない
- ハッシュタグ3〜4個（#パチスロ #パチンコ #{pref_hint} #今日のアツ台）"""

def build_raiten_prompt(raiten_list, pref_hint="東京"):
    now = datetime.now()
    tomorrow_short = (now + timedelta(days=1)).strftime("%m月%d日")

    lines = ""
    for r in raiten_list[:5]:
        talent = r['talent_name']
        hall = r['hall_name']
        url = TALENT_URLS.get(talent, "")
        url_str = f"\n    👉 {url}" if url else ""
        lines += f"  ・{talent} → {hall}{url_str}\n"

    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
{pref_hint}エリアの明日 {tomorrow_short} の来店イベント予告ツイートを作成してください。

【明日の来店情報】
{lines}

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で華やかに
- 必ず「明日{tomorrow_short}」と日付を入れる
- {pref_hint}エリアであることを明記
- 誰がどこに来るか明確に
- 来店者のXアカウントURLがある場合は必ず1つ載せる
- ホール情報のURLは載せない
- ハッシュタグ3〜4個（#来店情報 #パチスロ #{pref_hint} #パチンコ）
- ファンが行きたくなる熱量で書く"""

def build_event_prompt(analysis):
    return build_yokoku_prompt(analysis)
