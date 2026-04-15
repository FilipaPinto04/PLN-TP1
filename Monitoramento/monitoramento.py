import xml.etree.ElementTree as ET
import json
import re

DECORATIVE_FONTS = {"4", "5", "6", "7", "8", "10", "11", "12", "13"}
TERM_FONTS = {"0", "3"}   # bold-red  ou  bold-italic-red


def nova_entrada(conceito):
    return {
        "concept": conceito,
        "classe": "",
        "sinonimos": [],
        "description": "",
        "notes": [],
        "spanish": "",
        "english": "",
    }

def e_termo(font, left):
    """Devolve True se o elemento parece o início de um novo termo."""
    if font not in TERM_FONTS:
        return False
    return (60 <= left <= 70) or (100 <= left <= 115)


def extrair_sinonimo_inline(texto):
    """
    Se o texto for 'Sin. Algo' ou 'Sin Algo', devolve lista de sinónimos.
    Trata também múltiplos sinónimos separados por ';'.
    """
    m = re.match(r'^Sin\.?\s+(.+)', texto, re.IGNORECASE)
    if m:
        partes = [p.strip().rstrip('.') for p in m.group(1).split(';')]
        return [p for p in partes if p]
    return []


def limpar_prefixo_rotulo(texto):
    """Remove ': ' ou '. ' no início do texto (valor após rótulo)."""
    return re.sub(r'^[:\s,.]+', '', texto).strip()


