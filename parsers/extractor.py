import re
import os
from typing import Dict, Any, List

def extract_discussion_structure(raw_text: str, file_name: str) -> Dict[str, Any]:
    """
    Analyzes raw discussion text and extracts:
    - Inferred Title / Topic
    - Core Goals & Executive Summary
    - Architecture & Technical Decisions
    - Actionable Roadmap Items / Tasks
    """
    lines = raw_text.splitlines()

    # 1. Infer Title
    title = ""
    for l in lines[:15]:
        clean = l.strip().lstrip("#").strip()
        if clean and len(clean) > 4 and not clean.startswith(("Document:", "Topic:", "Page", "---")):
            title = clean[:120]
            break
    if not title:
        base = os.path.splitext(file_name)[0]
        title = base.replace("_", " ").replace("-", " ").title()

    # 2. Extract Executive Summary or first substantial paragraph
    summary_paras = []
    for p in raw_text.split("\n\n"):
        p_clean = p.strip()
        if not p_clean or p_clean.startswith("#") or p_clean.startswith("|") or len(p_clean) < 40:
            continue
        summary_paras.append(p_clean)
        if len(summary_paras) >= 2:
            break
    summary = "\n\n".join(summary_paras) if summary_paras else "No summary paragraph found."

    # 3. Detect Key Decisions / Architectural Highlights
    decisions = []
    decision_triggers = [
        "architecture", "decision", "approach", "chosen", "pattern", "strategy",
        "trade-off", "tradeoff", "standard", "protocol", "framework", "database", "stack"
    ]
    for p in raw_text.split("\n\n"):
        p_lower = p.lower()
        if any(trig in p_lower for trig in decision_triggers) and len(p.strip()) > 30:
            first_line = p.strip().split("\n")[0]
            if len(first_line) < 200:
                decisions.append(first_line)
        if len(decisions) >= 8:
            break

    # 4. Extract Actionable Items / Roadmap Tasks
    action_items = []
    
    # Priority action patterns (checkboxes, explicit action keywords)
    explicit_task_patterns = [
        r"^(?:[-*•]|\d+\.)?\s*\[[ x]\]\s*(.+)$",
        r"^(?:[-*•]|\d+\.)\s*(?:TODO|Task|Action|Step|Phase|Milestone)\s*\d*[:\-]\s*(.+)$",
        r"^(?:Phase|Step|Sprint|Milestone)\s*\d+[:\-]\s*(.+)$"
    ]
    
    in_action_section = False
    action_section_triggers = ["action item", "roadmap", "todo", "tasks", "next step", "implementation plan", "milestone"]

    for line in lines:
        line_strip = line.strip()
        if not line_strip or line_strip.startswith(("|", "---")):
            continue

        # Check if heading denotes an Action section
        if line_strip.startswith("#"):
            h_lower = line_strip.lower()
            in_action_section = any(t in h_lower for t in action_section_triggers)
            continue

        matched = False
        task_text = ""

        # Check explicit patterns first
        for pat in explicit_task_patterns:
            m = re.match(pat, line_strip, re.IGNORECASE)
            if m:
                task_text = m.group(1).strip()
                matched = True
                break

        # If inside an Action/Roadmap section, standard bullets are also tasks
        if not matched and in_action_section:
            bullet_m = re.match(r"^(?:[-*•]|\d+\.)\s*(.+)$", line_strip)
            if bullet_m:
                task_text = bullet_m.group(1).strip()
                matched = True

        if matched and task_text:
            if 8 < len(task_text) < 180 and not task_text.lower().startswith(("http", "note:", "tip:")):
                # Determine priority
                priority = "P2 - Medium"
                lower = task_text.lower()
                if any(w in lower for w in ["critical", "urgent", "core", "p0", "p1", "first", "must", "immediate"]):
                    priority = "P1 - High"
                elif any(w in lower for w in ["optional", "later", "nice to have", "p3", "future", "backlog"]):
                    priority = "P3 - Low"

                action_items.append({
                    "title": task_text,
                    "description": f"Extracted from discussion: {file_name}",
                    "priority": priority
                })
        if len(action_items) >= 30:
            break

    return {
        "title": title,
        "file_name": file_name,
        "summary": summary,
        "key_decisions": decisions,
        "action_items": action_items,
        "action_items_count": len(action_items)
    }
