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

MAX_FILE_SIZE = 15 * 1024 * 1024  # 10 MB per file
MAX_DIRECTORY_DEPTH = 40  # Maximum depth of directory traversal
MAX_FILES = 15_000  # Maximum number of files to process
MAX_TOTAL_SIZE_BYTES = 1000 * 1024 * 1024  # 500 MB total repo size
CHUNK_SIZE = 1024 * 1024  # 1 MB

IGNORED_DIRS = {".git", "__pycache__"}
IGNORED_FILES = {
    ".DS_Store",
    "Zone.Identifier",
    ".jpeg",
    ".jpg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".heif",
    ".heic",
    ".avif",
    ".svg",
    ".psd",
    ".raw",
    ".eps",
    ".pdf",
    ".ico",
    ".exr",
    ".tga",
    ".dds",
    ".wdp",
    ".dng",
    ".ppm",
}

TEXT_EXTS = {
  ".adoc",  # AsciiDoc
  ".asciidoc", # AsciiDoc (alternative)
  ".ada",   # Ada
  ".adb",   # Ada (body)
  ".ads",   # Ada (specification)
  ".asp",   # Active Server Pages (Classic)
  ".aspx",  # Active Server Pages .NET
  ".asm",   # Assembly Language
  ".astro", # Astro Component
  ".bash", # Bash Script
  ".bat", # Windows Batch Script
  ".bib",   # BibTeX Bibliography
  ".build", # Build File (generic)
  ".c", # C
  ".cbl",   # COBOL
  ".cfg",   # Configuration File (generic)
  ".clj", # Clojure
  ".cls",   # LaTeX Class File
  ".cob",   # COBOL (alternative)
  ".conf",  # Configuration File (generic)
  ".cpp", # C++
  ".cql",   # Cassandra Query Language
  ".cr",    # Crystal
  ".cs", # C#
  ".cshtml", # C# HTML (Razor)
  ".csproj",# C# Project
  ".css", # CSS
  ".csv",   # Comma-Separated Values
  ".cypher",# Cypher Query Language (Neo4j)
  ".d",     # D
  ".dart", # Dart
  ".dockerfile", # Dockerfile
  ".ejs",   # Embedded JavaScript templates
  ".elm", # Elm
  ".env",   # Environment Variables
  ".erb",   # Embedded Ruby (Rails templates)
  ".erl",   # Erlang
  ".ex", # Elixir
  ".exs", # Elixir Script
  ".f",     # Fortran
  ".f90",   # Fortran 90
  ".f95",   # Fortran 95
  ".fs", # F#
  ".fsi", # F# Interface
  ".fsproj",# F# Project
  ".gitattributes", # Git Attributes
  ".gitignore", # Git Ignore Rules
  ".go", # Go
  ".gradle",# Gradle Script
  ".graphql", # GraphQL Schema/Query
  ".groovy", # Groovy
  ".h", # C/C++ Header
  ".handlebars", # Handlebars templates (alternative)
  ".hbs", # Handlebars templates
  ".hcl",   # HashiCorp Configuration Language (Terraform, Packer)
  ".hpp", # C++ Header (alternative)
  ".hrl",   # Erlang Header
  ".hs",    # Haskell
  ".htm", # HTML (alternative)
  ".html", # HTML
  ".idr",   # Idris
  ".ini",   # INI Configuration
  ".java", # Java (source)
  ".jinja", # Jinja templates
  ".js", # JavaScript
  ".json", # JSON
  ".jsp",   # JavaServer Pages
  ".jsx", # JavaScript XML (React)
  ".kt", # Kotlin
  ".less", # LESS
  ".lhs",   # Literate Haskell
  ".lidr",  # Literate Idris
  ".liquid",# Liquid templates (Jekyll, Shopify)
  ".lua", # Lua
  ".m", # Objective-C / MATLAB script
  ".markdown", # Markdown (alternative)
  ".md", # Markdown
  ".ml",    # OCaml
  ".mli",   # OCaml Interface
  ".mustache", # Mustache templates
  ".nim",   # Nim
  ".p",     # Pascal (alternative)
  ".pas",   # Pascal
  ".php", # PHP
  ".pl", # Perl
  ".plist", # Property List (Apple)
  ".plsql", # Oracle PL/SQL
  ".pom",   # Project Object Model (Maven)
  ".pp",    # Pascal (alternative for Free Pascal)
  ".properties", # Java Properties
  ".ps1", # PowerShell Script
  ".psm1", # PowerShell Module
  ".psql",  # PostgreSQL procedural language
  ".pug",   # Pug templates (formerly Jade)
  ".py", # Python
  ".r", # R
  ".rb", # Ruby
  ".re",    # Reason
  ".rei",   # Reason Interface
  ".Rmd",   # R Markdown
  ".rs", # Rust
  ".rst",   # reStructuredText
  ".S",     # Assembly Language (often for Unix-like systems)
  ".sass", # Sass (indented syntax)
  ".sbt",   # Scala Build Tool
  ".scala", # Scala
  ".scss", # SCSS (Sass)
  ".sh", # Shell Script (generic)
  ".slim",  # Slim templates
  ".sln",   # Visual Studio Solution
  ".sol",   # Solidity (for Ethereum)
  ".sql", # SQL Queries
  ".strings", # Resource Strings (Apple)
  ".sty",   # LaTeX Style File
  ".svelte",# Svelte Component
  ".svg",   # Scalable Vector Graphics (XML-based)
  ".swift", # Swift
  ".tcl", # TCL
  ".tex",   # LaTeX
  ".tf",    # Terraform Configuration
  ".tfvars",# Terraform Variables
  ".toml", # TOML
  ".ts", # TypeScript
  ".tsv",   # Tab-Separated Values
  ".tsql",  # Transact-SQL (Microsoft SQL Server)
  ".tsx", # TypeScript XML (React)
  ".txt", # Plain Text
  ".v",     # Verilog
  ".vbhtml", # VB.NET HTML (Razor)
  ".vbcsproj",# Visual Basic .NET Project
  ".vcxproj",# Visual C++ Project
  ".vhd",   # VHDL
  ".vhdl",  # VHDL (alternative)
  ".vim",   # Vim Script
  ".vimrc", # Vim Configuration
  ".vue", # Vue.js Single File Components
  ".xaml",  # XAML (WPF, .NET MAUI)
  ".xcodeproj", # Xcode Project
  ".xcworkspace", # Xcode Workspace
  ".xml", # XML
  ".xul",   # XUL (Mozilla)
  ".yaml", # YAML (alternative)
  ".yml", # YAML
  ".zig",   # Zig
  ".zsh", # Zsh Script
}


