import os
import re
from io import BytesIO
from typing import Dict, Any, List, Tuple
from pypdf import PdfReader

class DocumentExtractor:
    """
    Handles PDF and Image document intake, table boundary alignment,
    and text normalization for medical laboratory reports.
    """

    @staticmethod
    def extract_from_pdf(file_bytes: bytes) -> Dict[str, Any]:
        """
        Extracts structured text and tabular lines from multi-page PDFs.
        """
        try:
            reader = PdfReader(BytesIO(file_bytes))
            raw_pages = []
            structured_lines = []

            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                raw_pages.append(page_text)
                
                # Split and normalize lines
                for line in page_text.splitlines():
                    cleaned = line.strip()
                    if cleaned:
                        structured_lines.append(cleaned)

            full_text = "\n".join(raw_pages).strip()
            table_rows = DocumentExtractor._detect_tabular_rows(structured_lines)

            return {
                "success": True,
                "document_type": "pdf",
                "page_count": len(reader.pages),
                "full_text": full_text,
                "structured_lines": structured_lines,
                "detected_table_rows": table_rows
            }
        except Exception as e:
            return {
                "success": False,
                "document_type": "pdf",
                "error": str(e),
                "full_text": "",
                "structured_lines": [],
                "detected_table_rows": []
            }

    @staticmethod
    def _detect_tabular_rows(lines: List[str]) -> List[Dict[str, Any]]:
        """
        Heuristic tabular row segmenter: identifies rows containing parameter names,
        numeric metrics, units, and reference intervals.
        """
        rows = []
        for line in lines:
            # Look for lines containing numbers with units or intervals
            # e.g., "Hemoglobin 11.4 g/dL 12.0 - 15.5 Low"
            # or "TSH : 5.2 uIU/mL (0.4 - 4.5)"
            tokens = re.split(r'\s{2,}|\t|\|', line)
            if len(tokens) >= 2:
                rows.append({
                    "raw_line": line,
                    "columns": [t.strip() for t in tokens if t.strip()]
                })
            else:
                # Fallback regex search for pattern: Name ... Number [Unit] ... Range
                match = re.search(r'([A-Za-z0-9\s\(\)\/\-\.\,]+?)\s+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\%\/\µ\^0-9]+)?\s*[\(\[]?([<>]?\s*\d+(?:\.\d+)?\s*(?:-|to)\s*[<>]?\s*\d+(?:\.\d+)?)?', line)
                if match:
                    rows.append({
                        "raw_line": line,
                        "columns": [g.strip() for g in match.groups() if g]
                    })
        return rows

    @staticmethod
    def extract_from_bytes(file_bytes: bytes, filename: str, mime_type: str = "") -> Dict[str, Any]:
        """
        Unified entrypoint for PDF, plain text, and image documents.
        """
        lower_name = filename.lower()
        if lower_name.endswith(".pdf") or "pdf" in mime_type.lower():
            return DocumentExtractor.extract_from_pdf(file_bytes)
        
        # Check if text format
        if lower_name.endswith((".txt", ".csv", ".tsv", ".log")) or "text" in mime_type.lower():
            try:
                decoded_text = file_bytes.decode("utf-8", errors="ignore").strip()
                structured_lines = [l.strip() for l in decoded_text.splitlines() if l.strip()]
                return {
                    "success": True,
                    "document_type": "text",
                    "page_count": 1,
                    "filename": filename,
                    "full_text": decoded_text,
                    "structured_lines": structured_lines,
                    "detected_table_rows": DocumentExtractor._detect_tabular_rows(structured_lines)
                }
            except Exception as e:
                print(f"Error decoding text document: {e}")

        # For image formats (jpg, png, webp, etc.)
        # Text extraction is complemented by multimodal model or text OCR
        return {
            "success": True,
            "document_type": "image",
            "page_count": 1,
            "filename": filename,
            "mime_type": mime_type or "image/jpeg",
            "file_size_bytes": len(file_bytes),
            "full_text": f"Scanned Visual Laboratory Document: {filename}",
            "structured_lines": [f"Laboratory Image Document: {filename}"],
            "detected_table_rows": []
        }

document_extractor = DocumentExtractor()
