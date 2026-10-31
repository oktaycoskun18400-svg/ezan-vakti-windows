# -*- coding: utf-8 -*-
"""Ezan Vakti - ekranın köşesinde her zaman üstte duran küçük namaz vakti sayacı.

Vakitler Diyanet İşleri Başkanlığı'nın sitesinden (namazvakitleri.diyanet.gov.tr) alınır.
Sol tık: ayrıntıları aç/kapat, sürükle: taşı (ekran kenarlarına yapışır),
Ctrl + fare tekerleği: boyut, sağ tık: menü (ayarlar, çıkış).
"""
import ctypes
import ctypes.wintypes as wt
import datetime as dt
import hashlib
import html
import json
import math
import os
import queue
import random
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import wave
import webbrowser
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

# Uygulamanın sürümü: yeni sürüm yayınlarken bunu ve surum_bilgisi.txt'yi birlikte güncelle
SURUM = "0.5.1"
BASE_URL = "https://namazvakitleri.diyanet.gov.tr"
TURKIYE = ("TÜRKİYE", "2")  # varsayılan ülke (ad, Diyanet kimliği)
HEADERS = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) EzanVakti/{SURUM}"}
# Güncellemeler yalnızca bu GitHub deposunun sürümlerinden indirilir
GITHUB_DEPO = "oktaycoskun18400-svg/ezan-vakti-windows"
GUNCELLEME_API = f"https://api.github.com/repos/{GITHUB_DEPO}/releases/latest"
GUNCELLEME_ONEKI = f"https://github.com/{GITHUB_DEPO}/releases/download/"
EXE_ADI = "EzanVakti.exe"

VAKITLER = ["İmsak", "Güneş", "Öğle", "İkindi", "Akşam", "Yatsı"]
VAKIT_EN = {"İmsak": "Fajr", "Güneş": "Sunrise", "Öğle": "Dhuhr",
            "İkindi": "Asr", "Akşam": "Maghrib", "Yatsı": "Isha"}
YONELME = {"İmsak": "İmsaka", "Güneş": "Güneşe", "Öğle": "Öğleye",
           "İkindi": "İkindiye", "Akşam": "Akşama", "Yatsı": "Yatsıya"}
AYLAR = {"Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
         "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12}
GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AY_EN = ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"]
GUN_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HICRI_AY_EN = {"Muharrem": "Muharram", "Safer": "Safar", "Rebiülevvel": "Rabi al-Awwal",
               "Rebiülahir": "Rabi al-Akhir", "Cemaziyelevvel": "Jumada al-Ula",
               "Cemaziyelahir": "Jumada al-Akhirah", "Recep": "Rajab", "Şaban": "Sha'ban",
               "Ramazan": "Ramadan", "Şevval": "Shawwal", "Zilkade": "Dhu al-Qa'dah",
               "Zilhicce": "Dhu al-Hijjah"}
# Dar pencerelerde kullanılan kısa hicrî ay adları
HICRI_AY_KISA = {"Rebiülevvel": "R.evvel", "Rebiülahir": "R.ahir", "Cemaziyelevvel": "C.evvel",
                 "Cemaziyelahir": "C.ahir", "Rabi al-Awwal": "Rabi I", "Rabi al-Akhir": "Rabi II",
                 "Jumada al-Ula": "Jumada I", "Jumada al-Akhirah": "Jumada II",
                 "Dhu al-Qa'dah": "Dhu'l-Qa'dah", "Dhu al-Hijjah": "Dhu'l-Hijjah"}

DILLER = {"tr": ("Türkçe", "Türkçe"), "en": ("English", "English")}
TEMALAR = {
    "Koyu":     {"bg": "#1e1e1e", "fg": "#f2f2f2", "sub": "#9a9a9a", "warn": "#ffb020"},
    "Açık":     {"bg": "#f7f7f7", "fg": "#1e1e1e", "sub": "#6a6a6a", "warn": "#d05a00"},
    "Yeşil":    {"bg": "#0f3d2e", "fg": "#eafff4", "sub": "#8fc7ad", "warn": "#ffd166"},
    "Lacivert": {"bg": "#1b2a4a", "fg": "#f3f1ea", "sub": "#a3adc6", "warn": "#d6a84c"},
}
VARSAYILAN_TEMA = "Lacivert"  # logodaki lacivert ve altın
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
    "custom": ("Kendi ses dosyam (mp3, wav...)", "My own sound file (mp3, wav...)"),
}
ONIZLEME_AYARLARI = ("style", "expanded", "theme", "opacity", "size")
# kimlikler ayar dosyasında saklandığı için değişmez, sadece görünen adlar değişebilir
STILLER = {"kart": ("Levha", "Plaque"), "hap": ("Hilal", "Crescent"), "klasik": ("Takvim", "Almanac")}
MODLAR = {"compact": ("Kompakt (sadece kalan süre)", "Compact (time left only)"),
          "extended": ("Genişletilmiş (kalan süre + tüm vakitler)", "Extended (time left + all times)")}
SNAP = 18  # kenara bu kadar pikselden yakınsa yapışır
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
    "calc_frame": (" Vakit hesabı ", " Prayer times "),
    "calc": ("Hesap:", "Times:"),
    "calc_hint": ("Diğer yöntemler, ilçenin konumuna göre astronomik olarak hesaplanır.",
                  "Other methods are calculated astronomically for the district's location."),
    "ok": ("Tamam", "OK"),
    "apply": ("Uygula", "Apply"),
    "saved": ("Kaydedildi ✓", "Saved ✓"),
    "menu_refresh": ("Vakitleri şimdi yenile", "Refresh times now"),
    "menu_hadith": ("Bir hadis göster", "Show a hadith"),
    "tz_title": ("SAAT DİLİMİ", "TIME ZONE"),
    "tz_warn": ("Bilgisayarınızın saat dilimi, seçilen şehrin saatiyle uyuşmuyor; kalan süreler yanlış "
                "görünebilir. Windows'un saat dilimi ayarını kontrol edin.",
                "Your computer's time zone doesn't match the selected city, so countdowns may be off. "
                "Check the Windows time zone setting."),
    "hadith_title": ("HADİS-İ ŞERİF", "HADITH"),
    "hadith_wait": ("Hadisler indiriliyor, biraz sonra tekrar deneyin.",
                    "Hadiths are being downloaded, please try again shortly."),
    "menu_update": ("Güncellemeleri denetle", "Check for updates"),
    "upd_title": ("GÜNCELLEME", "UPDATE"),
    "upd_available": ("Yeni sürüm {v} hazır. Güncellemek için buraya tıklayın.",
                      "Version {v} is available. Click here to update."),
    "upd_downloading": ("Yeni sürüm indiriliyor ve doğrulanıyor…", "Downloading and verifying the new version…"),
    "upd_failed": ("Güncelleme kurulamadı; mevcut sürüm çalışmaya devam ediyor. İndirme sayfası açılıyor.",
                   "The update couldn't be installed; the current version keeps running. "
                   "Opening the download page."),
    "upd_check_failed": ("Güncellemeler denetlenemedi. İnternet bağlantısını kontrol edin.",
                         "Couldn't check for updates. Check your internet connection."),
    "upd_none": ("Ezan Vakti güncel (sürüm {v}).", "Prayer Times is up to date (version {v})."),
    "auto_update": ("Güncellemeleri otomatik denetle", "Check for updates automatically"),
    "version": ("Sürüm", "Version"),
    "hadith_frame": (" Hadis ", " Hadith "),
    "hadith_alert": ("Vakte belirlenen süre kala hadis göster", "Show a hadith before the prayer time"),
    "hadith_time": ("Vakit girdiğinde hadis göster", "Show a hadith when the prayer time begins"),
    "hadith_hint": ("Süre, yukarıdaki \"dakika kala\" ayarıdır. Sağ tık → \"Bir hadis göster\" her zaman çalışır.",
                    "The time is the \"minutes before\" setting above. Right-click → \"Show a hadith\" "
                    "always works."),
    "menu_quit": ("Çıkış", "Quit"),
    "choose_loc": ("Konum seçin (sağ tık)", "Choose location (right-click)"),
    "loading_times": ("Vakitler alınıyor...", "Loading times..."),
    "fetch_err": ("Vakitler alınamadı:", "Could not get prayer times:"),
    "settings_title": ("Ezan Vakti - Ayarlar", "Prayer Times - Settings"),
    "location": (" Konum ", " Location "),
    "country": ("Ülke:", "Country:"),
    "province": ("İl / Eyalet:", "Province / State:"),
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
    "wav_type": ("Ses dosyaları", "Sound files"),
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
    "country_id": TURKIYE[1], "country_name": TURKIYE[0],
    "state_id": None, "state_name": "",
    "district_id": None, "district_name": "", "district_url": "",
    "alarm_on": True, "alarm_minutes": 10, "alarm_at_time": True,
    "alarm_vakitler": ["İmsak", "Öğle", "İkindi", "Akşam", "Yatsı"],
    "sound": "zil", "sound_file": "", "volume": 40,
    "style": "kart", "theme": VARSAYILAN_TEMA, "opacity": "Yarı saydam", "size": 13,
    "x": None, "y": None, "snap_x": "right", "snap_y": "bottom",
    "expanded": False, "autostart": False,
    "calc": "diyanet",
    "hadis_uyari": True,  # vakte alarm_minutes kala hadis göster
    "hadis_vakit": True,  # vakit girdiğinde hadis göster
    "guncelleme_otomatik": True, "guncelleme_son_kontrol": "",
}
# Vakit hesap yöntemleri: (Türkçe ad, İngilizce ad, kısa Türkçe, kısa İngilizce)
HESAPLAR = {
    "diyanet": ("Diyanet (resmi vakitler)", "Diyanet (official times)", "", ""),
    "ummulkura": ("Ümmü'l-Kurâ (Mekke)", "Umm al-Qura (Makkah)", "Ümmü'l-Kurâ", "Umm al-Qura"),
    "misir": ("Mısır Genel Araştırma Kurumu", "Egyptian General Authority", "Mısır", "Egypt"),
    "mwl": ("Müslüman Dünya Birliği (MWL)", "Muslim World League (MWL)", "MWL", "MWL"),
}
# Astronomik yöntemlerin açıları: fecir (imsak) ve yatsı için güneşin ufkun kaç derece altında olduğu.
# Ümmü'l-Kurâ'da yatsı açıyla değil, akşamdan sabit dakika sonra (Ramazan'da daha geç) girer.
YONTEMLER = {
    "ummulkura": {"fecir": 18.5, "yatsi_dk": 90, "yatsi_dk_ramazan": 120},
    "misir": {"fecir": 19.5, "yatsi": 17.5},
    "mwl": {"fecir": 18, "yatsi": 17},
}


def eski_ayarlari_cevir(cfg):
    """Önceki sürümün ayar dosyasını bu sürüme uyarlar."""
    if "hadis_on" in cfg:  # v1.2.0'daki tek hadis ayarı ikiye bölündü
        cfg["hadis_uyari"] = cfg["hadis_vakit"] = bool(cfg.pop("hadis_on"))
    if not isinstance(cfg["size"], int):
        cfg["size"] = ESKI_BOYUTLAR.get(cfg["size"], 13)
    if cfg["sound"] == "Kendi ses dosyam (.wav)":
        cfg["sound"] = "custom"
    if cfg["sound"] not in SESLER:
        cfg["sound"] = "zil"
    if cfg["style"] not in STILLER:
        cfg["style"] = "kart"
    if cfg["theme"] not in TEMALAR:
        cfg["theme"] = VARSAYILAN_TEMA
    if cfg["opacity"] not in SAYDAMLIK:
        cfg["opacity"] = "Yarı saydam"
    if cfg["language"] not in DILLER:
        cfg["language"] = "tr"
    if cfg["calc"] not in HESAPLAR:
        cfg["calc"] = "diyanet"
    cfg.pop("temkin", None)
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


def get_reg_list(country_id, **params):
    params.update(CountryId=country_id, Culture="tr-TR")
    url = BASE_URL + "/tr-TR/home/GetRegList?" + urllib.parse.urlencode(params)
    return json.loads(http_get(url))


def get_ulkeler():
    """Diyanet'in vakit verdiği ülkeler: [(ad, kimlik), ...] (sitedeki ülke listesinden)."""
    page = html.unescape(http_get(BASE_URL + "/tr-TR"))
    blok = re.search(r'name="country".*?</select>', page, re.S)
    if not blok:
        raise ValueError("Diyanet sayfasında ülke listesi bulunamadı.")
    return [(ad.strip(), kimlik) for kimlik, ad in
            re.findall(r'<option value="(\d+)"[^>]*>([^<]+)</option>', blok.group(0))]


def get_iller(country_id):
    data = get_reg_list(country_id, ChangeType="country")
    return [(s["SehirAdi"], s["SehirID"]) for s in data["StateList"] or []]


def get_ilceler(country_id, state_id):
    data = get_reg_list(country_id, ChangeType="state", StateId=state_id)
    return [(d["IlceAdi"], d["IlceID"], d["IlceUrl"]) for d in data["StateRegionList"] or []]


SATIR_RE = re.compile(
    r"<tr>\s*<td>\s*(\d{1,2})\s+(\w+)\s+(\d{4})[^<]*</td>\s*<td>([^<]*)</td>"
    r"((?:\s*<td>\s*\d{1,2}:\d{2}\s*</td>){6})")


def get_vakitler(district_url):
    """Diyanet sayfasındaki tablodan vakitleri ve hicrî tarihleri okur.

    ({"2026-10-31": ["06:01", ...6 vakit], ...}, {"2026-10-31": "20 Cemaziyelevvel 1448", ...}) döner.
    """
    page = html.unescape(http_get(BASE_URL + district_url))
    days, hicri = {}, {}
    for m in SATIR_RE.finditer(page):
        ay = AYLAR.get(m.group(2))
        if not ay:
            continue
        tarih = dt.date(int(m.group(3)), ay, int(m.group(1))).isoformat()
        days[tarih] = re.findall(r"\d{1,2}:\d{2}", m.group(5))
        hicri[tarih] = m.group(4).strip()
    if not days:
        raise ValueError("Diyanet sayfasında vakit tablosu bulunamadı.")
    return days, hicri


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
    # Gece yarısından sonra dünkü yatsı gerekir; dünün vakitleri kayıtlı değilse (vakitler bugünden
    # itibaren indirilir) bugünkü yatsıyla tahmin et, günden güne en fazla bir iki dakika değişir.
    bugunku = days.get(now.date().isoformat())
    if bugunku:
        h, m = map(int, bugunku[-1].split(":"))
        return dt.datetime.combine(now.date() - dt.timedelta(days=1), dt.time(h, m))
    return None


def yeni_girdi(vakit, now):
    """Vakit az önce mi girdi? (Uykudan uyanınca çoktan geçmiş vakitler için ses/hadis çıkmasın.)"""
    return 0 <= (now - vakit).total_seconds() < 90


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


# ---------------------------------------------------------------- hadisler
# Seçme hadislerin sadece kaynak bilgisi (kitap, numara) uygulamada durur. Türkçe ve
# İngilizce metinler ilk kullanımda açık hadith-api veri setinden indirilip saklanır;
# böylece başkasına ait çeviriler uygulamanın içinde dağıtılmamış olur.

