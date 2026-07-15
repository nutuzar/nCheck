import sys
import re
import os
import pysrt
import json
import time
import random
from datetime import datetime



from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QTextBrowser, QMessageBox, QTabWidget,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QGroupBox, QComboBox,
                             QFileDialog, QScrollArea, QLineEdit, QProgressBar, QRadioButton, QButtonGroup,
                             QListWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextDocument, QColor, QPalette
from PyQt5.QtPrintSupport import QPrinter

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(application_path, "nCheck_config.json")
HISTORY_FILE = os.path.join(application_path, "nCheck_history.json")

def load_config():
    default_config = {
        "gemini_url": "https://gemini.google.com/app",
        "cps": 21.0,
        "cpl": 38,
        "flash": 0.7,
        "zombie": 7.0,
        "gap": 24,
        "ell_tol": 5.0,
        "pen_cps": 1.0,
        "pen_cpl": 0.5,
        "pen_dur": 1.0,
        "pen_gap": 0.2,
        "pen_ell": 1.0
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except:
            pass
    return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except:
        pass

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
                    border: 2px solid #30D158;
                    border-radius: 12px;
                    background-color: rgba(48, 209, 88, 0.15);
                    color: #FFFFFF;
                    padding: 20px;
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
                    padding: 20px;
                }}
            """)

    def refresh_text(self):
        if self.file_path is not None:
            file_name = os.path.basename(self.file_path)
            prefix_text = self.main_window.get_text("status_success")
            self.setText(f"✅ {prefix_text}\n{file_name}")
        else:
            title_text = self.main_window.get_text(self.title_key)
            if self.is_optional:
                opt_text = f"({self.main_window.get_text('opt_optional')})"
            else:
                opt_text = f"({self.main_window.get_text('opt_required')})"
            drag_text = self.main_window.get_text("drag_hint")
            self.setText(f"📁\n{title_text}\n{opt_text}\n{drag_text}")

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
                if hasattr(self.main_window, 'validate_subtitle_language'):
                    if not self.main_window.validate_subtitle_language(file_path):
                        return
                        
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
        self.config = load_config()
        self.history = load_history()
        self.current_lang = "TR"
        
        self.current_tech_score = 0
        
        self.lang_dict = {
            "TR": {
                "window_title": "nCheck - Altyazı Teknik Kalite Kontrol Paneli v0.5",
                "panel_title": "🎬 nCheck - Altyazı Teknik Kalite Kontrol Paneli v0.5",
                "title_tr": "TÜRKÇE HEDEF (TR)",
                "opt_optional": "Opsiyonel",
                "opt_required": "Zorunlu",
                "drag_hint": "SRT veya ASS Dosyasını Buraya Sürükle",
                "status_success": "Başarılı!",
                "err_srt_ass_only": "Lütfen sadece .srt veya .ass uzantılı alt yazı dosyası yükleyin.",
                "tab_home": "Ana Sayfa",
                "tab_technical": "Teknik Yeterlilik",
                "tab_settings": "Standartlar",
                "tab_history": "Geçmiş",
                "tab_about": "Hakkında",
                "btn_process_only_tech": "Teknik Analiz Yap",
                "btn_load_tr_prompt": "Lütfen TR Dosyası Yükleyin...",
                "group_thresholds": "🚧 Teknik İhlal Eşikleri",
                "group_penalties": "⚖️ Teknik Ceza Çarpanları",
                "lbl_cps": "Maksimum Okuma (CPS):",
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
                "about_body": "<b>nCheck - Altyazı Teknik Kalite Kontrol Paneli</b><br><br><b>Geliştirici:</b> nutuzar<br><b>Versiyon:</b> 0.5",
                "rep_title": "⚙️ nCheck v0.5 Alt Yazı Teknik Analiz Raporu\n",
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
                "btn_save_pdf": "Bu Raporu PDF Olarak Kaydet",
                "btn_delete_history": "Geçmişten Sil",
                "lbl_vault": "Kilit",
                "pl_vault_pwd": "Şifre Girin...",
                "btn_unlock": "Kilidi Aç",
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
                "manifesto": """
