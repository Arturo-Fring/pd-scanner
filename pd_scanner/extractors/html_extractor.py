"""HTML extractor."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor
from pd_scanner.extractors.resource_router import EmbeddedResource


class HTMLExtractor(BaseExtractor):
    """Extract visible text from HTML content."""

    file_type = "html"

    def extract(self, path: Path) -> ExtractionResult:
        html = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        chunks = []
        warnings: list[str] = []
        ocr_calls = 0
        image_count = 0
        use_ocr = self.config.runtime.mode == "deep"
        ocr_available, ocr_status = self.ocr_service.get_status() if use_ocr else (False, "OCR disabled in fast mode.")

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
            if ocr_calls >= self.config.runtime.max_ocr_calls_per_file:
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
                    routed_chunks, routed_warnings = self.route_resource(
                        EmbeddedResource(
                            resource_type="image",
                            payload=image.copy(),
                            source_type="html_image_ocr",
                            source_path=str(path),
                            location={"tag": "img", "image_index": index, "src": str(image_path)},
                            metadata={"image_index": index, "src": str(image_path)},
                        )
                    )
                warnings.extend(routed_warnings)
                if any(self.ocr_service.is_runtime_failure_warning(item) for item in routed_warnings):
                    warnings.append("HTML embedded image OCR disabled for remaining images after backend issue.")
                    break
                if routed_chunks:
                    ocr_calls += 1
                    chunks.extend(routed_chunks)
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
                "embedded_images": image_count,
                "ocr_calls": ocr_calls,
            },
            warnings=warnings,
        )