HADIS_API = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions"
KITAP_ADLARI = {"bukhari": ("Buhârî", "Bukhari"), "muslim": ("Müslim", "Muslim"),
                "abudawud": ("Ebû Dâvûd", "Abu Dawud"), "tirmidhi": ("Tirmizî", "Tirmidhi"),
                "nasai": ("Nesâî", "Nasa'i"), "ibnmajah": ("İbn Mâce", "Ibn Majah"),
                "nawawi": ("Nevevî, Kırk Hadis", "an-Nawawi's Forty")}
TIRNAKLAR = "\"“”«»‘’'`"


# Kaynak metinlerdeki sondaki notlar ve sık yazım hataları
HADIS_SON_NOT = re.compile(
    r"\s*(Tekrar[ıi]?\s*:|Diğer tahric|Tirmizî rivâyet etmiştir|AÇIKLAMA|İzah için|Bu Hadis(in)? (geçtiği|İleride|ileride)|"
    r"\(Ravi\)|Zevaid|\((Müslim|Buhari|Buhârî|Ebû Dâvûd|Nesâî|İbn Mâce)[^)]*\)?|\(See Hadith|"
    r"Other chains|Abu .Abdur|Sufyan said|\(Sahih\)|A hasan( \(good\))? hadeeth|It was related by|"
    r"\[Imam an-Nawawi|\[Abu .Eisa|Bu Hadis \d+ numara|"
    r"\[(Buhari|Müslim|Tirmizi|Nesai|İbn Mace|Ebu Davud|Kitabu|Al-Bukhari|Bukhari|Muslim|At-Tirmidhi|"
    r"Ibn Majah|Abu Dawud|an-Nasa)[^\]]*\]).*$")
HADIS_DUZELT = {"yapınl": "yapın!", "şahidhği": "şahitliği", "onutn aybmı)": "onun aybını)",
                "Aııah": "Allah", "ResuluIlah": "Resulullah", "(günah}lara": "(günah)lara", "\xad": "",
                "Iki serin": "İki serin", "kî,": "ki,", "cennet'in": "cennetin", "cehennem'den": "cehennemden",
                "onun aybını)": "onun aybını", "üstteki, veren": "Üstteki, veren", "halk'a": "halka",
                "dal'ı": "dalı", "cennet'e": "cennete", "Son Of Adan": "Son of Adam", "ÇÜnkü": "Çünkü",
                "dillini": "dilini", "Siz'den": "Sizden", "alâmeti": "alameti", "yapbğın": "yaptığın",
                "diğer azalan": "diğer azaları", "Allah tan": "Allah'tan", "Şevval'dan": "Şevval'den",
                "yıl(ın günahların) ı": "yılın günahlarını", "(rızası İçin )": "(rızası için)",
                "imanı (nı)": "imanını", "pro longed": "prolonged", "Kith and kin": "kith and kin",
                "a second .": "a second.", 'two."And he indicaed': 'two." And he indicated'}
