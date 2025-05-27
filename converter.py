#!/usr/bin/env python3

# How It Works:
# 1. The script accepts a Git repository URL as a command-line parameter.
# 2. It clones the repository (with a shallow clone for speed) into a temporary directory.
# 3. It recursively scans the repository files (ignoring the .git directory), counting files and lines.
# 4. It collects basic statistics by file extension.
# 5. Finally, it prints a markdown-formatted summary of the codebase.

# To run the script, save it as, for example, "script.py", make it executable (or run with python3), and pass the Git URL:

#   $ python script.py https://github.com/pallets/flask

# You can expand it further by including more detailed analysis (like code complexity, specific folder reports, etc.) depending on your needs.


import os
import subprocess
import sys
import tempfile
import json
import platform
from collections import defaultdict
from pathlib import Path
from docling.document_converter import (  # type: ignore
    DocumentConverter,
    PdfFormatOption,
    SimplePipeline,
)
from docling.datamodel.base_models import InputFormat  # type: ignore
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend  # type: ignore

IGNORED_PATTERNS = {".git"}

# File extensions that should be processed by Docling
DOCLING_FORMATS = {
    InputFormat.PDF,
    InputFormat.IMAGE,
    InputFormat.DOCX,
    InputFormat.HTML,
    InputFormat.PPTX,
    InputFormat.ASCIIDOC,
    InputFormat.CSV,
    InputFormat.MD,
}

