import os
import json

def parse_text_or_json(file_path: str) -> str:
    """
    Parse a plain text, Markdown, or JSON file.
    If the file is JSON and represents a chat export (e.g., ChatGPT / Claude / DeepSeek),
    it is automatically reconstructed into clean turn-by-turn markdown.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _format_json_chat(data, file_path)
        except Exception as e:
            # Fallback to plain text read
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

    # .md or .txt
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _format_json_chat(data, file_path: str) -> str:
    """Format various JSON chat exports into markdown."""
    lines = [f"# Chat Export: {os.path.basename(file_path)}\n"]

    # 1. Standard ChatGPT export format: list of conversations or single conversation
    # Structure often has 'title', 'mapping' dict where each node has 'message'
    if isinstance(data, dict):
        if "title" in data:
            lines.append(f"**Topic**: {data['title']}\n")

        if "mapping" in data:
            # ChatGPT mapping
            mapping = data["mapping"]
            for node_id, node in mapping.items():
                msg = node.get("message")
                if not msg:
                    continue
                author = msg.get("author", {}).get("role", "system")
                content = msg.get("content", {})
                parts = content.get("parts", [])
                text_content = ""
                for part in parts:
                    if isinstance(part, str):
                        text_content += part + "\n"
                    elif isinstance(part, dict) and "text" in part:
                        text_content += part["text"] + "\n"

                if text_content.strip():
                    role_label = "👤 User" if author == "user" else ("🤖 Assistant" if author == "assistant" else f"⚙️ {author.title()}")
                    lines.append(f"### {role_label}\n\n{text_content.strip()}\n\n---\n")
            return "\n".join(lines)

        # Generic messages array: {"messages": [{"role": "...", "content": "..."}]}
        if "messages" in data and isinstance(data["messages"], list):
            for m in data["messages"]:
                role = m.get("role", "user")
                role_label = "👤 User" if role == "user" else "🤖 Assistant"
                content = m.get("content", "")
                lines.append(f"### {role_label}\n\n{content}\n\n---\n")
            return "\n".join(lines)

    elif isinstance(data, list):
        # Array of message dicts
        if data and isinstance(data[0], dict) and ("role" in data[0] or "content" in data[0]):
            for m in data:
                role = m.get("role", "user")
                role_label = "👤 User" if role == "user" else "🤖 Assistant"
                content = m.get("content", "")
                lines.append(f"### {role_label}\n\n{content}\n\n---\n")
            return "\n".join(lines)

    # Fallback: pretty JSON
    return json.dumps(data, indent=2, ensure_ascii=False)