# Ayıklamadan sonra uygulanan, belirli hadislere özel düzeltmeler (noktalama, kesik başlangıçlar)
HADIS_SON_DUZELT = {
    "zamanı vardır; Birincisi iftar ettiği an diğeri": "zamanı vardır: Birincisi iftar ettiği an, diğeri",
    "yol bulamazlar ve kur’a çekerlerdi": "yol bulamasalardı kur’a çekerlerdi",
    "sevap vardır oruçlunun": "sevap vardır; oruçlunun",
    "bedeldir.” Yani hac gibi sevâb kazandırır.": "bedeldir.",
    "olanınızım.» Not.": "olanınızım.",
    "Resulullah'tan (ﷺ) şunu ezberledim: \"": "",
    "I memorised from the Messenger of Allah (peace and blessings of Allah be upon him): “": "",
    "Günde yüz defa tesbih edenlerin": "Günde yüz defa «Sübhânallâhi ve bihamdihî» diyenin",
    "Subhan Allah wa bihamdihi,' one hundred times a day, will":
        "Whoever says ‘Subhan Allah wa bihamdihi’ one hundred times a day will",
    "I passed by the Prophet (saas) and he said to me: 'O Hazim": "O Hazim",
    'Hâzim "Lâ havle': 'Ey Hâzim! "Lâ havle',
    "O Allah forgive me if You wish. O Allah have mercy on me if You wish.’ Let him":
        "None of you should say: ‘O Allah forgive me if You wish. O Allah have mercy on me if You wish.’ "
        "Let him",
    "Ben kulumun bana ait tahmininin yanındayım bana dua ettiğinde":
        "Ben, kulumun Beni zannı üzereyim; bana dua ettiğinde",
    ' (This term "Haya" covers a large number of concepts which are to be taken together; amongst them are '
    'self respect, modesty, bashfulness, and scruple, etc.)': " (modesty)",
    'has not been granted).': 'has not been granted").',
    "O Allah! Compensate every person who spends":
        "Every day two angels come down; one of them says, ‘O Allah! Compensate every person who spends",
    "Your Cause,' and the other (angel) says, 'O Allah! Destroy every miser.":
        "Your Cause,’ and the other (angel) says, ‘O Allah! Destroy every miser.’",
    "Her gün, dünyaya iki melek iner ve bunlardan biri, Allah'ım! infak eden kişiye, yenisini ver.' "
    "Diğeri de, Allah'ım! Vermeyen'in malını telef et' der.":
        "Her gün dünyaya iki melek iner. Bunlardan biri: ‘Allah'ım! İnfak eden kişiye yenisini ver’ der. "
        "Diğeri de: ‘Allah'ım! Vermeyenin malını telef et’ der.",
    "(his promise )": "(his promise)",
    # --- Son gözden geçirme: anlam birliği (TR/EN), parantez açıklamaları, noktalama ve yazım ---
    # Namaz
    "Beş vakit namaz, bir sonraki cumaya kadar Cuma (namazı) büyük günahlar işlenmediği sürece, aralarındaki "
    "(günah)lara kefarettir.":
        "Beş vakit namaz ve bir Cuma (namazı) bir sonraki Cuma'ya kadar, büyük günahlardan kaçınıldığı sürece "
        "aralarındaki (günah)lara kefarettir.",
    "İki serin vakitteki namazları kim kılarsa cennete girer.":
        "İki serin vakit namazını (sabah ve ikindi) kılan cennete girer.",
    "(`Asr and Fajr)": "('Asr and Fajr)",
    "Her kim Allah için bir mescid bina ederse Allah da onun için Cennette onun mislini bina eder.":
        "Her kim Allah için bir mescit yaparsa, Allah da onun için cennette benzerini yapar.",
    "Namazın anahtarı, taharet (abdest-teyemmüm) dir. Tahrimi (girişi), tekbir almak; tahlili (çıkışı) selam "
    "vermektir.":
        "Namazın anahtarı taharettir (abdest veya teyemmüm). Namaza giriş tekbir almak, namazdan çıkış ise "
        "selam vermektir.",
    "Her kim mescide gidip gelirse her gidip gelmesi karşılığında Allah (Celle Celaluhu) o'na cennetteki yerini "
    "hazırlar.":
        "Her kim sabah akşam (cemaatle namaz için) mescide gidip gelirse, her gidip gelişi için Allah ona "
        "cennette bir ikram yeri hazırlar.",
    "İnsanlar ezan okumakta ve ilk safta namaz kılmanın ne kadar değerli olduğunu bilseler ve kur’a çekmekten "
    "başka yol bulamasalardı kur’a çekerlerdi.":
        "İnsanlar ezan okumanın ve ilk safta namaz kılmanın ne kadar sevaplı olduğunu bilselerdi ve buna kur'a "
        "çekmekten başka yolla ulaşamasalardı, kur'a çekerlerdi.",
    "Geceleyin bir namazı olup da kendisine uyku galebe çalan hiçbir kimse yoktur ki, o kimseye o namazın ecri "
    "yazılmasın ve uykusu da kendisine sadaka olmasın.":
        "Gece (kılmayı âdet edindiği) bir namazı olup da (bir gece) uykuya yenik düşen herkese o namazın sevabı "
        "yazılır; uykusu da ona sadaka olur.",
    "İman ile küfür arasında namaz'ı terk etmek vardır.": "İman ile küfür arasında namazı terk etmek vardır.",
    "Güneşin doğduğu en hayırlı gün; Cuma günüdür. Adem o günde yaratıldı, Cennete o gün girdi ve o gün "
    "Cennet’ten çıkarıldı, kıyamette Cuma günü kopacaktır.":
        "Güneşin doğduğu en hayırlı gün Cuma günüdür. Âdem o gün yaratıldı, o gün cennete girdi ve o gün "
        "cennetten çıkarıldı. Kıyamet de ancak Cuma günü kopacaktır.",
    "spend the entire night": "spent the entire night",
    "Kim günde on iki rekat nafile (namaz) kılarsa o namazlar sebebiyle kendisine cennette bir ev yapılır.":
        "Kim bir gün ve gecede on iki rekât nafile namaz kılarsa, bunlar sebebiyle kendisine cennette bir ev "
        "yapılır.",
    "a house will be built from him": "a house will be built for him",
    "Ezan'ı işittiğiniz zaman, müezzinin söylediklerini tekrarlayın!":
        "Ezanı işittiğiniz zaman, müezzinin söylediklerini (siz de) tekrarlayın!",
    "Mu'adh-dhin": "Mu'adhdhin",
    "Sabah namazının iki rek'ât sünneti, dünyâdan ve dünyâdaki her şey'den daha hayırlıdır.":
        "Sabah namazının iki rekât sünneti, dünyadan ve dünyadaki her şeyden daha hayırlıdır.",
    "Bazı namazlarınızı evinizde kılın!": "(Nafile) namazlarınızın bir kısmını evinizde kılın!",
    "Ya saflarınızı iyice düzeltirsiniz veya Allah (C.C.) yüzlerinizi tersine çevirecektir.":
        "Ya saflarınızı iyice düzeltirsiniz ya da Allah yüzlerinizi tersine çevirir.",
    "Şüphesiz münafıklara en çok ağır gelen namaz, yatsı ve sabah namazlarıdır. Eğer bunlardaki sevabı bilmiş "
    "olsaydılar bu iki namaz (için mescid)'e emekliye emekliye de olsa gelirlerdi.":
        "Münafıklara en ağır gelen namazlar, yatsı ve sabah namazlarıdır. Bu ikisindeki sevabı bilselerdi, "
        "(mescide) emekleyerek de olsa gelirlerdi.",
    # Oruç
    "Yalan söylemeyi ve bu yalancı şahitliği bırakmayan kimsenin yemeyi ve içmeyi bırakmasına Allah'ın asla "
    "ihtiyacı yoktur.":
        "Yalan sözü ve yalanla iş yapmayı bırakmayan kimsenin yemesini ve içmesini bırakmasına Allah'ın hiçbir "
        "ihtiyacı yoktur (yani Allah onun orucunu kabul etmez).",
    "and the joy of when he meets": "and the joy when he meets",
    "diğeri Cennet’te Rabbiyle": "diğeri cennette Rabbiyle",
    "sonra bunun arkasında Şevval'den altı gün oruç tutarsa, onun tutmuş olduğu oruç, yıl boyunca tutulan oruç "
    "gibidir.":
        "sonra arkasından Şevval'den altı gün oruç tutarsa, bütün yılı oruçla geçirmiş gibi olur.",
    "Her kim bir oruçluya iftar yemeği verirse kendisine onun sevâbı kadar sevap vardır; oruçlunun sevâbından "
    "bir şey eksiltmeksizin.":
        "Her kim bir oruçluya iftar ettirirse, oruçlunun sevabından hiçbir şey eksilmeksizin onun sevabı kadar "
        "sevap kazanır.",
    "Allah yolunda cihâd ederken kim bir gün oruç tutarsa Allah bu orucundan dolayı ondan Cehennem ateşini "
    "yetmiş yıl uzaklaştırır.":
        "Kim Allah yolunda bir gün oruç tutarsa, Allah o gün sebebiyle onun yüzünü cehennem ateşinden yetmiş "
        "yıl(lık mesafe) uzaklaştırır.",
    "except that, that day": "except that this day",
    "Allah'ın, Arefe günü orucunu ondan önceki yıla ve ondan sonraki yıla kefaret kılmasını umarım.":
        "Arefe günü orucunun, önceki ve sonraki yılın (günahlarına) kefaret olmasını Allah'tan umarım.",
    "Allah'ın, Aşure günü orucuyla ondan önceki yılın günahlarını bağışlamasını şüphesiz umarım.":
        "Aşure günü orucunun, önceki yılın (günahlarına) kefaret olmasını Allah'tan umarım.",
    "cehennem'in kapıları": "cehennemin kapıları",
    # Abdest
    "Ateşten dolayı vay topukların haline.": "(Abdestte iyi yıkanmayan) topukların ateşten vay haline!",
    "Save your heels from the Hell-fire.": "Save your heels from the Hell-fire (by washing them well in ablution).",
    # Sadaka
    "Sadaka hiçbir zaman malı eksiltmez, Allah affetmesiyle kişinin şerefini artırır. Allah için alçakgönüllülük "
    "gösteren bir kimsenin derecesini Allah yükseltir.":
        "Sadaka malı eksiltmez. Allah, affeden kulunun ancak şerefini artırır. Allah için alçakgönüllü olanı da "
        "Allah yükseltir.",
    "Yarım hurmayla bile olsa cehennemden korunun.":
        "Yarım hurmayı sadaka olarak vermekle de olsa cehennemden korunun.",
    "Her yapılan iyilik sadaka sevâbı kazandırır. Kardeşini güler yüzle karşılamak bir iyilik olduğu gibi kendi "
    "kabından ihtiyacı olan bir şeyi kardeşinin kabına boşaltmakta bir iyilik olup sadaka sevâbı kazandırır.":
        "Her iyilik bir sadakadır. Kardeşini güler yüzle karşılaman ve kovandan (artan suyu) kardeşinin kabına "
        "boşaltman da iyiliktir.",
    "‘Allah'ım! İnfak eden kişiye yenisini ver’": "‘Allah'ım! (Senin yolunda) infak edene yenisini ver’",
    # Güzel ahlak
    "Müslüman, dilinden, elinden müslümanlar selamette kalan kimsedir. Muhacir de Allâh`ın nehyettiğini "
    "terkedendir.":
        "Müslüman, dilinden ve elinden Müslümanların emin olduğu kimsedir. Muhacir (hicret eden) de Allah'ın "
        "yasakladıklarını terk edendir.",
    "Sizden biriniz kendisi için sevdiğini mü’min kardeşi içinde sevmedikçe gerçek mü’min olamaz.":
        "Sizden biriniz, kendisi için sevdiğini mümin kardeşi için de sevmedikçe (gerçek) mümin olamaz.",
    "Güçlü, kuvvetli kişi rakiplerinin sırtını yerine getiren kişi değildir. Asıl güçlü kuvvetli kişi, "
    "öfkelendiği vakit nefsine hakim olabilendir.":
        "Güçlü kişi, (güreşte) rakiplerinin sırtını yere getiren değildir. Asıl güçlü kişi, öfkelendiği vakit "
        "nefsine hâkim olandır.",
    "Allah şüphesiz ki Refik'tir. Kullarının yumuşaklıkla muamele etmelerini sever ve sert davranmakla vermediği "
    "(muvaffakiyet ve sevabı) yumuşaklıkla davranma ile (kuluna) verir.":
        "Şüphesiz Allah Refîk'tir (yumuşak davranandır) ve yumuşaklığı sever. Sertliğe vermediği (sevabı) "
        "yumuşaklığa verir.",
    "Cibril, komşu hakkında o kadar tavsiyede bulundu ki sonunda (kendi kendine) onu mirasçı kılacak, dedim.":
        "Cebrail bana komşu hakkında o kadar tavsiyede bulundu ki, onu (komşusuna) mirasçı kılacak sandım.",
    "Kur’ân-ı öğrenen ve öğretendir.": "Kur'an'ı öğrenen ve öğretendir.",
    "Canım kudret elinde olan Allah’a yemin ederim ki; İman etmeden Cennete giremezsiniz, birbirinizi sevmeden de "
    "iman etmiş olmazsınız. Size yaptığınız takdirde birbirinizi seveceğiniz bir işi göstereyim mi? Selamı "
    "aranızda yaygınlaştırınız.":
        "Canım kudret elinde olan Allah'a yemin ederim ki, iman etmedikçe cennete giremezsiniz; birbirinizi "
        "sevmedikçe de iman etmiş olmazsınız. Yaptığınızda birbirinizi seveceğiniz bir şeyi size göstereyim mi? "
        "Aranızda selamı yayınız.",
    "Çoğu insanın farkına varamadığı iki nimet vardır ki, onlar sağlık ve boş vakittir.":
        "İki nimet vardır ki insanların çoğu onlarda aldanmıştır: sağlık ve boş vakit.",
    "Allah şüphesiz (mükâfatlandırma veya cezalandırma bakımından) sizin suretlerinize ve mallarınıza bakmaz ve "
    "lâkin ancak amellerinize ve kalblerinize bakar.":
        "Allah sizin suretlerinize ve mallarınıza bakmaz; ancak kalplerinize ve amellerinize bakar.",
    "Kim bir müslüman (kardeşinin aybın)ı örterse Allah da onun aybını dünyada ve âhirette örter.":
        "Kim bir Müslümanın ayıbını örterse, Allah da dünyada ve ahirette onun ayıbını örter.",
    "Kıyamet günü mü’minin mizanında hiçbirşey güzel ahlaktan daha ağır değildir. Allah kaba ve ahlaksız "
    "kişileri asla sevmez.":
        "Kıyamet günü müminin mizanında güzel ahlaktan daha ağır gelen hiçbir şey yoktur. Allah, kaba ve "
        "hayâsız kimseye buğzeder.",
    "Ben ve yetimle ilgilenen kişi Cennet’te; şu ikisi gibiyiz diyerek iki parmağını gösterdi.":
        "Ben ve yetime bakan kişi cennette şu ikisi gibiyiz. (Ve işaret parmağı ile orta parmağını gösterdi.)",
    "Sabır, musibet'in darbesini ilk yediğin anda göstereceğin davranıştır.":
        "(Asıl) sabır, musibetin ilk anında gösterilendir.",
    "Batan bir dikene varıncaya kadar Müslüman'a gelip çatan her bir musibet karşılığında Allah, mutlaka onun "
    "günahlarının bir kısmını örter.":
        "Müslümana isabet eden her musibet sebebiyle, ayağına batan bir diken bile olsa, Allah onun "
        "günahlarından bir kısmını mutlaka bağışlar.",
    "Dünya; mü’min için bir hapishane, kafir için ise bir Cennettir.":
        "Dünya mümin için bir zindan, kâfir için ise cennettir.",
    "Ademoğlunun iki vadi dolu altını olsa üçüncü vadinin de kendisinin olmasını ister. Ne var ki insan oğlunun "
    "ağzını ancak toprak doldurur. Yine de Allah tevbe edenin tevbesini kabul eder.":
        "Âdemoğlunun bir vadi dolusu altını olsa, ikincisinin de olmasını ister. Onun ağzını ancak toprak "
        "doldurur. Allah tövbe edenin tövbesini kabul eder.",
    "nothing fills his mouth but dust, Allah turns": "nothing fills his mouth but dust, and Allah turns",
    "Kim rızkının lehine genişletilmesine, ecelinin de geciktirilmesine memnun oluyorsa, o da akrabalık bağını "
    "gözetsin.":
        "Kim rızkının genişletilmesini ve ömrünün uzatılmasını isterse, akrabalık bağını gözetsin.",
    "Who ever is pleased": "Whoever is pleased",
    "Ben de aileme en iyi olanınızım.": "Ben de aileme karşı en iyi olanınızım.",
    "yediyüz katına": "yedi yüz katına",
    "Mümin lanet eden bir kişi olamaz.": "Mümin, çokça lanet eden biri olamaz.",
    "Müslüman'a sövmek fısktır ve onunla çarpışmak küfürdür.":
        "Müslümana sövmek fısk (günah), onunla savaşmak küfürdür (inkârdır).",
    "yaptığı amellerin neticesine": "yaptıkları amellerin karşılığına",
    "İman altmış bu kadar şu`bedir. Haya da iman’ın bir şu`besidir.":
        "İman altmış küsur şubedir (kısımdır). Haya (utanma duygusu) da imanın bir şubesidir.",
    "Ademoğlu ihtiyarladıkça iki yönü gençleşir; uzun ömürlü olmak ve çok mal elde etmek.":
        "Âdemoğlu ihtiyarlar ama onda iki şey gençleşir: yaşama arzusu ve mal hırsı.",
    "best to your women": "best to their women",
    "Kim gereksiz ve günah kazandıran sözlerden dilini korursa her türlü sıkıntıdan ve günahtan kurtulur.":
        "Susan kurtulur. (Yani gereksiz ve günah olan sözlerden dilini koruyan kurtuluşa erer.)",
    "Allah insanlara merhamet etmeyene, merhamet etmez.": "Allah, insanlara merhamet etmeyene merhamet etmez.",
    "Mu'minler bir binanın tuğlaları gibidir, birbirine destek olurlar.":
        "Mümin, mümin için birbirini destekleyen bir binanın tuğlaları gibidir. (Ve parmaklarını birbirine "
        "geçirdi.)",
    "kendi ayağındaki nalınının tasmasından": "ayakkabısının bağından",
    'like these two." And he indicated with his fingers, meaning his index and his middle finger.':
        "like these two. (And he indicated with his index and middle fingers.)",
    'enforce each other." The Prophet (pbuh) then clasped his hands with the fingers interlaced (while saying that).':
        "support each other. (Then he clasped his hands with the fingers interlaced.)",
    "Şüphesiz ahlakı en güzel olanlarınız sizin en hayırlılarınızdandırlar.":
        "Sizin en hayırlılarınız, ahlakı en güzel olanlarınızdır.",
    "Ey müslüman kadınlar! Komşunuza bir koyun paçası bile olsa (hediye vermeyi) önemsiz sanmayın.":
        "Ey Müslüman kadınlar! Hiçbiriniz komşusundan gelen (ya da ona verdiği) hediyeyi, bir koyun paçası "
        "bile olsa küçümsemesin.",
    "Küçüklerimize şefkat etmeyen büyüklerimize": "Küçüklerimize şefkat etmeyen, büyüklerimize",
    "mu'minlerin bir vücuda": "müminlerin bir vücuda",
    "Bir kimseye kardeşinden -karşılaştıkları halde biri yüzünü bir tarafa, öbürü öbür tarafa çevirerek- üç "
    "günden fazla dargın durması helal değildir. Onların hayırlıları ise daha önce selam veren kişidir.":
        "Bir kimsenin, karşılaştıklarında biri bir yana öbürü öbür yana yüz çevirerek din kardeşine üç günden "
        "fazla küs durması helal değildir. İkisinin hayırlısı, önce selam verendir.",
    "İnsanların peygamberlik sözlerinden ilk öğrendiği şey şudur: Şayet utanmıyorsan dilediğini yap!":
        "İnsanların önceki peygamberlerin sözlerinden öğrendiklerinden biri de şudur: Utanmıyorsan dilediğini "
        "yap!",
    # Zikir, dua ve Kur'an
    "Bana bir defa salevât getirene Allah (c.c.) on salevât sevabı verir.":
        "Kim bana bir defa salavat getirirse, Allah da ona on kat rahmet eder.",
    'Ey Hâzim! "Lâ havle ve lâ kuvvete illâ billahi" zikrini çok söyle.':
        "Ey Hâzim! «Lâ havle ve lâ kuvvete illâ billâh» (Güç ve kuvvet ancak Allah'tandır) sözünü çok söyle.",
    "Kur'ân-ı Kerim'de maharetli olan (mu'min), Allah'a itaatkâr ve saygın meleklerle beraberdir. Okuyuşunda "
    "güçlük çekerek ve ayet ile kelimeleri tekrarlamak suretiyle (yâni okuyuşunda pişkin olmayarak) okuyan "
    "(müslüman) a iki sevab vardır.":
        "Kur'an'ı okumada mahir olan, şerefli ve itaatkâr (kâtip) meleklerle beraberdir. Onu zorlanarak, "
        "takılarak okuyana ise iki sevap vardır.",
    "İnsan öldüğü zaman amel defteri kapanır ancak şu üç kişinin defteri kapanmaz, sevap yazılmaya devam eder; "
    "sadakayı cariye (vakıf), kendisinden istifade edilen ilim ve kendisine dua eden hayırlı salih bir çocuk.":
        "İnsan ölünce ameli kesilir; ancak üç şey bundan müstesnadır: sadaka-i câriye (sevabı devam eden "
        "sadaka), kendisinden faydalanılan ilim ve kendisine dua eden salih evlat.",
    "Dua ettim kabul edilmedi denilerek acele edilmediği sürece dualar mutlaka kabul edilir.":
        "Sizden birinin duası, ‘Dua ettim ama kabul edilmedi’ diyerek acele etmedikçe kabul olunur.",
    "Sizden biriniz, Allah’ım dilersen beni bağışla, Allah’ım dilersen bana acı demesin. Duâsını kesin yapsın "
    "çünkü kendisini zorlayan yoktur.":
        "Sizden biriniz ‘Allah'ım, dilersen beni bağışla; Allah'ım, dilersen bana merhamet et’ demesin. "
        "Duasında kararlı olsun; çünkü Allah'ı zorlayabilecek hiç kimse yoktur.",
}
# Gösterilecek kaynak: Nevevî'nin Kırk Hadis'indekiler asıl Kütüb-i Sitte kaynağıyla, Müslim'dekiler
# veri setinin sıra numarası yerine bilinen numarasıyla gösterilir
KAYNAK = {
    ("muslim", 550): ("muslim", 233), ("muslim", 1688): ("muslim", 725),
    ("nawawi", 3): ("bukhari", 8), ("nawawi", 9): ("bukhari", 7288), ("nawawi", 11): ("tirmidhi", 2518),
    ("nawawi", 18): ("tirmidhi", 1987), ("nawawi", 20): ("bukhari", 3483), ("nawawi", 34): ("muslim", 49),
    ("nawawi", 39): ("ibnmajah", 2045),
}
HADIS_FILE = os.path.join(DATA_DIR, "hadisler.json")
HADIS_SURUM = 2  # önbellek biçimi: 2 = ham metinler (ayıklama gösterirken yapılır)
# Seçme hadisler: (kitap, hadith-api numarası, konu). Namaz, oruç, abdest, sadaka ve güzel
# ahlak üzerine; kısa, Türkçesi ve İngilizcesi düzgün olanlar. Buhârî ve Müslim dışındakiler
# "sahih" derecelilerden seçildi.
HADISLER = [
    ("muslim", 550, "namaz"), ("bukhari", 645, "namaz"), ("bukhari", 574, "namaz"), ("ibnmajah", 736, "namaz"),
    ("abudawud", 61, "namaz"), ("bukhari", 662, "namaz"), ("tirmidhi", 225, "namaz"), ("abudawud", 1314, "namaz"),
    ("bukhari", 1923, "oruc"), ("tirmidhi", 699, "oruc"), ("bukhari", 38, "oruc"),
    ("bukhari", 1903, "oruc"), ("tirmidhi", 766, "oruc"), ("ibnmajah", 1716, "oruc"), ("bukhari", 3257, "oruc"),
    ("tirmidhi", 807, "oruc"), ("bukhari", 887, "abdest"), ("tirmidhi", 2029, "sadaka"), ("bukhari", 1417, "sadaka"),
    ("bukhari", 1429, "sadaka"), ("bukhari", 10, "ahlak"), ("tirmidhi", 2515, "ahlak"), ("bukhari", 6114, "ahlak"),
    ("bukhari", 6136, "ahlak"), ("tirmidhi", 2500, "ahlak"), ("abudawud", 4809, "ahlak"), ("ibnmajah", 3688, "ahlak"),
    ("abudawud", 5151, "ahlak"), ("tirmidhi", 2909, "ahlak"), ("tirmidhi", 2688, "ahlak"), ("bukhari", 6412, "ahlak"),
    ("ibnmajah", 4143, "ahlak"), ("bukhari", 6065, "ahlak"), ("ibnmajah", 2544, "ahlak"),
    ("bukhari", 6464, "ahlak"), ("tirmidhi", 2002, "ahlak"), ("tirmidhi", 1918, "ahlak"),
    # Riyâzü's-Sâlihîn'in bölüm konularından (tövbe, sabır, zühd, akraba, zikir, ilim...);
    # Nevevî bu hadisleri Kütüb-i Sitte'den aldığı için kaynak olarak asıl kitap yazılır
    ("bukhari", 1283, "ahlak"), ("bukhari", 5640, "ahlak"), ("tirmidhi", 2324, "ahlak"), ("tirmidhi", 2337, "ahlak"),
    ("bukhari", 55, "sadaka"), ("bukhari", 5985, "ahlak"), ("ibnmajah", 1977, "ahlak"),
    ("abudawud", 1530, "zikir"), ("bukhari", 6405, "zikir"), ("ibnmajah", 3826, "zikir"), ("ibnmajah", 3779, "zikir"),
    ("tirmidhi", 1376, "zikir"), ("tirmidhi", 2618, "namaz"), ("tirmidhi", 488, "namaz"), ("tirmidhi", 221, "namaz"),
    ("abudawud", 1250, "namaz"), ("tirmidhi", 212, "namaz"), ("bukhari", 611, "namaz"), ("tirmidhi", 1623, "oruc"),
    ("ibnmajah", 1730, "oruc"), ("ibnmajah", 1738, "oruc"),
    ("bukhari", 42, "ahlak"), ("bukhari", 33, "ahlak"), ("tirmidhi", 2019, "ahlak"), ("ibnmajah", 69, "ahlak"),
    ("tirmidhi", 1970, "sadaka"), ("tirmidhi", 2014, "ahlak"), ("tirmidhi", 2388, "zikir"),
    ("muslim", 1688, "namaz"), ("bukhari", 432, "namaz"), ("bukhari", 717, "namaz"), ("ibnmajah", 797, "namaz"),
    ("bukhari", 2017, "oruc"), ("tirmidhi", 939, "oruc"), ("bukhari", 165, "abdest"), ("bukhari", 1426, "sadaka"),
    ("bukhari", 1393, "ahlak"), ("bukhari", 9, "ahlak"), ("bukhari", 6340, "zikir"), ("bukhari", 1899, "oruc"),
    ("tirmidhi", 2339, "ahlak"), ("tirmidhi", 1162, "ahlak"), ("tirmidhi", 2501, "ahlak"), ("abudawud", 4681, "ahlak"),
    ("bukhari", 7376, "ahlak"), ("bukhari", 2446, "ahlak"), ("bukhari", 6488, "ahlak"), ("bukhari", 3559, "ahlak"),
    ("ibnmajah", 3682, "sadaka"), ("bukhari", 2566, "ahlak"), ("tirmidhi", 3497, "zikir"),
    ("tirmidhi", 1919, "ahlak"), ("bukhari", 6011, "ahlak"), ("ibnmajah", 3362, "ahlak"), ("bukhari", 1442, "sadaka"),
    ("bukhari", 6077, "ahlak"),
    # İmam Nevevî, Kırk Hadis (el-Erbaîn) — kaynak olarak asıl kitabı gösterilir (KAYNAK)
    ("nawawi", 3, "namaz"), ("nawawi", 9, "ahlak"), ("nawawi", 11, "ahlak"), ("nawawi", 18, "ahlak"),
    ("nawawi", 20, "ahlak"), ("nawawi", 34, "ahlak"), ("nawawi", 39, "ahlak"),
]
HADIS_SURE_MS = 15000  # balon ekranda bu kadar kalır (tıklayınca hemen kapanır)


