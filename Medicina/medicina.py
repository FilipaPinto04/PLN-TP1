import xml.etree.ElementTree as ET
import json
import re
import sys
import os

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

# Páginas do vocabulário principal (o índice do PDF indica página 21 a 546)
VOCAB_PAGE_START = 21
VOCAB_PAGE_END   = 546

# Threshold horizontal para separar coluna esquerda da direita
COLUMN_SPLIT = 320  # left < 320 => coluna esquerda; left >= 320 => coluna direita

# Áreas médicas conhecidas no dicionário
AREAS_KNOWN = {
    "Anatomía", "Anatomía patolóxica", "Bioquímica", "Cirurxía", "Dermatoloxía",
    "Embrioloxía", "Endocrinoloxía", "Epidemioloxía", "Etiopatoxenia",
    "Farmacoloxía", "Fisioloxía", "Genética", "Hematoloxía", "Histoloxía",
    "Inmunoloxía", "Microbioloxía", "Neuroloxía", "Oncoloxía", "Patoloxías",
    "Pediatría", "Psiquiatría", "Radioloxía", "Semioloxía", "Terapéutica",
    "Termos xerais", "Uroloxía", "Xinecobstetricia", "Xinecoloxía",
    "Obstetricia", "Oftalmoloxía", "Ortopedia", "Reumatoloxía", "Traumatoloxía",
    "Medicina legal", "Saúde pública", "Xenética"
}

# ---------------------------------------------------------------------------
# Expressões regulareswvgrvw<fw<acf
# ---------------------------------------------------------------------------

GENDER_RE   = re.compile(r"\s+(m|f|m\s*/\s*f|f\s*/\s*m)\s*$")
LANG_PREFIX = re.compile(r"^\s*(es|en|pt|la)\s+(.+)$", re.DOTALL)
SIN_RE      = re.compile(r"^\s*SIN\.\-\s*(.+)$")
VAR_RE      = re.compile(r"^\s*VAR\.\-\s*(.+)$")
VID_RE      = re.compile(r"^\s*Vid\.\-\s*(.+)$")
ACR_RE      = re.compile(r"^\s*([A-Z]{2,})\s+Vid\.\-\s*(.+)$")

# ---------------------------------------------------------------------------
# Funções auxiliares de extração do XML
# ---------------------------------------------------------------------------

def get_text(elem):
    """Extrai texto limpo de um elemento XML (ignora tags internas)."""
    return "".join(elem.itertext()).strip()

def parse_page_to_lines(page):
    """
    Lê todos os <text> de uma página e devolve lista de
    (top, coluna, left, conteúdo) ordenada por top e depois left.
    """
    lines = []
    for text_elem in page.findall("text"):
        top     = int(text_elem.get("top"))
        left    = int(text_elem.get("left"))
        content = get_text(text_elem)
        if not content:
            continue
        col = "left" if left < COLUMN_SPLIT else "right"
        lines.append((top, col, left, content))
    lines.sort(key=lambda x: (x[0], x[2]))
    return lines

def merge_close_lines(lines, threshold=5):
    """
    Junta fragmentos de texto na mesma linha (top próximo) e mesma coluna.
    Mantém o left mínimo do grupo.
    """
    merged = []
    for top, col, left, content in lines:
        if merged and abs(top - merged[-1][0]) <= threshold and col == merged[-1][1]:
            prev_top, prev_col, prev_left, prev_content = merged[-1]
            merged[-1] = (prev_top, prev_col, min(prev_left, left), prev_content + " " + content)
        else:
            merged.append((top, col, left, content))
    return merged

def split_columns(merged_lines):
    """Separa as linhas em coluna esquerda e coluna direita."""
    left_col  = [(top, left, txt) for top, col, left, txt in merged_lines if col == "left"]
    right_col = [(top, left, txt) for top, col, left, txt in merged_lines if col == "right"]
    return left_col, right_col

def is_header_or_footer(text):
    """Detecta cabeçalhos ('Vocabulario') e rodapés (número de página sozinho)."""
    t = text.strip()
    if t in ("Vocabulario", "V"):
        return True
    if re.fullmatch(r"\d{1,3}", t):
        return True
    return False

def clean_col(col_lines):
    """Remove cabeçalhos, rodapés e linhas vazias de uma coluna."""
    return [(top, left, txt) for top, left, txt in col_lines
            if txt.strip() and not is_header_or_footer(txt.strip())]

# ---------------------------------------------------------------------------
# Funções auxiliares de parsing de entradas
# ---------------------------------------------------------------------------

def parse_areas(text):
    """Extrai áreas médicas de uma linha (podem estar separadas por espaços)."""
    areas = []
    parts = re.split(r"\s{2,}|\t", text.strip())
    for p in parts:
        if p.strip() in AREAS_KNOWN:
            areas.append(p.strip())
    if not areas:
        for area in AREAS_KNOWN:
            if area in text:
                areas.append(area)
    return list(dict.fromkeys(areas))

