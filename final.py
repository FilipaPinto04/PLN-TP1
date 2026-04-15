# Consolida todos os dicionários JSON num único ficheiro, cruzando informação pelo termo em português.

import json
import os
import re
from collections import defaultdict

# Configuração — caminhos conforme a estrutura de pastas

BASE = os.path.dirname(os.path.abspath(__file__))

FICHEIROS = {
    "medicina":      os.path.join(BASE, "Medicina",      "medicina.json"),
    "wipo":          os.path.join(BASE, "Wipo",          "wipo.json"),
    "ICNP":          os.path.join(BASE, "ICNP",          "ICNP.json"),
    "catala":        os.path.join(BASE, "DiMulti",       "dicionario_catala.json"),
    "enfermagem":    os.path.join(BASE, "Enfermagem",    "enfermagem.json"),
    "ministerio":    os.path.join(BASE, "Ministerio",    "ministerio.json"),
    "monitoramento": os.path.join(BASE, "Monitoramento", "monitoramento.json"),
    "neologismos":   os.path.join(BASE, "Neologismos",   "neologismos.json"),
    "ossos":         os.path.join(BASE, "Ossos",         "ossos.json"),
    "termos":        os.path.join(BASE, "Termos",        "termos.json"),
}

OUTPUT = os.path.join(BASE, "dicionario_final.json")

# Normalização

def normalizar(texto):
    if not texto:
        return ""
    t = str(texto).lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*\[.*?\]", "", t)  
    t = re.sub(r"\(syn\.\).*", "", t) 
    t = t.split(";")[0].strip()
    t = t.strip(".,;:").strip()
    return t

def chaves_validas(chave):
    invalidas = {"la", "en", "es", "pt", "fr", "de", "ar", "nl", "ja", "ko","zh", "ru", "oc", "eu", "gl", "it", "pl", "s.f.", "s.m."}
    if len(chave) < 3:
        return False
    if chave in invalidas:
        return False
    if chave.isdigit():
        return False
    return True


# Extractores 

def extrair_medicina(dados):
    resultados = []
    for termo_gl, info in dados.items():
        trad = info.get("traducoes", {})
        pt_raw = trad.get("pt", "")
        termos_pt = [normalizar(t) for t in str(pt_raw).split(";") if t.strip()]
        if not termos_pt:
            termos_pt = [normalizar(termo_gl)]
        for chave in termos_pt:
            if chave and chaves_validas(chave):
                resultados.append((chave, {
                    "termo_original": termo_gl,
                    "id":        str(info.get("id", "")),
                    "genero":    info.get("genero", ""),
                    "categoria": info.get("categoria", ""),
                    "traducoes": trad,
                    "sinonimos": info.get("sinonimos", []),
                    "variantes": info.get("variantes", []),
                    "nota":      info.get("nota", ""),
                }))
    return resultados


def extrair_wipo(dados):
    resultados = []
    for e in dados.get("entradas", []):
        trad = e.get("traducoes", {})
        pt_raw = trad.get("portugues", "")
        termos_pt = [normalizar(t) for t in str(pt_raw).split(";") if t.strip()]
        if not termos_pt:
            termos_pt = [normalizar(e.get("termo_en", ""))]
        for chave in termos_pt:
            if chave and chaves_validas(chave):
                resultados.append((chave, {
                    "termo_en":    e.get("termo_en", ""),
                    "definicao":   e.get("definicao_en", ""),
                    "area":        e.get("categoria", ""),
                    "pagina":      e.get("pagina", ""),
                    "traducoes":   trad,
                }))
    return resultados


def extrair_icnp(dados):
    resultados = []
    for e in dados.get("entradas", []):
        chave = normalizar(e.get("term", ""))
        if chave and chaves_validas(chave):
            resultados.append((chave, {
                "code":        e.get("code", ""),
                "axis":        e.get("axis", ""),
                "term":        e.get("term", ""),
                "description": e.get("description", ""),
            }))
    return resultados


