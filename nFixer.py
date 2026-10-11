import sys
import os
import re
import pysrt

TR_LOWER_MAP = {
    'İ': 'i', 'I': 'ı', 'Ç': 'ç', 'Ğ': 'ğ', 'Ö': 'ö', 'Ş': 'ş', 'Ü': 'ü'
}

class nFixer:
    def __init__(self, file_path=None, subs=None):
        """
        Hem bağımsız test için dosya yolundan okumayı, 
        hem de nCheck'in içindeyken doğrudan pysrt objesi almayı destekler.
        """
        if subs:
            self.subs = subs
        elif file_path:
            # Bağımsız betik olarak çalışırken UTF-8 ve Windows-1254 desteği
            try:
                self.subs = pysrt.open(file_path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                try:
                    self.subs = pysrt.open(file_path, encoding='windows-1254')
                except Exception:
                    self.subs = pysrt.open(file_path, encoding='latin-1')
        else:
            raise ValueError("Bana ya dosya yolu ya da pysrt objesi vermelisin.")

    def apply_typography_fixes(self):
        """
        FAZ 1: Tipografik ve Metinsel Hijyen
        Satır sürelerine veya ekran yerleşimine bakılmaksızın metnin çamaşır suyuna basıldığı yer.
        """
        for sub in self.subs:
            text = sub.text
            
            # --- VİRGÜL TEMİZLİĞİ (SE - FixCommas Mantığı) ---
            if ',' in text:
                # 1. Kural: Yan yana 3 virgülü (arada boşluk olsa da) 3 noktaya çevir
                text = re.sub(r', *, *,', '...', text)
                
                # 2. Kural: Art arda gelen veya arasına boşluk sızmış virgülleri teke düşür
                text = re.sub(r',\s*,+', ',', text)
                
                # 3. Kural: Cümle bitirme işaretlerinden (.,!?) hemen önce kalmış virgülleri sil
                text = re.sub(r',\s*([\.!\?\]\)])', r'\1', text)
                
                # 4. Kural: Virgülden sonra doğrudan harf geliyorsa (sayı değil), araya boşluk ekle
                # Python'da [^\W\d_] ifadesi tüm dillerdeki harfleri kapsar (Türkçe dahil)
                text = re.sub(r',([^\W\d_])', r', \1', text)
            # --- İTALİK ETİKET (TAG) TEMİZLİĞİ (SE Mantığı) ---
            if '<' in text and '>' in text:
                # 1. Kural: Çift Etiketleri Teke Düşür (yan yana veya aralıklı tekrarları teke indir)
                text = re.sub(r'(?:<[iI]>\s*)+<[iI]>', '<i>', text)
                text = re.sub(r'(?:</[iI]>\s*)+</[iI]>', '</i>', text)

                # 2. Kural: Boş Etiketleri Yok Et (içinde hiçbir metin barındırmayan veya sadece boşluk olanları sil)
                text = re.sub(r'<[iI]>\s*</[iI]>', '', text)

                # 3. Kural: Nefes Boşluklarını Dışarı At (etiketlerin hemen içine yazılmış boşlukları dışarı taşı)
                # <i> sonrasındaki boşluğu dışarı taşı (önünde boşluk yoksa önüne boşluk koy, varsa içindekini sil)
                text = re.sub(r'(?<!\s)<[iI]>\s+', ' <i>', text)
                text = re.sub(r'<[iI]>\s+', '<i>', text)
                # </i> öncesindeki boşluğu dışarı taşı (arkasında boşluk veya noktalama yoksa arkasına boşluk koy)
                text = re.sub(r'\s+</[iI]>(?!\s|[.,!?:;])', '</i> ', text)
                text = re.sub(r'\s+</[iI]>', '</i>', text)

                # Boşluk kaydırma sonrası kalabilecek olası boş etiketleri temizle
                text = re.sub(r'<[iI]>\s*</[iI]>', '', text)

                # 4. Kural: Kayıp Etiketleri Tamamla (metindeki <i> ve </i> sayılarını say ve dengele)
                open_count = len(re.findall(r'<[iI]>', text))
                close_count = len(re.findall(r'</[iI]>', text))

                if open_count > close_count:
                    # <i> açılmış ama kapanmamışsa, bloğun en sonuna </i> ekle
                    text = text + ('</i>' * (open_count - close_count))
                elif close_count > open_count:
                    # Hiç açılmadan kapatılan </i> varsa, bloğun en başına <i> koy
                    text = ('<i>' * (close_count - open_count)) + text
            # --- SEMBOL VE İŞARET TEMİZLİĞİ ---
            # 1. Çift Tırnak Düzeltmesi: Yan yana yazılmış iki tek tırnağı ('') standart çift tırnağa (") çevir
            if "''" in text:
                text = text.replace("''", '"')

            # 2. Gereksiz Büyüktür İşareti: SDH kalıntısı >> işaretlerini ve hemen peşinden gelen boşlukları sil
            if '>>' in text:
                text = re.sub(r'>>\s*', '', text)

            # 3. Müzik Sembolü Standardizasyonu: Farklı müzik sembollerini tek nota sembolüyle (♪) değiştir
            text = re.sub(r'[♫♬🎶🎵]', '♪', text)

            # 4. Çift Tire (Double Dash) Temizliği: Kesinti bildiren -- işaretini üç nokta (...) ile değiştir
            text = re.sub(r'(?<=[^\s\-])\s*--+(?=\s+|$|\n|[.,!?:;"\']|</?[iI]>)', '...', text)

            # 5. Bozuk Noktalar: 4+ noktayı (...) ve 2 noktayı (..) standart üç noktaya (...) çevir
            text = re.sub(r'\.{4,}', '...', text)
            text = re.sub(r'(?<!\.)\.\.(?!\.)', '...', text)

            # --- BOŞLUK VE OCR TEMİZLİĞİ ---
            # 1. Kelime İçi Büyük Harf (OCR Hatası): "yuvArlak", "gideCek" gibi tekil büyük harfleri küçült
            def fix_inner_caps(m):
                word = m.group(0)
                # İstisnaları koru (iPhone, iPad, eBay, MacDonald, McDonald vb.)
                if re.match(r'^(?:[ie][A-Z]|Mac[A-Z]|Mc[A-Z])', word):
                    return word
                return re.sub(
                    r'(?<=[a-zçğıöşü])([A-ZÇĞİÖŞÜ])(?=[a-zçğıöşü])',
                    lambda c: TR_LOWER_MAP.get(c.group(1), c.group(1).lower()),
                    word
                )
            text = re.sub(r'[a-zA-ZçÇğĞıİöÖşŞüÜ]+', fix_inner_caps, text)

            # 2. Görünmez Düşmanlar: Tab (\t) ve Non-breaking space (\u00A0) karakterlerini standart tek boşluğa çevir
            if '\t' in text or '\u00A0' in text:
                text = text.replace('\t', ' ').replace('\u00A0', ' ')

            # 3. Sayılar Arası Boşluk: OCR kaynaklı rakamlar arası boşlukları ("1 500" -> "1500") sil
            text = re.sub(r'(?<=\d)\s+(?=\d)', '', text)

            # 4. Fazla Boşluklar: Yan yana gelmiş 2 veya daha fazla boşluğu tek boşluğa indir
            text = re.sub(r' +', ' ', text)

            # 5. Satır Kenarları: Her satırın başındaki ve sonundaki boşlukları kırp (trim)
            text = re.sub(r'^ +| +$', '', text, flags=re.MULTILINE)

            sub.text = text

            # Gereksiz Başlangıç Tiresi Temizliği (Tek satırlık/diyalog olmayan metindeki tireyi sil)
            if not '\n' in sub.text and sub.text.startswith('-') and not re.search(r'\s+[-–]\s+', sub.text):
                sub.text = re.sub(r'^-\s*', '', sub.text)

        # Tamamen boşalan blokları listeden uçur
        self.subs = pysrt.SubRipFile([s for s in self.subs if s.text.strip()])

    def apply_structural_fixes(self, cpl_limit=42, pyramid_max_diff=12):
        """
        FAZ 2: Yapısal Dengeleme ve Mekânsal Tamir
        Metin temizlendikten sonra CPL sınırları, piramit dengesi, diyalog düzenlemeleri
        ve satır bölme/birleştirme işlemleri.
        """
        for sub in self.subs:
            text = sub.text.strip()
            if not text:
                continue

            # --- ÖN YAPILANDIRMA (Boşluk ve Diyalog Kontrolü) ---
            # 1. Fazladan \n veya tamamen boş satırları temizle
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if not lines:
                continue

            # 2. Tek satırda iki ayrı diyalog çizgisi varsa böl (örn: "- Nasılsın? - İyiyim.")
            new_lines = []
            for line in lines:
                clean_l = re.sub(r'<[^>]+>', '', line).strip()
                if (clean_l.startswith('-') or clean_l.startswith('–')) and re.search(r'\s+[-–]\s+', line):
                    parts = re.split(r'\s+[-–]\s+', line, maxsplit=1)
                    if len(parts) == 2:
                        p1 = parts[0].strip()
                        p2 = parts[1].strip()
                        if not (p2.startswith('-') or p2.startswith('–')):
                            p2 = f"- {p2}"
                        new_lines.extend([p1, p2])
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            lines = new_lines
            text = '\n'.join(lines)
            sub.text = text

            clean_lines = [re.sub(r'<[^>]+>', '', l).strip() for l in lines]
            is_dialogue = any(l.startswith('-') or l.startswith('–') for l in clean_lines)

            # --- İHLAL KONTROLÜ ---
            # Kural A (3+ Satır): Blokta 3 veya daha fazla satır var mı?
            rule_a = len(lines) >= 3

            # Kural B (CPL Aşımı): Satırlardan herhangi birinin uzunluğu 42 karakteri geçiyor mu?
            rule_b = any(len(l) > cpl_limit for l in clean_lines)

            # Kural C (Piramit İhlali): Blok tam 2 satırsa, fark 12'den büyük mü? (Diyaloglarda yoksay)
            rule_c = (len(lines) == 2 and not is_dialogue and abs(len(clean_lines[0]) - len(clean_lines[1])) > pyramid_max_diff)

            # Kural D (Gereksiz Bölünme): Blok 2 satırsa, diyalog değilse ve toplam karakter sayısı < 35 ise
            rule_d = (len(lines) == 2 and not is_dialogue and sum(len(l) for l in clean_lines) < 35)

            # --- DÜZELTME MANTIĞI (Yeniden Formatlama) ---
            # Diyalog olmayan ve A, B, C veya D ihlali olan blokları tek satıra indirip yeniden biçimlendir
            if (rule_a or rule_b or rule_c or rule_d) and not is_dialogue:
                single_line = text.replace('\n', ' ')
                single_line = re.sub(r' +', ' ', single_line).strip()

                clean_single = re.sub(r'<[^>]+>', '', single_line).strip()

                # İSTİSNA: Elde edilen tek satır CPL limitinden (42) kısaysa tek satır bırak (Kural D çözümü)
                if len(clean_single) <= cpl_limit:
                    sub.text = single_line
                    continue

                # Tek satır 42 karakterden uzunsa orta noktayı bul
                n = len(single_line)
                mid = n // 2

                # Ortadan sağa ve sola ilerleyerek en yakın boşluğu tespit et
                best_space_idx = -1
                for offset in range(n):
                    left = mid - offset
                    if 0 <= left < n and single_line[left] == ' ':
                        best_space_idx = left
                        break
                    right = mid + offset
                    if 0 <= right < n and single_line[right] == ' ':
                        best_space_idx = right
                        break

                # En yakın boşluktan ikiye böl ve \n ekle
                if best_space_idx != -1:
                    line1 = single_line[:best_space_idx].rstrip()
                    line2 = single_line[best_space_idx + 1:].lstrip()
                    sub.text = f"{line1}\n{line2}"
                else:
                    sub.text = single_line

    def apply_timing_fixes(self):
        """
        FAZ 3: Zamanlama ve Akış
        Metin ve yapı oturduktan sonra, Gap (84ms) koruması ve Koşullu Esneme (CPS düşürme) işlemleri.
        Dikkat: Bu faz, önceki fazların sonuçlarına bağlı olduğu için DAİMA en son çalıştırılmalı.
        """
        for i in range(len(self.subs)):
            current_sub = self.subs[i]
            next_sub = self.subs[i+1] if i + 1 < len(self.subs) else None

            # 1. GAP (Flicker) Koruması
            if next_sub:
                gap_ms = next_sub.start.ordinal - current_sub.end.ordinal
                if 0 <= gap_ms < 84:
                    new_end = next_sub.start.ordinal - 84
                    if new_end > current_sub.start.ordinal:
                        current_sub.end.ordinal = new_end

            # 2. Akıllı CPS Tamiri (Koşullu Esneme)
            char_count = len(current_sub.text_without_tags)
            dur_sec = (current_sub.end.ordinal - current_sub.start.ordinal) / 1000.0

            if dur_sec > 0:
                current_cps = char_count / dur_sec
                if current_cps > 19.5:
                    ideal_duration_ms = int((char_count / 19.5) * 1000)

                    if next_sub:
                        max_usable_duration_ms = (next_sub.start.ordinal - current_sub.start.ordinal) - 84
                    else:
                        max_usable_duration_ms = ideal_duration_ms

                    if max_usable_duration_ms > (current_sub.end.ordinal - current_sub.start.ordinal):
                        final_duration_ms = min(ideal_duration_ms, max_usable_duration_ms)
                        final_duration_ms = min(final_duration_ms, 7000)  # Max 7 saniye sınırı
                        current_sub.end.ordinal = current_sub.start.ordinal + final_duration_ms

    def run_all(self):
        """Tüm fazları sırasıyla çalıştırır."""
        self.apply_typography_fixes()
        self.apply_structural_fixes()
        self.apply_timing_fixes()
        return self.subs


if __name__ == "__main__":
    # Windows konsolunda Türkçe karakterlerin düzgün görünmesi için
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 65)
    print("           nFixer - Bağımsız Altyazı Onarım Modülü")
    print("=" * 65)

    # Sürükle-bırak veya komut satırı argümanlarını al
    target_files = []
    if len(sys.argv) > 1:
        target_files = sys.argv[1:]
    else:
        # Doğrudan çift tıklandıysa veya argüman verilmediyse konsoldan girdi al
        user_input = input("\nLütfen .srt dosyasını buraya sürükleyip bırakın ve Enter'a basın:\n> ").strip()
        user_input = user_input.strip('"').strip("'")
        if user_input and os.path.isfile(user_input):
            target_files = [user_input]

    if not target_files:
        print("\n[!] İşlenecek dosya bulunamadı veya geçersiz dosya yolu.")
        input("\nÇıkmak için Enter'a basın...")
        sys.exit(0)

    for file_path in target_files:
        file_path = file_path.strip('"').strip("'")
        if not os.path.isfile(file_path):
            print(f"\n[!] Dosya bulunamadı: {file_path}")
            continue

        base_name, ext = os.path.splitext(file_path)
        if ext.lower() not in [".srt"]:
            print(f"\n[!] Dikkat: '{os.path.basename(file_path)}' bir .srt dosyası değil. Yine de işlem deneniyor...")

        output_path = f"{base_name}_fixed{ext}"

        print(f"\n[+] İşleniyor: {os.path.basename(file_path)}")
        try:
            fixer = nFixer(file_path=file_path)
            total_before = len(fixer.subs)
            print(f"    - Başlangıç blok sayısı : {total_before}")

            print("    - Faz 1: Tipografik & Metinsel Hijyen uygulanıyor...")
            fixer.apply_typography_fixes()

            print("    - Faz 2: Yapısal Dengeleme & Mekânsal Tamir uygulanıyor...")
            fixer.apply_structural_fixes()

            print("    - Faz 3: Zamanlama & Akış (Koşullu Esneme & Gap) uygulanıyor...")
            fixer.apply_timing_fixes()

            total_after = len(fixer.subs)
            print(f"    - Kalan blok sayısı     : {total_after} (Silinen boş blok: {total_before - total_after})")

            # Onarılmış altyazıyı UTF-8 olarak kaydet
            fixer.subs.save(output_path, encoding='utf-8')
            print(f"\n[✔] BAŞARILI! Onarılmış altyazı kaydedildi:")
            print(f"    -> {output_path}")

        except Exception as e:
            print(f"\n[✖] Onarım sırasında hata oluştu ({os.path.basename(file_path)}): {e}")

    print("\n" + "=" * 65)
    input("Tüm işlemler tamamlandı. Çıkmak için Enter'a basın...")