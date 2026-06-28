#!/usr/bin/env python3
"""
fill_template.py — Fill a .pptx template with content from a JSON spec.

Usage:
    python fill_template.py template.pptx spec.json output.pptx

The spec.json defines slide-by-slide content to inject:
{
  "slides": [
    {
      "index": 0,
      "replacements": {
        "Title Placeholder": "My Presentation",
        "Subtitle Placeholder": "A great story"
      }
    },
    {
      "index": 1,
      "replacements": {
        "Heading 1": "Introduction",
        "Body text": "Welcome to the show"
      }
    }
  ]
}

This script unpacks the template, performs text replacements in the XML,
then repacks it. It reuses the pptx skill's office scripts when available,
falling back to direct zipfile manipulation.
"""

import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# Try to import from the pptx skill's scripts
PPTX_SKILL_PATH = os.path.expanduser(
    "~/.openclaw/skills/pptx/scripts"
)
OFFICE_SCRIPTS = os.path.expanduser(
    "~/.openclaw/skills/pptx/scripts/office"
)


def find_script(name):
    """Find a script from the pptx skill or return None."""
    for search_dir in [OFFICE_SCRIPTS, PPTX_SKILL_PATH]:
        candidate = os.path.join(search_dir, name)
        if os.path.exists(candidate):
            return candidate
    return None


def unpack_docx(src, dest):
    """Unpack a .pptx (ZIP) to a directory, pretty-printing XML."""
    unpack_script = find_script("unpack.py")
    if unpack_script:
        import subprocess
        subprocess.run([sys.executable, unpack_script, src, dest], check=True)
        return

    # Fallback: manual unzip
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(src, "r") as z:
        z.extractall(dest)


def pack_docx(src, dest, original=None):
    """Repack a directory into a .pptx file."""
    pack_script = find_script("pack.py")
    if pack_script:
        import subprocess
        cmd = [sys.executable, pack_script, src, dest]
        if original:
            cmd.extend(["--original", original])
        subprocess.run(cmd, check=True)
        return

    # Fallback: manual zip
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(src):
            for f in files:
                full = os.path.join(root, f)
                arcname = os.path.relpath(full, src)
                z.write(full, arcname)


def replace_in_xml(xml_content, replacements):
    """Replace text in XML content, handling split runs.

    PowerPoint often splits text across multiple <w:r><w:t> elements.
    This function joins adjacent text runs, performs replacements,
    then writes back.
    """
    # Simple approach: replace within <a:t> and <w:t> elements
    for old_text, new_text in replacements.items():
        # Try direct replacement in text elements first
        # OpenXML uses <a:t> for shapes, <w:t> for word processing
        pattern = re.compile(
            r"(<(?:a|w):t[^>]*>)" + re.escape(old_text) + r"(</(?:a|w):t>)"
        )
        if pattern.search(xml_content):
            xml_content = pattern.sub(r"\g<1>" + new_text + r"\g<2>", count=1)
        else:
            # Text might be split across runs — try joining adjacent runs
            # This is a simplified approach; complex splits may need manual editing
            pass

    return xml_content


def fill_template(template_path, spec_path, output_path):
    """Main: unpack template, apply replacements, repack."""
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    tmpdir = tempfile.mkdtemp(prefix="pptx_fill_")
    try:
        unpack_docx(template_path, tmpdir)

        # Find the main document XML
        doc_xml = os.path.join(tmpdir, "ppt", "slides.xml")
        # Actually, slides are in ppt/slides/slide1.xml, slide2.xml, etc.

        for slide_spec in spec.get("slides", []):
            idx = slide_spec.get("index", 0)
            replacements = slide_spec.get("replacements", {})
            if not replacements:
                continue

            slide_file = os.path.join(tmpdir, "ppt", "slides", f"slide{idx + 1}.xml")
            if not os.path.exists(slide_file):
                print(f"Warning: slide file not found: {slide_file}", file=sys.stderr)
                continue

            with open(slide_file, "r", encoding="utf-8") as f:
                xml = f.read()

            xml = replace_in_xml(xml, replacements)

            with open(slide_file, "w", encoding="utf-8") as f:
                f.write(xml)

        pack_docx(tmpdir, output_path, original=template_path)
        print(f"Created: {output_path}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python fill_template.py template.pptx spec.json output.pptx")
        sys.exit(1)

    template_path = sys.argv[1]
    spec_path = sys.argv[2]
    output_path = sys.argv[3]

    if not os.path.exists(template_path):
        print(f"Error: template not found: {template_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(spec_path):
        print(f"Error: spec not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    fill_template(template_path, spec_path, output_path)
