# -*- coding: utf-8 -*-
"""Ezan Vakti - ekranın köşesinde her zaman üstte duran küçük namaz vakti sayacı.

Vakitler Diyanet İşleri Başkanlığı'nın sitesinden (namazvakitleri.diyanet.gov.tr) alınır.
Sol tık: ayrıntıları aç/kapat, sürükle: taşı (ekran kenarlarına yapışır),
Ctrl + fare tekerleği: boyut, sağ tık: menü (ayarlar, çıkış).
"""
import ctypes
import ctypes.wintypes as wt
import datetime as dt
import html
import json
import math
import os
import queue
import re
import sys
import threading
import urllib.parse
import urllib.request
import wave
import winreg
import winsound
from array import array
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

APP_NAME = "EzanVakti"
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_FILE = os.path.join(DATA_DIR, "ayarlar.json")
CACHE_FILE = os.path.join(DATA_DIR, "vakitler.json")
SES_FILE = os.path.join(DATA_DIR, "calan_ses.wav")

BASE_URL = "https://namazvakitleri.diyanet.gov.tr"
TURKIYE_ID = 2
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EzanVakti/1.1"}

VAKITLER = ["İmsak", "Güneş", "Öğle", "İkindi", "Akşam", "Yatsı"]
VAKIT_EN = {"İmsak": "Fajr", "Güneş": "Sunrise", "Öğle": "Dhuhr",
            "İkindi": "Asr", "Akşam": "Maghrib", "Yatsı": "Isha"}
YONELME = {"İmsak": "İmsaka", "Güneş": "Güneşe", "Öğle": "Öğleye",
           "İkindi": "İkindiye", "Akşam": "Akşama", "Yatsı": "Yatsıya"}
AYLAR = {"Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
         "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12}

DILLER = {"tr": ("Türkçe", "Türkçe"), "en": ("English", "English")}
TEMALAR = {
    "Koyu":     {"bg": "#1e1e1e", "fg": "#f2f2f2", "sub": "#9a9a9a", "warn": "#ffb020"},
    "Açık":     {"bg": "#f7f7f7", "fg": "#1e1e1e", "sub": "#6a6a6a", "warn": "#d05a00"},
    "Yeşil":    {"bg": "#0f3d2e", "fg": "#eafff4", "sub": "#8fc7ad", "warn": "#ffd166"},
    "Lacivert": {"bg": "#14213d", "fg": "#f1f4ff", "sub": "#9aa6c7", "warn": "#fca311"},
}
TEMA_ADLARI = {"Koyu": ("Koyu", "Dark"), "Açık": ("Açık", "Light"),
               "Yeşil": ("Yeşil", "Green"), "Lacivert": ("Lacivert", "Navy")}
SAYDAMLIK = {"Opak": 1.0, "Yarı saydam": 0.75, "Çok saydam": 0.5, "Saydam (sadece yazı)": None}
SAYDAMLIK_ADLARI = {"Opak": ("Opak", "Opaque"), "Yarı saydam": ("Yarı saydam", "Semi-transparent"),
                    "Çok saydam": ("Çok saydam", "Very transparent"),
                    "Saydam (sadece yazı)": ("Saydam (sadece yazı)", "Transparent (text only)")}
ESKI_BOYUTLAR = {"Küçük": 10, "Orta": 13, "Büyük": 17, "Çok büyük": 22}
BOYUT_MIN, BOYUT_MAX = 8, 40
# ses kimliği: (Türkçe ad, İngilizce ad) - dahili sesler uygulama içinde üretilir
SESLER = {
    "zil":    ("Yumuşak zil", "Soft chime"),
    "ding":   ("Tek ding", "Single ding"),
    "bip":    ("Üç kısa bip", "Three short beeps"),
    "hicaz":  ("Hicaz ezgisi (ney)", "Hijaz melody (ney)"),
    "ussak":  ("Uşşak ezgisi (ney)", "Ushshaq melody (ney)"),
    "rast":   ("Rast ezgisi (ney)", "Rast melody (ney)"),
    "custom": ("Kendi ses dosyam (.wav)", "My own sound file (.wav)"),
}
ONIZLEME_AYARLARI = ("style", "expanded", "theme", "opacity", "size")
STILLER = {"kart": ("Kart", "Card"), "hap": ("Hap", "Pill"), "klasik": ("Klasik", "Classic")}
MODLAR = {"compact": ("Kompakt (sadece kalan süre)", "Compact (time left only)"),
          "extended": ("Genişletilmiş (kalan süre + tüm vakitler)", "Extended (time left + all times)")}
SNAP = 24  # kenara bu kadar pikselden yakınsa yapışır
SURUKLEME_ESIGI = 8  # fare bundan az oynarsa sürükleme sayılmaz
BASILI_TUTMA_MS = 800  # olduğu yerde bu kadar basılı tutunca tüm vakitler görünür

METINLER = {
    "app": ("Ezan Vakti", "Prayer Times"),
    "menu_settings": ("Ayarlar...", "Settings..."),
    "menu_toggle": ("Genişletilmiş mod (tüm vakitler)", "Extended mode (all times)"),
    "mode": ("Görünüm modu:", "View mode:"),
    "mode_hint": ("Kompakt modda basılı tutunca tüm vakitler geçici olarak görünür",
                  "In compact mode, press and hold to peek at all times"),
    "tab_general": ("Genel", "General"),
    "tab_alarm": ("Sesli uyarı", "Sound alert"),
    "tab_look": ("Görünüm", "Appearance"),
    "style": ("Stil:", "Style:"),
    "ok": ("Tamam", "OK"),
    "apply": ("Uygula", "Apply"),
    "saved": ("Kaydedildi ✓", "Saved ✓"),
    "menu_refresh": ("Vakitleri şimdi yenile", "Refresh times now"),
    "menu_quit": ("Çıkış", "Quit"),
    "choose_loc": ("Konum seçin (sağ tık)", "Choose location (right-click)"),
    "loading_times": ("Vakitler alınıyor...", "Loading times..."),
    "fetch_err": ("Vakitler alınamadı:", "Could not get prayer times:"),
    "settings_title": ("Ezan Vakti - Ayarlar", "Prayer Times - Settings"),
    "location": (" Konum ", " Location "),
    "province": ("İl:", "Province:"),
    "district": ("İlçe:", "District:"),
    "loading": ("Yükleniyor...", "Loading..."),
    "net_err": ("İnternet hatası", "Connection error"),
    "states_err": ("İl listesi alınamadı:", "Could not get province list:"),
    "pick_state": ("Önce il seçin", "Choose a province first"),
    "alarm": (" Sesli uyarı ", " Sound alert "),
    "alarm_a": ("Vakte", "Alert"),
    "alarm_b": ("dakika kala sesli uyar", "minutes before prayer time"),
    "alarm_at_time": ("Vakit girdiğinde de çal", "Also play when the time comes"),
    "which": ("Hangi vakitlerde:", "For which prayers:"),
    "sound": ("Ses:", "Sound:"),
    "listen": ("Dinle", "Play"),
    "volume": ("Ses seviyesi:", "Volume:"),
    "pick_wav": ("Ses dosyası seçin", "Choose a sound file"),
    "wav_type": ("WAV ses dosyası", "WAV sound file"),
    "appearance": (" Görünüm ", " Appearance "),
    "color": ("Renk:", "Color:"),
    "opacity": ("Saydamlık:", "Transparency:"),
    "size": ("Boyut:", "Size:"),
    "size_hint": ("Pencere üzerinde Ctrl + fare tekerleği ile de değişir",
                  "Also Ctrl + mouse wheel over the window"),
    "language": ("Dil / Language:", "Dil / Language:"),
    "other": (" Diğer ", " Other "),
    "autostart": ("Windows açılınca otomatik başlat", "Start automatically with Windows"),
    "cancel": ("İptal", "Cancel"),
    "save": ("Kaydet", "Save"),
    "need_loc": ("Lütfen il ve ilçe seçin.", "Please choose a province and district."),
    "bad_min": ("Dakika 1 ile 120 arasında olmalı.", "Minutes must be between 1 and 120."),
    "autostart_err": ("Otomatik başlatma ayarlanamadı:", "Could not set auto start:"),
}

VARSAYILAN_AYARLAR = {
    "language": "tr",
    "state_id": None, "state_name": "",
    "district_id": None, "district_name": "", "district_url": "",
    "alarm_on": True, "alarm_minutes": 10, "alarm_at_time": False,
    "alarm_vakitler": ["İmsak", "Öğle", "İkindi", "Akşam", "Yatsı"],
    "sound": "zil", "sound_file": "", "volume": 80,
    "style": "kart", "theme": "Koyu", "opacity": "Yarı saydam", "size": 13,
    "x": None, "y": None, "snap_x": "right", "snap_y": "bottom",
    "expanded": False, "autostart": False,
}


def eski_ayarlari_cevir(cfg):
    """Önceki sürümün ayar dosyasını bu sürüme uyarlar."""
    if not isinstance(cfg["size"], int):
        cfg["size"] = ESKI_BOYUTLAR.get(cfg["size"], 13)
    if cfg["sound"] == "Kendi ses dosyam (.wav)":
        cfg["sound"] = "custom"
    if cfg["sound"] not in SESLER:
        cfg["sound"] = "zil"
    if cfg["style"] not in STILLER:
        cfg["style"] = "kart"
    if cfg["theme"] not in TEMALAR:
        cfg["theme"] = "Koyu"
    if cfg["opacity"] not in SAYDAMLIK:
        cfg["opacity"] = "Yarı saydam"
    if cfg["language"] not in DILLER:
        cfg["language"] = "tr"
    return cfg


# ---------------------------------------------------------------- dosyalar

def load_json(path, default):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------- Diyanet

def http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def get_reg_list(**params):
    params.update(CountryId=TURKIYE_ID, Culture="tr-TR")
    url = BASE_URL + "/tr-TR/home/GetRegList?" + urllib.parse.urlencode(params)
    return json.loads(http_get(url))


def get_iller():
    data = get_reg_list(ChangeType="country")
    return [(s["SehirAdi"], s["SehirID"]) for s in data["StateList"]]


def get_ilceler(state_id):
    data = get_reg_list(ChangeType="state", StateId=state_id)
    return [(d["IlceAdi"], d["IlceID"], d["IlceUrl"]) for d in data["StateRegionList"]]


SATIR_RE = re.compile(
    r"<tr>\s*<td>\s*(\d{1,2})\s+(\w+)\s+(\d{4})[^<]*</td>\s*<td>[^<]*</td>"
    r"((?:\s*<td>\s*\d{1,2}:\d{2}\s*</td>){6})")


def get_vakitler(district_url):
    """Diyanet sayfasındaki tablodan {"2026-10-31": ["06:01", ...6 vakit], ...} döner."""
    page = html.unescape(http_get(BASE_URL + district_url))
    days = {}
    for m in SATIR_RE.finditer(page):
        ay = AYLAR.get(m.group(2))
        if not ay:
            continue
        tarih = dt.date(int(m.group(3)), ay, int(m.group(1)))
        days[tarih.isoformat()] = re.findall(r"\d{1,2}:\d{2}", m.group(4))
    if not days:
        raise ValueError("Diyanet sayfasında vakit tablosu bulunamadı.")
    return days


def onceki_vakit(days, now):
    """Girmiş olan son vaktin zamanı (ilerleme çubuğu için) ya da None."""
    for gun in (0, -1):
        tarih = now.date() + dt.timedelta(days=gun)
        saatler = days.get(tarih.isoformat())
        if not saatler:
            continue
        for saat in reversed(saatler):
            h, m = map(int, saat.split(":"))
            zaman = dt.datetime.combine(tarih, dt.time(h, m))
            if zaman <= now:
                return zaman
    return None


def siradaki_vakit(days, now):
    """(vakit adı, vakit zamanı) ya da veri yoksa None."""
    for gun in range(2):
        tarih = now.date() + dt.timedelta(days=gun)
        saatler = days.get(tarih.isoformat())
        if not saatler:
            continue
        for ad, saat in zip(VAKITLER, saatler):
            h, m = map(int, saat.split(":"))
            zaman = dt.datetime.combine(tarih, dt.time(h, m))
            if zaman > now:
                return ad, zaman
    return None


# ---------------------------------------------------------------- çizim yardımcıları

def tr_buyuk(metin):
    """Türkçe büyük harf: i → İ, ı → I."""
    return metin.replace("i", "İ").replace("ı", "I").upper()


def _rgb(renk):
    return tuple(int(renk[i:i + 2], 16) for i in (1, 3, 5))


def renk_karistir(a, b, oran):
    """a rengini oran kadar b rengine yaklaştırır."""
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * oran) for x, y in zip(_rgb(a), _rgb(b)))


