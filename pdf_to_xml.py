import subprocess
import sys
import os

def pdf_to_xml(pdf_path: str, xml_path: str = None) -> str:
    """
    Converte um ficheiro PDF para XML usando pdftohtml.
    Devolve o caminho do ficheiro XML gerado.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Ficheiro PDF não encontrado: {pdf_path}")

    if xml_path is None:
        xml_path = os.path.splitext(pdf_path)[0] + ".xml"

    print(f"A converter '{pdf_path}' para XML...")
    result = subprocess.run(
        ["pdftohtml", "-xml", pdf_path, xml_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Erro ao converter PDF:\n{result.stderr}")

    print(f"XML gerado: {xml_path}")
    return xml_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pdf_to_xml.py <ficheiro.pdf> [saida.xml]")
        sys.exit(1)

    pdf = sys.argv[1]
    xml = sys.argv[2] if len(sys.argv) > 2 else None
    pdf_to_xml(pdf, xml)
