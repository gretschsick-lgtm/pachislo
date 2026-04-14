import os, anthropic, tweepy
from datetime import datetime

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
    resp = _v2client().create_tweet(text=tweet_text, media_ids=media_ids)
    tweet_id = resp.data["id"]
    url = f"https://x.com/i/web/status/{tweet_id}"
    print(f"[poster] 投稿完了: {url}")
    return {"tweet_id": tweet_id, "url": url, "tweet_text": tweet_text, "has_image": bool(media_ids)}

def build_event_prompt(analysis):
    today = analysis["today"]
    tomorrow = analysis["tomorrow"]
    weekday = analysis["weekday"]
    stats = analysis["data_stats"]

    # アツいホール3店舗
    halls_txt = ""
    for i, h in enumerate(analysis["hot_halls"], 1):
        halls_txt += f"  {i}. {h['hall_name']}（過去{h['total_cnt']}回開催 / 直近30日{h['recent_cnt']}回）\n"
    if not halls_txt: halls_txt = "  （データ蓄積中）\n"

    # 明日のイベント
    tomorrow_txt = ""
    for e in analysis["tomorrow_events"]:
        tomorrow_txt += f"  ・{e['hall_name']} 「{e['event_name']}」\n"
    if not tomorrow_txt: tomorrow_txt = "  （なし）\n"

    # 今日のイベント
    today_txt = ""
    for e in analysis["today_events"]:
        today_txt += f"  ・{e['hall_name']} 「{e['event_name']}」\n"
    if not today_txt: today_txt = "  （なし）\n"

    # 曜日のアツいイベント
    weekday_txt = ""
    for e in analysis["weekday_hot"][:3]:
        weekday_txt += f"  ・{e['event_name']}（{e['cnt']}回）\n"
    if not weekday_txt: weekday_txt = "  （データ蓄積中）\n"

    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
過去データの分析から本日 {today}（{weekday}曜日）のアツい情報をツイートしてください。

【過去データから選んだアツいホールTOP3】
{halls_txt}
【本日のイベント】
{today_txt}
【明日 {tomorrow} のイベント】
{tomorrow_txt}
【{weekday}曜日によく開催されるアツいイベント】
{weekday_txt}
【データ蓄積】{stats['total_events']}件 / {stats['days_accumulated']}日分

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で読みやすく
- アツいホール3店舗を具体的に名前を出して紹介
- 明日のイベントがあれば必ず入れる
- ハッシュタグ4〜5個（#パチンコ #スロット #イベント情報 #今日のアツ台 #明日のイベント など）
- データが少ない場合も工夫して書く"""

def build_raiten_prompt(raiten_list):
    today = datetime.now().strftime("%Y年%m月%d日")
    lines = "\n".join(f"  ・{r['talent_name']} → {r['hall_name']}（{r.get('visit_date','')}）" for r in raiten_list[:5])
    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
本日 {today} の来店イベント情報をツイートしてください。

【本日の来店情報】
{lines}

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で華やかに
- 誰がどこに来るか明確に
- ハッシュタグ: #来店情報 #パチンコ #スロット と来店者名・店名
- ファンが行きたくなる熱量で書く"""
