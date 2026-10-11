import sys
import re
import os
import pysrt
import json
import time
import random
from datetime import datetime
from nFixer import nFixer

INDUSTRY_PROFILES = {
    "nCheck": {
        "cps": {"value": 19.5, "is_error": True},
        "cpl": {"value": 42, "is_error": True},
        "min_dur_ms": {"value": 833, "is_error": True},
        "min_gap_ms": {"value": 84, "is_error": True},
        "max_lines": {"value": 2, "is_error": True}
    },
    "Netflix TR": {
        "cps": {"value": 17.0, "is_error": True},
        "cpl": {"value": 42, "is_error": True},
        "min_dur_ms": {"value": 833, "is_error": True},
        "min_gap_ms": {"value": 83, "is_error": False},
        "max_lines": {"value": 2, "is_error": True}
    },
    "Amazon PV": {
        "cps": {"value": 17.0, "is_error": True},
        "cpl": {"value": 42, "is_error": False},
        "min_dur_ms": {"value": 1000, "is_error": True},
        "min_gap_ms": {"value": 83, "is_error": False},
        "max_lines": {"value": 2, "is_error": True}
    },
    "EBU / BBC": {
        "cps": {"value": 20.0, "is_error": False},
        "cpl": {"value": 40, "is_error": False},
        "min_dur_ms": {"value": 1000, "is_error": True},
        "min_gap_ms": {"value": 83, "is_error": False},
        "max_lines": {"value": 2, "is_error": True}
    },
    "OpenSubtitles": {
        "cps": {"value": 25.0, "is_error": True},
        "cpl": {"value": 45, "is_error": False},
        "min_dur_ms": {"value": 500, "is_error": False},
        "min_gap_ms": {"value": 24, "is_error": False},
        "max_lines": {"value": 2, "is_error": True}
    }
}


