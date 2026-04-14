import xml.etree.ElementTree as ET
import json
import re

def processar_monitoramento_v14(xml_path, json_out):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    entries = []
    current = None
    modo = "descricao"

    for page in root.findall(".//page"):
        for t in page.findall(".//text"):
            content = "".join(t.itertext()).strip()
            font = t.get("font")
            left = int(t.get("left", 0))

            if not content or content.isdigit() or "Glossário Temático" in content:
                continue

            # 1. NOVO TERMO (Âncora Margem Esquerda com tolerância)
            # Aceitamos entre 60 e 70 para compensar erros de conversão do PDF
            is_start_margin = 60 <= left <= 70
            
            # Um novo termo deve estar na margem E usar Font 0 ou Font 3
            if is_start_margin and (font == "0" or font == "3"):
                # IMPORTANTE: Se o texto for curto (título) ou estiver em Maiúsculas
                if len(content.split()) < 5 or content.isupper():
                    if current:
                        entries.append(current)
                    current = {
                        "concept": content.strip(),
                        "classe": "",
                        "description": "",
                        "sinonimos": [],
                        "notes": [],
                        "spanish": "",
                        "english": ""
                    }
                    modo = "descricao"
                    continue

            if not current: continue
            low = content.lower()

            # 2. DETECÇÃO DE RÓTULOS (Font 2 / Font 4)
            # Se encontrar um rótulo, mudamos o modo e saltamos para o próximo elemento
            if font == "2" or font == "4":
                if "sin" in low: modo = "sinonimo"; continue
                elif "nota" in low: modo = "notas"; continue
                elif "ver" in low: 
                    modo = "notas"
                    current["notes"].append(content)
                    continue
                elif "espanhol" in low: modo = "espanhol"; continue
                elif "inglês" in low or "ingles" in low: modo = "ingles"; continue
                elif low in ["fem", "masc", "fem.", "masc."]:
                    current["classe"] = content
                    continue

            # 3. ACUMULAÇÃO DE CONTEÚDO (Fontes 1, 2, 3, 4, 9)
            # Limpeza de prefixos (Aula 4)
            clean = re.sub(r'^[:\s,.]+', '', content).strip()
            if not clean: continue

            if modo == "sinonimo":
                # Se for um sinónimo novo (após ;) ou o primeiro da lista
                if not current["sinonimos"] or content.startswith(";"):
                    current["sinonimos"].append(clean)
                else:
                    # Se o texto for curto, acumulamos no sinónimo
                    if len(clean.split()) < 4: 
                        current["sinonimos"][-1] = (current["sinonimos"][-1] + " " + clean).strip()
                    else:
                        # Se o texto for longo, é a DESCRIÇÃO que começou!
                        current["description"] = clean
                        modo = "descricao" # Mudança de estado automática
            
            elif modo == "espanhol":
                current["spanish"] = (current["spanish"] + " " + clean).strip()
            
            elif modo == "ingles":
                current["english"] = (current["english"] + " " + clean).strip()
            
            elif modo == "notas":
                if re.match(r'^[a-z]\)', clean):
                    current["notes"].append(clean)
                elif current["notes"]:
                    current["notes"][-1] = (current["notes"][-1] + " " + clean).strip()
                else:
                    current["notes"].append(clean)
            
            elif modo == "descricao":
                # Evita duplicação (ex: "Área Área")
                if not current["description"].endswith(clean):
                    current["description"] = (current["description"] + " " + clean).strip()

    if current: entries.append(current)
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=4) #

processar_monitoramento_v14("m_glossario-tematico-monitoramento-e-avaliacao.xml", "monitoramento_final.json")