from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
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
        soffice,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(input_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as exc:
        return False, f"libreoffice failed: {exc}"

    converted = output_dir / f"{input_path.stem}.pdf"
    if converted.exists() and converted != output_path:
        converted.replace(output_path)

    return output_path.exists(), None


def convert_docx_to_pdf(input_file: Path, output_file: Path | None = None) -> Path:
    input_path = input_file.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() != ".docx":
        raise ValueError("Input file must have .docx extension")

    output_path = (
        output_file.expanduser().resolve()
        if output_file
        else input_path.with_suffix(".pdf")
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

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

    raise RuntimeError(
        "Conversion failed. "
        + " | ".join(errors)
        + ". Install Microsoft Word for docx2pdf or install LibreOffice and add soffice to PATH."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert DOCX file to PDF")
    parser.add_argument("input", type=Path, help="Path to .docx file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to output .pdf file (optional)",
    )
    args = parser.parse_args()

    try:
        pdf_path = convert_docx_to_pdf(args.input, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"PDF created: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
