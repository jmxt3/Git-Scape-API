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
import subprocess
from pathlib import Path

MAX_FILE_SIZE = 100 * 1024  # 100 KB per file
IGNORED_DIRS = {".git", "__pycache__"}
IGNORED_FILES = {
    ".DS_Store",
    "Zone.Identifier",
    ".jpeg", ".jpg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heif", ".heic",
    ".avif", ".svg", ".psd", ".raw", ".eps", ".pdf", ".ico", ".exr", ".tga", ".dds",
    ".wdp", ".dng", ".ppm"
}

TEXT_EXTS = {
    # Programming & Scripting Languages
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
    ".kts",         # Kotlin Script
    ".rb",          # Ruby
    ".php",         # PHP
    ".pl",          # Perl
    ".pm",          # Perl Module
    ".lua",         # Lua
    ".scala",       # Scala
    ".groovy",      # Groovy
    ".dart",        # Dart
    ".r",           # R
    ".sh",          # Shell Script (generic)
    ".bash",        # Bash Script
    ".zsh",         # Zsh Script
    ".fish",        # Fish Script
    ".bat",         # Windows Batch Script
    ".cmd",         # Windows Command Script
    ".ps1",         # PowerShell Script
    ".psm1",        # PowerShell Module
    ".psd1",        # PowerShell Data File
    ".tcl",         # TCL
    ".m",           # Objective-C / MATLAB script
    ".elm",         # Elm
    ".ex",          # Elixir
    ".exs",         # Elixir Script
    ".cr",          # Crystal
    ".nim",         # Nim
    ".v",           # Verilog
    ".sv",          # SystemVerilog
    ".vhdl",        # VHDL
    ".gd",          # GDScript (Godot Engine)
    ".clj",         # Clojure
    ".cljs",        # ClojureScript
    ".cljc",        # Clojure/ClojureScript

    # Web Development & Templating
    ".html",        # HTML
    ".htm",         # HTML (alternative)
    ".css",         # CSS
    ".scss",        # SCSS (Sass)
    ".sass",        # Sass (indented syntax)
    ".less",        # LESS
    ".vue",         # Vue.js Single File Components
    ".jsx",         # JavaScript XML (React)
    ".tsx",         # TypeScript XML (React)
    ".svelte",      # Svelte components
    ".ejs",         # Embedded JavaScript templates
    ".erb",         # Embedded Ruby (Rails templates)
    ".hbs",         # Handlebars templates
    ".handlebars",  # Handlebars templates (alternative)
    ".mustache",    # Mustache templates
    ".jinja",       # Jinja templates
    ".j2",          # Jinja2 templates (alternative)
    ".twig",        # Twig templates (PHP)
    # Markup & Documentation
    ".md",          # Markdown
    ".markdown",    # Markdown (alternative)
    ".rst",         # reStructuredText
    ".adoc",        # AsciiDoc
    ".asciidoc",    # AsciiDoc (alternative)
    ".tex",         # LaTeX
    ".bib",         # BibTeX (LaTeX bibliography)
    ".org",         # Emacs Org Mode
    # Data Serialization & Configuration
    ".txt",         # Plain Text
    ".json",        # JSON
    ".jsonc",       # JSON with Comments
    ".json5",       # JSON5
    ".yml",         # YAML
    ".yaml",        # YAML (alternative)
    ".xml",         # XML
    ".xsd",         # XML Schema Definition
    ".xsl",         # XSLT Stylesheet
    ".toml",        # TOML
    ".ini",         # INI
    ".cfg",         # Configuration
    ".conf",        # Configuration (generic)
    ".config",      # Configuration (alternative)
    ".properties",  # Java Properties
    ".env",         # Environment Variables (often .env.example, etc.)
    ".graphql",     # GraphQL Schema/Query
    ".gql",         # GraphQL (alternative)
    ".hcl",         # HashiCorp Configuration Language
    ".tf",          # Terraform (HCL)
    ".tfvars",      # Terraform Variables (HCL)
    ".csv",         # Comma-Separated Values
    ".tsv",         # Tab-Separated Values
    ".log",         # Log files (can be large but are text)

    # Build Systems & Project Files
    ".Makefile",    # Makefile (or often just 'Makefile' with no ext)
    ".mk",          # Makefile include
    ".cmake",       # CMake
    # "CMakeLists.txt" is a specific filename, covered by .txt but important
    ".gradle",      # Gradle build script (Groovy)
    ".gradle.kts",  # Gradle build script (Kotlin)
    ".pom",         # Maven Project Object Model (implicitly .xml)
    ".csproj",      # C# Project File (XML)
    ".vbproj",      # VB.NET Project File (XML)
    ".fsproj",      # F# Project File (XML)
    ".sln",         # Visual Studio Solution
    ".xcconfig",    # Xcode Configuration File
    # Version Control & Development Environment
    ".gitignore",   # Git Ignore file
    ".gitattributes",# Git Attributes file
    ".gitmodules",  # Git Modules file
    ".editorconfig",# EditorConfig
    ".prettierrc",  # Prettier configuration (often JSON, YAML, or JS module)
    ".eslintrc",    # ESLint configuration (often JSON, YAML, or JS module)
    ".babelrc",     # Babel configuration (often JSON)
    ".stylelintrc", # Stylelint configuration (often JSON, YAML)
    ".dockerfile",  # Dockerfile (or often just 'Dockerfile' with no ext)
    ".vagrantfile", # Vagrantfile (Ruby syntax)
    # Other Text-Based Files
    ".sql",         # SQL Queries
    ".ddl",         # Data Definition Language (SQL)
    ".patch",       # Patch file
    ".diff",        # Diff file
    ".sub",         # Subtitles (e.g., .srt, .sub - .srt is very common & text)
    ".srt",         # SubRip Subtitle file
    ".vtt",         # WebVTT Subtitle file
    ".cfg",         # Generic config (already listed, but very general)
    ".desktop",     # Linux Desktop Entry files (INI-like)
    ".service",     # Systemd service files (INI-like)
    ".conf",        # Generic config (already listed)
    ".list",        # Plain text lists
    ".theme",       # Theme files (often XML or INI-like)
    ".plantuml",    # PlantUML diagram definition
    ".puml",        # PlantUML (alternative)
    ".iuml",        # PlantUML (alternative)
    ".dot",         # Graphviz DOT language
    ".gv",          # Graphviz (alternative)
    ".http",        # HTTP requests (for testing/docs)
    ".rest",        # REST API requests (for testing/docs)
    ".proto",       # Protocol Buffer definition files
    ".asc",         # PGP armored files (ASCII representation of binary data)
    ".pem"          # Privacy Enhanced Mail (certificates, keys - ASCII)
}