def split_values(text):
    """Divide múltiplos valores separados por ';', limpa espaços e artefactos."""
    parts = [v.strip() for v in text.split(";") if v.strip()]
    cleaned = []
    for p in parts:
        p = re.sub(r"\s+\([a-z]+\)$", "", p).strip()  # remove sufixo "(sg)"
        p = re.sub(r"^\([a-z]+\)\s+", "", p).strip()  # remove prefixo "(sg)"
        if p:
            cleaned.append(p)
    return cleaned

# ---------------------------------------------------------------------------
# Parsing de um bloco de entrada
# ---------------------------------------------------------------------------

def parse_entry_block(lines_block):
    """
    Recebe uma lista de strings (linhas de uma entrada numerada)
    e devolve um dicionário com todos os campos extraídos.
    """
    if not lines_block:
        return None

    entry = {
        "id": None,
        "termo_gl": None,
        "genero": None,
        "areas": [],
        "sinonimos_gl": [],
        "variantes_gl": [],
        "traduccions": {"es": [], "en": [], "pt": [], "la": []},
        "remissoes": [],
        "acronimos": []
    }

    # --- Linha principal: número + termo + género ---
    first = lines_block[0].strip()
    m = re.match(r"^(\d+)\s+(.+)$", first)
    if not m:
        return None

    entry["id"] = int(m.group(1))
    rest = m.group(2).strip()

    gm = GENDER_RE.search(rest)
    if gm:
        entry["genero"] = gm.group(1).strip()
        entry["termo_gl"] = rest[:gm.start()].strip()
    else:
        entry["termo_gl"] = rest

    # --- Verifica se o termo continuou na linha seguinte ---
    start_idx = 1
    if len(lines_block) > 1:
        second = lines_block[1].strip()
        if (not LANG_PREFIX.match(second)
                and not re.match(r"^\d+\s+", second)
                and not SIN_RE.match(second)
                and not VAR_RE.match(second)
                and not VID_RE.match(second)
                and not ACR_RE.match(second)
                and not parse_areas(second)
                and entry["genero"] is None):
            combined = entry["termo_gl"] + " " + second
            gm2 = GENDER_RE.search(combined)
            if gm2:
                entry["genero"] = gm2.group(1).strip()
                entry["termo_gl"] = combined[:gm2.start()].strip()
            else:
                entry["termo_gl"] = combined
            start_idx = 2

    # --- Pré-processamento: detecta termos de remissão sem número ---
    # São linhas sem prefixo de língua seguidas imediatamente de "Vid.-"
    cleaned_lines = []
    i = start_idx
    while i < len(lines_block):
        line = lines_block[i].strip()
        if i + 1 < len(lines_block):
            next_line = lines_block[i + 1].strip()
            if (not LANG_PREFIX.match(line)
                    and not re.match(r"^\d+\s+", line)
                    and not SIN_RE.match(line)
                    and not VAR_RE.match(line)
                    and not ACR_RE.match(line)
                    and VID_RE.match(next_line)):
                vid_target = VID_RE.match(next_line).group(1)
                cleaned_lines.append(f"__REMISSAO_TERM__ {line.strip()} -> {vid_target}")
                i += 2
                continue
        cleaned_lines.append(line)
        i += 1

    # --- Parsing linha a linha ---
    current_lang = None

    for line in cleaned_lines:
        line_s = line.strip()
        if not line_s:
            continue

        # Abreviaturas isoladas como "(sg)" — ignorar
        if re.fullmatch(r"\([a-z]+\)", line_s):
            continue

        # Termo de remissão pré-processado
        if line_s.startswith("__REMISSAO_TERM__"):
            entry["remissoes"].append(line_s.replace("__REMISSAO_TERM__ ", ""))
            current_lang = None
            continue

        # Acrónimo com Vid.
        acr_m = ACR_RE.match(line_s)
        if acr_m:
            entry["acronimos"].append({
                "sigla": acr_m.group(1),
                "vid": acr_m.group(2).strip()
            })
            current_lang = None
            continue

        # Remissão simples: "Vid.- termo"
        vid_m = VID_RE.match(line_s)
        if vid_m:
            entry["remissoes"].append(vid_m.group(1).strip())
            current_lang = None
            continue

        # Sinónimos: "SIN.- ..."
        sin_m = SIN_RE.match(line_s)
        if sin_m:
            entry["sinonimos_gl"].extend(split_values(sin_m.group(1)))
            current_lang = None
            continue

        # Variantes: "VAR.- ..."
        var_m = VAR_RE.match(line_s)
        if var_m:
            entry["variantes_gl"].extend(split_values(var_m.group(1)))
            current_lang = None
            continue

        # Prefixo de língua: "es ...", "en ...", "pt ...", "la ..."
        lang_m = LANG_PREFIX.match(line_s)
        if lang_m:
            current_lang = lang_m.group(1)
            vals = split_values(lang_m.group(2))
            entry["traduccions"][current_lang].extend(vals)
            continue

        # Continuação de linha de tradução (fragmento que quebrou para a linha seguinte)
        if current_lang:
            is_remissao  = bool(re.search(r"Vid\.\-", line_s))
            is_novo_acr  = bool(re.match(r"^[A-Z]{2,}\s", line_s))
            is_lang_line = bool(LANG_PREFIX.match(line_s))
            is_sin_var   = bool(SIN_RE.match(line_s) or VAR_RE.match(line_s))
            if not is_remissao and not is_novo_acr and not is_lang_line and not is_sin_var:
                trad = entry["traduccions"][current_lang]
                # Se o último valor estava incompleto, concatena
                if trad and len(trad[-1]) < 20 and not trad[-1].endswith("]") and not trad[-1].endswith(")"):
                    trad[-1] = trad[-1] + " " + line_s.strip()
                else:
                    trad.extend(split_values(line_s))
                continue
            else:
                current_lang = None

        # Área médica
        areas = parse_areas(line_s)
        if areas:
            entry["areas"].extend(areas)
            entry["areas"] = list(dict.fromkeys(entry["areas"]))
            continue

        # Remissão inline (vid no meio da linha)
        vid_inline = re.search(r"Vid\.\-\s*(.+)$", line_s)
        if vid_inline:
            entry["remissoes"].append(vid_inline.group(1).strip())
            continue

    # --- Deduplicação ---
    for lang in entry["traduccions"]:
        entry["traduccions"][lang] = list(dict.fromkeys(entry["traduccions"][lang]))
    entry["remissoes"]    = list(dict.fromkeys(entry["remissoes"]))
    entry["sinonimos_gl"] = list(dict.fromkeys(entry["sinonimos_gl"]))

    return entry

