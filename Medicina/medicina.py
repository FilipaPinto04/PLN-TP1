import xml.etree.ElementTree as ET
import re, json, os

XML_PATH = "medicina.xml"
JSON_OUT = "medicina.json"

# Regex para ID, Termo e Classe
ENTRY_RE = re.compile(r"^(\d+)\s+(.+?)\s+([mfas]|m/f|mpl|fpl|adj\.?|adv\.?|v\.?|s\.?|loc\.?|prep\.?)$")
ID_TERMO_RE = re.compile(r"^(\d+)\s+(.+)$")
VID_RE  = re.compile(r"Vid\.[-\s]+(.*)", re.IGNORECASE)  

# Regex para SIN, VAR e Notas 
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
    # limpar
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
            
            # termo
            m_full = ENTRY_RE.match(content)
            m_id   = ID_TERMO_RE.match(content)
            
            if font == "3" or m_full or m_id:
                vm = VID_RE.search(content)
                if vm:
                    # termo antes do Vid.-
                    termo_vazio = content.split("Vid.")[0].strip()
                    alvo = vm.group(1).strip()
                    
                    flush()
                    current = new_entry(None, termo_vazio, "")
                    current["is_remissive"] = True
                    current["vid_target"] = alvo
                    flush() 
                    continue
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

            # áreas (font 6)
            if font == "6":
                for a in re.split(r"\s{2,}", content):
                    if a.strip() and a.strip() not in current["areas"]:
                        current["areas"].append(a.strip())
            
            # sinónimos e notas (font 5)
            elif font == "5" or "Nota" in content:
                sm = SIN_RE.match(content)
                nm = NOTA_RE.match(content)
                if sm:
                    tipo = "sinonimos" if "SIN" in sm.group(1).upper() else "variantes"
                    for p in re.split(r"\s*;\s*", sm.group(2)):
                        if p.strip(): current[tipo].append(p.strip())
                elif nm:
                    current["notas"].append(nm.group(1).strip())
                elif "SIN.-" in content: 
                    txt = content.replace("SIN.-", "").strip()
                    for p in re.split(r"\s*;\s*", txt):
                        if p.strip(): current["sinonimos"].append(p.strip())

            # traduções
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
    entries = parse_xml(XML_PATH)

    # entradas extra
    mapa_remissoes = {}
    for e in entries:
        if e.get("is_remissive") and e["vid_target"]:
            alvo = e["vid_target"].strip()
            origem = e["termo"].strip()
            if alvo not in mapa_remissoes:
                mapa_remissoes[alvo] = []
            if origem not in mapa_remissoes[alvo]:
                mapa_remissoes[alvo].append(origem)

    # dicionario
    dicionario_final = {}
    for e in entries:
        # dicionário se tiver ID
        if not e["id"] or not e["id"].isdigit():
            continue
            
        nome_chave = e["termo"]
        
        dicionario_final[nome_chave] = {
            "id":        e["id"],
            "genero":    e["genero"],
            "categoria": " | ".join(e["areas"]),
            "traducoes": {
                l: "; ".join(e["traducoes"][l])
                for l in ["es", "en", "pt"]
            },
            "sinonimos": e["sinonimos"],
            "variantes": e["variantes"], 
            "nota":      " ".join(e["notas"]),
            "entrada_extra": mapa_remissoes.get(nome_chave, [])
        }

    # guardar
    os.makedirs(os.path.dirname(os.path.abspath(JSON_OUT)), exist_ok=True)
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(dicionario_final, f, ensure_ascii=False, indent=4)

    print(f"{len(dicionario_final)} termos guardados em {JSON_OUT}")

if __name__ == "__main__":
    main()