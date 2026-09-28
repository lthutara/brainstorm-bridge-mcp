import os
import docx

def parse_docx(file_path: str) -> str:
    """
    Parse a .docx document into clean, readable Markdown.
    Preserves headings (#, ##, ###), bullet lists, and tables.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = docx.Document(file_path)
    output_lines = []

    for elem in doc.element.body:
        # Check if paragraph
        if elem.tag.endswith('p'):
            p = docx.text.paragraph.Paragraph(elem, doc)
            text = p.text.strip()
            if not text:
                continue

            style_name = (p.style.name or "").lower()
            if "heading 1" in style_name:
                output_lines.append(f"\n# {text}\n")
            elif "heading 2" in style_name:
                output_lines.append(f"\n## {text}\n")
            elif "heading 3" in style_name:
                output_lines.append(f"\n### {text}\n")
            elif "heading 4" in style_name:
                output_lines.append(f"\n#### {text}\n")
            elif "list" in style_name or "bullet" in style_name or text.startswith(("•", "-", "*", "–")):
                clean_text = text.lstrip("•-*– \t")
                output_lines.append(f"- {clean_text}")
            elif text.startswith(tuple(f"{i}." for i in range(1, 20))):
                output_lines.append(text)
            else:
                output_lines.append(text)

        # Check if table
        elif elem.tag.endswith('tbl'):
            table = docx.table.Table(elem, doc)
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.replace("\n", " ").strip() for cell in row.cells]
                table_rows.append(row_cells)

            if table_rows:
                output_lines.append("")
                # Header row
                header = table_rows[0]
                output_lines.append("| " + " | ".join(header) + " |")
                output_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                for r in table_rows[1:]:
                    # Match column length
                    if len(r) < len(header):
                        r = r + [""] * (len(header) - len(r))
                    elif len(r) > len(header):
                        r = r[:len(header)]
                    output_lines.append("| " + " | ".join(r) + " |")
                output_lines.append("")

    return "\n\n".join(output_lines)
