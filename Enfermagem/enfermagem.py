import fitz
import xml.etree.ElementTree as ET
import json
import os
import re

def processar_tudo():
    # 1. Configurar caminhos (Garante que funciona em qualquer pasta)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_dir, "Glossário de Enfermagem.pdf")
    xml_path = os.path.join(base_dir, "enfermagem.xml")
    json_path = os.path.join(base_dir, "enfermagem.json")

    if not os.path.exists(pdf_path):
        print(f"❌ Erro: Coloca o PDF na pasta: {base_dir}")
        return

    # --- ETAPA 3: GERAR XML ESTRUTURADO ---
    print("⏳ A gerar XML (Páginas 24-114)...")
    doc = fitz.open(pdf_path)
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<pdf2xml>']

    for i in range(23, 114): # Índice 0: pág 24 a 114
        pagina = doc[i]
        xml_lines.append(f'  <page number="{i+1}">')
        
        # Separar por colunas físicas para não misturar texto
        blocos = pagina.get_text("dict")["blocks"]
        esq, direita = [], []
        
        for b in blocos:
            if "lines" in b:
                for linha in b["lines"]:
                    for span in linha["spans"]:
                        txt = span["text"].strip()
                        if not txt or "GLOSSÁRIO" in txt or "Página" in txt: continue
                        
                        left = span["bbox"][0]
                        is_bold = "Bold" in span["font"] or span["flags"] & 2**4
                        clean_txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        
                        item = f'    <text left="{int(left)}" bold="{is_bold}">{clean_txt}</text>'
                        if left < 300: esq.append(item)
                        else: direita.append(item)
        
        xml_lines.extend(esq)
        xml_lines.extend(direita)
        xml_lines.append('  </page>')
    
    xml_lines.append('</pdf2xml>')
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(xml_lines))

    # --- ETAPA 5 & 6: EXTRAIR PARA JSON ---
    print("⏳ A processar XML para JSON...")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    entries = []
    current_term, current_def = "", []

    for text in root.iter('text'):
        txt = text.text.strip()
        is_bold = text.get('bold') == 'True'

        if txt.startswith("FONTE:") or "http" in txt:
            if current_term and current_def:
                entries.append({
                    "concept": current_term.strip().rstrip(','),
                    "description": " ".join(current_def).strip(),
                    "source": "Glossário de Enfermagem"
                })
                current_term, current_def = "", []
            continue

        if is_bold and len(txt) > 2:
            if current_term and current_def:
                entries.append({
                    "concept": current_term.strip().rstrip(','),
                    "description": " ".join(current_def).strip(),
                    "source": "Glossário de Enfermagem"
                })
                current_term, current_def = txt, []
            else:
                current_term = (current_term + " " + txt).strip() if not current_def else txt
        else:
            if current_term: current_def.append(txt)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    
    print(f"✅ CONCLUÍDO! Extraídos {len(entries)} termos.")
    print(f"📂 Ficheiro gerado: {json_path}")

if __name__ == "__main__":
    processar_tudo()