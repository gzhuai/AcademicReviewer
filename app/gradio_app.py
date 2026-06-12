import json
import logging
import os
import tempfile
from pathlib import Path

import gradio as gr
import httpx

from app.config import get_competition_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gradio_app")

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")


# ── Feedback extraction helper ──

def _extract_review_items(feedback_json: dict) -> list[dict]:
    """从 review feedback JSON 中提取所有可审核的条目。

    返回列表，每个条目包含:
        agent_name, item_path, item_type, ai_content, ai_substitutability
    """
    items = []

    # A2 StructureLogic
    structure = feedback_json.get("structure", {})
    for i, si in enumerate(structure.get("section_issues", [])):
        content = si.get("current_problem", "") or si.get("hint", "")
        items.append({
            "agent_name": "A2-StructureLogic",
            "item_path": f"structure.section_issues[{i}]",
            "item_type": "section_issue",
            "ai_content": content[:300],
            "ai_substitutability": si.get("substitutability", "REVIEW"),
            "severity": si.get("severity", ""),
        })
    for i, li in enumerate(structure.get("logic_issues", [])):
        content = li.get("issue", "") or li.get("transition_suggestion", "")
        items.append({
            "agent_name": "A2-StructureLogic",
            "item_path": f"structure.logic_issues[{i}]",
            "item_type": "logic_issue",
            "ai_content": content[:300],
            "ai_substitutability": li.get("substitutability", "REVIEW"),
            "severity": li.get("severity", ""),
        })

    # A3 ArgumentEvidence
    argument = feedback_json.get("argument", {})
    for i, cl in enumerate(argument.get("claims", [])):
        content = cl.get("missing_chain", "") or cl.get("coach_rewrite", "") or cl.get("claim", "")
        items.append({
            "agent_name": "A3-ArgumentEvidence",
            "item_path": f"argument.claims[{i}]",
            "item_type": "claim",
            "ai_content": content[:300],
            "ai_substitutability": cl.get("substitutability", "REVIEW"),
        })
    for i, fl in enumerate(argument.get("logical_fallacies", [])):
        content = f"{fl.get('fallacy_type', '')}: {fl.get('why_it_fails', '')}"
        items.append({
            "agent_name": "A3-ArgumentEvidence",
            "item_path": f"argument.logical_fallacies[{i}]",
            "item_type": "logical_fallacy",
            "ai_content": content[:300],
            "ai_substitutability": fl.get("substitutability", "REVIEW"),
            "severity": fl.get("severity", ""),
        })

    # A4 LanguageStyle
    language = feedback_json.get("language", {})
    for i, rw in enumerate(language.get("rewrites", [])):
        content = f"{rw.get('original', '')} → {rw.get('corrected', '')} ({rw.get('issue', '')})"
        items.append({
            "agent_name": "A4-LanguageStyle",
            "item_path": f"language.rewrites[{i}]",
            "item_type": "rewrite",
            "ai_content": content[:300],
            "ai_substitutability": rw.get("substitutability", "FULL"),
        })
    for i, sg in enumerate(language.get("suggestions", [])):
        content = f"{sg.get('type', '')}: {sg.get('description', '')}"
        items.append({
            "agent_name": "A4-LanguageStyle",
            "item_path": f"language.suggestions[{i}]",
            "item_type": "suggestion",
            "ai_content": content[:300],
            "ai_substitutability": sg.get("substitutability", "REVIEW"),
        })

    # A5 AcademicIntegrity
    integrity = feedback_json.get("integrity", {})
    cr = integrity.get("citation_report", {})
    if cr:
        issues = cr.get("format_issues", []) + cr.get("suspicious_citations", [])
        for i, iss in enumerate(issues):
            items.append({
                "agent_name": "A5-AcademicIntegrity",
                "item_path": f"integrity.citation_report.issues[{i}]",
                "item_type": "citation_issue",
                "ai_content": str(iss)[:300],
                "ai_substitutability": cr.get("substitutability", "FULL"),
            })
    or_report = integrity.get("originality_report", {})
    if or_report:
        flags = or_report.get("similarity_flags", []) + or_report.get("ai_generation_flags", [])
        for i, flg in enumerate(flags):
            items.append({
                "agent_name": "A5-AcademicIntegrity",
                "item_path": f"integrity.originality_report.flags[{i}]",
                "item_type": "originality_flag",
                "ai_content": str(flg)[:300],
                "ai_substitutability": or_report.get("substitutability", "ESCALATE"),
            })

    return items


def _api(path: str, method: str = "GET", **kwargs):
    url = f"{API_BASE}{path}"
    try:
        if method == "GET":
            resp = httpx.get(url, params=kwargs, timeout=120)
        elif method == "POST":
            resp = httpx.post(url, **kwargs, timeout=300)
        else:
            return {"error": f"Unsupported method: {method}"}
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_competitions():
    data = _api("/api/v1/competitions")
    if "error" in data:
        return []
    return [c["name"] for c in data.get("competitions", [])]


