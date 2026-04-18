"""HTML extractor."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from pd_scanner.core.utils import safe_read_text_details, sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor
from pd_scanner.extractors.resource_router import EmbeddedResource


class HTMLExtractor(BaseExtractor):
    """Extract visible text from HTML content."""

    file_type = "html"

    def extract(self, path: Path) -> ExtractionResult:
        html, encoding, looks_mojibake = safe_read_text_details(path)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        chunks = []
        warnings: list[str] = []
        ocr_attempts = 0
        ocr_successes = 0
        image_count = 0
        use_ocr = self.config.runtime.mode == "deep"
        ocr_status_payload = self.ocr_service.get_status_payload() if use_ocr else None
        ocr_available = bool(ocr_status_payload["available"]) if ocr_status_payload else False
        ocr_status = str(ocr_status_payload["message"]) if ocr_status_payload else "OCR disabled in fast mode."
        if looks_mojibake:
            warnings.append("HTML text still looks suspiciously garbled after decoding; review source encoding.")

        text = sanitize_whitespace(soup.get_text(separator=" "))
        if text:
            routed_chunks, routed_warnings = self.route_resource(
                EmbeddedResource(
                    resource_type="text",
                    payload=text,
                    source_type="html_text",
                    source_path=str(path),
                    location={"html_path": "body"},
                )
            )
            chunks.extend(routed_chunks)
            warnings.extend(routed_warnings)

        for index, tag in enumerate(soup.find_all("img"), start=1):
            alt_bits = [sanitize_whitespace(tag.get("alt", "")), sanitize_whitespace(tag.get("title", ""))]
            alt_text = sanitize_whitespace(" ".join(bit for bit in alt_bits if bit))
            if alt_text:
                routed_chunks, routed_warnings = self.route_resource(
                    EmbeddedResource(
                        resource_type="text",
                        payload=alt_text,
                        source_type="html_alt_text",
                        source_path=str(path),
                        location={"tag": "img", "image_index": index},
                        metadata={"image_index": index},
                    )
                )
                chunks.extend(routed_chunks)
                warnings.extend(routed_warnings)

            image_count += 1
            if image_count > self.config.runtime.max_embedded_images_per_file:
                warnings.append("HTML embedded image limit reached; remaining images skipped.")
                break
            if ocr_attempts >= self.config.runtime.max_ocr_calls_per_file:
                warnings.append("HTML OCR call limit reached; remaining images skipped.")
                break
            if not use_ocr:
                continue
            if not ocr_available:
                warnings.append(f"HTML embedded image OCR skipped: {ocr_status}")
                break
            src = sanitize_whitespace(tag.get("src", ""))
            if not src:
                continue
            if src.startswith(("http://", "https://", "data:")):
                warnings.append(f"HTML embedded image skipped because remote/data URI OCR is unsupported: {src[:64]}")
                continue
            image_path = (path.parent / src).resolve() if not Path(src).is_absolute() else Path(src).resolve()
            if not image_path.exists():
                warnings.append(f"HTML embedded image not found locally: {src}")
                continue
            try:
                from PIL import Image

                with Image.open(image_path) as image:
                    route_result = self.route_resource_detailed(
                        EmbeddedResource(
                            resource_type="image",
                            payload=image.copy(),
                            source_type="html_image_ocr",
                            source_path=str(path),
                            location={"tag": "img", "image_index": index, "src": str(image_path)},
                            metadata={"image_index": index, "src": str(image_path)},
                        )
                    )
                warnings.extend(route_result.warnings)
                if route_result.attempted_ocr:
                    ocr_attempts += 1
                if route_result.chunks:
                    chunks.extend(route_result.chunks)
                if route_result.ocr_text_found:
                    ocr_successes += 1
                if any(self.ocr_service.is_runtime_failure_warning(item) for item in route_result.warnings):
                    warnings.append("HTML embedded image OCR disabled for remaining images after backend issue.")
                    break
            except Exception as exc:
                warnings.append(f"HTML image OCR failed for {src}: {exc}")

        for index, tag in enumerate(soup.find_all("a"), start=1):
            href = sanitize_whitespace(tag.get("href", ""))
            title = sanitize_whitespace(tag.get("title", ""))
            label = sanitize_whitespace(tag.get_text(separator=" "))
            link_text = sanitize_whitespace(" ".join(bit for bit in (label, title, href) if bit))
            if not link_text:
                continue
            routed_chunks, routed_warnings = self.route_resource(
                EmbeddedResource(
                    resource_type="link",
                    payload=link_text,
                    source_type="html_link",
                    source_path=str(path),
                    location={"tag": "a", "link_index": index},
                    metadata={"href": href, "title": title},
                )
            )
            chunks.extend(routed_chunks)
            warnings.extend(routed_warnings)

        for index, tag in enumerate(soup.find_all("meta"), start=1):
            meta_name = sanitize_whitespace(tag.get("name", "") or tag.get("property", "") or tag.get("http-equiv", ""))
            content = sanitize_whitespace(tag.get("content", ""))
            if not (meta_name and content):
                continue
            routed_chunks, routed_warnings = self.route_resource(
                EmbeddedResource(
                    resource_type="metadata",
                    payload=f"{meta_name}: {content}",
                    source_type="html_metadata",
                    source_path=str(path),
                    location={"tag": "meta", "meta_index": index},
                    metadata={"meta_name": meta_name},
                )
            )
            chunks.extend(routed_chunks)
            warnings.extend(routed_warnings)

        return self.build_result(
            chunks=chunks,
            metadata={
                "structured": False,
                "encoding": encoding,
                "embedded_images": image_count,
                "ocr_available": ocr_available,
                "ocr_status": ocr_status,
                "ocr_backend": ocr_status_payload.get("backend") if ocr_status_payload else None,
                "ocr_device": ocr_status_payload.get("device") if ocr_status_payload else None,
                "ocr_calls": ocr_attempts,
                "ocr_successes": ocr_successes,
                "ocr_used": ocr_attempts > 0,
            },
            warnings=warnings,
        )
