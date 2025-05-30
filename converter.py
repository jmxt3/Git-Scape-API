#!/usr/bin/env python3
"""
Handles Git repository cloning, analysis, and Markdown digest generation.
Provides functionality to walk repository files, filter text-based files,
and generate a structured Markdown output of the repository's content.
Includes progress reporting capabilities for long-running operations.

Author: João Machete
"""
import os
import sys
import tempfile
import shutil
import subprocess
import gc
import logging
from pathlib import Path
from typing import Optional, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file
MAX_DIRECTORY_DEPTH = 20  # Maximum depth of directory traversal
MAX_FILES = 10_000  # Maximum number of files to process
MAX_TOTAL_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB total repo size
CHUNK_SIZE = 1024 * 1024  # 1 MB

IGNORED_DIRS = {".git", "__pycache__"}
IGNORED_FILES = {
    ".DS_Store",
    "Zone.Identifier",
    ".jpeg", ".jpg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heif", ".heic",
    ".avif", ".svg", ".psd", ".raw", ".eps", ".pdf", ".ico", ".exr", ".tga", ".dds",
    ".wdp", ".dng", ".ppm"
}

TEXT_EXTS = {
    ".py",          # Python
    ".js",          # JavaScript
    ".ts",          # TypeScript
    ".java",        # Java (source)
    ".go",          # Go
    ".rs",          # Rust
    ".c",           # C
    ".cpp",         # C++
    ".h",           # C/C++ Header
    ".hpp",         # C++ Header (alternative)
    ".cs",          # C#
    ".fs",          # F#
    ".fsi",         # F# Interface
    ".swift",       # Swift
    ".kt",          # Kotlin
    ".rb",          # Ruby
    ".php",         # PHP
    ".pl",          # Perl
    ".lua",         # Lua
    ".scala",       # Scala
    ".groovy",      # Groovy
    ".dart",        # Dart
    ".r",           # R
    ".sh",          # Shell Script (generic)
    ".bash",        # Bash Script
    ".zsh",         # Zsh Script
    ".bat",         # Windows Batch Script
    ".ps1",         # PowerShell Script
    ".psm1",        # PowerShell Module
    ".tcl",         # TCL
    ".m",           # Objective-C / MATLAB script
    ".elm",         # Elm
    ".ex",          # Elixir
    ".exs",         # Elixir Script
    ".clj",         # Clojure
    ".html",        # HTML
    ".htm",         # HTML (alternative)
    ".css",         # CSS
    ".scss",        # SCSS (Sass)
    ".sass",        # Sass (indented syntax)
    ".less",        # LESS
    ".vue",         # Vue.js Single File Components
    ".jsx",         # JavaScript XML (React)
    ".tsx",         # TypeScript XML (React)
    ".hbs",         # Handlebars templates
    ".handlebars",  # Handlebars templates (alternative)
    ".mustache",    # Mustache templates
    ".jinja",       # Jinja templates
    ".md",          # Markdown
    ".markdown",    # Markdown (alternative)
    ".txt",         # Plain Text
    ".json",        # JSON
    ".yml",         # YAML
    ".yaml",        # YAML (alternative)
    ".xml",         # XML
    ".toml",        # TOML
    ".graphql",     # GraphQL Schema/Query
    ".sql",         # SQL Queries
}

def clone_repository(repo_url: str, clone_path: str, github_token: Optional[str] = None, subpath: Optional[str] = None):
    """
    Clone a repository using sparse checkout and blob filtering to minimize memory usage.
    """
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)
    os.makedirs(clone_path, exist_ok=True)
    env = os.environ.copy()
    if github_token:
        env["GIT_ASKPASS"] = "echo"
        env["GIT_TERMINAL_PROMPT"] = "0"
        repo_url = repo_url.replace("https://", f"https://{github_token}@")
    clone_cmd = [
        "git", "clone", "--filter=blob:none", "--sparse", "--depth=1", repo_url, clone_path
    ]
    subprocess.run(clone_cmd, check=True, env=env)
    if subpath:
        # Enable sparse checkout for a specific subpath
        subprocess.run(["git", "-C", clone_path, "sparse-checkout", "set", subpath], check=True, env=env)

def is_text_file(path: Path) -> bool:
    ext = path.suffix.lower()
    return ext in TEXT_EXTS

def get_total_repo_size(repo_path: str) -> int:
    total = 0
    for root, dirs, files in os.walk(repo_path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except Exception:
                continue
    return total

def read_file_in_chunks(path: Path, chunk_size: int = CHUNK_SIZE):
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

def trace_repo(repo_path: str, file_callback: Optional[Callable[[Path], None]] = None):
    """
    Walk the repo, process files in a memory-efficient way, and call file_callback for each file.
    """
    stats = {"total_files": 0, "total_size": 0}
    for root, dirs, files in os.walk(repo_path):
        # Filter ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            path = Path(root) / file
            if path.suffix.lower() in IGNORED_FILES or path.name in IGNORED_FILES:
                continue
            if not is_text_file(path):
                continue
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                logger.info(f"Skipping large file: {path} ({file_size} bytes)")
                continue
            if stats["total_files"] >= MAX_FILES or stats["total_size"] + file_size > MAX_TOTAL_SIZE_BYTES:
                logger.warning("File or size limit reached, stopping traversal.")
                return
            stats["total_files"] += 1
            stats["total_size"] += file_size
            if file_callback:
                file_callback(path)
            gc.collect()  # Free memory after each file

def print_tree(repo_path: str) -> list[str]:
    """
    Print a tree structure of the repository (memory efficient).
    """
    tree_lines = []
    for root, dirs, files in os.walk(repo_path):
        level = root.replace(repo_path, '').count(os.sep)
        indent = ' ' * 4 * level
        tree_lines.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            tree_lines.append(f"{subindent}{f}")
    return tree_lines

def generate_markdown_digest(repo_url: str, repo_path: str, progress_callback=None) -> str:
    """
    Generate a Markdown digest of the repository, reading large files in chunks.
    """
    digest_lines = [f"# Repository Digest for {repo_url}\n"]
    def process_file(path: Path):
        digest_lines.append(f"\n## {path.relative_to(repo_path)}\n")
        try:
            for chunk in read_file_in_chunks(path):
                try:
                    digest_lines.append(chunk.decode("utf-8", errors="replace"))
                except Exception:
                    digest_lines.append("[Error decoding chunk]\n")
        except Exception as e:
            digest_lines.append(f"[Error reading file: {e}]\n")
        if progress_callback:
            progress_callback(path)
    trace_repo(repo_path, file_callback=process_file)
    gc.collect()
    return "".join(digest_lines)

# If run as script, keep the CLI for backward compatibility
if __name__ == "__main__":
    # Example usage: python converter.py <repo_url> <clone_path>
    import sys
    if len(sys.argv) >= 3:
        repo_url = sys.argv[1]
        clone_path = sys.argv[2]
        clone_repository(repo_url, clone_path)
        print("\n".join(print_tree(clone_path)))
        print("\n--- Markdown Digest ---\n")
        print(generate_markdown_digest(repo_url, clone_path))
    else:
        print("Usage: python converter.py <repo_url> <clone_path>")
