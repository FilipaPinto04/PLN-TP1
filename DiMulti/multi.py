import xml.etree.ElementTree as ET
import json
import os
import re

XML_PATH  = "diccionari-multilinguee-de-la-covid-19.xml"
JSON_PATH = "./dicionario_catala.json"

COL_SPLIT = 442   

LANGS_LEFT  = ["oc", "eu", "gl", "es", "en", "fr", "it", "de"]
LANGS_RIGHT = ["pt", "pt [PT]", "pt [BR]", "nl", "ar"]
ALL_LANGS   = LANGS_LEFT + LANGS_RIGHT

BLACKLIST = ["DICCIONARI MULTILINGÜE", "TERMCAT", "ÍNDEX", "PÀG."]

GRAM_CLASSES = re.compile(r"^(n|adj|adv|v|f|m|loc|prep|pron)(\s+(m|f|n))?(\s+pl)?$")


def is_separator(content):
    """';' isolado ou quase isolado — separador de siglas/sinónimos."""
    return content.strip() in [";", "; ", " ;"]


def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    entries = []
    current = None
    current_lang = None
    modo = None         
    page_category = None

    def new_entry(id_val):
        return {
            "id": id_val,
            "termo": "",
            "classe_gramatical": "",
            "siglas": [],
            "sinonimos": [],
            "denominacio_comuna": [],
            "remissoes": [],
            "categoria": page_category,
            "definicao": "",
            "equivalentes": {},
            "codigos": {},
            "notas": [],
        }

    def add_to_lang(lang, text, is_class=False):
        if lang not in current["equivalentes"]:
            current["equivalentes"][lang] = {"termo": "", "classe": ""}
        if is_class:
            c = current["equivalentes"][lang]["classe"]
            current["equivalentes"][lang]["classe"] = (c + " " + text).strip()
        else:
            t = current["equivalentes"][lang]["termo"]
            current["equivalentes"][lang]["termo"] = (t + " " + text).strip()

    for page in root.findall(".//page"):

        for t in page.findall(".//text[@font='0']"):
            txt = "".join(t.itertext()).strip()
            if txt and not txt.isdigit():
                page_category = txt

        elements = []
        for t in page.findall(".//text"):
            content = "".join(t.itertext()).strip()
            if not content:
                continue
            if any(b in content.upper() for b in BLACKLIST):
                continue
            font = t.get("font", "0")
            left = int(t.get("left", 0))
            elements.append((left, font, content))

        # Separar em coluna esquerda e direita
        col_left  = [(f, c, l) for l, f, c in elements if l < COL_SPLIT]
        col_right = [(f, c, l) for l, f, c in elements if l >= COL_SPLIT]

        for font, content, left in col_left + col_right:

            if font == "1" and content.isdigit() and int(content) > 0:
                if current:
                    entries.append(current)
                current = new_entry(int(content))
                current_lang = None
                modo = None
                continue

            if current is None:
                continue

            # sigla / sin
            if font == "1" and content.isdigit() and int(content) > 0:
                col_atual = col_left + col_right
                pos = col_atual.index((font, content, left))
                proximo = next((f for f,c,l in col_atual[pos+1:pos+4] if c and f == "2"), None)
                anterior = next(((f,c) for f,c,l in reversed(col_atual[:pos]) if c), (None,None))
                if proximo is None or anterior[0] in ("4","10"):
                    continue  

            # ;
            if is_separator(content):
                if current_lang and current_lang in current["equivalentes"]:
                    add_to_lang(current_lang, ";")
                continue

            # termo ou sigla ou sin (font=2, negrito)
            if font == "2":
                if not current["termo"]:
                    current["termo"] = content
                elif modo == "sigla":
                    current["siglas"].append({"termo": content, "classe": ""})
                elif modo == "sinonimo":
                    current["sinonimos"].append({"termo": content, "classe": ""})
                elif modo == "den_com":
                    current["denominacio_comuna"].append({"termo": content, "classe": ""})
                elif modo == "veg":
                    current["remissoes"].append(content)
                    modo = None
                elif current_lang and current_lang in current["equivalentes"]:
                    add_to_lang(current_lang, content)
                continue

            # linguas e classe (font=3, itálico) 
            if font == "3":
                if content in ALL_LANGS or "pt [" in content:
                    current_lang = content
                    if content not in current["equivalentes"]:
                        current["equivalentes"][content] = {"termo": "", "classe": ""}
                    modo = None 
                elif content == "CAS":
                    current_lang = "CAS"
                    modo = None
                elif GRAM_CLASSES.match(content) or content in ["n", "adj", "v", "f", "m"]:
                    if current_lang and current_lang in current["equivalentes"]:
                        add_to_lang(current_lang, content, is_class=True)
                    elif modo == "sigla" and current["siglas"]:
                        c = current["siglas"][-1]["classe"]
                        current["siglas"][-1]["classe"] = (c + " " + content).strip()
                    elif modo == "sinonimo" and current["sinonimos"]:
                        c = current["sinonimos"][-1]["classe"]
                        current["sinonimos"][-1]["classe"] = (c + " " + content).strip()
                    elif modo == "den_com" and current["denominacio_comuna"]:
                        c = current["denominacio_comuna"][-1]["classe"]
                        current["denominacio_comuna"][-1]["classe"] = (c + " " + content).strip()
                    else:
                        g = current["classe_gramatical"]
                        current["classe_gramatical"] = (g + " " + content).strip()
                continue

            # árabe (font=4)
            if font == "4":
                if current_lang == "ar":
                    if "ar" not in current["equivalentes"]:
                        current["equivalentes"]["ar"] = {"termo": "", "classe": ""}
                    t_ar = current["equivalentes"]["ar"]["termo"]
                    current["equivalentes"]["ar"]["termo"] = (t_ar + " " + content).strip()
                continue

            # notas (font=5 e font=6)
            if font in ["5", "6"]:
                current_lang = None
                modo = None
                texto = content.strip()
                
                # texto começa com "Nota:", "1" ou "2" - nova entrada na lista
                if texto.startswith("Nota:") or (texto[0:1].isdigit() and texto[1:2] == "."):
                    current["notas"].append(texto)
                else:
                    if current["notas"]:
                        current["notas"][-1] = (current["notas"][-1] + " " + texto).strip()
                    else:
                        current["notas"].append(texto)
                continue

            # texto (font=1) 
            if font in ["1"]:
                if current_lang == "ar":
                    current_lang = None

                # Cabeçalho secção (maiúsculas + ponto)
                if content.isupper() and content.endswith(".") and len(content) > 4:
                    current_lang = None
                    current["categoria"] = content.rstrip(".")
                    current["definicao"] = (current["definicao"] + " " + content).strip()
                    continue

                # Rótulos que definem o tipo do próximo token (font=2)
                if content.strip() in ("sigla", "sigles"):
                    current_lang = None
                    modo = "sigla"
                    continue
                if content.strip() in ("sin.", "sin. compl."):
                    current_lang = None
                    modo = "sinonimo"
                    continue
                if content.strip() in ("den. com.",):
                    current_lang = None
                    modo = "den_com"
                    continue
                if content.strip() == "veg.":
                    current_lang = None
                    modo = "veg"
                    continue

                # "CAS" exceção
                if current_lang == "CAS":
                    current["codigos"]["CAS"] = content
                    current_lang = None
                    continue

                # Tradução  
                if current_lang and current_lang != "ar" and current_lang in current["equivalentes"]:
                    add_to_lang(current_lang, content)
                    continue

                # Sem língua activa - definição
                if not content.isdigit() and content not in ("veg.",):
                    current["definicao"] = (current["definicao"] + " " + content).strip()
    if current:
        entries.append(current)

    # tirar redundâncias
    seen_ids = {}
    for e in entries:
        id_val = e["id"]
        if id_val not in seen_ids:
            seen_ids[id_val] = e
        else:
            existing = seen_ids[id_val]
            if len(e.get("equivalentes", {})) > len(existing.get("equivalentes", {})):
                seen_ids[id_val] = e
    entries = sorted(seen_ids.values(), key=lambda e: e["id"])

    # limpeza final 
    for e in entries:
        for lang, t in e["equivalentes"].items():
            t["termo"] = t["termo"].strip(" ;").strip()
        e["definicao"] = e["definicao"].strip(" ;").strip()

        if not e.get("siglas"):             e.pop("siglas", None)
        if not e.get("sinonimos"):          e.pop("sinonimos", None)
        if not e.get("denominacio_comuna"): e.pop("denominacio_comuna", None)
        if not e.get("remissoes"):          e.pop("remissoes", None)
        if not e.get("codigos"):            e.pop("codigos", None)
        if not e.get("notas"):              e.pop("notas", None)

    return entries

def main():
    print("A iniciar o processamento do XML...")
    entries = parse_xml(XML_PATH)
    
    dicionario_final = {}
    for e in entries:
        termo_chave = e.get("termo", "").strip()
        
        if termo_chave:
            dicionario_final[termo_chave] = {
                "id": e.get("id"),
                "classe_gramatical": e.get("classe_gramatical"),
                "definicao": e.get("definicao"),
                "equivalentes": e.get("equivalentes"),
                "categoria": e.get("categoria"),
                "notas": e.get("notas", []),
                "siglas": e.get("siglas"),
                "sinonimos": e.get("sinonimos"),
                "codigos": e.get("codigos")
            }
            dicionario_final[termo_chave] = {k: v for k, v in dicionario_final[termo_chave].items() if v is not None}

    total_termos = len(dicionario_final)
    
    diretorio = os.path.dirname(JSON_PATH)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)
    
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dicionario_final, f, ensure_ascii=False, indent=2)
    
    print(f"Foram escritos {total_termos} termos únicos no dicionário.")
    print(f"Destino: {JSON_PATH}")

if __name__ == "__main__":
    main()