import xml.etree.ElementTree as ET
import json
import os

def analisar_xml_para_json():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    xml_path = None
    for f in os.listdir(base_dir):
        if f.lower().endswith(".xml") and "enfermagem" in f.lower():
            xml_path = os.path.join(base_dir, f)
            break

    if not xml_path:
        print("Ficheiro XML não encontrado.")
        return

    json_path = os.path.join(base_dir, "enfermagem.json")

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Erro ao ler o XML: {e}")
        return

    entries = []
    current_term = ""
    current_def = []
    current_source = ""
    capturando_fonte = False

    for page in root.findall(".//page"):
        elements = page.findall("text")
        
        # ordenar
        elements.sort(key=lambda x: (int(x.get('left', 0)) > 440, int(x.get('top', 0))))

        for text_tag in elements:
            txt = "".join(text_tag.itertext()).strip()
            
            # filtros de ruído 
            if not txt or "GLOSSÁRIO" in txt or "Página" in txt or (txt.isdigit() and len(txt) < 4):
                continue
                
            left_pos = int(text_tag.get('left', 0))
            font_id = text_tag.get('font')

            # termo (fonte 0) 
            is_conceito = (font_id == "0")

            if is_conceito:
                if current_term:
                    entries.append({
                        "concept": current_term,
                        "description": " ".join(current_def).strip(),
                        "source": current_source if current_source else "Glossário de Enfermagem"
                    })
                
                current_term = txt
                current_def = []
                current_source = ""
                capturando_fonte = False
                
            elif "FONTE:" in txt.upper():
                capturando_fonte = True
                continue
                
            elif current_term:
                if capturando_fonte:
                    current_source = (current_source + " " + txt).strip()
                else:
                    current_def.append(txt)

    # guardar
    if current_term:
        entries.append({
            "concept": current_term,
            "description": " ".join(current_def).strip(),
            "source": current_source if current_source else "Glossário de Enfermagem"
        })

    dicionario_final = {}
    for e in entries:
        termo_chave = e["concept"].strip()
        
        if len(termo_chave) > 1:
            dicionario_final[termo_chave] = {
                "descricao": e["description"],
                "fonte": e["source"]
            }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dicionario_final, f, ensure_ascii=False, indent=4)
    
    print(f"Extraídos {len(dicionario_final)} termos.")
    
if __name__ == "__main__":
    analisar_xml_para_json()