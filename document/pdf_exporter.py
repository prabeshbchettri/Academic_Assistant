from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.settings import settings
from document.latex_generator import LatexGenerator
from models.report import ReportContent

logger = logging.getLogger(__name__)


class PdfExporter:
    """
    Exports high-quality PDF using the best available engine in the fallback chain:
    1. Tectonic (bundled or system)
    2. XeLaTeX (system)
    3. LibreOffice headless
    """

    def __init__(self, latex_generator: LatexGenerator | None = None):
        self.latex_gen = latex_generator or LatexGenerator()

    def export(
        self,
        report: ReportContent,
        docx_path: Path,
        assignment_id: int = 1,
        version: int = 1,
    ) -> Path | None:
        out_dir = settings.storage_dir / "outputs" / str(assignment_id) / f"v{version}"
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_target = out_dir / "report.pdf"
        tex_target = out_dir / "report.tex"

        # Generate LaTeX source
        tex_source = self.latex_gen.render(report)
        tex_target.write_text(tex_source, encoding="utf-8")

        # Try LaTeX engine first (Tectonic or XeLaTeX)
        pdf_path = self._compile_with_tectonic(tex_source, pdf_target)
        if not pdf_path:
            pdf_path = self._compile_with_xelatex(tex_source, pdf_target)

        # Fallback to LibreOffice headless using docx if LaTeX compilation did not succeed
        if not pdf_path:
            pdf_path = self._compile_with_libreoffice(docx_path, out_dir)

        # Write metadata.json
        meta_target = out_dir / "metadata.json"
        metadata = {
            "title": report.title,
            "version": version,
            "created_at": datetime.now(UTC).isoformat(),
            "docx_path": str(docx_path),
            "pdf_path": str(pdf_path) if pdf_path else None,
            "engine": "tectonic/xelatex" if pdf_path and pdf_path.exists() else "libreoffice",
        }
        meta_target.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return pdf_path

    def _compile_with_tectonic(self, tex_source: str, target_pdf: Path) -> Path | None:
        tectonic_bin = shutil.which("tectonic") or settings.tectonic_path
        if not tectonic_bin:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = Path(tmpdir) / "document.tex"
            tex_file.write_text(tex_source, encoding="utf-8")

            cmd = [tectonic_bin, "--untrusted", "-o", tmpdir, str(tex_file)]
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
                produced_pdf = Path(tmpdir) / "document.pdf"
                if result.returncode == 0 and produced_pdf.exists():
                    shutil.copy2(produced_pdf, target_pdf)
                    logger.info("Compiled PDF using Tectonic at %s", target_pdf)
                    return target_pdf
            except Exception as exc:
                logger.warning("Tectonic compilation failed: %s", exc)

        return None

    def _compile_with_xelatex(self, tex_source: str, target_pdf: Path) -> Path | None:
        xelatex_bin = shutil.which("xelatex") or shutil.which("pdflatex")
        if not xelatex_bin:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = Path(tmpdir) / "document.tex"
            tex_file.write_text(tex_source, encoding="utf-8")

            cmd = [xelatex_bin, "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_file)]
            try:
                # Run twice for table of contents
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
                produced_pdf = Path(tmpdir) / "document.pdf"
                if produced_pdf.exists():
                    shutil.copy2(produced_pdf, target_pdf)
                    logger.info("Compiled PDF using %s at %s", xelatex_bin, target_pdf)
                    return target_pdf
            except Exception as exc:
                logger.warning("%s compilation failed: %s", xelatex_bin, exc)

        return None

    def _compile_with_libreoffice(self, docx_path: Path, output_dir: Path) -> Path | None:
        libreoffice_bin = shutil.which("libreoffice") or shutil.which("soffice")
        if not libreoffice_bin or not docx_path.exists():
            return None

        cmd = [
            libreoffice_bin,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(docx_path),
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            expected_pdf = output_dir / f"{docx_path.stem}.pdf"
            if expected_pdf.exists():
                logger.info("Compiled PDF using LibreOffice headless at %s", expected_pdf)
                return expected_pdf
        except Exception as exc:
            logger.warning("LibreOffice conversion failed: %s", exc)

        return None