def clone_repository(
    repo_url: str,
    clone_path: str,
    github_token: Optional[str] = None,
    subpath: Optional[str] = None,
):
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
        "git",
        "clone",
        "--filter=blob:none",
        "--sparse",
        "--depth=1",
        repo_url,
        clone_path,
    ]
    subprocess.run(clone_cmd, check=True, env=env)
    if subpath:
        # Enable sparse checkout for a specific subpath
        subprocess.run(
            ["git", "-C", clone_path, "sparse-checkout", "set", subpath],
            check=True,
            env=env,
        )


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
    if not path.exists():
        logger.warning(f"File disappeared before reading: {path}")
        return
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        logger.warning(f"Skipping file due to error during chunked read: {path} ({e})")
        return


def _walk_error_handler(os_error: OSError):
    """Handles errors during os.walk, allowing it to skip problematic directories."""
    logger.warning(
        f"Error accessing directory {os_error.filename} during walk: {os_error.strerror}. Skipping."
    )


def trace_repo(repo_path: str, file_callback: Optional[Callable[[Path], None]] = None):
    """
    Walk the repo, process files in a memory-efficient way, and call file_callback(path) for each file.
    file_callback must accept exactly one argument: the Path of the file.
    """
    stats = {"total_files": 0, "total_size": 0}
    for root, dirs, files_in_dir in os.walk(repo_path, onerror=_walk_error_handler):
        # Filter ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file_name in files_in_dir:
            path = Path(root) / file_name
            try:
                if path.suffix.lower() in IGNORED_FILES or path.name in IGNORED_FILES:
                    continue
                if not is_text_file(path):
                    continue

                if not path.is_file():  # Checks existence and if it's a file
                    logger.info(f"Skipping non-file or missing entry: {path}")
                    continue

                file_size = path.stat().st_size
                if file_size > MAX_FILE_SIZE:
                    logger.info(f"Skipping large file: {path} ({file_size} bytes)")
                    continue

                if (
                    stats["total_files"] >= MAX_FILES
                    or stats["total_size"] + file_size > MAX_TOTAL_SIZE_BYTES
                ):
                    logger.warning(f"Repository size or file count limit reached. Stopping traversal. Files processed so far: {stats['total_files']}, size so far: {stats['total_size']}.")
                    return # Stop all traversal

                stats["total_files"] += 1
                stats["total_size"] += file_size

                if file_callback:
                    file_callback(path)

                gc.collect()
            except FileNotFoundError:
                logger.warning(f"File not found during trace_repo processing: {path}. Skipping this file.")
            except OSError as oe:
                logger.warning(f"OSError processing file {path} in trace_repo: {oe}. Skipping this file.")
            except Exception as e:
                logger.error(f"Unexpected error processing file {path} in trace_repo: {e}. Skipping this file.")


