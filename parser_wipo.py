"""
Parser melhorado para o WIPO Pearl COVID-19 Glossary
Usa pdfplumber com extração por colunas para lidar com o layout a 2 colunas
"""

import pdfplumber
import json
import re
import os

LANG_MAP = {
    "AR": "arabic",
    "DE": "german",
    "ES": "spanish",
    "FR": "french",
    "JA": "japanese",
    "KO": "korean",
    "PT": "portuguese",
    "RU": "russian",
    "ZH": "chinese",
}

LANG_CODES = set(LANG_MAP.keys())


def extract_columns(pdf_path, start_page=5):
    """
    Extrai texto respeitando o layout a 2 colunas.
    Divide cada página ao meio e extrai as duas colunas separadamente.
    """
    all_lines = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num < start_page:
                continue

            width = page.width
            mid = width / 2

            # Coluna esquerda
            left = page.crop((0, 0, mid, page.height))
            left_text = left.extract_text()

            # Coluna direita
            right = page.crop((mid, 0, width, page.height))
            right_text = right.extract_text()

            if left_text:
                all_lines.extend(left_text.split("\n"))
            if right_text:
                all_lines.extend(right_text.split("\n"))

    return all_lines


def clean_lines(lines):
    """Remove cabeçalhos, rodapés e linhas vazias."""
    skip_patterns = [
        r"^COVID-19 Glossary\s*$",
        r"^WIPO Pearl\s*$",
        r"^Multilingual Glossary\s*$",
        r"^\s*\d+\s*$",
        r"^\s*$",
        r"^A\s*$", r"^B\s*$", r"^C\s*$", r"^D\s*$",  # letras de secção
        r"^E\s*$", r"^F\s*$", r"^G\s*$", r"^H\s*$",
        r"^I\s*$", r"^L\s*$", r"^M\s*$", r"^N\s*$",
        r"^P\s*$", r"^Q\s*$", r"^R\s*$", r"^S\s*$",
        r"^T\s*$", r"^U\s*$", r"^V\s*$", r"^X\s*$",
        r"^Z\s*$",
    ]
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(re.match(p, line) for p in skip_patterns):
            continue
        cleaned.append(line)
    return cleaned


def split_into_entry_blocks(lines):
    """
    Divide as linhas em blocos de entrada.
    Uma nova entrada começa quando encontramos:
    - uma linha que parece um termo em inglês (começa com minúscula/maiúscula,
      sem prefixo de língua, não é definição de continuação)
    """
    lang_re = re.compile(r"^(AR|DE|ES|FR|JA|KO|PT|RU|ZH)\s")
    syn_re = re.compile(r"^\(syn\.\)")
    domain_re = re.compile(r"^(MEDI|SCIE|CHEM|ENVR),")
    arabic_re = re.compile(r"^[\u0600-\u06FF\u0750-\u077F]")

    # Um "termo" começa com letra maiúscula, não tem prefixo de língua
    # e não é continuação de frase (não começa em minúscula após ponto)
    def is_term_start(line):
        if not line:
            return False
        if lang_re.match(line):
            return False
        if syn_re.match(line):
            return False
        if domain_re.match(line):
            return False
        if arabic_re.match(line):
            return False
        # Deve começar com letra maiúscula
        if not line[0].isupper():
            return False
        # Não deve parecer continuação de frase (começa com maiúscula depois de espaço)
        return True

    blocks = []
    current = []

    for line in lines:
        if is_term_start(line) and current:
            # Verificar se o bloco atual tem conteúdo suficiente
            # (evitar blocos de uma única linha de definição)
            blocks.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


