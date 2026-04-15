import xml.etree.ElementTree as ET
import json
import os
import re

def limpar(txt):
    if not txt: return ""
    # Corrige ligaturas do PDF (fi, fl) e remove espaços duplos
    txt = txt.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return re.sub(r'\s+', ' ', txt).strip().strip(',;. ')

def processar_ministerio():
    xml_input = "glossario_ministerio_saude.xml"
    json_output = "ministerio.json"
    
    if not os.path.exists(xml_input):
        print(f"❌ Erro: {xml_input} não encontrado.")
        return

    tree = ET.parse(xml_input)
    root = tree.getroot()
    
    # IDs de fontes de negrito e conectores para categorias
    BOLD_FONTS = {"1", "8", "11", "12", "13", "15", "17"}
    CONECTORS = (" à", " de", " do", " da", " e", " em", " para", " o", " a", " e ")
    
    entries = []
    current_entry = None
    comecou = False
    
    for page in root.findall(".//page"):
        items = page.findall(".//text")
        if not items: continue
        
        # --- DIVISÃO POR COLUNAS ---
        # Separamos a página em duas metades (Coluna 1 e Coluna 2)
        # Trust na ordem original do XML dentro de cada coluna
        mid = 446
        col1 = [t for t in items if int(t.get("left", 0)) < mid]
        col2 = [t for t in items if int(t.get("left", 0)) >= mid]
        
        state = "concept"

        for t in col1 + col2:
            content = "".join(t.itertext()).strip()
            if not content: continue
            
            # Filtros Globais (Cabeçalhos e Rodapés)
            if "Glossário" in content or "Ministério da Saúde" in content: continue
            if content.isdigit() and (int(t.get("top", 0)) > 1180 or int(t.get("top", 0)) < 150): continue

            font_id = t.get("font", "")
            is_bold = (font_id in BOLD_FONTS) or (t.find("b") is not None)
            left = int(t.get("left", 0))
            
            # Gatilho de início em "Abordagem médica"
            if not comecou:
                if "Abordagem" in content and is_bold: comecou = True
                else: continue

            # --- DETECÇÃO DE NOVO TERMO ---
            # Se é negrito e não é a etiqueta "Categoria:"
            if is_bold and "Categoria:" not in content:
                # Se o termo anterior já tem conteúdo, fecha-o e abre um novo
                if current_entry and (current_entry["category"] or current_entry["description"] or current_entry["reference"]):
                    entries.append(current_entry)
                    current_entry = {"concept": content, "category": "", "description": "", "reference": "", "source": "Ministério da Saúde", "_margin": left}
                    state = "concept"
                elif current_entry is None:
                    current_entry = {"concept": content, "category": "", "description": "", "reference": "", "source": "Ministério da Saúde", "_margin": left}
                    state = "concept"
                else:
                    # Se ainda não temos conteúdo, junta este negrito ao nome (ex: "Abordagem" + "médica")
                    current_entry["concept"] = (current_entry["concept"] + " " + content).strip()
                continue

            if current_entry:
                # 1. Marcador de Categoria
                if "Categoria:" in content:
                    state = "category"
                    parts = content.split("Categoria:")
                    if len(parts) > 1: current_entry["category"] = parts[1].strip()
                    continue
                
                # 2. Marcador de Referência (Ver...)
                if content.startswith("Ver") and state == "concept":
                    state = "reference"
                    current_entry["reference"] = content
                    continue

                # 3. Preenchimento de Campos
                if state == "concept":
                    # Se não é bold e não é marcador, começa a descrição
                    state = "description"
                    current_entry["description"] = content
                elif state == "category":
                    # Se o texto volta à margem esquerda e não termina em conector, vira descrição
                    cat_val = current_entry["category"].lower()
                    if left <= current_entry["_margin"] + 5 and not cat_val.endswith(CONECTORS):
                        state = "description"
                        current_entry["description"] = content
                    else:
                        current_entry["category"] = (current_entry["category"] + " " + content).strip()
                elif state == "description":
                    current_entry["description"] = (current_entry["description"] + " " + content).strip()
                elif state == "reference":
                    current_entry["reference"] = (current_entry["reference"] + " " + content).strip()

    if current_entry:
        entries.append(current_entry)

    # Limpeza Final e Desduplicação
    # --- SUBSTITUI ESTA SECÇÃO NO TEU SCRIPT ---
    
    # Limpeza Final e Transformação em DICIONÁRIO
    dicionario_final = {}
    for e in entries:
        for k in ["concept", "category", "description", "reference"]: 
            e[k] = limpar(e[k])
        
        if e["reference"]: 
            e["description"] = ""
        
        # Removemos a margem interna antes de guardar
        if "_margin" in e: 
            del e["_margin"]
        
        # Usamos o conceito (termo) como CHAVE do dicionário
        key = e["concept"].strip()
        
        # Apenas adicionamos se o termo for válido
        if len(key) > 2:
            # Se quiseres que a chave seja sempre em minúsculas para facilitar a união:
            # key = key.lower()
            
            dicionario_final[key] = {
                "categoria": e["category"],
                "descricao": e["description"],
                "referencia": e["reference"]
            }

    # Guardar como JSON (agora o objeto principal é { })
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(dicionario_final, f, ensure_ascii=False, indent=4)
    

if __name__ == "__main__":
    processar_ministerio()