import xml.etree.ElementTree as ET
import json
import os
import re

def processar_termos_medicos(xml_input="termos.xml", json_output="termos.json"):
    if not os.path.exists(xml_input):
        print(f"❌ Erro: '{xml_input}' não encontrado.")
        return

    print(f"⏳ Processando XML e gerando Dicionário...")
    
    try:
        tree = ET.parse(xml_input)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Erro ao ler XML: {e}")
        return

    linhas_pdf = []
    buffer_linha = []
    MARGEM_ESQUERDA = 135 

    for page in root.findall(".//page"):
        for t in page.findall(".//text"):
            content = "".join(t.itertext())
            left = int(t.get("left", 0))
            is_bold = (t.find("b") is not None) or (t.get("font") in ["0", "1", "3"])
            
            if left < MARGEM_ESQUERDA and buffer_linha:
                linhas_pdf.append(buffer_linha)
                buffer_linha = []
            
            buffer_linha.append({"text": content, "bold": is_bold})
            
    if buffer_linha:
        linhas_pdf.append(buffer_linha)

    # Mudança aqui: usamos um dicionário em vez de uma lista
    resultado_final = {}
    encontrou_inicio = False

    for chunks in linhas_pdf:
        concept_parts = []
        desc_parts = []
        
        for chunk in chunks:
            txt = chunk["text"]
            if chunk["bold"]:
                concept_parts.append(txt)
            else:
                clean_txt = txt.replace("(pop)", "").strip()
                if clean_txt and clean_txt != ",":
                    desc_parts.append(clean_txt)
        
        concept = " ".join(concept_parts).strip().strip(",; ")
        description = " ".join(desc_parts).strip().strip(",; ")
        description = re.sub(r'\s+', ' ', description)
        description = re.sub(r'\s*,\s*', ', ', description)

        if not encontrou_inicio:
            if "micrograma" in concept.lower() or "micrograma" in description.lower():
                encontrou_inicio = True
                if "micrograma" in description.lower() and not concept:
                    concept = "micrograma"
                    description = description.lower().replace("micrograma", "").strip().strip(", ")
            else:
                continue

        # Adicionando ao dicionário (a chave é o conceito)
        if concept and description:
            # O .strip() garante que não fiquem espaços sobrando na chave
            resultado_final[concept] = description

    with open(json_output, 'w', encoding='utf-8') as f:
        # Salvando o dicionário diretamente
        json.dump(resultado_final, f, ensure_ascii=False, indent=4)
    
    print(f"✅ SUCESSO! {len(resultado_final)} termos mapeados no dicionário.")
    if resultado_final:
        primeiro_termo = list(resultado_final.keys())[0]
        print(f"🚀 Exemplo: {primeiro_termo} -> {resultado_final[primeiro_termo]}")

if __name__ == "__main__":
    processar_termos_medicos()