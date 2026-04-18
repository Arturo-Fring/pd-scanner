"""DOCX extractor."""

from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from PIL import Image

from pd_scanner.core.models import ExtractedChunk, ExtractionResult
from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor
from pd_scanner.extractors.resource_router import EmbeddedResource


class DOCXExtractor(BaseExtractor):
    """Extract paragraphs and tables from DOCX files."""

    file_type = "docx"

    def extract(self, path: Path) -> ExtractionResult:
        document = Document(path)
        chunks: list[ExtractedChunk] = []
        warnings: list[str] = []
        ocr_calls = 0
        image_count = 0
        use_ocr = self.config.runtime.mode == "deep"
        ocr_available, ocr_status = self.ocr_service.get_status() if use_ocr else (False, "OCR disabled in fast mode.")
        for index, paragraph in enumerate(document.paragraphs):
            text = sanitize_whitespace(paragraph.text)
            if text:
                routed_chunks, routed_warnings = self.route_resource(
                    EmbeddedResource(
                        resource_type="text",
                        payload=text,
                        source_type="docx_paragraph",
                        source_path=str(path),
                        location={"paragraph": index + 1},
                        metadata={"paragraph": index + 1},
                    )
                )
                chunks.extend(routed_chunks)
                warnings.extend(routed_warnings)
        for table_index, table in enumerate(document.tables):
            for row_index, row in enumerate(table.rows):
                for cell_index, cell in enumerate(row.cells):
                    cell_text = sanitize_whitespace(cell.text)
                    if not cell_text:
                        continue
                    routed_chunks, routed_warnings = self.route_resource(
                        EmbeddedResource(
                            resource_type="text",
                            payload=cell_text,
                            source_type="docx_table_cell",
                            source_path=str(path),
                            location={"table": table_index + 1, "row": row_index + 1, "cell": cell_index + 1},
                            metadata={"structured": True, "table": table_index + 1, "row": row_index + 1, "cell": cell_index + 1},
                        )
                    )
                    for chunk in routed_chunks:
                        chunk.columns = ("docx_table_cell",)
                    chunks.extend(routed_chunks)
                    warnings.extend(routed_warnings)

        for image_index, relationship in enumerate(document.part._rels.values(), start=1):
            if relationship.reltype != RT.IMAGE:
                continue
            image_count += 1
            if image_count > self.config.runtime.max_embedded_images_per_file:
                warnings.append("DOCX embedded image limit reached; remaining images skipped.")
                break
            if ocr_calls >= self.config.runtime.max_ocr_calls_per_file:
                warnings.append("DOCX OCR call limit reached; remaining images skipped.")
                break
            if not use_ocr:
                continue
            if not ocr_available:
                warnings.append(f"DOCX embedded image OCR skipped: {ocr_status}")
                break
            try:
                with Image.open(io.BytesIO(relationship.target_part.blob)) as image:
                    routed_chunks, routed_warnings = self.route_resource(
                        EmbeddedResource(
                            resource_type="image",
                            payload=image.copy(),
                            source_type="docx_image_ocr",
                            source_path=str(path),
                            location={"image_index": image_index},
                            metadata={"image_index": image_index},
                        )
                    )
                warnings.extend(routed_warnings)
                if any(self.ocr_service.is_runtime_failure_warning(item) for item in routed_warnings):
                    warnings.append("DOCX embedded image OCR disabled for remaining images after backend issue.")
                    break
                if routed_chunks:
                    ocr_calls += 1
                    chunks.extend(routed_chunks)
            except Exception as exc:
                warnings.append(f"DOCX embedded image OCR failed for image {image_index}: {exc}")

        return self.build_result(
            chunks=chunks,
            metadata={
                "chunk_count": len(chunks),
                "paragraph_count": len(document.paragraphs),
                "table_count": len(document.tables),
                "embedded_images": image_count,
                "ocr_calls": ocr_calls,
                "structured": False,
            },
            warnings=warnings,
        )
