import subprocess
import sys
import os

def pdf_to_xml(pdf_path: str, xml_path: str = None, first_page: int = None, last_page: int = None) -> str:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Ficheiro PDF não encontrado: {pdf_path}")

    if xml_path is None:
        xml_path = os.path.splitext(pdf_path)[0] + ".xml"

    # ADICIONADO O FLAG '-i' para ignorar imagens e não encher a pasta de lixo
    command = ["pdftohtml", "-xml", "-noframes", "-i"]
    
    if first_page:
        command.extend(["-f", str(first_page)])
    if last_page:
        command.extend(["-l", str(last_page)])
        
    command.append(pdf_path)

    print(f"A executar: {' '.join(command)}")
    
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Erro ao converter PDF:\n{result.stderr}")

    print(f"Conversão concluída com sucesso! Sem imagens geradas.")
    return xml_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pdf_to_xml.py <ficheiro.pdf> [página_inicial] [página_final]")
        sys.exit(1)

    pdf = sys.argv[1]
    p_inicial = int(sys.argv[2]) if len(sys.argv) > 2 else None
    p_final = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    try:
        pdf_to_xml(pdf, first_page=p_inicial, last_page=p_final)
    except Exception as e:
        print(f"Erro: {e}")