# -------------- Submit Review Tab --------------

def submit_review(file_obj, competition, student_name, model_provider):
    if file_obj is None:
        return "请先上传文件", None
    if not competition:
        return "请先选择竞赛", None

    tmp_path = None
    try:
        suffix = Path(file_obj).suffix if isinstance(file_obj, str) else ""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        if isinstance(file_obj, str):
            with open(file_obj, "rb") as src:
                tmp.write(src.read())
        else:
            tmp.write(file_obj.read() if hasattr(file_obj, "read") else file_obj)
        tmp.close()
        tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            files = {"file": (Path(file_obj).name if isinstance(file_obj, str) else "upload", f)}
            data = {"competition": competition, "student_name": student_name or ""}
            if model_provider:
                data["model_provider"] = model_provider

            resp = httpx.post(
                f"{API_BASE}/api/v1/review",
                data=data,
                files=files,
                timeout=300,
            )
            resp.raise_for_status()
            result = resp.json()

        scores_md = "## 评分明细\n\n"
        for agent, score in result.get("scores", {}).items():
            scores_md += f"- **{agent}**: {score}\n"

        meta = result.get("meta", {})
        meta_md = f"""
## 元数据
- **总评分**: {result.get('total_score')}
- **竞赛类型**: {result.get('competition_type')}
- **字数**: {meta.get('word_count')}
- **模型**: {meta.get('model')}
- **耗时**: {meta.get('duration_seconds')}s
"""

        errors_md = ""
        if result.get("errors"):
            errors_md = "\n## 错误\n" + "\n".join(f"- {e}" for e in result["errors"])

        full_report = json.dumps(result, ensure_ascii=False, indent=2)

        return scores_md + meta_md + errors_md, full_report

    except httpx.HTTPStatusError as e:
        return f"请求失败: HTTP {e.response.status_code}\n{e.response.text[:800]}", None
    except Exception as e:
        return f"错误: {e}", None
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


# -------------- Review History Tab --------------

def load_history(page: int = 0, page_size: int = 20):
    data = _api("/api/v1/reviews", offset=page * page_size, limit=page_size)
    if "error" in data:
        return [], f"加载失败: {data['error']}", 0

    rows = []
    for r in data.get("reviews", []):
        rows.append([
            r.get("submission_id", ""),
            r.get("student_name", ""),
            r.get("competition", ""),
            r.get("competition_type", ""),
            r.get("filename", ""),
            r.get("word_count", 0),
            r.get("total_score", "-"),
            r.get("model_provider", "-"),
            r.get("submitted_at", ""),
        ])

    total = data.get("total", 0)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return rows, f"共 {total} 条记录 (第 {page + 1}/{total_pages} 页)", total


def load_review_detail(submission_id: int):
    if not submission_id:
        return "请输入 Submission ID"

    data = _api(f"/api/v1/reviews/{submission_id}")
    if "error" in data:
        return f"加载失败: {data['error']}"

    info = f"""
## 提交信息
- **ID**: {data.get('submission_id')}
- **学生**: {data.get('student_name')}
- **竞赛**: {data.get('competition')} ({data.get('competition_type')})
- **文件**: {data.get('filename')}
- **字数**: {data.get('word_count')}
- **状态**: {data.get('status')}
- **时间**: {data.get('submitted_at')}
"""

    reviews_md = ""
    for rv in data.get("reviews", []):
        reviews_md += f"""
### Review #{rv.get('review_id')} ({rv.get('model_provider')})
- **总分**: {rv.get('total_score')}
- **Rubric**: {rv.get('scores', {}).get('rubric')}
- **Structure**: {rv.get('scores', {}).get('structure')}
- **Argument**: {rv.get('scores', {}).get('argument')}
- **Language**: {rv.get('scores', {}).get('language')}
- **Integrity**: {rv.get('scores', {}).get('integrity')}
- **耗时**: {rv.get('duration_seconds')}s
- **时间**: {rv.get('created_at')}
"""

    return info + reviews_md


# -------------- Config Stats Tab --------------

def load_stats():
    data = _api("/api/v1/config/stats")
    if "error" in data:
        return f"加载失败: {data['error']}"

    competitions = data.get("competitions", {})
    configs = data.get("configs", {})
    db = data.get("db", {})

    comp_md = f"""
## 竞赛配置
- **总数**: {competitions.get('total')}
- **类型**: {', '.join(competitions.get('types', []))}
"""

    config_md = f"""
## 配置文件统计
- Rubrics: {configs.get('rubrics')}
- Structure Schemas: {configs.get('structure_schemas')}
- Evidence Patterns: {configs.get('evidence_patterns')}
- Style Guides: {configs.get('style_guides')}
- Citation Rules: {configs.get('citation_rules')}
"""

    by_comp = db.get("by_competition", {})
    by_comp_md = "\n".join(f"- {k}: {v} 篇" for k, v in sorted(by_comp.items())) if by_comp else "- 暂无数据"

    db_md = f"""
## 数据库统计
- **总提交数**: {db.get('total_submissions')}

### 按竞赛分布
{by_comp_md}
"""

    return comp_md + config_md + db_md + _sync_status_md()


