import sys
import os
import re
import math
import pysrt

TR_LOWER_MAP = {
    'İ': 'i', 'I': 'ı', 'Ç': 'ç', 'Ğ': 'ğ', 'Ö': 'ö', 'Ş': 'ş', 'Ü': 'ü'
}

TR_UPPER_MAP = {
    'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'
}

CONJUNCTIONS_BEFORE = {
    'çünkü', 'ama', 'fakat', 'lakin', 've', 'veya', 'ya da', 'eğer', 
    'oysa', 'halbuki', 'oysaki', 'zira', 'yoksa', 'nitekim', 'meğer', 
    'meğerse', 'madem', 'mademki'
}

PROTECTED_PARTICLES = {
    'için', 'gibi', 'kadar', 'rağmen', 'göre', 'doğru', 'karşı', 'ötürü', 
    'beri', 'adına', 'mı', 'mi', 'mu', 'mü', 'mısın', 'misin', 'musun', 
    'müsün', 'mıyız', 'miyiz', 'musunuz', 'müsünüz'
}

def get_clean_line(l):
    return re.sub(r'<[^>]+>', '', l).strip()

def starts_with_dash(l):
    clean = get_clean_line(l)
    return clean.startswith('-') or clean.startswith('–')

def ensure_dash_prefix(l):
    l = l.strip()
    clean = get_clean_line(l)
    if clean.startswith('-') or clean.startswith('–'):
        m = re.match(r'^((?:<[^>]+>\s*)*)[-–]\s*(.*)$', l)
        if m:
            return f"{m.group(1)}- {m.group(2)}"
        return l
    else:
        m = re.match(r'^((?:<[^>]+>\s*)*)(.*)$', l)
        if m and m.group(1):
            return f"{m.group(1)}- {m.group(2)}"
        return f"- {l}"

def remove_dash_prefix(l):
    l = l.strip()
    m = re.match(r'^((?:<[^>]+>\s*)*)[-–]\s*(.*)$', l)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return l

def is_sentence_end(text):
    clean = get_clean_line(text).rstrip()
    if not clean:
        return False
    return clean[-1] in '.?!…:;"\''

def starts_with_uppercase(text):
    clean = get_clean_line(text).lstrip()
    if not clean:
        return False
    first_char = clean[0]
    return first_char.isupper() or first_char in 'ÇĞİÖŞÜ' or first_char in '0123456789"\'“‘«'

def balance_html_tags(l1, l2):
    """İki satır arasındaki açık/kapalı HTML etiketlerini (i, b, u) dengeler."""
    for tag in ['i', 'b', 'u']:
        open_t = f'<{tag}>'
        close_t = f'</{tag}>'
        
        # l1 kontrolü: Açılmış ama kapanmamış etiket var mı?
        diff1 = l1.count(open_t) - l1.count(close_t)
        if diff1 > 0:
            l1 = l1 + (close_t * diff1)
            l2 = (open_t * diff1) + l2
        elif diff1 < 0:
            l1 = (open_t * abs(diff1)) + l1

        # l2 kontrolü: Açılmadan kapatılmış etiket var mı?
        diff2 = l2.count(open_t) - l2.count(close_t)
        if diff2 < 0:
            l2 = (open_t * abs(diff2)) + l2
        elif diff2 > 0:
            l2 = l2 + (close_t * diff2)

    return l1, l2

