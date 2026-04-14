import xml.etree.ElementTree as ET
import json
import os
import re

def limpar(txt):
    if not txt: return ""
    # Normaliza espaços e remove pontuação residual
    txt = txt.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return re.sub(r'\s+', ' ', txt).strip().strip(',;. ')

def processar_ministerio_v28(xml_input="glossario_ministerio_saude.xml", json_output="ministerio.json"):
    if not os.path.exists(xml_input):
        print(f"❌ Erro: '{xml_input}' não encontrado.")
        return

    tree = ET.parse(xml_input)
    root = tree.getroot()
    entries = []
    
    # Identificadores de Negrito (Termos técnicos)
    BOLD_FONTS = {"1", "8", "11", "12", "13"}
    # Conectores para não cortar categorias a meio
    CONECTORS = (" à", " de", " do", " da", " e", " em", " para", " o", " a")
    
    current_entry = None
    comecou = False
    last_font_was_bold = False
    state = "concept" # concept, category, description, reference

    for page in root.findall(".//page"):
        items = page.findall(".//text")
        if not items: continue
        
        # Separação por colunas (Esquerda < 446, Direita >= 446)
        col1 = [t for t in items if int(t.get("left", 0)) < 446]
        col2 = [t for t in items if int(t.get("left", 0)) >= 446]
        
        # Ordenamos apenas por altura dentro de cada coluna
        col1.sort(key=lambda x: int(x.get("top", 0)))
        col2.sort(key=lambda x: int(x.get("top", 0)))
        
        for t in col1 + col2:
            content = "".join(t.itertext()).strip()
            if not content or "Glossário" in content or "Ministério da Saúde" in content:
                continue
            
            font_id = t.get("font", "")
            is_bold = (font_id in BOLD_FONTS) or (t.find("b") is not None)
            
            # Gatilho de início
            if not comecou:
                if "Abordagem" in content and is_bold: comecou = True
                else: continue

            # --- LÓGICA DE TRANSIÇÃO ---
            # Se é negrito e não é a etiqueta "Categoria:"
            if is_bold and "Categoria:" not in content:
                if last_font_was_bold and current_entry:
                    # Continuação do mesmo conceito (ex: "Abordagem" + "médica")
                    current_entry["concept"] += " " + content
                else:
                    # NOVO TERMO (porque o anterior não era bold)
                    if current_entry:
                        entries.append(current_entry)
                    current_entry = {
                        "concept": content, "category": "", 
                        "description": "", "reference": "", 
                        "source": "Ministério da Saúde"
                    }
                    state = "concept"
                last_font_was_bold = True
                continue

            # Se chegámos aqui, o texto atual NÃO é um título de conceito
            last_font_was_bold = False
            
            if current_entry:
                if "Categoria:" in content:
                    state = "category"
                    parts = content.split("Categoria:")
                    if len(parts) > 1: current_entry["category"] = parts[1].strip()
                
                elif content.startswith("Ver") and state == "concept":
                    state = "reference"
                    current_entry["reference"] = content
                
                elif state == "category":
                    # Se a categoria termina em conector, continua a ser categoria
                    if current_entry["category"].lower().endswith(CONECTORS) or len(current_entry["category"]) < 10:
                        current_entry["category"] = (current_entry["category"] + " " + content).strip()
                    else:
                        state = "description"
                        current_entry["description"] = content
                else:
                    # Acumula na descrição ou referência
                    if state == "reference":
                        current_entry["reference"] = (current_entry["reference"] + " " + content).strip()
                    else:
                        current_entry["description"] = (current_entry["description"] + " " + content).strip()

    if current_entry:
        entries.append(current_entry)

    # Limpeza final e desduplicação
    final = []
    vistos = set()
    for e in entries:
        for k in ["concept", "category", "description", "reference"]:
            e[k] = limpar(e[k])
        if e["reference"]: e["description"] = ""
        
        # Filtro de duplicados
        key = e["concept"].lower()
        if key not in vistos and len(e["concept"]) > 2:
            final.append(e)
            vistos.add(key)

    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=4)
    
    print(f"✅ SUCESSO! {len(final)} termos extraídos corretamente.")

if __name__ == "__main__":
    processar_ministerio_v28()