def processar_glossario(xml_path, json_out):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # MUDANÇA: Iniciamos como dicionário
    entries = {}
    current = None
    modo = None   
    espera_valor_rotulo = False

    for page in root.findall(".//page"):
        for t in page.findall(".//text"):
            content = "".join(t.itertext()).strip()
            font = t.get("font", "")
            left = int(t.get("left", 0))

            if font in DECORATIVE_FONTS or not content:
                continue

            # Novo TERMO
            if e_termo(font, left):
                termo = content.strip(" .,;:")
                if not termo:
                    continue
                if current:
                    # MUDANÇA: Salva no dicionário usando o conceito como chave
                    entries[current["concept"]] = current
                current = nova_entrada(termo)
                modo = "desc"
                espera_valor_rotulo = False
                continue

            if current is None:
                continue

            low = content.lower()

            # --- Lógica de processamento de fontes (font 9, 2, 1) ---
            # (Manter toda a lógica interna de processamento de 'modo' igual ao seu original)
            # ... [Omitido para brevidade, permanece idêntico ao seu script original] ...
            # ── 3. Símbolo ⇒ (font=9): este termo é uma sigla ────────────────
            if font == "9" and "⇒" in content:
                modo = "sigla"
                continue

            # ── 4. Elementos em itálico (font=2) ─────────────────────────────
            if font == "2":

                # 1. PRIORIDADE: Classe Gramatical (fem, masc, pl, misto)
                # Se for uma destas palavras isoladas, É a classe.
                if re.fullmatch(r'(fem|masc|pl|misto)(\.|\s)*', low.strip()):
                    current["classe"] = content.strip().strip('.')
                    # Importante: mudamos o modo para algo que NÃO seja desc ou sinonimo
                    # para evitar que o font 1 seguinte (pontuação) estrague tudo
                    modo = "pos_classe"
                    continue
                # SAÍDA DE EMERGÊNCIA: Se encontrarmos um rótulo conhecido, 
                # mudamos o modo IMEDIATAMENTE antes de processar.
                if re.match(r'^notas?\b', low):
                    modo = "notas"
                    # Não damos continue aqui, deixamos descer para o bloco 4d
                elif re.match(r'^em (espanhol|ingl[eê]s)', low):
                    # O modo vai ser definido nos blocos 4b/4c
                    pass 
                elif re.match(r'^ver\b', low):
                    modo = "ver" # Modo temporário para referências

                # 4f. Sinónimo (Corrigido para não comer a descrição)
                if re.search(r'\bsin\.?\b', low):
                    # Se "ver" ficou na descrição, limpamos
                    current["description"] = re.sub(r'\s*ver$', '', current["description"], flags=re.IGNORECASE).strip()
                    parts = re.split(r'sin\.?\s*', content, flags=re.IGNORECASE)
                    if len(parts) > 1 and parts[1].strip():
                        current["sinonimos"].append(parts[1].strip().rstrip('.'))
                    modo = "sinonimo"
                    continue

                # Se estamos no modo sinónimo e o texto é itálico, é continuação (ex: Metas Intermediárias)
                if modo == "sinonimo":
                    if current["sinonimos"]:
                        current["sinonimos"][-1] = (current["sinonimos"][-1] + " " + content.strip()).strip().rstrip('.')
                    else:
                        current["sinonimos"].append(content.strip().rstrip('.'))
                    continue

                if "em espanhol" in low:
                    modo = "espanhol"
                    valor = re.sub(r'^em espanhol\s*:?\s*', '', content, flags=re.IGNORECASE).strip()
                    if valor: current["spanish"] = (current["spanish"] + " " + valor).strip()
                    espera_valor_rotulo = False
                    continue

                if "em inglês" in low or "em ingles" in low:
                    modo = "ingles"
                    valor = re.sub(r'^em ingl[eê]s\s*:?\s*', '', content, flags=re.IGNORECASE).strip()
                    if valor: current["english"] = (current["english"] + " " + valor).strip()
                    espera_valor_rotulo = False
                    continue

                # E. SIGLA (Vai para a descrição)
                if modo == "sigla":
                    alvo = content.strip().rstrip('.')
                    if alvo:
                        prefixo = "⇒ "
                        current["description"] = (current["description"] + " " + prefixo + alvo).strip()
                    modo = "desc"
                    continue

                # F. NOTAS E VER
                if re.match(r'^notas?\b', low):
                    modo = "notas"
                    continue

                if re.match(r'^ver\b', low):
                    ref = content.strip().rstrip('.')
                    if modo == "notas":
                        current["notes"].append(ref) if not current["notes"] else current["notes"][-1] + " " + ref
                    else:
                        current["description"] = (current["description"] + " " + ref).strip()
                    continue

                # G. TRADUÇÕES SEM RÓTULO (Continuações em itálico)
                if modo in ("espanhol", "ingles"):
                    lang_key = "spanish" if modo == "espanhol" else "english"
                    current[lang_key] = (current[lang_key] + " " + content.strip()).strip()
                    continue

                # H. ITÁLICO GENÉRICO (Só entra aqui se não for nada do acima)
                clean = limpar_prefixo_rotulo(content)
                if not clean: continue
                if modo == "notas":
                    if current["notes"]: current["notes"][-1] = (current["notes"][-1] + " " + clean).strip()
                    else: current["notes"].append(clean)
                else:
                    current["description"] = (current["description"] + " " + clean).strip()
                continue

            # ── 5. Texto normal (font=1): conteúdo/valores ───────────────────
            if font == "1":
                # A. Captura pontuação isolada (Mantém o ";" em Accountability)
                if re.fullmatch(r'[\s,\.;:]+', content):
                    if modo in ("espanhol", "ingles"):
                        lang_key = "spanish" if modo == "espanhol" else "english"
                        current[lang_key] += content
                    continue

                clean = limpar_prefixo_rotulo(content)
                if not clean:
                    continue

                # B. Lógica de SINÓNIMO (Saída para Descrição)
                if modo == "sinonimo":
                    # Se o texto começa com letra maiúscula e é longo, 
                    # ou se começa com ". ", é a descrição a começar.
                    if (len(clean) > 15 and clean[0].isupper()) or content.startswith(". "):
                        modo = "desc"
                        # Não fazemos continue para ele cair no bloco de descrição abaixo
                    else:
                        if current["sinonimos"]:
                            current["sinonimos"][-1] = (current["sinonimos"][-1] + " " + clean).strip()
                        else:
                            current["sinonimos"].append(clean)
                        continue

                # C. TRADUÇÕES (Acumulação robusta)
                if modo == "espanhol":
                    current["spanish"] = (current["spanish"] + " " + clean).strip()
                    continue
                if modo == "ingles":
                    current["english"] = (current["english"] + " " + clean).strip()
                    continue

                # D. NOTAS (Mantendo a tua lógica de itens i, ii, a, b)
                if modo == "notas":
                    # Detecta i), ii), a), b) etc.
                    if re.match(r'^([ivxlcdm]+\)|[a-z]\))', clean.lower()):
                        current["notes"].append(clean)
                    elif current["notes"]:
                        current["notes"][-1] = (current["notes"][-1] + " " + clean).strip()
                    else:
                        current["notes"].append(clean)
                    continue

                # E. DESCRIÇÃO (Modo Geral)
                # Verifica se o modo é "ver" (referência) ou "desc"
                if not current["description"].endswith(clean):
                    current["description"] = (current["description"] + " " + clean).strip()
                continue

    if current:
        # MUDANÇA: Salva o último termo no dicionário
        entries[current["concept"]] = current

    # ── Pós-processamento ────────────────────────────────────────────────────
    # MUDANÇA: Iteramos sobre os valores do dicionário
    for e in entries.values():
        e["description"] = re.sub(r'\s+', ' ', e["description"]).strip().lstrip('. ')
        
        for s in e["sinonimos"]:
            if e["description"].startswith(s):
                e["description"] = e["description"][len(s):].strip().lstrip('. ')

        e["notes"] = [re.sub(r'\s+', ' ', n).strip().lstrip(': ') for n in e["notes"] if n.strip()]

        for lang in ["spanish", "english"]:
            val = e[lang].strip().lstrip(': ')
            val = re.sub(r'\.+$', '', val)
            e[lang] = val.strip()

        e["sinonimos"] = [s.strip().rstrip('.') for s in e["sinonimos"] if s.strip()]
        e["classe"] = e["classe"].strip().strip('.')

    with open(json_out, "w", encoding="utf-8") as f:
        # MUDANÇA: O arquivo agora conterá o objeto entries (dicionário)
        json.dump(entries, f, ensure_ascii=False, indent=4)

    print(f"✓ {len(entries)} entradas extraídas → {json_out}")

if __name__ == "__main__":
    processar_glossario(
        "m_glossario-tematico-monitoramento-e-avaliacao.xml",
        "monitoramento.json"
    )