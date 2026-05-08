"""OCR Engine — extracts text from images and PDFs.

Supports:
- Images (PNG, JPEG, TIFF) via Tesseract
- PDFs via pdf2image + Tesseract
- Optionally Surya (if installed)
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Try to import surya (optional)
try:
    from surya.ocr import run_ocr
    from surya.model.detection import load_model as load_detection_model
    from surya.model.recognition import load_model as load_recognition_model
    SURYA_AVAILABLE = True
except ImportError:
    SURYA_AVAILABLE = False


class OCREngine:
    """Unified OCR engine with fallback between Surya and Tesseract."""

    def __init__(self, prefer_surya: bool = True):
        self.prefer_surya = prefer_surya and SURYA_AVAILABLE
        self.surya_det_model = None
        self.surya_rec_model = None

        if self.prefer_surya:
            self._load_surya_models()

    def _load_surya_models(self):
        """Lazy load Surya models."""
        if not SURYA_AVAILABLE:
            return
        try:
            self.surya_det_model = load_detection_model()
            self.surya_rec_model = load_recognition_model()
        except Exception as e:
            print(f"Failed to load Surya models: {e}")
            self.prefer_surya = False

    def extract_text(self, file_path: str, language: str = "rus+eng") -> str:
        """Extract text from image or PDF.

        Args:
            file_path: Path to image or PDF.
            language: Tesseract language code (e.g., 'rus' for Russian).

        Returns:
            Extracted text as a single string.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type
        if path.suffix.lower() in (".pdf",):
            return self._extract_from_pdf(file_path, language)
        else:
            return self._extract_from_image(file_path, language)

    def _extract_from_image(self, image_path: str, language: str) -> str:
        """Extract text from a single image."""
        if self.prefer_surya and self.surya_det_model and self.surya_rec_model:
            return self._surya_ocr_image(image_path)

        # Fallback to Tesseract
        return pytesseract.image_to_string(
            Image.open(image_path),
            lang=language,
            config="--psm 3 --oem 3"
        )

    def _extract_from_pdf(self, pdf_path: str, language: str) -> str:
        """Extract text from PDF by converting each page to image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            images = convert_from_path(pdf_path, dpi=300, output_folder=tmpdir)
            texts = []
            for i, img in enumerate(images):
                img_path = os.path.join(tmpdir, f"page_{i}.png")
                img.save(img_path, "PNG")
                page_text = self._extract_from_image(img_path, language)
                texts.append(page_text)
            return "\n\n".join(texts)

    def _surya_ocr_image(self, image_path: str) -> str:
        """Run Surya OCR on an image."""
        if not SURYA_AVAILABLE:
            raise RuntimeError("Surya not installed")
        try:
            # Surya expects PIL Image
            image = Image.open(image_path)
            det_model = self.surya_det_model or load_detection_model()
            rec_model = self.surya_rec_model or load_recognition_model()
            result = run_ocr([image], det_model, rec_model)[0]
            # Combine text lines
            lines = [line.text for line in result.text_lines]
            return "\n".join(lines)
        except Exception as e:
            print(f"Surya OCR failed: {e}, falling back to Tesseract")
            self.prefer_surya = False
            return self._extract_from_image(image_path, "rus+eng")


def get_ocr_engine() -> OCREngine:
    """Factory function returning a configured OCR engine."""
    # Check if Surya is available via environment variable
    use_surya = os.environ.get("USE_SURYA", "false").lower() == "true"
    return OCREngine(prefer_surya=use_surya)


# Quick test
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python engine.py <file_path>")
        sys.exit(1)
    engine = get_ocr_engine()
    text = engine.extract_text(sys.argv[1])
    print("--- Extracted text (first 500 chars) ---")
    print(text[:500])