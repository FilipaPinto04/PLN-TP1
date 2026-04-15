import xml.etree.ElementTree as ET
import json
import re
import os

VOCAB_PAGE_START = 1
VOCAB_PAGE_END   = 141

COL_CODE_MAX  = 230   
COL_TERM_MAX  = 510   

FONT_HEADER = "2"     
FONT_DATA   = "3"    
FONT_FOOTER = "0"    

# extrair code e axis da coluna esquerda: "10041692  F"
CODE_AXIS_RE = re.compile(r"^(\d+)\s+([A-Z]+)$")


def get_text(elem):
    return "".join(elem.itertext()).strip()

def xml_to_json(xml_path, json_path):
    print(f"[1/3] A carregar XML: {xml_path}")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    entries   = []
    current   = None  
    last_top  = None  

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

            # coluna code + axis 
            if left < COL_CODE_MAX:
                m = CODE_AXIS_RE.match(content)
                if m:
                    if current:
                        entries.append(current)
                    current = {
                        "code":        m.group(1),
                        "axis":        m.group(2),
                        "term":        "",
                        "description": ""
                    }
                    last_top = None

            # termo
            elif left < COL_TERM_MAX:
                if current is not None:
                    if current["term"]:
                        current["term"] += " " + content
                    else:
                        current["term"] = content

            # descrição
            else:
                if current is not None:
                    if current["description"]:
                        current["description"] += " " + content
                    else:
                        current["description"] = content
                    last_top = top

    if current:
        entries.append(current)

    print(f"{len(entries)} termos extraídos.")

    output = {
        "fonte":          "CIPE® 2019 - Classificação Internacional para a Prática de Enfermagem",
        "editora":        "International Council of Nurses (ICN)",
        "ano":            2019,
        "lingua":         "pt",
        "total_entradas": len(entries),
        "entradas":       entries
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


if __name__ == "__main__":
    BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
    XML_PATH  = os.path.join(BASE_DIR, "ICNP_2019_PortuguÃªs.xml")
    JSON_PATH = os.path.join(BASE_DIR, "ICNP.json")
    xml_to_json(XML_PATH, JSON_PATH)