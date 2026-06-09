# Auto-generated HTML from annotated review markdown
import re, json

with open("tests/fixtures/jl_coach_annotated.md", "r", encoding="utf-8") as f:
    md = f.read()

# Split into sections
parts = md.split("\n---\n")
body_md = parts[0] if parts else md
summary_md = parts[1] if len(parts) > 1 else ""

# Parse paragraphs
paras = re.split(r"\n\n### 段落 (\d+)\n\n", body_md)
paras = [p for p in paras if p.strip()]

def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def render_annotation(line):
    # [A3!!—logic]  →  red badge
    # [A2—dup]  →  blue badge
    # error types
    line = re.sub(r'\*\*\[A3!!—逻辑谬误\]\*\*', '<span class="badge badge-false">⚡ 逻辑谬误 A3</span>', line)
    line = re.sub(r'\*\*\[A3!!—(\w+)\]\*\*', r'<span class="badge badge-false">⚡ \1 A3</span>', line)
    line = re.sub(r'\*\*\[A2—重复\]\*\*', '<span class="badge badge-dupe">🔄 内容重复 A2</span>', line)
    line = re.sub(r'\*\*\[A2(\w*)—(\w+)\]\*\*', r'<span class="badge badge-struct">📐 \2 A2</span>', line)
    line = re.sub(r'\*\*\[A4—(\w+)\]\*\*', r'<span class="badge badge-lang">✏️ \1 A4</span>', line)
    line = re.sub(r'\*\*\[A5!—(\w+)\]\*\*', r'<span class="badge badge-cite">📖 \1 A5</span>', line)
    # inline code
    line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
    return line

def render_md_text(text):
    """Simple markdown to HTML for paragraph text"""
    text = esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', text)
    return text

def render_summary(summary_md):
    sections = re.split(r'\n### ', summary_md)
    html = ""
    for sec in sections:
        if not sec.strip():
            continue
        lines = sec.strip().split("\n")
        title = lines[0].strip()
        html += f'<div class="summary-card"><h3>{render_md_text(title)}</h3>\n'
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            if line.startswith("- ✅"):
                html += f'<div class="pos">✅ {render_md_text(line[3:])}</div>\n'
            elif line.startswith("- ⚠️"):
                html += f'<div class="neg">⚠️ {render_md_text(line[3:])}</div>\n'
            elif line.startswith("**"):
                html += f'<p><strong>{render_md_text(line.strip("*"))}</strong></p>\n'
            else:
                html += f'<p>{render_md_text(line)}</p>\n'
        html += '</div>\n'
    return html