def _sync_status_md():
    try:
        from app.utils.sync import is_sync_enabled
        from app.config import settings, get_competition_list
        if is_sync_enabled():
            return f"""
## 同步状态
- **中央服务器**: {settings.sync_server_url}
- **本机标识**: {settings.instance_name or '(自动识别)'}
- 评审和校准数据会自动上报到中央服务器
"""
        else:
            return f"""
## 同步状态
- **中央服务器**: 未配置
- 如需团队协作，请在 .env 中设置 `SYNC_SERVER_URL`
"""
    except Exception:
        return ""


# -------------- Build UI --------------

CSS = """
.gradio-container { max-width: 1200px; margin: 0 auto; }
.report-box { font-family: monospace; font-size: 13px; }
"""


# ── Teacher Review functions ──

def load_review_for_teacher(submission_id: int):
    """加载评审结果供老师审核。返回 (annotated_md, items_summary, items_state)。"""
    if not submission_id or submission_id <= 0:
        return "请输入有效的 Submission ID", "", [], ""

    data = _api(f"/api/v1/reviews/{submission_id}")
    if "error" in data:
        return f"加载失败: {data['error']}", "", [], ""

    reviews = data.get("reviews", [])
    if not reviews:
        return "未找到评审记录", "", [], ""

    latest = reviews[0]
    feedback = latest.get("feedback", {})
    if isinstance(feedback, str):
        try:
            feedback = json.loads(feedback)
        except json.JSONDecodeError:
            feedback = {}

    # Build annotated markdown
    meta = feedback.get("meta", {})
    annotated_md = meta.get("annotated_md", "")

    # Show review summary
    scores = latest.get("scores", {})
    summary = f"""## 评审概要
- **ID**: {data.get('submission_id')}
- **学生**: {data.get('student_name', '-')}
- **竞赛**: {data.get('competition')} ({data.get('competition_type')})
- **总评分**: {latest.get('total_score', '-')}
- **A1-Rubric**: {scores.get('rubric', '-')} | **A2-Structure**: {scores.get('structure', '-')}
- **A3-Argument**: {scores.get('argument', '-')} | **A4-Language**: {scores.get('language', '-')}
- **A5-Integrity**: {scores.get('integrity', '-')} | **模型**: {latest.get('model_provider', '-')}
"""

    # Extract items
    items = _extract_review_items(feedback)

    # Build items summary
    full_count = sum(1 for it in items if it["ai_substitutability"] == "FULL")
    review_count = sum(1 for it in items if it["ai_substitutability"] == "REVIEW")
    escalate_count = sum(1 for it in items if it["ai_substitutability"] == "ESCALATE")

    items_md = f"""## 审核项列表（共 {len(items)} 条）

| # | Agent | 类型 | 置信度 | AI 判断 |
|---|-------|------|--------|---------|
"""
    for i, it in enumerate(items):
        emoji_map = {"FULL": "", "REVIEW": "⚡", "ESCALATE": "🔴"}
        emoji = emoji_map.get(it["ai_substitutability"], "")
        content = it["ai_content"].replace("\n", " ")[:120]
        sev = f"[{it.get('severity', '')}]" if it.get("severity") else ""
        items_md += f"| {i} | {it['agent_name']} | {it['item_type']}{sev} | {emoji}{it['ai_substitutability']} | {content} |\n"

    items_md += f"""
> **汇总**: {full_count} FULL (可直接信任) | {review_count} REVIEW (需确认) | {escalate_count} ESCALATE (必须审核)
"""

    full_report = annotated_md if annotated_md else "*(无标注报告)*"
    combined = summary + "\n---\n" + full_report
    items_json = json.dumps(items, ensure_ascii=False)

    return combined, items_md, items, items_json


