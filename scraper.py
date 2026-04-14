import os, re, time, tweepy
from datetime import datetime, date, timedelta

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
    return any(k in text for k in ["イベント","来店","全台","旧イベ","設定","特日","ガチ日","周年","記念","アツ","熱","取材","狙い","推し","快便","明日の","月イチ","ゾロ目","新装","特定日","抽選"])

def _is_raiten(text):
    return any(k in text for k in ["来店","来場","ゲスト","タレント","プロ","選手","取材","収録","実践来店"])

def _extract_event_name(text):
    for pat in [r"【([^】]{2,20})】", r"「([^」]{2,20})」",
                r"(全台[^\s　。！]{0,10})", r"(旧イベ[^\s　。！]{0,10})",
                r"(周年[^\s　。！]{0,10})", r"(月イチ[^\s　。！]{0,10})"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return text[:20].strip()

def _extract_talent(text):
    for pat in [r"([^\s　、。！]+(?:選手|さん|プロ|氏))(?:が|の)?(?:来店|来場|実践)",
                r"(?:来店|来場)[：:]\s*([^\s　\n！。、]{2,15})",
                r"【来店】([^\s　\n！。【】]{2,15})",
                r"(いそまる|よしき|じゃんじゃん|れんじろう|るいべえ|ガール)"]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return "(来店者不明)"

def _extract_hall(text):
    for pat in [
        r"(マルハン[^\s　。！\n、]{1,15})", r"(ピーアーク[^\s　。！\n、]{1,15})",
        r"(ガーデン[^\s　。！\n、]{1,10})", r"(キコーナ[^\s　。！\n、]{1,10})",
        r"(楽園[^\s　。！\n、]{1,10})", r"(ダイナム[^\s　。！\n、]{1,10})",
        r"(エスパス[^\s　。！\n、]{1,10})", r"(アビバ[^\s　。！\n、]{1,10})",
        r"(ジアス[^\s　。！\n、]{1,10})", r"(UNO[^\s　。！\n、]{1,10})",
        r"(123[^\s　。！\n、]{1,10})", r"(メッセ[^\s　。！\n、]{1,10})",
        r"(アイランド[^\s　。！\n、]{1,10})", r"(エクスアリーナ[^\s　。！\n、]{1,10})",
        r"(プレサス[^\s　。！\n、]{1,10})", r"(パラッツォ[^\s　。！\n、]{1,10})",
        r"(ニラク[^\s　。！\n、]{1,10})", r"(PIA[^\s　。！\n、]{1,10})",
        r"(Dステ[^\s　。！\n、]{1,10})", r"(第一プラザ[^\s　。！\n、]{1,10})",
        r"(ラカータ[^\s　。！\n、]{1,10})", r"(ガイア[^\s　。！\n、]{1,10})",
        r"(ベルシティ[^\s　。！\n、]{1,10})", r"(ベガスベガス[^\s　。！\n、]{1,10})",
    ]:
        m = re.search(pat, text)
        if m: return m.group(1).strip()
    return ""

# ════════════════════════════════════════════
# 全関東共通（まとめ・情報発信系）
# ════════════════════════════════════════════
COMMON_ACCOUNTS = [
    "paapsaward",        # PAA：毎日全国の来店・取材情報まとめ（超優良）
    "chanoma_777",       # 茶の間：来店・取材情報毎日まとめ
    "slot_channel_",     # スロちゃん：関東全域情報まとめ
    "touslot",           # 東スロ：東京・神奈川・埼玉予想まとめ
    "slo1_tyousataiZ",   # スロイベ調査隊Z関東
    "kachigumimax",      # Makotoパチスロ案内人
    "slotdekatu",        # ペカ男爵
    "slotterguild",      # スロッターギルド
    "ibentoan",          # 朧：スロットイベント案内
    "ainavipachislot",   # AIナビ関東版
    "MH_Tencho0220",     # 元店長いっぺー@マルハン
]

# ════════════════════════════════════════════
# 東京専用
# ════════════════════════════════════════════
TOKYO_ACCOUNTS = [
    "endo1maruhan",      # マルハン新宿東宝ビル店員
    "999999Q9Q",         # 東京マルハン情報
    "slot_ogikiti",      # 荻吉@スロ（東京中心）
    "pachislotenchou",   # マルハン店長系
    "dynamjp",           # ダイナム公式
]

# ════════════════════════════════════════════
# 神奈川専用
# ════════════════════════════════════════════
KANAGAWA_ACCOUNTS = [
    "karasuro_7",        # カラスロ：神奈川の明日のアツい店
    "1_take6",           # Take6：神奈川ホール調査・予想
    "maruhan_yokoham",   # マルハンメガシティ横浜町田公式
]

# ════════════════════════════════════════════
# 埼玉専用
# ════════════════════════════════════════════
SAITAMA_ACCOUNTS = [
    "kata_sainokuni",    # 塊：埼玉・東京・群馬の狙いや傾向
    "ikechinpachislo",   # いけちん：関東パチスロデータまとめ
]

# 地域コードとアカウントのマッピング
ACC