from PyQt5.QtWidgets import (QToolTip, QTextBrowser, QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QTextBrowser, QMessageBox, QTabWidget,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QGroupBox, QComboBox,
                             QFileDialog, QScrollArea, QLineEdit, QProgressBar, QRadioButton, QButtonGroup,
                             QListWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextDocument, QColor, QPalette
# removed QPrinter import

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

HISTORY_FILE = os.path.join(application_path, "nCheck_history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

def save_history(history_list):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, indent=4, ensure_ascii=False)
    except:
        pass

def get_rating_info(score, lang="TR"):
    if lang == "EN":
        if score < 60.0: return "⭐", "#FF3B30", "INADEQUATE"
        elif score < 65.0: return "⭐⭐", "#FFCC00", "MEDIOCRE"
        elif score < 70.0: return "⭐⭐½", "#FFCC00", "MEDIOCRE"
        elif score < 80.0: return "⭐⭐⭐", "#34C759", "ABOVE AVG"
        elif score < 85.0: return "⭐⭐⭐½", "#34C759", "WATCHABLE"
        elif score < 90.0: return "⭐⭐⭐⭐", "#34C759", "GOOD"
        elif score < 95.0: return "⭐⭐⭐⭐½", "#007AFF", "VERY GOOD"
        else: return "⭐⭐⭐⭐⭐", "#007AFF", "ARCHIVE"
    else:
        if score < 60.0: return "⭐", "#FF3B30", "YETERSİZ"
        elif score < 65.0: return "⭐⭐", "#FFCC00", "VASAT"
        elif score < 70.0: return "⭐⭐½", "#FFCC00", "VASAT"
        elif score < 80.0: return "⭐⭐⭐", "#34C759", "VASAT ÜSTÜ"
        elif score < 85.0: return "⭐⭐⭐½", "#34C759", "İZLENEBİLİR"
        elif score < 90.0: return "⭐⭐⭐⭐", "#34C759", "İYİ"
        elif score < 95.0: return "⭐⭐⭐⭐½", "#007AFF", "ÇOK İYİ"
        else: return "⭐⭐⭐⭐⭐", "#007AFF", "ARŞİVLİK"

def insan_gibi_bekle(sure_min=0.5, sure_max=2.0):
    time.sleep(random.uniform(sure_min, sure_max))

class DragDropLabel(QLabel):
    def __init__(self, title_key, main_window, is_optional=False, parent=None):
        super().__init__(parent)
        self.title_key = title_key
        self.main_window = main_window
        self.file_path = None
        self.is_optional = is_optional
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Segoe UI Variable", 12))
        self.setAcceptDrops(True)
        self.update_style(False)

    def update_style(self, is_hovered=False):
        if self.file_path is not None:
            self.setStyleSheet("""
                QLabel {
                    border: 2pt solid #30D158;
                    border-radius: 9pt;
                    background-color: rgba(48, 209, 88, 0.15);
                    color: #FFFFFF;
                    padding: 15pt;
                }
            """)
        else:
            if is_hovered:
                border_color = "#0A84FF"
                bg_color = "rgba(10, 132, 255, 0.1)"
            else:
                border_color = "#3A3A3C"
                bg_color = "#1C1C1E"
                
            self.setStyleSheet(f"""
                QLabel {{
                    border: 2px dashed {border_color};
                    border-radius: 12px;
                    background-color: {bg_color};
                    color: #AEAEB2;
                    padding: 10px;
                }}
            """)

    def refresh_text(self):
        if self.file_path is not None:
            import os
            file_name = os.path.basename(self.file_path)
            prefix_text = self.main_window.get_text("status_success")
            self.setText(prefix_text + chr(10) + file_name)
        else:
            title_text = self.main_window.get_text(self.title_key)
            drag_text = self.main_window.get_text("drag_hint")
            self.setText(title_text + chr(10) + drag_text)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.update_style(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.update_style(False)

    def dropEvent(self, event):
        self.update_style(False)
        urls = event.mimeData().urls()
        if len(urls) > 0:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.srt', '.ass')):

                        
                self.file_path = file_path
                self.refresh_text()
                self.update_style(False)
                self.main_window.update_ui_state()
            else:
                msg = self.main_window.get_text("err_srt_ass_only")
                QMessageBox.warning(self, "nAudit", msg)

class GemSubtitleProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.history = load_history()
        self.current_lang = "TR"
        
        self.current_tech_score = 0
        
        self.lang_dict = {
            "TR": {
                "window_title": "nCheck - Altyazı Teknik Kalite Kontrol Paneli v0.7",
                "panel_title": "🎬 nCheck - Altyazı Teknik Kalite Kontrol Paneli v0.7",
                "title_tr": "TÜRKÇE HEDEF (TR)",
                "opt_required": "Zorunlu",
                "drag_hint": "SRT veya ASS Dosyasını Buraya Sürükle",
                "status_success": "Başarılı!",
                "err_srt_ass_only": "Lütfen sadece .srt veya .ass uzantılı alt yazı dosyası yükleyin.",
                "tab_home": "Ana Sayfa",
                "tab_technical": "Teknik Rapor",
                "tab_settings": "Standartlar",
                "tab_history": "Geçmiş",
                "tab_about": "Hakkında",
                "btn_process_only_tech": "Teknik Analiz Yap",
                "btn_auto_fix": "🛠️ Otomatik Onar",
                "btn_load_tr_prompt": "Lütfen TR Dosyası Yükleyin...",
                "group_thresholds": "🚧 Teknik İhlal Eşikleri",
                "group_penalties": "⚖️ Teknik Ceza Çarpanları",
                "lbl_cpl": "Maksimum Karakter (CPL):",
                "lbl_flash": "Minimum Flaş (Sn):",
                "lbl_zombie": "Maksimum Zombi (Sn):",
                "lbl_gap": "Minimum Boşluk (ms):",
                "lbl_ell_tol": "Üç Nokta Toleransı (%):",
                "lbl_p_cps": "CPS İhlal Çarpanı:",
                "lbl_p_cpl": "CPL İhlal Çarpanı:",
                "lbl_p_dur": "Zamanlama Çarpanı:",
                "lbl_p_gap": "Boşluk Çarpanı:",
                "lbl_p_ell": "Üç Nokta Çarpanı:",
                "msg_success_body": "Alt yazılar analiz edildi. Sekmelerden sonuçları inceleyebilirsiniz.",
                "about_body": """<div style="font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif; line-height: 1.6; color: #E5E5E5; padding: 10px 15px;">
    <div align="center" style="margin-bottom: 25px;">
        <h1 style="color: #0A84FF; font-size: 20pt; margin-bottom: 6px;">🎬 nCheck v0.7 - Otonom Altyazı Teknik Kalite Kontrol Paneli</h1>
        <p style="font-size: 13pt; color: #FFFFFF; margin: 6px 0;"><b>Geliştirici:</b> nutuzar &nbsp;&nbsp;|&nbsp;&nbsp; <b>Sürüm:</b> v0.7 (Kararlı) &nbsp;&nbsp;|&nbsp;&nbsp; <b>Lisans:</b> GPL-3.0</p>
        <p style="color: #8E8E93; font-size: 11pt; font-style: italic; margin-top: 6px;">
            MQM (Multidimensional Quality Metrics) standartlarını baz alan SRT ve ASS altyazı dosyaları için teknik denetim motoru.
        </p>
    </div>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">
    
    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">📌 Genel Bakış</h2>
    <p style="font-size: 11pt; margin-bottom: 10px;">
        <b>Geliştirici:</b> nutuzar<br>
        <b>Sürüm:</b> v0.7 (Kararlı)<br>
        <b>Lisans:</b> GPL-3.0
    </p>
    <p style="font-size: 11pt; color: #CCC; margin-bottom: 10px;">
        nCheck, SRT ve ASS formatındaki altyazı dosyalarının teknik yeterliliğini, uluslararası yayıncılık standartlarına (MQM) göre denetleyen bir kalite kontrol (QC) aracıdır. Çevirinin anlamsal veya dilbilgisi kalitesine müdahale etmez; odağı tamamen <b>okunabilirlik, görsel ergonomi ve teknik yerleşimdir.</b>
    </p>
    <p style="font-size: 11pt; color: #CCC;">
        Devasa altyazı arşivleri oluşturanlar, çevirmenler ve kalite güvence (QA) süreçlerini otomatize etmek isteyen kullanıcılar için tasarlanmıştır. Yüklenen her dosyayı analiz ederek hataları tespit eder, objektif bir kalite skoru (0-100) hesaplar ve yazdırmaya hazır bir HTML raporu üretir.
    </p>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">

    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">🚀 Temel Özellikler</h2>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.7;">
        <li><b>Otonom Çok Katmanlı Analiz:</b> Dosya sürüklendiği an binlerce satırı milisaniyeler içinde tarar. nCheck Türkçe standartları (19.5 CPS, 42 CPL, 84ms boşluk, 833ms minimum süre) üzerinden 100 üzerinden sanatkârane bir kalite puanı hesaplarken, eşzamanlı olarak Netflix, Amazon, EBU ve OpenSubtitles gibi küresel platformların katı yayın standartlarına göre de sektörel uyumluluk (Geçti/Kaldı) denetimi yapar.</li>
        <li><b>Otonom Onarım Motoru:</b> Sadece hataları raporlamakla kalmaz, entegre "Otomatik Onar" butonu sayesinde tespit edilen yapısal sorunları tek tıkla çözer. Deterministik bir matematikle çalışan bu üç fazlı motor; tipografik çöpleri temizler, uzun veya dengesiz piramit satırlarını geometrik olarak yeniden merkezler ve senkronu bozmadan 84ms'lik güvenli boşluklar ile akıllı CPS esnemelerini (mümkün olduğu ölçüde) uygular. Metnin edebi anlamına veya kelimelerine asla dokunmaz; yalnızca mekanik düzenlemeyi yaparak dosyanızı MQM standartlarına göre yaklaştırır.</li>
        <li><b>Dil-Körü Mimari ve JSON Esnekliği:</b> Başka bir dildeki (örn: Almanca) kaynak dosyalarınız için farklı teknik limitler kullanmak isterseniz, bu değerleri doğrudan sistemin kalbindeki JSON sözlüğüne (INDUSTRY_PROFILES) saniyeler içinde yeni bir profil olarak zahmetsizce ekleyebilirsiniz.</li>
    </ul>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">

    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">📊 Derecelendirme Skalası</h2>
    <p style="font-size: 11pt; color: #CCC;">
        nCheck, dosyanın aldığı nihai puana göre (0-100) aşağıdaki sınıflandırmalardan birini atar:
    </p>
    <ul style="font-size: 11pt; list-style-type: none; line-height: 1.8;">
        <li><b>0 - 59</b> &nbsp;: 🔴 <b>REDDEDİLDİ / YETERSİZ</b></li>
        <li><b>60 - 64</b> : 🟡 <b>VASAT</b></li>
        <li><b>65 - 69</b> : 🟡 <b>VASAT ÜSTÜ</b></li>
        <li><b>70 - 79</b> : 🟢 <b>İZLENEBİLİR</b></li>
        <li><b>80 - 89</b> : 🟢 <b>İYİ</b></li>
        <li><b>90 - 94</b> : 🔵 <b>ÇOK İYİ</b></li>
        <li><b>95 - 100</b>: 🔵 <b>ARŞİVLİK</b></li>
    </ul>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">

    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">📜 nCheck Kalite Değerlendirme Manifestosu (MQM)</h2>
    <p style="font-size: 11pt; color: #CCC;">
        nCheck'in puanlama algoritması, küresel yayın endüstrisi standartlarına dayanır. Toplam 100 puan, üç farklı ağırlık merkezine (%50, %35, %15) bölünmüştür. Ayrıca skordan bağımsız çalışan bir "İnfaz Kurulu" (Kategori 0) mevcuttur.
    </p>
    <p style="font-size: 10pt; color: #8E8E93; font-style: italic;">
        *(Not: Dilbilgisi ve imla kontrolü nCheck'in değil, ekosistemin diğer parçası olan <b>nSpell</b> uygulamasının görevidir.)*
    </p>

    <h3 style="color: #FF3B30; font-size: 12pt; margin-top: 15px;">⛔ KATEGORİ 0: Kritik Hatalar (Puanlama Dışı / Doğrudan Ret)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        Bu kategorideki ihlaller altyazının temel yayın standartlarını bozar ve oynatıcıların çökmesine neden olabilir. Bir dosya 99 puan bile alsa, aşağıdaki hatalardan birini barındırıyorsa doğrudan <b>REDDEDİLDİ</b> durumuna düşer:
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li><b>Zaman Kodu Çakışması (Overlapping):</b> Bir altyazı bloğu bitmeden diğerinin başlaması.</li>
        <li><b>Çoklu Satır İhlali:</b> Ekranda tek bir blokta 3 veya daha fazla satırın yer alması.</li>
        <li><b>Negatif Süre (Zamansal Paradoks):</b> Bir bloğun bitiş zamanının, kendi başlangıç zamanından daha erken olması durumu.</li>
    </ul>

    <h3 style="color: #FF9500; font-size: 12pt; margin-top: 15px;">🔴 KATEGORİ 1: Okunabilirlik ve Akış (Maksimum 50 Puan)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        İzleyicinin metni filmin temposundan kopmadan okuyabilme kapasitesini ölçer.
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li><b>CPS İhlali:</b> Saniyede okunan karakter (Karakter/Saniye) limitinin aşılması.</li>
        <li><b>Flaş Altyazılar:</b> Ekranda insan gözünün algılayamayacağı kadar kısa (örn: 0.7sn altı) kalan metinler.</li>
        <li><b>Zombi Altyazılar:</b> Ekranda gereksiz yere uzun (örn: 7sn üstü) kalan metinler.</li>
    </ul>

    <h3 style="color: #FFCC00; font-size: 12pt; margin-top: 15px;">🟡 KATEGORİ 2: Görsel Konfor ve Yerleşim (Maksimum 35 Puan)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        Metnin ekranda kapladığı alan ve gözü yorma potansiyeli bu kategoride değerlendirilir.
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li><b>CPL İhlali:</b> Satır başına düşen karakter (Karakter/Satır) limitinin aşılması.</li>
        <li><b>Frame Gap (Boşluk) İhlali:</b> İki altyazı arasında yeterli boşluğun (örn: 24ms) bırakılmaması sonucu oluşan titreme (flicker) etkisi.</li>
        <li><b>Piramit (Satır Dengesi) İhlali:</b> İki satırlık bloklarda üst ve alt satırın karakter sayıları arasında uçurum olması (dikey dengesizlik).</li>
    </ul>

    <h3 style="color: #34C759; font-size: 12pt; margin-top: 15px;">🟢 KATEGORİ 3: Tipografik Hijyen (Maksimum 15 Puan)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        Dosyanın tipografik işçiliğini denetler. Oran hesabı yerine ihlal başına maktu ceza kesilir.
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li>Kelimeler arası gereksiz çift boşluklar.</li>
        <li>Noktalama işaretlerinden önce bırakılan kuraldışı boşluklar.</li>
        <li>Kapatılmamış veya hatalı yazılmış HTML biçimlendirme etiketleri (<code>&lt;i&gt;</code>, <code>&lt;b&gt;</code> vb.).</li>
        <li>Üç nokta (...) istismarı veya kuraldışı sembol kullanımları.</li>
    </ul>
</div>""",
                "rep_title": "⚙️ nCheck v0.7 Alt Yazı Teknik Analiz Raporu\n",
                "rep_file": "**Hedef Dosya (TR):** ",
                "rep_total_lines": "**Toplam Satır (Blok) Sayısı:** ",
                "rep_violations": "📊 İhlal Oranları ve Kesintiler\n",
                "rep_cps_err": "* **CPS (Okuma Hızı > {0}) İhlali:** %{1:.1f} oranında satırda bulundu. (Katsayı: x{2})\n",
                "rep_cpl_err": "* **CPL (Satır Genişliği > {0}) İhlali:** %{1:.1f} oranında satırda bulundu. (Katsayı: x{2})\n",
                "rep_flash_err": "* **Süre (Flaş < {0}s / Zombi > {1}s) İhlali:** %{2:.1f} oranında satırda bulundu. (Katsayı: x{3})\n",
                "rep_gap_err": "* **Boşluk (Frame Gap < {0}ms) İhlali:** %{1:.1f} oranında satırda bulundu. (Katsayı: x{2})\n",
                "rep_ell_err": "* **Üç Nokta/Tire İstismarı:** %{0:.1f} oranında bulundu. (%{1} tolerans aşıldı, %{2:.1f} ihlal var). (Katsayı: x{3})\n",
                "rep_minus": "  -> Düşülen Puan: -",
                "rep_score": "🏅 NİHAİ TEKNİK SKOR: ",
                "rep_status": "**Durum:** ",
                "st_perfect": "MÜKEMMEL (Kusursuz bir teknik işçilik.)",
                "st_good": "İZLENEBİLİR (Ufak tefek pürüzler var ancak seyirciyi yormaz.)",
                "st_fair": "VASAT (Göz yoran satırlar ve okuma zorlukları mevcut.)",
                "st_bad": "KÖTÜ (Zamanlama ve uzunluk kuralları tamamen ihlal edilmiş.)",
                "btn_clear": "Yeni / Temizle",
                "btn_open_folder": "Çıktı Klasörünü Aç",
                "btn_save_html": "Kaydet",
                "btn_delete_history": "Seçili Olanı Sil",
                "btn_clear_history": "Tümünü Sil",
                "lbl_analysis_results": "Analiz Sonuçları",
                "rep_cat0_title": "⛔ KATEGORİ 0 (Ölümcül Hata)\n",
                "rep_cat0_r1": "Blok {0}: 3 veya daha fazla satır içeriyor.",
                "rep_cat0_r2": "Blok {0}-{1}: Zaman kodu çakışması (Overlapping).",
                "rep_cat0_r3": "  - ... ve {0} benzer ihlal daha.\n",
                "rep_cat0_result": "  -> SONUÇ: <span style='color: #FF3B30; font-weight: bold;'>DOSYA DOĞRUDAN REDDEDİLDİ!</span>\n\n",
                "rep_rejected": "<span style='color: #FF3B30; font-weight: bold;'>🔴 REDDEDİLDİ</span>",
                "rep_disqualified": "(DİSKALİFİYE)",
                "rep_warn_utf8": "<span style='color: #FF3B30; font-weight: bold;'>⚠️ UYARI: Dosya modern UTF-8 standartlarında değil. Oynatıcılarda Türkçe karakter sorunu yaşanabilir.</span>\n",
                "rep_cat1_title": "🔴 KATEGORİ 1: OKUNABİLİRLİK VE AKIŞ (Maks 50 Puan)\n",
                "rep_cat1_cps": "  * CPS İhlali (&gt; {0}): %{1:.1f} (Çarpan: x2.0)\n",
                "rep_cat1_dur": "  * Süre İhlali (&lt; {0}s / &gt; {1}s): %{2:.1f} (Çarpan: x1.5)\n",
                "rep_cat1_score": "  -> Kategori 1 Skoru: {0:.1f} / 50\n\n",
                "rep_cat2_title": "🟡 KATEGORİ 2: GÖRSEL KONFOR VE YERLEŞİM (Maks 35 Puan)\n",
                "rep_cat2_cpl": "  * CPL İhlali (&gt; {0}): %{1:.1f} (Çarpan: x1.5)\n",
                "rep_cat2_gap": "  * Boşluk (Gap) İhlali (&lt; {0}ms): %{1:.1f} (Çarpan: x0.5)\n",
                "rep_cat2_pyr": "  * Piramit (Satır Dengesi) İhlali: {0} blok (Ceza: -{1:.1f})\n",
                "rep_cat2_score": "  -> Kategori 2 Skoru: {0:.1f} / 35\n\n",
                "rep_cat3_title": "🟢 KATEGORİ 3: TİPOGRAFİK HİJYEN (Maks 15 Puan)\n",
                "rep_cat3_typo": "  * Tipografik Hataya Sahip Blok: {0} adet (Ceza: -{1:.1f})\n",
                "rep_cat3_score": "  -> Kategori 3 Skoru: {0:.1f} / 15\n\n",
                "manifesto": ""
            },
            "EN": {
                "window_title": "nCheck - Subtitle Technical Quality Control Panel v0.7",
                "panel_title": "🎬 nCheck - Subtitle Technical Quality Control Panel v0.7",
                "title_tr": "TURKISH TARGET (TR)",
                "opt_required": "Required",
                "drag_hint": "Drag & Drop SRT or ASS File Here",
                "status_success": "Success!",
                "err_srt_ass_only": "Please load only .srt or .ass files.",
                "tab_home": "Home",
                "tab_technical": "Technical Report",
                "tab_settings": "Standards",
                "tab_history": "History",
                "tab_about": "About",
                "btn_process_only_tech": "Perform Only Technical Analysis",
                "btn_auto_fix": "🛠️ Auto Fix",
                "btn_load_tr_prompt": "Please Load TR File...",
                "group_thresholds": "🚧 Tech Violation Thresholds",
                "group_penalties": "⚖️ Tech Penalty Multipliers",
                "lbl_cpl": "Max Characters (CPL):",
                "lbl_flash": "Min Flash (Sec):",
                "lbl_zombie": "Max Zombie (Sec):",
                "lbl_gap": "Min Frame Gap (ms):",
                "lbl_ell_tol": "Ellipsis Tolerance (%):",
                "lbl_p_cps": "CPS Penalty:",
                "lbl_p_cpl": "CPL Penalty:",
                "lbl_p_dur": "Timing Penalty:",
                "lbl_p_gap": "Gap Penalty:",
                "lbl_p_ell": "Ellipsis Penalty:",
                "msg_success_body": "Subtitles analyzed successfully.",
                "about_body": """<div style="font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif; line-height: 1.6; color: #E5E5E5; padding: 10px 15px;">
    <div align="center" style="margin-bottom: 25px;">
        <h1 style="color: #0A84FF; font-size: 20pt; margin-bottom: 6px;">🎬 nCheck v0.7 - Autonomous Subtitle Technical Quality Control Panel</h1>
        <p style="font-size: 13pt; color: #FFFFFF; margin: 6px 0;"><b>Geliştirici:</b> nutuzar &nbsp;&nbsp;|&nbsp;&nbsp; <b>Version:</b> v0.7 (Stable) &nbsp;&nbsp;|&nbsp;&nbsp; <b>License:</b> GPL-3.0</p>
        <p style="color: #8E8E93; font-size: 11pt; font-style: italic; margin-top: 6px;">
            Technical inspection engine for SRT and ASS subtitle files based on MQM (Multidimensional Quality Metrics) standards.
        </p>
    </div>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">
    
    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">📌 Overview</h2>
    <p style="font-size: 11pt; margin-bottom: 10px;">
        <b>Geliştirici:</b> nutuzar<br>
        <b>Version:</b> v0.7 (Stable)<br>
        <b>License:</b> GPL-3.0
    </p>
    <p style="font-size: 11pt; color: #CCC; margin-bottom: 10px;">
        nCheck is a quality control (QC) tool that audits the technical compliance of subtitle files in SRT and ASS formats according to international broadcasting standards (MQM). It does not interfere with the semantic or grammatical quality of the translation; its focus is entirely on <b>readability, visual ergonomics, and spatial placement.</b>
    </p>
    <p style="font-size: 11pt; color: #CCC;">
        Designed for subtitle archivists, translators, and users seeking to automate quality assurance (QA) pipelines. It analyzes each uploaded file to detect errors, calculates an objective quality score (0-100), and generates a print-ready HTML report.
    </p>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">

    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">🚀 Key Features</h2>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.7;">
        <li><b>Autonomous Multi-Layered Analysis:</b> Scans thousands of lines within milliseconds upon drag & drop. While calculating an artisanal quality score out of 100 based on nCheck Turkish standards (19.5 CPS, 42 CPL, 84ms gap, 833ms minimum duration), it simultaneously performs industry compliance (Pass/Fail) audits against strict global broadcasting standards like Netflix, Amazon, EBU, and OpenSubtitles.</li>
        <li><b>Autonomous Repair Engine:</b> Not only reports errors, but also resolves structural issues with a single click thanks to the integrated "Auto Fix" button. Operating on deterministic mathematics, this three-phase engine cleans typographic debris, geometrically re-centers long or unbalanced pyramid lines, and applies safe 84ms gaps alongside intelligent CPS stretching (where possible) without disrupting sync. It never touches the literary meaning or wording of the text; it solely applies mechanical formatting to align your file with MQM standards.</li>
        <li><b>Language-Agnostic Architecture & JSON Flexibility:</b> If you wish to use different technical thresholds for source files in another language (e.g., German), you can effortlessly add these values as a new profile in seconds directly to the JSON dictionary (INDUSTRY_PROFILES) at the core of the system.</li>
    </ul>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">

    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">📊 Rating Scale</h2>
    <p style="font-size: 11pt; color: #CCC;">
        nCheck assigns one of the following tiers based on the file's final score (0-100):
    </p>
    <ul style="font-size: 11pt; list-style-type: none; line-height: 1.8;">
        <li><b>0 - 59</b> &nbsp;: 🔴 <b>REJECTED / INSUFFICIENT</b></li>
        <li><b>60 - 64</b> : 🟡 <b>MEDIOCRE</b></li>
        <li><b>65 - 69</b> : 🟡 <b>ABOVE MEDIOCRE</b></li>
        <li><b>70 - 79</b> : 🟢 <b>WATCHABLE</b></li>
        <li><b>80 - 89</b> : 🟢 <b>GOOD</b></li>
        <li><b>90 - 94</b> : 🔵 <b>VERY GOOD</b></li>
        <li><b>95 - 100</b>: 🔵 <b>ARCHIVAL</b></li>
    </ul>
    <hr style="border: none; border-top: 1px solid #333; margin: 20px 0;">

    <h2 style="color: #0A84FF; font-size: 14pt; margin-top: 20px;">📜 nCheck Quality Evaluation Manifesto (MQM)</h2>
    <p style="font-size: 11pt; color: #CCC;">
        nCheck's scoring algorithm is built on global broadcasting industry standards. The total 100 points are distributed across three distinct centers of gravity (50%, 35%, 15%). Additionally, an independent "Execution Board" (Category 0) enforces zero tolerance.
    </p>
    <p style="font-size: 10pt; color: #8E8E93; font-style: italic;">
        *(Note: Grammar and spelling checks are handled by <b>nSpell</b>, another component of the ecosystem, rather than nCheck.)*
    </p>

    <h3 style="color: #FF3B30; font-size: 12pt; margin-top: 15px;">⛔ CATEGORY 0: Critical Errors (Excluded from Scoring / Direct Rejection)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        Violations in this category break fundamental broadcasting standards and may cause media players to crash. Even if a file achieves a score of 99, containing any of the following errors triggers an immediate <b>REJECTED</b> status:
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li><b>Timecode Overlapping:</b> A subtitle block starting before the preceding one ends.</li>
        <li><b>Multi-Line Violation:</b> 3 or more lines appearing in a single block on screen.</li>
        <li><b>Negative Duration (Temporal Paradox):</b> A block's end time occurring earlier than its start time.</li>
    </ul>

    <h3 style="color: #FF9500; font-size: 12pt; margin-top: 15px;">🔴 CATEGORY 1: Readability and Flow (Maximum 50 Points)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        Measures the viewer's ability to comfortably read the text without breaking away from the film's tempo.
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li><b>CPS Violation:</b> Exceeding the reading speed limit (Characters Per Second).</li>
        <li><b>Flash Subtitles:</b> Lines remaining on screen too briefly for human cognitive absorption (e.g., &lt; 0.7s).</li>
        <li><b>Zombie Subtitles:</b> Lines lingering on screen unnecessarily long (e.g., &gt; 7s).</li>
    </ul>

    <h3 style="color: #FFCC00; font-size: 12pt; margin-top: 15px;">🟡 CATEGORY 2: Visual Comfort and Placement (Maximum 35 Points)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        Evaluates the screen real estate occupied by text and its propensity to cause visual fatigue.
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li><b>CPL Violation:</b> Exceeding the maximum characters per line limit (Characters Per Line).</li>
        <li><b>Frame Gap Violation:</b> Insufficient gap (e.g., &lt; 24ms) between consecutive subtitles causing visual flicker.</li>
        <li><b>Pyramid (Line Balance) Violation:</b> Excessive disparity in character length between top and bottom lines in two-line blocks (vertical imbalance).</li>
    </ul>

    <h3 style="color: #34C759; font-size: 12pt; margin-top: 15px;">🟢 CATEGORY 3: Typographic Hygiene (Maximum 15 Points)</h3>
    <p style="font-size: 11pt; color: #CCC;">
        Inspects the typographic craftsmanship of the file. Deductions are flat penalties per violation rather than ratio-based.
    </p>
    <ul style="font-size: 11pt; color: #CCC; line-height: 1.6;">
        <li>Unnecessary double spaces between words.</li>
        <li>Illegal whitespace preceding punctuation marks.</li>
        <li>Unclosed or malformed HTML formatting tags (<code>&lt;i&gt;</code>, <code>&lt;b&gt;</code>, etc.).</li>
        <li>Ellipsis (...) misuse or non-standard symbol exploitation.</li>
    </ul>
</div>""",
                "rep_title": "⚙️ nCheck v0.7 Subtitle Technical Analysis Report\n",
                "rep_file": "**Target File (TR):** ",
                "rep_total_lines": "**Total Lines:** ",
                "rep_violations": "📊 Violation Rates and Deductions\n",
                "rep_cps_err": "* **CPS (Speed > {0}) Violation:** Found in %{1:.1f} of lines. (Multiplier: x{2})\n",
                "rep_cpl_err": "* **CPL (Width > {0}) Violation:** Found in %{1:.1f} of lines. (Multiplier: x{2})\n",
                "rep_flash_err": "* **Duration (Flash < {0}s / Zombie > {1}s) Violation:** %{2:.1f} of lines. (Multiplier: x{3})\n",
                "rep_gap_err": "* **Gap (Frame Gap < {0}ms) Violation:** %{1:.1f} of lines. (Multiplier: x{2})\n",
                "rep_ell_err": "* **Ellipsis Exploitation:** %{0:.1f} found. (%{1} tol. exceeded, %{2:.1f} violation). (Multiplier: x{3})\n",
                "rep_minus": "  -> Deducted: -",
                "rep_score": "🏅 FINAL TECHNICAL SCORE: ",
                "rep_status": "**Status:** ",
                "st_perfect": "PERFECT",
                "st_good": "WATCHABLE",
                "st_fair": "FAIR",
                "st_bad": "BAD",
                "btn_clear": "New / Clear",
                "btn_open_folder": "Open Output Folder",
                "btn_save_html": "Save",
                "btn_delete_history": "Delete Selected",
                "btn_clear_history": "Clear All",
                "lbl_analysis_results": "Analysis Results",
                "rep_cat0_title": "⛔ CATEGORY 0 (Fatal Error)\n",
                "rep_cat0_r1": "Block {0}: Contains 3 or more lines.",
                "rep_cat0_r2": "Block {0}-{1}: Timecode Overlapping.",
                "rep_cat0_r3": "  - ... and {0} more similar violations.\n",
                "rep_cat0_result": "  -> RESULT: <span style='color: #FF3B30; font-weight: bold;'>FILE DIRECTLY REJECTED!</span>\n\n",
                "rep_rejected": "<span style='color: #FF3B30; font-weight: bold;'>🔴 REJECTED</span>",
                "rep_disqualified": "(DISQUALIFIED)",
                "rep_warn_utf8": "<span style='color: #FF3B30; font-weight: bold;'>⚠️ WARNING: File is not in modern UTF-8 format. Character encoding issues may occur.</span>\n",
                "rep_cat1_title": "🔴 CATEGORY 1: READABILITY AND FLOW (Max 50 Points)\n",
                "rep_cat1_cps": "  * CPS Violation (&gt; {0}): {1:.1f}% (Multiplier: x2.0)\n",
                "rep_cat1_dur": "  * Duration Violation (&lt; {0}s / &gt; {1}s): {2:.1f}% (Multiplier: x1.5)\n",
                "rep_cat1_score": "  -> Category 1 Score: {0:.1f} / 50\n\n",
                "rep_cat2_title": "🟡 CATEGORY 2: VISUAL COMFORT AND PLACEMENT (Max 35 Points)\n",
                "rep_cat2_cpl": "  * CPL Violation (&gt; {0}): {1:.1f}% (Multiplier: x1.5)\n",
                "rep_cat2_gap": "  * Frame Gap Violation (&lt; {0}ms): {1:.1f}% (Multiplier: x0.5)\n",
                "rep_cat2_pyr": "  * Pyramid (Line Balance) Violation: {0} blocks (Penalty: -{1:.1f})\n",
                "rep_cat2_score": "  -> Category 2 Score: {0:.1f} / 35\n\n",
                "rep_cat3_title": "🟢 CATEGORY 3: TYPOGRAPHIC HYGIENE (Max 15 Points)\n",
                "rep_cat3_typo": "  * Blocks with Typographic Errors: {0} (Penalty: -{1:.1f})\n",
                "rep_cat3_score": "  -> Category 3 Score: {0:.1f} / 15\n\n",
                "manifesto": ""
            }
        }

        self.setup_ui()
        self.populate_history()

    def setup_ui(self):
        # Ekran boyutuna göre dinamik ölçeklendirme ve ortalama
        screen = QApplication.desktop().availableGeometry()
        w = min(1200, int(screen.width() * 0.85))
        h = min(720, int(screen.height() * 0.85))
        self.setMinimumSize(600, 400)
        self.resize(w, h)
        self.move(int((screen.width() - w) / 2), int((screen.height() - h) / 2) - 20)
        self.setStyleSheet("""
            QMainWindow { background-color: #0E0E11; color: #F0F0F5; font-family: 'Segoe UI Variable', 'Segoe UI', system-ui; }
            QWidget { background-color: #0E0E11; color: #F0F0F5; font-family: 'Segoe UI Variable', 'Segoe UI', system-ui; }
            QTabWidget::pane { border: 1px solid #23232A; background: #16161A; border-radius: 12px; margin-top: -1px; }
            QTabBar::tab { background: #1C1C22; color: #7A7A8A;  min-width: 120px; padding: 12px 10px; border-top-left-radius: 10px; border-top-right-radius: 10px; margin-right: 6px; font-weight: 700; font-size: 11pt; }
            QTabBar::tab:selected { background: #16161A; color: #FFFFFF; border-bottom: 3px solid #007AFF; }
            QTabBar::tab:hover:!selected { background: #23232A; color: #FFFFFF; }
            QGroupBox { border: 1px solid #2A2A35; border-radius: 9pt; margin-top: 15pt; padding-top: 10pt; color: #FFFFFF; font-size: 11pt; background: #16161A; }
            QGroupBox::title { subcontrol-origin: margin; left: 12pt; padding: 0 7pt; color: #007AFF; font-weight: bold; font-size: 12pt; }
            QPushButton { background-color: #007AFF; border: none; border-radius: 10px; color: #FFFFFF; padding: 14px; font-weight: bold; font-size: 12pt; }
            QPushButton:hover { background-color: #0056B3; }
            QPushButton:disabled { background-color: #23232A; color: #555565; }
            QTextEdit, QTextBrowser { background-color: #111115; border: 1px solid #2A2A35; border-radius: 10px; padding: 12px; color: #E5E5E5; font-size: 11pt; line-height: 1.6; }
            QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background-color: #1C1C22; border: 1px solid #333340; border-radius: 6pt; color: #FFFFFF; padding: 4pt 9pt; min-width: 52pt; min-height: 28px; min-width: 80px; font-size: 11pt; }
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus { border: 1px solid #007AFF; background-color: #23232A; }
            QSpinBox:disabled, QDoubleSpinBox:disabled { background-color: #16161A; color: #666677; border: 1px solid #23232A; }
            QLabel { color: #E5E5E5; font-size: 11pt; }
            QScrollArea { border: none; background-color: transparent; }
            QListWidget { background-color: #111115; border: 1px solid #2A2A35; border-radius: 10px; font-size: 11pt; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #1C1C22; }
            QListWidget::item:selected { background-color: #1C1C22; color: #007AFF; font-weight: bold; border-left: 4px solid #007AFF; }
            QProgressBar { border: 1px solid #2A2A35; border-radius: 10px; background-color: #111115; color: #FFFFFF; font-weight: bold; text-align: center; height: 32px; }
            QProgressBar::chunk { background-color: #007AFF; border-radius: 10px; width: 20px; }
            QRadioButton { color: #FFFFFF; font-weight: bold; font-size: 11pt; padding: 5px; }
            QRadioButton::indicator { width: 18px; height: 18px; border-radius: 9px; border: 2px solid #555565; background: #1E1E24; }
            QRadioButton::indicator:checked { background: #007AFF; border: 2px solid #007AFF; }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # --- HEADER ---
        self.header_layout = QHBoxLayout()
        self.header_label = QLabel()
        self.header_label.setFont(QFont("Segoe UI Variable", 16, QFont.Bold))
        
        self.lang_group = QButtonGroup()
        self.radio_tr = QRadioButton("TR")
        self.radio_en = QRadioButton("EN")
        self.radio_tr.setChecked(True)
        self.lang_group.addButton(self.radio_tr)
        self.lang_group.addButton(self.radio_en)
        self.radio_en.toggled.connect(self.switch_language)
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(self.radio_tr)
        lang_layout.addWidget(self.radio_en)
        
        self.header_layout.addWidget(self.header_label)
        self.header_layout.addStretch()
        self.header_layout.addLayout(lang_layout)
        self.main_layout.addLayout(self.header_layout)

        # --- TABS ---
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Tab 1: Ana Sayfa
        self.home_tab = QWidget()
        self.home_layout = QVBoxLayout(self.home_tab)
        self.home_layout.setContentsMargins(20, 20, 20, 20)
        self.home_layout.setSpacing(15)

        # SCORE BOARD
        self.score_board_layout = QHBoxLayout()
        self.score_board_layout.setSpacing(20)
        
        self.tech_score_lbl = QLabel("TEKNİK YETERLİLİK\n--")
        self.tech_score_lbl.setAlignment(Qt.AlignCenter)
        self.tech_score_lbl.setFont(QFont("Segoe UI Variable", 14, QFont.Bold))
        self.tech_score_lbl.setStyleSheet("QLabel { background-color: #2D2D30; border-radius: 12px; padding: 10px; color: #FFFFFF; border: 2px solid #444444; }")
        

        
        self.home_layout.addLayout(self.score_board_layout)

        # DROP ZONES
        self.drop_layout = QHBoxLayout()
        self.drop_layout.setSpacing(25)
        self.tr_drop_box = DragDropLabel("title_tr", self, is_optional=False)
        self.drop_layout.addWidget(self.tr_drop_box)
        self.home_layout.addLayout(self.drop_layout, stretch=4)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("Değerlendiriliyor...")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.home_layout.addWidget(self.progress_bar)

        self.action_buttons_layout = QHBoxLayout()
        self.action_buttons_layout.setSpacing(15)
        
        self.process_button = QPushButton()
        self.process_button.setFont(QFont("Segoe UI Variable", 14, QFont.Bold))
        self.process_button.setMinimumHeight(45)
        self.process_button.setStyleSheet("QPushButton { background-color: #FF9500; } QPushButton:hover { background-color: #FFA522; }")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.start_technical_analysis)

        self.fix_button = QPushButton("🛠️ Otomatik Onar")
        self.fix_button.setFont(QFont("Segoe UI Variable", 14, QFont.Bold))
        self.fix_button.setMinimumHeight(45)
        self.fix_button.setStyleSheet("""
            QPushButton { background-color: #5856D6; color: #FFFFFF; }
            QPushButton:hover { background-color: #6C6AE4; }
            QPushButton:disabled { background-color: #2C2C35; color: #555565; }
        """)
        self.fix_button.setEnabled(False)
        self.fix_button.clicked.connect(self.start_auto_fix)
        
        self.clear_btn = QPushButton("Yeni / Temizle")
        self.clear_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.clear_btn.setMinimumHeight(45)
        self.clear_btn.setStyleSheet("QPushButton { background-color: #555565; color: #FFF; } QPushButton:hover { background-color: #444455; }")
        self.clear_btn.clicked.connect(self.clear_current_file)
        
        self.open_folder_btn = QPushButton("Çıktı Klasörünü Aç")
        self.open_folder_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.open_folder_btn.setMinimumHeight(45)
        self.open_folder_btn.setStyleSheet("QPushButton { background-color: #30D158; color: #FFF; } QPushButton:hover { background-color: #28C14E; }")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        
        self.action_buttons_layout.addWidget(self.process_button, stretch=2)
        self.action_buttons_layout.addWidget(self.fix_button, stretch=2)
        self.action_buttons_layout.addWidget(self.clear_btn, stretch=1)
        self.action_buttons_layout.addWidget(self.open_folder_btn, stretch=1)
        
        self.home_layout.addLayout(self.action_buttons_layout)
        self.tabs.addTab(self.home_tab, "")



        # Tab 3: Teknik Yeterlilik
        self.tech_tab = QWidget()
        self.tech_layout = QVBoxLayout(self.tech_tab)
        
        self.tech_header_layout = QHBoxLayout()
        self.tech_header_lbl = QLabel("Analiz Sonuçları")
        self.tech_header_lbl.setFont(QFont("Segoe UI Variable", 16, QFont.Bold))
        
        
        self.tech_header_layout.addWidget(self.tech_header_lbl)
        self.tech_header_layout.addStretch()
        
        self.save_html_btn = QPushButton("Kaydet")
        self.save_html_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.save_html_btn.setStyleSheet("QPushButton { background-color: #007AFF; color: #FFF; padding: 6px 15px; border-radius: 5px; } QPushButton:hover { background-color: #005BB5; }")
        self.save_html_btn.clicked.connect(lambda: self.save_html_report(is_history=False))
        self.save_html_btn.setEnabled(False)
        self.tech_header_layout.addWidget(self.save_html_btn)
        
        self.tech_text = QTextBrowser()
        self.tech_text.setReadOnly(True)
        self.tech_text.setOpenLinks(False)
        self.tech_text.anchorClicked.connect(self.handle_link_click)
        self.tech_text.setFont(QFont("Consolas", 12))
        self.tech_text.setStyleSheet("QTextEdit { background-color: #111115; color: #30D158; padding: 15px; border-radius: 10px; border: 1px solid #2A2A35;}")
        
        self.tech_layout.addLayout(self.tech_header_layout)
        self.tech_layout.addWidget(self.tech_text)
        self.tabs.addTab(self.tech_tab, "")

        # Tab 4: Ayarlar
        
        # Tab 5: Geçmiş
        self.history_tab = QWidget()
        self.history_layout = QHBoxLayout(self.history_tab)
        
        self.history_list = QListWidget()
        self.history_list.setFixedWidth(300)
        self.history_list.itemSelectionChanged.connect(self.on_history_selected)
        
        self.history_detail_layout = QVBoxLayout()
        self.history_detail_text = QTextBrowser()
        self.history_detail_text.setReadOnly(True)
        self.history_detail_text.setOpenLinks(False)
        self.history_detail_text.anchorClicked.connect(self.handle_link_click)
        self.history_detail_text.setFont(QFont("Consolas", 11))
        
        
        self.history_delete_btn = QPushButton("Seçili Olanı Sil")
        self.history_delete_btn.setFont(QFont("Segoe UI Variable", 11, QFont.Bold))
        self.history_delete_btn.setStyleSheet("QPushButton { background-color: #333333; color: #FFF; padding: 12px; } QPushButton:hover { background-color: #555555; }")
        self.history_delete_btn.clicked.connect(self.delete_history_entry)
        self.history_delete_btn.setEnabled(False)
        
        self.history_clear_all_btn = QPushButton("Tümünü Sil")
        self.history_clear_all_btn.setFont(QFont("Segoe UI Variable", 11, QFont.Bold))
        self.history_clear_all_btn.setStyleSheet("QPushButton { background-color: #FF3B30; color: #FFF; padding: 12px; } QPushButton:hover { background-color: #D70015; }")
        self.history_clear_all_btn.clicked.connect(self.clear_all_history)
        
        buttons_layout = QHBoxLayout()
        self.history_save_btn = QPushButton("Kaydet")
        self.history_save_btn.setFont(QFont("Segoe UI Variable", 11, QFont.Bold))
        self.history_save_btn.setStyleSheet("QPushButton { background-color: #007AFF; color: #FFF; padding: 12px; border-radius: 5px; } QPushButton:hover { background-color: #005BB5; }")
        self.history_save_btn.clicked.connect(lambda: self.save_html_report(is_history=True))
        self.history_save_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.history_save_btn)
        buttons_layout.addWidget(self.history_delete_btn)
        buttons_layout.addWidget(self.history_clear_all_btn)
        
        self.history_detail_layout.addWidget(self.history_detail_text)
        self.history_detail_layout.addLayout(buttons_layout)
        
        self.history_layout.addWidget(self.history_list)
        self.history_layout.addLayout(self.history_detail_layout)
        
        self.tabs.addTab(self.history_tab, "")

        # Tab 6: Hakkında
        self.about_tab = QWidget()
        self.about_layout = QVBoxLayout(self.about_tab)
        self.about_text = QTextEdit()
        self.about_text.setReadOnly(True)
        self.about_text.setStyleSheet("border: none; font-size: 11pt; line-height: 1.6; margin: 20px; background: transparent;")
        self.about_layout.addWidget(self.about_text)
        self.tabs.addTab(self.about_tab, "")

        self.switch_language()
        self.refresh_ui_texts()

    def clear_current_file(self):
        self.tr_drop_box.file_path = None
        self.tr_drop_box.refresh_text()
        self.tr_drop_box.update_style(False)
        self.tech_text.clear()
        self.set_score_labels(0)
        
        self.update_ui_state()

    def populate_history(self):
        self.history_list.clear()
        for idx, entry in enumerate(reversed(self.history)):
            title = f"{entry.get('date', 'Tarih Yok')} - {entry.get('filename', 'Dosya Yok')}"
            item = QListWidgetItem(title)
            # Store original index (since we are iterating reversed)
            item.setData(Qt.UserRole, len(self.history) - 1 - idx)
            self.history_list.addItem(item)

    def on_history_selected(self):
        selected = self.history_list.selectedItems()
        if not selected:
            
            self.history_delete_btn.setEnabled(False)
            if hasattr(self, 'history_save_btn'): self.history_save_btn.setEnabled(False)
            return
            
        idx = selected[0].data(Qt.UserRole)
        entry = self.history[idx]
        
        html_report = entry.get('html_report', '')
        if not html_report:
            # Fallback for older history
            t_s = entry.get('tech_score', 0)
            display_text = f"Tarih: {entry.get('date', '')}\nDosya: {entry.get('filename', '')}\nTeknik Skor: {t_s}\n"
            self.history_detail_text.setPlainText(display_text + entry.get('tech_report', ''))
        else:
            self.history_detail_text.setHtml(html_report)
            
        self.history_delete_btn.setEnabled(True)
        if hasattr(self, 'history_save_btn'): self.history_save_btn.setEnabled(True)


    def handle_link_click(self, url):
        url_str = url.toString()
        if "ncheck://sub/" in url_str:
            import urllib.parse
            from PyQt5.QtWidgets import QToolTip
            from PyQt5.QtGui import QCursor
            
            try:
                encoded_text = url_str.split("ncheck://sub/")[1]
                sub_text = urllib.parse.unquote(encoded_text)
                
                # HTML formatting for the tooltip
                formatted = f"<div style='padding: 5px; font-size: 11pt; color: #111111; font-weight: bold;'>{sub_text}</div>"
                QToolTip.showText(QCursor.pos(), formatted)
            except Exception as e:
                pass
        else:
            import webbrowser
            webbrowser.open(url_str)

    def save_html_report(self, is_history=False):
        import os
        try:
            reports_dir = os.path.join(application_path, "Raporlar")
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)
                
            if is_history:
                selected = self.history_list.selectedItems()
                if not selected: return
                idx = selected[0].data(Qt.UserRole)
                entry = self.history[idx]
                filename_base = entry.get('filename', 'Rapor')
                html_content = entry.get('html_report', '')
            else:
                if not hasattr(self, 'tr_drop_box') or not self.tr_drop_box.file_path: return
                filename_base = os.path.basename(self.tr_drop_box.file_path)
                html_content = getattr(self, 'current_html_report', '')
                
            if not html_content: return
                
            name_only = os.path.splitext(filename_base)[0]
            out_name = f"{name_only}_nCheck.html"
            out_path = os.path.join(reports_dir, out_name)
            
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            title = "Başarılı" if self.current_lang == "TR" else "Success"
            msg = f"Rapor kaydedildi:\n{out_path}" if self.current_lang == "TR" else f"Report saved:\n{out_path}"
            QMessageBox.information(self, title, msg)
        except Exception as e:
            title = "Hata" if self.current_lang == "TR" else "Error"
            QMessageBox.critical(self, title, f"{str(e)}")

    def clear_all_history(self):
        reply = QMessageBox.question(self, 'Tümünü Sil', 'Tüm geçmişi silmek istediğinize emin misiniz?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.history = []
            self.populate_history()
            self.history_detail_text.clear()
            self.history_delete_btn.setEnabled(False)
            save_history(self.history)

    def delete_history_entry(self):
        selected = self.history_list.selectedItems()
        if not selected: return
        
        reply = QMessageBox.question(self, 'Sil', 'Bu raporu geçmişten silmek istediğinize emin misiniz?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            idx = selected[0].data(Qt.UserRole)
            del self.history[idx]
            save_history(self.history)
            self.populate_history()
            self.history_detail_text.clear()
            
            self.history_delete_btn.setEnabled(False)

    def switch_language(self):
        if self.radio_en.isChecked():
            self.current_lang = "EN"
        else:
            self.current_lang = "TR" 
        self.refresh_ui_texts()
        self.update_ui_state()
        
        # Otomatik re-analyze if a report is currently displayed
        if hasattr(self, 'tech_text') and self.tech_text.toPlainText().strip() != "":
            if hasattr(self, 'tr_drop_box') and self.tr_drop_box.file_path:
                self.start_technical_analysis(show_msg=False)


    def refresh_ui_texts(self):
        self.setWindowTitle(self.get_text("window_title"))
        self.header_label.setText(self.get_text("panel_title"))
        self.tr_drop_box.refresh_text()
        
        self.tabs.setTabText(0, self.get_text("tab_home"))
        self.tabs.setTabText(1, self.get_text("tab_technical"))
        self.tabs.setTabText(2, self.get_text("tab_history"))
        self.tabs.setTabText(3, self.get_text("tab_about"))
        self.tech_header_lbl.setText(self.get_text("lbl_analysis_results"))
        self.clear_btn.setText(self.get_text("btn_clear"))
        self.open_folder_btn.setText(self.get_text("btn_open_folder"))
        if hasattr(self, 'fix_button'): self.fix_button.setText(self.get_text("btn_auto_fix"))
        self.history_delete_btn.setText(self.get_text("btn_delete_history"))
        if hasattr(self, 'save_html_btn'): self.save_html_btn.setText(self.get_text("btn_save_html"))
        if hasattr(self, 'history_save_btn'): self.history_save_btn.setText(self.get_text("btn_save_html"))
        self.history_clear_all_btn.setText(self.get_text("btn_clear_history"))
        self.about_text.setHtml(self.get_text('about_body'))

    def get_text(self, key):
        if key in self.lang_dict[self.current_lang]:
            return self.lang_dict[self.current_lang][key]
        return ""

    def update_ui_state(self):
        has_tr = self.tr_drop_box.file_path is not None
        if has_tr:
            self.process_button.setEnabled(True)
            self.process_button.setText(self.get_text("btn_process_only_tech"))
            self.process_button.setStyleSheet("QPushButton { background-color: #0A84FF; } QPushButton:hover { background-color: #007AFF; }")
            if hasattr(self, 'fix_button'):
                self.fix_button.setEnabled(False)
        else:
            self.process_button.setEnabled(False)
            self.process_button.setText(self.get_text("btn_load_tr_prompt"))
            self.process_button.setStyleSheet("QPushButton { background-color: #333333; color: #777777; }")
            if hasattr(self, 'fix_button'):
                self.fix_button.setEnabled(False)

    def _read_ass_as_srt(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            self.last_file_is_utf8 = True
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='windows-1254') as f:
                lines = f.readlines()
            self.last_file_is_utf8 = False

        events_started = False
        format_columns = []
        srt_blocks = []
        sub_index = 1

        for line in lines:
            line = line.strip()
            if line.startswith('[Events]'):
                events_started = True
                continue
            if events_started and line.startswith('Format:'):
                format_columns = [col.strip().lower() for col in line[7:].split(',')]
                continue
            if events_started and line.startswith('Dialogue:'):
                content = line[9:].strip()
                parts = content.split(',', len(format_columns) - 1)
                if len(parts) != len(format_columns):
                    continue
                
                row_data = dict(zip(format_columns, parts))
                
                start_ass = row_data.get('start', '0:00:00.00')
                end_ass = row_data.get('end', '0:00:00.00')
                text_ass = row_data.get('text', '')
                
                def convert_time(t):
                    t_parts = t.split('.')
                    hms = t_parts[0].split(':')
                    h = hms[0].zfill(2)
                    m = hms[1].zfill(2)
                    s = hms[2].zfill(2)
                    ms = t_parts[1].ljust(2, '0') + "0" if len(t_parts) > 1 else "000"
                    return f"{h}:{m}:{s},{ms}"
                    
                start_srt = convert_time(start_ass)
                end_srt = convert_time(end_ass)
                
                text_clean = re.sub(r'\{[^}]*\}', '', text_ass)
                text_clean = text_clean.replace(r'\N', '\n').replace(r'\n', '\n').strip()
                
                if not text_clean:
                    continue
                
                srt_blocks.append(f"{sub_index}\n{start_srt} --> {end_srt}\n{text_clean}\n")
                sub_index += 1

        srt_content = "\n".join(srt_blocks)
        return pysrt.from_string(srt_content)

    def load_subtitles(self, file_path):
        if file_path.lower().endswith('.ass'):
            return self._read_ass_as_srt(file_path)
        else:
            try:
                subs = pysrt.open(file_path, encoding='utf-8-sig')
                self.last_file_is_utf8 = True
                return subs
            except UnicodeDecodeError:
                try:
                    subs = pysrt.open(file_path, encoding='windows-1254')
                    self.last_file_is_utf8 = False
                    return subs
                except Exception as e:
                    raise Exception(f"Dosya okuma hatası: {str(e)}")

    def clean_srt_for_gemini(self, file_path):
        try:
            subs = self.load_subtitles(file_path)
        except Exception as e:
            return f"Okuma hatası: {str(e)}"
            
        blocks = []
        for sub in subs:
            text = sub.text_without_tags
            text = re.sub(r'\[.*?\]|\(.*?\)', '', text)
            
            lines = []
            for line in text.split('\n'):
                stripped_line = line.strip()
                if stripped_line != "":
                    lines.append(stripped_line)
                    
            if len(lines) > 0:
                blocks.append(" ".join(lines))
        
        clean_text = " | ".join(blocks)
        
        if len(clean_text) > 30000:
            return clean_text[:30000]
        else:
            return clean_text


    def render_html_report(self, stats):
        is_en = (self.current_lang == "EN")
        txt_unknown = "Unknown File" if is_en else "Bilinmeyen Dosya"
        
        filename = stats.get('filename', txt_unknown)
        total_lines = stats.get('total_lines', 0)
        final_score = stats.get('final_score', 0)
        t_star, tc, t_stat = get_rating_info(final_score, self.current_lang) if final_score > 0 else ("--", "#444444", "--")
        
        cat0_violations = stats.get('cat0_violations', 0)
        cat0_reasons = stats.get('cat0_reasons', [])
        cat0_indices = stats.get('cat0_indices', [])
        
        is_red_card = cat0_violations > 0
        txt_yap_hata = "STRUCTURAL ERROR" if is_en else "YAPISAL HATA"
        if is_red_card:
            main_status = f"<span style='color: #FF3B30; font-weight: bold;'>{final_score:.1f} / 100 🔴 {txt_yap_hata}</span>"
        else:
            main_status = f"<span style='color: {tc}; font-weight: bold;'>{final_score:.1f} / 100 {t_star} {t_stat}</span>"

        badges = []
        for profile, data in stats.get('industry_badges', {}).items():
            st = data['status']
            rs = ', '.join(data['reasons'])
            if st in ['GEÇERSİZ', 'INVALID']:
                badges.append(f"<div style='margin-bottom: 8px;'><span style='background-color: rgba(255,59,48,0.2); color: #FF3B30; padding: 6px 12px; border-radius: 6px; border: 1px solid #FF3B30; font-weight: bold; display: inline-block;'>{profile}: 🔴 {st} ({rs})</span></div>")
            elif st in ['UYUMLU', 'COMPLIANT']:
                badges.append(f"<div style='margin-bottom: 8px;'><span style='background-color: rgba(255,204,0,0.2); color: #FFCC00; padding: 6px 12px; border-radius: 6px; border: 1px solid #FFCC00; font-weight: bold; display: inline-block;'>{profile}: 🟡 {st} ({rs})</span></div>")
            else:
                badges.append(f"<div style='margin-bottom: 8px;'><span style='background-color: rgba(52,199,89,0.2); color: #34C759; padding: 6px 12px; border-radius: 6px; border: 1px solid #34C759; font-weight: bold; display: inline-block;'>{profile}: 🟢 {st}</span></div>")

        badges_html = "<div style='margin-top: 20px; margin-bottom: 25px; display: flex; flex-direction: column;'>" + "".join(badges) + "</div>"
        
        txt_blocks = "blocks" if is_en else "blok"
        txt_indices = "Indices:" if is_en else "İndeksler:"
        
        def make_accordion(title, indices):
            if not indices: return ""
            import urllib.parse
            
            idx_html_list = []
            for idx in indices:
                sub_text = stats.get('sub_texts', {}).get(str(idx), '')
                if sub_text:
                    url_encoded = urllib.parse.quote(sub_text)
                    link_html = f'<a href="ncheck://sub/{url_encoded}" onclick="showSubText(\'{idx}\'); return false;" title="Tıkla ve Görüntüle" class="clickable-idx" style="color: #64d2ff; font-weight: bold; text-decoration: none; border-bottom: 1px dotted #64d2ff; padding-bottom: 1px;">{idx}</a>'
                    idx_html_list.append(link_html)
                else:
                    idx_html_list.append(str(idx))
                    
            idx_str = ", ".join(idx_html_list)
            
            return f'''
            <div style='margin-top: 12px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 5px; display: block;'>
                <div style='font-weight: bold; color: #007AFF; margin-bottom: 5px;'>{title} ({len(indices)} {txt_blocks})</div>
                <div style='word-wrap: break-word; font-family: Consolas; font-size: 10pt; color: #AAA; padding-top: 5px; border-top: 1px solid #333; line-height: 1.5;'>
                    {txt_indices} {idx_str}
                </div>
            </div>
            '''

        txt_cps_viol = "CPS Violations" if is_en else "CPS İhlalleri"
        txt_dur_viol = "Duration Violations" if is_en else "Süre İhlalleri"
        txt_cpl_viol = "CPL Violations" if is_en else "CPL İhlalleri"
        txt_gap_viol = "Gap Violations" if is_en else "Gap İhlalleri"
        txt_pyr_viol = "Pyramid Violations" if is_en else "Piramit İhlalleri"
        txt_typ_viol = "Typographic Violations" if is_en else "Tipografi İhlalleri"

        cat1_accordions = make_accordion(txt_cps_viol, stats.get('cps_indices', [])) + make_accordion(txt_dur_viol, stats.get('dur_indices', []))
        cat2_accordions = make_accordion(txt_cpl_viol, stats.get('cpl_indices', [])) + make_accordion(txt_gap_viol, stats.get('gap_indices', [])) + make_accordion(txt_pyr_viol, stats.get('pyramid_indices', []))
        cat3_accordions = make_accordion(txt_typ_viol, stats.get('typo_indices', []))

        cat0_html = ""
        txt_cat0_viol = "Cat 0 Erroneous Block Indices" if is_en else "Kat 0 Hatalı Blok İndeksleri"
        txt_cat0_title = "CATEGORY 0: Structural Errors" if is_en else "KATEGORİ 0: Yapısal Hatalar"
        txt_cat0_desc = "This file has been directly rejected due to the following fatal errors:" if is_en else "Bu dosya, aşağıdaki ölümcül hatalar nedeniyle doğrudan reddedilmiştir:"
        
        if is_red_card:
            cat0_list = "<ul style='color: #FFF; padding-left: 20px;'>"
            for r in cat0_reasons:
                cat0_list += f"<li>{r}</li>"
            cat0_list += "</ul>"
            cat0_acc = make_accordion(txt_cat0_viol, cat0_indices)
            
            cat0_html = f'''
            <div style='margin-top: 25px; background: rgba(255, 59, 48, 0.1); border: 2px solid #FF3B30; border-radius: 8px; padding: 20px;'>
                <h2 style='color: #FF3B30; margin-top: 0;'>⛔ {txt_cat0_title}</h2>
                <p style='color: #FFF; font-size: 15px;'>{txt_cat0_desc}</p>
                {cat0_list}
                {cat0_acc}
            </div>
            '''
            
        txt_rep_title = "nCheck v0.7 Subtitle Technical Analysis Report" if is_en else "nCheck v0.7 Alt Yazı Teknik Analiz Raporu"
        txt_target_file = "Target File:" if is_en else "Hedef Dosya:"
        txt_total_lines = "Total Lines (Blocks):" if is_en else "Toplam Satır (Blok) Sayısı:"
        txt_final_score = "FINAL TECHNICAL SCORE (nCheck Standard):" if is_en else "NİHAİ TEKNİK SKOR (nCheck Standartı):"
        
        txt_cat1 = "CATEGORY 1: Readability" if is_en else "KATEGORİ 1: Okunabilirlik"
        txt_cat2 = "CATEGORY 2: Visual Comfort" if is_en else "KATEGORİ 2: Görsel Konfor"
        txt_cat3 = "CATEGORY 3: Hygiene" if is_en else "KATEGORİ 3: Hijyen"
        txt_pts = "Points" if is_en else "Puan"
        
        txt_cps = "CPS Violation" if is_en else "CPS İhlali"
        txt_dur = "Duration Violation" if is_en else "Süre İhlali"
        txt_cpl = "CPL Violation" if is_en else "CPL İhlali"
        txt_gap = "Gap Violation" if is_en else "Boşluk (Gap) İhlali"
        txt_pyr = "Pyramid Violation" if is_en else "Piramit İhlali"
        txt_typ = "Typographic Error" if is_en else "Tipografik Hata"

        dashboard_html = f'''<div style='font-family: "Segoe UI Variable", sans-serif;'>
    <h2 style='color: #E5E5E5; margin-bottom: 5px;'>⚙️ {txt_rep_title}</h2>
    <p style='color: #AAA; font-size: 14px;'>
        <b>{txt_target_file}</b> {filename}<br>
        <b>{txt_total_lines}</b> {total_lines}<br>
    </p>
    <div style='font-size: 18px; margin-top: 15px;'>
        <b>{txt_final_score}</b> {main_status}
    </div>
    
    {badges_html}
    
    {cat0_html}
    
    <div style='display: flex; gap: 15px; margin-top: 25px;'>
        <div style='flex: 1; background: #1C1C22; border: 1px solid #2A2A35; border-radius: 8px; padding: 15px;'>
            <h3 style='color: #FF9500; margin-top: 0;'>🔴 {txt_cat1}</h3>
            <p style='font-size: 24px; font-weight: bold; color: #FF9500; margin: 10px 0;'>{stats.get('cat1_score',0):.1f} <span style='font-size: 14px; color: #888;'>/ 50 {txt_pts}</span></p>
            <ul style='color: #DDD; padding-left: 20px; font-size: 13px;'>
                <li>{txt_cps}: {stats.get('R_cps',0):.1f}%</li>
                <li>{txt_dur}: {stats.get('R_dur',0):.1f}%</li>
            </ul>
            {cat1_accordions}
        </div>
        
        <div style='flex: 1; background: #1C1C22; border: 1px solid #2A2A35; border-radius: 8px; padding: 15px;'>
            <h3 style='color: #FFCC00; margin-top: 0;'>🟡 {txt_cat2}</h3>
            <p style='font-size: 24px; font-weight: bold; color: #FFCC00; margin: 10px 0;'>{stats.get('cat2_score',0):.1f} <span style='font-size: 14px; color: #888;'>/ 35 {txt_pts}</span></p>
            <ul style='color: #DDD; padding-left: 20px; font-size: 13px;'>
                <li>{txt_cpl}: {stats.get('R_cpl',0):.1f}%</li>
                <li>{txt_gap}: {stats.get('R_gap',0):.1f}%</li>
                <li>{txt_pyr}: {stats.get('pyramid',0)} {txt_blocks}</li>
            </ul>
            {cat2_accordions}
        </div>
        
        <div style='flex: 1; background: #1C1C22; border: 1px solid #2A2A35; border-radius: 8px; padding: 15px;'>
            <h3 style='color: #34C759; margin-top: 0;'>🟢 {txt_cat3}</h3>
            <p style='font-size: 24px; font-weight: bold; color: #34C759; margin: 10px 0;'>{stats.get('cat3_score',0):.1f} <span style='font-size: 14px; color: #888;'>/ 15 {txt_pts}</span></p>
            <ul style='color: #DDD; padding-left: 20px; font-size: 13px;'>
                <li>{txt_typ}: {stats.get('typo',0)} {txt_blocks}</li>
            </ul>
            {cat3_accordions}
        </div>
    </div>
</div>'''


        import json
        sub_data_json = json.dumps(stats.get('sub_texts', {}))

        interactive_script = f'''
        <style>
            .clickable-idx {{ cursor: pointer; transition: background 0.2s; }}
            .clickable-idx:hover {{ background: rgba(100, 210, 255, 0.2); color: #fff !important; }}
            #subModal {{
                display: none; position: fixed; z-index: 1000; left: 50%; top: 50%; transform: translate(-50%, -50%);
                background-color: #2c2c2e; border: 1px solid #3a3a3c; border-radius: 12px; padding: 25px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.8); color: #ebebf5; min-width: 320px; max-width: 80%; font-family: 'Segoe UI', sans-serif;
            }}
            #subModalOverlay {{
                display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; 
                background: rgba(0,0,0,0.7); backdrop-filter: blur(3px);
            }}
        </style>
        
        <div id="subModalOverlay" onclick="closeSubText()"></div>
        <div id="subModal">
            <h3 id="subModalTitle" style="color: #64d2ff; margin-top:0; border-bottom: 1px solid #3a3a3c; padding-bottom: 10px;">Satır Detayı</h3>
            <div id="subModalContent" style="font-size: 18px; margin: 20px 0; font-weight: bold; color: #ffffff;"></div>
            <button onclick="closeSubText()" style="background: #0a84ff; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; float: right; font-weight: bold;">Kapat</button>
            <div style="clear: both;"></div>
        </div>

        <script>
            const subData = {sub_data_json};
            function showSubText(idx) {{
                const text = subData[idx] || "Metin bulunamadı.";
                document.getElementById('subModalTitle').innerText = "Blok İndeksi: " + idx;
                document.getElementById('subModalContent').innerHTML = text;
                document.getElementById('subModalOverlay').style.display = 'block';
                document.getElementById('subModal').style.display = 'block';
            }}
            function closeSubText() {{
                document.getElementById('subModalOverlay').style.display = 'none';
                document.getElementById('subModal').style.display = 'none';
            }}
        </script>
        '''

        dashboard_html += interactive_script
        return dashboard_html

    def analyze_technical(self, file_path):
        try:
            subs = self.load_subtitles(file_path)
        except Exception as e:
            return {"error": f"Teknik analiz okuma hatası: {str(e)}"}, 0, False

        total_lines = len(subs)
        if total_lines == 0:
            return {"error": "Dosya boş, tamamen yoksayıldı veya geçersiz."}, 0, False

        # Profil bazlı nCheck kuralları (sabit referans)
        ncheck_rules = INDUSTRY_PROFILES["nCheck"]
        val_cps_limit = ncheck_rules["cps"]["value"]
        val_cpl_limit = ncheck_rules["cpl"]["value"]
        val_flash_min = ncheck_rules["min_dur_ms"]["value"] / 1000.0
        val_gap_ms = ncheck_rules["min_gap_ms"]["value"]
        val_max_lines = ncheck_rules["max_lines"]["value"]
        val_zombie_max = 7.0 # Zombi varsayılan configte kalabilir

        cat0_violations = 0
        cat0_reasons = []
        cat0_indices = []
        
        cps_violations = 0
        cps_indices = []
        
        duration_violations = 0
        dur_indices = []
        
        cpl_violations = 0
        cpl_indices = []
        
        gap_violations = 0
        gap_indices = []
        
        pyramid_violations = 0
        pyramid_indices = []
        
        typo_blocks = 0
        typo_indices = []

        # Badge checks veri toplayıcı
        badge_violations = {k: {"cps": 0, "cpl": 0, "min_dur_ms": 0, "min_gap_ms": 0, "max_lines": 0} for k in INDUSTRY_PROFILES.keys()}

        for i, sub in enumerate(subs):
            text = sub.text_without_tags.strip()
            raw_text = sub.text.strip()
            
            lines = text.split('\n')
            idx = i + 1
            
            duration_ms = sub.end.ordinal - sub.start.ordinal
            duration_sec = duration_ms / 1000.0
            
            # Kategori 0: İnfaz Kurulu
            is_cat0 = False
            
            # Negatif süre kontrolü
            if duration_ms < 0:
                is_cat0 = True
                cat0_reasons.append(f"Block {idx}: Negative Duration / Start > End." if self.current_lang == "EN" else f"Blok {idx}: Negatif Süre / Başlangıç bitişten büyük.")
                
            # Max lines kontrolü
            if len(lines) > val_max_lines:
                is_cat0 = True
                cat0_reasons.append(f"Block {idx}: Contains 3 or more lines." if self.current_lang == "EN" else f"Blok {idx}: 3 veya daha fazla satır içeriyor.")
            
            # Overlapping kontrolü
            if i < total_lines - 1:
                next_sub = subs[i+1]
                if sub.end.ordinal > next_sub.start.ordinal:
                    is_cat0 = True
                    cat0_reasons.append(f"Block {idx}-{idx+1}: Timecode overlapping." if self.current_lang == "EN" else f"Blok {idx}-{idx+1}: Zaman kodu çakışması (Overlapping).")
                    
            if is_cat0:
                cat0_violations += 1
                cat0_indices.append(idx)

            # Badge değerlendirmeleri
            cps = 0
            if duration_sec > 0:
                cps = len(text) / duration_sec
                
            has_gap = False
            gap_ms = 0
            if i < total_lines - 1:
                next_sub = subs[i+1]
                gap_ms = next_sub.start.ordinal - sub.end.ordinal
                has_gap = True

            max_line_len = max([len(l) for l in lines]) if lines else 0

            for profile, rules in INDUSTRY_PROFILES.items():
                if cps > rules["cps"]["value"]:
                    badge_violations[profile]["cps"] += 1
                if max_line_len > rules["cpl"]["value"]:
                    badge_violations[profile]["cpl"] += 1
                if duration_ms > 0 and duration_ms < rules["min_dur_ms"]["value"]:
                    badge_violations[profile]["min_dur_ms"] += 1
                if has_gap and gap_ms >= 0 and gap_ms < rules["min_gap_ms"]["value"]:
                    badge_violations[profile]["min_gap_ms"] += 1
                if len(lines) > rules["max_lines"]["value"]:
                    badge_violations[profile]["max_lines"] += 1

            # Kategori 1 & 2 (nCheck)
            if max_line_len > val_cpl_limit:
                cpl_violations += 1
                cpl_indices.append(idx)
                
            # Piramit Kuralı (Kat 2)
            if len(lines) == 2:
                if abs(len(lines[0]) - len(lines[1])) > 12:
                    pyramid_violations += 1
                    pyramid_indices.append(idx)

            if duration_sec > 0:
                if cps > val_cps_limit:
                    cps_violations += 1
                    cps_indices.append(idx)
                if duration_sec < val_flash_min or duration_sec > val_zombie_max:
                    duration_violations += 1
                    dur_indices.append(idx)
            else:
                duration_violations += 1
                dur_indices.append(idx)

            if has_gap and gap_ms >= 0 and gap_ms < val_gap_ms:
                gap_violations += 1
                gap_indices.append(idx)
                    
            # Kategori 3: Tipografik Hijyen
            has_typo = False
            
            # Çift boşluk
            if "  " in raw_text: has_typo = True
            
            # Yeni kural: Noktalama sonrası bitişiklik (boşluk bırakılmaması)
            # Örn: Nasıl?İyiyim. İstisnalar: sayılar arası (1.5), ardışık noktalar (...), veya HTML etiketleri öncesi (<)
            if re.search(r'[,.?!][A-Za-zÇÖŞĞÜİçöşğüı]', text): 
                has_typo = True
                
            # Yeni Kural: İkili diyalog senkronu
            if len(lines) == 2:
                h1 = lines[0].strip().startswith('-') or lines[0].strip().startswith('–')
                h2 = lines[1].strip().startswith('-') or lines[1].strip().startswith('–')
                if (h1 and not h2) or (h2 and not h1):
                    has_typo = True
            
            # Yeni Kural: Süslü Etiket Artıkları (Orphaned ASS tags in SRT)
            if re.search(r'\{\\a[n]?[1-9]\}', raw_text) or re.search(r'\{\\[a-zA-Z]+[^\}]+\}', raw_text):
                has_typo = True

            i_open = raw_text.count('<i>')
            i_close = raw_text.count('</i>')
            b_open = raw_text.count('<b>')
            b_close = raw_text.count('</b>')
            u_open = raw_text.count('<u>')
            u_close = raw_text.count('</u>')
            if i_open != i_close or b_open != b_close or u_open != u_close:
                has_typo = True
                
            if "---" in raw_text or re.search(r'\.\s\.\s\.', raw_text) or re.search(r'(?<!\.)\.\.(?!\.)', raw_text):
                has_typo = True
                
            if has_typo:
                typo_blocks += 1
                typo_indices.append(idx)

        R_cps = (cps_violations / total_lines) * 100
        R_dur = (duration_violations / total_lines) * 100
        R_cpl = (cpl_violations / total_lines) * 100
        R_gap = (gap_violations / total_lines) * 100
        
        # Kategori 1 (Maks 50 Puan)
        cat1_deduction = (R_cps * 2.0) + (R_dur * 1.5)
        cat1_score = 50.0 - cat1_deduction
        if cat1_score < 0: cat1_score = 0.0
        
        # Kategori 2 (Maks 35 Puan)
        cat2_deduction = (R_cpl * 1.5) + (R_gap * 0.5) + (pyramid_violations * 0.5)
        cat2_score = 35.0 - cat2_deduction
        if cat2_score < 0: cat2_score = 0.0
        
        # Kategori 3 (Maks 15 Puan)
        cat3_deduction = typo_blocks * 1.0
        cat3_score = 15.0 - cat3_deduction
        if cat3_score < 0: cat3_score = 0.0
        
        final_score = cat1_score + cat2_score + cat3_score
        
        industry_badges = {}
        for profile, rules in INDUSTRY_PROFILES.items():
            if profile == "nCheck": continue
            
            reasons = []
            has_error = False
            has_warning = False
            
            prof_viol = badge_violations[profile]
            is_en = (self.current_lang == "EN")
            if prof_viol["cps"] > 0:
                if rules["cps"]["is_error"]: has_error = True; reasons.append(f"CPS Exceeded ({prof_viol['cps']})" if is_en else f"CPS Aşımı ({prof_viol['cps']})")
                else: has_warning = True; reasons.append(f"CPS Warning ({prof_viol['cps']})" if is_en else f"CPS Uyarısı ({prof_viol['cps']})")
            
            if prof_viol["cpl"] > 0:
                if rules["cpl"]["is_error"]: has_error = True; reasons.append(f"CPL Exceeded ({prof_viol['cpl']})" if is_en else f"CPL Aşımı ({prof_viol['cpl']})")
                else: has_warning = True; reasons.append(f"CPL Warning ({prof_viol['cpl']})" if is_en else f"CPL Uyarısı ({prof_viol['cpl']})")
                
            if prof_viol["min_dur_ms"] > 0:
                if rules["min_dur_ms"]["is_error"]: has_error = True; reasons.append(f"Short Duration ({prof_viol['min_dur_ms']})" if is_en else f"Kısa Süre ({prof_viol['min_dur_ms']})")
                else: has_warning = True; reasons.append(f"Short Dur Warning ({prof_viol['min_dur_ms']})" if is_en else f"Kısa Süre Uyarısı ({prof_viol['min_dur_ms']})")
                
            if prof_viol["min_gap_ms"] > 0:
                if rules["min_gap_ms"]["is_error"]: has_error = True; reasons.append(f"Gap Violation ({prof_viol['min_gap_ms']})" if is_en else f"Boşluk İhlali ({prof_viol['min_gap_ms']})")
                else: has_warning = True; reasons.append(f"Gap Warning ({prof_viol['min_gap_ms']})" if is_en else f"Boşluk Uyarısı ({prof_viol['min_gap_ms']})")
                
            if prof_viol["max_lines"] > 0:
                if rules["max_lines"]["is_error"]: has_error = True; reasons.append(f"Line Violation ({prof_viol['max_lines']})" if is_en else f"Satır İhlali ({prof_viol['max_lines']})")
                else: has_warning = True; reasons.append(f"Line Warning ({prof_viol['max_lines']})" if is_en else f"Satır Uyarısı ({prof_viol['max_lines']})")
                
            if has_error:
                status = "INVALID" if is_en else "GEÇERSİZ"
            elif has_warning:
                status = "COMPLIANT" if is_en else "UYUMLU"
            else:
                status = "PASSED" if is_en else "GEÇERLİ"
                
            industry_badges[profile] = {
                "status": status,
                "reasons": reasons
            }

        stats = {
            'filename': os.path.basename(file_path),
            'cat1_score': cat1_score,
            'cat2_score': cat2_score,
            'cat3_score': cat3_score,
            'final_score': round(final_score, 1),
            'R_cps': R_cps,
            'R_dur': R_dur,
            'R_cpl': R_cpl,
            'R_gap': R_gap,
            'pyramid': pyramid_violations,
            'typo': typo_blocks,
            'cat0_violations': cat0_violations,
            'cat0_reasons': cat0_reasons,
            'cat0_indices': cat0_indices,
            'cps_indices': cps_indices,
            'dur_indices': dur_indices,
            'cpl_indices': cpl_indices,
            'gap_indices': gap_indices,
            'pyramid_indices': pyramid_indices,
            'typo_indices': typo_indices,
            'total_lines': total_lines,
            'industry_badges': industry_badges,
            'sub_texts': {str(i+1): sub.text.replace(chr(10), '<br>').replace('"', '&quot;').replace("'", "&#39;") for i, sub in enumerate(subs)}
        }
        
        return stats, round(final_score, 1), cat0_violations > 0

    def set_score_labels(self, tech_score, is_red_card=False):
        if is_red_card:
            self.tech_score_lbl.setText(f"TEKNİK YETERLİLİK\n{tech_score} / 100\n🔴 REDDEDİLDİ")
            self.tech_score_lbl.setStyleSheet(f"QLabel {{ background-color: #2D2D30; border-radius: 12px; padding: 10px; color: #FF3B30; border: 2px solid #FF3B30; font-size: 13pt; font-weight: bold; }}")
            return
            
        t_star, tc, t_stat = get_rating_info(tech_score) if tech_score > 0 else ("--", "#444444", "--")
        tech_text = f"{tech_score} {t_star}" if tech_score > 0 else "--"
        
        self.tech_score_lbl.setText(f"TEKNİK YETERLİLİK\n{tech_text}")
        self.tech_score_lbl.setStyleSheet(f"QLabel {{ background-color: #2D2D30; border-radius: 12px; padding: 10px; color: {tc}; border: 2px solid {tc}; font-size: 13pt; }}")

    def start_technical_analysis(self, show_msg=True):
        self.current_tech_score = 0
        self.set_score_labels(0)
        self.tech_text.clear()
        
        stats, tech_score, is_red_card = self.analyze_technical(self.tr_drop_box.file_path)
        if "error" in stats:
            QMessageBox.warning(self, "Hata", stats["error"])
            return
            
        self.current_tech_score = tech_score
        self.current_tech_stats = stats
        self.current_is_red_card = is_red_card
        
        html_report = self.render_html_report(stats)
        self.current_html_report = html_report
        self.tech_text.setHtml(html_report)
        if hasattr(self, 'save_html_btn'):
            self.save_html_btn.setEnabled(True)
        
        self.set_score_labels(tech_score, is_red_card)
        
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": os.path.basename(self.tr_drop_box.file_path),
            "tech_score": tech_score,
            "is_red_card": is_red_card,
            "stats": stats,
            "html_report": html_report
        }
        self.history.append(entry)
        save_history(self.history)
        self.populate_history()
        
        self.tabs.setCurrentIndex(1)
        if show_msg:
            QMessageBox.information(self, "nCheck", self.get_text("msg_success_body"))

        # Analiz bittiğinde Öncesi/Sonrası etkisi için Otomatik Onar butonunu aktif et
        if hasattr(self, 'fix_button'):
            self.fix_button.setEnabled(True)

    def start_auto_fix(self):
        if not hasattr(self, 'tr_drop_box') or not self.tr_drop_box.file_path:
            QMessageBox.warning(self, "Uyarı", "Onarılacak altyazı dosyası bulunamadı.")
            return

        current_file = self.tr_drop_box.file_path
        if not os.path.isfile(current_file):
            QMessageBox.warning(self, "Hata", f"Dosya bulunamadı:\n{current_file}")
            return

        try:
            # 1. nFixer çağır ve çalıştır
            fixer = nFixer(file_path=current_file)
            clean_subs = fixer.run_all()

            # 2. [OrijinalDosyaAdi]_Fixed.srt formatında kaydet
            base_name, _ = os.path.splitext(current_file)
            if base_name.endswith("_Fixed"):
                fixed_file_path = f"{base_name}.srt"
            else:
                fixed_file_path = f"{base_name}_Fixed.srt"

            clean_subs.save(fixed_file_path, encoding='utf-8')

            # 3. Drop box dosya yolunu ve arayüz metnini güncelle
            self.tr_drop_box.file_path = fixed_file_path
            self.tr_drop_box.refresh_text()
            self.tr_drop_box.update_style(False)

            # 4. Otomatik olarak teknik analizi çağır (Öncesi/Sonrası şoku)
            self.start_technical_analysis(show_msg=True)

        except Exception as e:
            QMessageBox.critical(self, "Onarım Hatası", f"Otomatik onarım sırasında bir hata oluştu:\n{str(e)}")


    def open_output_folder(self):
        try:
            folder_to_open = ""
            if self.tr_drop_box.file_path:
                folder_to_open = os.path.dirname(self.tr_drop_box.file_path)
            else:
                folder_to_open = os.path.expanduser("~")
                
            if sys.platform == 'win32':
                os.startfile(folder_to_open)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.call(['open', folder_to_open])
            else:
                import subprocess
                subprocess.call(['xdg-open', folder_to_open])
        except Exception as e:
            QMessageBox.warning(self, "nAudit", f"Klasör açılamadı: {str(e)}")

if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    default_font = QFont("Segoe UI Variable", 10)
    default_font.setStyleHint(QFont.SansSerif)
    app.setFont(default_font)
    
    window = GemSubtitleProcessor()
    window.show()
    sys.exit(app.exec_())
