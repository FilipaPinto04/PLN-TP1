import xml.etree.ElementTree as ET
import re
import json
import os

XML_PATH = "ossos.xml"
JSON_OUT = "ossos.json"

def processar_hierarquia_ossos(caminho_xml):
    # Regex de hierarquia
    CAT_RE = re.compile(r"^(SISTEMA\s+[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ\s]+)$")
    DOM_RE = re.compile(r"^\d+\.\s+([A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ\s]+)$")
    SEC_RE = re.compile(r"^(\d+(?:\.\d+)+)\.?\s*(.+)$")
    LEG_RE = re.compile(r"^([a-z]{1,2}[1-9]?)\)\s+(.+)$")
    
    # Termos de ruído para remoção total, mesmo que estejam colados ao texto
    BAD_STRINGS = [
        "Anatomia na prática:", "Anatomia na pr", "nA práticA", "nAtomiA", 
        "iStemA", "m uSculoeSquelético", "uSculoeSquelético", "SUMÁRIO", "GABARITO"
    ]

    entradas = []
    current_cat = ""
    current_dom = ""
    cur_sec = None

    try:
        tree = ET.parse(XML_PATH)
        root = tree.getroot()

        for page in root.findall("page"):
            for text_node in page.findall("text"):
                # Filtro por Posição: O texto lateral está geralmente em left > 1100
                left_pos = int(text_node.get("left", 0))
                if left_pos > 1100:
                    continue

                content = "".join(text_node.itertext()).strip()
                
                # Limpeza agressiva: remove as strings de ruído de dentro do conteúdo
                for bad in BAD_STRINGS:
                    content = content.replace(bad, "").strip()

                if not content or content.isdigit():
                    continue

                # 1. Detetar Categoria
                if CAT_RE.match(content):
                    current_cat = content
                    continue

                # 2. Detetar Domínio
                dm = DOM_RE.match(content)
                if dm:
                    current_dom = dm.group(1).strip()
                    continue

                # 3. Detetar Termo
                sm = SEC_RE.match(content)
                if sm:
                    if cur_sec: entradas.append(cur_sec)
                    cur_sec = {
                        "id": f"osso_{len(entradas):04d}",
                        "categoria": current_cat,
                        "dominio": current_dom,
                        "termo": sm.group(2).strip(),
                        "codigo_sec": sm.group(1),
                        "estruturas": []
                    }
                    continue

                # 4. Detetar Estruturas
                lm = LEG_RE.match(content)
                if lm and cur_sec:
                    cur_sec["estruturas"].append({
                        "letra": lm.group(1),
                        "nome": lm.group(2).strip()
                    })
                    continue
                
                # 5. Lógica de Continuação
                if cur_sec and cur_sec["estruturas"] and content[0].islower():
                    # Verifica se o que sobrou não é apenas lixo
                    if len(content) > 1:
                        cur_sec["estruturas"][-1]["nome"] += " " + content

        if cur_sec: entradas.append(cur_sec)

        resultado = {
            "metadata": {"fonte": "Anatomia_na_Pratica_2015", "total_entradas": len(entradas)},
            "entradas": entradas
        }

        with open(JSON_OUT, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        
        print(f"Sucesso: JSON filtrado gerado.")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    processar_hierarquia_ossos(XML_PATH)