def parse_entry(lines):
    """Faz parse de um bloco de linhas numa entrada estruturada."""
    if not lines:
        return None

    lang_re = re.compile(r"^(AR|DE|ES|FR|JA|KO|PT|RU|ZH)\s+(.*)")
    syn_re = re.compile(r"^\(syn\.\)\s*(.*)")
    domain_re = re.compile(r"^(MEDI|SCIE|CHEM|ENVR),\s*(.*)")
    arabic_re = re.compile(r"^[\u0600-\u06FF\u0750-\u077F]")

    entry = {
        "term_en": "",
        "synonyms_en": [],
        "definition": "",
        "domain": "",
        "subdomain": "",
        "translations": {},
        "source": "WIPOPearl_COVID-19_Glossary"
    }

    i = 0

    # Linha 0: termo em inglês
    entry["term_en"] = lines[0].strip()
    i = 1

    # Linha 1 (opcional): sinónimos em inglês
    if i < len(lines) and syn_re.match(lines[i]):
        m = syn_re.match(lines[i])
        raw = m.group(1)
        # Separar por vírgula mas respeitando possíveis vírgulas dentro de nomes
        parts = re.split(r",\s*(?=\(syn\.\)|[A-Z𝑅])", raw)
        entry["synonyms_en"] = [p.strip().lstrip("(syn.) ").strip() for p in parts if p.strip()]
        i += 1

    # Linhas seguintes: definição (até domínio ou código de língua)
    def_lines = []
    while i < len(lines):
        line = lines[i]
        if domain_re.match(line):
            break
        if lang_re.match(line):
            break
        if arabic_re.match(line):
            break
        def_lines.append(line)
        i += 1

    entry["definition"] = " ".join(def_lines).strip()

    # Domínio
    if i < len(lines) and domain_re.match(lines[i]):
        m = domain_re.match(lines[i])
        entry["domain"] = m.group(1)
        entry["subdomain"] = m.group(2).strip()
        i += 1

    # Traduções (ignorar linha árabe pois é RTL e difícil de processar corretamente)
    while i < len(lines):
        line = lines[i]
        m = lang_re.match(line)
        if m:
            code = m.group(1)
            content = m.group(2).strip()
            if code != "AR" and code in LANG_MAP:
                # Separar termo principal dos sinónimos
                syn_split = re.split(r",\s*\(syn\.\)\s*", content)
                term = syn_split[0].strip()
                syns = []
                if len(syn_split) > 1:
                    # Pode haver múltiplos sinónimos separados por vírgula
                    raw_syns = syn_split[1]
                    # Concatenar linhas seguintes que ainda pertencem a este bloco de sinónimos
                    j = i + 1
                    while j < len(lines) and not lang_re.match(lines[j]) and not arabic_re.match(lines[j]):
                        # linha de continuação do sinónimo
                        if not domain_re.match(lines[j]):
                            raw_syns += " " + lines[j].strip()
                            i = j  # avançar ponteiro
                        j += 1
                    syns = [s.strip() for s in re.split(r",\s*(?=\(syn\.\)|[A-Z\u00C0-\u024F\u0400-\u04FF\u3000-\u9FFF𝑅])", raw_syns) if s.strip()]
                    syns = [s.lstrip("(syn.) ").strip() for s in syns]

                entry["translations"][LANG_MAP[code]] = {
                    "term": term,
                    "synonyms": syns
                }
        i += 1

    return entry


def main():
    pdf_path = "/mnt/user-data/uploads/WIPOPearl_COVID-19_Glossary.pdf"
    output_path = "/mnt/user-data/outputs/wipo_glossary.json"

    print("A extrair texto com suporte a 2 colunas...")
    lines = extract_columns(pdf_path, start_page=5)

    print(f"Total de linhas extraídas: {len(lines)}")

    print("A limpar linhas...")
    lines = clean_lines(lines)

    print("A dividir em blocos de entradas...")
    blocks = split_into_entry_blocks(lines)
    print(f"Blocos encontrados: {len(blocks)}")

    print("A fazer parse de cada entrada...")
    entries = []
    for block in blocks:
        entry = parse_entry(block)
        if entry and entry["term_en"] and entry["definition"]:
            entries.append(entry)

    print(f"Entradas válidas: {len(entries)}")

    output = {
        "metadata": {
            "source": "WIPO Pearl COVID-19 Glossary",
            "publisher": "World Intellectual Property Organization (WIPO)",
            "year": 2020,
            "languages": ["english"] + list(LANG_MAP.values()),
            "total_entries": len(entries)
        },
        "entries": entries
    }

    os.makedirs("/mnt/user-data/outputs", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nJSON guardado em: {output_path}")

    # Mostrar exemplo de 3 entradas bem formadas
    print("\n--- Exemplo de entradas extraídas ---")
    shown = 0
    for e in entries:
        if e["definition"] and e["translations"] and shown < 3:
            print(json.dumps(e, ensure_ascii=False, indent=2))
            print()
            shown += 1


if __name__ == "__main__":
    main()
