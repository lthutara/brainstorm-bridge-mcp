import os
import re
from typing import Dict, Any

# Keyword signals for AI, engineering, and technical discussions
AI_TECH_KEYWORDS = {
    "agent", "roadmap", "ai", "llm", "deepseek", "chatgpt", "claude", "gemini",
    "prompt", "architecture", "mcp", "spec", "freebsd", "linux", "driver",
    "course", "kernel", "tekku", "myplanner", "pipeline", "transcription",
    "rag", "langchain", "dataset", "evaluation", "benchmark", "inference",
    "token", "guide", "tutorial", "system", "tracker", "launch", "toolbox",
    "youtube", "newsletter", "workflow", "model", "neural", "python", "fastapi"
}

# Keyword signals for School / Academic / CBSE
ACADEMIC_KEYWORDS = {
    "cbse", "pan india", "assignment", "qp", "pt-2", "pt1", "pt2", "pt-1",
    "class_vii", "class_vi", "class vii", "class vi", "syllabus", "question paper",
    "maths", "physics", "chemistry", "biology", "hindi sl", "social science",
    "computer science", "ch-", "chapter", "assessment"
}

# Keyword signals for Resumes & Career
RESUME_KEYWORDS = {
    "resume", "curriculum vitae", "cv", "biodata", "job_description", "profile"
}

# Keyword signals for Official / Financial / Legal / Bills
OFFICIAL_KEYWORDS = {
    "challan", "udyam", "invoice", "receipt", "bank", "statement", "tax",
    "registration", "certificate", "agreement", "salary", "payslip", "bill"
}

MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".mp3", ".wav", ".mp4", ".mov", ".mkv"}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".7z", ".rar"}
INSTALLER_EXTS = {".exe", ".msi", ".deb", ".dmg", ".pkg"}

def classify_file(file_name: str, file_path: str = "") -> Dict[str, Any]:
    """
    Classify a file into one of:
    - ai_discussions: AI chat exports, tech roadmaps, programming specs
    - academic_cbse: School/CBSE assignments, question papers
    - resumes_career: Resumes, CVs, career documents
    - official_financial: Challans, invoices, tax, registration docs
    - media: Images, audio, video
    - installers_archives: Exe, zip, msi
    - other: General unclassified
    """
    ext = os.path.splitext(file_name)[1].lower()
    name_clean = file_name.lower().replace("_", " ").replace("-", " ")
    name_words = set(re.findall(r'[a-zA-Z0-9]+', file_name.lower()))

    def matches_keywords(kw_set):
        for kw in kw_set:
            if " " in kw:
                if kw in name_clean:
                    return True
            else:
                if kw in name_words:
                    return True
        return False

    # 1. Media
    if ext in MEDIA_EXTS:
        return {
            "category": "media",
            "label": "🎨 Media & Photos",
            "folder": "Media_Photos",
            "confidence": 0.95
        }

    # 2. Installers & Archives
    if ext in INSTALLER_EXTS or ext in ARCHIVE_EXTS:
        return {
            "category": "installers_archives",
            "label": "📦 Installers & Archives",
            "folder": "Installers_Archives",
            "confidence": 0.95
        }

    # 3. Academic / CBSE
    if matches_keywords(ACADEMIC_KEYWORDS):
        return {
            "category": "academic_cbse",
            "label": "📚 Academic & School CBSE",
            "folder": "School_CBSE",
            "confidence": 0.9
        }

    # 4. Resumes & Career
    if matches_keywords(RESUME_KEYWORDS):
        return {
            "category": "resumes_career",
            "label": "💼 Resume & Career",
            "folder": "Resumes_Career",
            "confidence": 0.9
        }

    # 5. Official / Financial
    if matches_keywords(OFFICIAL_KEYWORDS) or "maintenance" in name_clean:
        return {
            "category": "official_financial",
            "label": "📄 Official & Financial",
            "folder": "Official_Financial",
            "confidence": 0.85
        }

    # 6. AI / Technical Discussions
    if ext in (".md", ".json"):
        # Markdown and JSON in Downloads are overwhelmingly developer/chat notes
        return {
            "category": "ai_discussions",
            "label": "🤖 AI Discussion & Tech Roadmap",
            "folder": "AI_Brainstorming",
            "confidence": 0.85
        }

    if ext in (".docx", ".txt", ".pdf"):
        # Check title keywords with word boundaries
        if matches_keywords(AI_TECH_KEYWORDS):
            return {
                "category": "ai_discussions",
                "label": "🤖 AI Discussion & Tech Roadmap",
                "folder": "AI_Brainstorming",
                "confidence": 0.9
            }

        # If file_path is provided and small, sample first 1KB
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) < 20 * 1024 * 1024:
            try:
                snippet = ""
                if ext == ".txt":
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        snippet = f.read(1500).lower()
                elif ext == ".docx":
                    import docx
                    d = docx.Document(file_path)
                    snippet = " ".join([p.text for p in d.paragraphs[:5]]).lower()

                if snippet and any(k in snippet for k in AI_TECH_KEYWORDS):
                    return {
                        "category": "ai_discussions",
                        "label": "🤖 AI Discussion & Tech Roadmap",
                        "folder": "AI_Brainstorming",
                        "confidence": 0.8
                    }
            except Exception:
                pass

    return {
        "category": "other",
        "label": "📁 Other Document",
        "folder": "Other_Downloads",
        "confidence": 0.5
    }