def extrair_catala(dados):
    resultados = []
    for termo_ca, info in dados.items():
        eq = info.get("equivalentes", {})
        pt_info = eq.get("pt") or eq.get("pt [PT]") or eq.get("pt [BR]") or {}
        pt_raw  = pt_info.get("termo", "") if isinstance(pt_info, dict) else ""
        termos_pt = [normalizar(t) for t in str(pt_raw).split(";") if t.strip()]
        if not termos_pt:
            termos_pt = [normalizar(termo_ca)]
        for chave in termos_pt:
            if chave and chaves_validas(chave):
                resultados.append((chave, {
                    "id":               info.get("id", ""),
                    "termo_ca":         termo_ca,
                    "classe_gramatical": info.get("classe_gramatical", ""),
                    "definicao":        info.get("definicao", ""),
                    "equivalentes":     eq,
                    "notas":            info.get("notas", []),
                }))
    return resultados


def extrair_enfermagem(dados):
    resultados = []
    for termo, info in dados.items():
        chave = normalizar(termo)
        if chave and chaves_validas(chave):
            resultados.append((chave, {
                "termo":    termo,
                "descricao": info.get("descricao", "") if isinstance(info, dict) else str(info),
                "fonte":    info.get("fonte", "") if isinstance(info, dict) else "",
            }))
    return resultados


def extrair_ministerio(dados):
    resultados = []
    for termo, info in dados.items():
        chave = normalizar(termo)
        if chave and chaves_validas(chave):
            resultados.append((chave, {
                "termo":      termo,
                "categoria":  info.get("categoria", "") if isinstance(info, dict) else "",
                "descricao":  info.get("descricao", "") if isinstance(info, dict) else str(info),
                "referencia": info.get("referencia", "") if isinstance(info, dict) else "",
            }))
    return resultados


def extrair_monitoramento(dados):

    resultados = []
    for termo, info in dados.items():
        chave = normalizar(termo)
        if chave and chaves_validas(chave):
            resultados.append((chave, {
                "termo":       termo,
                "classe":      info.get("classe", ""),
                "description": info.get("description", ""),
                "sinonimos":   info.get("sinonimos", []),
                "notes":       info.get("notes", []),
                "spanish":     info.get("spanish", ""),
                "english":     info.get("english", ""),
            }))
    return resultados


def extrair_neologismos(dados):
    resultados = []
    for termo, info in dados.items():
        chave = normalizar(termo)
        if chave and chaves_validas(chave):
            resultados.append((chave, {
                "termo":            termo,
                "grammar_category": info.get("grammar_category", ""),
                "term_en":          info.get("term_en", ""),
                "term_es":          info.get("term_es", ""),
                "definition":       info.get("definition", ""),
                "inf_encicl":       info.get("inf_encicl", ""),
                "source":           info.get("source", ""),
            }))
    return resultados


def extrair_ossos(dados):
    resultados = []
    for e in dados.get("entradas", []):
        chave = normalizar(e.get("termo", ""))
        if chave and chaves_validas(chave):
            resultados.append((chave, {
                "id":        e.get("id", ""),
                "categoria": e.get("categoria", ""),
                "dominio":   e.get("dominio", ""),
                "termo":     e.get("termo", ""),
                "codigo":    e.get("codigo_sec", ""),
                "estruturas": e.get("estruturas", []),
            }))
    return resultados


def extrair_termos(dados):
    resultados = []
    for termo, definicao in dados.items():
        chave = normalizar(termo)
        if chave and chaves_validas(chave):
            resultados.append((chave, {
                "termo":    termo,
                "descricao": str(definicao),
            }))
    return resultados


# Mapeamento fonte - extractor

EXTRACTORS = {
    "medicina":      extrair_medicina,
    "wipo":          extrair_wipo,
    "ICNP":          extrair_icnp,
    "catala":        extrair_catala,
    "enfermagem":    extrair_enfermagem,
    "ministerio":    extrair_ministerio,
    "monitoramento": extrair_monitoramento,
    "neologismos":   extrair_neologismos,
    "ossos":         extrair_ossos,
    "termos":        extrair_termos,
}

# Pipeline principal

