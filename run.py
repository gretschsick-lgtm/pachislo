import re, io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

def _get_font(size):
    """フォントを取得（システムフォントにフォールバック）"""
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def _draw_bg(draw, w, h):
    """赤・金グラデーション風背景"""
    for y in range(h):
        ratio = y / h
        r = int(20 + ratio * 30)
        g = int(0 + ratio * 5)
        b = int(0 + ratio * 5)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 金色の装飾ライン
    gold = (212, 175, 55)
    draw.rectangle([0, 0, w-1, h-1], outline=gold, width=6)
    draw.rectangle([10, 10, w-11, h-11], outline=(180, 140, 30), width=2)

    # 上部の金帯
    draw.rectangle([0, 0, w, 80], fill=(30, 10, 0))
    draw.line([(0, 80), (w, 80)], fill=gold, width=3)

    # 下部の金帯
    draw.rectangle([0, h-60, w, h], fill=(30, 10, 0))
    draw.line([(0, h-60), (w, h-60)], fill=gold, width=3)

def _draw_text_shadow(draw, pos, text, font, fill, shadow_fill=(0,0,0), offset=2):
    x, y = pos
    draw.text((x+offset, y+offset), text, font=font, fill=shadow_fill)
    draw.text((x, y), text, font=font, fill=fill)

def _make_image(title, date_str, pref, halls, event_names):
    W, H = 1200, 675
    img = Image.new("RGB", (W, H), (15, 0, 0))
    draw = ImageDraw.Draw(img)

    _draw_bg(draw, W, H)

    gold = (212, 175, 55)
    white = (255, 255, 255)
    red_bright = (255, 60, 60)
    light_gold = (255, 230, 100)

    # フォント
    f_title = _get_font(48)
    f_pref  = _get_font(36)
    f_label = _get_font(28)
    f_hall  = _get_font(34)
    f_small = _get_font(22)
    f_date  = _get_font(30)

    # ヘッダー部分
    _draw_text_shadow(draw, (20, 15), "🎰 PACHISLOT INFO", f_pref, gold)
    _draw_text_shadow(draw, (W-260, 20), date_str, f_date, light_gold)

    # タイトル
    _draw_text_shadow(draw, (W//2 - 300, 95), title, f_title, white)

    # 都道府県バッジ
    draw.rounded_rectangle([20, 95, 160, 145], radius=10, fill=red_bright)
    _draw_text_shadow(draw, (35, 103), f"📍{pref}", f_label, white, offset=1)

    # 区切り線
    draw.line([(20, 160), (W-20, 160)], fill=gold, width=2)

    # ホールTOP3
    _draw_text_shadow(draw, (20, 170), "🏆 注目ホール TOP3", f_label, light_gold)

    medals = ["🥇", "🥈", "🥉"]
    colors = [gold, (192,192,192), (205,127,50)]
    for i, (hall, evname) in enumerate(zip(halls[:3], event_names[:3])):
        y = 215 + i * 100
        # ホールカード背景
        draw.rounded_rectangle([20, y, W-20, y+85], radius=8,
                                fill=(40+i*5, 15, 10), outline=colors[i], width=2)
        # メダル＋ホール名
        _draw_text_shadow(draw, (35, y+10), f"{medals[i]} {hall}", f_hall, white)
        # イベント名
        evname_short = evname[:25] + "…" if len(evname) > 25 else evname
        _draw_text_shadow(draw, (60, y+52), evname_short, f_small, light_gold)

    # フッター
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    _draw_text_shadow(draw, (20, H-45), f"⚡ 自動収集データより生成  {now_str}", f_small, gold)
    _draw_text_shadow(draw, (W-200, H-45), "#パチスロ #パチンコ", f_small, (150, 150, 150))

    return img

def _save(img, prefix, name):
    slug = re.sub(r"[^\w]", "_", name)[:20]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{prefix}_{slug}_{ts}.jpg"
    img.save(path, "JPEG", quality=92)
    print(f"[images] 保存: {path}")
    return str(path)

def get_event_image(event, analysis=None, pref_hint="東京"):
    """イベント予告用画像を生成"""
    try:
        now = datetime.now()
        from datetime import timedelta
        tomorrow = (now + timedelta(days=1)).strftime("%m月%d日")
        date_str = tomorrow

        halls = []
        evnames = []

        if analysis:
            for h in analysis.get("hot_halls", [])[:3]:
                halls.append(h.get("hall_name", ""))
                evnames.append(f"過去{h.get('total_cnt',0)}回開催")
            for e in analysis.get("tomorrow_events", [])[:3]:
                if e.get("hall_name") not in halls:
                    halls.append(e.get("hall_name", ""))
                    evnames.append(e.get("event_name", "イベント開催"))

        if not halls:
            halls = [event.get("hall_name", "注目ホール")]
            evnames = [event.get("event_name", "イベント開催")]

        while len(halls) < 3:
            halls.append("—")
            evnames.append("情報収集中")

        img = _make_image(
            title=f"明日{date_str}の激アツ予告🔥",
            date_str=date_str,
            pref=pref_hint,
            halls=halls[:3],
            event_names=evnames[:3],
        )
        return _save(img, "event", f"{pref_hint}_{event.get('event_name','event')}")
    except Exception as e:
        print(f"[images] 生成失敗: {e}")
        return None

def get_raiten_image(raiten, pref_hint="東京"):
    """来店予告用画像を生成"""
    try:
        from datetime import timedelta
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%m月%d日")

        talent = raiten.get("talent_name", "演者")
        hall = raiten.get("hall_name", "")

        img = _make_image(
            title=f"🌟来店情報🌟",
            date_str=tomorrow,
            pref=pref_hint,
            halls=[hall, "—", "—"],
            event_names=[f"{talent} 来店！", "", ""],
        )
        return _save(img, "raiten", raiten.get("talent_name", "raiten"))
    except Exception as e:
        print(f"[images] 来店画像生成失敗: {e}")
        return None