# Build HTML
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>审稿标注报告 — Should Machines Be Held Morally Responsible?</title>
<style>
:root{{--primary:#2563eb;--bg:#f8fafc;--card:#fff;--text:#1e293b;--muted:#64748b;--border:#e2e8f0;--ok:#16a34a;--warn:#ea580c;--err:#dc2626}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.85;padding-bottom:80px}}
.sidebar{{position:fixed;top:0;left:0;width:240px;height:100vh;background:#0f172a;color:#e2e8f0;overflow-y:auto;z-index:100;padding:24px 0}}
.sidebar h2{{font-size:13px;padding:0 20px 16px;color:#fff;border-bottom:1px solid #334155;margin-bottom:8px}}
.sidebar nav a{{display:block;padding:5px 20px;color:#94a3b8;text-decoration:none;font-size:12px;border-left:3px solid transparent}}
.sidebar nav a:hover{{color:#fff;background:#1e293b;border-left-color:var(--primary)}}
.main{{margin-left:240px;max-width:900px;padding:40px 48px}}
h1{{font-size:24px;margin-bottom:4px;color:#0f172a}}
.subtitle{{color:var(--muted);font-size:14px;margin-bottom:16px}}
h2{{font-size:18px;margin:32px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--border);color:#0f172a}}
h3{{font-size:15px;margin:20px 0 8px;color:#334155}}
.score-big{{font-size:40px;font-weight:800;color:var(--primary)}}
.para-card{{background:var(--card);border:1px solid var(--border);border-radius:10px;margin:16px 0;overflow:hidden}}
.para-num{{background:#0f172a;color:#e2e8f0;font-size:12px;padding:6px 16px;font-weight:600}}
.para-text{{padding:14px 16px;font-size:14px;line-height:1.9;color:#334155;white-space:pre-wrap}}
.anno-list{{padding:0 16px 12px}}
.anno-item{{padding:8px 12px;margin:4px 0;border-radius:6px;font-size:13px;line-height:1.7}}
.anno-item.false{{background:#fef2f2;border-left:3px solid var(--err)}}
.anno-item.dupe{{background:#fffbeb;border-left:3px solid var(--warn)}}
.anno-item.struct{{background:#eff6ff;border-left:3px solid var(--primary)}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;margin-right:4px}}
.badge-false{{background:#fee2e2;color:#991b1b}}
.badge-dupe{{background:#ffedd5;color:#9a3412}}
.badge-struct{{background:#dbeafe;color:#1e40af}}
.badge-lang{{background:#dcfce7;color:#166534}}
.badge-cite{{background:#f3e8ff;color:#7e22ce}}
code{{background:#f1f5f9;padding:1px 5px;border-radius:3px;font-family:"JetBrains Mono",monospace;font-size:12px}}
.correct-box{{display:block;margin-top:4px;padding:6px 10px;background:#f0fdf4;border-left:3px solid var(--ok);border-radius:4px;font-size:12px;color:#166534}}
.score-row{{display:flex;gap:20px;flex-wrap:wrap;margin:16px 0}}
.score-chip{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 24px;text-align:center;min-width:100px}}
.score-chip .label{{font-size:11px;color:var(--muted);text-transform:uppercase;margin-bottom:4px}}
.score-chip .val{{font-size:28px;font-weight:800}}
.summary-card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;margin:14px 0}}
.summary-card h3{{margin-top:0;font-size:15px}}
.pos{{color:var(--ok);font-size:13px;margin:4px 0}}
.neg{{color:var(--warn);font-size:13px;margin:4px 0}}
@media(max-width:768px){{.sidebar{{display:none}}.main{{margin-left:0;padding:16px}}}}
</style>
</head>
<body>
<aside class="sidebar">
<h2>审稿标注报告</h2>
<nav>
<a href="#scores">综合得分</a>
'''
# Add sidebar links for each paragraph
for i in range(1, 13):
    html += f'<a href="#p{i}">段落 {i}</a>\n'
html += '''<a href="#summary">评审总结</a>
</nav>
</aside>
<div class="main">
<h1>审稿标注报告</h1>
<p class="subtitle">Should Machines Be Held Morally Responsible for Their Decisions? &nbsp;|&nbsp; John Locke Essay Competition &nbsp;|&nbsp; 2026-06-10</p>
<h2 id="scores">综合得分</h2>
<div class="score-row">
<div class="score-chip"><div class="label">综合</div><div class="val" style="color:var(--primary)">7.9</div></div>
<div class="score-chip"><div class="label">结构逻辑 A2</div><div class="val" style="color:var(--ok)">8.0</div></div>
<div class="score-chip"><div class="label">论点证据 A3</div><div class="val" style="color:var(--warn)">7.8</div></div>
<div class="score-chip"><div class="label">学术诚信 A5</div><div class="val" style="color:var(--ok)">8.0</div></div>
</div>
<p style="font-size:12px;color:var(--muted)">A2 = 结构逻辑 &nbsp;|&nbsp; A3 = 论点证据 &nbsp;|&nbsp; A4 = 语言风格 &nbsp;|&nbsp; A5 = 学术诚信</p>
'''

# Render each paragraph
for i in range(1, 13):
    para_key = f"\n段落 {i}\n"
    # Find matching section
    section_content = ""
    for sec in re.split(r"\n### 段落 \d+\n", body_md):
        if not sec.strip():
            continue
        # Find the paragraph with the right number
        pass

# Simpler approach: iterate through split by ### 段落
sections = re.split(r"### 段落 (\d+)\n\n", body_md)
for idx in range(1, len(sections), 2):
    num = sections[idx]
    content = sections[idx+1] if idx+1 < len(sections) else ""
    
    lines = content.strip().split("\n")
    text_lines = []
    annotations = []
    in_anno = False
    current_anno = ""
    anno_class = "struct"
    
    for line in lines:
        if line.startswith("> **[A"):
            if current_anno:
                annotations.append((current_anno.strip(), anno_class))
            in_anno = True
            # Determine annotation class
            if "A3!!" in line:
                anno_class = "false"
            elif "A2" in line and ("重复" in line):
                anno_class = "dupe"
            elif "A2" in line:
                anno_class = "struct"
            elif "A4" in line:
                anno_class = "struct"
            elif "A5" in line:
                anno_class = "struct"
            current_anno = line[2:] + "\n"
            # Remove markdown bold markers
            current_anno = re.sub(r'\*\*\[(A\w+[!]*[—\w]*)\]\*\*', r'[\1]', current_anno)
        elif line.startswith(">   ") and in_anno:
            current_anno += line[2:] + "\n"
        elif line.startswith(">") and in_anno:
            current_anno += line[2:] + "\n"
        else:
            text_lines.append(line)
    
    if current_anno:
        annotations.append((current_anno.strip(), anno_class))
    
    text = "\n".join(text_lines).strip()
    if not text:
        continue
    
    html += f'<div class="para-card" id="p{num}">\n'
    html += f'<div class="para-num">段落 {num}</div>\n'
    html += f'<div class="para-text">{render_md_text(text)}</div>\n'
    if annotations:
        html += '<div class="anno-list">\n'
        for anno_text, cls in annotations:
            rendered = render_annotation(anno_text)
            html += f'<div class="anno-item {cls}">{rendered}</div>\n'
        html += '</div>\n'
    html += '</div>\n'

# Summary section
html += '<h2 id="summary">评审总结</h2>\n'
html += render_summary(summary_md)

html += '''
</div>
</body>
</html>'''

with open("docs/jl_coach_review_report.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML saved: {len(html)} chars")
