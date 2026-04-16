import re, io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

def _get_font(size):
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
    for y in range(h):
        ratio = y / h
        r = int(20 + ratio * 30)
        g = int(0 + ratio * 5)
        b = int(0 + ratio * 5)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    gold = (212, 175, 55)
    draw.rectangle([0, 0, w-1, h-1], outline=gold, width=6)
    draw.rectangle([10, 10, w-11, h-11], outline=(180, 140, 30), width=2)
    draw.rectangle([0, 0, w, 80], fill=(30, 10, 0))
    draw.line([(0, 80), (w, 80)], fill=gold, width=3)
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

    f_title = _get_font(44)
    f_pref  = _get_font(32)
    f_label = _get_font(28)
    f_hall  = _get_font(32)
    f_small = _get_font(22)
    f_date  = _get_font(28)

    _draw_text_shadow(draw, (20, 15), "🎰 PACHISLOT INFO", f_pref, gold)
    _draw_text_shadow(draw, (W-280, 20), date_str, f_date, light_gold)

    _draw_text_shadow(draw, (W//2 - 280, 92), title, f_title, white)

    draw.rounded_rectangle([20, 90, 160, 140], radius=10, fill=red_bright)
    _draw_text_shadow(draw, (30, 98), f"📍{pref}", f_label, white, offset=1)

    draw.line([(20, 158), (W-20, 158)], fill=gold, width=2)
    _draw_text_shadow(draw, (20, 168), "🏆 注目ホール TOP3", f_label, light_gold)

    medals = ["🥇", "🥈", "🥉"]
    colors = [gold, (192,192,192), (205,127,50)]

    for i, (hall, evname) in enumerate(zip(halls[:3], event_names[:3])):
        y = 210 + i * 100
        draw.rounded_rectangle([20, y, W-20, y+88], radius=8,
                                fill=(40+i*5, 15, 10), outline=colors[i], width=2)
        hall_short = hall[:22] + "…" if len(hall) > 22 else hall
        _draw_text_shadow(draw, (35, y+8), f"{medals[i]} {hall_short}", f_hall, white)
        evname_short = evname[:30] + "…" if len(evname) > 30 else evname
        _draw_text_shadow(draw, (60, y+50), f"📌 {evname_short}", f_small, light_gold)

    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    _draw_text_shadow(draw, (20, H-45), f"⚡ 自動収集データより生成  {now_str}", f_small, gold)
    _draw_text_shadow(draw, (W-220, H-45), "#パチスロ #パチンコ", f_small, (150, 150, 150))

    return img

def _save(img, prefix, name):
    slug = re.sub(r"[^\w]", "_", name)[:20]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{prefix}_{slug}_{ts}.jpg"
    img.save(path, "JPEG", quality=92)
    print(f"[images] 保存: {path}")
    return str(path)

def get_event_image(event, analysis=None, pref_hint="東京"):
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m月%d日")
        tomorrow_iso = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        halls = []
        evnames = []

        if analysis:
            # ①明日のイベントを優先（実際のイベント名を使う）
            for e in analysis.get("tomorrow_events", []):
                if e.get("hall_name") and e.get("event_date","") == tomorrow_iso:
                    halls.append(e.get("hall_name", ""))
                    evnames.append(e.get("event_name", "イベント開催"))

            # ②足りない分はhot_hallsで補完（イベント名付き）
            for h in analysis.get("hot_halls", []):
                if len(halls) >= 3:
                    break
                hname = h.get("hall_name", "")
                if hname and hname not in halls:
                    halls.append(hname)
                    # hot_hallsに対応する明日のイベント名を探す
                    ev_name = "全台系/取材イベント"
                    for e in analysis.get("tomorrow_events", []):
                        if e.get("hall_name") == hname:
                            ev_name = e.get("event_name", ev_name)
                            break
                    evnames.append(ev_name)

        if not halls:
            halls = [event.get("hall_name", "注目ホール")]
            evnames = [event.get("event_name", "イベント開催")]

        while len(halls) < 3:
            halls.append("—")
            evnames.append("情報収集中")

        img = _make_image(
            title=f"明日{tomorrow}の激アツ予告🔥",
            date_str=tomorrow,
            pref=pref_hint,
            halls=halls[:3],
            event_names=evnames[:3],
        )
        return _save(img, "event", f"{pref_hint}_{event.get('event_name','event')}")
    except Exception as e:
        print(f"[images] 生成失敗: {e}")
        return None

def get_raiten_image(raiten, pref_hint="東京"):
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m月%d日")
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