def split_line_smart(single_line, cpl_limit=42):
    """
    Tek bir metni CPL ve HTML etiketlerini gözeterek en dengeli noktadan ikiye böler.
    HTML etiketlerinin açık/kapalı dengesini korur ve yayın standartlarına uygun hale getirir.
    """
    single_line = re.sub(r' +', ' ', single_line.replace('\n', ' ')).strip()
    clean_single = re.sub(r'<[^>]+>', '', single_line).strip()

    if len(clean_single) <= cpl_limit:
        return single_line

    # 1. Durum: Tüm blok baştan sona tek bir etiketle sarılı mı? (örn: <i>...</i>)
    m = re.match(r'^(<([a-zA-Z]+)[^>]*>)(.*)(</\2>)$', single_line, flags=re.DOTALL)
    if m:
        open_tag = m.group(1)
        tag_name = m.group(2).lower()
        inner_content = m.group(3).strip()
        close_tag = m.group(4)
        
        # Eğer inner_content içinde aynı etiketin kapanışı yoksa tam bir dış sarmaldır
        if f'</{tag_name}>' not in inner_content:
            split_inner = split_line_smart(inner_content, cpl_limit)
            if '\n' in split_inner:
                parts = split_inner.split('\n', 1)
                return f"{open_tag}{parts[0].strip()}{close_tag}\n{open_tag}{parts[1].strip()}{close_tag}"

    # 2. Durum: Genel metin bölme (Ağırlıklı Linguistik ve Geometrik Puanlama Motoru)
    tag_spans = [match.span() for match in re.finditer(r'<[^>]+>', single_line)]
    
    def is_inside_tag(pos):
        return any(start <= pos < end for start, end in tag_spans)

    scored_candidates = []
    for i, ch in enumerate(single_line):
        if ch == ' ' and not is_inside_tag(i):
            p1 = single_line[:i].rstrip()
            p2 = single_line[i+1:].lstrip()
            c1 = len(re.sub(r'<[^>]+>', '', p1))
            c2 = len(re.sub(r'<[^>]+>', '', p2))
            diff = abs(c1 - c2)
            max_c = max(c1, c2)

            score = 0.0

            # 1. CPL Güvenliği (Kırmızı Çizgi)
            if max_c > cpl_limit:
                score -= (max_c - cpl_limit) * 100.0

            # 2. Geometrik Denge (Piramit ve Merkez Yakınlığı)
            if diff <= 12:
                score += 15.0
            score -= diff * 0.8

            # 3. Noktalama Mıknatısı (Boşluğun solundaki karaktere bakar)
            p1_clean = re.sub(r'<[^>]+>', '', p1).rstrip()
            if p1_clean:
                last_char = p1_clean[-1]
                if last_char in '.?!…':
                    score += 80.0
                elif last_char in ',;:':
                    score += 70.0
                elif last_char in '"\'”»' and len(p1_clean) > 1 and p1_clean[-2] in '.?!…,:;':
                    score += 70.0

            # 4. Kelime Bazlı Linguistik Analiz (Bağlaçlar ve Edatlar)
            # a) Boşluğun solundaki son kelime
            p1_words = p1_clean.lower().split()
            if p1_words:
                last_word = re.sub(r'[^\wçğıöşü]', '', p1_words[-1])
                # Bağlacı üst satırın sonunda tek başına bırakma cezası
                if last_word in CONJUNCTIONS_BEFORE:
                    score -= 50.0

            # b) Boşluğun sağındaki ilk kelime
            p2_clean = re.sub(r'<[^>]+>', '', p2).lstrip()
            p2_words = p2_clean.lower().split()
            if p2_words:
                first_word = re.sub(r'[^\wçğıöşü]', '', p2_words[0])
                # Bağlaç öncesinden kırma bonusu (+50)
                if first_word in CONJUNCTIONS_BEFORE:
                    score += 50.0
                # Edat / İlgeç / Soru eki öncesinden bölmeme koruması (-50)
                if first_word in PROTECTED_PARTICLES:
                    score -= 50.0

            scored_candidates.append((score, -diff, i))

    if not scored_candidates:
        return single_line

    # En yüksek skora sahip boşluğu seç (skor eşitliğinde diff daha küçük olan)
    scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_idx = scored_candidates[0][2]

    line1 = single_line[:best_idx].rstrip()
    line2 = single_line[best_idx + 1:].lstrip()

    # Etiket dengelemeyi uygula
    line1, line2 = balance_html_tags(line1, line2)
    return f"{line1}\n{line2}"