def hadis_ozu(metin, dil):
    """Rivayet zincirini atıp Peygamber'in sözünü döner ("... şöyle buyurdu: «söz»" → "söz")."""
    t = re.sub(r"\s+", " ", metin or "").strip()
    t = HADIS_SON_NOT.sub("", t)
    for yanlis, dogru in HADIS_DUZELT.items():
        t = t.replace(yanlis, dogru)
    if dil == "tr":
        bulunan = list(re.finditer(r"(buyur\w*|şöyle de\w*|dedi ki)\s*(ki)?\s*[:,;]?\s*", t))
        if bulunan:
            sonrasi = t[bulunan[-1].end():]
            # "...buyurduğu nakledilmiştir: «söz»" gibi: kısa bir ekten sonra gelen ':' işaretini de geç
            sonrasi = re.sub(r"^[^:\"“«]{0,30}:\s*", "", sonrasi)
            # Söz "buyurdu"dan önce de gelebilir: «...» buyurmuştur → tırnak içini al
            # (kesme işareti Türkçede ek ayırdığı için tırnak sayılmaz: "Cerir'in", "iman’ın")
            tirnakli = re.findall(r"[\"“«]([^\"”»“«]{10,})[\"”»]", t[:bulunan[-1].start()])
            t = sonrasi if len(sonrasi.strip(TIRNAKLAR + " .")) >= 10 or not tirnakli else tirnakli[-1]
        t = re.sub(r"^((I|İ)şittim|Demiştir|Söylemiştir|dedi)\W+", "", t, flags=re.I).lstrip("-–— ")
    else:
        # "X said: 'The Messenger said, «söz»'" gibi iç içe aktarımlarda her katmanı soy
        for tur in range(3):
            m = (re.search(r"\b(said|says|say|saying|replied)\b[,:]?\s*(?=[\"“‘'])", t)
                 or re.search(r"\b(said|says|saying)\b\s*:\s*", t))
            if not m or (tur and m.start() > 80):
                break
            t = t[m.end():].lstrip(TIRNAKLAR + " ")
        t = re.sub(r"^Narrated [^:]{1,60}:\s*", "", t).replace("(ﷺ)", "(pbuh)")
    t = t.strip().strip(TIRNAKLAR + " .,;:").strip()
    if t and t[-1] not in ".!?…":
        t += "."
    if not t:
        return ""
    ilk = {"i": "İ", "ı": "I"}.get(t[0], t[0].upper()) if dil == "tr" else t[0].upper()
    t = ilk + t[1:]
    for yanlis, dogru in HADIS_SON_DUZELT.items():
        t = t.replace(yanlis, dogru)
    if dil == "tr":  # kelime içindeki kesme işareti tek tip olsun: Allah’a → Allah'a
        t = re.sub(r"(?<=\w)[’`](?=\w)", "'", t)
    return t


def hadis_kaynagi(kitap, numara, en=False):
    """Balonda gösterilecek kaynak: "— Buhârî, 6114"."""
    kitap, numara = KAYNAK.get((kitap, numara), (kitap, numara))
    ad = KITAP_ADLARI[kitap][en]
    return f"— {ad}, {numara}" if numara else f"— {ad}"


def hadis_onbellegi():
    """İndirilmiş ham hadis metinleri; eski biçimdeki önbellek yok sayılır (yeniden indirilir)."""
    veri = load_json(HADIS_FILE, {})
    if isinstance(veri, dict) and veri.get("_surum") == HADIS_SURUM:
        return veri.get("hadis", {})
    return {}


HADIS_YEDEK_API = "https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions"


def _hadis_json(yol):
    """Önce CDN'den, olmazsa GitHub'dan; sunucu yoğunsa (403/429) kısa bekleyip tekrar dener."""
    son_hata = None
    for deneme in range(3):
        for kok in (HADIS_API, HADIS_YEDEK_API):
            try:
                return json.loads(http_get(f"{kok}/{yol}"))
            except Exception as e:  # ağ/sunucu hatası
                son_hata = e
        time.sleep(1.5 * (deneme + 1))
    raise son_hata


def hadis_indir(kitap, numara):
    """Bir hadisin ham Türkçe ve İngilizce metnini indirir: {"tr": ..., "en": ...}.

    Ham metin saklanır; ayıklama (hadis_ozu) gösterirken yapılır, böylece sonraki
    düzeltmeler yeniden indirmeden uygulanır.
    """
    sonuc = {}
    for dil, onek in (("tr", "tur"), ("en", "eng")):
        veri = _hadis_json(f"{onek}-{kitap}/{numara}.min.json")
        sonuc[dil] = veri["hadiths"][0].get("text", "")
        time.sleep(0.3)  # sunucuyu art arda isteklerle yormamak için
    return sonuc


def eksik_hadisleri_indir(mevcut):
    """Henüz indirilmemiş seçme hadisleri indirir; {"kitap:no": {...}} döner (arka planda çalışır)."""
    yeni = {}
    for kitap, numara, _ in HADISLER:
        anahtar = f"{kitap}:{numara}"
        if anahtar in mevcut:
            continue
        try:
            yeni[anahtar] = hadis_indir(kitap, numara)
        except Exception:
            continue  # bu sefer olmadı; bir sonraki açılışta tekrar denenir
    return yeni


# ---------------------------------------------------------------- astronomik hesap
# Diyanet dışındaki yöntemler için güneşin konumundan vakit hesabı.
#
# Konumun saat dilimi ve yaz saati bilinmediği için öğle anı her gün Diyanet'in o günkü
# güneş doğuşu ve batışının tam ortasından alınır (Diyanet doğuşu 7 dk erken, batışı
# 7 dk geç verdiği için orta nokta değişmez). Böylece her ülkede, yaz saati dahil, doğru olur.

DIYANET_GUNES_TEMKIN = 7 / 60  # saat


def _saat(metin):
    return int(metin[:2]) + int(metin[3:]) / 60


def _julyen(gun):
    """Tarihin UTC gece yarısındaki Jülyen günü."""
    y, m = gun.year, gun.month
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + gun.day + 2 - a + a // 4 - 1524.5