def submit_teacher_feedback(submission_id: int, teacher_id: str, items_state: list, override_notes: str) -> str:
    """提交老师审核反馈。

    items_state: 从 load_review_for_teacher 返回的 items list
    override_notes: 覆写说明 JSON 文本，格式: [{"index": 0, "action": "OVERRIDE", "note": "..."}]
    """
    if not items_state:
        return "请先加载评审结果"

    # Parse override notes
    overrides = {}
    if override_notes and override_notes.strip():
        try:
            ov = json.loads(override_notes)
            for entry in ov:
                idx = entry.get("index")
                if idx is not None and 0 <= idx < len(items_state):
                    overrides[idx] = {
                        "action": entry.get("action", "OVERRIDE"),
                        "note": entry.get("note", ""),
                    }
        except json.JSONDecodeError:
            return "覆写说明格式错误：请输入有效的 JSON 数组"

    # Get review_id
    data = _api(f"/api/v1/reviews/{submission_id}")
    if "error" in data:
        return f"加载评审失败: {data['error']}"
    reviews = data.get("reviews", [])
    if not reviews:
        return "未找到评审记录"
    review_id = reviews[0].get("review_id")

    # Build corrections
    corrections = []
    for i, item in enumerate(items_state):
        if i in overrides:
            corrections.append({
                "agent_name": item["agent_name"],
                "item_path": item["item_path"],
                "item_type": item["item_type"],
                "ai_content": item["ai_content"],
                "ai_substitutability": item["ai_substitutability"],
                "teacher_action": overrides[i]["action"],
                "teacher_note": overrides[i]["note"],
            })
        else:
            corrections.append({
                "agent_name": item["agent_name"],
                "item_path": item["item_path"],
                "item_type": item["item_type"],
                "ai_content": item["ai_content"],
                "ai_substitutability": item["ai_substitutability"],
                "teacher_action": "CONFIRM",
                "teacher_note": "",
            })

    payload = {
        "review_id": review_id,
        "teacher_id": teacher_id or "anonymous",
        "corrections": corrections,
    }

    resp = _api("/api/v1/feedback", "POST", json=payload)
    if "error" in resp:
        return f"提交失败: {resp['error']}"

    confirmed = sum(1 for c in corrections if c["teacher_action"] == "CONFIRM")
    overridden = sum(1 for c in corrections if c["teacher_action"] == "OVERRIDE")
    refined = sum(1 for c in corrections if c["teacher_action"] == "REFINE")
    return f"✅ 反馈已提交 ({resp.get('saved', 0)} 条): {confirmed} 确认, {overridden} 修正, {refined} 细化"


def load_feedback_stats():
    """加载反馈统计。"""
    data = _api("/api/v1/feedback/stats")
    if "error" in data:
        return f"加载失败: {data['error']}"

    total = data.get("total_feedback", 0)
    if total == 0:
        return "暂无反馈数据。完成教师审核后自动积累。"

    md = f"""## 反馈闭环统计

**总计**: {total} 条反馈
**整体确认率**: {data.get('overall_confirmation_rate', 0)*100:.1f}%
  - ✅ 确认: {data.get('total_confirmed', 0)}
  - ✏️ 修正: {data.get('total_overridden', 0)}  
  - 🔧 细化: {data.get('total_refined', 0)}

### 按 Agent
| Agent | 总数 | 确认 | 修正 | 细化 | 确认率 |
|-------|------|------|------|------|--------|
"""
    by_agent = data.get("by_agent", {})
    for agent, stats in sorted(by_agent.items()):
        md += f"| {agent} | {stats['total']} | {stats['confirmed']} | {stats['overridden']} | {stats['refined']} | {stats['confirmation_rate']*100:.1f}% |\n"

    md += "\n### 按置信度标签\n"
    md += "| AI 标签 | 总数 | 确认 | 修正 | 细化 | 确认率 |\n"
    md += "|---------|------|------|------|------|--------|\n"
    by_sub = data.get("by_substitutability", {})
    for sub, stats in sorted(by_sub.items()):
        emoji = {"FULL": "", "REVIEW": "⚡", "ESCALATE": "🔴"}.get(sub, "")
        md += f"| {emoji}{sub} | {stats['total']} | {stats['confirmed']} | {stats['overridden']} | {stats['refined']} | {stats['confirmation_rate']*100:.1f}% |\n"

    return md