def reduce_multiline_dialogue(lines):
    """
    3 veya daha fazla satırlı diyalog bloklarını, konuşmacı hiyerarşisini
    ve tireleri koruyarak tam 2 satıra indirir.
    """
    while len(lines) > 2:
        # Öncelik 1: Tiresiz devam satırı var mı? (Satır i tireli, satır i+1 tiresiz ise aynı konuşmacıdır)
        merged = False
        for i in range(len(lines) - 1):
            if starts_with_dash(lines[i]) and not starts_with_dash(lines[i+1]):
                lines[i] = lines[i].strip() + ' ' + lines[i+1].strip()
                lines.pop(i+1)
                merged = True
                break
        if merged:
            continue

        # Öncelik 2: Eğer tüm satırlar tireli ise en kısa komşu iki satırı birleştir
        best_pair = 0
        min_len = float('inf')
        for i in range(len(lines) - 1):
            comb_len = len(get_clean_line(lines[i])) + len(get_clean_line(lines[i+1]))
            if comb_len < min_len:
                min_len = comb_len
                best_pair = i
        
        lines[best_pair] = lines[best_pair].strip() + ' ' + lines[best_pair+1].strip()
        lines.pop(best_pair+1)

    return lines

CONJUNCTIONS = ['ve', 'veya', 'ya da', 'ama', 'fakat', 'lakin', 'çünkü', 'oysa', 'oysaki', 'halbuki']

