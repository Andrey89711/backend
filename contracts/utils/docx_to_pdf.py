import shutil
import subprocess
from pathlib import Path
from typing import Optional

def _convert_with_docx2pdf(input_path: Path, output_path: Path) -> tuple[bool, Optional[str]]:
    try:
        from docx2pdf import convert
    except ImportError:
        return False, "docx2pdf is not installed"
    try:
        convert(str(input_path), str(output_path))
    except Exception as exc:
        return False, f"docx2pdf failed: {exc}"
    return output_path.exists(), None

def _convert_with_libreoffice(input_path: Path, output_path: Path) -> tuple[bool, Optional[str]]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return False, "LibreOffice (soffice) is not found in PATH"

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        soffice, "--headless", "--convert-to", "pdf",
        "--outdir", str(output_dir), str(input_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as exc:
        return False, f"libreoffice failed: {exc}"

    converted = output_dir / f"{input_path.stem}.pdf"
    if converted.exists() and converted != output_path:
        try:
            converted.replace(output_path)
        except PermissionError:
            pass

    return output_path.exists(), None

def convert_docx_to_pdf(input_file: Path, output_file: Path) -> Path:
    """Конвертирует DOCX в PDF"""
    input_path = input_file.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() != ".docx":
        raise ValueError("Input file must have .docx extension")

    output_path = output_file.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    errors = []

    ok, err = _convert_with_docx2pdf(input_path, output_path)
    if ok:
        return output_path
    if err:
        errors.append(err)

    ok, err = _convert_with_libreoffice(input_path, output_path)
    if ok:
        return output_path
    if err:
        errors.append(err)

    raise RuntimeError("Conversion failed: " + " | ".join(errors))