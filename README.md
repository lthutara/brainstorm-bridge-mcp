# Downloads MCP Server for AI Chatbot Ideas & Discussions

A Model Context Protocol (MCP) server that monitors the Downloads folder, parses web AI chatbot brainstorming exports (`.docx`, `.md`, `.txt`, `.pdf`, `.json`), and exposes tools for search, extraction, and direct MyPlanner task creation.

## Key Capabilities & Tools

1. **`list_recent_discussions(limit=15, days=14, file_type="")`**
   - Scans the Windows Downloads folder (`/mnt/c/Users/lokes/Downloads`) for recent discussion exports and documents.
   - Returns file sizes, modified timestamps, format extensions, and text preview snippets.

2. **`read_chat_discussion(file_name, extract_structure=True)`**
   - Parses DOCX, PDF, Markdown, Text, and JSON chat exports into clean, formatted Markdown.
   - Automatically extracts inferred title, executive summary, key architectural decisions, and actionable roadmap items.

3. **`search_chat_discussions(query, limit=10, max_files=40)`**
   - Fast full-text search across downloaded AI brainstorming sessions and documents.
   - Returns matching files, matched lines/snippets with context, and occurrence counts.

4. **`import_discussion_to_myplanner(file_name, category="Ideation", sprint="active")`**
   - Automatically parses actionable roadmap tasks from any discussion export.
   - Creates the tasks directly in MyPlanner (`planner.db`), complete with back-links to the source file.

## Configuration in Antigravity

Registered in `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "downloads": {
      "command": "/home/lthutara/ai-projects/chat-ideas-mcp/venv/bin/python3",
      "args": [
        "/home/lthutara/ai-projects/chat-ideas-mcp/mcp_server.py"
      ]
    }
  }
}
```