def find_optimal_split_point(text):
    """
    Uzun bir metni ritmik ve linguistik olarak iki ayrı altyazı bloğuna bölmek için
    en uygun boşluk indeksini bulur.
    Öncelik 1: %30-%70 bandındaki cümle bitişleri (. ? ! ...)
    Öncelik 2: %30-%70 bandındaki bağlaçlar (ve, veya, ama vb.) veya virgül (,)
    Öncelik 3: 50/50 ortalamaya en yakın boşluk
    """
    clean_text = get_clean_line(text)
    total_len = len(clean_text)
    if total_len < 20:
        return -1

    tag_spans = [m.span() for m in re.finditer(r'<[^>]+>', text)]
    def is_inside_tag(pos):
        return any(start <= pos < end for start, end in tag_spans)

    spaces = [i for i, ch in enumerate(text) if ch == ' ' and not is_inside_tag(i)]
    if not spaces:
        return -1

    # İdeal bölme penceresi: Metnin %30'u ile %70'i arası
    min_bound = int(total_len * 0.30)
    max_bound = int(total_len * 0.70)

    scored_spaces = []
    for sp in spaces:
        p1_clean = len(get_clean_line(text[:sp]))
        p2_clean = len(get_clean_line(text[sp+1:]))
        diff = abs(p1_clean - p2_clean)
        in_window = (min_bound <= p1_clean <= max_bound)

        preceding = text[:sp].rstrip()
        is_p1 = False
        if preceding and preceding[-1] in '.?!…':
            is_p1 = True

        is_p2 = False
        if preceding and preceding[-1] == ',':
            is_p2 = True
        else:
            following_words = text[sp+1:].lstrip().lower().split()
            if following_words:
                first_w = re.sub(r'[^\wçğıöşü]', '', following_words[0])
                if first_w in CONJUNCTIONS:
                    is_p2 = True

        priority = 3
        if is_p1 and in_window:
            priority = 1
        elif is_p2 and in_window:
            priority = 2

        scored_spaces.append((priority, 0 if in_window else 1, diff, sp))

    scored_spaces.sort(key=lambda x: (x[0], x[1], x[2]))
    return scored_spaces[0][3]


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

            # --- NOKTALAMA BOŞLUKLARI VE BÜYÜK HARF RESTORASYONU ---
            # 1. Noktalama sonrası eksik boşluk ekleme (?, !, .)
            text = re.sub(r'([\?!])([a-zA-ZçÇğĞıİöÖşŞüÜ])', r'\1 \2', text)
            text = re.sub(r'(?<!\.)\.(?!\.)([a-zA-ZçÇğĞıİöÖşŞüÜ])', r'. \1', text)

            # 2. Satır başındaki üç noktaları kaldırma (SE standardı: Remove leading '...')
            lines_clean = []
            for l in text.split('\n'):
                cleaned_l = re.sub(r'^((?:<[^>]+>\s*)*(?:[-–]\s*)?)\.{3,}\s*', r'\1', l)
                lines_clean.append(cleaned_l)
            text = '\n'.join(lines_clean)

            # 3. Cümle bitişlerinden sonra büyük harfle başlama
            def to_tr_upper(m):
                punct_and_space = m.group(1)
                ch = m.group(2)
                return punct_and_space + TR_UPPER_MAP.get(ch, ch.upper())

            text = re.sub(r'([\?!][\s"\'”»]+)([a-zçğıöşü])', to_tr_upper, text)
            text = re.sub(r'((?<!\.)\.(?!\.)[\s"\'”»]+)([a-zçğıöşü])', to_tr_upper, text)

            # Son trim
            text = re.sub(r'^ +| +$', '', text, flags=re.MULTILINE)

            sub.text = text

        # Tamamen boşalan blokları listeden uçur
        self.subs = pysrt.SubRipFile([s for s in self.subs if s.text.strip()])

    def split_oversized_subtitles(self, min_chars=80, min_duration_ms=2400):
        """
        80+ karakter ve en az 2400ms süreye sahip aşırı uzun altyazı bloklarını,
        ritmik ve linguistik kurallara göre iki ayrı zaman kodlu bloğa böler.
        İki kardeş blok arasına tam 84ms güvenlik boşluğu yerleştirir.
        """
        new_subs = pysrt.SubRipFile()
        
        for sub in self.subs:
            text = sub.text.strip()
            clean_text = get_clean_line(text)
            duration_ms = sub.end.ordinal - sub.start.ordinal
            
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            is_dialogue = any(starts_with_dash(l) for l in lines)

            # Bölme şartları:
            # 1. Metin çok uzun olmalı (>= 80 karakter)
            # 2. Süre ikiye bölünmeye yetecek kadar uzun olmalı (>= 2400ms)
            # 3. İki satırlı diyalog olmamalı (diyaloglar ayrı konuşmacılardır)
            if len(clean_text) >= min_chars and duration_ms >= min_duration_ms and not is_dialogue:
                split_idx = find_optimal_split_point(text)
                if split_idx != -1:
                    part1 = text[:split_idx].strip()
                    part2 = text[split_idx+1:].strip()

                    # Açık kalan HTML etiketlerini her iki parçada dengele
                    part1, part2 = balance_html_tags(part1, part2)

                    usable_duration_ms = duration_ms - 84
                    len1 = len(get_clean_line(part1))
                    len2 = len(get_clean_line(part2))
                    total_len = max(1, len1 + len2)

                    d1 = int((len1 / total_len) * usable_duration_ms)
                    d2 = usable_duration_ms - d1

                    start_ms = sub.start.ordinal
                    end_ms = sub.end.ordinal

                    # 1. Parça
                    sub1 = pysrt.SubRipItem(
                        start=pysrt.SubRipTime.from_ordinal(start_ms),
                        end=pysrt.SubRipTime.from_ordinal(start_ms + d1),
                        text=part1
                    )
                    new_subs.append(sub1)

                    # 2. Parça (84ms güvenlik tamponu sonrası başlar)
                    sub2 = pysrt.SubRipItem(
                        start=pysrt.SubRipTime.from_ordinal(start_ms + d1 + 84),
                        end=pysrt.SubRipTime.from_ordinal(end_ms),
                        text=part2
                    )
                    new_subs.append(sub2)
                    continue

            new_subs.append(sub)

        # İndeksleri baştan sona temizle ve numaralandır
        new_subs.clean_indexes()
        self.subs = new_subs

    def apply_structural_fixes(self, cpl_limit=42, pyramid_max_diff=12):
        """
        FAZ 2: Yapısal Dengeleme ve Mekânsal Tamir
        Öncelikle aşırı uzun (80+ karakter) blokları zaman bazlı olarak ikiye böler.
        Ardından CPL sınırları, piramit dengesi, diyalog düzenlemeleri
        ve satır bölme/birleştirme işlemlerini uygular.
        """
        # Adım 0: Aşırı uzun blokları zaman bazlı olarak ikiye böl
        self.split_oversized_subtitles()

        split_pat = re.compile(r'(?:(?<=[\.\?!…])\s+[-–]\s+|\s+[-–]\s+(?=[A-ZÇĞİÖŞÜ0-9"\'“‘«]))')

        for sub in self.subs:
            text = sub.text.strip()
            if not text:
                continue

            # --- ÖN YAPILANDIRMA (Boşluk ve Diyalog Kontrolü) ---
            # 1. Fazladan \n veya tamamen boş satırları temizle
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if not lines:
                continue

            # 2. Akıllı Diyalog ve Yetim Tire Motoru
            # Kural C: Tek satırda gizli diyalog varsa satırları böl ve tireleri ekle
            new_lines = []
            for line in lines:
                clean_l = get_clean_line(line)
                if split_pat.search(line):
                    parts = split_pat.split(line, maxsplit=1)
                    if len(parts) == 2:
                        new_lines.append(ensure_dash_prefix(parts[0]))
                        new_lines.append(ensure_dash_prefix(parts[1]))
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            lines = new_lines

            # Kural A, B ve D: Blok satır sayısına göre diyalog ve tire restorasyonu
            if len(lines) == 1:
                # Kural D: Tek satırda kalan gerçek yetim tire: İnfaz / Sil
                if starts_with_dash(lines[0]):
                    lines[0] = remove_dash_prefix(lines[0])

            elif len(lines) == 2:
                dash1 = starts_with_dash(lines[0])
                dash2 = starts_with_dash(lines[1])

                if dash1 and dash2:
                    # İkisi de tireli: Biçimlerini standart "- " yap
                    lines[0] = ensure_dash_prefix(lines[0])
                    lines[1] = ensure_dash_prefix(lines[1])

                elif not dash1 and dash2:
                    # Kural A: Altta tire var, üstte yok -> Kesin diyalog, üste de tire ekle
                    lines[0] = ensure_dash_prefix(lines[0])
                    lines[1] = ensure_dash_prefix(lines[1])

                elif dash1 and not dash2:
                    # Kural B: Üstte tire var, altta yok
                    # Eğer üstteki satır cümle sonu ile bitiyorsa VEYA alttaki satır büyük harfle başlıyorsa -> Diyalogdur
                    if is_sentence_end(lines[0]) or starts_with_uppercase(lines[1]):
                        lines[0] = ensure_dash_prefix(lines[0])
                        lines[1] = ensure_dash_prefix(lines[1])
                    else:
                        # Cümle devamı (küçük harfle devam ediyor): Tek kişinin cümlesidir, üstteki sahte tireyi sil
                        lines[0] = remove_dash_prefix(lines[0])

            text = '\n'.join(lines)
            sub.text = text

            clean_lines = [get_clean_line(l) for l in lines]
            is_dialogue = any(starts_with_dash(l) for l in clean_lines)

            # 3 veya daha fazla satırlı diyalogları konuşmacı yapısını koruyarak 2 satıra indir (Kat 0 İnfaz Önleyici)
            if len(lines) >= 3 and is_dialogue:
                lines = reduce_multiline_dialogue(lines)
                text = '\n'.join(lines)
                sub.text = text
                clean_lines = [get_clean_line(l) for l in lines]
                is_dialogue = any(starts_with_dash(l) for l in clean_lines)

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

                # Akıllı etiket korumalı bölücü (CPL, piramit ve açık/kapalı HTML tag dengesi)
                sub.text = split_line_smart(single_line, cpl_limit=cpl_limit)
            else:
                # İki satırlı mevcut bloklarda açık/kapalı etiket dengesini kontrol et ve düzelt
                cur_lines = sub.text.split('\n')
                if len(cur_lines) == 2:
                    l1, l2 = balance_html_tags(cur_lines[0], cur_lines[1])
                    sub.text = f"{l1}\n{l2}"

    def apply_timing_fixes(self):
        """
        FAZ 3: Zamanlama ve Akış
        Metin ve yapı oturduktan sonra, Zombi (7000ms) budaması, Gap ve Çakışma (<84ms) onarımı,
        Flaş Altyazı (min 833ms) onarımı ve Akıllı CPS Tamiri işlemleri.
        Dikkat: Bu faz, önceki fazların sonuçlarına bağlı olduğu için DAİMA en son çalıştırılmalı.
        """
        for i in range(len(self.subs)):
            current_sub = self.subs[i]
            next_sub = self.subs[i+1] if i + 1 < len(self.subs) else None

            # 1. Zombi Avcısı (Maksimum 7000ms / 7 Saniye Budaması)
            current_duration_ms = current_sub.end.ordinal - current_sub.start.ordinal
            if current_duration_ms > 7000:
                current_sub.end.ordinal = current_sub.start.ordinal + 7000

            # 2. GAP ve Çakışma (Overlapping) Koruması (< 84ms)
            if next_sub:
                gap_ms = next_sub.start.ordinal - current_sub.end.ordinal
                if gap_ms < 84:
                    new_end = next_sub.start.ordinal - 84
                    # Zamansal paradoksu önle: Bitiş, başlangıcın en az 200ms ilerisinde kalmalı
                    if new_end >= current_sub.start.ordinal + 200:
                        current_sub.end.ordinal = new_end
                    elif next_sub.start.ordinal > current_sub.start.ordinal:
                        # Çok aşırı çakışma durumunda en azından next_sub.start'a kadar çek
                        current_sub.end.ordinal = next_sub.start.ordinal

            # 3. Flaş Altyazı (Kısa Süre < 833ms) Onarımı
            current_duration_ms = current_sub.end.ordinal - current_sub.start.ordinal
            if current_duration_ms < 833:
                deficit_ms = 833 - current_duration_ms
                if next_sub:
                    available_gap_ms = next_sub.start.ordinal - current_sub.end.ordinal
                    if available_gap_ms > 84:
                        max_extend_ms = available_gap_ms - 84
                        extend_ms = min(deficit_ms, max_extend_ms)
                        current_sub.end.ordinal += extend_ms
                else:
                    # Dosyanın son altyazısı: Sağında engel olmadığı için eksik sürenin tamamı eklenir (7000ms zombi tavanı aşılmadan)
                    extend_ms = min(deficit_ms, max(0, 7000 - current_duration_ms))
                    if extend_ms > 0:
                        current_sub.end.ordinal += extend_ms

            # 4. Akıllı CPS Tamiri (Güvenli Tamponlu ve 7sn Korumalı Esneme)
            char_count = len(current_sub.text_without_tags.strip())
            current_duration_ms = current_sub.end.ordinal - current_sub.start.ordinal

            if current_duration_ms > 0:
                dur_sec = current_duration_ms / 1000.0
                current_cps = char_count / dur_sec
                if current_cps > 19.5:
                    # CPS'i 19.5 sınırının güvenle altına (19.0 CPS konfor alanına) çekecek hedef süre
                    target_duration_ms = int(math.ceil((char_count / 19.0) * 1000))

                    if next_sub:
                        # 84ms güvenlik tamponu düşüldükten sonra kullanılabilecek maksimum süre
                        max_usable_duration_ms = (next_sub.start.ordinal - current_sub.start.ordinal) - 84
                        if max_usable_duration_ms > current_duration_ms:
                            final_duration_ms = min(target_duration_ms, max_usable_duration_ms)
                            final_duration_ms = min(final_duration_ms, 7000)  # 7 saniye Zombi Altyazı sınırı
                            if final_duration_ms > current_duration_ms:
                                current_sub.end.ordinal = current_sub.start.ordinal + final_duration_ms
                    else:
                        # Dosyanın son altyazısı: 7 saniye zombi sınırını aşmadan CPS'i düşür
                        final_duration_ms = min(target_duration_ms, 7000)
                        if final_duration_ms > current_duration_ms:
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

            print("    - Faz 2: Yapısal Dengeleme & Mekânsal Tamir (Zaman Bazlı Bölme, CPL/Piramit) uygulanıyor...")
            fixer.apply_structural_fixes()

            print("    - Faz 3: Zamanlama & Akış (Zombi Avcısı, Gap/Çakışma, Flaş & Akıllı CPS) uygulanıyor...")
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