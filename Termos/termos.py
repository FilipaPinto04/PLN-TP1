import xml.etree.ElementTree as ET
import json
import os
import re

def processar_termos_medicos(xml_input="termos.xml", json_output="termos.json"):
    if not os.path.exists(xml_input):
        print(f"❌ Erro: '{xml_input}' não encontrado.")
        return

    print(f"⏳ Processando XML através de segmentação por margem...")
    
    try:
        tree = ET.parse(xml_input)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Erro ao ler XML: {e}")
        return

    # 1. Agrupar chunks de texto por "entradas" (linhas do PDF)
    # No seu PDF, cada entrada nova começa na margem esquerda (left=128)
    linhas_pdf = []
    buffer_linha = []
    MARGEM_ESQUERDA = 135 # Valor de segurança baseado no seu left=128

    for page in root.findall(".//page"):
        for t in page.findall(".//text"):
            content = "".join(t.itertext())
            left = int(t.get("left", 0))
            is_bold = (t.find("b") is not None) or (t.get("font") in ["0", "1", "3"])
            
            # Se voltamos à margem esquerda, começou uma nova linha/termo no PDF
            if left < MARGEM_ESQUERDA and buffer_linha:
                linhas_pdf.append(buffer_linha)
                buffer_linha = []
            
            buffer_linha.append({"text": content, "bold": is_bold})
            
    if buffer_linha:
        linhas_pdf.append(buffer_linha)

    # 2. Processar cada linha para extrair Conceito e Descrição
    entries = []
    encontrou_inicio = False

    for chunks in linhas_pdf:
        concept_parts = []
        desc_parts = []
        
        for chunk in chunks:
            txt = chunk["text"]
            if chunk["bold"]:
                concept_parts.append(txt)
            else:
                # Remove o marcador (pop) e limpa pontuação
                clean_txt = txt.replace("(pop)", "").strip()
                if clean_txt and clean_txt != ",":
                    desc_parts.append(clean_txt)
        
        # Limpeza final das strings
        concept = " ".join(concept_parts).strip().strip(",; ")
        description = " ".join(desc_parts).strip().strip(",; ")
        # Normaliza espaços duplos e vírgulas coladas
        description = re.sub(r'\s+', ' ', description)
        description = re.sub(r'\s*,\s*', ', ', description)

        # --- FILTRO DE INÍCIO (MICROGRAMA) ---
        if not encontrou_inicio:
            # Verifica se micrograma aparece em qualquer parte da linha
            if "micrograma" in concept.lower() or "micrograma" in description.lower():
                encontrou_inicio = True
                # Ajuste para o primeiro caso (Desc, Concept)
                if "micrograma" in description.lower() and not concept:
                    concept = "micrograma"
                    description = description.lower().replace("micrograma", "").strip().strip(", ")
            else:
                continue

        if concept and description:
            entries.append({
                "concept": concept,
                "description": description,
                "source": "Glossário de Termos Médicos Técnicos e Populares"
            })

    # 3. Gravação e Desduplicação
    # O PDF inverte termos (A->B e B->A), vamos manter apenas um de cada
    vistos = set()
    resultado_final = []
    for e in entries:
        key = e["concept"].lower()
        if key not in vistos:
            resultado_final.append(e)
            vistos.add(key)

    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(resultado_final, f, ensure_ascii=False, indent=4)
    
    print(f"✅ SUCESSO! {len(resultado_final)} termos extraídos sem misturas.")
    if resultado_final:
        print(f"🚀 Primeiro termo: {resultado_final[0]['concept']} -> {resultado_final[0]['description']}")

if __name__ == "__main__":
    processar_termos_medicos()