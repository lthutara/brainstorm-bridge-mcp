import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from classifier import classify_file

DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/mnt/c/Users/lokes/Downloads")

KNOWN_PROJECT_TARGETS = {
    "tekku_research": "/mnt/c/Users/lokes/ai-projects/nextgen-technologies/article_research",
    "study_notes": "/mnt/c/Users/lokes/ai-projects/nextgen-technologies/study_notes",
    "ai_brainstorming": os.path.join(DOWNLOADS_DIR, "AI_Brainstorming"),
    "school_cbse": os.path.join(DOWNLOADS_DIR, "School_CBSE"),
    "resumes_career": os.path.join(DOWNLOADS_DIR, "Resumes_Career"),
    "official_financial": os.path.join(DOWNLOADS_DIR, "Official_Financial")
}

def scan_and_plan_organization(
    category_filter: str = "all",
    days: int = 180,
    downloads_dir: str = DOWNLOADS_DIR
) -> Dict[str, Any]:
    """
    Scan Downloads folder and generate a clean organization plan.
    Does not move any files.
    """
    cutoff = datetime.now() - timedelta(days=days)
    plan = {
        "downloads_dir": downloads_dir,
        "total_scanned": 0,
        "categories_summary": {},
        "moves": []
    }

    try:
        entries = os.scandir(downloads_dir)
    except Exception as e:
        return {"error": f"Cannot scan downloads directory: {e}"}

    for entry in entries:
        # Ignore subdirectories (already organized or system folders)
        if not entry.is_file():
            continue
        # Ignore Windows hidden/lock files
        if entry.name.startswith(("~$", ".")):
            continue

        try:
            stat = entry.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)
            if mtime < cutoff:
                continue
        except Exception:
            continue

        plan["total_scanned"] += 1
        classification = classify_file(entry.name, entry.path)
        cat = classification["category"]

        if category_filter != "all" and cat != category_filter:
            continue

        target_folder = os.path.join(downloads_dir, classification["folder"])
        target_path = os.path.join(target_folder, entry.name)

        plan["categories_summary"][cat] = plan["categories_summary"].get(cat, 0) + 1
        plan["moves"].append({
            "file_name": entry.name,
            "source_path": entry.path,
            "target_folder": target_folder,
            "target_path": target_path,
            "category": cat,
            "category_label": classification["label"],
            "size_kb": round(stat.st_size / 1024, 1),
            "modified_at": mtime.strftime("%Y-%m-%d %H:%M")
        })

    return plan

def execute_organization(
    category_filter: str = "all",
    days: int = 180,
    dry_run: bool = True,
    downloads_dir: str = DOWNLOADS_DIR
) -> Dict[str, Any]:
    """
    Execute organization plan. If dry_run=True, only previews planned moves.
    If dry_run=False, moves files into their respective categorized subfolders.
    """
    plan = scan_and_plan_organization(category_filter=category_filter, days=days, downloads_dir=downloads_dir)
    if "error" in plan:
        return plan

    moves = plan.get("moves", [])
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "message": f"Organization preview: {len(moves)} files planned for categorization.",
            "total_files": len(moves),
            "categories": plan["categories_summary"],
            "planned_moves": moves[:25] # Show first 25 preview moves
        }

    # Execute moves safely
    moved_count = 0
    errors = []
    for item in moves:
        src = item["source_path"]
        dst_folder = item["target_folder"]
        dst = item["target_path"]

        try:
            os.makedirs(dst_folder, exist_ok=True)
            # If destination already exists with same name, add unique suffix
            if os.path.exists(dst):
                base, ext = os.path.splitext(item["file_name"])
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dst = os.path.join(dst_folder, f"{base}_{timestamp}{ext}")

            shutil.move(src, dst)
            moved_count += 1
        except Exception as e:
            errors.append({"file": item["file_name"], "error": str(e)})

    return {
        "success": True,
        "dry_run": False,
        "message": f"Successfully organized and moved {moved_count} files into categorized folders.",
        "moved_count": moved_count,
        "error_count": len(errors),
        "errors": errors
    }

def file_document_to_project(
    file_name: str,
    target_project: str = "tekku_research",
    copy_or_move: str = "copy",
    downloads_dir: str = DOWNLOADS_DIR
) -> Dict[str, Any]:
    """
    Move or copy a specific document from Downloads into a project workspace folder.
    """
    # 1. Resolve source file
    src_path = None
    if os.path.isabs(file_name) and os.path.exists(file_name):
        src_path = file_name
    else:
        candidate = os.path.join(downloads_dir, file_name)
        if os.path.exists(candidate):
            src_path = candidate
        else:
            # Check inside categorized subfolders as well!
            for root, dirs, files in os.walk(downloads_dir):
                if file_name.lower() in [f.lower() for f in files]:
                    for f in files:
                        if f.lower() == file_name.lower():
                            src_path = os.path.join(root, f)
                            break
                if src_path:
                    break

    if not src_path or not os.path.exists(src_path):
        return {"error": f"File '{file_name}' not found in Downloads or subfolders."}

    # 2. Resolve destination folder
    dest_dir = KNOWN_PROJECT_TARGETS.get(target_project.lower(), target_project)
    if not os.path.isabs(dest_dir):
        dest_dir = os.path.abspath(dest_dir)

    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(src_path))

    # 3. Perform copy or move
    action = copy_or_move.lower()
    if action == "move":
        shutil.move(src_path, dest_path)
    else:
        shutil.copy2(src_path, dest_path)

    return {
        "success": True,
        "action": action,
        "source_file": src_path,
        "destination_file": dest_path,
        "target_project": target_project,
        "file_size_kb": round(os.path.getsize(dest_path) / 1024, 1)
    }
