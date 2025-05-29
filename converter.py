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
    """
    if github_token is None:
        github_token = os.getenv("GITHUB_TOKEN")
    if github_token and repo_url.startswith("https://github.com/"):
        # Insert token into the URL for authentication
        repo_url = repo_url.replace(
            "https://github.com/", f"https://{github_token}:x-oauth-basic@github.com/"
        )
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", repo_url, clone_path])
    except subprocess.CalledProcessError as e:
        # Raise an exception instead of exiting
        raise RuntimeError(f"Error cloning repository: {e}")

def is_text_file(path):
    ext = path.suffix.lower()
    return ext in TEXT_EXTS

def walk_repo(repo_path):
    file_summaries = []
    for root, dirs, files in os.walk(repo_path):
        # Prune ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in sorted(files):
            if file in IGNORED_FILES:
                continue
            path = Path(root) / file
            rel_path = os.path.relpath(path, repo_path)
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
            if not is_text_file(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                file_summaries.append((rel_path, content))
            except Exception:
                continue
    return file_summaries

def print_tree(repo_path):
    lines = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        level = os.path.relpath(root, repo_path).count(os.sep)
        indent = "    " * level
        lines.append(f"{indent}{os.path.basename(root)}/")
        for f in sorted(files):
            if f in IGNORED_FILES:
                continue
            lines.append(f"{indent}    {f}")
    return lines

def generate_markdown_digest(repo_url, repo_path):
    md = []
    md.append(f"# Codebase Digest for {repo_url}\n")
    md.append("## Directory Tree\n")
    md.append("```")
    md.extend(print_tree(repo_path))
    md.append("```\n")
    md.append("## Files and Content\n")
    for rel_path, content in walk_repo(repo_path):
        ext = Path(rel_path).suffix.lstrip(".")
        md.append(f"### {rel_path}\n")
        md.append(f"```{ext}\n{content}\n```\n")
    return "\n".join(md)

# If run as script, keep the CLI for backward compatibility
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python converter2.py <repo_path_or_git_url>")
        sys.exit(1)
    src = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = tmpdir
        if src.startswith("http://") or src.startswith("https://") or src.endswith(".git"):
            clone_repository(src, repo_path)
        else:
            repo_path = src
        print(generate_markdown_digest(src, repo_path))