def print_tree(repo_path: str) -> list[str]:
    """
    Print a tree structure of the repository (memory efficient).
    """
    tree_lines = []
    for root, dirs, files in os.walk(repo_path):
        level = root.replace(repo_path, "").count(os.sep)
        indent = " " * 4 * level
        tree_lines.append(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 4 * (level + 1)
        for f in files:
            tree_lines.append(f"{subindent}{f}")
    return tree_lines


def generate_markdown_digest(
    repo_url: str, repo_path: str, progress_callback=None
) -> str:
    """
    Generate a Markdown digest of the repository, reading large files in chunks.
    Sends progress updates in the required JSON format if progress_callback is provided.
    """
    digest_lines = [f"# Repository Digest for {repo_url}\n"]
    file_count = 0
    total_files = 0

    # List of common documentation files to attempt to include at the beginning
    common_files = [
        "README.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
    ]

    # Process common files first, if they exist (case-insensitive)
    repo_files = {
        str(p.name).lower(): p for p in Path(repo_path).iterdir() if p.is_file()
    }
    for common_file in common_files:
        # Try to find the file in a case-insensitive way
        file_path = None
        for fname, p in repo_files.items():
            if fname == common_file.lower():
                file_path = p
                break
        if file_path and file_path.exists() and file_path.is_file():
            try:
                rel_path = file_path.relative_to(repo_path)
                digest_lines.append(f"\n## {rel_path}\n")
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    digest_lines.append(f.read())
                if progress_callback:
                    progress_callback(f"Processed {file_path.name}", 5)
            except FileNotFoundError:
                logger.warning(f"Common file {file_path} not found, skipping.")
            except OSError as oe:
                # Catch OSError more broadly, FNF is a subclass. This helps if FNF isn't caught directly.
                logger.warning(f"OSError when processing common file {file_path} (Error: {oe}). Skipping.")
            except Exception as e:
                logger.warning(f"Could not process common file {file_path}: {e}")
        elif common_file.lower() in repo_files: # File was in repo_files but .exists() or .is_file() failed
            logger.warning(f"Common file '{common_file}' found in listing but failed exists/is_file check for path: {repo_files.get(common_file.lower())}")
        else: # File not found in initial listing by iterdir
            logger.info(f"Common file '{common_file}' not found at the root of the repository: {repo_path}")
    # Count total files for percentage calculation
    for root, dirs, files_in_dir in os.walk(repo_path, onerror=_walk_error_handler):
        # Filter ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file_name in files_in_dir:
            path = Path(root) / file_name
            try:
                if path.suffix.lower() in IGNORED_FILES or path.name in IGNORED_FILES:
                    continue
                if not is_text_file(path):
                    continue
                # Skip common files that we already processed or will be processed separately
                if path.name in common_files:
                    continue

                if not path.is_file(): # Ensure it's a file and exists
                    continue

                total_files += 1
            except OSError as oe:
                logger.warning(f"OSError checking file {path} during pre-count: {oe}. Skipping from count.")
            except Exception as e:
                logger.error(f"Unexpected error checking file {path} during pre-count: {e}. Skipping from count.")

    def process_file(path: Path):
        nonlocal file_count, total_files
        # Skip already processed common files
        if path.name in common_files:
            return

        if not path.exists():
            logger.warning(f"File disappeared before processing: {path}")
            return

        try:
            digest_lines.append(f"\n## {path.relative_to(repo_path)}\n")
            for chunk in read_file_in_chunks(path):
                try:
                    digest_lines.append(chunk.decode("utf-8", errors="replace"))
                except Exception:
                    logger.warning(
                        f"Skipping chunk in file {path} due to decode error."
                    )
                    continue
        except Exception as e:
            logger.warning(
                f"Skipping file due to error during processing: {path} ({e})"
            )
            return

        file_count += 1
        if progress_callback and total_files > 0:
            percentage = int((file_count / total_files) * 90) + 10  # 10-100%
            message = f"Currently processing {path.name}..."
            progress_callback(message, percentage)

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
        logger.info("\n".join(print_tree(clone_path)))
        logger.info("\n--- Markdown Digest ---\n")
        logger.info(generate_markdown_digest(repo_url, clone_path))
    else:
        logger.info("Usage: python converter.py <repo_url> <clone_path>")
