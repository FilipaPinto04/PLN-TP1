import xml.etree.ElementTree as ET
import json
import os

def parse_wipo_xml(xml_path, json_path):
    if not os.path.exists(xml_path):
        print(f"Erro: Ficheiro {xml_path} não encontrado.")
        return

    tree = ET.parse(xml_path)
    root = tree.getroot()

    mapa_linguas = {
        "EN": "ingles", "PT": "portugues", "FR": "frances", "ES": "espanhol",
        "DE": "alemao", "AR": "arabe", "RU": "russo", "ZH": "chines",
        "JA": "japones", "KO": "coreano"
    }

    data = {"fonte": "WIPO Pearl COVID-19 Glossary", "total_entradas": 0, "entradas": []}
    current_entry = None
    current_lang = None
    blacklist = ["MULTILINGUAL GLOSSARY", "WIPO PEARL", "COVID-19 GLOSSARY", "FOREWORD", "CONTENTS"]

    print(f"[1/2] A analisar páginas usando filtro de fonte (font='9')...")

    for page in root.findall('.//page'):
        page_num = page.get('number')
        
        for text in page.findall('.//text'):
            # Captura o texto e o atributo da fonte
            content = "".join(text.itertext()).strip()
            font_id = text.get('font')
            
            if not content or any(b in content.upper() for b in blacklist) or content.isdigit():
                continue

            content_upper = content.upper()
            is_bold = text.find('b') is not None

            # --- ESTRATÉGIA BASEADA NA FONT="9" ---
            # Se a fonte for 9, é categoricamente uma CATEGORIA
            if font_id == "9":
                if current_entry:
                    # Limpa colchetes se existirem e guarda
                    limpo = content.replace("[", "").replace("]", "").strip()
                    if current_entry["categoria"]:
                        current_entry["categoria"] += " " + limpo
                    else:
                        current_entry["categoria"] = limpo
                continue # Salta para o próximo elemento para não tratar como termo/definição

            # 1. NOVO TERMO (Negrito e não é sigla de língua)
            # Geralmente termos EN têm uma fonte específica também (podes verificar se é a 4 ou 2)
            if is_bold and content_upper not in mapa_linguas and len(content) > 3:
                if current_entry:
                    data["entradas"].append(current_entry)
                
                current_entry = {
                    "termo_en": content,
                    "categoria": None,
                    "pagina": page_num,
                    "traducoes": {lang: "" for lang in mapa_linguas.values()},
                    "definicao_en": ""
                }
                current_lang = "EN"

            # 2. MUDANÇA DE LÍNGUA
            elif content_upper in mapa_linguas:
                current_lang = content_upper
            
            # 3. ACUMULAR CONTEÚDO (DEFINIÇÕES OU TRADUÇÕES)
            elif current_entry:
                if current_lang == "EN":
                    if content != current_entry["termo_en"]:
                        current_entry["definicao_en"] = (current_entry["definicao_en"] + " " + content).strip()
                elif current_lang in mapa_linguas:
                    lang_key = mapa_linguas[current_lang]
                    current_entry["traducoes"][lang_key] = (current_entry["traducoes"][lang_key] + " " + content).strip()

    if current_entry:
        data["entradas"].append(current_entry)

    data["total_entradas"] = len(data["entradas"])
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Concluído! {data['total_entradas']} termos extraídos. A categoria deve estar preenchida!")

if __name__ == "__main__":
    parse_wipo_xml("WIPOPearl_COVID-19_Glossary.xml", "wipo.json")