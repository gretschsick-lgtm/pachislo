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
        print(f"[poster] メディアアップロード: {media.media_id}")
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
    weekday = analysis["weekday"]
    def fmt(items, key): return "\n".join(f"  ・{i[key]}（{i['cnt']}回）" for i in items) or "  （データ蓄積中）"
    upcoming_txt = "\n".join(f"  ・{u['hall_name']} 「{u['event_name']}」 {u['event_date']}" for u in analysis["upcoming"]) or "  （なし）"
    stats = analysis["data_stats"]
    return f"""あなたはパチンコ・パチスロ情報を発信するXアカウントです。
過去データの分析結果をもとに「本日 {today}（{weekday}曜日）のアツいイベント情報」を告知するツイートを日本語で1つ作成してください。

【{weekday}曜日によく開催されるアツいイベント】
{fmt(analysis["weekday_hot"],'event_name')}

【この時期に多いイベント】
{fmt(analysis["monthday_hot"],'event_name')}

【最近の人気イベントTop5】
{fmt(analysis["overall_hot"][:5],'event_name')}

【直近の注目予定】
{upcoming_txt}

【アクティブなホール】
{fmt(analysis["top_halls"][:3],'hall_name')}

【データ蓄積状況】{stats['total_events']}件 / {stats['days_accumulated']}日分

【ルール】
- ツイート本文のみ出力
- 280文字以内
- 絵文字で読みやすく
- 具体的なイベント名・ホール名を入れる
- ハッシュタグ4〜5個（#パチンコ #スロット #イベント情報 #今日のアツ台 など）
- 「本日」「今日」など時制を明確に
- データが少ない場合でも工夫して魅力的な文章にする"""

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
