# CLAUDE.md — AcademicReviewer

## 项目概览

学术竞赛论文智能评审系统，基于 5 个 LLM Agent 并行协作的自动化评审工具。
支持 ISEF、John Locke、SIC、WGHS、HiMCM 等学术/投资竞赛。

- **后端**: FastAPI (port 8000, `run.py` → `app/main.py`)
- **前端**: Gradio (port 7860, `app/gradio_app.py`)
- **数据库**: SQLite (`data/academic_reviewer.db`)
- **LLM**: DeepSeek / OpenAI / Gemini / GLM 可切换

## 架构

```
用户上传论文 + 选择竞赛 + 模型
  → POST /api/v1/review
  → Orchestrator.review()
    → lookup_competition() → 读取 configs/competition_registry.json
    → _load_rubric_config() → configs/rubrics/{竞赛名}_2026.json
    → _load_knowledge_cards_for_competition() → data/expert_insights/*.md
    → Round 1 (并行): A1-RubricParser + A2-StructureLogic + A3-ArgumentEvidence
    → Round 2 (并行): A4-LanguageStyle + A5-AcademicIntegrity
    → _compute_total_score() → 加权平均
    → build_annotated_markdown() → 标注报告
    → 返回 ReviewReport → 存储到 DB → 返回 API
```

### 核心文件

| 文件 | 职责 |
|------|------|
| `app/orchestrator.py` | 编排 5 Agent 两轮并行执行，rubric/知识卡加载，评分计算 |
| `app/agents/` | 5 个 Agent 实现（rubric_parser, structure_logic, argument_evidence, language_style, academic_integrity），均继承 BaseAgent |
| `app/agents/base.py` | Agent 基类，`chat_json()` 调用 LLM，max_tokens 控制输出长度 |
| `app/llm/` | LLM 适配器（openai, deepseek, gemini, glm），工厂模式创建 |
| `app/calibration/engine.py` | 校准引擎：对比获奖/失败文章，提取特征差异，解析教师文档 |
| `app/calibration/expert_annotator.py` | 教师经验文档解析器（结构化 Mode 3 + 自由格式 Mode 1/2） |
| `app/calibration/knowledge_cards.py` | 将 ExpertInsights 分层渲染为 Prompt 文本块 |
| `app/gradio_app.py` | Gradio UI，7 个 Tab，反馈渲染，校准保存 |
| `app/utils/confidence_engine.py` | 置信度标签引擎（FULL/REVIEW/ESCALATE） |
| `app/utils/annotation_builder.py` | 标注报告生成 |
| `prompts/` | 5 个 Agent 的 System Prompt 模板（a1-a5） |
| `configs/rubrics/` | 各竞赛评分标准 |
| `configs/structure_schemas/` | 各竞赛类型结构模板 |
| `configs/evidence_patterns/` | 各竞赛类型证据标准 |
| `configs/style_guides/` | 各竞赛类型风格指南 |
| `data/expert_insights/` | 教师上传的经验文档，评审时自动加载为知识卡 |

### Agent 评分键

| Agent | score_key | 权重（默认） |
|-------|-----------|-------------|
| RubricParser | rubric_score | 0.25 |
| StructureLogic | structure_score | 0.20 |
| ArgumentEvidence | overall_score | 0.25 |
| LanguageStyle | overall_language_score (嵌套在 summary 内) | 0.15 |
| AcademicIntegrity | integrity_score | 0.15 |

## 已知问题与注意事项

### 1. Rubric 加载链断裂风险

`_load_rubric_config()` 的解析顺序：
1. `configs/rubrics/{竞赛名_normalized}_2026.json`（精确匹配）
2. `configs/rubrics/{竞赛类型}_2026.json`（类型 fallback，如 finance_2026.json）
3. `configs/rubrics/isef_2026.json`（最终保底）

**新增竞赛时**，必须确保至少有一条链路存在。如果三个都没有，系统不会报错但会用一个完全不匹配的 ISEF 科学竞赛标准来评审投资报告等项目。

### 2. Agent JSON 输出截断

`app/agents/base.py` 中 `max_tokens=16384`。如果 LLM 输出超过这个限制，JSON 解析会失败（返回 `parse_error` + `raw_output`）。
`_try_parse_raw_output()` 在 `gradio_app.py` 中尝试恢复截断的 JSON，但它只能恢复完整闭合的结构。
**如果增加新 Agent 或 prompt 要求更多输出，需要同步提高 max_tokens。**

