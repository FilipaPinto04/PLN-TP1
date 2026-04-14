import fitz
import json
import os
import re

def processar_ministerio():
    pasta_do_script = os.path.dirname(os.path.abspath(__file__))
    os.chdir(pasta_do_script)
    
    pdf_name = "glossario_ministerio_saude.pdf"
    json_name = "ministerio.json"

    if not os.path.exists(pdf_name):
        print(f"❌ Erro: Ficheiro não encontrado.")
        return

    print(f"⏳ A extrair... Foco total na 'Abordagem médica'.")
    
    doc = fitz.open(pdf_name)
    entries = []
    current_term = ""
    current_def = ""
    comecou_realmente = False

    for i in range(14, 112): # Pág 15 a 112
        page = doc[i]
        # Obter spans e garantir que estão ordenados pela posição na página
        blocks = page.get_text("dict")["blocks"]
        spans = []
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        spans.append(s)

        for s in spans:
            txt = s["text"].strip()
            if not txt or "Glossário" in txt or "Página" in txt:
                continue

            is_bold = "Bold" in s["font"] or s["flags"] & 2**4

            # GATILHO DE INÍCIO
            if not comecou_realmente:
                if "Abordagem" in txt and is_bold:
                    comecou_realmente = True
                    current_term = txt
                    continue
                else:
                    continue 

            if is_bold:
                # Se já temos uma definição a decorrer e aparece um NOVO negrito
                if current_term and current_def.strip():
                    entries.append({
                        "concept": current_term.strip().rstrip(','),
                        "description": re.sub(r'\s+', ' ', current_def).strip(),
                        "source": "Ministério da Saúde",
                        "type": "technical_term"
                    })
                    current_term = txt
                    current_def = ""
                else:
                    # Se for negrito mas ainda não temos definição, 
                    # pode ser a continuação do título (ex: "Abordagem" + "médica")
                    current_term = (current_term + " " + txt).strip()
            else:
                # Se não é negrito, é obrigatoriamente descrição
                if current_term:
                    current_def += " " + txt

    # Guardar o último termo
    if current_term and current_def:
        entries.append({
            "concept": current_term.strip().rstrip(','),
            "description": re.sub(r'\s+', ' ', current_def).strip(),
            "source": "Ministério da Saúde",
            "type": "technical_term"
        })

    doc.close()

    with open(json_name, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    
    if entries:
        print(f"✅ SUCESSO! Primeiro termo: {entries[0]['concept']}")
        print(f"📝 Descrição do 1º termo: {entries[0]['description'][:50]}...")
    else:
        print("⚠️ Aviso: Nenhum termo foi extraído.")

if __name__ == "__main__":
    processar_ministerio()