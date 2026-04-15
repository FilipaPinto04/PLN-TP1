import xml.etree.ElementTree as ET
import re, json, os

XML_PATH = "medicina.xml"
JSON_OUT = "medicina.json"

# Regex para ID, Termo e Classe
ENTRY_RE = re.compile(r"^(\d+)\s+(.+?)\s+([mfas]|m/f|mpl|fpl|adj\.?|adv\.?|v\.?|s\.?|loc\.?|prep\.?)$")
ID_TERMO_RE = re.compile(r"^(\d+)\s+(.+)$")

# Regex para SIN, VAR e Notas (mais flexível)
SIN_RE   = re.compile(r"^(SIN\.|VAR\.)[-\s]+(.*)", re.IGNORECASE)
NOTA_RE  = re.compile(r"^Nota\.[-\s]+(.*)", re.IGNORECASE)
LANGS    = {"es", "en", "pt"}

def gtext(el):
    return "".join(el.itertext()).strip()

def new_entry(num, termo, genero):
    termo_limpo = termo.strip()
    termo_limpo = re.sub(r"\s+[as]$", "", termo_limpo)
    termo_limpo = re.sub(r"\s+", " ", termo_limpo)
    
    return {
        "id": str(num) if num else "rem",
        "termo": termo_limpo,
        "genero": genero.strip() if genero else "",
        "areas": [],
        "sinonimos": [],
        "variantes": [],
        "notas": [],
        "traducoes": {l: [] for l in LANGS},
    }

def add_lang_term(current, lang, text):
    if not text.strip() or text.strip() == ";": return
    # Limpeza de caracteres residuais de formatação
    text = text.replace("•", "").strip()
    partes = [p.strip() for p in re.split(r"\s*;\s*", text) if p.strip()]
    for p in partes:
        if p and p not in current["traducoes"][lang]:
            current["traducoes"][lang].append(p)

def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    entries = []
    current = None
    current_lang = None

    def flush():
        nonlocal current
        if current:
            if any(current["traducoes"].values()) or current["id"] != "rem":
                entries.append(current)
        current = None

    for page in root.findall("page"):
        elems = []
        for t in page.findall("text"):
            c = gtext(t)
            if not c: continue
            top, left, font = int(t.get("top")), int(t.get("left")), t.get("font")
            if top < 50 or top > 950: continue 
            elems.append((top, left, font, c))

        col_esq = sorted([e for e in elems if e[1] < 300], key=lambda x: (x[0], x[1]))
        col_dir = sorted([e for e in elems if e[1] >= 300], key=lambda x: (x[0], x[1]))

        for top, left, font, content in col_esq + col_dir:
            
            # Novo Termo
            m_full = ENTRY_RE.match(content)
            m_id   = ID_TERMO_RE.match(content)
            
            if font == "3" or m_full or m_id:
                if m_full:
                    flush()
                    current = new_entry(m_full.group(1), m_full.group(2), m_full.group(3))
                    current_lang = None
                    continue
                elif m_id:
                    flush()
                    current = new_entry(m_id.group(1), m_id.group(2), "")
                    current_lang = None
                    continue
                elif len(content) > 3 and not content.startswith(("es ", "en ", "pt ")):
                    flush()
                    current = new_entry(None, content, "")
                    current_lang = None
                    continue

            if not current: continue

            # Áreas (font 6)
            if font == "6":
                # Divide por múltiplos espaços para limpar áreas como "Fisioloxía   Anatomía"
                for a in re.split(r"\s{2,}", content):
                    if a.strip() and a.strip() not in current["areas"]:
                        current["areas"].append(a.strip())
            
            # Sinónimos e Notas (font 5)
            elif font == "5" or "Nota" in content:
                sm = SIN_RE.match(content)
                nm = NOTA_RE.match(content)
                if sm:
                    tipo = "sinonimos" if "SIN" in sm.group(1).upper() else "variantes"
                    for p in re.split(r"\s*;\s*", sm.group(2)):
                        if p.strip(): current[tipo].append(p.strip())
                elif nm:
                    current["notas"].append(nm.group(1).strip())
                elif "SIN.-" in content: # Fallback para formatos colados
                    txt = content.replace("SIN.-", "").strip()
                    for p in re.split(r"\s*;\s*", txt):
                        if p.strip(): current["sinonimos"].append(p.strip())

            # Traduções
            elif content.strip()[:2] in LANGS and (content.strip()[2:3] == " " or len(content.strip()) == 2):
                lang = content.strip()[:2]
                current_lang = lang
                resto = content.strip()[2:].strip()
                if resto:
                    add_lang_term(current, lang, resto)
            
            elif (font == "7" or font == "0") and current_lang:
                add_lang_term(current, current_lang, content)

    flush()
    return entries

def main():
    print("[MED] A processar XML...")
    entries = parse_xml(XML_PATH)

    dicionario_final = {}
    for e in entries:
        nome_chave = e["termo"]
        
        # Formata o género
        gen = e["genero"]
        if gen == "a": gen = "adj."
        
        trads = {l: "; ".join(e["traducoes"][l]) for l in ["es", "en", "pt"]}

        dicionario_final[nome_chave] = {
            "id": e["id"],
            "genero": gen,
            "categoria": " ".join(e["areas"]), # Espaço simples entre áreas
            "traducoes": trads,
            "sinonimos": e["sinonimos"],
            "variantes": e["variantes"],
            "nota": " ".join(e["notas"]),
            "entrada_extra": {}
        }

    diretorio = os.path.dirname(os.path.abspath(JSON_OUT))
    if diretorio: os.makedirs(diretorio, exist_ok=True)

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(dicionario_final, f, ensure_ascii=False, indent=4)

    print(f"Sucesso! {len(dicionario_final)} termos extraídos.")

if __name__ == "__main__":
    main()