def anahtar_renk(renk):
    """Saydam yapılacak renk: verilen renkten 1 birim farklı (kenar yumuşatması o renge karışsın)."""
    r, g, b = _rgb(renk)
    return "#%02x%02x%02x" % (r, g, b + 1 if b < 255 else b - 1)


HILAL_IC_ORAN, HILAL_KAYMA, HILAL_YON = 0.80, 0.50, -0.45  # iç dairenin boyu, kayması, yönü


def hilal_icinde(x, y, R):
    """(x, y) noktası, merkezi (0, 0) ve yarıçapı R olan sağa bakan hilalin içinde mi?"""
    ox = R * HILAL_KAYMA * math.cos(HILAL_YON)
    oy = R * HILAL_KAYMA * math.sin(HILAL_YON)
    r = R * HILAL_IC_ORAN
    return x * x + y * y <= R * R and (x - ox) ** 2 + (y - oy) ** 2 > r * r


def hilal_resmi(R, renk, zemin):
    """Kenarları yumuşatılmış hilal resmi (dışı saydam). Kenarlar zemin rengine karışır."""
    boy = int(math.ceil(2 * R)) + 2
    merkez = boy / 2
    (r1, g1, b1), (r2, g2, b2) = _rgb(renk), _rgb(zemin)
    img = tk.PhotoImage(width=boy, height=boy)
    satirlar, bos = [], []
    ornek = 4  # her pikselde 4x4 örnek
    for py in range(boy):
        satir = []
        for px in range(boy):
            dolu = sum(hilal_icinde(px + (i + 0.5) / ornek - merkez, py + (j + 0.5) / ornek - merkez, R)
                       for i in range(ornek) for j in range(ornek)) / ornek ** 2
            if dolu == 0:
                bos.append((px, py))
            satir.append("#%02x%02x%02x" % (round(r2 + (r1 - r2) * dolu), round(g2 + (g1 - g2) * dolu),
                                            round(b2 + (b1 - b2) * dolu)))
        satirlar.append("{" + " ".join(satir) + "}")
    img.put(" ".join(satirlar))
    for px, py in bos:
        img.transparency_set(px, py, True)
    return img