<h2 style='color: #007AFF;'>nCheck Kalite Değerlendirme Manifestosu (MQM Tabanlı)</h2>
<p>nCheck, altyazı dosyalarını (SRT/ASS) değerlendirirken rastgele puan kırma veya "keyfi katsayılar" kullanma mantığını tamamen reddeder. Puanlama algoritmasının temeli, küresel yayıncılık endüstrisinin (Netflix, Disney, EBU) kullandığı MQM (Multidimensional Quality Metrics) standartlarına dayanır.</p>
<p>Bir dosyanın alacağı 100 üzerinden nihai skor, izleyicinin bilişsel kapasitesi, ekranın görsel ergonomisi ve metnin tipografik işçiliği baz alınarak üç ana ağırlık merkezine (%50, %35, %15) bölünmüştür. Ayrıca skordan bağımsız işleyen bir "Sıfır Tolerans" mekanizması mevcuttur.</p>
<p>Emeğinizin neye göre, nasıl değerlendirildiğini anlamak için aşağıdaki matrisi inceleyebilirsiniz:</p>
<br>
<h3 style='color: #FF3B30;'>⛔ KATEGORİ 0: İnfaz Kurulu (MQM: Critical / Ölümcül Hata)</h3>
<p><b>Ağırlık: Puanlama Dışı (Doğrudan Ret)</b></p>
<p>Bu kategorideki ihlaller, altyazının okunabilirliğini değil, doğrudan oynatılabilirliğini ve temel yayın standartlarını hedefler. Bir dosyanın puanı 99 bile olsa, aşağıdaki hatalardan birini barındırıyorsa sistem tarafından kırmızı kart görür ve "REDDEDİLDİ" durumuna düşer.</p>
<ul>
<li><b>Zaman Kodu Çakışması (Overlapping):</b> Bir altyazı bitmeden diğerinin başlaması.</li>
<li><b>Çoklu Satır İhlali:</b> Ekranda tek bir blokta 3 veya daha fazla satırın yer alması.</li>
</ul>
<br>
<h3 style='color: #FF9500;'>🔴 KATEGORİ 1: Okunabilirlik ve Akış (MQM: Major / Büyük Hata)</h3>
<p><b>Ağırlık: Toplam Skorun %50'si (Maksimum 50 Puan)</b></p>
<p>Bir altyazının varoluş amacı izleyici tarafından, filmin temposundan kopmadan okunabilmesidir. İzleyicinin gözü metne yetişemiyorsa, geri kalan hiçbir unsurun önemi yoktur.</p>
<ul>
<li><b>CPS (Okuma Hızı) Aşımı:</b> Saniyede okunan karakter sayısının (seçili dil profiline göre) maksimum sınırı aşması. İhlaller, oranlarına göre bu 50 puanlık dilimden ağır kesintiler yapar.</li>
<li><b>Flaş ve Zombi Altyazılar:</b> Ekranda insan gözünün algılayamayacağı kadar kısa (örn: 0,7 sn altı) veya gereksiz yere uzun (örn: 7 sn üstü) kalan metinler.</li>
</ul>
<br>
<h3 style='color: #FFCC00;'>🟡 KATEGORİ 2: Görsel Konfor ve Yerleşim (MQM: Major-Minor / Orta Düzey Hata)</h3>
<p><b>Ağırlık: Toplam Skorun %35'i (Maksimum 35 Puan)</b></p>
<p>Metin rahat okunabilir hızda olsa bile, ekranda kapladığı alan ve gözü yorma potansiyeli bu kategoride değerlendirilir.</p>
<ul>
<li><b>CPL (Satır Genişliği) Aşımı:</b> Satır başına düşen karakter sayısının sınırları aşması. Uzun satırlar izleyicinin gözünü ekranın bir ucundan diğer ucuna savurur.</li>
<li><b>Boşluk İhlali (Frame Gap):</b> Arka arkaya gelen iki altyazı arasında yeterli milisaniye boşluğunun bırakılmaması, ekranda titreme (flicker) hissi yaratır.</li>
<li><b>Satır Dengesi (Piramit Kuralı):</b> İki satırlık bloklarda üst ve alt satırın karakter sayıları arasında uçurum olması. Gözün metni okurken dikeyde dengesiz bir sıçrama yapmasına neden olur.</li>
</ul>
<br>
<h3 style='color: #34C759;'>🟢 KATEGORİ 3: Tipografik Hijyen ve İşçilik (MQM: Minor / Küçük Hata)</h3>
<p><b>Ağırlık: Toplam Skorun %15'i (Maksimum 15 Puan)</b></p>
<p>Zamanlaması ve akışı kusursuz bir metnin, çevirmenin zanaatkar tarafını gösterdiği detaylarıdır. Çeviri "Vasat" durumuna düşmez ancak "Arşivlik" seviyesine çıkmasını engelleyen pürüzler burada cezalandırılır. Bu kategori, oran hesabı yerine maktu (sabit) cezalarla çalışır.</p>
<ul>
<li><b>Çift Boşluklar (Double Spaces):</b> Kelimeler arası bırakılan hantal ve gereksiz boşluklar.</li>
<li><b>Noktalama Hataları:</b> Virgül veya noktadan önce bırakılan boşluklar.</li>
<li><b>Bozuk Etiketler:</b> Açılıp (örn: &lt;i&gt;) kapanmayan veya hatalı uygulanan HTML etiketleri.</li>
<li><b>İşaret İstismarı:</b> Üç nokta yerine üç adet tekil nokta kullanılması gibi kuraldışı sembol kullanımları.</li>
</ul>
"""
            },
            "EN": {
                "window_title": "nCheck - Subtitle Technical Quality Control Panel v0.5",
                "panel_title": "🎬 nCheck - Subtitle Technical Quality Control Panel v0.5",
                "title_tr": "TURKISH TARGET (TR)",
                "opt_optional": "Optional",
                "opt_required": "Required",
                "drag_hint": "Drag & Drop SRT or ASS File Here",
                "status_success": "Success!",
                "err_srt_ass_only": "Please load only .srt or .ass files.",
                "tab_home": "Home",
                "tab_technical": "Technical Proficiency",
                "tab_settings": "Standards",
                "tab_history": "History",
                "tab_about": "About",
                "btn_process_only_tech": "Perform Only Technical Analysis",
                "btn_load_tr_prompt": "Please Load TR File...",
                "group_thresholds": "🚧 Tech Violation Thresholds",
                "group_penalties": "⚖️ Tech Penalty Multipliers",
                "lbl_cps": "Max Reading (CPS):",
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
                "about_body": "<b>nCheck - Subtitle Technical Quality Control Panel</b><br><br><b>Developer:</b> nutuzar<br><b>Version:</b> 0.5",
                "rep_title": "⚙️ nCheck v0.5 Subtitle Technical Analysis Report\n",
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
                "btn_save_pdf": "Save Report as PDF",
                "btn_delete_history": "Delete from History",
                "lbl_vault": "Vault",
                "pl_vault_pwd": "Enter Password...",
                "btn_unlock": "Unlock",
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
                "manifesto": """
