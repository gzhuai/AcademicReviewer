import json
import logging
import os
import tempfile
from pathlib import Path

import gradio as gr
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gradio_app")

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")


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
        from app.config import settings
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

def build_ui():
    css = """
    .gradio-container { max-width: 1200px; margin: 0 auto; }
    .report-box { font-family: monospace; font-size: 13px; }
    """

    with gr.Blocks(title="AcademicReviewer", css=css, theme=gr.themes.Soft()) as demo:
        gr.Markdown("# AcademicReviewer — 学术竞赛论文智能评审系统")

        with gr.Tabs():
            # Tab 1: Submit Review
            with gr.TabItem("提交评审"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 上传文档")
                        file_input = gr.File(label="上传文件 (txt, pdf, docx)", file_types=[".txt", ".pdf", ".docx"])
                        competition_dropdown = gr.Dropdown(
                            label="竞赛名称",
                            choices=fetch_competitions(),
                            value="ISEF",
                            interactive=True,
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

            # Tab 4: Calibration
            with gr.TabItem("校准引擎"):
                gr.Markdown("### 校准引擎 — 分析获奖/失败文章差距")
                gr.Markdown("上传我方获奖文章和失败文章目录（.txt/.md），系统将自动提取特征并生成校准报告。")

                cal_competition = gr.Textbox(label="竞赛名称", value="ISEF")
                cal_type = gr.Textbox(label="竞赛类型", value="research")
                with gr.Row():
                    cal_winners = gr.File(label="我方获奖文章 (可多选)", file_count="multiple", file_types=[".txt", ".md"])
                    cal_losers = gr.File(label="我方失败文章 (可多选)", file_count="multiple", file_types=[".txt", ".md"])
                cal_external = gr.File(label="外部获奖文章 (可选)", file_count="multiple", file_types=[".txt", ".md"])
                cal_expert = gr.File(label="教师经验文档 (可选，.md格式)", file_count="multiple", file_types=[".md"])
                cal_output = gr.Textbox(label="报告输出路径 (可选)", placeholder="留空则在下方显示")
                cal_btn = gr.Button("运行校准", variant="primary", size="lg")
                cal_report = gr.Markdown("等待运行...", elem_classes="report-box")

                def run_calibration_ui(competition, comp_type, winners, losers, external, expert_docs, output_path):
                    if not winners or not losers:
                        return "请上传获奖文章和失败文章"

                    import subprocess
                    import sys

                    winner_dir = tempfile.mkdtemp(prefix="cal_win_")
                    loser_dir = tempfile.mkdtemp(prefix="cal_los_")
                    ext_dir = tempfile.mkdtemp(prefix="cal_ext_") if external else None
                    expert_dir = tempfile.mkdtemp(prefix="cal_exp_") if expert_docs else None

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

                        cmd = [
                            sys.executable, "cli/calibrate.py",
                            "--competition", competition,
                            "--type", comp_type,
                            "--winners", winner_dir,
                            "--losers", loser_dir,
                        ]
                        if ext_dir and external:
                            cmd.extend(["--external", ext_dir])
                        if expert_dir and expert_docs:
                            cmd.extend(["--expert-docs", expert_dir])
                        if output_path:
                            cmd.extend(["--output", output_path])

                        result = subprocess.run(
                            cmd,
                            cwd=str(Path(__file__).resolve().parent.parent),
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )

                        if result.returncode != 0:
                            return f"校准失败:\n```\n{result.stderr}\n```"

                        if output_path:
                            return f"报告已保存到: {output_path}\n\n{result.stdout[-3000:]}"
                        return result.stdout or "校准完成（无输出）"

                    except subprocess.TimeoutExpired:
                        return "校准超时 (>120s)"
                    except Exception as e:
                        return f"错误: {e}"
                    finally:
                        import shutil
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

    return demo


def main():
    demo = build_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
    )


if __name__ == "__main__":
    main()