def yuvarlak_kutu(canvas, x1, y1, x2, y2, r, **kw):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    noktalar = []
    # her köşe için çeyrek daire üzerindeki noktalar
    for cx, cy, bas in ((x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0),
                        (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)):
        for i in range(9):
            a = math.radians(bas + i * 90 / 8)
            noktalar += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return canvas.create_polygon(noktalar, **kw)


# ---------------------------------------------------------------- Windows

def kaynak_yolu(dosya):
    """Uygulamayla gelen dosyanın yolu (.exe içinde de, .py olarak çalışırken de)."""
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), dosya)


def tek_kopya_mi():
    """Uygulama zaten açıksa False döner."""
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\EzanVaktiTekKopya")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def baslangic_komutu():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return f'"{pythonw}" "{os.path.abspath(__file__)}"'


def windows_ile_baslat(acik):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if acik:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, baslangic_komutu())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


_user32 = ctypes.windll.user32
_user32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
_user32.MonitorFromPoint.restype = wt.HMONITOR
_user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.POINTER(MONITORINFO)]


def calisma_alani(x, y):
    """(x, y) noktasına en yakın ekranın görev çubuğu hariç alanı: (sol, üst, sağ, alt)."""
    mon = _user32.MonitorFromPoint(wt.POINT(int(x), int(y)), 2)  # MONITOR_DEFAULTTONEAREST
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    _user32.GetMonitorInfoW(mon, ctypes.byref(mi))
    r = mi.rcWork
    return r.left, r.top, r.right, r.bottom


# ---------------------------------------------------------------- ses
# Windows'un ses düzeni "Ses yok" olsa bile çalsın diye sesler dosyadan çalınır.

_ses_kilit = threading.Lock()


HZ = 22050


def _pcm(ornekler):
    """-1..1 arası örnekleri 16 bit WAV verisine çevirir."""
    tepe = max(1e-9, max(abs(s) for s in ornekler))
    return (1, 2, HZ), array("h", (int(s / tepe * 29000) for s in ornekler)).tobytes()


def _yanki(ornekler, oran=0.28):
    """Küçük bir oda yankısı: sesi daha yumuşak ve dolgun yapar."""
    out = ornekler + [0.0] * int(HZ * 0.6)
    for gecikme, kazanc in ((0.083, oran), (0.127, oran * 0.8), (0.191, oran * 0.6)):
        d = int(HZ * gecikme)
        for i in range(d, len(out)):
            out[i] += out[i - d] * kazanc
    return out


def _can_notasi(frekans, sure, sonum=3.2):
    """Zil/çan benzeri tek nota: hızlı başlar, yavaşça söner."""
    ornekler = []
    for i in range(int(HZ * sure)):
        t = i / HZ
        zarf = math.exp(-sonum * t) * min(1.0, t * 200)
        ornekler.append((math.sin(2 * math.pi * frekans * t)
                         + 0.35 * math.sin(4 * math.pi * frekans * t)
                         + 0.12 * math.sin(6 * math.pi * frekans * t)) * zarf)
    return ornekler


def ses_zil():
    return _pcm(_can_notasi(659.25, 0.9) + _can_notasi(523.25, 1.6))


def ses_ding():
    return _pcm(_yanki(_can_notasi(880.0, 1.8, sonum=2.4), 0.18))


def ses_bip():
    ornekler = []
    for _ in range(3):
        for i in range(int(HZ * 0.13)):
            t = i / HZ
            zarf = min(1.0, t * 300, (0.13 - t) * 300)
            ornekler.append(math.sin(2 * math.pi * 988 * t) * zarf)
        ornekler += [0.0] * int(HZ * 0.11)
    return _pcm(ornekler)


def _ney_melodisi(kok, perdeler, ezgi, vurus=0.36):
    """Ney benzeri yumuşak bir tonla makam ezgisi çalar.

    kok: durak perdesinin frekansı, perdeler: makam dizisi (sent cinsinden),
    ezgi: [(perde sırası, vuruş sayısı), ...]
    """
    import random
    rnd = random.Random(7)
    ornekler = []
    faz = 0.0
    onceki = None
    for sira, vurus_sayisi in ezgi:
        hedef = kok * 2 ** (perdeler[sira] / 1200)
        baslangic = onceki or hedef
        n = int(HZ * vurus * vurus_sayisi)
        for i in range(n):
            t = i / HZ
            # perdeler arası yumuşak geçiş (glissando) ve hafif titreşim (vibrato)
            kayma = min(1.0, t / 0.06)
            f = baslangic + (hedef - baslangic) * kayma
            f *= 1 + 0.004 * math.sin(2 * math.pi * 5.2 * t) * min(1.0, t / 0.25)
            faz += 2 * math.pi * f / HZ
            zarf = min(1.0, t / 0.05, (n / HZ - t) / 0.04 + 0.35)
            v = math.sin(faz) + 0.22 * math.sin(2 * faz) + 0.07 * math.sin(3 * faz)
            v += (rnd.random() - 0.5) * 0.05  # nefes sesi
            ornekler.append(v * zarf)
        onceki = hedef
    son = int(HZ * 0.25)  # yumuşak bitiş
    for i in range(son):
        ornekler[-son + i] *= 1 - i / son
    return _pcm(_yanki(ornekler))


# Makam dizileri (sent): Türk müziğindeki koma aralıklarına yakın değerler
HICAZ = [0, 113, 384, 498, 702, 792, 996, 1200]
USSAK = [0, 165, 294, 498, 702, 792, 996, 1200]
RAST = [0, 204, 384, 498, 702, 906, 1086, 1200]


def ses_hicaz():
    return _ney_melodisi(293.66, HICAZ, [
        (0, .5), (2, .5), (3, .5), (4, 1.5), (3, .5), (2, .5), (1, .5), (0, 2)], vurus=0.28)


def ses_ussak():
    return _ney_melodisi(329.63, USSAK, [
        (3, .5), (2, .5), (1, .5), (2, .5), (3, 1.5), (2, .5), (1, .5), (0, 2)], vurus=0.28)


def ses_rast():
    return _ney_melodisi(392.0, RAST, [
        (4, .5), (3, .5), (2, .5), (3, .5), (4, 1.5), (2, .5), (1, .5), (0, 2)], vurus=0.28)


_uretilen = {}


def dahili_ses(kimlik):
    """Dahili sesi bir kez üretir, sonra hafızadan verir."""
    if kimlik not in _uretilen:
        _uretilen[kimlik] = SES_URETICILER.get(kimlik, ses_zil)()
    return _uretilen[kimlik]


SES_URETICILER = {"zil": ses_zil, "ding": ses_ding, "bip": ses_bip,
                  "hicaz": ses_hicaz, "ussak": ses_ussak, "rast": ses_rast}


