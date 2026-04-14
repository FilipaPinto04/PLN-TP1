import fitz
import json
import os
import re

def limpar_xml(txt):
    if not txt: return ""
    return txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def processar():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    pdf_in = "glossario_neologismos_saude.pdf"
    xml_out = "neologismos.xml"
    json_out = "neologismos.json"

    if not os.path.exists(pdf_in):
        print(f"❌ Erro: '{pdf_in}' não encontrado.")
        return

    doc = fitz.open(pdf_in)
    entries = []
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<pdf2xml>']
    
    current_term = ""
    current_def = ""

    print(f"⏳ A limpar títulos e extrair neologismos (Pág 87-183)...")

    for i in range(86, 183):
        if i >= len(doc): break
        page = doc[i]
        xml_lines.append(f'  <page number="{i+1}">')
        
        # 1. Extrair e ordenar spans por coluna (X) e altura (Y)
        spans = []
        for b in page.get_text("dict")["blocks"]:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        spans.append({
                            "text": s["text"].strip(),
                            "x": s["bbox"][0],
                            "y": s["bbox"][1],
                            "font": s["font"],
                            "flags": s["flags"]
                        })

        # Divisor de colunas em X=290
        spans.sort(key=lambda s: (s["x"] > 290, s["y"]))

        for s in spans:
            txt = s["text"]
            
            # --- FILTROS DE EXCLUSÃO ---
            if not txt or "Glossário" in txt or txt.isdigit():
                continue
            
            # FILTRO CRÍTICO: Ignora "3.2.", "3.2.1", etc.
            if re.match(r'^\d+(\.\d+)+', txt):
                continue
                
            # Ignora letras capitulares do índice (A, B, C...)
            if len(txt) == 1 and txt.isupper():
                continue

            is_bold = "Bold" in s["font"] or (s["flags"] & 2**4)
            # Margem onde os conceitos (abeta, etc) começam
            e_margem = (s["x"] < 80) or (290 < s["x"] < 330)

            if is_bold and e_margem:
                # Se encontrarmos um novo conceito, salvamos o acumulado
                if current_term:
                    entries.append({
                        "concept": current_term.strip(),
                        "description": re.sub(r'\s+', ' ', current_def).strip(),
                        "source": "Glossário de Neologismos da Saúde"
                    })
                current_term = txt
                current_def = ""
                tipo = "concept"
            else:
                if current_term:
                    current_def += " " + txt
                tipo = "description"

            xml_lines.append(f'    <text type="{tipo}" x="{s["x"]:.1f}">{limpar_xml(txt)}</text>')
        
        xml_lines.append('  </page>')

    # Salvar o último
    if current_term:
        entries.append({"concept": current_term.strip(), "description": current_def.strip(), "source": "Glossário de Neologismos da Saúde"})

    xml_lines.append('</pdf2xml>')

    with open(xml_out, 'w', encoding='utf-8') as f: f.write("\n".join(xml_lines))
    with open(json_out, 'w', encoding='utf-8') as f: json.dump(entries, f, ensure_ascii=False, indent=4)

    doc.close()
    print(f"✅ SUCESSO! O primeiro termo agora deve ser 'abeta'.")

if __name__ == "__main__":
    processar()