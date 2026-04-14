import fitz
import json
import os
import re

def limpar_xml(txt):
    if not txt: return ""
    return txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def processar_monitoramento():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    pdf_in = "m_glossario-tematico-monitoramento-e-avaliacao.pdf"
    xml_out = "monitoramento.xml"
    json_out = "monitoramento.json"

    if not os.path.exists(pdf_in):
        print(f"❌ Erro: '{pdf_in}' não encontrado.")
        return

    doc = fitz.open(pdf_in)
    entries = []
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<pdf2xml>']
    
    current_term, current_def, current_es, current_en = "", "", "", ""

    print(f"⏳ A processar páginas 21 até 80...")

    # Alterado para range(20, 80) para incluir a página 80 (índice 79)
    for i in range(20, 80):
        if i >= len(doc): break
        page = doc[i]
        xml_lines.append(f'  <page number="{i+1}">')
        
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    # 1. Analisar a linha completa para idiomas
                    texto_da_linha = "".join([s["text"] for s in l["spans"]]).strip()
                    if not texto_da_linha or "Glossário Temático" in texto_da_linha or texto_da_linha.isdigit():
                        continue
                    
                    txt_low = texto_da_linha.lower()
                    
                    # Detecção de Espanhol
                    if "espanhol" in txt_low:
                        current_es = re.sub(r'\(?em espanhol\s*:?\)?', '', texto_da_linha, flags=re.IGNORECASE).strip()
                        xml_lines.append(f'    <text type="spanish">{limpar_xml(texto_da_linha)}</text>')
                        continue
                    # Detecção de Inglês
                    elif "inglês" in txt_low or "ingles" in txt_low:
                        current_en = re.sub(r'\(?em ingl[êe]s\s*:?\)?', '', texto_da_linha, flags=re.IGNORECASE).strip()
                        xml_lines.append(f'    <text type="english">{limpar_xml(texto_da_linha)}</text>')
                        continue

                    # 2. Se não for idioma, separar spans (Negrito vs Normal)
                    for s in l["spans"]:
                        txt = s["text"].strip()
                        if not txt: continue
                        
                        is_bold = "Bold" in s["font"] or (s["flags"] & 2**4)
                        
                        if is_bold and len(txt) > 2:
                            # Se já temos um termo com dados, guardamos antes de começar o novo
                            if current_term and (current_def.strip() or current_es or current_en):
                                entries.append({
                                    "concept": current_term.strip(),
                                    "description": re.sub(r'\s+', ' ', current_def).strip(),
                                    "spanish": current_es.strip(),
                                    "english": current_en.strip(),
                                    "source": "Glossário Temático: Monitoramento e Avaliação"
                                })
                                current_term = txt
                                current_def, current_es, current_en = "", "", ""
                            else:
                                # Continuação de título
                                current_term = (current_term + " " + txt).strip()
                            xml_lines.append(f'    <text type="concept">{limpar_xml(txt)}</text>')
                        else:
                            if current_term:
                                current_def += " " + txt
                                xml_lines.append(f'    <text type="description">{limpar_xml(txt)}</text>')
        
        xml_lines.append('  </page>')

    # Guardar o último termo da página 80
    if current_term:
        entries.append({
            "concept": current_term.strip(),
            "description": re.sub(r'\s+', ' ', current_def).strip(),
            "spanish": current_es.strip(),
            "english": current_en.strip(),
            "source": "Glossário Temático: Monitoramento e Avaliação"
        })

    xml_lines.append('</pdf2xml>')
    with open(xml_out, 'w', encoding='utf-8') as f: f.write("\n".join(xml_lines))
    with open(json_out, 'w', encoding='utf-8') as f: json.dump(entries, f, ensure_ascii=False, indent=4)

    doc.close()
    print(f"✅ Concluído! Páginas 21-80 processadas.")
    print(f"📂 Gerados: {xml_out} e {json_out}")

if __name__ == "__main__":
    processar_monitoramento()