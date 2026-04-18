# Debug Artifacts

## Purpose

Debug artifacts are workflow-oriented JSON files designed for developer inspection.

They help answer:

- what files were scanned
- what extraction previews looked like
- what chunk types were produced
- what detector findings were generated
- what metadata the workflow collected

## Base Location

All workflow debug artifacts live under:

```text
<output>/debug/
```

Common subdirectories:

- `pdf_scan`
- `text_scan`
- `structured_scan`
- `image_scan`
- `video_scan`
- `detector_lab`

## Workflow Artifact Map

### `output/debug/pdf_scan`

Typical file:

- `pdf_workflow_preview.json`

Contains:

- invalid PDF names
- preview count
- per-file preview payloads

Useful for:

- OCR fallback inspection
- invalid PDF debugging
- checking produced chunk types such as `pdf_text`, `pdf_image_ocr`, `pdf_page_ocr`

### `output/debug/text_scan`

Typical file:

- `preview.json`

Contains:

- counts by type
- text stats
- preview payloads

Useful for:

- checking docx/rtf/txt routing
- verifying chunk counts
- seeing extractor names and sample text

### `output/debug/structured_scan`

Typical file:

- `structured_preview.json`

Contains:

- structured stats
- preview payloads
- row counts
- columns
- detected column hints

Useful for:

- understanding structured traversal behavior
- validating preview-only mode
- checking metadata produced by CSV/JSON/Parquet/Excel extractors

### `output/debug/image_scan`

Typical file:

- `image_preview.json`

Contains:

- OCR availability
- OCR status message
- preview payloads

Useful for:

- verifying OCR availability handling
- checking image OCR output without full-scan noise

### `output/debug/video_scan`

Typical file:

- `video_preview.json`

Contains:

- OCR availability
- OCR status message
- preview payloads

Useful for:

- checking frame-sampled OCR output
- verifying video workflow integration

### `output/debug/detector_lab`

Typical file:

- `detector_findings.json`

Contains:

- input source
- masked findings
- confidence
- explanation
- sanitized source context

Useful for:

- detector tuning
- validator behavior inspection
- explanation debugging

## Preview JSON Shape

Workflow preview payloads are built from `WorkflowPreview`.

Common shape:

```json
{
  "title": "Extraction Preview: sample.pdf",
  "items": [
    {
      "path": "C:/.../sample.pdf",
      "file_type": "pdf",
      "metadata": { "...": "..." },
      "warnings": [],
      "sample_chunks": [
        {
          "location": "{\"page\": 1}",
          "source_type": "pdf_text",
          "source_path": "C:/.../sample.pdf",
          "text": "..."
        }
      ],
      "sample_rows": []
    }
  ]
}
```

## Important Fields

Inside `sample_chunks`, expect:

- `location`
- `source_type`
- `source_path`
- `text`
- `columns`
- `metadata`

These are especially important after multimodal extraction changes because they expose where a chunk came from.

## How To Use Artifacts During Development

### For PDF

Look for:

- whether chunk source types are `pdf_text` or OCR-based
- page metadata
- invalid PDFs

### For structured files

Look for:

- row counts
- columns
- structured hints
- truncation behavior

### For OCR

Look for:

- OCR availability message
- whether warnings show expected fast/deep behavior
- whether previews contain OCR-derived chunks

### For detectors

Look for:

- masked findings only
- confidence values
- explanation strings
- detector context quality

## Relationship To `scan.log`

Debug artifacts are not a replacement for `scan.log`.

Use artifacts when you want:

- compact structured preview data
- chunk-level visibility
- workflow metadata

Use `scan.log` when you want:

- parser/runtime errors
- stack traces
- detailed logging chronology

