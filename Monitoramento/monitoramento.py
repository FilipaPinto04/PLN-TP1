import xml.etree.ElementTree as ET
import json
import re

DECORATIVE_FONTS = {"4", "5", "6", "7", "8", "10", "11", "12", "13"}
TERM_FONTS = {"0", "3"} 


def nova_entrada(conceito):
    return {
        "concept": conceito,
        "classe": "",
        "sinonimos": [],
        "description": "",
        "notes": [],
        "spanish": "",
        "english": "",
    }

def e_termo(font, left):
    if font not in TERM_FONTS:
        return False
    return (60 <= left <= 70) or (100 <= left <= 115)


def extrair_sinonimo_inline(texto):
    m = re.match(r'^Sin\.?\s+(.+)', texto, re.IGNORECASE)
    if m:
        partes = [p.strip().rstrip('.') for p in m.group(1).split(';')]
        return [p for p in partes if p]
    return []


def limpar_prefixo_rotulo(texto):
    return re.sub(r'^[:\s,.]+', '', texto).strip()


def processar_glossario(xml_path, json_out):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # dicionario
    entries = {}
    current = None
    modo = None   
    espera_valor_rotulo = False

    for page in root.findall(".//page"):
        for t in page.findall(".//text"):
            content = "".join(t.itertext()).strip()
            font = t.get("font", "")
            left = int(t.get("left", 0))

            if font in DECORATIVE_FONTS or not content:
                continue

            # termo
            if e_termo(font, left):
                termo = content.strip(" .,;:")
                if not termo:
                    continue
                if current:
                    entries[current["concept"]] = current
                current = nova_entrada(termo)
                modo = "desc"
                espera_valor_rotulo = False
                continue

            if current is None:
                continue

            low = content.lower()

            # processamento 
            if font == "9" and "⇒" in content:
                modo = "sigla"
                continue

            # itálicos (font=2) 
            if font == "2":

                # classe
                if re.fullmatch(r'(fem|masc|pl|misto)(\.|\s)*', low.strip()):
                    current["classe"] = content.strip().strip('.')
                    modo = "pos_classe"
                    continue
                # notas
                if re.match(r'^notas?\b', low):
                    modo = "notas"
                # traducao
                elif re.match(r'^em (espanhol|ingl[eê]s)', low):
                    pass 
                elif re.match(r'^ver\b', low):
                    modo = "ver"

                # sinónimos 
                if re.search(r'\bsin\.?\b', low):
                    current["description"] = re.sub(r'\s*ver$', '', current["description"], flags=re.IGNORECASE).strip()
                    parts = re.split(r'sin\.?\s*', content, flags=re.IGNORECASE)
                    if len(parts) > 1 and parts[1].strip():
                        current["sinonimos"].append(parts[1].strip().rstrip('.'))
                    modo = "sinonimo"
                    continue

                # modo sinónimo passa a itálico - continuação
                if modo == "sinonimo":
                    if current["sinonimos"]:
                        current["sinonimos"][-1] = (current["sinonimos"][-1] + " " + content.strip()).strip().rstrip('.')
                    else:
                        current["sinonimos"].append(content.strip().rstrip('.'))
                    continue

                if "em espanhol" in low:
                    modo = "espanhol"
                    valor = re.sub(r'^em espanhol\s*:?\s*', '', content, flags=re.IGNORECASE).strip()
                    if valor: current["spanish"] = (current["spanish"] + " " + valor).strip()
                    espera_valor_rotulo = False
                    continue

                if "em inglês" in low or "em ingles" in low:
                    modo = "ingles"
                    valor = re.sub(r'^em ingl[eê]s\s*:?\s*', '', content, flags=re.IGNORECASE).strip()
                    if valor: current["english"] = (current["english"] + " " + valor).strip()
                    espera_valor_rotulo = False
                    continue

                # sigla
                if modo == "sigla":
                    alvo = content.strip().rstrip('.')
                    if alvo:
                        prefixo = "⇒ "
                        current["description"] = (current["description"] + " " + prefixo + alvo).strip()
                    modo = "desc"
                    continue

                #notas 
                if re.match(r'^notas?\b', low):
                    modo = "notas"
                    continue

                if re.match(r'^ver\b', low):
                    ref = content.strip().rstrip('.')
                    if modo == "notas":
                        current["notes"].append(ref) if not current["notes"] else current["notes"][-1] + " " + ref
                    else:
                        current["description"] = (current["description"] + " " + ref).strip()
                    continue

                # lingua
                if modo in ("espanhol", "ingles"):
                    lang_key = "spanish" if modo == "espanhol" else "english"
                    current[lang_key] = (current[lang_key] + " " + content.strip()).strip()
                    continue

                # fallback
                clean = limpar_prefixo_rotulo(content)
                if not clean: continue
                if modo == "notas":
                    if current["notes"]: current["notes"][-1] = (current["notes"][-1] + " " + clean).strip()
                    else: current["notes"].append(clean)
                else:
                    current["description"] = (current["description"] + " " + clean).strip()
                continue

            # texto (font=1)
            if font == "1":
                if re.fullmatch(r'[\s,\.;:]+', content):
                    if modo in ("espanhol", "ingles"):
                        lang_key = "spanish" if modo == "espanhol" else "english"
                        current[lang_key] += content
                    continue

                clean = limpar_prefixo_rotulo(content)
                if not clean:
                    continue

                # sinonimo (depois descrição)
                if modo == "sinonimo":
                    if (len(clean) > 15 and clean[0].isupper()) or content.startswith(". "):
                        modo = "desc"
                    else:
                        if current["sinonimos"]:
                            current["sinonimos"][-1] = (current["sinonimos"][-1] + " " + clean).strip()
                        else:
                            current["sinonimos"].append(clean)
                        continue

                # tradução
                if modo == "espanhol":
                    current["spanish"] = (current["spanish"] + " " + clean).strip()
                    continue
                if modo == "ingles":
                    current["english"] = (current["english"] + " " + clean).strip()
                    continue

                # notas
                if modo == "notas":
                    if re.match(r'^([ivxlcdm]+\)|[a-z]\))', clean.lower()):
                        current["notes"].append(clean)
                    elif current["notes"]:
                        current["notes"][-1] = (current["notes"][-1] + " " + clean).strip()
                    else:
                        current["notes"].append(clean)
                    continue

                # descrião - "ver" (referência) ou "desc"
                if not current["description"].endswith(clean):
                    current["description"] = (current["description"] + " " + clean).strip()
                continue

    if current:
        entries[current["concept"]] = current

    #dicionario
    for e in entries.values():
        e["description"] = re.sub(r'\s+', ' ', e["description"]).strip().lstrip('. ')
        
        for s in e["sinonimos"]:
            if e["description"].startswith(s):
                e["description"] = e["description"][len(s):].strip().lstrip('. ')

        e["notes"] = [re.sub(r'\s+', ' ', n).strip().lstrip(': ') for n in e["notes"] if n.strip()]

        for lang in ["spanish", "english"]:
            val = e[lang].strip().lstrip(': ')
            val = re.sub(r'\.+$', '', val)
            e[lang] = val.strip()

        e["sinonimos"] = [s.strip().rstrip('.') for s in e["sinonimos"] if s.strip()]
        e["classe"] = e["classe"].strip().strip('.')

    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)

    print(f"{len(entries)} termos extraídos para {json_out}")

if __name__ == "__main__":
    processar_glossario(
        "m_glossario-tematico-monitoramento-e-avaliacao.xml",
        "monitoramento.json"
    )