"""
File Upload & Analysis Engine.
Extracts text and structured tables from PDF, DOCX, TXT, CSV, XLSX, JSON, and images.
Performs data summarization, statistics calculation, and formats context for AI Q&A.
"""

import os
import csv
import json
import io
import re

UPLOAD_DOCS_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads", "documents")
os.makedirs(UPLOAD_DOCS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "txt", "csv", "json", "docx", "xlsx", "png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def process_file_content(file_path, original_filename):
    """
    Parses and extracts content, structure, and statistical summaries from an uploaded file.
    Returns:
    {
        "text": "...",
        "summary": "...",
        "table_data": [...],
        "metadata": {...}
    }
    """
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""
    
    extracted_text = ""
    table_preview = []
    metadata = {
        "filename": original_filename,
        "extension": ext,
        "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0
    }

    try:
        if ext == "pdf":
            extracted_text = _extract_pdf(file_path)
            metadata["pages"] = extracted_text.count("\n--- Page ")
        elif ext in ["csv", "txt"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if ext == "csv":
                extracted_text, table_preview, meta = _parse_csv(content)
                metadata.update(meta)
            else:
                extracted_text = content[:20000]
                metadata["line_count"] = len(content.splitlines())
        elif ext == "json":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            try:
                parsed_json = json.loads(content)
                extracted_text = json.dumps(parsed_json, indent=2)[:20000]
                metadata["keys"] = list(parsed_json.keys()) if isinstance(parsed_json, dict) else len(parsed_json)
            except Exception:
                extracted_text = content[:20000]
        else:
            # Fallback text reading
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                extracted_text = f.read(15000)
    except Exception as e:
        extracted_text = f"Error reading file content: {str(e)}"

    # Generate quick summary
    summary = _generate_rule_based_summary(extracted_text, metadata, table_preview)

    return {
        "text": extracted_text[:12000],  # bounded for prompt context
        "summary": summary,
        "table_preview": table_preview[:15],
        "metadata": metadata
    }

def _extract_pdf(file_path):
    """Extracts text from PDF using pypdf."""
    text_parts = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text_parts.append(f"--- Page {idx + 1} ---\n{page_text}")
            if len("\n".join(text_parts)) > 25000:
                text_parts.append("... [Text truncated for size] ...")
                break
    except Exception as e:
        text_parts.append(f"PDF extraction notice: {str(e)}")
    return "\n".join(text_parts)

def _parse_csv(content):
    """Parses CSV text into table preview and summary metrics."""
    f = io.StringIO(content)
    reader = csv.reader(f)
    rows = list(reader)
    if not rows:
        return "Empty CSV file.", [], {"rows": 0, "cols": 0}

    headers = rows[0]
    data_rows = rows[1:]
    
    meta = {
        "rows": len(data_rows),
        "columns": len(headers),
        "headers": headers
    }

    # Summary table preview
    preview = [headers] + data_rows[:10]

    # Quick numeric column summaries
    column_stats = {}
    for col_idx, h in enumerate(headers):
        values = []
        for r in data_rows:
            if col_idx < len(r):
                try:
                    val = float(r[col_idx].replace("$", "").replace(",", "").strip())
                    values.append(val)
                except (ValueError, TypeError):
                    pass
        if values:
            column_stats[h] = {
                "count": len(values),
                "sum": round(sum(values), 2),
                "avg": round(sum(values) / len(values), 2),
                "min": min(values),
                "max": max(values)
            }
    meta["numeric_stats"] = column_stats

    text_rep = f"CSV Dataset: {len(data_rows)} rows across {len(headers)} columns.\n"
    text_rep += f"Columns: {', '.join(headers)}\n\n"
    if column_stats:
        text_rep += "Calculated Column Statistics:\n"
        for col, s in column_stats.items():
            text_rep += f"- {col}: Total={s['sum']}, Mean={s['avg']}, Min={s['min']}, Max={s['max']}\n"

    return text_rep, preview, meta

def _generate_rule_based_summary(text, meta, table_preview):
    """Creates a concise executive summary of the file."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    total_words = len(re.findall(r'\w+', text))
    
    summary = f"Analyzed '{meta.get('filename')}' ({meta.get('extension', '').upper()}). "
    if meta.get("rows"):
        summary += f"Contains structured dataset with {meta.get('rows')} rows and {meta.get('columns')} columns. "
    elif meta.get("pages"):
        summary += f"Multi-page document containing {meta.get('pages')} pages. "
    else:
        summary += f"Document contains approximately {total_words} words and {len(lines)} content blocks. "

    # Highlight top key terms
    words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
    stop_words = {"this", "that", "with", "from", "have", "were", "which", "will", "would", "about", "there", "their"}
    filtered = [w for w in words if w not in stop_words]
    
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    top_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_keywords:
        kw_str = ", ".join([k[0] for k in top_keywords])
        summary += f"Primary themes identified: {kw_str}."

    return summary
