# Extractors

## Contract

Every extractor is expected to return `ExtractionResult`:

- `file_type`
- `extracted_text_chunks`
- `table_records`
- `metadata`
- `warnings`

The downstream detector/classifier pipeline does not care about the original file format. It only consumes normalized chunks and metadata.

## Shared Components

### `BaseExtractor`

Role:

- common helper base
- builds `ExtractionResult`
- constructs `ExtractedChunk`
- exposes `route_resource()`
- provides shared `OCRService` and `EmbeddedResourceRouter`

### `OCRService`

Role:

- centralized OCR availability check
- centralized OCR execution
- reused across image/video and embedded-resource OCR

Used by:

- `ImageOCRExtractor`
- `VideoExtractor`
- `PDFExtractor`
- `DOCXExtractor`
- `HTMLExtractor`
- `EmbeddedResourceRouter`

### `EmbeddedResourceRouter`

Role:

- convert structural resources into normalized chunks
- route `text`, `link`, `metadata`, `image`
- apply OCR only when allowed
- append OCR provenance to metadata

Important behavior:

- in `fast` mode OCR-heavy image resources are skipped
- if OCR is unavailable, resource-level warnings are returned

## Structured Extractors

### `csv_extractor.py`

Input:

- `.csv`

Output:

- `source_type = table_row`
- `row_index`
- `columns`
- `table_records` sample rows

Workflow usage:

- full scan
- structured scan

Fallback / limits:

- tries multiple encodings
- chunked read via `pandas.read_csv(..., chunksize=...)`
- row limit enforced by config

### `json_extractor.py`

Input:

- `.json`
- `.jsonl`

Output:

- `source_type = table_row`
- flattened nested records
- `columns` from flattened keys

Workflow usage:

- full scan
- structured scan

Fallback / limits:

- streaming via `ijson` when available
- falls back to `json.load`
- malformed JSONL rows are skipped with warnings

### `parquet_extractor.py`

Input:

- `.parquet`

Output:

- `source_type = table_row`
- dataframe rows normalized to text

Workflow usage:

- full scan
- structured scan

Fallback / limits:

- reads with pandas
- no explicit chunk streaming at parquet layer in current implementation

### `excel_extractor.py`

Input:

- `.xls`
- `.xlsx`

Output:

- `source_type = table_row`
- sheet name stored in metadata
- `table_records` keeps sampled rows

Workflow usage:

- full scan
- structured scan

Fallback / limits:

- `.xls -> xlrd`
- `.xlsx -> openpyxl`
- if engine is unavailable, extractor raises controlled runtime error
- row limit is enforced

## Text / Document Extractors

### `pdf_extractor.py`

Input:

- `.pdf`

Output source types:

- `pdf_text`
- `pdf_text_sparse`
- `pdf_image_ocr`
- `pdf_page_ocr`

Embedded resource handling:

- extracts text layer first
- extracts embedded page images and routes them through OCR
- for sparse/no-text pages may rasterize page and run OCR fallback

Workflow usage:

- full scan
- pdf scan

Fallback / limits:

- invalid PDFs raise controlled runtime error
- OCR only in deep mode and only if available
- obeys `max_embedded_images_per_file`
- obeys `max_ocr_calls_per_file`
- obeys `max_pdf_ocr_pages`

### `docx_extractor.py`

Input:

- `.docx`

Output source types:

- `docx_paragraph`
- `docx_table_cell`
- `docx_image_ocr`

Embedded resource handling:

- extracts paragraphs
- extracts each table cell as a separate chunk
- iterates embedded image relationships and OCRs them

Workflow usage:

- full scan
- text scan

Fallback / limits:

- embedded image OCR only in deep mode
- skips OCR if unavailable
- obeys image and OCR call limits

### `rtf_extractor.py`

Input:

- `.rtf`

Output source types:

- usually a body-style text chunk

Workflow usage:

- full scan
- text scan

Fallback / limits:

- best effort text extraction
- errors are isolated to the file

### `txt_extractor.py`

Input:

- `.txt`

Output source types:

- body text chunk

Workflow usage:

- full scan
- text scan

Fallback / limits:

- simple direct text read

### `doc_extractor.py`

Input:

- `.doc`

Output:

- best-effort textual extraction

Workflow usage:

- full scan only

Fallback / limits:

- intentionally weak support
- should not crash the whole pipeline

### `html_extractor.py`

Input:

- `.html`
- `.htm`

Output source types:

- `html_text`
- `html_alt_text`
- `html_link`
- `html_metadata`
- `html_image_ocr`

Embedded resource handling:

- visible body text
- `img.alt`
- `img.title`
- link text and href/title context
- meta tags
- local embedded images routed to OCR

Workflow usage:

- full scan

Fallback / limits:

- script/style/noscript removed
- remote/data URI image OCR is skipped
- local image OCR requires deep mode + OCR availability
- obeys image and OCR call limits

## OCR-Heavy Extractors

### `image_ocr_extractor.py`

Input:

- `.jpg`
- `.jpeg`
- `.png`
- `.gif`
- `.tif`
- `.tiff`

Output source types:

- `image_ocr`

Workflow usage:

- full scan
- image scan

Fallback / limits:

- fast mode skips OCR by design
- no OCR -> controlled warning
- invalid image decode -> controlled runtime error

### `video_extractor.py`

Input:

- `.mp4`

Output source types:

- OCR text chunks derived from sampled frames

Workflow usage:

- full scan
- video scan

Fallback / limits:

- frame sampling by configured step
- OCR availability required for useful output
- frame count is limited by config

## Multimodal Extraction Explained

### PDF: text vs image OCR

- `pdf_text` means text came from the native PDF text layer
- `pdf_image_ocr` means text came from an embedded image object inside the PDF
- `pdf_page_ocr` means the entire page was rasterized and OCR’d

### DOCX: text vs embedded image OCR

- `docx_paragraph` means direct paragraph text
- `docx_table_cell` means a structured cell chunk
- `docx_image_ocr` means text extracted from an embedded image object in the document package

### HTML: visible text vs semantic attributes vs image OCR

- `html_text` is visible DOM text
- `html_alt_text` is image attribute text
- `html_link` contains anchor label/title/href context
- `html_metadata` comes from meta tags
- `html_image_ocr` comes from a locally resolvable image file referenced by the HTML

## Where Each Extractor Is Selected

Extractor selection is centralized in:

- `pd_scanner/scanner/file_dispatcher.py`

That file is the single source of truth for suffix-to-extractor mapping.

