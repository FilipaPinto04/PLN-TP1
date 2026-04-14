"""
icnp_xml_to_json.py
-------------------
Analisa o XML gerado a partir do ICNP_2019_Português.pdf
e produz um ficheiro JSON estruturado.

Uso:
    python icnp_xml_to_json.py
"""

import xml.etree.ElementTree as ET
import json
import re
import os

# ---------------------------------------------------------------------------
# Configuração específica deste PDF
# ---------------------------------------------------------------------------

VOCAB_PAGE_START = 1
VOCAB_PAGE_END   = 141

# Thresholds horizontais das colunas (left)
COL_CODE_MAX  = 230   # left < 230  → coluna code+axis
COL_TERM_MAX  = 510   # 230 <= left < 510 → coluna term
                      # left >= 510 → coluna description

FONT_HEADER = "2"     # cabeçalhos da tabela ("code", "axis term", "description")
FONT_DATA   = "3"     # dados da tabela
FONT_FOOTER = "0"     # rodapé ("CIPE", data, número de página)

# Regex para extrair code e axis da coluna esquerda: "10041692  F"
CODE_AXIS_RE = re.compile(r"^(\d+)\s+([A-Z]+)$")

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def get_text(elem):
    return "".join(elem.itertext()).strip()

def xml_to_json(xml_path, json_path):
    print(f"[1/3] A carregar XML: {xml_path}")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    entries   = []
    current   = None  # entrada em curso
    last_top  = None  # top da última linha de description (para continuações)

    print(f"[2/3] A analisar...")

    for page in root.findall("page"):
        num = int(page.get("number"))
        if not (VOCAB_PAGE_START <= num <= VOCAB_PAGE_END):
            continue

        for t in page.findall("text"):
            font    = t.get("font")
            left    = int(t.get("left", 0))
            top     = int(t.get("top", 0))
            content = get_text(t)

            if not content:
                continue

            # Ignorar cabeçalhos e rodapés
            if font in (FONT_HEADER, FONT_FOOTER):
                continue

            if font != FONT_DATA:
                continue

            # --- Coluna code + axis ---
            if left < COL_CODE_MAX:
                m = CODE_AXIS_RE.match(content)
                if m:
                    # Guarda entrada anterior
                    if current:
                        entries.append(current)
                    current = {
                        "code":        m.group(1),
                        "axis":        m.group(2),
                        "term":        "",
                        "description": ""
                    }
                    last_top = None

            # --- Coluna term ---
            elif left < COL_TERM_MAX:
                if current is not None:
                    if current["term"]:
                        current["term"] += " " + content
                    else:
                        current["term"] = content

            # --- Coluna description ---
            else:
                if current is not None:
                    if current["description"]:
                        current["description"] += " " + content
                    else:
                        current["description"] = content
                    last_top = top

    # Adiciona a última entrada
    if current:
        entries.append(current)

    print(f"      {len(entries)} entradas extraídas.")

    output = {
        "fonte":          "CIPE® 2019 - Classificação Internacional para a Prática de Enfermagem",
        "editora":        "International Council of Nurses (ICN)",
        "ano":            2019,
        "lingua":         "pt",
        "total_entradas": len(entries),
        "entradas":       entries
    }

    print(f"[3/3] A guardar JSON: {json_path}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Concluído!")
    return output


if __name__ == "__main__":
    BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
    XML_PATH  = os.path.join(BASE_DIR, "ICNP_2019_PortuguÃªs.xml")
    JSON_PATH = os.path.join(BASE_DIR, "ICNP.json")
    xml_to_json(XML_PATH, JSON_PATH)