def _gunes(jd):
    """Güneşin deklinasyonu (radyan) ve zaman denklemi (saat)."""
    d = jd - 2451545.0
    g = math.radians((357.529 + 0.98560028 * d) % 360)
    q = (280.459 + 0.98564736 * d) % 360
    boylam = math.radians((q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360)
    egim = math.radians(23.439 - 0.00000036 * d)
    ra = math.degrees(math.atan2(math.cos(egim) * math.sin(boylam), math.cos(boylam))) / 15 % 24
    return math.asin(math.sin(egim) * math.sin(boylam)), (q / 15 - ra + 12) % 24 - 12


def _saat_acisi(yukseklik, deklinasyon, enlem):
    """Güneşin verilen yüksekliğe (derece) geldiği an ile öğle arasındaki süre (saat).

    Güneş o yüksekliğe hiç ulaşmıyorsa (kutuplara yakın yerlerde yazın) None döner.
    """
    x = ((math.sin(math.radians(yukseklik)) - math.sin(deklinasyon) * math.sin(enlem))
         / (math.cos(deklinasyon) * math.cos(enlem)))
    if not -1.0 <= x <= 1.0:
        return None
    return math.degrees(math.acos(x)) / 15


def ogle_farki(gun, diyanet_saatleri):
    """O gün için yerel saat ile güneş saati arasındaki fark (saat dilimi + yaz saati - boylam)."""
    orta = (_saat(diyanet_saatleri[1]) + _saat(diyanet_saatleri[4])) / 2
    return orta + _gunes(_julyen(gun) + 0.5)[1] - 12


def astronomik_vakitler(gun, enlem, fark, yontem, ramazan=False):
    """Verilen gün için 6 vakti ["HH:MM", ...] olarak hesaplar; hesaplanamazsa None.

    fark: ogle_farki() ile bulunan, yerel saatle güneş saati arasındaki fark.
    """
    ayar = YONTEMLER[yontem]
    jd0 = _julyen(gun)
    enlem_r = math.radians(enlem)

    def gunes_an(saat):
        return _gunes(jd0 + (saat - fark) / 24)

    def ogle(saat):
        return 12 + fark - gunes_an(saat)[1]

    def vakit(saat, yukseklik, yon):
        # iki tur: önce tahmini saatte, sonra bulunan saatte güneşin konumuyla
        for _ in range(2):
            dek = gunes_an(saat)[0]
            if yukseklik == "ikindi":  # cismin gölgesi kendi boyu + öğle gölgesi kadar
                yuk = math.degrees(math.atan(1 / (1 + math.tan(abs(enlem_r - dek)))))
            else:
                yuk = yukseklik
            aci = _saat_acisi(yuk, dek, enlem_r)
            if aci is None:
                return None
            saat = ogle(saat) + yon * aci
        return saat

    oglen = ogle(12)
    gunes = vakit(6, -0.833, -1)
    aksam = vakit(18, -0.833, 1)
    ikindi = vakit(15, "ikindi", 1)
    if None in (gunes, aksam, ikindi):
        return None  # güneşin doğmadığı/batmadığı günler: Diyanet vakitleri kullanılır
    # Yüksek enlem kuralı: fecir/yatsı, gecenin (açı/60) payından uzağa düşmesin
    gece = 24 - (aksam - gunes)
    imsak = vakit(5, -ayar["fecir"], -1)
    pay = ayar["fecir"] / 60 * gece
    if imsak is None or gunes - imsak > pay:
        imsak = gunes - pay
    if "yatsi" in ayar:
        yatsi = vakit(20, -ayar["yatsi"], 1)
        pay = ayar["yatsi"] / 60 * gece
        if yatsi is None or yatsi - aksam > pay:
            yatsi = aksam + pay
    else:
        yatsi = aksam + (ayar["yatsi_dk_ramazan"] if ramazan else ayar["yatsi_dk"]) / 60

    def metin(saat):
        dk = min(23 * 60 + 59, max(0, round(saat * 60)))
        return f"{dk // 60:02d}:{dk % 60:02d}"
    return [metin(s) for s in (imsak, gunes, oglen, ikindi, aksam, yatsi)]


# Saat ve saat dilimi her seferinde doğrudan Windows'tan okunur. Python'un kendi saat
# fonksiyonları saat dilimini program açılırken bir kez öğrenir; uygulama açıkken Windows'ta saat
# dilimi değiştirilirse eski dilimle devam ederler.

class SYSTEMTIME(ctypes.Structure):
    _fields_ = [(ad, wt.WORD) for ad in ("wYear", "wMonth", "wDayOfWeek", "wDay",
                                         "wHour", "wMinute", "wSecond", "wMilliseconds")]


class DYNAMIC_TIME_ZONE_INFORMATION(ctypes.Structure):
    _fields_ = [("Bias", wt.LONG), ("StandardName", wt.WCHAR * 32), ("StandardDate", SYSTEMTIME),
                ("StandardBias", wt.LONG), ("DaylightName", wt.WCHAR * 32), ("DaylightDate", SYSTEMTIME),
                ("DaylightBias", wt.LONG), ("TimeZoneKeyName", wt.WCHAR * 128),
                ("DynamicDaylightTimeDisabled", wt.BOOLEAN)]


_k32 = ctypes.windll.kernel32


def windows_saat_dilimi():
    """Windows'ta şu an seçili saat dilimi (her çağrıda güncel)."""
    bilgi = DYNAMIC_TIME_ZONE_INFORMATION()
    _k32.GetDynamicTimeZoneInformation(ctypes.byref(bilgi))
    return bilgi


def simdi():
    """Windows'un şu anki yerel saati (saat dilimi değişse bile anında güncel)."""
    st = SYSTEMTIME()
    _k32.GetLocalTime(ctypes.byref(st))
    return dt.datetime(st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond, st.wMilliseconds * 1000)


def bugun():
    return simdi().date()


def saat_dilimi_imzasi():
    """Saat dilimi değişti mi diye karşılaştırmak için kısa bir özet."""
    bilgi = windows_saat_dilimi()
    return bilgi.TimeZoneKeyName, bilgi.Bias, bool(bilgi.DynamicDaylightTimeDisabled)


def pc_utc_farki(gun):
    """Bilgisayarın (Windows saat dilimi ayarının) o gün öğle vaktindeki UTC farkı, saat cinsinden.
    Windows'un o yıla ait yaz saati kurallarıyla hesaplanır."""
    utc = SYSTEMTIME(wYear=gun.year, wMonth=gun.month, wDay=gun.day, wHour=12)
    yerel = SYSTEMTIME()
    if not _k32.SystemTimeToTzSpecificLocalTimeEx(ctypes.byref(windows_saat_dilimi()), ctypes.byref(utc),
                                                  ctypes.byref(yerel)):
        an = time.mktime((gun.year, gun.month, gun.day, 12, 0, 0, 0, 0, -1))  # yedek yol
        return time.localtime(an).tm_gmtoff / 3600
    fark = dt.datetime(yerel.wYear, yerel.wMonth, yerel.wDay, yerel.wHour, yerel.wMinute) - \
        dt.datetime(gun.year, gun.month, gun.day, 12)
    return fark.total_seconds() / 3600


# Diyanet ülke kimliği -> o ülkede yıl boyunca görülen UTC farkları (dakika, yaz saati dahil).
# IANA saat dilimi verisinden üretildi; bilgisayarın farkı bunların dışındaysa saat dilimi yanlış seçilmiştir.
ULKE_UTC_FARKLARI = {
    "1": (120, 180), "2": (180,), "3": (60, 120), "4": (60, 120), "5": (240,), "6": (120, 180),
    "7": (60, 120), "8": (60, 120), "9": (60, 120), "10": (60, 120), "11": (60, 120), "12": (60, 120),
    "13": (60, 120), "14": (60, 120), "15": (0, 60), "16": (60, 120), "17": (60, 120), "18": (60, 120),
    "19": (60, 120), "20": (120, 180), "21": (60, 120), "22": (120, 180), "23": (0, 60, 120), "24": (60, 120),
    "25": (60, 120), "26": (60, 120), "27": (60, 120), "28": (60, 120), "29": (180,), "30": (60, 120),
    "31": (60, 120), "32": (0, 60), "33": (-600, -540, -480, -420, -360, -300, -240), "34": (60, 120),
    "35": (60, 120), "36": (60, 120), "37": (120, 180), "38": (60, 120), "39": (60, 120), "40": (120, 180),
    "41": (120, 180), "42": (120, 180), "44": (120, 180), "45": (-60, 0, 60), "46": (120, 180),
    "47": (120, 180), "48": (-240, -180, -120, -60, 0), "49": (60, 120), "51": (-240, -180),
    "52": (-480, -420, -360, -300, -240, -210, -180, -150), "53": (-480, -420, -360, -300),
    "54": (-300, -240), "55": (120,), "56": (660,), "57": (-300,), "58": (-240,),
    "59": (480, 525, 570, 600, 630, 660), "60": (420, 480), "61": (360, 480), "62": (240,), "63": (60,),
    "64": (180,), "65": (120,), "66": (-240,), "67": (120,), "68": (-240,), "69": (-300,), "70": (-300, -240),
    "71": (0,), "72": (-240,), "73": (0,), "74": (330,), "75": (180,), "76": (345,), "77": (300,),
    "79": (60,), "80": (60,), "81": (120,), "82": (-240,), "83": (-240,), "84": (60,), "85": (600, 660),
    "86": (60,), "87": (-240,), "88": (180,), "89": (-300,), "90": (-240,), "91": (0,), "92": (300,),
    "93": (240,), "94": (180,), "95": (180,), "96": (-240,), "97": (480,), "98": (180,), "99": (-360,),
    "100": (480,), "101": (300,), "102": (0,), "103": (300,), "104": (240,), "105": (-360,), "106": (0,),
    "107": (480,), "108": (480,), "109": (0,), "110": (180,), "111": (0,), "112": (240,), "113": (480,),
    "114": (180,), "115": (660,), "116": (540,), "117": (420, 480, 540), "118": (60,), "119": (-300,),
    "120": (0,), "122": (0,), "123": (-240,), "124": (180,), "125": (-240,), "126": (480,), "127": (60,),
    "128": (540,), "129": (120,), "130": (780,), "131": (300,), "132": (180,), "133": (180,), "134": (420,),
    "135": (420,), "136": (-240,), "137": (420,), "138": (240,), "139": (-360, -300), "140": (60,),
    "141": (-360,), "142": (540,), "143": (0,), "144": (-60,), "145": (0, 60),
    "146": (-300, -240, -180, -120), "147": (-240,), "148": (180,), "149": (540,), "150": (180,),
    "151": (120,), "152": (0,), "153": (-240,), "154": (390,), "155": (360,), "156": (60,), "157": (180,),
    "158": (120,), "159": (300,), "160": (180,), "161": (420,), "162": (-360,), "163": (60, 120),
    "164": (240,), "165": (-360,), "166": (270,), "167": (120,), "168": (360,), "169": (600,), "170": (120,),
    "171": (-240,), "172": (-180,), "173": (240,), "174": (120,), "175": (180,), "176": (540,), "177": (360,),
    "178": (-660,), "179": (480,), "180": (60, 120), "181": (60,), "182": (-360,), "183": (-480,),
    "184": (60,), "185": (600, 660), "186": (-240,), "187": (330,), "188": (-240,), "189": (120, 180),
    "191": (180,), "192": (180,), "193": (720, 765, 780, 825), "194": (-180,), "196": (120,), "197": (720,),
    "198": (780,), "199": (-180,), "200": (-360, -300, -240, -180), "201": (-180,), "202": (210,),
    "203": (120,), "204": (120, 180), "205": (120, 180), "206": (120, 180),
    "207": (120, 180, 240, 300, 360, 420, 480, 540, 600, 660, 720), "208": (180,), "209": (-300, -240),
    "210": (0,), "212": (0, 60), "213": (0,), "214": (120,), "216": (120,),
}


def saat_dilimi_uyumsuz(ulke_id, gunler):
    """Bilgisayarın saati seçilen şehrin saatiyle uyuşmuyor mu? (Kalan süreler o zaman kayar.)

    Türkiye yıl boyu UTC+3 olduğu için kesin kontrol edilir. Diğer ülkelerde şehrin yaz saati
    geçişleri Diyanet vakitlerinden çıkarılıp bilgisayarınkiyle karşılaştırılır: düzenler farklıysa
    "yerel saat - güneş saati" farkı yıl içinde oynar. (İkisi de yaz saati kullanmıyor ve aradaki
    fark sabitse bu yöntem fark edemez.)
    """
    if not gunler:
        return False
    izinli = ULKE_UTC_FARKLARI.get(str(ulke_id))
    if izinli and round(pc_utc_farki(bugun()) * 60) not in izinli:
        return True  # bilgisayarın şu anki farkı o ülkede hiçbir yerde, hiçbir mevsimde görülmüyor
    if ulke_id == TURKIYE[1]:
        ilk = bugun()
        return any(abs(pc_utc_farki(ilk + dt.timedelta(days=i)) - 3) > 0.01 for i in range(0, 366, 7))
    farklar = []
    for tarih in sorted(gunler)[::7]:
        try:
            gun = dt.date.fromisoformat(tarih)
            farklar.append(pc_utc_farki(gun) - ogle_farki(gun, gunler[tarih]))
        except (ValueError, IndexError, OverflowError):
            continue
    return len(farklar) > 4 and max(farklar) - min(farklar) > 0.5


def enlem_tahmini(gunler):
    """Diyanet'in güneş doğuşu/batışı saatlerinden yerin enlemi (gün uzunluğu enleme bağlıdır).

    Ekinoks yakınında gün uzunluğu enlemden pek etkilenmediği için o günler kullanılmaz.
    """
    enlemler = []
    for tarih, saatler in gunler.items():
        try:
            gun = dt.date.fromisoformat(tarih)
            dogus = _saat(saatler[1]) + DIYANET_GUNES_TEMKIN
            batis = _saat(saatler[4]) - DIYANET_GUNES_TEMKIN
        except (ValueError, IndexError):
            continue
        dek = _gunes(_julyen(gun) + 0.5)[0]
        if abs(math.degrees(dek)) < 12 or not 0 < batis - dogus < 24:
            continue
        hedef = math.cos(math.radians(15 * (batis - dogus) / 2))
        alt, ust = -70.0, 70.0
        for _ in range(40):  # ikiye bölme ile enlemi bul
            orta_enlem = (alt + ust) / 2
            e = math.radians(orta_enlem)
            deger = ((math.sin(math.radians(-0.833)) - math.sin(dek) * math.sin(e))
                     / (math.cos(dek) * math.cos(e)))
            # kuzey yarımkürede yazın enlem arttıkça gün uzar (deger azalır)
            if (deger > hedef) == (dek > 0):
                alt = orta_enlem
            else:
                ust = orta_enlem
        enlemler.append((alt + ust) / 2)
    if not enlemler:
        return None
    enlemler.sort()
    return enlemler[len(enlemler) // 2]


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


def logo_icinde(x, y, R):
    """Logodaki altın kısım: sekiz köşeli Selçuklu yıldızının (iç içe iki kare) içinde, ortadaki
    lacivert dairenin dışında; ya da o dairenin içindeki hilalde. Merkez (0, 0), R yıldızın köşesi."""
    a = R / math.sqrt(2)  # karelerin yarı kenarı
    if not ((abs(x) <= a and abs(y) <= a) or abs(x + y) <= R and abs(x - y) <= R):
        return False
    if x * x + y * y > (0.545 * R) ** 2:
        return True
    hx, hy = x / (0.364 * R), y / (0.364 * R)  # hilal, logodaki oranlarla
    return hx * hx + hy * hy <= 1 and (hx - 0.39) ** 2 + (hy + 0.28) ** 2 > 0.69


def hilal_resmi(R, renk, zemin, icinde=hilal_icinde):
    """Kenarları yumuşatılmış hilal (ya da 'icinde' ile verilen şekil) resmi; dışı saydam.
    Kenarlar zemin rengine karışır."""
    boy = int(math.ceil(2 * R)) + 2
    merkez = boy / 2
    (r1, g1, b1), (r2, g2, b2) = _rgb(renk), _rgb(zemin)
    img = tk.PhotoImage(width=boy, height=boy)
    satirlar, bos = [], []
    ornek = 4  # her pikselde 4x4 örnek
    for py in range(boy):
        satir = []
        for px in range(boy):
            dolu = sum(icinde(px + (i + 0.5) / ornek - merkez, py + (j + 0.5) / ornek - merkez, R)
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


_kutu_sayaci = 0


def _dolu_kutu(canvas, x1, y1, x2, y2, r, renk, etiket):
    """Köşeleri gerçek daire olan dolu kutu (x2, y2 dahil). Çokgen yerine Windows'un
    daire çizimi kullanıldığı için kenarlar küçük boyutta da basamaklı görünmez."""
    d = 2 * r
    ayar = {"fill": renk, "outline": "", "tags": etiket}
    for ox, oy in ((x1, y1), (x2 + 1 - d, y1), (x1, y2 + 1 - d), (x2 + 1 - d, y2 + 1 - d)):
        # Tk dolu dairenin sağ/alt kenar pikselini de boyar: d çaplı daire için bitiş ox+d-1
        canvas.create_oval(ox, oy, ox + d - 1, oy + d - 1, **ayar)
    canvas.create_rectangle(x1 + r, y1, x2 + 1 - r, y2 + 1, **ayar)
    canvas.create_rectangle(x1, y1 + r, x2 + 1, y2 + 1 - r, **ayar)


def yuvarlak_kutu(canvas, x1, y1, x2, y2, r, fill, outline=""):
    """Yuvarlak köşeli kutu çizer; tüm parçaları taşıyan etiketi döner."""
    global _kutu_sayaci
    _kutu_sayaci += 1
    etiket = f"kutu{_kutu_sayaci}"
    x1, y1, x2, y2 = round(x1), round(y1), round(x2), round(y2)
    r = int(min(r, (x2 - x1 + 1) / 2, (y2 - y1 + 1) / 2))
    if outline:  # 1 piksellik çerçeve: dışta çerçeve rengi, 1 piksel içeride zemin
        _dolu_kutu(canvas, x1, y1, x2, y2, r, outline, etiket)
        _dolu_kutu(canvas, x1 + 1, y1 + 1, x2 - 1, y2 - 1, max(0, r - 1), fill, etiket)
    else:
        _dolu_kutu(canvas, x1, y1, x2, y2, r, fill, etiket)
    return etiket


# ---------------------------------------------------------------- Windows

def kaynak_yolu(dosya):
    """Uygulamayla gelen dosyanın yolu (.exe içinde de, .py olarak çalışırken de)."""
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), dosya)


def tek_kopya_mi(bekle_sn=0):
    """Uygulama zaten açıksa False döner.

    bekle_sn: güncellemeden sonra yeniden başlarken eski sürüm kapanana kadar bu kadar bekler.
    """
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = wt.HANDLE
    son = time.monotonic() + bekle_sn
    while True:
        tutamak = k32.CreateMutexW(None, False, "Local\\EzanVaktiTekKopya")
        if k32.GetLastError() != 183:  # ERROR_ALREADY_EXISTS değilse bu kopya tek
            return True
        k32.CloseHandle(tutamak)
        if time.monotonic() >= son:
            return False
        time.sleep(0.2)


# ---------------------------------------------------------------- güncelleme

def surum_tuple(metin):
    return tuple(int(x) for x in re.findall(r"\d+", metin)[:3])


def son_surum_bilgisi():
    """GitHub'daki en son sürüm: {"surum", "url", "boyut", "sha256", "sayfa"}."""
    veri = json.loads(http_get(GUNCELLEME_API))
    exe = next(a for a in veri.get("assets", []) if a.get("name") == EXE_ADI)
    sha = (exe.get("digest") or "").removeprefix("sha256:").lower()
    if not sha:  # GitHub parmak izi vermezse sürümle yüklenen .sha256 dosyasına bak
        ek = next((a for a in veri["assets"] if a.get("name") == EXE_ADI + ".sha256"), None)
        sha = http_get(ek["browser_download_url"]).split()[0].lower() if ek else ""
    return {"surum": veri["tag_name"].lstrip("vV"), "url": exe["browser_download_url"],
            "boyut": int(exe["size"]), "sha256": sha, "sayfa": veri["html_url"]}


def guncellemeyi_indir(bilgi, hedef):
    """Yeni .exe'yi hedef + '.new' olarak indirir; boyutu ve SHA-256 parmak izi tutmazsa hata verir."""
    if not bilgi["url"].startswith(GUNCELLEME_ONEKI) or not re.fullmatch(r"[0-9a-f]{64}", bilgi["sha256"]):
        raise ValueError("Güvenilmeyen güncelleme bilgisi")
    yeni = hedef + ".new"
    ozet = hashlib.sha256()
    req = urllib.request.Request(bilgi["url"], headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r, open(yeni, "wb") as f:
        while parca := r.read(1 << 16):
            f.write(parca)
            ozet.update(parca)
    if os.path.getsize(yeni) != bilgi["boyut"] or ozet.hexdigest() != bilgi["sha256"]:
        os.remove(yeni)
        raise ValueError("İndirilen dosya doğrulanamadı")
    return yeni


def guncellemeyi_kur(yeni, hedef):
    """Çalışan .exe'nin yerine yenisini koyar (çalışan dosya silinemez ama yeniden adlandırılabilir)."""
    eski = hedef + ".old"
    if os.path.exists(eski):
        os.remove(eski)
    os.replace(hedef, eski)
    try:
        os.replace(yeni, hedef)
    except OSError:
        os.replace(eski, hedef)  # yenisi konamadıysa eskisini geri koy
        raise


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


# Sayaç ve balon hiçbir zaman klavye/fare odağını almamalı: tam ekran (pencereli) oyunlarda öne
# geçince oyun girişleri kesiliyordu. Tk'nin "-topmost" ve lift() çağrıları pencereyi etkinleştirebildiği
# için üstte tutma işi doğrudan SWP_NOACTIVATE ile yapılır.
GWL_EXSTYLE, WS_EX_NOACTIVATE = -20, 0x08000000
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
HWND_TOPMOST = wt.HWND(-1)
_user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
_user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
_user32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
_user32.GetForegroundWindow.restype = wt.HWND
_user32.SetForegroundWindow.argtypes = [wt.HWND]
_user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]


def _hwnd(pencere):
    return int(pencere.wm_frame(), 16)


def odak_almasin(pencere):
    """Pencereye tıklansa da etkinleşmesin; odak o an hangi programdaysa orada kalsın."""
    h = _hwnd(pencere)
    _user32.SetWindowLongW(h, GWL_EXSTYLE, _user32.GetWindowLongW(h, GWL_EXSTYLE) | WS_EX_NOACTIVATE)


def ustte_tut(pencere):
    _user32.SetWindowPos(_hwnd(pencere), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def on_pencere():
    return _user32.GetForegroundWindow()


def odagi_geri_ver(onceki):
    """Yeni açılan pencerelerimizden biri odağı kaptıysa odağı önceki programa (ör. oyuna) geri verir."""
    simdiki = on_pencere()
    if not onceki or not simdiki or simdiki == onceki:
        return
    pid = wt.DWORD()
    _user32.GetWindowThreadProcessId(simdiki, ctypes.byref(pid))
    if pid.value == os.getpid():
        _user32.SetForegroundWindow(onceki)


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


_winmm = ctypes.windll.winmm
SES_UZANTILARI = "*.wav *.mp3 *.m4a *.aac *.wma *.flac"


def _mci(komut):
    return _winmm.mciSendStringW(komut, None, 0, None)


def mci_durdur():
    _mci("close ezan_ses")


def mci_cal(yol, volume):
    """WAV dışındaki dosyaları (mp3, m4a, wma...) Windows'un kendi oynatıcısıyla (MCI) çalar."""
    mci_durdur()
    if _mci(f'open "{yol}" type mpegvideo alias ezan_ses'):
        return False
    _mci(f"setaudio ezan_ses volume to {round(1000 * (max(0, min(volume, 100)) / 100) ** 2)}")
    return _mci("play ezan_ses") == 0


def ses_cal(sound, sound_file, volume):
    mci_durdur()
    if sound == "custom" and sound_file and not sound_file.lower().endswith(".wav"):
        winsound.PlaySound(None, 0)
        if not (os.path.exists(sound_file) and mci_cal(sound_file, volume)):
            threading.Thread(target=winsound.Beep, args=(880, 400), daemon=True).start()
        return

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
        self._hesaplanan = (None, {})  # (anahtar, astronomik yöntemle hesaplanmış vakitler)
        self._konum = (None, None)  # (anahtar, ilçenin tahmini (enlem, boylam))
        self.hadisler = hadis_onbellegi()  # indirilmiş ham hadis metinleri
        self.hadis_iniyor = False
        self.son_hadisler = []  # aynı hadis kısa sürede tekrar gelmesin
        self.hadis_fired = set()
        self.hadis_hedef = None
        self.balon = None
        self.guncelleme_suruyor = False
        self.acilis_zamani = time.monotonic()
        self.saat_dilimi = saat_dilimi_imzasi()

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
        self.root.bind("<Button-3>", self.menu_ac)
        self.root.bind("<Double-Button-1>", lambda e: self.open_settings())  # menüyü bulamayanlar için
        self.root.bind("<Control-MouseWheel>", self.wheel_resize)

        onceki = on_pencere()
        self.apply_config()
        self.root.update_idletasks()
        odak_almasin(self.root)
        odagi_geri_ver(onceki)
        self.root.after(100, self.poll)
        self.tick()
        if not self.cfg["district_url"]:
            self.root.after(300, self.open_settings)
        if self.cfg["hadis_uyari"] or self.cfg["hadis_vakit"]:  # açılışı yavaşlatmasın diye biraz sonra
            self.root.after(5000, self.hadis_indirmeyi_baslat)
        self.saat_dilimi_uyarildi = False
        self.root.after(3000, self.saat_dilimi_uyar)

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
        self.menu.add_command(label=self.t("menu_hadith"), command=lambda: self.hadis_goster(manuel=True))
        self.menu.add_command(label=self.t("menu_refresh"), command=lambda: self.fetch(force=True))
        self.menu.add_command(label=self.t("menu_update"), command=lambda: self.guncelleme_denetle(manuel=True))
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
        # Dil ya da görünüm değiştiyse açık balon da yeni haline geçsin (sadece genişletme gibi
        # değişikliklerde yeniden çizilmez)
        gorunum = tuple(self.cfg[k] for k in ("language", "theme", "opacity", "size"))
        if gorunum != getattr(self, "_balon_gorunumu", gorunum):
            self.balonu_yenile()
        self._balon_gorunumu = gorunum

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
        # pencere tam piksele yukarı yuvarlanır (render); çerçeve son pikselin içinde kalsın
        w, h = math.ceil(w), math.ceil(h)
        if yaricap:
            oge = yuvarlak_kutu(c, 0, 0, w - 1, h - 1, yaricap, fill=renk["bg"], outline=renk["line"])
        else:
            oge = c.create_rectangle(0, 0, w - 1, h - 1, fill=renk["bg"], outline=renk["sub"])
        c.tag_lower(oge)

    def tarih_satirlari(self, gun):
        """Tek satırlık tarih seçenekleri, uzundan kısaya; sığan ilki gösterilir.

        Önce "31 Ekim 2026 · 20 Cemaziyelevvel 1448", sonra kısa biçimler
        ("31.10.2026 · 20 C.evvel 1448"), en son sadece hicrî tarih.
        """
        hicri = self.cache.get("hijri", {}).get(gun.isoformat(), "") \
            if self.cache.get("district_id") == self.cfg["district_id"] else ""
        if self.cfg["language"] == "en":
            for tr, en in HICRI_AY_EN.items():
                hicri = hicri.replace(tr, en)
            uzun = f"{gun.day} {AY_EN[gun.month - 1][:3]} {gun.year}"
        else:
            uzun = f"{gun.day} {list(AYLAR)[gun.month - 1]} {gun.year}"
        kisa = f"{gun.day:02d}.{gun.month:02d}.{gun.year}"
        if not hicri:
            return uzun, kisa
        hicri_kisa = hicri
        for uzun_ad, kisa_ad in HICRI_AY_KISA.items():
            hicri_kisa = hicri_kisa.replace(uzun_ad, kisa_ad)
        return (f"{uzun} · {hicri}", f"{kisa} · {hicri}", f"{uzun} · {hicri_kisa}",
                f"{kisa} · {hicri_kisa}", hicri, hicri_kisa)

    def alt_bilgi(self, view, x, y, anchor, font, genislik):
        """Tarihi (sığan biçimiyle) ve konumu yazar; yeni y değerini döner."""
        secenekler = view[7]
        tarih = next((m for m in secenekler if font.measure(m) <= genislik), secenekler[-1])
        satir = font.metrics("linespace")
        for metin in (tarih, self.konum_adi()):
            self.yazi(x, y, metin, font, self.colors["sub"], anchor)
            y += satir
        return y

    def alt_bilgi_genislik(self, view, font):
        # pencere en fazla "31.10.2026 · 20 C.evvel 1448" sığacak kadar genişler
        secenekler = view[7]
        tarih = secenekler[3] if len(secenekler) == 6 else secenekler[-1]
        return max(font.measure(tarih), font.measure(self.konum_adi()))

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
        self.canvas.configure(width=math.ceil(w), height=math.ceil(h))

    def ciz_mesaj(self, metin):
        s = self.cfg["size"]
        f = self.font(s * 0.85, True)
        pad = s
        w, h = f.measure(metin) + 2 * pad, f.metrics("linespace") + s
        self.yazi(w / 2, h / 2, metin, f, self.colors["fg"], "center")
        self.zemin(w, h, 0 if self.cfg["style"] == "klasik" else s * 0.8)
        return w, h

    def ciz_klasik(self, view, expanded):
        _, ad, sure, yakin, _, saatler, gecmis, _ = view
        renk, s = self.colors, self.cfg["size"]
        ana, kucuk, minik = self.font(s, True), self.font(s * 0.8), self.font(s * 0.65)
        pad = s * 0.75 + 2
        metin = self.ana_metin(ad, sure)
        w = ana.measure(metin) + 2 * pad
        satir = kucuk.metrics("linespace")
        if expanded:
            adlar = max(kucuk.measure(self.vakit_adi(v)) for v in VAKITLER)
            w = max(w, adlar + kucuk.measure("00:00") + 3 * pad,
                    self.alt_bilgi_genislik(view, minik) + 2 * pad)
        y = max(2, s // 4)
        self.yazi(w / 2, y, metin, ana, renk["warn"] if yakin else renk["fg"], "n")
        y += ana.metrics("linespace") + max(2, s // 4)
        if expanded:
            for i, v in enumerate(VAKITLER):
                r = renk["warn"] if v == ad else renk["fg"]
                self.yazi(pad, y, self.vakit_adi(v), kucuk, r)
                self.yazi(w - pad, y, saatler[i] if saatler else "--:--", kucuk, r, "ne")
                y += satir
            y = self.alt_bilgi(view, w / 2, y + 2, "n", minik, w - 2 * pad) + s // 3
        self.zemin(w, y, 0)
        return w, y

    def ciz_kart(self, view, expanded):
        _, ad, sure, yakin, ilerleme, saatler, gecmis, _ = view
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
            ic = max(ic, adlar + satir_kalin.measure("00:00") + s * 2, self.alt_bilgi_genislik(view, minik))
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
            y = self.alt_bilgi(view, pad, y + s * 0.35, "nw", minik, ic) + pad * 0.5
        h = y
        self.zemin(w, h, s * 0.9)
        return w, h

    def ciz_hap(self, view, expanded):
        _, ad, sure, yakin, _, saatler, gecmis, _ = view
        renk, s = self.colors, self.cfg["size"]
        kalin, ince = self.font(s, True), self.font(s)
        minik = self.font(s * 0.65)
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
            w = max(icerik + 2 * pad, 3 * hucre_w + 2 * ara + 2 * pad,
                    self.alt_bilgi_genislik(view, minik) + 2 * pad)
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
        h = self.alt_bilgi(view, w / 2, y0 + 2 * hucre_h + ara + s * 0.4, "n", minik, w - 2 * pad) + pad * 0.7
        self.zemin(w, h, s * 0.9)
        return w, h

    def konum_adi(self):
        if not self.cfg["district_name"]:
            return ""
        il, ilce = self.cfg["state_name"], self.cfg["district_name"]
        ad = il if il == ilce else f"{ilce} / {il}"
        if self.cfg["calc"] != "diyanet":
            ad += " · " + HESAPLAR[self.cfg["calc"]][2 + (self.cfg["language"] == "en")]
        return ad

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
        self._pos = (x, y)
        self.root.geometry(f"+{x}+{y}")
        if self.balon:  # sayaç büyüyüp küçülünce ya da yer değiştirince balon da uysun
            self.balon.konumla()

    def toggle_expanded(self):
        self.cfg["expanded"] = not self.cfg["expanded"]
        self.save_config()
        self.apply_config()
        if self.settings and self.settings.win.winfo_exists():
            self.settings.mod.set("extended" if self.cfg["expanded"] else "compact")

    def menu_ac(self, e):
        # Kullanıcı bilerek sağ tıkladı: menü düzgün kapanabilsin diye yalnızca bu an odağı al
        _user32.SetForegroundWindow(_hwnd(self.root))
        self.menu.tk_popup(e.x_root, e.y_root)

    def wheel_resize(self, e):
        yeni = self.cfg["size"] + (1 if e.delta > 0 else -1)
        self.cfg["size"] = max(BOYUT_MIN, min(BOYUT_MAX, yeni))
        self.save_config()
        self.apply_config()

    # -------------------------------------------------- sürükleme ve kenara yapışma

    def drag_start(self, e):
        self._drag = (e.x_root, e.y_root) + self._pos
        self._moved = False
        self._snap = (self.cfg["snap_x"], self.cfg["snap_y"])
        self._hold_job = self.root.after(BASILI_TUTMA_MS, self.held)

    def held(self):
        """Kompakt moddayken basılı tutuldu: bırakılana kadar tüm vakitleri göster."""
        self._hold_job = None
        if not self.cfg["expanded"]:
            self.peeking = True
            self.apply_config()
            # pencere büyüyüp yer değiştirmiş olabilir: sürükleme buradan devam etsin
            px, py = self.root.winfo_pointerxy()
            self._drag = (px, py) + self._pos

    def cancel_hold(self):
        if getattr(self, "_hold_job", None):
            self.root.after_cancel(self._hold_job)
            self._hold_job = None

    def drag_move(self, e):
        sx, sy, wx, wy = self._drag
        dx, dy = e.x_root - sx, e.y_root - sy
        if not self._moved and abs(dx) + abs(dy) > SURUKLEME_ESIGI:
            # sürükleme başladı; açılmış geçici görünüm bırakılana kadar açık kalır
            self.cancel_hold()
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
        self._pos = (x, y)
        self.root.geometry(f"+{x}+{y}")
        if self.balon:  # açık hadis balonu sayaçla birlikte gelsin
            self.balon.konumla()

    def drag_end(self, e):
        self.cancel_hold()
        self.dragging = False
        if self._moved:
            self.cfg["x"], self.cfg["y"] = self._pos
            self.cfg["snap_x"], self.cfg["snap_y"] = self._snap
            self.save_config()
        if self.peeking:  # geçici görünümü kapat; pencere yapıştığı kenarda küçülür
            self.peeking = False
            self.apply_config()

    # -------------------------------------------------- vakitler

    def fetch(self, force=False):
        if self.fetching or not self.cfg["district_url"]:
            return
        self.fetching = True
        self.last_attempt = simdi()
        self.run_bg(get_vakitler, lambda r, e: self.fetched(r, e, force), self.cfg["district_url"])

    def fetched(self, sonuc, error, force):
        self.fetching = False
        if error:
            if force:
                messagebox.showerror(self.t("app"), f"{self.t('fetch_err')}\n{error}")
            return
        days, hicri = sonuc
        if self.cache.get("district_id") != self.cfg["district_id"]:
            self.cache = {"district_id": self.cfg["district_id"], "days": {}}
            self.saat_dilimi_uyarildi = False  # yeni şehir: uyarı bu oturumda daha önce gösterildiyse de yine göster
        self.cache["days"].update(days)
        self.cache.setdefault("hijri", {}).update(hicri)
        # 40 günden eski kayıtları sil
        sinir = (bugun() - dt.timedelta(days=40)).isoformat()
        self.cache["days"] = {k: v for k, v in self.cache["days"].items() if k >= sinir}
        self.cache["hijri"] = {k: v for k, v in self.cache["hijri"].items() if k >= sinir}
        self.cache["fetched"] = bugun().isoformat()
        save_json(CACHE_FILE, self.cache)
        self.update_display()
        self.saat_dilimi_uyar()  # yeni şehrin vakitleri geldi: saat dilimi uyuşuyor mu?
        if self.settings and self.settings.win.winfo_exists():
            self.settings.saat_dilimi_etiketi()

    def need_fetch(self):
        if not self.cfg["district_url"] or self.fetching:
            return False
        if self.cache.get("district_id") != self.cfg["district_id"]:
            return True
        if self.last_attempt and simdi() - self.last_attempt < dt.timedelta(minutes=10):
            return False
        return self.cache.get("fetched") != bugun().isoformat()

    def days(self):
        if self.cache.get("district_id") != self.cfg["district_id"]:
            return {}
        gunler = self.cache.get("days", {})
        yontem = self.cfg["calc"]
        if yontem not in YONTEMLER or not gunler:
            return gunler
        # Yerin enlemi Diyanet vakitlerinden bir kez çıkarılır
        konum_anahtar = (self.cfg["district_id"], id(gunler))
        if self._konum[0] != konum_anahtar:
            self._konum = (konum_anahtar, enlem_tahmini(gunler))
        enlem = self._konum[1]
        if enlem is None:
            return gunler
        # Sadece dün, bugün ve yarın hesaplanır; gün değişene kadar saklanır
        gun0 = bugun()
        anahtar = (konum_anahtar, yontem, gun0)
        if self._hesaplanan[0] != anahtar:
            hicri = self.cache.get("hijri", {})
            hesap = {}
            for gun_farki in (-1, 0, 1):
                gun = gun0 + dt.timedelta(days=gun_farki)
                diyanet = gunler.get(gun.isoformat())
                if not diyanet:
                    continue
                ramazan = "Ramazan" in hicri.get(gun.isoformat(), "")
                hesap[gun.isoformat()] = astronomik_vakitler(
                    gun, enlem, ogle_farki(gun, diyanet), yontem, ramazan) or diyanet
            self._hesaplanan = (anahtar, hesap)
        return self._hesaplanan[1]

    # -------------------------------------------------- her saniye

    def tick(self):
        if self.tick_count % 2 == 0:  # Windows'ta saat dilimi değiştirildi mi? (çok hafif bir kontrol)
            imza = saat_dilimi_imzasi()
            if imza != self.saat_dilimi:
                self.saat_dilimi = imza
                self.saat_dilimi_degisti()
        if self.need_fetch():
            self.fetch()
        # Günde bir kez, açılıştan 1 dakika sonra (açılışı yavaşlatmasın) güncelleme denetimi
        if (self.cfg["guncelleme_otomatik"] and not self.guncelleme_suruyor
                and self.cfg["guncelleme_son_kontrol"] != bugun().isoformat()
                and time.monotonic() - self.acilis_zamani > 60):
            self.guncelleme_denetle()
        self.update_display()
        self.tick_count += 1
        if self.tick_count % 10 == 0:  # başka pencereler öne geçse de üstte kal (odak almadan)
            ustte_tut(self.root)
            if self.balon and self.balon.acik():
                ustte_tut(self.balon.win)
        self.root.after(1000 - simdi().microsecond // 1000 + 5, self.tick)

    def update_display(self):
        now = simdi()
        days = self.days()
        hedef = siradaki_vakit(days, now)

        if not self.cfg["district_url"]:
            view = ("msg", self.t("choose_loc"))
        elif not hedef:
            view = ("msg", self.t("loading_times"))
        else:
            ad, zaman = hedef
            kalan = (zaman - now).total_seconds()
            dakika = int(kalan // 60)  # tam dakika: 27 dk 12 sn kaldıysa 27 gösterilir
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
            view = ("vakit", ad, sure, yakin, ilerleme, saatler, gecmis, self.tarih_satirlari(now.date()))

        # Sadece görünen bir şey değiştiyse yeniden çiz (her saniye çizmemek için)
        expanded = self.cfg["expanded"] or self.peeking
        anahtar = (view, expanded, self.konum_adi())
        if anahtar != self.last_view:
            self.last_view = anahtar
            self.render(view, expanded)
            if not self.dragging:  # boyut değişince kenara yapışık kalsın
                self.place_window()

        if hedef:
            kalan = (hedef[1] - now).total_seconds()
            self.check_alarm(hedef[0], hedef[1], kalan, now)
            self.check_hadis(hedef[0], hedef[1], kalan, now)

    # -------------------------------------------------- saat dilimi

    def saat_dilimi_sorunlu(self):
        gunler = self.cache.get("days", {}) if self.cache.get("district_id") == self.cfg["district_id"] else {}
        return bool(self.cfg["district_url"]) and saat_dilimi_uyumsuz(self.cfg["country_id"], gunler)

    def saat_dilimi_degisti(self):
        """Windows'ta saat dilimi değişti: sayacı yeni saate göre çiz, uyarıyı yeniden değerlendir."""
        self.last_view = None
        self._hesaplanan = (None, {})
        self.saat_dilimi_uyarildi = False
        if self.saat_dilimi_sorunlu():
            self.saat_dilimi_uyar()
        elif self.balon and self.balon.acik() and self.balon.icerik == ("tz",):
            self.balon.kapat()  # artık uyuşuyor: açık uyarıyı kaldır
        if self.settings and self.settings.win.winfo_exists():
            self.settings.saat_dilimi_etiketi()
        self.update_display()

    def saat_dilimi_uyar(self):
        """Bilgisayarın saat dilimi şehirle uyuşmuyorsa oturum başına bir kez küçük bir uyarı göster."""
        if self.saat_dilimi_uyarildi or not self.saat_dilimi_sorunlu():
            return
        self.saat_dilimi_uyarildi = True
        self.balon_ac(("tz",))

    # -------------------------------------------------- güncelleme

    def guncelleme_denetle(self, manuel=False):
        """GitHub'da daha yeni sürüm var mı? Varsa tıklanınca güncelleyen bir balon gösterir."""
        if self.guncelleme_suruyor:
            return
        self.guncelleme_suruyor = True
        self.run_bg(son_surum_bilgisi, lambda b, h: self.guncelleme_geldi(b, h, manuel))

    def guncelleme_geldi(self, bilgi, hata, manuel):
        self.guncelleme_suruyor = False
        if hata:
            if manuel:
                self.balon_ac(("bilgi", "upd_title", "upd_check_failed"))
            else:  # internet yoksa bugün bir daha zorlamasın; sonraki açılış ya da yarın denenir
                self.cfg["guncelleme_son_kontrol"] = bugun().isoformat()
            return
        self.cfg["guncelleme_son_kontrol"] = bugun().isoformat()
        self.save_config()
        if surum_tuple(bilgi["surum"]) > surum_tuple(SURUM):
            self.balon_ac(("guncelleme", bilgi), sure_ms=30000)
        elif manuel:
            self.balon_ac(("bilgi", "upd_title", "upd_none"))

    def guncelle(self, bilgi):
        """Kullanıcı balona tıkladı: indir, doğrula, eskisinin yerine koy ve yeniden başlat."""
        if not getattr(sys, "frozen", False):  # .py olarak çalışıyorsa sadece sayfayı aç
            webbrowser.open(bilgi["sayfa"])
            return
        self.guncelleme_suruyor = True
        self.balon_ac(("bilgi", "upd_title", "upd_downloading"), sure_ms=120000)
        self.run_bg(guncellemeyi_indir, lambda yol, h: self.guncelleme_indi(bilgi, yol, h),
                    bilgi, sys.executable)

    def guncelleme_indi(self, bilgi, yeni, hata):
        self.guncelleme_suruyor = False
        try:
            if hata:
                raise hata
            guncellemeyi_kur(yeni, sys.executable)
            subprocess.Popen([sys.executable, "--guncellendi"], close_fds=True)
        except Exception:
            if yeni and os.path.exists(yeni):
                try:
                    os.remove(yeni)
                except OSError:
                    pass
            self.balon_ac(("bilgi", "upd_title", "upd_failed"))
            webbrowser.open(bilgi["sayfa"])
            return
        self.quit()  # yeni sürüm, bu kopya kapanınca açılacak (tek_kopya_mi bekler)

    # -------------------------------------------------- balon

    def balon_ac(self, icerik, sure_ms=HADIS_SURE_MS):
        """İçeriği o anki dil ve görünümle balonda gösterir (varsa eski balonu hemen kapatır)."""
        if self.balon:
            self.balon.kapat(aninda=True)
        en = self.cfg["language"] == "en"
        tikla = None
        if icerik[0] == "tz":
            baslik, metin, kaynak = self.t("tz_title"), self.t("tz_warn"), ""
        elif icerik[0] == "bekle":
            baslik, metin, kaynak = self.t("hadith_title"), self.t("hadith_wait"), ""
        elif icerik[0] == "bilgi":  # ("bilgi", başlık anahtarı, metin anahtarı)
            baslik, metin, kaynak = self.t(icerik[1]), self.t(icerik[2]).format(v=SURUM), ""
        elif icerik[0] == "guncelleme":
            bilgi = icerik[1]
            baslik, kaynak = self.t("upd_title"), f"{SURUM} → {bilgi['surum']}"
            metin = self.t("upd_available").format(v=bilgi["surum"])
            tikla = lambda: self.guncelle(bilgi)
        else:
            _, kitap, numara = icerik
            dil = "en" if en else "tr"
            baslik = self.t("hadith_title")
            metin = hadis_ozu(self.hadisler[f"{kitap}:{numara}"][dil], dil)
            kaynak = hadis_kaynagi(kitap, numara, en)
        self.balon = HadisBalonu(self, baslik, metin, kaynak, icerik, sure_ms, tikla)

    def balonu_yenile(self):
        """Dil ya da görünüm değişti: açık balonu aynı içerik ve kalan süreyle yeniden çiz."""
        if self.balon and self.balon.acik() and self.balon.icerik:
            self.balon_ac(self.balon.icerik, self.balon.kalan_ms())

    # -------------------------------------------------- hadisler

    def check_hadis(self, ad, zaman, kalan, now):
        """Vakte ayarlanan dakika kala (hadis_uyari) ve vakit girdiğinde (hadis_vakit) hadis gösterir."""
        onceki = self.hadis_hedef
        self.hadis_hedef = (ad, zaman)
        if onceki and onceki[1] != zaman and yeni_girdi(onceki[1], now) and onceki[0] != "Güneş":
            if self.cfg["hadis_vakit"]:
                self.hadis_goster()  # vakit girdi
            return
        if ad == "Güneş" or not self.cfg["hadis_uyari"]:  # güneşin doğuşu namaz vakti değil
            return
        esik = self.cfg["alarm_minutes"] * 60
        anahtar = zaman.isoformat()
        if esik - 30 < kalan <= esik and anahtar not in self.hadis_fired:
            self.hadis_fired.add(anahtar)
            hicri = self.cache.get("hijri", {}).get(now.date().isoformat(), "")
            if "Ramazan" in hicri and ad in ("İmsak", "Akşam"):
                self.hadis_goster(konular=("oruc",))  # sahur ve iftar öncesi
            else:
                self.hadis_goster(konular=("namaz", "abdest"))

    def hadis_indirmeyi_baslat(self):
        eksik = any(f"{k}:{n}" not in self.hadisler for k, n, _ in HADISLER)
        if not eksik or self.hadis_iniyor:
            return
        self.hadis_iniyor = True
        self.run_bg(eksik_hadisleri_indir, self.hadisler_indi, dict(self.hadisler))

    def hadisler_indi(self, yeni, error):
        self.hadis_iniyor = False
        if yeni:
            self.hadisler.update(yeni)
            save_json(HADIS_FILE, {"_surum": HADIS_SURUM, "hadis": self.hadisler})

    def hadis_sec(self, konular=None):
        dil = "en" if self.cfg["language"] == "en" else "tr"
        hazir = [h for h in HADISLER if self.hadisler.get(f"{h[0]}:{h[1]}", {}).get(dil)]
        if konular:
            hazir = [h for h in hazir if h[2] in konular] or hazir
        if not hazir:
            return None
        tazeler = [h for h in hazir if h not in self.son_hadisler] or hazir
        secilen = random.choice(tazeler)
        self.son_hadisler = (self.son_hadisler + [secilen])[-20:]
        return secilen

    def hadis_goster(self, konular=None, manuel=False):
        secilen = self.hadis_sec(konular)
        if not secilen:
            if manuel:  # henüz indirilmedi: indirmeyi başlat, kullanıcıya söyle
                self.hadis_indirmeyi_baslat()
                self.balon_ac(("bekle",))
            return
        self.balon_ac(("hadis", secilen[0], secilen[1]))

    def check_alarm(self, ad, zaman, kalan, now):
        cfg = self.cfg
        # Vakit girdi: hedef bir sonraki vakite geçti
        if self.last_target and self.last_target[1] != zaman and yeni_girdi(self.last_target[1], now):
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
        mci_durdur()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------- ayarlar

class HadisBalonu:
    """Sayacın yanında açılan, aynı temada küçük hadis balonu. Süresi dolunca ya da tıklayınca
    yavaşça solarak kapanır.

    icerik: balonda ne gösterildiği ("hadis", kitap, numara) / ("tz",) / ("bekle",); dil ya da
    görünüm değişince aynı içerik yeni haliyle yeniden açılabilsin diye saklanır.
    """

    SOLMA_MS, SOLMA_HIZLI_MS, SOLMA_ADIM = 500, 200, 12

    def __init__(self, app, baslik, metin, kaynak, icerik=None, sure_ms=HADIS_SURE_MS, tikla=None):
        renk, s = app.colors, app.cfg["size"]
        self.icerik, self.kapaniyor = icerik, False
        self.bitis = time.monotonic() + sure_ms / 1000
        onceki = on_pencere()
        w = self.win = tk.Toplevel(app.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=app.key)
        w.attributes("-transparentcolor", app.key)
        # sayaç "sadece yazı" modunda olsa bile hadis okunabilsin diye balonun hep zemini var
        self.alfa = max(SAYDAMLIK[app.cfg["opacity"]] or 1.0, 0.92)
        w.attributes("-alpha", self.alfa)
        c = tk.Canvas(w, bg=app.key, highlightthickness=0, bd=0)
        c.pack()

        genislik, pad = int(s * 21), int(s * 0.9)
        f_baslik, f_metin, f_kaynak = app.font(s * 0.7, True), app.font(s * 0.9), app.font(s * 0.7)
        y = pad
        c.create_text(pad, y, text=baslik, font=f_baslik, fill=renk["warn"], anchor="nw")
        y += f_baslik.metrics("linespace") + s * 0.3
        oge = c.create_text(pad, y, text=metin, font=f_metin, fill=renk["fg"], anchor="nw", width=genislik)
        y = c.bbox(oge)[3]
        if kaynak:
            y += s * 0.4
            c.create_text(pad + genislik, y, text=kaynak, font=f_kaynak, fill=renk["sub"], anchor="ne")
            y += f_kaynak.metrics("linespace")
        W, H = genislik + 2 * pad, math.ceil(y + pad)
        c.tag_lower(yuvarlak_kutu(c, 0, 0, W - 1, H - 1, s * 0.9, fill=renk["bg"], outline=renk["line"]))
        c.configure(width=W, height=H)

        # Sayaç ekranın sağ yarısındaysa sağ kenarları, değilse sol kenarları hizala. Bu seçim balon
        # açıkken sabit kalır; sürüklerken ekranın ortasından geçince balon yana sıçramasın.
        self.app, self.boyut = app, (W, H)
        mx, mw = app._pos[0], app.root.winfo_width()
        sol, _, sag, _ = calisma_alani(mx + mw // 2, app._pos[1])
        self.sag_hizali = mx + mw / 2 > (sol + sag) / 2
        self.konumla()
        w.update_idletasks()
        odak_almasin(w)
        odagi_geri_ver(onceki)  # balon oyun oynarken açılırsa odak oyunda kalsın

        # pencereye bağlı olay tuvalde de çalışır; tikla verildiyse (güncelleme) kapanırken o da yapılır
        w.bind("<Button-1>", lambda e: (self.kapat(hizli=True), tikla and tikla()))
        w.after(max(0, int(sure_ms)), self.kapat)

    def konumla(self):
        """Balonu sayacın üstüne (yer yoksa altına) koyar; sayaç sürüklendikçe tekrar çağrılır."""
        if not self.win.winfo_exists():
            return
        app, (W, H) = self.app, self.boyut
        mx, my = app._pos
        mw, mh = app.root.winfo_width(), app.root.winfo_height()
        sol, ust, sag, alt = calisma_alani(mx + mw // 2, my + mh // 2)
        x = mx + mw - W if self.sag_hizali else mx
        y = my - H - 8 if my - H - 8 >= ust else my + mh + 8
        x, y = max(sol, min(x, sag - W)), max(ust, min(y, alt - H))
        self.win.geometry(f"+{int(x)}+{int(y)}")

    def acik(self):
        return not self.kapaniyor and bool(self.win.winfo_exists())

    def kalan_ms(self):
        return max(0, int((self.bitis - time.monotonic()) * 1000))

    def kapat(self, hizli=False, aninda=False):
        """Balonu kapatır: normalde yarım saniyede solarak, tıklanınca daha hızlı.
        aninda: yerine hemen yenisi açılacaksa (dil değişimi, yeni hadis) solma beklenmez."""
        if not self.win.winfo_exists():
            return
        if aninda:
            self.win.destroy()
            return
        if self.kapaniyor:
            return
        self.kapaniyor = True
        sure = self.SOLMA_HIZLI_MS if hizli else self.SOLMA_MS
        self._sol(1, sure // self.SOLMA_ADIM)

    def _sol(self, adim, aralik):
        if not self.win.winfo_exists():
            return
        if adim >= self.SOLMA_ADIM:
            self.win.destroy()
            return
        self.win.attributes("-alpha", self.alfa * (1 - adim / self.SOLMA_ADIM))
        self.win.after(aralik, self._sol, adim + 1, aralik)


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


def arama_bicimi(metin):
    """Harf aramasında karşılaştırma için: Türkçe büyük harf, işaretsiz (ç→C, ı/i→I, ü→U ...)."""
    metin = metin.replace("i", "İ").replace("ı", "I").upper()
    return metin.translate(str.maketrans("ÇĞİÖŞÜÂÎÛ", "CGIOSUAIU"))


class HarfleAtla:
    """Salt okunur açılır listede bir harfe basınca o harfle başlayan öğeye gider. Hızlı yazılan
    harfler birleşir ("tu" → TUNUS), aynı harfe tekrar basınca o harfle başlayan sonrakine geçer.
    Liste açıkken de kapalıyken de çalışır."""

    def __init__(self, cb):
        self.cb, self.yazilan, self.son, self.bekleyen = cb, "", 0.0, None
        cb.bind("<KeyPress>", self.kapaliyken)
        self.liste = cb.tk.call("ttk::combobox::PopdownWindow", cb) + ".f.l"
        cb.tk.call("bind", self.liste, "<KeyPress>", "+" + cb.register(self.acikken) + " %A")

    def bul(self, harf, simdiki):
        if not harf or not harf.isprintable() or (harf == " " and not self.yazilan):
            return None
        an = time.monotonic()
        self.yazilan = (self.yazilan if an - self.son < 1.0 else "") + arama_bicimi(harf)
        self.son = an
        adlar = [arama_bicimi(a) for a in self.cb["values"]]
        if not adlar:
            return None
        tek = len(set(self.yazilan)) == 1  # "aaa": a ile başlayanlar arasında dolaş
        aranan = self.yazilan[0] if tek else self.yazilan
        basla = simdiki + 1 if tek else max(simdiki, 0)
        for k in range(len(adlar)):
            i = (basla + k) % len(adlar)
            if adlar[i].startswith(aranan):
                return i
        return None

    def kapaliyken(self, e):
        i = self.bul(e.char, self.cb.current())
        if i is None:
            return None
        self.cb.current(i)
        # ülke/il seçimi internetten liste çeker: hızlı yazarken her harfte değil, durunca seç
        if self.bekleyen:
            self.cb.after_cancel(self.bekleyen)
        self.bekleyen = self.cb.after(400, lambda: self.cb.event_generate("<<ComboboxSelected>>"))
        return "break"

    def acikken(self, harf):
        secili = self.cb.tk.call(self.liste, "curselection")
        i = self.bul(harf, int(secili[0]) if secili else -1)
        if i is not None:
            for komut in (("selection", "clear", 0, "end"), ("selection", "set", i), ("see", i), ("activate", i)):
                self.cb.tk.call(self.liste, *komut)


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

        # Başlık şeridi: logo, uygulama adı ve seçili konum
        tema = TEMALAR[VARSAYILAN_TEMA]
        ust = tk.Frame(w, bg=tema["bg"])
        ust.pack(fill="x")
        tk.Frame(ust, bg=tema["warn"], height=2).pack(side="bottom", fill="x")  # altın alt çizgi
        self._baslik_logo = hilal_resmi(15, tema["warn"], tema["bg"], logo_icinde)
        tk.Label(ust, image=self._baslik_logo, bg=tema["bg"]).pack(side="left", padx=(14, 8), pady=10)
        tk.Label(ust, text=t("app"), bg=tema["bg"], fg=tema["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        self.baslik_konum = tk.Label(ust, text=app.konum_adi(), bg=tema["bg"], fg=tema["sub"],
                                     font=("Segoe UI", 10))
        self.baslik_konum.pack(side="right", padx=16)

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
        ttk.Label(f, text=t("country")).grid(row=0, column=0, sticky="w", **pad)
        self.ulke_cb = ttk.Combobox(f, state="readonly", width=30, height=20)
        self.ulke_cb.grid(row=0, column=1, **pad)
        ttk.Label(f, text=t("province")).grid(row=1, column=0, sticky="w", **pad)
        self.il_cb = ttk.Combobox(f, state="readonly", width=30, height=20)
        self.il_cb.grid(row=1, column=1, **pad)
        ttk.Label(f, text=t("district")).grid(row=2, column=0, sticky="w", **pad)
        self.ilce_cb = ttk.Combobox(f, state="readonly", width=30, height=20)
        self.ilce_cb.grid(row=2, column=1, **pad)
        self._harf_arama = [HarfleAtla(cb) for cb in (self.ulke_cb, self.il_cb, self.ilce_cb)]
        self.tz_lbl = ttk.Label(f, foreground="#b3261e", wraplength=330, justify="left")
        self.tz_lbl.grid(row=3, column=0, columnspan=2, sticky="w", padx=8)
        self.saat_dilimi_etiketi()
        self.ulke_cb.set(c["country_name"])
        self.il_cb.set(t("loading"))
        self.ulke_cb.bind("<<ComboboxSelected>>", lambda e: self.ulke_secildi())
        self.il_cb.bind("<<ComboboxSelected>>", lambda e: self.il_secildi())
        self.ulkeler, self.iller, self.ilceler = [], [], []

        f = ttk.LabelFrame(genel, text=t("calc_frame"), padding=6)
        f.pack(fill="x", pady=(10, 0))
        ttk.Label(f, text=t("calc")).grid(row=0, column=0, sticky="w", **pad)
        self.hesap = Secim(f, HESAPLAR, c["calc"], en, width=30)
        self.hesap.cb.grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(f, text=t("calc_hint"), foreground="#666") \
            .grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))

        f = ttk.LabelFrame(genel, text=t("other"), padding=6)
        f.pack(fill="x", pady=(10, 0))
        ttk.Label(f, text=t("language")).grid(row=0, column=0, sticky="w", **pad)
        self.dil = Secim(f, DILLER, c["language"], en, width=14)
        self.dil.cb.grid(row=0, column=1, sticky="w", **pad)
        self.autostart = tk.BooleanVar(value=c["autostart"])
        ttk.Checkbutton(f, text=t("autostart"), variable=self.autostart) \
            .grid(row=1, column=0, columnspan=2, sticky="w", **pad)
        self.guncelleme_otomatik = tk.BooleanVar(value=c["guncelleme_otomatik"])
        ttk.Checkbutton(f, text=t("auto_update"), variable=self.guncelleme_otomatik) \
            .grid(row=2, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(f, text=f"{t('version')} {SURUM}", foreground="#666") \
            .grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))

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
        hf = ttk.LabelFrame(f, text=t("hadith_frame"), padding=6)
        hf.grid(row=7, column=0, columnspan=2, sticky="we", padx=8, pady=(10, 4))
        self.hadis_uyari = tk.BooleanVar(value=c["hadis_uyari"])
        self.hadis_vakit = tk.BooleanVar(value=c["hadis_vakit"])
        ttk.Checkbutton(hf, text=t("hadith_alert"), variable=self.hadis_uyari).pack(anchor="w", pady=2)
        ttk.Checkbutton(hf, text=t("hadith_time"), variable=self.hadis_vakit).pack(anchor="w", pady=2)
        ttk.Label(hf, text=t("hadith_hint"), foreground="#666", wraplength=340, justify="left") \
            .pack(anchor="w", pady=(2, 0))

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

        app.run_bg(get_ulkeler, self.ulkeler_geldi)
        ulke = c["country_id"]
        app.run_bg(get_iller, lambda r, e: self.iller_geldi(r, e, ulke, ilk=True), ulke)

    # -------------------------------------------------- konum

    def saat_dilimi_etiketi(self):
        """Kayıtlı şehir için saat dilimi uyarısını göster ya da gizle."""
        self.tz_lbl.configure(text=("⚠ " + self.app.t("tz_warn")) if self.app.saat_dilimi_sorunlu() else "")

    def ulke_id(self):
        i = self.ulke_cb.current()
        return self.ulkeler[i][1] if self.ulkeler and i >= 0 else self.app.cfg["country_id"]

    def ulkeler_geldi(self, ulkeler, error):
        if not self.win.winfo_exists():
            return
        if error:  # liste alınamazsa en azından kayıtlı ülke seçili kalsın
            ulkeler = [(self.app.cfg["country_name"], self.app.cfg["country_id"])]
        self.ulkeler = ulkeler
        self.ulke_cb.configure(values=[ad for ad, _ in ulkeler])
        secili = next((i for i, (_, uid) in enumerate(ulkeler) if uid == self.app.cfg["country_id"]), 0)
        self.ulke_cb.current(secili)

    def ulke_secildi(self):
        self.iller, self.ilceler = [], []
        self.il_cb.configure(values=[])
        self.ilce_cb.configure(values=[])
        self.il_cb.set(self.app.t("loading"))
        self.ilce_cb.set("")
        ulke = self.ulke_id()
        self.app.run_bg(get_iller, lambda r, e: self.iller_geldi(r, e, ulke), ulke)

    def iller_geldi(self, iller, error, ulke, ilk=False):
        if not self.win.winfo_exists() or ulke != self.ulke_id():
            return  # bu arada başka ülke seçildi
        t = self.app.t
        if error:
            self.il_cb.set(t("net_err"))
            messagebox.showerror(t("app"), f"{t('states_err')}\n{error}", parent=self.win)
            return
        self.iller = iller
        self.il_cb.configure(values=[ad for ad, _ in iller])
        secili = None
        if ilk:
            secili = next((i for i, (_, sid) in enumerate(iller) if sid == self.app.cfg["state_id"]), None)
        if secili is None and len(iller) == 1:
            secili = 0  # eyaleti/ili olmayan ülkeler: tek seçenek kendiliğinden seçilir
        if secili is None:
            self.il_cb.set("")
            self.ilce_cb.set(t("pick_state"))
        else:
            self.il_cb.current(secili)
            self.il_secildi(ilk=ilk)

    def il_secildi(self, ilk=False):
        i = self.il_cb.current()
        if i < 0:
            return
        self.ilceler = []
        self.ilce_cb.configure(values=[])
        self.ilce_cb.set(self.app.t("loading"))
        ulke, il = self.ulke_id(), self.iller[i][1]
        self.app.run_bg(get_ilceler, lambda r, e: self.ilceler_geldi(r, e, ilk, il), ulke, il)

    def ilceler_geldi(self, ilceler, error, ilk, il):
        i = self.il_cb.current() if self.win.winfo_exists() else -1
        if i < 0 or not self.iller or self.iller[i][1] != il:
            return  # pencere kapandı ya da bu arada başka il seçildi
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
                                             filetypes=[(t("wav_type"), SES_UZANTILARI)])
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
        self.baslik_konum.configure(text=self.app.konum_adi())
        self.saat_dilimi_etiketi()
        self.durum_lbl.configure(text=self.app.t("saved"))
        self.win.after(2000, lambda: self.win.winfo_exists() and self.durum_lbl.configure(text=""))

    def kaydet(self):
        """Ayarları kaydedip uygular; bir sorun varsa False döner."""
        app, c, t = self.app, self.app.cfg, self.app.t
        il_i, ilce_i = self.il_cb.current(), self.ilce_cb.current()
        if self.iller and il_i >= 0 and self.ilceler and ilce_i >= 0:
            il_adi, il_id = self.iller[il_i]
            ilce_adi, ilce_id, ilce_url = self.ilceler[ilce_i]
            ulke_i = self.ulke_cb.current()
            if self.ulkeler and ulke_i >= 0:
                c.update(country_name=self.ulkeler[ulke_i][0], country_id=self.ulkeler[ulke_i][1])
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
                 hadis_uyari=self.hadis_uyari.get(), hadis_vakit=self.hadis_vakit.get(),
                 language=self.dil.get(), autostart=self.autostart.get(),
                 guncelleme_otomatik=self.guncelleme_otomatik.get(),
                 calc=self.hesap.get(),
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
        if c["hadis_uyari"] or c["hadis_vakit"]:
            app.hadis_indirmeyi_baslat()
        return True


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # yazılar bulanık olmasın
    except (AttributeError, OSError):
        pass
    # Güncellemeden sonra açılıyorsa eski sürümün kapanmasını bekle
    if not tek_kopya_mi(bekle_sn=15 if "--guncellendi" in sys.argv else 0):
        return
    if getattr(sys, "frozen", False):  # önceki güncellemeden kalan eski .exe'yi temizle
        try:
            os.remove(sys.executable + ".old")
        except OSError:
            pass
    try:  # görev çubuğunda Python'un değil uygulamanın kendi ikonu görünsün
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EzanVakti.App")
    except (AttributeError, OSError):
        pass
    EzanVakti().run()


if __name__ == "__main__":
    main()
