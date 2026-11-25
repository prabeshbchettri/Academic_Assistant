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
    Exports high-quality PDF using the configured engine order:
    1. Tectonic (bundled or system)
    2. XeLaTeX / pdfLaTeX (system)
    3. LibreOffice headless
    """

    def __init__(self, latex_generator: LatexGenerator | None = None):
        self.latex_gen = latex_generator or LatexGenerator()
        self.last_engine: str = "none"

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

        # Save human-readable LaTeX source with original path
        tex_source_saved = self.latex_gen.render(report)
        tex_target.write_text(tex_source_saved, encoding="utf-8")

        logo_src: Path | None = None
        if report.front_page and report.front_page.logo_path:
            candidate = Path(report.front_page.logo_path)
            if candidate.exists() and candidate.is_file():
                logo_src = candidate

        # Use relative staged logo filename inside compilation temp dir to avoid path/space issues
        staged_logo_name = f"ioe_logo{logo_src.suffix.lower()}" if logo_src else None
        compile_tex = (
            self.latex_gen.render(report, logo_override=staged_logo_name)
            if staged_logo_name
            else tex_source_saved
        )

        preferred = settings.pdf_engine.strip().lower()
        engine_chain = (
            ["libreoffice", "tectonic", "xelatex"]
            if preferred == "libreoffice"
            else (
                ["xelatex", "tectonic", "libreoffice"]
                if "xelatex" in preferred
                else ["tectonic", "xelatex", "libreoffice"]
            )
        )

        pdf_path: Path | None = None
        actual_engine = "none"
        for engine_name in engine_chain:
            if engine_name == "tectonic":
                pdf_path = self._compile_with_tectonic(
                    compile_tex, pdf_target, logo_src, staged_logo_name
                )
            elif engine_name == "xelatex":
                pdf_path = self._compile_with_xelatex(
                    compile_tex, pdf_target, logo_src, staged_logo_name
                )
            elif engine_name == "libreoffice":
                pdf_path = self._compile_with_libreoffice(docx_path, out_dir)

            if pdf_path and pdf_path.exists():
                actual_engine = engine_name
                break

        self.last_engine = actual_engine

        meta_target = out_dir / "metadata.json"
        metadata = {
            "title": report.title,
            "version": version,
            "created_at": datetime.now(UTC).isoformat(),
            "docx_path": str(docx_path),
            "pdf_path": str(pdf_path) if pdf_path else None,
            "engine": actual_engine,
        }
        meta_target.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return pdf_path

    @staticmethod
    def _stage_logo(
        tmpdir: str, logo_src: Path | None, staged_name: str | None
    ) -> None:
        if logo_src and staged_name and logo_src.exists():
            shutil.copy2(logo_src, Path(tmpdir) / staged_name)

    def _compile_with_tectonic(
        self,
        tex_source: str,
        target_pdf: Path,
        logo_src: Path | None = None,
        staged_logo_name: str | None = None,
    ) -> Path | None:
        tectonic_bin = shutil.which("tectonic") or settings.tectonic_path
        if not tectonic_bin:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            self._stage_logo(tmpdir, logo_src, staged_logo_name)
            tex_file = Path(tmpdir) / "document.tex"
            tex_file.write_text(tex_source, encoding="utf-8")

            cmd = [tectonic_bin, "--untrusted", "-o", ".", "document.tex"]
            try:
                result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, timeout=60)
                produced_pdf = Path(tmpdir) / "document.pdf"
                if (
                    result.returncode == 0
                    and produced_pdf.exists()
                    and produced_pdf.stat().st_size > 200
                ):
                    shutil.copy2(produced_pdf, target_pdf)
                    logger.info("Compiled PDF using Tectonic at %s", target_pdf)
                    return target_pdf
                logger.warning(
                    "Tectonic did not produce valid PDF (rc=%s): %s",
                    result.returncode,
                    result.stderr.decode("utf-8", errors="replace")[:400],
                )
            except Exception as exc:
                logger.warning("Tectonic compilation failed: %s", exc)

        return None

    def _compile_with_xelatex(
        self,
        tex_source: str,
        target_pdf: Path,
        logo_src: Path | None = None,
        staged_logo_name: str | None = None,
    ) -> Path | None:
        xelatex_bin = shutil.which("xelatex") or shutil.which("pdflatex")
        if not xelatex_bin:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            self._stage_logo(tmpdir, logo_src, staged_logo_name)
            tex_file = Path(tmpdir) / "document.tex"
            tex_file.write_text(tex_source, encoding="utf-8")

            cmd = [
                xelatex_bin,
                "-interaction=nonstopmode",
                "document.tex",
            ]
            try:
                # Run twice in tmpdir so TOC, page numbers, and relative logo resolve cleanly
                subprocess.run(cmd, cwd=tmpdir, capture_output=True, timeout=40)
                result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, timeout=40)
                produced_pdf = Path(tmpdir) / "document.pdf"
                if (
                    result.returncode == 0
                    and produced_pdf.exists()
                    and produced_pdf.stat().st_size > 200
                ):
                    shutil.copy2(produced_pdf, target_pdf)
                    logger.info("Compiled PDF using %s at %s", xelatex_bin, target_pdf)
                    return target_pdf
                logger.warning(
                    "%s failed to produce valid PDF (rc=%s, size=%s): %s",
                    xelatex_bin,
                    result.returncode,
                    produced_pdf.stat().st_size if produced_pdf.exists() else 0,
                    result.stdout.decode("utf-8", errors="replace")[-400:],
                )
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
            subprocess.run(cmd, capture_output=True, timeout=60)
            expected_pdf = output_dir / f"{docx_path.stem}.pdf"
            if expected_pdf.exists():
                logger.info("Compiled PDF using LibreOffice headless at %s", expected_pdf)
                return expected_pdf
        except Exception as exc:
            logger.warning("LibreOffice conversion failed: %s", exc)

        return None
