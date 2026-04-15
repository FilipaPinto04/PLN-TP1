import xml.etree.ElementTree as ET
import json
import os
import re

def analisar():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(base_dir, "glossario_neologismos_saude.xml")
    json_path = os.path.join(base_dir, "neologismos.json")

    if not os.path.exists(xml_path):
        print(f"❌ Ficheiro {xml_path} não encontrado.")
        return

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Alterado para dicionário
    entries = {}
    current_entry = None

    for page in root.findall(".//page"):
        for text in page.findall("text"):
            txt = "".join(text.itertext()).strip()
            if not txt: continue
            
            left = int(text.get("left", 0))

            is_concept_start = (left == 128) and not re.match(r'^\d', txt) and len(txt) > 1

            if is_concept_start:
                if current_entry:
                    # Processa e adiciona ao dicionário usando o conceito como chave
                    resultado = processar_campos(current_entry)
                    entries[resultado["concept"]] = resultado
                
                current_entry = {
                    "concept": txt,
                    "grammar_category": "",
                    "raw_text": ""
                }
            elif current_entry:
                if not current_entry["grammar_category"] and re.match(r'^[sivn]\.(f|m|adj|adv)\.?$', txt.lower()):
                    current_entry["grammar_category"] = txt
                else:
                    current_entry["raw_text"] += " " + txt

    # Processa o último termo
    if current_entry:
        resultado = processar_campos(current_entry)
        entries[resultado["concept"]] = resultado

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Concluído! JSON gerado como dicionário com {len(entries)} termos.")

def processar_campos(item):
    full_text = re.sub(r'\s+', ' ', item["raw_text"]).strip()
    
    ing = re.search(r'([^;]+)\[ing\]', full_text)
    esp = re.search(r'([^;]+)\[esp\]', full_text)
    inf = re.search(r'Inf\.\s*encicl\.:\s*(.*)', full_text)
    
    def_clean = re.sub(r'[^;]+\[ing\]\s*;?\s*', '', full_text)
    def_clean = re.sub(r'[^;]+\[esp\]\s*;?\s*', '', def_clean)
    def_clean = re.sub(r'Inf\.\s*encicl\.:.*', '', def_clean)
    def_clean = re.sub(r'“.*”\s*\(\d+\)', '', def_clean) 
    
    return {
        "concept": item["concept"],
        "grammar_category": item["grammar_category"],
        "term_en": ing.group(1).strip() if ing else "",
        "term_es": esp.group(1).strip() if esp else "",
        "definition": def_clean.strip(),
        "inf_encicl": inf.group(1).strip() if inf else "",
        "source": "Glossário de Neologismos da Saúde"
    }

if __name__ == "__main__":
    analisar()