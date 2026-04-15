import json
import os
from collections import OrderedDict

def consolidar_dados():
    dicionario_final = {}
    
    # Mapeamento conforme a tua estrutura de pastas [cite: 13]
    ficheiros = {
        "Medicina/medicina.json": "medicina.pdf",
        "Enfermagem/enfermagem.json": "enfermagem.pdf",
        "Ossos/ossos.json": "ossos.pdf",
        "ICNP/ICNP.json": "ICNP.pdf",
        "Neologismos/neologismos.json": "neologismos.pdf",
        "Termos/termos.json": "termos.pdf",
        "Ministerio/ministerio.json": "ministerio.pdf",
        "Monitoramento/monitoramento.json": "monitoramento.pdf",
        "Wipo/wipo.json": "wipo.pdf"
    }

    for caminho, fonte_pdf in ficheiros.items():
        if not os.path.exists(caminho):
            continue
            
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        nome_f = os.path.basename(caminho)

        # Normalização de dados para iterar conforme o formato do JSON [cite: 14, 15]
        if nome_f == "medicina.json":
            itens = [{"termo_bruto": k, **v} for k, v in dados.items()]
        elif "entradas" in dados:
            itens = dados["entradas"]
        elif isinstance(dados, list):
            itens = dados
        else:
            itens = [{"termo_bruto": k, **v} for k, v in dados.items()]

        for item in itens:
            # Lógica de Pivot para encontrar o termo em Português [cite: 17]
            traducoes = item.get("traducoes", {})
            t_original = item.get("termo_bruto") or item.get("concept") or item.get("term") or item.get("termo")
            
            # Prioridade para o termo em PT para facilitar o cruzamento
            termo_pt = (traducoes.get("pt") or traducoes.get("portugues") or t_original)
            if not termo_pt: continue
            
            # Limpeza e normalização da chave [cite: 16]
            chave = str(termo_pt).split(';')[0].strip().lower()

            if chave not in dicionario_final:
                dicionario_final[chave] = {
                    "conceito": chave,
                    "fontes_unicas": set(), # Usamos set para não repetir a mesma fonte
                    "dados": []
                }
            
            # Adicionar a informação e registar a fonte
            dicionario_final[chave]["fontes_unicas"].add(fonte_pdf)
            dicionario_final[chave]["dados"].append({
                "fonte": fonte_pdf,
                "info": item
            })

    # --- Lógica de Ordenação ---
    # Ordenamos os itens: primeiro os que aparecem em mais ficheiros (len das fontes_unicas)
    itens_ordenados = sorted(
        dicionario_final.items(), 
        key=lambda x: len(x[1]["fontes_unicas"]), 
        reverse=True
    )

    # Converter de volta para dicionário preservando a ordem (OrderedDict)
    resultado_final = OrderedDict()
    for chave, valor in itens_ordenados:
        # Converter o set de fontes para lista para ser serializável em JSON [cite: 18]
        valor["total_fontes"] = len(valor["fontes_unicas"])
        valor["fontes_unicas"] = list(valor["fontes_unicas"])
        resultado_final[chave] = valor

    # Guardar o ficheiro JSON final [cite: 8, 18, 29]
    with open('dicionario_biomedico_final.json', 'w', encoding='utf-8') as f:
        json.dump(resultado_final, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Sucesso! O JSON foi ordenado por cruzamento de dados.")

if __name__ == "__main__":
    consolidar_dados()