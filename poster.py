import os, anthropic, tweepy
from datetime import datetime, timedelta

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
    today = now.strftime("%Y年%m月%d日")
    weekday = ["月","火","水","木","金","土","日"][now.weekday()]
    tomorrow = (now + timedelta(days=1)).strftime("%Y年%m月%d日")
    tomorrow_short = (now + timedelta(days=1)).strftime("%m月%d日")

    halls_txt = ""
    for i, h in enumerate(analysis.get("hot_halls", [])[:3], 1):
        halls_txt += f"  {i}. {h['hall_name']}（過去{h['total_cnt']}回 / 直近30日{h['recent_cnt']}回）\n"
    if not halls_txt: halls_txt = "  （データ蓄積中）\n"

    tomorrow_txt = "\n".join(f"  ・{e['hall_name']} 「{e['event_name']}」" for e in analysis.get("tomorrow_events", [])) or "  （なし）"
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
- アツいホール3店舗を具体的に紹介
- ハッシュタグ4〜5個（#パチンコ #スロット #{pref_hint} #明日のイベント #パチスロ）"""

def build_matome_prompt(matome, pref_hint="東京"):
    now = datetime.now()
    today = now.strftime("%Y年%m月%d日")
    weekday = ["月","火","水","木","金","土","日"][now.weekday()]

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
- ハッシュタグ4〜5個（#パチンコ #スロット #{pref_hint} #今日のアツ台 #パチスロ）"""

def build_raiten_prompt(raiten_list, pref_hint="東京"):
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).strftime("%Y年%m月%d日")
    tomorrow_short = (now + timedelta(days=1)).strftime("%m月%d日")
    lines = "\n".join(f"  ・{r['talent_name']} → {r['hall_name']}" for r in raiten_list[:5])
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
- ハッシュタグ: #来店情報 #パチンコ #{pref_hint} と来店者名・店名
- ファンが行きたくなる熱量で書く"""

def build_event_prompt(analysis):
    return build_yokoku_prompt(analysis)
