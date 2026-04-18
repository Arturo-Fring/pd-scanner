"""PDF extractor with text-layer first and OCR fallback in deep mode."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image

from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor
from pd_scanner.extractors.resource_router import EmbeddedResource


class PDFExtractor(BaseExtractor):
    """Extract text from PDFs and OCR sparse pages when needed."""

    file_type = "pdf"

    def extract(self, path: Path):
        chunks = []
        warnings: list[str] = []
        available, ocr_status = self.ocr_service.get_status()
        use_ocr = self.config.runtime.mode == "deep" and available
        page_count = 0
        ocr_pages = 0
        embedded_images = 0
        ocr_calls = 0

        try:
            document = fitz.open(path)
        except Exception as exc:
            raise RuntimeError(f"Invalid PDF or unable to open PDF: {exc}") from exc

        with document:
            page_count = document.page_count
            for page_index in range(page_count):
                try:
                    page = document.load_page(page_index)
                    text = sanitize_whitespace(page.get_text("text"))
                except Exception as exc:
                    warnings.append(f"Failed to read PDF page {page_index + 1}: {exc}")
                    continue

                has_dense_text = bool(text and len(text) >= self.config.ocr.min_pdf_text_chars)
                has_sparse_text = bool(text and not has_dense_text)

                if text and len(text) >= self.config.ocr.min_pdf_text_chars:
                    routed_chunks, routed_warnings = self.route_resource(
                        EmbeddedResource(
                            resource_type="text",
                            payload=text,
                            source_type="pdf_text",
                            source_path=str(path),
                            location={"page": page_index + 1},
                            metadata={"page": page_index + 1},
                        )
                    )
                    chunks.extend(routed_chunks)
                    warnings.extend(routed_warnings)

                if text and self.config.runtime.mode == "fast":
                    routed_chunks, routed_warnings = self.route_resource(
                        EmbeddedResource(
                            resource_type="text",
                            payload=text,
                            source_type="pdf_text_sparse",
                            source_path=str(path),
                            location={"page": page_index + 1},
                            metadata={"page": page_index + 1, "sparse_text": True},
                        )
                    )
                    chunks.extend(routed_chunks)
                    warnings.extend(routed_warnings)

                for image_index, image_info in enumerate(page.get_images(full=True), start=1):
                    xref = image_info[0]
                    embedded_images += 1
                    if embedded_images > self.config.runtime.max_embedded_images_per_file:
                        warnings.append("PDF embedded image limit reached; remaining images skipped.")
                        break
                    if ocr_calls >= self.config.runtime.max_ocr_calls_per_file:
                        warnings.append("PDF OCR call limit reached; remaining embedded images skipped.")
                        break
                    if not use_ocr:
                        continue
                    try:
                        extracted = document.extract_image(xref)
                        image_bytes = extracted.get("image")
                        if not image_bytes:
                            continue
                        with Image.open(io.BytesIO(image_bytes)) as image:
                            routed_chunks, routed_warnings = self.route_resource(
                                EmbeddedResource(
                                    resource_type="image",
                                    payload=image.copy(),
                                    source_type="pdf_image_ocr",
                                    source_path=str(path),
                                    location={"page": page_index + 1, "image_index": image_index},
                                    metadata={"page": page_index + 1, "image_index": image_index},
                                )
                            )
                        warnings.extend(routed_warnings)
                        if routed_chunks:
                            ocr_calls += 1
                            chunks.extend(routed_chunks)
                    except Exception as exc:
                        warnings.append(f"Embedded image OCR failed for page {page_index + 1}, image {image_index}: {exc}")

                if has_dense_text or (has_sparse_text and self.config.runtime.mode == "fast"):
                    continue

                if self.config.runtime.mode == "fast":
                    continue

                if not use_ocr:
                    warnings.append(f"Sparse PDF page {page_index + 1} skipped: {ocr_status}")
                    continue

                if ocr_pages >= self.config.runtime.max_pdf_ocr_pages:
                    warnings.append("PDF OCR page limit reached; remaining sparse pages skipped.")
                    break

                try:
                    pixmap = page.get_pixmap(dpi=self.config.ocr.image_dpi)
                    with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                        ocr_text = sanitize_whitespace(self.ocr_service.extract_text(image))
                    ocr_pages += 1
                    ocr_calls += 1
                    if ocr_text:
                        routed_chunks, routed_warnings = self.route_resource(
                            EmbeddedResource(
                                resource_type="text",
                                payload=ocr_text,
                                source_type="pdf_page_ocr",
                                source_path=str(path),
                                location={"page": page_index + 1},
                                metadata={"page": page_index + 1, "ocr": True},
                            )
                        )
                        chunks.extend(routed_chunks)
                        warnings.extend(routed_warnings)
                    else:
                        warnings.append(f"OCR returned empty text for page {page_index + 1}.")
                except Exception as exc:
                    warnings.append(f"OCR failed for page {page_index + 1}: {exc}")

        return self.build_result(
            chunks=chunks,
            metadata={
                "structured": False,
                "page_count": page_count,
                "ocr_used": ocr_pages > 0,
                "ocr_pages": ocr_pages,
                "embedded_images": embedded_images,
                "ocr_calls": ocr_calls,
            },
            warnings=warnings,
        )