### 3. A4 语言 Agent 假阳性问题

A4 (LanguageStyle) 的 prompt 历史上缺少"无错误则不输出"的约束，导致 LLM 逐句原样照抄产生大量假修正（85/87 条 original==corrected）。
已在 2026-06-23 修复 prompt（增加 5 条硬性约束），但如果再次出现大量回退到旧行为的情况，检查 prompt 是否被覆盖。

### 4. 校准→知识卡管道需要手动确认

校准引擎解析教师文档后**不会自动保存**到 `data/expert_insights/`。
用户必须在校准 Tab 中点击「💾 确认保存为正式经验」按钮才会写入文件。
这是设计决策——防止上传错误的文档自动污染评审标准。

### 5. 前端反馈区域需关注性能

`_render_feedback_markdown()` 函数约 280 行，对大数据量的反馈（如 87 条 rewrites）会生成很长的 Markdown（实测 22KB+）。
Gradio Markdown 组件对超长内容渲染可能较慢，如果反馈文本超过 50KB，考虑分页或折叠显示。

### 6. 竞赛注册与配置同步

`configs/competition_registry.json` 是竞赛配置的单一事实源。
通过 Gradio 的「赛事管理」Tab 修改竞赛配置后会自动备份旧文件为 `.json.bak`。
如果中央同步开启，配置还需手动从服务器拉取。

## 2026-06-23 修复记录

### Commit c732c5e: 四项系统性修复

1. **前端反馈显示缺失**（曾遗漏的问题：评审完成后只显示分数不显示文字反馈）
   - API 返回了完整的 rubric/structure/argument/language/integrity 数据
   - 但 `gradio_app.py` 的 `submit_review()` 只渲染了 scores 和 meta
   - 新增 `_render_feedback_markdown()` 将 5 个 Agent 的输出结构化为可读 Markdown
   - 新增 `_try_parse_raw_output()` 恢复被 max_tokens 截断的 JSON（跟踪 {}[] 深度+自动闭合）

2. **SIC 评分标准错误**（输出的是 ISEF 科学竞赛维度：研究假设/实验设计/数据分析...）
   - 根因：`configs/rubrics/sic_2026.json` 不存在，fallback 硬编码为 `isef_2026.json`
   - 虽然 registry 中 SIC 的 type=finance、其他配置（schema/evidence/style）都是正确的
   - 新建 `sic_2026.json`（6 个投资维度）和 `finance_2026.json`（类型 fallback）
   - 修改 `orchestrator._load_rubric_config()` 增加 type-based 回退

3. **A4 语言 Agent 87 条修正中 85 条是误报**（original==corrected）
   - 根因：prompt 没有"无错误则不列出"的约束，LLM 被强制检查每句话
   - 修改 `prompts/a4_language_style.txt` 增加 5 条硬约束

4. **校准引擎上传的教师文档没有进入评审**
   - 根因：校准引擎解析后只显示报告，从未写入 `data/expert_insights/`
   - `run_calibration()` 改为返回 `(report, expert_insights)` 元组
   - Gradio 校准 Tab 新增「💾 确认保存为正式经验」按钮

5. **Agent max_tokens 4096→16384** 防止 JSON 输出被截断

### 对比测试数据（SIC S15 Team 20）

教师批注版（docx 24 条批注，另一个 AI Agent 生成）vs 当前系统评审结果：

| 维度 | 教师批注版 | 修复前当前系统 | 修复后预期 |
|------|-----------|---------------|-----------|
| 评分标准 | 投资竞赛维度 | ❌ ISEF科学维度 | ✅ 投资6维度 |
| 事实核查 | 发现目标价矛盾/ticker错误/计算错误 | ❌ 未做 | ⚠️ 仍依赖LLM |
| 竞赛专业知识 | 杜邦分析/WACC拆解 | ❌ 不知道 | ✅ Rubric要求 |
| 格式检查 | 封面/页数/拼写 | ❌ 未检查 | ✅ 展示维度包含 |
| 逻辑推理 | 有 | ✅ 后见之明/幸存者偏差 | ✅ 保持 |
| 语言修正精度 | 精准 | ❌ 85/87假阳性 | ✅ 硬约束 |
| 引用检查 | — | ✅ AI幻觉检测 | ✅ 保持 |