# ---------------------------------------------------------------------------
# Extração dos blocos de uma coluna
# ---------------------------------------------------------------------------

def extract_column_blocks(col_lines):
    """
    Agrupa as linhas de uma coluna em blocos por entrada numerada.
    Cada novo número de entrada inicia um bloco.
    """
    blocks   = []
    current  = []

    for _, left, txt in col_lines:
        t = txt.strip()
        if re.match(r"^\d+\s+", t):
            if current:
                blocks.append(current)
            current = [t]
        else:
            current.append(t)

    if current:
        blocks.append(current)

    return blocks

# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def xml_to_dict(xml_path: str) -> dict:
    """
    Lê um ficheiro XML gerado pelo pdftohtml e extrai todas as entradas
    do vocabulário médico, devolvendo um dicionário estruturado.
    """
    print(f"A carregar XML: {xml_path}")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    all_entries = []
    seen_ids    = set()

    vocab_pages = [
        p for p in root.findall("page")
        if VOCAB_PAGE_START <= int(p.get("number")) <= VOCAB_PAGE_END
    ]
    print(f"Páginas a processar: {len(vocab_pages)} ({VOCAB_PAGE_START}–{VOCAB_PAGE_END})")

    for page in vocab_pages:
        raw_lines           = parse_page_to_lines(page)
        merged              = merge_close_lines(raw_lines)
        left_col, right_col = split_columns(merged)
        left_col            = clean_col(left_col)
        right_col           = clean_col(right_col)

        for col in (left_col, right_col):
            blocks = extract_column_blocks(col)
            for block in blocks:
                entry = parse_entry_block(block)
                if entry and entry["id"] not in seen_ids and entry["id"] >= 10 and entry["termo_gl"]:
                    seen_ids.add(entry["id"])
                    all_entries.append(entry)

    all_entries.sort(key=lambda e: e["id"])
    print(f"Entradas extraídas: {len(all_entries)}")

    return {
        "fonte":          "Vocabulario de Medicina (galego-español-inglés-portugués)",
        "editora":        "Universidade de Santiago de Compostela",
        "ano":            2008,
        "total_entradas": len(all_entries),
        "entradas":       all_entries
    }


def xml_to_json(xml_path: str, json_path: str = None) -> str:
    """
    Converte o XML para JSON e guarda o ficheiro.
    Devolve o caminho do ficheiro JSON gerado.
    """
    if json_path is None:
        json_path = os.path.splitext(xml_path)[0] + ".json"

    dicionario = xml_to_dict(xml_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dicionario, f, ensure_ascii=False, indent=2)

    print(f"JSON guardado: {json_path}")
    return json_path


if __name__ == "__main__":
    XML_PATH  = "medicina.xml"
    JSON_PATH = "medicina.json"
    xml_to_json(XML_PATH, JSON_PATH)