def sesi_kis(genislik, veri, carpan):
    if genislik == 2:
        a = array("h")
        a.frombytes(veri[:len(veri) // 2 * 2])
        return array("h", (int(s * carpan) for s in a)).tobytes()
    if genislik == 1:
        return bytes(int((b - 128) * carpan) + 128 for b in veri)
    return veri


def _ses_cal(sound, sound_file, volume):
    yol = sound_file if sound == "custom" else None
    try:
        if yol and os.path.exists(yol):
            with wave.open(yol, "rb") as w:
                bicim = (w.getnchannels(), w.getsampwidth(), w.getframerate())
                veri = w.readframes(w.getnframes())
        else:
            bicim, veri = dahili_ses(sound)
    except (wave.Error, EOFError, OSError):
        # okunamayan (sıkıştırılmış vb.) wav: ses seviyesi ayarlanmadan çal
        winsound.PlaySound(yol, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return
    veri = sesi_kis(bicim[1], veri, (max(0, min(volume, 100)) / 100) ** 2)
    with _ses_kilit:
        winsound.PlaySound(None, 0)  # çalan sesi durdur, dosya boşalsın
        os.makedirs(DATA_DIR, exist_ok=True)
        with wave.open(SES_FILE, "wb") as w:
            w.setnchannels(bicim[0])
            w.setsampwidth(bicim[1])
            w.setframerate(bicim[2])
            w.writeframes(veri)
        winsound.PlaySound(SES_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC)


def ses_cal(sound, sound_file, volume):
    def calistir():
        try:
            _ses_cal(sound, sound_file, volume)
        except Exception:
            winsound.Beep(880, 400)
    threading.Thread(target=calistir, daemon=True).start()


# ---------------------------------------------------------------- ana pencere

class EzanVakti:
    def __init__(self):
        self.cfg = eski_ayarlari_cevir(dict(VARSAYILAN_AYARLAR, **load_json(CONFIG_FILE, {})))
        self.cache = load_json(CACHE_FILE, {"district_id": None, "days": {}, "fetched": ""})
        self.q = queue.Queue()
        self.fetching = False
        self.last_attempt = None
        self.fired = set()
        self.last_target = None
        self.settings = None
        self.tick_count = 0
        self.dragging = False
        self.peeking = False  # kompakt modda basılı tutarken geçici genişletme
        self.last_view = None
        self.fonts = {}

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        # Her şey bu tuvale çizilir; tuvalin zemin rengi saydam yapılır,
        # böylece yuvarlak köşeler ve "sadece yazı" görünümü mümkün olur.
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.canvas.pack()
        ikon = kaynak_yolu("ikon.ico")
        if os.path.exists(ikon):  # ayarlar penceresinde ve görev çubuğunda görünen ikon
            try:
                self.root.iconbitmap(default=ikon)
            except tk.TclError:
                pass

        self.menu = tk.Menu(self.root, tearoff=0)
        # Ana pencereye bağlanan olaylar içindeki tüm yazılarda da çalışır
        # (her olay bir kez işlensin diye alt parçalara ayrıca bağlanmaz).
        self.root.bind("<ButtonPress-1>", self.drag_start)
        self.root.bind("<B1-Motion>", self.drag_move)
        self.root.bind("<ButtonRelease-1>", self.drag_end)
        self.root.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.root.bind("<Control-MouseWheel>", self.wheel_resize)

        self.apply_config()
        self.root.after(100, self.poll)
        self.tick()
        if not self.cfg["district_url"]:
            self.root.after(300, self.open_settings)

    # -------------------------------------------------- yardımcılar

    def t(self, anahtar):
        return METINLER[anahtar][self.cfg["language"] == "en"]

    def vakit_adi(self, ad):
        return VAKIT_EN[ad] if self.cfg["language"] == "en" else ad

    def run_bg(self, func, callback, *args):
        """func'ı arka planda çalıştırır, bitince callback(sonuç, hata) ana iş parçacığında çağrılır."""
        def worker():
            try:
                self.q.put((callback, func(*args), None))
            except Exception as e:  # ağ hatası vb.
                self.q.put((callback, None, e))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        while not self.q.empty():
            callback, result, error = self.q.get()
            callback(result, error)
        self.root.after(100, self.poll)

    def save_config(self):
        save_json(CONFIG_FILE, self.cfg)

    def play_sound(self):
        ses_cal(self.cfg["sound"], self.cfg["sound_file"], self.cfg["volume"])

    # -------------------------------------------------- görünüm

    def build_menu(self):
        self.menu.delete(0, "end")
        self.menu.add_command(label=self.t("menu_settings"), command=self.open_settings)
        self.expanded_var = tk.BooleanVar(value=self.cfg["expanded"])
        self.menu.add_checkbutton(label=self.t("menu_toggle"), variable=self.expanded_var,
                                  command=self.toggle_expanded)
        self.menu.add_command(label=self.t("menu_refresh"), command=lambda: self.fetch(force=True))
        self.menu.add_separator()
        self.menu.add_command(label=self.t("menu_quit"), command=self.quit)

    def apply_config(self):
        tema = TEMALAR[self.cfg["theme"]]
        saydamlik = SAYDAMLIK[self.cfg["opacity"]]
        self.colors = dict(tema, line=renk_karistir(tema["bg"], tema["fg"], 0.18),
                           hl=renk_karistir(tema["bg"], tema["fg"], 0.10),
                           track=renk_karistir(tema["bg"], tema["fg"], 0.22))
        self.with_bg = saydamlik is not None
        # Saydam yapılacak renk: tema zeminine çok yakın, ama birebir aynı değil
        self.key = anahtar_renk(tema["bg"])

        self.root.title(self.t("app"))
        self.build_menu()
        self.root.configure(bg=self.key)
        self.canvas.configure(bg=self.key)
        self.root.attributes("-transparentcolor", self.key)
        self.root.attributes("-alpha", 1.0 if saydamlik is None else saydamlik)
        self.last_view = None
        self.update_display()
        self.place_window()

    # -------------------------------------------------- çizim

    def font(self, boyut, kalin=False):
        anahtar = (max(6, int(boyut)), kalin)
        if anahtar not in self.fonts:
            self.fonts[anahtar] = tkfont.Font(family="Segoe UI", size=anahtar[0],
                                              weight="bold" if kalin else "normal")
        return self.fonts[anahtar]

    def yazi(self, x, y, metin, font, renk, anchor="nw"):
        """Yazı yazar; zemin yoksa okunabilsin diye etrafına gölge çizer."""
        if not self.with_bg:
            golge = self.colors["bg"]
            for dx, dy in ((1, 1), (-1, 0), (1, 0), (0, -1), (0, 1), (2, 2)):
                self.canvas.create_text(x + dx, y + dy, text=metin, font=font, fill=golge, anchor=anchor)
        self.canvas.create_text(x, y, text=metin, font=font, fill=renk, anchor=anchor)

    def zemin(self, w, h, yaricap):
        """Pencere zeminini çizer ve en alta indirir."""
        if not self.with_bg:
            return
        c, renk = self.canvas, self.colors
        if yaricap:
            oge = yuvarlak_kutu(c, 0, 0, w - 1, h - 1, yaricap, fill=renk["bg"], outline=renk["line"])
        else:
            oge = c.create_rectangle(0, 0, w - 1, h - 1, fill=renk["bg"], outline=renk["sub"])
        c.tag_lower(oge)

    def ana_metin(self, ad, sure):
        if self.cfg["language"] == "en":
            return f"{VAKIT_EN[ad]} in {sure}"
        return f"{YONELME[ad]} {sure}"

    def render(self, view, expanded):
        self.canvas.delete("all")
        if view[0] == "msg":
            w, h = self.ciz_mesaj(view[1])
        else:
            ciz = {"kart": self.ciz_kart, "hap": self.ciz_hap}.get(self.cfg["style"], self.ciz_klasik)
            w, h = ciz(view, expanded)
        self.canvas.configure(width=int(w), height=int(h))

    def ciz_mesaj(self, metin):
        s = self.cfg["size"]
        f = self.font(s * 0.85, True)
        pad = s
        w, h = f.measure(metin) + 2 * pad, f.metrics("linespace") + s
        self.yazi(w / 2, h / 2, metin, f, self.colors["fg"], "center")
        self.zemin(w, h, 0 if self.cfg["style"] == "klasik" else s * 0.8)
        return w, h

    def ciz_klasik(self, view, expanded):
        _, ad, sure, yakin, _, saatler, gecmis = view
        renk, s = self.colors, self.cfg["size"]
        ana, kucuk, minik = self.font(s, True), self.font(s * 0.8), self.font(s * 0.65)
        pad = s * 0.75 + 2
        metin = self.ana_metin(ad, sure)
        w = ana.measure(metin) + 2 * pad
        satir = kucuk.metrics("linespace")
        if expanded:
            adlar = max(kucuk.measure(self.vakit_adi(v)) for v in VAKITLER)
            w = max(w, adlar + kucuk.measure("00:00") + 3 * pad)
        y = max(2, s // 4)
        self.yazi(w / 2, y, metin, ana, renk["warn"] if yakin else renk["fg"], "n")
        y += ana.metrics("linespace") + max(2, s // 4)
        if expanded:
            for i, v in enumerate(VAKITLER):
                r = renk["warn"] if v == ad else renk["fg"]
                self.yazi(pad, y, self.vakit_adi(v), kucuk, r)
                self.yazi(w - pad, y, saatler[i] if saatler else "--:--", kucuk, r, "ne")
                y += satir
            y += 2
            self.yazi(w / 2, y, self.konum_adi(), minik, renk["sub"], "n")
            y += minik.metrics("linespace") + s // 3
        self.zemin(w, y, 0)
        return w, y

    def ciz_kart(self, view, expanded):
        _, ad, sure, yakin, ilerleme, saatler, gecmis = view
        renk, s = self.colors, self.cfg["size"]
        etiket_f, buyuk = self.font(s * 0.72, True), self.font(s * 1.7, True)
        satir_f, satir_kalin = self.font(s * 0.85), self.font(s * 0.85, True)
        minik = self.font(s * 0.65)
        pad = s * 1.0
        if self.cfg["language"] == "en":
            etiket = f"{VAKIT_EN[ad].upper()} IN"
        else:
            etiket = tr_buyuk(YONELME[ad])
        ic = max(etiket_f.measure(etiket), buyuk.measure(sure), s * 6)
        if expanded:
            adlar = max(satir_kalin.measure(self.vakit_adi(v)) for v in VAKITLER)
            ic = max(ic, adlar + satir_kalin.measure("00:00") + s * 2, minik.measure(self.konum_adi()))
        w = ic + 2 * pad

        y = pad * 0.6
        self.yazi(pad, y, etiket, etiket_f, renk["sub"])
        y += etiket_f.metrics("linespace") - s * 0.1
        self.yazi(pad - s * 0.08, y, sure, buyuk, renk["warn"] if yakin else renk["fg"])
        y += buyuk.metrics("linespace")
        cubuk = max(3, s // 4)
        c = self.canvas
        c.create_rectangle(pad, y, pad + ic, y + cubuk, fill=renk["track"], width=0)
        if ilerleme > 0:
            c.create_rectangle(pad, y, pad + ic * ilerleme, y + cubuk, fill=renk["warn"], width=0)
        y += cubuk + pad * 0.7

        if expanded:
            satir = satir_f.metrics("linespace") * 1.08
            for i, v in enumerate(VAKITLER):
                if v == ad:
                    f, r = satir_kalin, renk["warn"]
                elif gecmis and gecmis[i]:
                    f, r = satir_f, renk["sub"]
                else:
                    f, r = satir_f, renk["fg"]
                self.yazi(pad, y, self.vakit_adi(v), f, r)
                self.yazi(w - pad, y, saatler[i] if saatler else "--:--", f, r, "ne")
                y += satir
            y += s * 0.35
            self.yazi(pad, y, self.konum_adi(), minik, renk["sub"])
            y += minik.metrics("linespace") + pad * 0.5
        h = y
        self.zemin(w, h, s * 0.9)
        return w, h

    def ciz_hap(self, view, expanded):
        _, ad, sure, yakin, _, saatler, gecmis = view
        renk, s = self.colors, self.cfg["size"]
        kalin, ince = self.font(s, True), self.font(s)
        isim = self.vakit_adi(ad)
        bosluk = s * 0.5
        hilal_r = s * 0.62
        icerik = 2 * hilal_r + bosluk + ince.measure(isim) + bosluk + kalin.measure(sure)
        ust_h = kalin.metrics("linespace") + s * 0.6

        hucre_f = self.font(s * 0.75)
        hucre_kalin = self.font(s * 0.75, True)
        hucre_w = max(hucre_kalin.measure(self.vakit_adi(v)) for v in VAKITLER) + s * 1.2
        hucre_h = hucre_f.metrics("linespace") * 2 + s * 0.5
        ara = s * 0.3
        if expanded:
            pad = s * 0.7
            w = max(icerik + 2 * pad, 3 * hucre_w + 2 * ara + 2 * pad)
        else:
            pad = ust_h / 2
            w = icerik + 2 * pad

        # üst satır: ☾ İkindi 0:12
        x = pad if not expanded else (w - icerik) / 2
        orta = ust_h / 2
        anahtar = (round(hilal_r, 1), renk["warn"], renk["bg"])
        if getattr(self, "_hilal", (None,))[0] != anahtar:
            self._hilal = (anahtar, hilal_resmi(hilal_r, renk["warn"], renk["bg"]))
        self.canvas.create_image(x + hilal_r, orta, image=self._hilal[1], anchor="center")
        x += 2 * hilal_r + bosluk
        self.yazi(x, orta, isim, ince, renk["fg"], "w")
        x += ince.measure(isim) + bosluk
        self.yazi(x, orta, sure, kalin, renk["warn"] if yakin else renk["fg"], "w")
        if not expanded:
            self.zemin(w, ust_h, ust_h / 2)
            return w, ust_h

        # vakitler: 3 x 2 ızgara
        bas_x = (w - (3 * hucre_w + 2 * ara)) / 2
        y0 = ust_h
        for i, v in enumerate(VAKITLER):
            sx = bas_x + (i % 3) * (hucre_w + ara)
            sy = y0 + (i // 3) * (hucre_h + ara)
            if v == ad:
                if self.with_bg:
                    yuvarlak_kutu(self.canvas, sx, sy, sx + hucre_w, sy + hucre_h, s * 0.5,
                                  fill=renk["hl"], outline="")
                f, r = hucre_kalin, renk["warn"]
            elif gecmis and gecmis[i]:
                f, r = hucre_f, renk["sub"]
            else:
                f, r = hucre_f, renk["fg"]
            cx = sx + hucre_w / 2
            self.yazi(cx, sy + s * 0.25, self.vakit_adi(v), f, r, "n")
            self.yazi(cx, sy + s * 0.25 + hucre_f.metrics("linespace"),
                      saatler[i] if saatler else "--:--", f, r, "n")
        h = y0 + 2 * hucre_h + ara + pad
        self.zemin(w, h, s * 0.9)
        return w, h

    def konum_adi(self):
        if not self.cfg["district_name"]:
            return ""
        il, ilce = self.cfg["state_name"], self.cfg["district_name"]
        return il if il == ilce else f"{ilce} / {il}"

    def place_window(self):
        """Pencereyi kayıtlı yerine koyar; bir kenara yapışıksa o kenarda tutar."""
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        c = self.cfg
        if c["x"] is None or c["y"] is None:
            x = y = 0
            sol, ust, sag, alt = calisma_alani(1, 1)  # ana ekran
        else:
            x, y = c["x"], c["y"]
            sol, ust, sag, alt = calisma_alani(x + w // 2, y + h // 2)
        if c["snap_x"] == "left":
            x = sol
        elif c["snap_x"] == "right":
            x = sag - w
        if c["snap_y"] == "top":
            y = ust
        elif c["snap_y"] == "bottom":
            y = alt - h
        x = max(sol, min(x, sag - w))
        y = max(ust, min(y, alt - h))
        self.root.geometry(f"+{x}+{y}")

    def toggle_expanded(self):
        self.cfg["expanded"] = not self.cfg["expanded"]
        self.save_config()
        self.apply_config()
        if self.settings and self.settings.win.winfo_exists():
            self.settings.mod.set("extended" if self.cfg["expanded"] else "compact")

    def wheel_resize(self, e):
        yeni = self.cfg["size"] + (1 if e.delta > 0 else -1)
        self.cfg["size"] = max(BOYUT_MIN, min(BOYUT_MAX, yeni))
        self.save_config()
        self.apply_config()

    # -------------------------------------------------- sürükleme ve kenara yapışma

    def drag_start(self, e):
        self._drag = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y())
        self._moved = False
        self._snap = (self.cfg["snap_x"], self.cfg["snap_y"])
        self._hold_job = self.root.after(BASILI_TUTMA_MS, self.held)

    def held(self):
        """Kompakt moddayken basılı tutuldu: bırakılana kadar tüm vakitleri göster."""
        self._hold_job = None
        if not self.cfg["expanded"]:
            self.peeking = True
            self.apply_config()

    def cancel_hold(self):
        if getattr(self, "_hold_job", None):
            self.root.after_cancel(self._hold_job)
            self._hold_job = None

    def drag_move(self, e):
        sx, sy, wx, wy = self._drag
        dx, dy = e.x_root - sx, e.y_root - sy
        if not self._moved and abs(dx) + abs(dy) > SURUKLEME_ESIGI:
            # sürükleme başladı: bekleyen ya da açılmış geçici görünümü iptal et
            self.cancel_hold()
            if self.peeking:
                self.peeking = False
                self.apply_config()
            self._moved = True
            self.dragging = True
        if not self._moved:
            return
        x, y = wx + dx, wy + dy
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sol, ust, sag, alt = calisma_alani(x + w // 2, y + h // 2)
        snap_x = snap_y = None
        if abs(x - sol) <= SNAP:
            x, snap_x = sol, "left"
        elif abs(x + w - sag) <= SNAP:
            x, snap_x = sag - w, "right"
        if abs(y - ust) <= SNAP:
            y, snap_y = ust, "top"
        elif abs(y + h - alt) <= SNAP:
            y, snap_y = alt - h, "bottom"
        self._snap = (snap_x, snap_y)
        self.root.geometry(f"+{x}+{y}")

    def drag_end(self, e):
        self.cancel_hold()
        self.dragging = False
        if self.peeking:
            self.peeking = False
            self.apply_config()
        if self._moved:
            self.cfg["x"], self.cfg["y"] = self.root.winfo_x(), self.root.winfo_y()
            self.cfg["snap_x"], self.cfg["snap_y"] = self._snap
            self.save_config()

    # -------------------------------------------------- vakitler

    def fetch(self, force=False):
        if self.fetching or not self.cfg["district_url"]:
            return
        self.fetching = True
        self.last_attempt = dt.datetime.now()
        self.run_bg(get_vakitler, lambda r, e: self.fetched(r, e, force), self.cfg["district_url"])

    def fetched(self, days, error, force):
        self.fetching = False
        if error:
            if force:
                messagebox.showerror(self.t("app"), f"{self.t('fetch_err')}\n{error}")
            return
        if self.cache.get("district_id") != self.cfg["district_id"]:
            self.cache = {"district_id": self.cfg["district_id"], "days": {}}
        self.cache["days"].update(days)
        # 40 günden eski kayıtları sil
        sinir = (dt.date.today() - dt.timedelta(days=40)).isoformat()
        self.cache["days"] = {k: v for k, v in self.cache["days"].items() if k >= sinir}
        self.cache["fetched"] = dt.date.today().isoformat()
        save_json(CACHE_FILE, self.cache)
        self.update_display()

    def need_fetch(self):
        if not self.cfg["district_url"] or self.fetching:
            return False
        if self.cache.get("district_id") != self.cfg["district_id"]:
            return True
        if self.last_attempt and dt.datetime.now() - self.last_attempt < dt.timedelta(minutes=10):
            return False
        return self.cache.get("fetched") != dt.date.today().isoformat()

    def days(self):
        if self.cache.get("district_id") != self.cfg["district_id"]:
            return {}
        return self.cache.get("days", {})

    # -------------------------------------------------- her saniye

    def tick(self):
        if self.need_fetch():
            self.fetch()
        self.update_display()
        self.tick_count += 1
        if self.tick_count % 10 == 0:  # başka pencereler öne geçse de üstte kal
            self.root.attributes("-topmost", True)
            self.root.lift()
        self.root.after(1000 - dt.datetime.now().microsecond // 1000 + 5, self.tick)

    def update_display(self):
        now = dt.datetime.now()
        days = self.days()
        hedef = siradaki_vakit(days, now)

        if not self.cfg["district_url"]:
            view = ("msg", self.t("choose_loc"))
        elif not hedef:
            view = ("msg", self.t("loading_times"))
        else:
            ad, zaman = hedef
            kalan = (zaman - now).total_seconds()
            dakika = math.ceil(kalan / 60)
            sure = f"{dakika // 60}:{dakika % 60:02d}"
            uyari_suresi = self.cfg["alarm_minutes"] * 60
            yakin = self.cfg["alarm_on"] and ad in self.cfg["alarm_vakitler"] and kalan <= uyari_suresi
            onceki = onceki_vakit(days, now)
            ilerleme = 0.0
            if onceki and zaman > onceki:
                ilerleme = round(1 - kalan / (zaman - onceki).total_seconds(), 2)
            saatler = days.get(now.date().isoformat())
            gecmis = None
            if saatler:
                gecmis = tuple(dt.datetime.combine(now.date(), dt.time(*map(int, s.split(":")))) <= now
                               for s in saatler)
                saatler = tuple(saatler)
            view = ("vakit", ad, sure, yakin, ilerleme, saatler, gecmis)

        # Sadece görünen bir şey değiştiyse yeniden çiz (her saniye çizmemek için)
        expanded = self.cfg["expanded"] or self.peeking
        anahtar = (view, expanded, self.konum_adi())
        if anahtar != self.last_view:
            self.last_view = anahtar
            self.render(view, expanded)
            if not self.dragging:  # boyut değişince kenara yapışık kalsın
                self.place_window()

        if hedef:
            self.check_alarm(hedef[0], hedef[1], (hedef[1] - now).total_seconds(), now)

    def check_alarm(self, ad, zaman, kalan, now):
        cfg = self.cfg
        # Vakit girdi: hedef bir sonraki vakite geçti
        if self.last_target and self.last_target[1] != zaman and self.last_target[1] <= now:
            onceki = self.last_target[0]
            if cfg["alarm_at_time"] and onceki in cfg["alarm_vakitler"]:
                self.play_sound()
        self.last_target = (ad, zaman)

        if not cfg["alarm_on"] or ad not in cfg["alarm_vakitler"]:
            return
        esik = cfg["alarm_minutes"] * 60
        anahtar = f"{zaman.isoformat()}-{esik}"
        # Sadece eşik aşıldığı anda çal (uygulama geç açıldıysa çalma)
        if esik - 30 < kalan <= esik and anahtar not in self.fired:
            self.fired.add(anahtar)
            self.play_sound()

    # -------------------------------------------------- diğer

    def open_settings(self):
        if self.settings and self.settings.win.winfo_exists():
            self.settings.win.lift()
            self.settings.win.focus_force()
            return
        self.settings = AyarlarPenceresi(self)

    def quit(self):
        winsound.PlaySound(None, 0)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------- ayarlar

class Secim:
    """Görünen adı dile göre değişen, kimliği sabit kalan açılır liste."""

    def __init__(self, parent, secenekler, secili, en, width=24):
        # secenekler: {kimlik: (Türkçe ad, İngilizce ad, ...)}
        self.kimlikler = list(secenekler)
        self.adlar = [secenekler[k][en] for k in self.kimlikler]
        self.cb = ttk.Combobox(parent, state="readonly", width=width, values=self.adlar)
        self.cb.current(self.kimlikler.index(secili) if secili in self.kimlikler else 0)

    def get(self):
        return self.kimlikler[self.cb.current()]

    def set(self, kimlik):
        self.cb.current(self.kimlikler.index(kimlik))


class AyarlarPenceresi:
    def __init__(self, app):
        self.app = app
        t = app.t
        c = app.cfg
        en = c["language"] == "en"
        w = self.win = tk.Toplevel(app.root)
        w.title(t("settings_title"))
        w.attributes("-topmost", True)
        w.resizable(False, False)
        pad = {"padx": 8, "pady": 5}
        ttk.Style(w).configure("TNotebook.Tab", padding=(16, 6))

        # Başlık şeridi: hilal, uygulama adı ve seçili konum
        yesil, altin = TEMALAR["Yeşil"]["bg"], TEMALAR["Yeşil"]["warn"]
        ust = tk.Frame(w, bg=yesil)
        ust.pack(fill="x")
        self._baslik_hilal = hilal_resmi(13, altin, yesil)
        tk.Label(ust, image=self._baslik_hilal, bg=yesil).pack(side="left", padx=(16, 8), pady=12)
        tk.Label(ust, text=t("app"), bg=yesil, fg="#eafff4",
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(ust, text=app.konum_adi(), bg=yesil, fg=TEMALAR["Yeşil"]["sub"],
                 font=("Segoe UI", 10)).pack(side="right", padx=16)

        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        def sekme(baslik):
            f = ttk.Frame(nb, padding=12)
            nb.add(f, text=baslik)
            return f

        # ---- Genel sekmesi: konum, dil, otomatik başlatma
        genel = sekme(t("tab_general"))
        f = ttk.LabelFrame(genel, text=t("location"), padding=6)
        f.pack(fill="x")
        ttk.Label(f, text=t("province")).grid(row=0, column=0, sticky="w", **pad)
        self.il_cb = ttk.Combobox(f, state="readonly", width=30, height=20)
        self.il_cb.grid(row=0, column=1, **pad)
        ttk.Label(f, text=t("district")).grid(row=1, column=0, sticky="w", **pad)
        self.ilce_cb = ttk.Combobox(f, state="readonly", width=30, height=20)
        self.ilce_cb.grid(row=1, column=1, **pad)
        self.il_cb.set(t("loading"))
        self.il_cb.bind("<<ComboboxSelected>>", lambda e: self.il_secildi())
        self.iller, self.ilceler = [], []

        f = ttk.LabelFrame(genel, text=t("other"), padding=6)
        f.pack(fill="x", pady=(10, 0))
        ttk.Label(f, text=t("language")).grid(row=0, column=0, sticky="w", **pad)
        self.dil = Secim(f, DILLER, c["language"], en, width=14)
        self.dil.cb.grid(row=0, column=1, sticky="w", **pad)
        self.autostart = tk.BooleanVar(value=c["autostart"])
        ttk.Checkbutton(f, text=t("autostart"), variable=self.autostart) \
            .grid(row=1, column=0, columnspan=2, sticky="w", **pad)

        # ---- Uyarı sekmesi
        f = sekme(t("tab_alarm"))
        self.alarm_on = tk.BooleanVar(value=c["alarm_on"])
        satir = ttk.Frame(f)
        satir.grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(satir, text=t("alarm_a"), variable=self.alarm_on).pack(side="left")
        self.dakika = tk.StringVar(value=str(c["alarm_minutes"]))
        ttk.Spinbox(satir, from_=1, to=120, width=4, textvariable=self.dakika).pack(side="left", padx=4)
        ttk.Label(satir, text=t("alarm_b")).pack(side="left")

        self.alarm_at_time = tk.BooleanVar(value=c["alarm_at_time"])
        ttk.Checkbutton(f, text=t("alarm_at_time"), variable=self.alarm_at_time) \
            .grid(row=1, column=0, columnspan=2, sticky="w", **pad)

        ttk.Label(f, text=t("which")).grid(row=2, column=0, columnspan=2, sticky="w", padx=8)
        vf = ttk.Frame(f)
        vf.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))
        self.vakit_vars = {}
        for i, ad in enumerate(VAKITLER):
            v = tk.BooleanVar(value=ad in c["alarm_vakitler"])
            self.vakit_vars[ad] = v
            ttk.Checkbutton(vf, text=app.vakit_adi(ad), variable=v) \
                .grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 12))

        ttk.Label(f, text=t("sound")).grid(row=4, column=0, sticky="w", **pad)
        sf = ttk.Frame(f)
        sf.grid(row=4, column=1, sticky="w", **pad)
        self.ses = Secim(sf, SESLER, c["sound"], en, width=26)
        self.ses.cb.pack(side="left")
        self.ses.cb.bind("<<ComboboxSelected>>", lambda e: self.ses_secildi())
        ttk.Button(sf, text=t("listen"), width=7, command=self.dinle).pack(side="left", padx=4)
        self.ses_dosyasi = c["sound_file"]
        self.dosya_lbl = ttk.Label(f, foreground="#666")
        self.dosya_lbl.grid(row=5, column=1, sticky="w", padx=8)
        self.dosya_etiketi()

        ttk.Label(f, text=t("volume")).grid(row=6, column=0, sticky="w", **pad)
        self.ses_seviyesi = tk.IntVar(value=c["volume"])
        tk.Scale(f, from_=0, to=100, orient="horizontal", length=220, variable=self.ses_seviyesi,
                 showvalue=True, resolution=5).grid(row=6, column=1, sticky="w", padx=8)

        # ---- Görünüm sekmesi (değişiklikler pencerede anında görünür)
        f = sekme(t("tab_look"))
        ttk.Label(f, text=t("style")).grid(row=0, column=0, sticky="w", **pad)
        self.stil = Secim(f, STILLER, c["style"], en)
        self.stil.cb.grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(f, text=t("mode")).grid(row=1, column=0, sticky="w", **pad)
        self.mod = Secim(f, MODLAR, "extended" if c["expanded"] else "compact", en, width=38)
        self.mod.cb.grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(f, text=t("mode_hint"), foreground="#666") \
            .grid(row=2, column=1, sticky="w", padx=8, pady=(0, 4))
        ttk.Label(f, text=t("color")).grid(row=3, column=0, sticky="w", **pad)
        self.tema = Secim(f, TEMA_ADLARI, c["theme"], en)
        self.tema.cb.grid(row=3, column=1, sticky="w", **pad)
        ttk.Label(f, text=t("opacity")).grid(row=4, column=0, sticky="w", **pad)
        self.saydamlik = Secim(f, SAYDAMLIK_ADLARI, c["opacity"], en)
        self.saydamlik.cb.grid(row=4, column=1, sticky="w", **pad)
        ttk.Label(f, text=t("size")).grid(row=5, column=0, sticky="w", **pad)
        self.boyut = tk.IntVar(value=c["size"])
        tk.Scale(f, from_=BOYUT_MIN, to=BOYUT_MAX, orient="horizontal", length=220,
                 variable=self.boyut, command=lambda _d: self.onizle()) \
            .grid(row=5, column=1, sticky="w", padx=8)
        ttk.Label(f, text=t("size_hint"), foreground="#666") \
            .grid(row=6, column=1, sticky="w", padx=8, pady=(0, 4))
        for secim in (self.stil, self.mod, self.tema, self.saydamlik):
            secim.cb.bind("<<ComboboxSelected>>", lambda e: self.onizle())
        self.orijinal = {k: c[k] for k in ONIZLEME_AYARLARI}

        bf = ttk.Frame(w)
        bf.pack(fill="x", padx=12, pady=12)
        ttk.Button(bf, text=t("cancel"), command=self.iptal).pack(side="right")
        ttk.Button(bf, text=t("apply"), command=self.uygula).pack(side="right", padx=6)
        ttk.Button(bf, text=t("ok"), command=self.tamam).pack(side="right")
        self.durum_lbl = ttk.Label(bf, foreground="#2a8a2a")
        self.durum_lbl.pack(side="left")
        w.protocol("WM_DELETE_WINDOW", self.iptal)

        app.run_bg(get_iller, self.iller_geldi)

    # -------------------------------------------------- konum

    def iller_geldi(self, iller, error):
        if not self.win.winfo_exists():
            return
        t = self.app.t
        if error:
            self.il_cb.set(t("net_err"))
            messagebox.showerror(t("app"), f"{t('states_err')}\n{error}", parent=self.win)
            return
        self.iller = iller
        self.il_cb.configure(values=[ad for ad, _ in iller])
        secili = next((i for i, (_, sid) in enumerate(iller) if sid == self.app.cfg["state_id"]), None)
        if secili is None:
            self.il_cb.set("")
            self.ilce_cb.set(t("pick_state"))
        else:
            self.il_cb.current(secili)
            self.il_secildi(ilk=True)

    def il_secildi(self, ilk=False):
        i = self.il_cb.current()
        if i < 0:
            return
        self.ilceler = []
        self.ilce_cb.configure(values=[])
        self.ilce_cb.set(self.app.t("loading"))
        self.app.run_bg(get_ilceler, lambda r, e: self.ilceler_geldi(r, e, ilk), self.iller[i][1])

    def ilceler_geldi(self, ilceler, error, ilk):
        if not self.win.winfo_exists():
            return
        if error:
            self.ilce_cb.set(self.app.t("net_err"))
            return
        self.ilceler = ilceler
        self.ilce_cb.configure(values=[ad for ad, _, _ in ilceler])
        secili = None
        if ilk:
            secili = next((i for i, (_, iid, _) in enumerate(ilceler)
                           if iid == self.app.cfg["district_id"]), None)
        if secili is None:
            # il merkezini (ile aynı adlı ilçeyi) öner
            il_adi = self.il_cb.get()
            secili = next((i for i, (ad, _, _) in enumerate(ilceler) if ad == il_adi), None)
        if secili is None:
            self.ilce_cb.set("")
        else:
            self.ilce_cb.current(secili)

    # -------------------------------------------------- ses ve boyut

    def ses_secildi(self):
        if self.ses.get() == "custom":
            t = self.app.t
            yol = filedialog.askopenfilename(parent=self.win, title=t("pick_wav"),
                                             filetypes=[(t("wav_type"), "*.wav")])
            if yol:
                self.ses_dosyasi = yol
            elif not self.ses_dosyasi:
                self.ses.set("zil")
        self.dosya_etiketi()

    def dosya_etiketi(self):
        if self.ses.get() == "custom" and self.ses_dosyasi:
            self.dosya_lbl.configure(text=os.path.basename(self.ses_dosyasi))
        else:
            self.dosya_lbl.configure(text="")

    def dinle(self):
        ses_cal(self.ses.get(), self.ses_dosyasi, self.ses_seviyesi.get())

    def gorunum_secimleri(self):
        return {"style": self.stil.get(), "expanded": self.mod.get() == "extended",
                "theme": self.tema.get(), "opacity": self.saydamlik.get(), "size": self.boyut.get()}

    def onizle(self):
        """Görünüm ayarlarını kaydetmeden pencerede anında göster."""
        yeni = self.gorunum_secimleri()
        if any(self.app.cfg[k] != v for k, v in yeni.items()):
            self.app.cfg.update(yeni)
            self.app.apply_config()

    def iptal(self):
        if any(self.app.cfg[k] != v for k, v in self.orijinal.items()):
            self.app.cfg.update(self.orijinal)
            self.app.apply_config()
        self.win.destroy()

    # -------------------------------------------------- kaydet

    def tamam(self):
        if self.kaydet():
            self.win.destroy()

    def uygula(self):
        eski_dil = self.app.cfg["language"]
        if not self.kaydet():
            return
        if self.app.cfg["language"] != eski_dil:
            # pencere yeni dilde yeniden açılsın
            self.win.destroy()
            self.app.open_settings()
            return
        self.orijinal = {k: self.app.cfg[k] for k in ONIZLEME_AYARLARI}
        self.durum_lbl.configure(text=self.app.t("saved"))
        self.win.after(2000, lambda: self.win.winfo_exists() and self.durum_lbl.configure(text=""))

    def kaydet(self):
        """Ayarları kaydedip uygular; bir sorun varsa False döner."""
        app, c, t = self.app, self.app.cfg, self.app.t
        il_i, ilce_i = self.il_cb.current(), self.ilce_cb.current()
        if self.iller and il_i >= 0 and self.ilceler and ilce_i >= 0:
            il_adi, il_id = self.iller[il_i]
            ilce_adi, ilce_id, ilce_url = self.ilceler[ilce_i]
            c.update(state_id=il_id, state_name=il_adi,
                     district_id=ilce_id, district_name=ilce_adi, district_url=ilce_url)
        elif not c["district_url"]:
            messagebox.showwarning(t("app"), t("need_loc"), parent=self.win)
            return False

        try:
            dakika = int(self.dakika.get())
            if not 1 <= dakika <= 120:
                raise ValueError
        except ValueError:
            messagebox.showwarning(t("app"), t("bad_min"), parent=self.win)
            return False

        c.update(alarm_on=self.alarm_on.get(), alarm_minutes=dakika,
                 alarm_at_time=self.alarm_at_time.get(),
                 alarm_vakitler=[ad for ad, v in self.vakit_vars.items() if v.get()],
                 sound=self.ses.get(), sound_file=self.ses_dosyasi,
                 volume=self.ses_seviyesi.get(),
                 language=self.dil.get(), autostart=self.autostart.get(),
                 **self.gorunum_secimleri())
        try:
            windows_ile_baslat(c["autostart"])
        except OSError as e:
            messagebox.showwarning(t("app"), f"{t('autostart_err')}\n{e}", parent=self.win)

        app.save_config()
        app.apply_config()
        if app.cache.get("district_id") != c["district_id"]:
            app.last_attempt = None
            app.fetch()
        return True


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # yazılar bulanık olmasın
    except (AttributeError, OSError):
        pass
    if not tek_kopya_mi():
        return
    try:  # görev çubuğunda Python'un değil uygulamanın kendi ikonu görünsün
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EzanVakti.App")
    except (AttributeError, OSError):
        pass
    EzanVakti().run()


if __name__ == "__main__":
    main()
