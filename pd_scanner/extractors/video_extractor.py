"""Video OCR extractor for MP4 files."""

from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
from PIL import Image

from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor


class VideoExtractor(BaseExtractor):
    """Extract frames from video and OCR them."""

    file_type = "video"

    def extract(self, path: Path):
        warnings: list[str] = []
        if self.config.runtime.mode == "fast":
            warnings.append("Deep video OCR skipped in fast mode.")
            return self.build_result(metadata={"structured": False, "ocr_used": False}, warnings=warnings)

        ocr_status_payload = self.ocr_service.get_status_payload()
        available = bool(ocr_status_payload["available"])
        status = str(ocr_status_payload["message"])
        if not available:
            warnings.append(status)
            return self.build_result(
                metadata={
                    "structured": False,
                    "ocr_used": False,
                    "ocr_calls": 0,
                    "ocr_status": ocr_status_payload.get("status"),
                    "ocr_backend": ocr_status_payload.get("backend"),
                    "ocr_device": ocr_status_payload.get("device"),
                },
                warnings=warnings,
            )

        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise RuntimeError("Unable to open video file")

        fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
        if fps <= 0:
            fps = 1.0
            warnings.append("Video FPS unavailable; falling back to 1 FPS for frame stepping.")
        frame_step = max(1, int(fps * self.config.runtime.video_frame_step_sec))
        frame_index = 0
        sampled = 0
        chunks = []
        seen_hashes: set[str] = set()
        ocr_runtime_failed = False
        ocr_calls = 0
        duplicate_frames = 0

        try:
            while sampled < self.config.runtime.max_video_frames:
                success, frame = capture.read()
                if not success:
                    break
                if frame_index % frame_step != 0:
                    frame_index += 1
                    continue

                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb)
                    digest = hashlib.md5(pil_image.resize((32, 32)).tobytes()).hexdigest()
                    if digest in seen_hashes:
                        duplicate_frames += 1
                        frame_index += 1
                        continue
                    seen_hashes.add(digest)
                    ocr_result = self.ocr_service.extract_text_from_image(pil_image)
                    ocr_calls += 1
                    warnings.extend(ocr_result.warnings)
                    if ocr_result.status in {"runtime_failed", "backend_unavailable", "models_missing"}:
                        ocr_runtime_failed = True
                    text = sanitize_whitespace(ocr_result.text)
                    if text:
                        chunks.append(
                            self.make_chunk(
                                text,
                                source_type="video_frame_ocr",
                                source_path=str(path),
                                location={"frame_index": frame_index},
                                metadata={"frame_index": frame_index, "ocr_backend": ocr_result.backend},
                            )
                        )
                except Exception as exc:
                    warnings.append("Video frame OCR step failed; continuing with next sampled frame.")
                sampled += 1
                frame_index += 1
                if ocr_runtime_failed:
                    warnings.append("Video OCR disabled for remaining frames after backend issue.")
                    break
        finally:
            capture.release()

        if sampled >= self.config.runtime.max_video_frames:
            warnings.append("Video frame OCR limit reached; remaining frames skipped.")

        return self.build_result(
            chunks=chunks,
            metadata={
                "structured": False,
                "ocr_used": ocr_calls > 0,
                "ocr_calls": ocr_calls,
                "sampled_frames": sampled,
                "duplicate_frames_skipped": duplicate_frames,
                "fps": fps,
                "frame_step": frame_step,
                "ocr_runtime_failed": ocr_runtime_failed,
                "ocr_backend": ocr_status_payload.get("backend"),
                "ocr_device": ocr_status_payload.get("device"),
                "ocr_status": ocr_status_payload.get("status"),
            },
            warnings=warnings,
        )