def clone_repository(repo_url, clone_path, github_token=None):
    """Clone the repository from repo_url into clone_path.
    Supports private repositories using a GitHub Personal Access Token.
    Yields progress messages during the cloning process.
    """
    if github_token is None:
        github_token = os.getenv("GITHUB_TOKEN")
    if github_token and repo_url.startswith("https://github.com/"):
        # Insert token into the URL for authentication
        repo_url = repo_url.replace(
            "https://github.com/", f"https://{github_token}:x-oauth-basic@github.com/"
        )
    try:
        # Use Popen to stream output
        process = subprocess.Popen(["git", "clone", "--depth", "1", "--progress", repo_url, clone_path],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                yield f"clone: {line.strip()}"
            process.stdout.close()
        else:
            yield "clone: Failed to capture stdout from git clone process." # Or handle as an error

        return_code = process.wait()
        if return_code:
            # Attempt to get more error details if stderr was redirected to stdout
            # This part is tricky as stdout is already consumed or closed.
            # For simplicity, we'll stick to the original error reporting.
            raise subprocess.CalledProcessError(return_code, process.args)
    except subprocess.CalledProcessError as e:
        # Consider yielding an error message here too, or ensure the calling code handles it
        yield f"clone_error: Error cloning repository: {e}"
        raise RuntimeError(f"Error cloning repository: {e}")
    except FileNotFoundError: # Specifically catch if git command is not found
        yield "clone_error: Git command not found. Please ensure Git is installed and in your PATH."
        raise RuntimeError("Git command not found. Please ensure Git is installed and in your PATH.")
    except Exception as e: # Catch other potential errors
        yield f"clone_error: An unexpected error occurred during cloning: {e}"
        raise RuntimeError(f"An unexpected error occurred during cloning: {e}")

def is_text_file(path: Path) -> bool:
    """Check if a file is a text file based on its extension."""
    ext = path.suffix.lower()
    return ext in TEXT_EXTS

def trace_repo(repo_path: str):
    """
    Go through the repository, yielding file content only (no per-file progress messages).
    Skips ignored directories, ignored files, large files, and binary files.
    """
    all_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            if file in IGNORED_FILES:
                continue
            path = Path(root) / file
            try:
                if path.stat().st_size > MAX_FILE_SIZE:
                    continue
                if not is_text_file(path):
                    continue
                all_files.append(path)
            except FileNotFoundError:
                continue

    for path in all_files:
        rel_path = os.path.relpath(path, repo_path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            yield {"type": "file_content", "path": rel_path, "content": content}
        except Exception as e:
            continue

def print_tree(repo_path: str) -> list[str]:
    """Generate a list of strings representing the directory tree."""
    lines = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        level = os.path.relpath(root, repo_path).count(os.sep)
        indent = "    " * level
        # Handle the case where repo_path is the root itself
        base_name = os.path.basename(root) if root != repo_path else os.path.basename(os.path.abspath(root))
        lines.append(f"{indent}{base_name}/")
        for f in sorted(files):
            if f in IGNORED_FILES:
                continue
            lines.append(f"{indent}    {f}")
    return lines

def generate_markdown_digest(repo_url: str, repo_path: str, progress_callback=None) -> str:
    """
    Generate a Markdown digest for the given repository.
    Includes a directory tree and content of text files.
    Uses progress_callback to report progress during generation.
    Now reports progress as a percentage (0-100%) for each step and per file, sending JSON-serializable dicts.
    """
    if progress_callback is None:
        progress_callback = lambda msg, pct: None # No-op if no callback

    md_parts = []
    progress_callback("Starting Markdown digest generation.", 0)
    md_parts.append(f"# Codebase Digest for {repo_url}\n")

    progress_callback("Generating directory tree...", 10)
    md_parts.append("## Directory Tree\n")
    md_parts.append("```")
    tree_lines = print_tree(repo_path)
    for line in tree_lines:
        md_parts.append(line)
    md_parts.append("```\n")
    progress_callback("Directory tree generated.", 20)

    progress_callback("Digesting files for content...", 30)
    md_parts.append("## Files and Content\n")

    # Gather all files first for progress calculation
    all_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            if file in IGNORED_FILES:
                continue
            path = Path(root) / file
            try:
                if path.stat().st_size > MAX_FILE_SIZE:
                    continue
                if not is_text_file(path):
                    continue
                all_files.append(path)
            except FileNotFoundError:
                continue
    total_files = len(all_files)
    if total_files == 0:
        progress_callback("No files to process.", 90)
    else:
        for idx, path in enumerate(all_files):
            rel_path = os.path.relpath(path, repo_path)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                ext = Path(rel_path).suffix.lstrip(".")
                md_parts.append(f"### {rel_path}\n")
                md_parts.append(f"```{ext}\n{content}\n```\n")
            except Exception:
                continue
            percent = 30 + int((idx + 1) / total_files * 60)
            progress_callback(f"Digesting {idx+1}/{total_files} files...", percent)

    progress_callback("File content processing complete.", 95)
    progress_callback("Markdown digest generation complete.", 100)
    return "\n".join(md_parts)

# If run as script, keep the CLI for backward compatibility
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python converter.py <repo_path_or_git_url>")
        sys.exit(1)
    src = sys.argv[1]

    # Define a simple progress printer for CLI
    def cli_progress_printer(message):
        print(message, file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Construct clone_path within tmpdir
        # Ensure the "repo" subdirectory is used consistently if needed,
        # or clone directly into tmpdir if that's the intention.
        # For simplicity, let's assume clone_repository handles the exact path.
        actual_clone_path = os.path.join(tmpdir, "repo_cli_clone") # Use a distinct name or pass tmpdir directly

        if src.startswith("http://") or src.startswith("https://") or src.endswith(".git"):
            cli_progress_printer(f"Cloning {src} into {actual_clone_path}...")
            try:
                for progress_update in clone_repository(src, actual_clone_path):
                    cli_progress_printer(progress_update)
                # After successful clone, repo_path for digest is actual_clone_path
                repo_to_digest = actual_clone_path
                repo_url_for_digest = src # Use original src URL for the digest title
            except RuntimeError as e:
                cli_progress_printer(f"Failed to clone repository: {e}")
                sys.exit(1)
        else:
            # If src is a local path, use it directly
            repo_to_digest = src
            repo_url_for_digest = f"local path: {src}" # Adjust how local paths are named in digest

        cli_progress_printer(f"Generating digest for {repo_to_digest}...")
        final_digest = generate_markdown_digest(repo_url_for_digest, repo_to_digest, progress_callback=cli_progress_printer)
        print(final_digest)
