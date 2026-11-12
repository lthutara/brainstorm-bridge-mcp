# 🌉 BrainstormBridge (`brainstorm-bridge`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-2.1.0-emerald.svg)](https://modelcontextprotocol.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Security: Prompt Injection Protected](https://img.shields.io/badge/Security-Prompt_Injection_Hardened-green.svg)](#-threat-model--prompt-injection-defense)

**The Secure, Prompt-Injection-Hardened Context Bridge from Chatbot Brainstorms to Coding Agents.**

Bring architecture notes, data schemas, and brainstorming exports from ChatGPT, Claude, DeepSeek, and Gemini directly into **Claude Code, Cursor, Antigravity CLI, and Copilot Workspace**—without the risk of Indirect Prompt Injection (IPI).

---

## 💡 The Problem

Developers love brainstorming architectures in web and mobile chat interfaces (ChatGPT, Claude, DeepSeek) because of their canvas, speed, voice mode, and conversational depth. 

However, transferring that context into terminal coding harnesses is painful and dangerous:
1. **Manual Copy-Paste Fatigue**: Splitting 50-turn chat transcripts into architecture docs and actionable tasks takes hours.
2. **The Prompt Injection Vulnerability**: Ingesting unvetted external downloads or chat exports into autonomous coding agents creates a severe **Indirect Prompt Injection (IPI)** vector. Malicious text, hidden zero-width steganography, or HTML comments can hijack the agent into reading `.env` keys or executing unwanted shell commands.

**BrainstormBridge** solves both problems: it ingests and parses multi-turn chat exports, strips malicious injection vectors, wraps content in an immutable XML sandbox, and automatically synthesizes architecture decisions and a checklisted `ROADMAP.md`.

---

## 📐 Architecture & Security Pipeline

```
┌────────────────────────────────────────┐
│  Web Chat Export (ChatGPT/Claude/etc)  │
│      (.md, .json, .docx, .pdf, .txt)   │
└───────────────────┬────────────────────┘
                    │  (Explicit User Drop)
                    ▼
┌────────────────────────────────────────┐
│   Safe Inbox: ~/.brainstorm-inbox/     │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│            Prompt Injection Sanitizer Layer            │
│  • Strip invisible Unicode zero-width steganography    │
│  • Strip hidden HTML comments (<!-- System: ... -->)   │
│  • Neutralize active instruction-hijacking patterns    │
│  • Enclose in <untrusted_brainstorm_document> sandbox  │
└───────────────────┬────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│           Semantic Synthesizer & Task Engine           │
│  • Inferred Title & Executive Summary                  │
│  • Architectural Decisions & Stack Trade-offs          │
│  • P1 / P2 / P3 Action Items & Roadmaps                │
└───────────────────┬────────────────────────────────────┘
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
┌──────────────┐          ┌──────────────┐
│  ROADMAP.md  │          │ Coding Agent │
│  tasks.json  │          │ (Claude/Agy) │
└──────────────┘          └──────────────┘
```

---

## 🛡️ Threat Model & Prompt Injection Defense

BrainstormBridge enforces **Data-Instruction Separation**:
* **Air-Gapped Inbox (`~/.brainstorm-inbox/`)**: The tool never scans the raw system `Downloads/` directory by default, preventing drive-by downloads or phishing attachments from being processed.
* **Unicode Steganography Stripping**: Strips zero-width non-joiners, word joiners, and hidden BOM marks (`\u200B`, `\u200C`, `\uFEFF`) used to hide instructions from human eyes.
* **Hidden Comment Neutralization**: Strips HTML comment blocks and deceptive invisible CSS tags (`display:none`, `font-size:0px`).
* **XML Sandboxing**: Wraps all ingested context in immutable `<untrusted_brainstorm_document>` tags with explicit boundaries instructing the host model to treat all enclosed text strictly as passive data.

---

## 🚀 Key MCP Tools

| Tool | Description |
| :--- | :--- |
| **`list_inbox_brainstorms`** | Lists recent discussion exports waiting in the safe quarantined inbox. |
| **`ingest_brainstorm`** | Reads, sanitizes, and extracts structured architectural decisions and tasks from `.md`, `.json`, `.docx`, `.pdf`, or `.txt`. |
| **`export_brainstorm_to_roadmap`** | Automatically generates a checklisted **`ROADMAP.md`** or **`tasks.json`** directly in your active project. |
| **`search_inbox`** | Performs fast full-text search across all saved brainstorm sessions. |
| **`export_brainstorm_to_myplanner`** | (Optional) Directly syncs action items into a local MyPlanner database. |

---

## 📦 Installation & Setup

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/lthutara/brainstorm-bridge-mcp.git
cd brainstorm-bridge-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure in your AI Agent Harness

#### For Claude Desktop & Claude Code
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "brainstorm-bridge": {
      "command": "/path/to/brainstorm-bridge/venv/bin/python3",
      "args": ["/path/to/brainstorm-bridge/mcp_server.py"],
      "env": {
        "BRAINSTORM_INBOX_DIR": "~/.brainstorm-inbox"
      }
    }
  }
}
```

#### For Antigravity CLI / Gemini Config (`~/.gemini/config/mcp_config.json`)
```json
{
  "mcpServers": {
    "brainstorm-bridge": {
      "command": "/path/to/brainstorm-bridge/venv/bin/python3",
      "args": ["/path/to/brainstorm-bridge/mcp_server.py"]
    }
  }
}
```

#### For Cursor
Add an MCP server in Cursor Settings $\rightarrow$ Features $\rightarrow$ MCP:
* **Name**: `brainstorm-bridge`
* **Type**: `command`
* **Command**: `/path/to/brainstorm-bridge/venv/bin/python3 /path/to/brainstorm-bridge/mcp_server.py`

---

## 💬 Example Workflow

1. You brainstorm a new feature in ChatGPT or Claude on your phone or web browser and export the chat as `auth-architecture.md`.
2. Move it to your inbox:
   ```bash
   mv ~/Downloads/auth-architecture.md ~/.brainstorm-inbox/
   ```
3. In your coding agent (Claude Code, Cursor, Antigravity):
   > *"I have a brainstorm export named auth-architecture.md in the inbox. Ingest it and generate our roadmap."*
4. BrainstormBridge sanitizes the file, confirms no prompt injection triggers exist, extracts your architectural choices, and writes a pristine `ROADMAP.md` ready for coding!

---

## 🧪 Testing

Run the automated security and unit test suite:
```bash
./venv/bin/python3 -m unittest discover tests
```

---

## 📄 License
MIT License. Free for personal and commercial use. Contributions are welcome!