def consolidar():

    todas_entradas     = defaultdict(lambda: {"fontes": [], "dados": {}})
    contagem_por_fonte = {}
    fontes_carregadas  = []

    # Carregar e extrair
    for nome, caminho in FICHEIROS.items():
        if not os.path.exists(caminho):
            continue

        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)

        extractor = EXTRACTORS.get(nome)
        if not extractor:
            continue

        pares = extractor(dados)
        contagem_por_fonte[nome] = len(pares)
        fontes_carregadas.append(nome)

        for chave, entry in pares:
            todas_entradas[chave]["fontes"].append(nome)
            if nome not in todas_entradas[chave]["dados"]:
                todas_entradas[chave]["dados"][nome] = entry

    # Calcular estatísticas
    total_termos   = len(todas_entradas)
    so_uma_fonte   = sum(1 for v in todas_entradas.values() if len(set(v["fontes"])) == 1)
    duas_ou_mais   = sum(1 for v in todas_entradas.values() if len(set(v["fontes"])) >= 2)
    tres_ou_mais   = sum(1 for v in todas_entradas.values() if len(set(v["fontes"])) >= 3)
    max_cruzamento = max(len(set(v["fontes"])) for v in todas_entradas.values())

    pares_fontes = defaultdict(int)
    for v in todas_entradas.values():
        fontes = sorted(set(v["fontes"]))
        for i in range(len(fontes)):
            for j in range(i + 1, len(fontes)):
                pares_fontes[(fontes[i], fontes[j])] += 1

    top_pares = sorted(pares_fontes.items(), key=lambda x: x[1], reverse=True)[:10]

    top_termos = sorted(
        todas_entradas.items(),
        key=lambda x: len(set(x[1]["fontes"])),
        reverse=True
    )[:20]

    dist_fontes = defaultdict(int)
    for v in todas_entradas.values():
        dist_fontes[len(set(v["fontes"]))] += 1

    # Escrever estatísticas
    nome_arquivo = "estatisticas.txt"

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write("\n")
        f.write("   ESTATÍSTICAS\n")
        f.write("\n")
        f.write(f"  Total de termos únicos:           {total_termos:>6}\n")
        f.write(f"  Termos em apenas 1 fonte:        {so_uma_fonte:>6}  ({so_uma_fonte*100//total_termos}%)\n")
        f.write(f"  Termos em 2+ fontes (cruzados):  {duas_ou_mais:>6}  ({duas_ou_mais*100//total_termos}%)\n")
        f.write(f"  Termos em 3+ fontes:             {tres_ou_mais:>6}  ({tres_ou_mais*100//total_termos}%)\n")
        f.write(f"  Máximo de fontes num só termo:   {max_cruzamento:>6}\n")
        f.write("\n")
    
        f.write("  Quantidade de termos extraídos por fonte:\n")
        
        for fonte, qtd in sorted(contagem_por_fonte.items(), key=lambda x: x[1], reverse=True):
            f.write(f"    {fonte:<25}: {qtd:>6} termos\n")
        
        f.write("\n")

        f.write("\n")
        f.write("  Top pares de fontes com mais termos em comum:\n")
        for par, count in top_pares:
            f.write(f"    {par[0]:<16} ↔ {par[1]:<16}  {count:>4} termos\n")
        
        f.write("\n")
        f.write("  Top 10 termos mais cruzados:\n")
        for termo, v in top_termos[:10]:
            f.write(f"    '{termo}' → {sorted(set(v['fontes']))}\n")
        f.write("\n")

    print(f"Relatório gerado com sucesso em: {nome_arquivo}")

    # 4. Dicionário final 
    dicionario_final = sorted(
        todas_entradas.items(),
        key=lambda x: (-len(set(x[1]["fontes"])), x[0])
    )

    resultado = {
        termo: {
            "total_fontes": len(set(v["fontes"])),
            "fontes":       sorted(set(v["fontes"])),
            "dados":        v["dados"],
        }
        for termo, v in dicionario_final
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f" Ficheiro guardado: {OUTPUT}")


if __name__ == "__main__":
    consolidar()