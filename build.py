#!/usr/bin/env python3
"""
build.py — King of Tokyo Guide Builder
Reads all .md files from /monsters, parses YAML frontmatter + markdown,
and outputs data.json for the web app.

Usage: python3 build.py

No external libraries needed — uses Python stdlib only.
"""

import os
import json
import re

MONSTERS_DIR = os.path.join(os.path.dirname(__file__), "monsters")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def parse_frontmatter(text):
    """Extract YAML frontmatter and body from a markdown string."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    yaml_block = text[3:end].strip()
    body = text[end + 3:].strip()

    frontmatter = {}
    lines = yaml_block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if not value:
                # Check if next lines are a list (start with "  - ")
                list_items = []
                while i + 1 < len(lines) and lines[i + 1].startswith("  - "):
                    i += 1
                    list_items.append(lines[i].strip()[2:].strip())
                if list_items:
                    frontmatter[key] = list_items
            else:
                try:
                    frontmatter[key] = int(value)
                except ValueError:
                    frontmatter[key] = value
        i += 1

    # Parse stats block manually
    stats_match = re.search(r'stats:\n((?:  \w+: \d+\n?)+)', text)
    if stats_match:
        stats = {}
        for stat_line in stats_match.group(1).strip().splitlines():
            sk, _, sv = stat_line.strip().partition(":")
            stats[sk.strip()] = int(sv.strip())
        frontmatter["stats"] = stats

    return frontmatter, body


def markdown_to_html(md):
    """
    Very simple Markdown → HTML converter (handles common patterns).
    For production, replace with 'marked' (JS) or 'mistune' (Python).
    """
    lines = md.split("\n")
    html = []
    in_table = False
    in_ul = False
    in_ol = False

    def close_list():
        nonlocal in_ul, in_ol
        if in_ul:
            html.append("</ul>")
            in_ul = False
        if in_ol:
            html.append("</ol>")
            in_ol = False

    def inline(text):
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Inline code
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # Headings
        if line.startswith("### "):
            close_list()
            html.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            close_list()
            html.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            close_list()
            html.append(f"<h1>{inline(line[2:])}</h1>")

        # Table row
        elif line.startswith("|"):
            if not in_table:
                in_table = True
                html.append('<table>')
                # First row = header
                cells = [c.strip() for c in line.strip("|").split("|")]
                html.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells) + "</tr></thead><tbody>")
                i += 1  # skip separator line
            else:
                cells = [c.strip() for c in line.strip("|").split("|")]
                html.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
        else:
            if in_table:
                html.append("</tbody></table>")
                in_table = False

        # Unordered list
        if line.startswith("- "):
            if not in_ul:
                close_list()
                in_ul = True
                html.append("<ul>")
            html.append(f"<li>{inline(line[2:])}</li>")

        # Ordered list
        elif re.match(r'^\d+\. ', line):
            if not in_ol:
                close_list()
                in_ol = True
                html.append("<ol>")
            item_text = re.sub(r'^\d+\. ', '', line)
            html.append(f"<li>{inline(item_text)}</li>")

        # Blank line
        elif line.strip() == "":
            close_list()

        # Normal paragraph (skip headings and lists already handled)
        elif not line.startswith("#") and not line.startswith("|") and not line.startswith("-") and not re.match(r'^\d+\. ', line):
            close_list()
            if line.strip():
                html.append(f"<p>{inline(line)}</p>")

        i += 1

    close_list()
    if in_table:
        html.append("</tbody></table>")

    return "\n".join(html)


def build():
    files = sorted(f for f in os.listdir(MONSTERS_DIR) if f.endswith(".md"))
    monsters = []

    for filename in files:
        filepath = os.path.join(MONSTERS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()

        frontmatter, body = parse_frontmatter(raw)
        content_html = markdown_to_html(body)
        monster_id = filename.replace(".md", "")

        monsters.append({
            "id": monster_id,
            **frontmatter,
            "content_html": content_html,
        })

    monsters.sort(key=lambda m: m.get("name", ""))

    output = {"monsters": monsters}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Built data.json with {len(monsters)} monsters:")
    for m in monsters:
        print(f"   - {m.get('name', '?')} ({m['id']})")


if __name__ == "__main__":
    build()