# Extensions to ignore for regular text processing
IGNORED_EXTENSIONS = {
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


def clone_repository(repo_url, clone_path):
    """Clone the repository from repo_url into clone_path.
    Supports private repositories using a GITHUB_TOKEN environment variable.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token and repo_url.startswith("https://github.com/"):
        # Insert token into the URL for authentication
        repo_url = repo_url.replace(
            "https://github.com/", f"https://{github_token}:x-oauth-basic@github.com/"
        )
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", repo_url, clone_path])
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error cloning repository: {e}")


def generate_tree_structure(
    path, prefix="", is_last=True, ignore_patterns=IGNORED_PATTERNS
):
    """Generate a tree-like structure of the directory."""
    tree_lines = []
    basename = os.path.basename(path)

    # Skip ignored patterns
    for pattern in ignore_patterns:
        if pattern in basename:
            return tree_lines

    # Add current node
    if prefix == "":  # root directory
        tree_lines.append(f"└── {basename}/")
        new_prefix = "    "
    else:
        connector = "└── " if is_last else "├── "
        tree_lines.append(
            prefix + connector + basename + ("/" if os.path.isdir(path) else "")
        )
        new_prefix = prefix + ("    " if is_last else "│   ")

    if os.path.isdir(path):
        # List directory contents
        items = sorted(os.listdir(path))
        for index, item in enumerate(items):
            item_path = os.path.join(path, item)
            is_last_item = index == len(items) - 1
            tree_lines.extend(
                generate_tree_structure(item_path, new_prefix, is_last_item)
            )

    return tree_lines


def analyze_codebase(repo_path):
    """Walk the repository directory and collect stats."""
    file_count = 0
    total_lines = 0
    extension_stats = defaultdict(lambda: {"files": 0, "lines": 0})
    converted_contents = []

    # Set up Docling converter with format options
    doc_converter = DocumentConverter(
        allowed_formats=DOCLING_FORMATS,
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=SimplePipeline, backend=PyPdfiumDocumentBackend
            ),
        },
    )

    # Generate tree structure
    tree_structure = generate_tree_structure(repo_path)

    # Walk the directory structure
    for root, dirs, files in os.walk(repo_path):
        # exclude ignored patterns
        dirs[:] = [d for d in dirs if not any(p in d for p in IGNORED_PATTERNS)]

        docling_files = []
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            relative_path = os.path.relpath(file_path, repo_path)

            # Determine if file should be processed by Docling
            path = Path(file_path)
            try:
                if doc_converter.can_convert(path):
                    docling_files.append(path)
                    continue
            except Exception:
                pass

            # Skip ignored extensions for regular processing
            if ext in IGNORED_EXTENSIONS:
                continue

            # Process non-Docling files using original method
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    markdown_content = f"```{ext[1:] if ext else ''}\n{content}\n```"
                    lines = content.count("\n") + 1

                    converted_contents.append(
                        {
                            "path": relative_path,
                            "content": markdown_content,
                            "extension": ext,
                        }
                    )

                    file_count += 1
                    total_lines += lines
                    extension_stats[ext]["files"] += 1
                    extension_stats[ext]["lines"] += 1
            except Exception:
                continue

        # Process Docling-compatible files
        if docling_files:
            try:
                results = doc_converter.convert_all(docling_files)
                for res in results:
                    if res.valid:
                        relative_path = os.path.relpath(str(res.input.file), repo_path)
                        markdown_content = res.document.export_to_markdown()
                        ext = os.path.splitext(relative_path)[1].lower()
                        lines = markdown_content.count("\n") + 1

                        converted_contents.append(
                            {
                                "path": relative_path,
                                "content": markdown_content,
                                "extension": ext,
                            }
                        )

                        file_count += 1
                        total_lines += lines
                        extension_stats[ext]["files"] += 1
                        extension_stats[ext]["lines"] += lines
            except Exception as e:
                print(f"Warning: Docling conversion failed for some files: {str(e)}")

    return file_count, total_lines, extension_stats, converted_contents, tree_structure


def generate_markdown(
    repo_url, file_count, total_lines, extension_stats, file_contents, tree_structure
):
    """Generate a markdown digest for the repository."""
    md = []
    md.append(f"# Codebase Digest for {repo_url}")
    md.append("")

    md.append("## Directory Structure")
    md.append("")
    md.append("```")
    md.extend(tree_structure)
    md.append("```")
    md.append("")

    md.append("## Overall Statistics")
    md.append("")
    md.append(f"- **Total Files Processed:** {file_count}")
    md.append(f"- **Total Lines Generated:** {total_lines}")
    md.append("")

    if extension_stats:
        md.append("## Breakdown by File Type")
        md.append("")
        md.append("| Extension | # Files | Lines Generated |")
        md.append("|-----------|---------|-----------------|")
        for ext, stats in sorted(
            extension_stats.items(), key=lambda x: x[1]["files"], reverse=True
        ):
            md.append(f"| {ext} | {stats['files']} | {stats['lines']} |")

    md.append("\n## Converted Contents\n")

    # Sort files by path for better organization
    sorted_files = sorted(file_contents, key=lambda x: x["path"])

    for file_info in sorted_files:
        md.append(f"\n### {file_info['path']}\n")
        md.append(file_info["content"])
        md.append("\n---\n")

    return "\n".join(md)


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <GIT_REPOSITORY_URL>")
        sys.exit(1)

    repo_url = sys.argv[1]

    # Create output filename from repo URL
    repo_name = repo_url.rstrip("/").split("/")[-1]
    output_file = f"{repo_name}_digest.md"

    # Use a short path for the temporary directory to avoid path length issues on Windows
    system = platform.system()
    if system == "Windows":
        short_tmp_dir = "C:/tmp"
    else:
        short_tmp_dir = "/tmp"
    os.makedirs(short_tmp_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=short_tmp_dir) as tmpdir:
        clone_path = os.path.join(tmpdir, "r")  # use a single-letter subdir
        print(f"Cloning repository {repo_url} ...")
        clone_repository(repo_url, clone_path)
        print("Analyzing and converting codebase ...")
        file_count, total_lines, extension_stats, file_contents, tree_structure = (
            analyze_codebase(clone_path)
        )

        markdown = generate_markdown(
            repo_url,
            file_count,
            total_lines,
            extension_stats,
            file_contents,
            tree_structure,
        )

        # Save to file
        output_path = Path(output_file)
        output_path.write_text(markdown, encoding="utf-8")
        print(f"\nMarkdown digest has been saved to: {output_file}")
        print("\nContent preview:\n")
        print(markdown[:1000] + "..." if len(markdown) > 1000 else markdown)


if __name__ == "__main__":
    main()