def build_ui():
    with gr.Blocks(title="AcademicReviewer") as demo:
        gr.Markdown("# AcademicReviewer — 学术竞赛论文智能评审系统")
        gr.Markdown("""
> **隐私声明**：提交的论文全文将发送到您选择的 LLM 提供商（DeepSeek / OpenAI / Gemini / GLM）的 API 进行评审处理。
> 请勿上传包含身份证号、联系方式等个人敏感信息的学生作品。评审结果仅在本地 SQLite 数据库存储，不上传至第三方。
> 团队协作模式下，评审数据经内网同步到中央服务器，传输内容与上述相同。
""")

        with gr.Tabs():
            # Tab 1: Submit Review
            with gr.TabItem("提交评审"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 上传文档")
                        file_input = gr.File(label="上传文件 (txt, pdf, docx)", file_types=[".txt", ".pdf", ".docx"])
                        competition_dropdown = gr.Dropdown(
                            label="竞赛名称 (可输入新赛事名称)",
                            choices=fetch_competitions(),
                            value="ISEF",
                            interactive=True,
                            allow_custom_value=True,
                        )
                        refresh_btn = gr.Button("刷新竞赛列表", size="sm")
                        refresh_btn.click(fn=lambda: gr.Dropdown(choices=fetch_competitions()), outputs=[competition_dropdown])

                        student_name = gr.Textbox(label="学生姓名 (可选)", placeholder="张三")
                        model_provider = gr.Dropdown(
                            label="模型提供商",
                            choices=["deepseek", "openai", "gemini", "glm"],
                            value="deepseek",
                        )
                        submit_btn = gr.Button("开始评审", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        gr.Markdown("### 评审结果")
                        result_md = gr.Markdown("等待提交...")
                        result_json = gr.Code(label="完整 JSON 报告", language="json", visible=False)

                submit_btn.click(
                    fn=submit_review,
                    inputs=[file_input, competition_dropdown, student_name, model_provider],
                    outputs=[result_md, result_json],
                )

            # Tab 2: Review History
            with gr.TabItem("评审历史"):
                with gr.Row():
                    page_slider = gr.Slider(minimum=0, maximum=50, value=0, step=1, label="页码")
                    page_size = gr.Number(value=20, label="每页条数", precision=0)
                    load_btn = gr.Button("刷新", variant="secondary")

                history_table = gr.Dataframe(
                    headers=["ID", "学生", "竞赛", "类型", "文件名", "字数", "评分", "模型", "提交时间"],
                    label="评审记录",
                    interactive=False,
                    wrap=True,
                )
                history_info = gr.Markdown("")

                with gr.Accordion("查看详情", open=False):
                    detail_id = gr.Number(label="Submission ID", value=0, precision=0)
                    detail_btn = gr.Button("加载详情")
                    detail_md = gr.Markdown("")

                load_btn.click(
                    fn=load_history,
                    inputs=[page_slider, page_size],
                    outputs=[history_table, history_info, gr.Number(value=0, visible=False)],
                )
                detail_btn.click(
                    fn=load_review_detail,
                    inputs=[detail_id],
                    outputs=[detail_md],
                )

            # Tab 3: Config Stats
            with gr.TabItem("系统状态"):
                stats_btn = gr.Button("加载统计", variant="primary")
                stats_md = gr.Markdown("点击按钮加载系统统计信息")
                stats_btn.click(fn=load_stats, outputs=[stats_md])

                with gr.Accordion(" 从中央服务器同步最新配置", open=False):
                    gr.Markdown("将管理员审核后的最新竞赛评分标准、结构模式、风格指南等同步到本地。")
                    sync_preview_btn = gr.Button("预览变更", variant="secondary")
                    sync_apply_btn = gr.Button("确认同步", variant="primary", size="sm")
                    sync_result = gr.Markdown("")

                    def do_sync_preview():
                        from app.utils.sync import pull_configs_from_server
                        return pull_configs_from_server(dry_run=True)

                    def do_sync_apply():
                        from app.utils.sync import pull_configs_from_server
                        return pull_configs_from_server(dry_run=False)

                    sync_preview_btn.click(fn=do_sync_preview, outputs=[sync_result])
                    sync_apply_btn.click(fn=do_sync_apply, outputs=[sync_result])

            # Tab 4: Calibration
            with gr.TabItem("校准引擎"):
                gr.Markdown("### 校准引擎 — 分析获奖/失败文章差距")
                gr.Markdown("上传我方获奖文章和失败文章目录（.txt/.md），系统将自动提取特征并生成校准报告。")

                cal_competition = gr.Dropdown(
                    label="竞赛名称 (可输入新赛事名称)",
                    choices=[c["name"] for c in get_competition_list()],
                    value="ISEF",
                    allow_custom_value=True,
                )
                cal_type = gr.Dropdown(
                    label="竞赛类型",
                    choices=sorted(set(c["type"] for c in get_competition_list())),
                    value="research",
                    allow_custom_value=True,
                )

                def on_competition_change(selected):
                    for c in get_competition_list():
                        if c["name"] == selected:
                            return c["type"]
                    return "research"

                cal_competition.change(fn=on_competition_change, inputs=[cal_competition], outputs=[cal_type])
                with gr.Row():
                    cal_winners = gr.File(label="我方获奖文章 (可多选)", file_count="multiple", file_types=[".txt", ".md", ".pdf", ".docx"])
                    cal_losers = gr.File(label="我方失败文章 (可多选)", file_count="multiple", file_types=[".txt", ".md", ".pdf", ".docx"])
                cal_external = gr.File(label="外部获奖文章 (可选)", file_count="multiple", file_types=[".txt", ".md", ".pdf", ".docx"])
                cal_expert = gr.File(label="教师经验文档 (可选，.md/.pdf/.docx格式)", file_count="multiple", file_types=[".md", ".pdf", ".docx"])
                cal_output = gr.Textbox(label="报告输出路径 (可选)", placeholder="留空则在下方显示")
                cal_btn = gr.Button("运行校准", variant="primary", size="lg")
                cal_report = gr.Markdown("等待运行...", elem_classes="report-box")

                def run_calibration_ui(competition, comp_type, winners, losers, external, expert_docs, output_path):
                    winners = winners or []
                    losers = losers or []
                    external = external or []
                    expert_docs = expert_docs or []
                    if not (winners or losers or external or expert_docs):
                        return "❌ 请至少上传一组文件（获奖文章 / 失败文章 / 外部获奖文章 / 教师经验文档 任选其一即可）"

                    import shutil
                    from app.calibration.engine import run_calibration

                    winner_dir = tempfile.mkdtemp(prefix="cal_win_")
                    loser_dir = tempfile.mkdtemp(prefix="cal_los_")
                    ext_dir = tempfile.mkdtemp(prefix="cal_ext_") if external else None
                    expert_dir = tempfile.mkdtemp(prefix="cal_exp_") if expert_docs else None
                    output_file = output_path if output_path else None

                    try:
                        for f in winners:
                            dest = Path(winner_dir) / Path(f).name
                            dest.write_bytes(Path(f).read_bytes())
                        for f in losers:
                            dest = Path(loser_dir) / Path(f).name
                            dest.write_bytes(Path(f).read_bytes())
                        if external and ext_dir:
                            for f in external:
                                dest = Path(ext_dir) / Path(f).name
                                dest.write_bytes(Path(f).read_bytes())
                        if expert_docs and expert_dir:
                            for f in expert_docs:
                                dest = Path(expert_dir) / Path(f).name
                                dest.write_bytes(Path(f).read_bytes())

                        winner_files = [str(Path(winner_dir) / Path(f).name) for f in winners]
                        loser_files = [str(Path(loser_dir) / Path(f).name) for f in losers]
                        ext_files = []
                        if external and ext_dir:
                            ext_files = [str(Path(ext_dir) / Path(f).name) for f in external] if ext_dir else []
                        expert_files = []
                        if expert_docs and expert_dir:
                            expert_files = [str(Path(expert_dir) / Path(f).name) for f in expert_docs] if expert_dir else []

                        report = run_calibration(
                            competition=competition,
                            competition_type=comp_type,
                            winner_files=winner_files,
                            loser_files=loser_files,
                            external_winner_files=ext_files or None,
                            expert_doc_paths=expert_files or None,
                            output_report_path=output_file,
                        )

                        if output_file:
                            return f"报告已保存到: {output_file}\n\n{report[-3000:]}" if report else "校准完成"
                        return report or "校准完成（无输出）"

                    except Exception as e:
                        import traceback
                        return f"校准失败:\n{traceback.format_exc()}"
                    finally:
                        shutil.rmtree(winner_dir, ignore_errors=True)
                        shutil.rmtree(loser_dir, ignore_errors=True)
                        if ext_dir:
                            shutil.rmtree(ext_dir, ignore_errors=True)
                        if expert_dir:
                            shutil.rmtree(expert_dir, ignore_errors=True)

                cal_btn.click(
                    fn=run_calibration_ui,
                    inputs=[cal_competition, cal_type, cal_winners, cal_losers, cal_external, cal_expert, cal_output],
                    outputs=[cal_report],
                )

            # Tab 5: Admin Dashboard
            with gr.TabItem("管理看板"):
                gr.Markdown("###  数据汇总看板")
                gr.Markdown("展示所有同事实例上报的评审和校准数据汇总。仅中央服务器可用。")

                admin_btn = gr.Button("加载汇总数据", variant="primary", size="lg")
                admin_md = gr.Markdown("点击按钮加载...")

                def load_admin_dashboard():
                    data = _api("/api/v1/admin/dashboard")
                    if "error" in data:
                        return f"加载失败: {data['error']}"

                    summary = data.get("summary", {})
                    reviews_by_comp = data.get("reviews_by_competition", {})
                    cals_by_comp = data.get("calibrations_by_competition", {})
                    cals_by_instance = data.get("calibrations_by_instance", {})
                    recent = data.get("recent_calibrations", [])

                    md = f"""
##   汇总概览
- **评审总数**: {summary.get('total_reviews', 0)}
- **校准次数**: {summary.get('total_calibrations', 0)}
- **接入实例数**: {summary.get('total_instances', 0)}
- **实例列表**: {', '.join(summary.get('instances', [])) or '(无)'}

##   评审分布
"""
                    for k, v in sorted(reviews_by_comp.items()):
                        md += f"- {k}: {v} 篇\n"

                    md += f"\n##   校准分布（按实例）\n"
                    for k, v in sorted(cals_by_instance.items()):
                        md += f"- {k}: {v} 次\n"

                    md += f"\n##   校准分布（按竞赛）\n"
                    for k, v in sorted(cals_by_comp.items()):
                        md += f"- {k}: {v} 次\n"

                    if recent:
                        md += f"\n##   最近校准记录\n"
                        md += "| 实例 | 竞赛 | 获奖 | 失败 | 时间 |\n"
                        md += "|------|------|------|------|------|\n"
                        for r in recent:
                            md += f"| {r['instance']} | {r['competition']} | {r['winners']} | {r['losers']} | {r.get('created_at', '')} |\n"

                    return md

                admin_btn.click(fn=load_admin_dashboard, outputs=[admin_md])

            # Tab 6: Competition Management
            with gr.TabItem("赛事管理"):
                gr.Markdown("### 🏆 赛事注册管理")
                gr.Markdown("添加、编辑或删除赛事信息。修改后即时生效，旧配置会自动备份。")

                comp_list_md = gr.Markdown("点击「加载赛事列表」查看当前注册的赛事")

                def load_comp_list():
                    data = _api("/api/v1/admin/competitions")
                    if "error" in data:
                        return f"加载失败: {data['error']}"
                    comps = data.get("competitions", [])
                    types = data.get("types", {})
                    md = f"### 当前已注册 {len(comps)} 个赛事\n\n"
                    md += "| 名称 | 类型 | 引用格式 | 别名 |\n"
                    md += "|------|------|----------|------|\n"
                    for c in comps:
                        cn = types.get(c.get("type", ""), c.get("type", ""))
                        aliases = ", ".join(c.get("aliases", [])[:3])
                        md += f"| {c['_name']} | {cn}({c.get('type','')}) | {c.get('citation_style','')} | {aliases} |\n"
                    return md

                load_comp_btn = gr.Button("加载赛事列表", variant="secondary")
                load_comp_btn.click(fn=load_comp_list, outputs=[comp_list_md])

                gr.Markdown("---")
                gr.Markdown("### ➕ 添加/编辑赛事")

                with gr.Row():
                    new_name = gr.Textbox(label="赛事名称 *", placeholder="如: IMMC, Conrad Challenge")
                    new_type = gr.Dropdown(
                        label="竞赛类型 *",
                        choices=sorted(set(c["type"] for c in get_competition_list())),
                        value="research",
                    )
                new_subtype = gr.Textbox(label="子类型 (可选)", placeholder="如: advanced, economics")
                with gr.Row():
                    new_structure = gr.Dropdown(
                        label="结构模板",
                        choices=[c["structure_schema"] for c in get_competition_list()],
                        value="research.json",
                    )
                    new_evidence = gr.Dropdown(
                        label="证据标准",
                        choices=sorted(set(c["evidence_config"] for c in get_competition_list())),
                        value="research.json",
                    )
                with gr.Row():
                    new_style = gr.Dropdown(
                        label="风格模板",
                        choices=sorted(set(c["style_template"] for c in get_competition_list())),
                        value="tech_academic.json",
                    )
                    new_citation = gr.Dropdown(label="引用格式", choices=["APA", "MLA", "Chicago"], value="APA")
                new_aliases = gr.Textbox(
                    label="别名 (逗号分隔)",
                    placeholder="如: immc, 国际数学建模挑战赛, IMMC竞赛",
                    value="",
                )

                def add_competition_fn(name, comp_type, subtype, structure, evidence, style, citation, aliases):
                    if not name or not name.strip():
                        return "❌ 赛事名称不能为空", gr.update()
                    data = _api("/api/v1/admin/competitions")
                    if "error" in data:
                        return f"❌ 读取失败: {data['error']}", gr.update()
                    comps = data.get("competitions", [])
                    found = False
                    for c in comps:
                        if c["_name"] == name.strip():
                            c["type"] = comp_type
                            c["subtype"] = subtype.strip() or None
                            c["structure_schema"] = structure
                            c["evidence_config"] = evidence
                            c["style_template"] = style
                            c["citation_style"] = citation
                            c["aliases"] = [a.strip() for a in aliases.split(",") if a.strip()]
                            found = True
                            break
                    if not found:
                        comps.append({
                            "_name": name.strip(),
                            "type": comp_type,
                            "subtype": subtype.strip() or None,
                            "structure_schema": structure,
                            "evidence_config": evidence,
                            "style_template": style,
                            "citation_style": citation,
                            "aliases": [a.strip() for a in aliases.split(",") if a.strip()],
                        })
                    payload = {"competitions": comps, "types": data.get("types", {})}
                    save = _api("/api/v1/admin/competitions", "POST", json=payload)
                    if "error" in save:
                        return f"❌ 保存失败: {save['error']}", gr.update()
                    action = "更新" if found else "添加"
                    return f"✅ 已{action}赛事「{name.strip()}」(共 {save.get('count', '?')} 个赛事)", gr.update()

                add_comp_btn = gr.Button("保存赛事", variant="primary", size="lg")
                add_result = gr.Markdown("")

                add_comp_btn.click(
                    fn=add_competition_fn,
                    inputs=[new_name, new_type, new_subtype, new_structure, new_evidence, new_style, new_citation, new_aliases],
                    outputs=[add_result, comp_list_md],
                )

                gr.Markdown("---")
                gr.Markdown("### 🗑️ 删除赛事")
                with gr.Row():
                    del_name = gr.Dropdown(
                        label="选择要删除的赛事",
                        choices=[c["name"] for c in get_competition_list()],
                    )

                    def delete_competition_fn(name):
                        if not name:
                            return "请选择赛事", gr.update(choices=[c["name"] for c in get_competition_list()])
                        data = _api("/api/v1/admin/competitions")
                        comps = data.get("competitions", [])
                        comps = [c for c in comps if c["_name"] != name]
                        payload = {"competitions": comps, "types": data.get("types", {})}
                        save = _api("/api/v1/admin/competitions", "POST", json=payload)
                        if "error" in save:
                            return f"❌ {save['error']}", gr.update(choices=[c["name"] for c in get_competition_list()])
                        return f"✅ 已删除「{name}」(剩余 {save.get('count', '?')} 个赛事)", gr.update(choices=[c["_name"] for c in comps])

                    del_btn = gr.Button("确认删除", variant="stop")
                    del_result = gr.Markdown("")
                    del_btn.click(fn=delete_competition_fn, inputs=[del_name], outputs=[del_result, del_name])

            # Tab 7: Teacher Review (Phase 3: 反馈闭环)
            with gr.TabItem("教师审核"):
                gr.Markdown("### 📝 教师审核 — AI评审结果人工复核")
                gr.Markdown("加载已完成的评审，逐条确认/修正/细化 AI 的评审意见，积累数据用于置信度校准。")

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### 1. 加载评审")
                        teacher_submission_id = gr.Number(label="Submission ID", value=0, precision=0)
                        teacher_id_input = gr.Textbox(label="教师姓名", placeholder="张老师")
                        load_review_btn = gr.Button("加载评审", variant="primary")
                        teacher_items_state = gr.State([])

                    with gr.Column(scale=1):
                        gr.Markdown("#### 2. 提交反馈")
                        gr.Markdown("覆写项格式 (JSON): `[{\"index\": 0, \"action\": \"OVERRIDE\", \"note\": \"...\"}]`")
                        gr.Markdown("- action: CONFIRM / OVERRIDE / REFINE")
                        override_notes = gr.Textbox(
                            label="覆写说明 (可选)",
                            placeholder='[{"index": 3, "action": "OVERRIDE", "note": "rebuttal 确实回应了核心主张"}]',
                            lines=4,
                        )
                        submit_feedback_btn = gr.Button("提交审核反馈", variant="primary", size="lg")
                        submit_all_confirm_btn = gr.Button("全部确认 (快速通道)", variant="secondary")

                teacher_result = gr.Markdown("")

                with gr.Accordion("📋 审核项明细", open=True):
                    teacher_items_md = gr.Markdown("加载评审后显示")

                with gr.Accordion("📄 标注报告", open=False):
                    teacher_annotated_md = gr.Markdown("加载评审后显示", elem_classes="report-box")

                load_review_btn.click(
                    fn=load_review_for_teacher,
                    inputs=[teacher_submission_id],
                    outputs=[teacher_annotated_md, teacher_items_md, teacher_items_state, gr.State("")],
                )

                submit_feedback_btn.click(
                    fn=submit_teacher_feedback,
                    inputs=[teacher_submission_id, teacher_id_input, teacher_items_state, override_notes],
                    outputs=[teacher_result],
                )

                submit_all_confirm_btn.click(
                    fn=lambda sid, tid, items: submit_teacher_feedback(sid, tid, items, ""),
                    inputs=[teacher_submission_id, teacher_id_input, teacher_items_state],
                    outputs=[teacher_result],
                )

                gr.Markdown("---")
                gr.Markdown("### 📊 反馈闭环统计")
                feedback_stats_btn = gr.Button("加载统计", variant="secondary")
                feedback_stats_md = gr.Markdown("点击加载反馈统计数据")
                feedback_stats_btn.click(fn=load_feedback_stats, outputs=[feedback_stats_md])

                gr.Markdown("---")
                gr.Markdown("### 💡 知识卡更新建议")
                gr.Markdown("检测被老师反复纠正的审核模式，建议补充或修正知识卡条目。")
                with gr.Row():
                    suggestion_threshold = gr.Number(label="触发阈值 (最低修正次数)", value=3, precision=0)
                    suggestion_btn = gr.Button("检测建议", variant="secondary")
                suggestion_md = gr.Markdown("")

                def load_feedback_suggestions(threshold_val):
                    data = _api(f"/api/v1/feedback/suggestions?threshold={int(threshold_val or 3)}")
                    if "error" in data:
                        return f"加载失败: {data['error']}"
                    suggestions = data.get("suggestions", [])
                    if not suggestions:
                        return f"✅ 当前无建议（共 {data.get('total_override_events', 0)} 次修正事件，均未超过阈值 {data['threshold']}）"

                    md = f"## 知识卡更新建议（阈值={data['threshold']}）\n\n"
                    md += f"共 {data['total_override_events']} 次修正事件，{len(suggestions)} 个高频模式：\n\n"
                    md += "| Agent | 条目类型 | 被修正次数 | 建议知识卡类型 | 教师备注样例 |\n"
                    md += "|-------|----------|-----------|---------------|-------------|\n"
                    for s in suggestions:
                        notes = "; ".join(s.get("sample_teacher_notes", [])[:2])
                        md += f"| {s['agent_name']} | {s['item_type']} | {s['override_count']} | {s['knowledge_card_type']} | {notes[:100]} |\n"
                    md += f"\n> {data.get('note', '')}"
                    return md

                suggestion_btn.click(
                    fn=load_feedback_suggestions,
                    inputs=[suggestion_threshold],
                    outputs=[suggestion_md],
                )

    return demo


def main():
    demo = build_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        css=CSS,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