<h2 style='color: #007AFF;'>nCheck Quality Evaluation Manifesto (MQM Based)</h2>
<p>nCheck completely rejects the logic of random point deductions or "arbitrary coefficients" when evaluating subtitle files (SRT/ASS). The foundation of its scoring algorithm is based on the MQM (Multidimensional Quality Metrics) standards used by the global broadcasting industry (Netflix, Disney, EBU).</p>
<p>The final score out of 100 that a file receives is divided into three main centers of gravity (50%, 35%, 15%) based on the viewer's cognitive capacity, the visual ergonomics of the screen, and the typographic craftsmanship of the text. Furthermore, there is a "Zero Tolerance" mechanism that operates independently of the score.</p>
<p>You can review the matrix below to understand how and on what basis your labor is evaluated:</p>
<br>
<h3 style='color: #FF3B30;'>⛔ CATEGORY 0: Execution Board (MQM: Critical / Fatal Error)</h3>
<p><b>Weight: Excluded from Scoring (Direct Rejection)</b></p>
<p>Violations in this category target the direct playability and basic broadcasting standards of the subtitle, rather than its readability. Even if a file scores 99, if it contains one of the following errors, it receives a red card from the system and falls into the "REJECTED" status.</p>
<ul>
<li><b>Timecode Overlap:</b> A subtitle starting before the previous one ends.</li>
<li><b>Multiple Line Violation:</b> Having 3 or more lines in a single block on the screen.</li>
</ul>
<br>
<h3 style='color: #FF9500;'>🔴 CATEGORY 1: Readability and Flow (MQM: Major / Major Error)</h3>
<p><b>Weight: 50% of Total Score (Maximum 50 Points)</b></p>
<p>The existential purpose of a subtitle is to be read by the viewer without breaking away from the tempo of the film. If the viewer's eyes cannot catch up with the text, no other element matters.</p>
<ul>
<li><b>CPS (Reading Speed) Violation:</b> Exceeding the maximum limit of characters read per second (according to the selected language profile). Violations make heavy deductions from this 50-point slice based on their ratios.</li>
<li><b>Flash and Zombie Subtitles:</b> Texts that remain on the screen for too short a time for the human eye to perceive (e.g., under 0.7s) or unnecessarily long (e.g., over 7s).</li>
</ul>
<br>
<h3 style='color: #FFCC00;'>🟡 CATEGORY 2: Visual Comfort and Placement (MQM: Major-Minor / Medium Level Error)</h3>
<p><b>Weight: 35% of Total Score (Maximum 35 Points)</b></p>
<p>Even if the text is at a comfortably readable speed, the area it covers on the screen and its potential to strain the eyes are evaluated in this category.</p>
<ul>
<li><b>CPL (Line Width) Violation:</b> Exceeding the limits of the number of characters per line. Long lines throw the viewer's eyes from one end of the screen to the other.</li>
<li><b>Frame Gap Violation:</b> Not leaving enough millisecond gaps between two consecutive subtitles creates a flicker sensation on the screen.</li>
<li><b>Line Balance (Pyramid Rule):</b> Having a massive gap between the character counts of the upper and lower lines in two-line blocks. It causes the eye to make an unbalanced vertical jump while reading the text.</li>
</ul>
<br>
<h3 style='color: #34C759;'>🟢 CATEGORY 3: Typographic Hygiene and Craftsmanship (MQM: Minor / Minor Error)</h3>
<p><b>Weight: 15% of Total Score (Maximum 15 Points)</b></p>
<p>These are the details that show the artisan side of the translator in a text with perfect timing and flow. The translation does not fall into the "Mediocre" status, but the roughness that prevents it from reaching the "Archive" level is punished here. This category works with fixed (flat) penalties instead of ratio calculation.</p>
<ul>
<li><b>Double Spaces:</b> Clunky and unnecessary spaces left between words.</li>
<li><b>Punctuation Errors:</b> Spaces left before commas or periods.</li>
<li><b>Broken Tags:</b> HTML tags that are opened (e.g., &lt;i&gt;) but not closed, or applied incorrectly.</li>
<li><b>Symbol Exploitation:</b> Illegal symbol uses, such as using three single dots instead of an ellipsis.</li>
</ul>
"""
            }
        }

        self.setup_ui()
        self.populate_history()

    def closeEvent(self, event):
        self.save_current_settings()
        super().closeEvent(event)

    def save_current_settings(self):
        if hasattr(self, 'spin_cps'):
            self.config["cps"] = self.spin_cps.value()
            self.config["cpl"] = self.spin_cpl.value()
            self.config["flash"] = self.spin_flash.value()
            self.config["zombie"] = self.spin_zombie.value()
            self.config["gap"] = self.spin_gap.value()
            save_config(self.config)

    def lock_settings(self, lock):
        for w in [self.spin_cps, self.spin_cpl, self.spin_flash, self.spin_zombie, self.spin_gap]:
            w.setReadOnly(lock)
            w.setEnabled(not lock)

    def unlock_settings(self):
        if self.password_input.text() == "1969":
            self.lock_settings(False)
            QMessageBox.information(self, "Zindan", "Kilit Açıldı! Standartları değiştirebilirsiniz.")
            self.password_input.clear()
        else:
            QMessageBox.warning(self, "Hata", "Yanlış Şifre!")

    def setup_ui(self):
        self.resize(1625, 1235)
        self.setStyleSheet("""
            QMainWindow { background-color: #0E0E11; color: #F0F0F5; font-family: 'Segoe UI Variable', 'Segoe UI', system-ui; }
            QWidget { background-color: #0E0E11; color: #F0F0F5; font-family: 'Segoe UI Variable', 'Segoe UI', system-ui; }
            QTabWidget::pane { border: 1px solid #23232A; background: #16161A; border-radius: 12px; margin-top: -1px; }
            QTabBar::tab { background: #1C1C22; color: #7A7A8A; padding: 16px 14px; min-width: 180px; border-top-left-radius: 10px; border-top-right-radius: 10px; margin-right: 6px; font-weight: 700; font-size: 15px; }
            QTabBar::tab:selected { background: #16161A; color: #FFFFFF; border-bottom: 3px solid #007AFF; }
            QTabBar::tab:hover:!selected { background: #23232A; color: #FFFFFF; }
            QGroupBox { border: 1px solid #2A2A35; border-radius: 12px; margin-top: 28px; padding-top: 24px; color: #FFFFFF; font-size: 15px; background: #16161A; }
            QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 10px; color: #007AFF; font-weight: bold; font-size: 16px; }
            QPushButton { background-color: #007AFF; border: none; border-radius: 10px; color: #FFFFFF; padding: 14px; font-weight: bold; font-size: 16px; }
            QPushButton:hover { background-color: #0056B3; }
            QPushButton:disabled { background-color: #23232A; color: #555565; }
            QTextEdit, QTextBrowser { background-color: #111115; border: 1px solid #2A2A35; border-radius: 10px; padding: 18px; color: #E5E5E5; font-size: 15px; line-height: 1.6; }
            QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background-color: #1C1C22; border: 1px solid #333340; border-radius: 8px; color: #FFFFFF; padding: 10px; min-width: 70px; font-size: 15px; }
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus { border: 1px solid #007AFF; background-color: #23232A; }
            QSpinBox:disabled, QDoubleSpinBox:disabled { background-color: #16161A; color: #666677; border: 1px solid #23232A; }
            QLabel { color: #E5E5E5; font-size: 15px; }
            QScrollArea { border: none; background-color: transparent; }
            QListWidget { background-color: #111115; border: 1px solid #2A2A35; border-radius: 10px; font-size: 15px; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #1C1C22; }
            QListWidget::item:selected { background-color: #1C1C22; color: #007AFF; font-weight: bold; border-left: 4px solid #007AFF; }
            QProgressBar { border: 1px solid #2A2A35; border-radius: 10px; background-color: #111115; color: #FFFFFF; font-weight: bold; text-align: center; height: 32px; }
            QProgressBar::chunk { background-color: #007AFF; border-radius: 10px; width: 20px; }
            QRadioButton { color: #FFFFFF; font-weight: bold; font-size: 15px; padding: 5px; }
            QRadioButton::indicator { width: 18px; height: 18px; border-radius: 9px; border: 2px solid #555565; background: #1E1E24; }
            QRadioButton::indicator:checked { background: #007AFF; border: 2px solid #007AFF; }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

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
        self.home_layout.setContentsMargins(30, 30, 30, 30)
        self.home_layout.setSpacing(25)

        # SCORE BOARD
        self.score_board_layout = QHBoxLayout()
        self.score_board_layout.setSpacing(20)
        
        self.tech_score_lbl = QLabel("TEKNİK YETERLİLİK\n--")
        self.tech_score_lbl.setAlignment(Qt.AlignCenter)
        self.tech_score_lbl.setFont(QFont("Segoe UI Variable", 14, QFont.Bold))
        self.tech_score_lbl.setStyleSheet("QLabel { background-color: #2D2D30; border-radius: 12px; padding: 20px; color: #FFFFFF; border: 2px solid #444444; }")
        

        
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
        self.process_button.setMinimumHeight(65)
        self.process_button.setStyleSheet("QPushButton { background-color: #FF9500; } QPushButton:hover { background-color: #FFA522; }")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.start_technical_analysis)
        
        self.clear_btn = QPushButton("Yeni / Temizle")
        self.clear_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.clear_btn.setMinimumHeight(65)
        self.clear_btn.setStyleSheet("QPushButton { background-color: #555565; color: #FFF; } QPushButton:hover { background-color: #444455; }")
        self.clear_btn.clicked.connect(self.clear_current_file)
        
        self.open_folder_btn = QPushButton("Çıktı Klasörünü Aç")
        self.open_folder_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.open_folder_btn.setMinimumHeight(65)
        self.open_folder_btn.setStyleSheet("QPushButton { background-color: #30D158; color: #FFF; } QPushButton:hover { background-color: #28C14E; }")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        
        self.action_buttons_layout.addWidget(self.process_button, stretch=2)
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
        
        self.save_pdf_btn = QPushButton("PDF Olarak Kaydet")
        self.save_pdf_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.save_pdf_btn.setMinimumHeight(45)
        self.save_pdf_btn.setStyleSheet("QPushButton { background-color: #007AFF; color: #FFF; padding: 10px 20px; border-radius: 8px;} QPushButton:hover { background-color: #0056B3; } QPushButton:disabled { background-color: #333333; color: #777777; }")
        self.save_pdf_btn.clicked.connect(self._on_save_pdf_clicked)
        self.save_pdf_btn.setEnabled(False)
        
        self.tech_header_layout.addWidget(self.tech_header_lbl)
        self.tech_header_layout.addStretch()
        self.tech_header_layout.addWidget(self.save_pdf_btn)
        
        self.tech_text = QTextEdit()
        self.tech_text.setReadOnly(True)
        self.tech_text.setFont(QFont("Consolas", 12))
        self.tech_text.setStyleSheet("QTextEdit { background-color: #111115; color: #30D158; padding: 15px; border-radius: 10px; border: 1px solid #2A2A35;}")
        
        self.tech_layout.addLayout(self.tech_header_layout)
        self.tech_layout.addWidget(self.tech_text)
        self.tabs.addTab(self.tech_tab, "")

        # Tab 4: Ayarlar
        # Tab 4: Ayarlar (Standartlar)
        self.settings_tab = QWidget()
        self.settings_layout = QHBoxLayout(self.settings_tab)
        
        self.manifesto_browser = QTextBrowser()
        self.manifesto_browser.setOpenExternalLinks(True)
        self.manifesto_browser.setHtml(self.get_text("manifesto"))
        self.settings_layout.addWidget(self.manifesto_browser, stretch=7)
        
        self.controls_layout = QVBoxLayout()
        self.controls_layout.setSpacing(15)
        
        self.threshold_group = QGroupBox(self.get_text("group_thresholds"))
        self.threshold_group.setFont(QFont("Segoe UI Variable", 10, QFont.Bold))
        self.form_threshold = QFormLayout(self.threshold_group)
        self.form_threshold.setContentsMargins(15, 25, 15, 15)
        
        self.spin_cps = QDoubleSpinBox(); self.spin_cps.setRange(10.0, 40.0); self.spin_cps.setSingleStep(0.5); self.spin_cps.setValue(self.config.get("cps", 21.0))
        self.spin_cpl = QSpinBox(); self.spin_cpl.setRange(20, 80); self.spin_cpl.setValue(self.config.get("cpl", 40))
        self.spin_flash = QDoubleSpinBox(); self.spin_flash.setRange(0.1, 2.0); self.spin_flash.setSingleStep(0.1); self.spin_flash.setValue(self.config.get("flash", 0.7))
        self.spin_zombie = QDoubleSpinBox(); self.spin_zombie.setRange(2.0, 15.0); self.spin_zombie.setSingleStep(0.5); self.spin_zombie.setValue(self.config.get("zombie", 7.0))
        self.spin_gap = QSpinBox(); self.spin_gap.setRange(0, 500); self.spin_gap.setValue(self.config.get("gap", 24))
        
        self.lbl_cps_node = QLabel(self.get_text("lbl_cps")); self.form_threshold.addRow(self.lbl_cps_node, self.spin_cps)
        self.lbl_cpl_node = QLabel(self.get_text("lbl_cpl")); self.form_threshold.addRow(self.lbl_cpl_node, self.spin_cpl)
        self.lbl_flash_node = QLabel(self.get_text("lbl_flash")); self.form_threshold.addRow(self.lbl_flash_node, self.spin_flash)
        self.lbl_zombie_node = QLabel(self.get_text("lbl_zombie")); self.form_threshold.addRow(self.lbl_zombie_node, self.spin_zombie)
        self.lbl_gap_node = QLabel(self.get_text("lbl_gap")); self.form_threshold.addRow(self.lbl_gap_node, self.spin_gap)

        self.vault_group = QGroupBox("Kilit")
        self.vault_group.setFont(QFont("Segoe UI Variable", 10, QFont.Bold))
        self.vault_layout = QVBoxLayout(self.vault_group)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Şifre Girin...")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.unlock_btn = QPushButton("Kilidi Aç")
        self.unlock_btn.clicked.connect(self.unlock_settings)
        
        self.vault_layout.addWidget(self.password_input)
        self.vault_layout.addWidget(self.unlock_btn)
        self.vault_layout.addStretch()

        self.controls_layout.addWidget(self.threshold_group)
        self.controls_layout.addWidget(self.vault_group)
        self.controls_layout.addStretch()
        
        self.settings_layout.addLayout(self.controls_layout, stretch=3)
        self.lock_settings(True)
        self.tabs.addTab(self.settings_tab, "")

        # Tab 5: Geçmiş
        self.history_tab = QWidget()
        self.history_layout = QHBoxLayout(self.history_tab)
        
        self.history_list = QListWidget()
        self.history_list.setFixedWidth(300)
        self.history_list.itemSelectionChanged.connect(self.on_history_selected)
        
        self.history_detail_layout = QVBoxLayout()
        self.history_detail_text = QTextEdit()
        self.history_detail_text.setReadOnly(True)
        self.history_detail_text.setFont(QFont("Consolas", 11))
        
        self.history_pdf_btn = QPushButton("Bu Raporu PDF Olarak Kaydet")
        self.history_pdf_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.history_pdf_btn.setStyleSheet("QPushButton { background-color: #FF453A; color: #FFF; padding: 15px; } QPushButton:hover { background-color: #D70015; }")
        self.history_pdf_btn.clicked.connect(self.save_history_pdf)
        self.history_pdf_btn.setEnabled(False)
        
        self.history_delete_btn = QPushButton("Geçmişten Sil")
        self.history_delete_btn.setFont(QFont("Segoe UI Variable", 12, QFont.Bold))
        self.history_delete_btn.setStyleSheet("QPushButton { background-color: #333333; color: #FFF; padding: 15px; } QPushButton:hover { background-color: #555555; }")
        self.history_delete_btn.clicked.connect(self.delete_history_entry)
        self.history_delete_btn.setEnabled(False)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.history_pdf_btn)
        buttons_layout.addWidget(self.history_delete_btn)
        
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
        self.about_text.setStyleSheet("border: none; font-size: 22px; line-height: 1.8; margin: 40px; background: transparent;")
        self.about_text.setAlignment(Qt.AlignCenter)
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
        self.save_pdf_btn.setEnabled(False)
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
            self.history_pdf_btn.setEnabled(False)
            self.history_delete_btn.setEnabled(False)
            return
            
        idx = selected[0].data(Qt.UserRole)
        entry = self.history[idx]
        
        t_s = entry.get('tech_score', 0)
        display_text = f"Tarih: {entry.get('date', '')}\n"
        display_text += f"Dosya: {entry.get('filename', '')}\n"
        display_text += f"Teknik Skor: {t_s}\n"
        display_text += "="*60 + "\n\n"
        display_text += "--- TEKNİK YETERLİLİK ---\n" + entry.get('tech_report', '')
        
        self.history_detail_text.setPlainText(display_text)
        self.history_pdf_btn.setEnabled(True)
        self.history_delete_btn.setEnabled(True)

    def save_history_pdf(self):
        selected = self.history_list.selectedItems()
        if not selected: return
        idx = selected[0].data(Qt.UserRole)
        entry = self.history[idx]
        
        self.save_pdf_report(
            entry.get('tech_report', ''),
            entry.get('tech_score', 0),
            entry.get('is_red_card', False),
            entry.get('stats', {}),
            default_filename=f"nCheck_History_{entry.get('filename', 'report')}.pdf"
        )

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
            self.history_pdf_btn.setEnabled(False)
            self.history_delete_btn.setEnabled(False)

    def switch_language(self):
        if self.radio_en.isChecked():
            self.current_lang = "EN"
            self.spin_cps.setValue(18.0)
            self.spin_cpl.setValue(38)
        else:
            self.current_lang = "TR"
            self.spin_cps.setValue(21.0)
            self.spin_cpl.setValue(40)
        self.refresh_ui_texts()
        self.update_ui_state()
        
        # Otomatik re-analyze if a report is currently displayed
        if hasattr(self, 'tech_text') and self.tech_text.toPlainText().strip() != "":
            if hasattr(self, 'tr_drop_box') and self.tr_drop_box.file_path:
                self.start_technical_analysis(show_msg=False)

    def validate_subtitle_language(self, file_path):
        try:
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='windows-1254') as f:
                    lines = f.readlines()
        except Exception:
            return True
            
        text_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.isdigit() or '-->' in line:
                continue
            if line.startswith('[') or line.startswith('Format:'):
                continue
            text_lines.append(line)
            
        if not text_lines:
            return True
            
        start_idx = len(text_lines) // 4
        end_idx = start_idx * 3
        body_text = "".join(text_lines[start_idx:end_idx]).lower()
        
        tr_chars = ['ğ', 'ş', 'ı', 'ö', 'ç', 'ü']
        tr_char_count = sum(body_text.count(c) for c in tr_chars)
        
        if self.current_lang == "EN" and tr_char_count >= 10:
            QMessageBox.critical(self, "HATA / ERROR", "İngilizce (EN) modu seçili ancak yüklenen dosya Türkçe.\nLütfen hedef dili düzeltin.\n\nEnglish (EN) mode is selected but the file is in Turkish.\nPlease correct the target language.")
            return False
            
        if self.current_lang == "TR" and tr_char_count == 0:
            QMessageBox.critical(self, "HATA / ERROR", "Türkçe (TR) modu seçili ancak dosyada hiçbir Türkçe karakter bulunamadı.\nLütfen hedef dili düzeltin.\n\nTurkish (TR) mode is selected but the file has no Turkish characters.\nPlease correct the target language.")
            return False
            
        return True

    def refresh_ui_texts(self):
        self.setWindowTitle(self.get_text("window_title"))
        self.header_label.setText(self.get_text("panel_title"))
        self.tr_drop_box.refresh_text()
        
        self.tabs.setTabText(0, self.get_text("tab_home"))
        self.tabs.setTabText(1, self.get_text("tab_technical"))
        self.tabs.setTabText(2, self.get_text("tab_settings"))
        self.tabs.setTabText(3, self.get_text("tab_history"))
        self.tabs.setTabText(4, self.get_text("tab_about"))
        
        self.threshold_group.setTitle(self.get_text("group_thresholds"))
        self.lbl_cps_node.setText(self.get_text("lbl_cps"))
        self.lbl_cpl_node.setText(self.get_text("lbl_cpl"))
        self.lbl_flash_node.setText(self.get_text("lbl_flash"))
        self.lbl_zombie_node.setText(self.get_text("lbl_zombie"))
        self.lbl_gap_node.setText(self.get_text("lbl_gap"))

        self.tech_header_lbl.setText(self.get_text("lbl_analysis_results"))
        self.clear_btn.setText(self.get_text("btn_clear"))
        self.open_folder_btn.setText(self.get_text("btn_open_folder"))
        self.save_pdf_btn.setText(self.get_text("btn_save_pdf"))
        self.history_pdf_btn.setText(self.get_text("btn_save_pdf"))
        self.history_delete_btn.setText(self.get_text("btn_delete_history"))
        self.vault_group.setTitle(self.get_text("lbl_vault"))
        self.password_input.setPlaceholderText(self.get_text("pl_vault_pwd"))
        self.unlock_btn.setText(self.get_text("btn_unlock"))

        self.about_text.setHtml(f"<div align='center'>{self.get_text('about_body')}</div>")
        if hasattr(self, 'manifesto_browser'):
            self.manifesto_browser.setHtml(self.get_text('manifesto'))

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
        else:
            self.process_button.setEnabled(False)
            self.process_button.setText(self.get_text("btn_load_tr_prompt"))
            self.process_button.setStyleSheet("QPushButton { background-color: #333333; color: #777777; }")

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

    def analyze_technical(self, file_path):
        try:
            subs = self.load_subtitles(file_path)
        except Exception as e:
            return f"Teknik analiz okuma hatası: {str(e)}", 0, False

        total_lines = len(subs)
        if total_lines == 0:
            return "Dosya boş, tamamen yoksayıldı veya geçersiz.", 0, False

        val_cps_limit = self.spin_cps.value()
        val_cpl_limit = self.spin_cpl.value()
        val_flash_min = self.spin_flash.value()
        val_zombie_max = self.spin_zombie.value()
        val_gap_ms = self.spin_gap.value()

        cat0_violations = 0
        cat0_reasons = []
        cps_violations = 0
        duration_violations = 0
        cpl_violations = 0
        gap_violations = 0
        pyramid_violations = 0
        typo_blocks = 0

        for i, sub in enumerate(subs):
            text = sub.text_without_tags.strip()
            raw_text = sub.text.strip()
            
            lines = text.split('\n')
            
            # Kategori 0: İnfaz Kurulu
            is_cat0 = False
            if len(lines) >= 3:
                is_cat0 = True
                cat0_reasons.append(self.get_text("rep_cat0_r1").format(i+1))
            
            if i < total_lines - 1:
                next_sub = subs[i+1]
                if sub.end.ordinal > next_sub.start.ordinal:
                    is_cat0 = True
                    cat0_reasons.append(self.get_text("rep_cat0_r2").format(i+1, i+2))
                    
            if is_cat0:
                cat0_violations += 1

            # Kategori 1 & 2
            is_cpl_violation = False
            for line in lines:
                if len(line) > val_cpl_limit:
                    is_cpl_violation = True
                    break
            if is_cpl_violation:
                cpl_violations += 1
                
            # Piramit Kuralı (Kat 2)
            if len(lines) == 2:
                if abs(len(lines[0]) - len(lines[1])) > 12:
                    pyramid_violations += 1

            duration_sec = (sub.end.ordinal - sub.start.ordinal) / 1000.0
            if duration_sec > 0:
                cps = len(text) / duration_sec
                if cps > val_cps_limit:
                    cps_violations += 1
                if duration_sec < val_flash_min or duration_sec > val_zombie_max:
                    duration_violations += 1
            else:
                duration_violations += 1

            if i < total_lines - 1:
                next_sub = subs[i+1]
                gap_ms = next_sub.start.ordinal - sub.end.ordinal
                if gap_ms >= 0 and gap_ms < val_gap_ms:
                    gap_violations += 1
                    
            # Kategori 3: Tipografik Hijyen
            has_typo = False
            if "  " in raw_text: has_typo = True
            if re.search(r'\s+[,.?!]', raw_text): has_typo = True
            
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
        
        if cat0_violations > 0:
            status = self.get_text("rep_rejected")
            final_score_str = f"{final_score:.1f} " + self.get_text("rep_disqualified")
        else:
            t_star, t_color, t_stat = get_rating_info(final_score, self.current_lang)
            status = f"{t_star} {t_stat}"
            final_score_str = f"{final_score:.1f} / 100"

        report = ""
        report += self.get_text('rep_title')
        report += self.get_text('rep_file') + os.path.basename(file_path) + "\n"
        report += self.get_text('rep_total_lines') + str(total_lines) + "\n"
        
        if not getattr(self, 'last_file_is_utf8', True):
            report += self.get_text("rep_warn_utf8")
        
        report += "\n"
        
        if cat0_violations > 0:
            report += self.get_text("rep_cat0_title")
            for r in cat0_reasons[:5]:
                report += f"  - {r}\n"
            if len(cat0_reasons) > 5:
                report += self.get_text("rep_cat0_r3").format(len(cat0_reasons) - 5)
            report += self.get_text("rep_cat0_result")
            
        report += self.get_text("rep_cat1_title")
        if R_cps > 0: report += self.get_text("rep_cat1_cps").format(val_cps_limit, R_cps)
        if R_dur > 0: report += self.get_text("rep_cat1_dur").format(val_flash_min, val_zombie_max, R_dur)
        report += self.get_text("rep_cat1_score").format(cat1_score)
        
        report += self.get_text("rep_cat2_title")
        if R_cpl > 0: report += self.get_text("rep_cat2_cpl").format(val_cpl_limit, R_cpl)
        if R_gap > 0: report += self.get_text("rep_cat2_gap").format(val_gap_ms, R_gap)
        if pyramid_violations > 0: report += self.get_text("rep_cat2_pyr").format(pyramid_violations, pyramid_violations * 0.5)
        report += self.get_text("rep_cat2_score").format(cat2_score)
        
        report += self.get_text("rep_cat3_title")
        if typo_blocks > 0: report += self.get_text("rep_cat3_typo").format(typo_blocks, cat3_deduction)
        report += self.get_text("rep_cat3_score").format(cat3_score)
        
        report += self.get_text("rep_score") + final_score_str + "\n"
        report += self.get_text("rep_status") + status
        
        stats = {
            'cat1_score': cat1_score,
            'cat2_score': cat2_score,
            'cat3_score': cat3_score,
            'final_score': round(final_score, 1),
            'status': status,
            'R_cps': R_cps,
            'R_dur': R_dur,
            'R_cpl': R_cpl,
            'R_gap': R_gap,
            'pyramid': pyramid_violations,
            'typo': typo_blocks,
            'cat0_violations': cat0_violations,
            'cat0_reasons': cat0_reasons,
            'val_cps_limit': val_cps_limit,
            'val_flash_min': val_flash_min,
            'val_zombie_max': val_zombie_max,
            'val_cpl_limit': val_cpl_limit,
            'val_gap_ms': val_gap_ms,
            'cat3_deduction': cat3_deduction,
            'final_score_str': final_score_str,
            'total_lines': total_lines
        }
        return report, round(final_score, 1), cat0_violations > 0, stats

    def set_score_labels(self, tech_score, is_red_card=False):
        if is_red_card:
            self.tech_score_lbl.setText(f"TEKNİK YETERLİLİK\n{tech_score} / 100\n🔴 REDDEDİLDİ")
            self.tech_score_lbl.setStyleSheet(f"QLabel {{ background-color: #2D2D30; border-radius: 12px; padding: 20px; color: #FF3B30; border: 2px solid #FF3B30; font-size: 13pt; font-weight: bold; }}")
            return
            
        t_star, tc, t_stat = get_rating_info(tech_score) if tech_score > 0 else ("--", "#444444", "--")
        tech_text = f"{tech_score} {t_star}" if tech_score > 0 else "--"
        
        self.tech_score_lbl.setText(f"TEKNİK YETERLİLİK\n{tech_text}")
        self.tech_score_lbl.setStyleSheet(f"QLabel {{ background-color: #2D2D30; border-radius: 12px; padding: 20px; color: {tc}; border: 2px solid {tc}; font-size: 13pt; }}")

    def start_technical_analysis(self, show_msg=True):
        self.current_tech_score = 0
        self.set_score_labels(0)
        self.tech_text.clear()
        
        tech_report, tech_score, is_red_card, stats = self.analyze_technical(self.tr_drop_box.file_path)
        self.current_tech_score = tech_score
        self.current_tech_report = tech_report
        self.current_tech_stats = stats
        self.current_is_red_card = is_red_card
        
        ui_html = tech_report.replace('\n', '<br>')
        ui_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', ui_html)
        self.tech_text.setHtml(f"<div style='font-family: Consolas;'>{ui_html}</div>")
        
        self.set_score_labels(tech_score, is_red_card)
        
        self.save_pdf_btn.setEnabled(True)
        
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": os.path.basename(self.tr_drop_box.file_path),
            "tech_score": tech_score,
            "is_red_card": is_red_card,
            "tech_report": tech_report,
            "stats": stats
        }
        self.history.append(entry)
        save_history(self.history)
        self.populate_history()
        
        self.tabs.setCurrentIndex(1)
        self.tabs.setCurrentIndex(1)
        if show_msg:
            QMessageBox.information(self, "nCheck", self.get_text("msg_success_body"))

    def _on_save_pdf_clicked(self, checked=False):
        tech_report = getattr(self, 'current_tech_report', '')
        tech_score = getattr(self, 'current_tech_score', 0)
        is_red_card = getattr(self, 'current_is_red_card', False)
        stats = getattr(self, 'current_tech_stats', {})
        self.save_pdf_report(tech_report, tech_score, is_red_card, stats)

    def save_pdf_report(self, tech_content, tech_score, is_red_card, stats, default_filename=None):
        if not tech_content:
            return
            
        if not default_filename:
            default_name = "nCheck_Auto_QC_Report.pdf"
            if self.tr_drop_box.file_path is not None:
                base_name = os.path.basename(self.tr_drop_box.file_path)
                base_without_ext = os.path.splitext(base_name)[0]
                default_name = f"nCheck_Auto_QC_{base_without_ext}.pdf"
        else:
            default_name = default_filename

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "PDF Kaydet", default_name, "PDF Files (*.pdf);;All Files (*)", options=options)
        
        if file_path:
            try:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                
                t_star, t_color, t_stat = get_rating_info(tech_score, self.current_lang) if tech_score > 0 else ("--", "#444444", "--")
                
                if is_red_card:
                    stat_str = "REDDEDİLDİ" if self.current_lang == "TR" else "REJECTED"
                    stamp_color = "#FF3B30"
                    score_str = "--"
                else:
                    stat_str = t_stat.upper()
                    stamp_color = t_color
                    score_str = f"{tech_score:.1f}" if isinstance(tech_score, (int, float)) else str(tech_score)

                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                target_filename = os.path.basename(self.tr_drop_box.file_path) if hasattr(self, 'tr_drop_box') and self.tr_drop_box.file_path else "History_File"
                if default_filename:
                    target_filename = default_filename.replace("nCheck_History_", "").replace(".pdf", "")

                log_lines = tech_content.split('\n')
                filtered_log = []
                for line in log_lines:
                    if "KATEGORİ" in line or "CATEGORY" in line or "İhlal" in line or "Violation" in line or "Ceza" in line or "Penalty" in line or "Blok" in line or "Block" in line or "SONUÇ" in line or "RESULT" in line:
                        filtered_log.append(line)
                
                html_log = "<br>".join(filtered_log)
                html_log = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_log)

                stats = stats or {}
                c1_score = stats.get('cat1_score', 0)
                c2_score = stats.get('cat2_score', 0)
                c3_score = stats.get('cat3_score', 0)

                cat1_name = "Okunabilirlik" if self.current_lang == "TR" else "Readability"
                cat2_name = "Görsel Konfor" if self.current_lang == "TR" else "Visual Comfort"
                cat3_name = "Hijyen" if self.current_lang == "TR" else "Hygiene"
                
                date_lbl = "Tarih" if self.current_lang == "TR" else "Date"
                file_lbl = "Dosya" if self.current_lang == "TR" else "File"
                viol_title = "Detaylı İhlal Logu" if self.current_lang == "TR" else "Detailed Violation Log"

                html_template = f"""
                <html>
                <head>
                <style>
                    body {{ font-family: 'Segoe UI', Helvetica, sans-serif; font-size: 11pt; color: #333; }}
                    .report-container {{ border: 2px solid {stamp_color}; padding: 20px; border-radius: 10px; }}
                    h1, h2, h3 {{ margin: 0; padding: 0; }}
                    .header-table {{ width: 100%; border-bottom: 2px solid #EEE; padding-bottom: 15px; margin-bottom: 20px; }}
                    .dashboard-table {{ width: 100%; border-collapse: separate; border-spacing: 15px 0; margin-bottom: 30px; }}
                    .dash-box {{ background-color: #F8F9FA; border: 1px solid #DDD; padding: 15px; text-align: center; border-radius: 8px; }}
                    .box-title {{ font-size: 12pt; color: #666; font-weight: bold; margin-bottom: 10px; }}
                    .box-score {{ font-size: 24pt; font-weight: bold; color: {stamp_color}; }}
                    .log-section {{ background-color: #F9F9F9; padding: 15px; border-left: 5px solid {stamp_color}; font-family: 'Consolas', monospace; font-size: 10pt; line-height: 1.5; }}
                </style>
                </head>
                <body>
                
                <div class="report-container">
                    <table class="header-table">
                        <tr>
                            <td width="60%">
                                <h1 style="color: #222;">nCheck Auto-QC Report</h1>
                                <p><b>{date_lbl}:</b> {current_time}<br><b>{file_lbl}:</b> {target_filename}</p>
                            </td>
                            <td width="40%" style="text-align: right;">
                                <h1 style="color: {stamp_color}; font-size: 32pt;">{score_str}</h1>
                                <h2 style="color: {stamp_color}; letter-spacing: 2px;">{stat_str}</h2>
                            </td>
                        </tr>
                    </table>
                
                    <table class="dashboard-table">
                        <tr>
                            <td width="33%" class="dash-box">
                                <div class="box-title">CAT 1: {cat1_name}</div>
                                <div class="box-score">{c1_score:.1f} / 50</div>
                            </td>
                            <td width="33%" class="dash-box">
                                <div class="box-title">CAT 2: {cat2_name}</div>
                                <div class="box-score">{c2_score:.1f} / 35</div>
                            </td>
                            <td width="33%" class="dash-box">
                                <div class="box-title">CAT 3: {cat3_name}</div>
                                <div class="box-score">{c3_score:.1f} / 15</div>
                            </td>
                        </tr>
                    </table>
                
                    <h3 style="margin-bottom: 10px; color: #444;">{viol_title}</h3>
                    <div class="log-section">
                        {html_log}
                    </div>
                </div>
                
                </body>
                </html>
                """
                doc = QTextDocument()
                doc.setHtml(html_template)
                doc.print_(printer)
                
                self.last_saved_pdf_dir = os.path.dirname(os.path.abspath(file_path))
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("nCheck")
                msg_box.setText("PDF başarıyla kaydedildi:\n" + file_path)
                msg_box.setIcon(QMessageBox.Information)
                open_btn = msg_box.addButton("Aç", QMessageBox.ActionRole)
                msg_box.addButton("Tamam", QMessageBox.AcceptRole)
                msg_box.exec_()
                
                if msg_box.clickedButton() == open_btn:
                    if sys.platform == 'win32':
                        os.startfile(file_path)
                    else:
                        os.system(f'xdg-open "{file_path}"')
            except Exception as e:
                QMessageBox.critical(self, "nAudit", f"PDF oluşturma hatası: {str(e)}")

    def open_output_folder(self):
        try:
            folder_to_open = ""
            if hasattr(self, 'last_saved_pdf_dir') and self.last_saved_pdf_dir and os.path.exists(self.last_saved_pdf_dir):
                folder_to_open = self.last_saved_pdf_dir
            elif self.tr_drop_box.file_path:
                folder_to_open = os.path.dirname(self.tr_drop_box.file_path)
            else:
                folder_to_open = os.path.expanduser("~")
                
            if sys.platform == 'win32':
                os.startfile(folder_to_open)
            else:
                os.system(f'xdg-open "{folder_to_open}"')
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
