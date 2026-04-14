import fitz
import json
import os
import re

def processar_termos_finais():
    pasta_do_script = os.path.dirname(os.path.abspath(__file__))
    os.chdir(pasta_do_script)
    
    pdf_name = "Glossário de Termos Médicos Técnicos e Populares.pdf"
    json_name = "termos.json"
    xml_name = "termos.xml"

    if not os.path.exists(pdf_name):
        print(f"❌ Erro: '{pdf_name}' não encontrado.")
        return

    print(f"⏳ A processar... O primeiro termo será 'micrograma'.")
    
    doc = fitz.open(pdf_name)
    entries = []
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<pdf2xml>']
    
    # Gatilho para ignorar o lixo do topo da página 1
    encontrou_inicio = False

    for i in range(len(doc)):
        page = doc[i]
        xml_lines.append(f'  <page number="{i+1}">')
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    line_concept = ""
                    line_description = ""
                    
                    for s in l["spans"]:
                        txt = s["text"].strip()
                        if not txt or "Glossário" in txt or "Fonte:" in txt:
                            continue
                        
                        is_bold = "Bold" in s["font"] or (s["flags"] & 2**4)
                        
                        # XML continua a registar tudo para manter a estrutura
                        clean_txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        xml_lines.append(f'    <text bold="{is_bold}">{clean_txt}</text>')
                        
                        if is_bold:
                            line_concept = txt.strip().rstrip(',')
                        else:
                            line_description += " " + txt

                    # --- FILTRO DE INÍCIO REAL ---
                    if not encontrou_inicio:
                        if "micrograma" in line_concept.lower():
                            encontrou_inicio = True
                        else:
                            continue # Salta para a próxima linha até achar o micrograma

                    if line_concept and len(line_concept) > 1:
                        entries.append({
                            "concept": line_concept,
                            "description": line_description.strip().lstrip(', '),
                            "source": "Glossário de Termos Médicos Técnicos e Populares"
                        })

        xml_lines.append('  </page>')

    xml_lines.append('</pdf2xml>')

    # Gravação
    with open(xml_name, 'w', encoding='utf-8') as f:
        f.write("\n".join(xml_lines))
    with open(json_name, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    
    doc.close()
    print(f"✅ SUCESSO!")
    if entries:
        print(f"🚀 O primeiro conceito no JSON é: '{entries[0]['concept']}'")

if __name__ == "__main__":
    processar_termos_finais()