"""PDF extractor with text-layer first routing and controlled OCR fallback."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image

from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor
from pd_scanner.extractors.resource_router import EmbeddedResource


class PDFExtractor(BaseExtractor):
    """Extract PDF text, embedded-image OCR, and page OCR without double-processing."""

    file_type = "pdf"

    def extract(self, path: Path):
        chunks = []
        warnings: list[str] = []
        ocr_status_payload = self.ocr_service.get_status_payload()
        ocr_available = bool(ocr_status_payload["available"])
        ocr_status = str(ocr_status_payload["message"])
        use_ocr = self.config.runtime.mode == "deep" and ocr_available

        page_count = 0
        dense_text_pages = 0
        sparse_text_pages = 0
        empty_text_pages = 0
        embedded_images = 0
        embedded_image_ocr_attempts = 0
        embedded_image_ocr_successes = 0
        page_ocr_attempts = 0
        page_ocr_successes = 0
        skipped_page_ocr_due_embedded_text = 0
        skipped_page_ocr_due_backend = 0
        skipped_page_ocr_due_limit = 0
        empty_page_ocr_results = 0
        page_debug: list[dict[str, object]] = []

        image_limit_warning_emitted = False
        call_limit_warning_emitted = False
        page_limit_warning_emitted = False
        runtime_disable_warning_emitted = False

        try:
            document = fitz.open(path)
        except Exception as exc:
            raise RuntimeError(f"Invalid PDF or unable to open PDF: {exc}") from exc

        with document:
            page_count = document.page_count
            for page_index in range(page_count):
                page_number = page_index + 1
                page_info: dict[str, object] = {
                    "page": page_number,
                    "text_chars": 0,
                    "classification": "empty",
                    "embedded_images": 0,
                    "embedded_image_text_chars": 0,
                    "page_ocr_attempted": False,
                    "page_ocr_text_chars": 0,
                    "page_ocr_decision": "not_needed",
                }
                try:
                    page = document.load_page(page_index)
                    text = sanitize_whitespace(page.get_text("text"))
                except Exception as exc:
                    warnings.append(f"Failed to read PDF page {page_number}: {exc}")
                    page_info["page_ocr_decision"] = "page_read_failed"
                    page_debug.append(page_info)
                    continue

                text_chars = len(text)
                page_info["text_chars"] = text_chars
                has_dense_text = text_chars >= self.config.ocr.min_pdf_text_chars
                has_sparse_text = 0 < text_chars < self.config.ocr.min_pdf_text_chars

                if has_dense_text:
                    dense_text_pages += 1
                    page_info["classification"] = "dense_text"
                    routed_chunks, routed_warnings = self.route_resource(
                        EmbeddedResource(
                            resource_type="text",
                            payload=text,
                            source_type="pdf_text",
                            source_path=str(path),
                            location={"page": page_number},
                            metadata={"page": page_number, "text_chars": text_chars},
                        )
                    )
                    chunks.extend(routed_chunks)
                    warnings.extend(routed_warnings)
                elif has_sparse_text:
                    sparse_text_pages += 1
                    page_info["classification"] = "sparse_text"
                else:
                    empty_text_pages += 1
                    page_info["classification"] = "empty_text"

                page_embedded_text_chars = 0
                page_image_count = 0
                image_runtime_failed = False

                for image_index, image_info in enumerate(page.get_images(full=True), start=1):
                    xref = image_info[0]
                    embedded_images += 1
                    page_image_count += 1
                    if embedded_images > self.config.runtime.max_embedded_images_per_file:
                        if not image_limit_warning_emitted:
                            warnings.append("PDF embedded image limit reached; remaining images skipped.")
                            image_limit_warning_emitted = True
                        break
                    if (embedded_image_ocr_attempts + page_ocr_attempts) >= self.config.runtime.max_ocr_calls_per_file:
                        if not call_limit_warning_emitted:
                            warnings.append("PDF OCR call limit reached; remaining embedded images and page OCR skipped.")
                            call_limit_warning_emitted = True
                        break
                    if not use_ocr:
                        continue
                    try:
                        extracted = document.extract_image(xref)
                        image_bytes = extracted.get("image")
                        if not image_bytes:
                            continue
                        with Image.open(io.BytesIO(image_bytes)) as image:
                            route_result = self.route_resource_detailed(
                                EmbeddedResource(
                                    resource_type="image",
                                    payload=image.copy(),
                                    source_type="pdf_image_ocr",
                                    source_path=str(path),
                                    location={"page": page_number, "image_index": image_index},
                                    metadata={"page": page_number, "image_index": image_index},
                                )
                            )
                        warnings.extend(route_result.warnings)
                        if route_result.attempted_ocr:
                            embedded_image_ocr_attempts += 1
                        if route_result.chunks:
                            chunks.extend(route_result.chunks)
                        if route_result.ocr_text_found:
                            embedded_image_ocr_successes += 1
                            page_embedded_text_chars += route_result.text_chars
                        if any(self.ocr_service.is_runtime_failure_warning(item) for item in route_result.warnings):
                            image_runtime_failed = True
                            use_ocr = False
                            if not runtime_disable_warning_emitted:
                                warnings.append(
                                    "PDF OCR disabled for remaining pages and embedded images after backend issue."
                                )
                                runtime_disable_warning_emitted = True
                            break
                    except Exception as exc:
                        warnings.append(f"Embedded image OCR failed for page {page_number}, image {image_index}: {exc}")

                page_info["embedded_images"] = page_image_count
                page_info["embedded_image_text_chars"] = page_embedded_text_chars

                if has_dense_text:
                    page_info["page_ocr_decision"] = "skipped_dense_text"
                    page_debug.append(page_info)
                    continue

                if self.config.runtime.mode == "fast":
                    if has_sparse_text:
                        self._append_sparse_text_chunk(chunks, warnings, path, page_number, text, reason="fast_mode")
                    page_info["page_ocr_decision"] = "skipped_fast_mode"
                    page_debug.append(page_info)
                    continue

                if page_embedded_text_chars >= self.config.ocr.min_pdf_text_chars:
                    if has_sparse_text:
                        self._append_sparse_text_chunk(
                            chunks,
                            warnings,
                            path,
                            page_number,
                            text,
                            reason="embedded_image_text_sufficient",
                        )
                    skipped_page_ocr_due_embedded_text += 1
                    page_info["page_ocr_decision"] = "skipped_embedded_image_text_sufficient"
                    page_debug.append(page_info)
                    continue

                if not use_ocr:
                    if has_sparse_text:
                        self._append_sparse_text_chunk(chunks, warnings, path, page_number, text, reason="ocr_unavailable")
                    skipped_page_ocr_due_backend += 1
                    page_info["page_ocr_decision"] = (
                        "skipped_after_runtime_failure" if image_runtime_failed else "skipped_ocr_unavailable"
                    )
                    page_debug.append(page_info)
                    continue

                if page_ocr_attempts >= self.config.runtime.max_pdf_ocr_pages:
                    if has_sparse_text:
                        self._append_sparse_text_chunk(chunks, warnings, path, page_number, text, reason="page_limit")
                    skipped_page_ocr_due_limit += 1
                    if not page_limit_warning_emitted:
                        warnings.append("PDF OCR page limit reached; remaining sparse/empty pages skipped.")
                        page_limit_warning_emitted = True
                    page_info["page_ocr_decision"] = "skipped_page_limit"
                    page_debug.append(page_info)
                    continue

                if (embedded_image_ocr_attempts + page_ocr_attempts) >= self.config.runtime.max_ocr_calls_per_file:
                    if has_sparse_text:
                        self._append_sparse_text_chunk(chunks, warnings, path, page_number, text, reason="ocr_call_limit")
                    skipped_page_ocr_due_limit += 1
                    if not call_limit_warning_emitted:
                        warnings.append("PDF OCR call limit reached; remaining sparse/empty pages skipped.")
                        call_limit_warning_emitted = True
                    page_info["page_ocr_decision"] = "skipped_ocr_call_limit"
                    page_debug.append(page_info)
                    continue

                try:
                    pixmap = page.get_pixmap(dpi=self.config.ocr.image_dpi)
                    with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                        ocr_result = self.ocr_service.extract_text_from_image(image)
                    page_ocr_attempts += 1
                    page_info["page_ocr_attempted"] = True
                    warnings.extend(ocr_result.warnings)
                    if ocr_result.status in {"runtime_failed", "backend_unavailable", "models_missing"}:
                        use_ocr = False
                        if not runtime_disable_warning_emitted:
                            warnings.append("PDF OCR disabled for remaining pages and embedded images after backend issue.")
                            runtime_disable_warning_emitted = True
                    ocr_text = sanitize_whitespace(ocr_result.text)
                    page_info["page_ocr_text_chars"] = len(ocr_text)
                    if ocr_text:
                        page_ocr_successes += 1
                        routed_chunks, routed_warnings = self.route_resource(
                            EmbeddedResource(
                                resource_type="text",
                                payload=ocr_text,
                                source_type="pdf_page_ocr",
                                source_path=str(path),
                                location={"page": page_number},
                                metadata={
                                    "page": page_number,
                                    "ocr": True,
                                    "ocr_backend": ocr_result.backend,
                                    "ocr_metadata": ocr_result.metadata,
                                },
                            )
                        )
                        chunks.extend(routed_chunks)
                        warnings.extend(routed_warnings)
                        page_info["page_ocr_decision"] = "page_ocr_text"
                    else:
                        empty_page_ocr_results += 1
                        if has_sparse_text:
                            self._append_sparse_text_chunk(
                                chunks,
                                warnings,
                                path,
                                page_number,
                                text,
                                reason="page_ocr_empty",
                            )
                        page_info["page_ocr_decision"] = "page_ocr_empty"
                except Exception as exc:
                    warnings.append(f"OCR failed for page {page_number}: {exc}")
                    if has_sparse_text:
                        self._append_sparse_text_chunk(chunks, warnings, path, page_number, text, reason="page_ocr_exception")
                    page_info["page_ocr_decision"] = "page_ocr_exception"

                page_debug.append(page_info)

        if skipped_page_ocr_due_backend:
            warnings.append(f"PDF page OCR skipped for {skipped_page_ocr_due_backend} sparse/empty pages: {ocr_status}")
        if skipped_page_ocr_due_embedded_text:
            warnings.append(
                f"PDF page OCR skipped for {skipped_page_ocr_due_embedded_text} pages because embedded image OCR already produced enough text."
            )
        if empty_page_ocr_results:
            warnings.append(f"PDF page OCR returned empty text for {empty_page_ocr_results} pages.")

        total_ocr_calls = embedded_image_ocr_attempts + page_ocr_attempts
        return self.build_result(
            chunks=chunks,
            metadata={
                "structured": False,
                "page_count": page_count,
                "dense_text_pages": dense_text_pages,
                "sparse_text_pages": sparse_text_pages,
                "empty_text_pages": empty_text_pages,
                "embedded_images": embedded_images,
                "embedded_image_ocr_attempts": embedded_image_ocr_attempts,
                "embedded_image_ocr_successes": embedded_image_ocr_successes,
                "page_ocr_attempts": page_ocr_attempts,
                "page_ocr_successes": page_ocr_successes,
                "ocr_pages": page_ocr_attempts,
                "ocr_calls": total_ocr_calls,
                "ocr_used": total_ocr_calls > 0,
                "ocr_available": ocr_available,
                "ocr_status": ocr_status,
                "ocr_backend": ocr_status_payload.get("backend"),
                "ocr_device": ocr_status_payload.get("device"),
                "page_debug": page_debug[:50],
            },
            warnings=warnings,
        )

    def _append_sparse_text_chunk(
        self,
        chunks: list,
        warnings: list[str],
        path: Path,
        page_number: int,
        text: str,
        *,
        reason: str,
    ) -> None:
        if not text:
            return
        routed_chunks, routed_warnings = self.route_resource(
            EmbeddedResource(
                resource_type="text",
                payload=text,
                source_type="pdf_text_sparse",
                source_path=str(path),
                location={"page": page_number},
                metadata={"page": page_number, "sparse_text": True, "reason": reason, "text_chars": len(text)},
            )
        )
        chunks.extend(routed_chunks)
        warnings.extend(routed_warnings)
