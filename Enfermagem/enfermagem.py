import xml.etree.ElementTree as ET
import json
import os
import re

def analisar_xml_para_json():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Localizar o ficheiro XML
    xml_path = None
    for f in os.listdir(base_dir):
        if f.lower().endswith(".xml") and "enfermagem" in f.lower():
            xml_path = os.path.join(base_dir, f)
            break

    if not xml_path:
        print("❌ Erro: Ficheiro XML não encontrado.")
        return

    json_path = os.path.join(base_dir, "enfermagem.json")

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Erro ao ler o XML: {e}")
        return

    entries = []
    current_term = ""
    current_def = []
    current_source = ""
    capturando_fonte = False

    # Processamento página a página
    for page in root.findall(".//page"):
        elements = page.findall("text")
        
        # ORDENAÇÃO: 
        # 1. Identificamos o meio da página dinamicamente ou usamos 440 como margem segura
        # 2. Ordenamos por Coluna (Esquerda vs Direita) e depois por altura (top)
        elements.sort(key=lambda x: (int(x.get('left', 0)) > 440, int(x.get('top', 0))))

        for text_tag in elements:
            txt = "".join(text_tag.itertext()).strip()
            
            # Filtros de ruído (Títulos de topo e números de página)
            if not txt or "GLOSSÁRIO" in txt or "Página" in txt or (txt.isdigit() and len(txt) < 4):
                continue
                
            left_pos = int(text_tag.get('left', 0))
            font_id = text_tag.get('font')

            # IDENTIFICAÇÃO DO CONCEITO:
            # A fonte "0" é o nosso marcador universal de termos.
            # Se for font="0", é um novo termo, esteja ele em que coluna estiver.
            is_conceito = (font_id == "0")

            if is_conceito:
                # Salvar o termo anterior antes de processar o novo
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
                    # Se encontrarmos um novo link ou referência após "FONTE:"
                    current_source = (current_source + " " + txt).strip()
                else:
                    # Acumular descrição: apenas se não for um marcador de página ou ruído
                    current_def.append(txt)

    # Guardar o último termo processado
    if current_term:
        entries.append({
            "concept": current_term,
            "description": " ".join(current_def).strip(),
            "source": current_source if current_source else "Glossário de Enfermagem"
        })

    # Gravação Final
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    
    print(f"✅ SUCESSO! Extraídos {len(entries)} termos.")
    print(f"📂 Ficheiro atualizado: {json_path}")

if __name__ == "__main__":
    analisar_xml_para_json()