# Changelog

## v0.6.1 (2026-06-24) — 稳定性修复 + docx 导出 + 项目清理

### A4 假阳性三层防御
- **问题**: 评审结果中 ~80 条 rewrites 的 original==corrected（逐句照抄假阳性）
- **修复**: 三层防御体系
  - Prompt 层 — 反例警告 + 输出前必检清单 + 数量硬上限 30 条
  - 数据管道层 — `confidence_engine._sanitize_rewrites()` 入库前强制剔除 identical 条目
  - 渲染层 — `_render_feedback_markdown()` 展示前再次过滤
- 日志: `[LanguageStyle] Sanitized rewrites: removed X false-positive entries`

### .docx 批注导出
- **新增 `app/utils/docx_exporter.py`** (370 行): 将原文 + 5 Agent 评审导出为 Word .docx 批注文档
  - 真实 Word 批注 (comments.xml) — 右键点击气泡可见完整评审意见
  - 语法修正内联显示 (删除线红色原文 → 加粗绿色修正)
  - 段落注解 (A2 结构 / A3 论证 / A4 语言 / A5 学术诚信，分色标注)
  - 置信度标记 (⚡ REVIEW / 🔴 ESCALATE / 无标记 FULL)
  - 总结章节 (评分表格 + 各 Agent 发现 + 元数据)
- **Gradio**: 评审结果页面新增「📥 导出批注文档 (.docx)」按钮
- **API**: `GET /api/v1/reviews/{id}/export` → FileResponse
- 通过 lxml + zipfile 直接操作 OOXML 包，python-docx 渲染内容

### 安装指南修复 (12 项)
- **严重**: `.env` API Key 泄露 → 占位值；`requirements-lock.txt` UTF-16→UTF-8 重新生成
- **关键**: `start_all.sh` 新增 headless/SSH 后台进程 fallback；`install.bat` 新增 PowerShell 检测
- **优化**: `requirements.txt` 收紧版本范围 (chromadb>=1.0.0/<2.0.0, gradio>=5.0.0/<7.0.0)，显式添加 python-dotenv
- **新增**: `install.ps1`/`install.sh` 磁盘空间预检 (<2GB 拒绝安装)；README 首次安装前必读 + 常见问题表 + 手动安装步骤
- `docs/使用指南.html` 15 个失效的 trae-api 占位图 → 📷 文字占位

### 项目清理 (16 项)
- **删除 8 个文件**: 一次性测试制品 (5Agent_审稿/测试计划等)、硬编码个人路径的 PDF 提取脚本、赛事注册自动备份
- **移除 3 个未使用依赖**: `openai`、`google-generativeai`、`zhipuai` (所有适配器用 httpx 裸调)
- **移除死代码**: `app/main.py` 未使用 import；`app/database.py` `get_db()`；`app/utils/vector_store.py` `index_document()`/`remove_document()`；`app/agents/academic_integrity.py` `submission_id` 参数
- **消除重复**: `_split_paragraphs()`/`_parse_location()` 提取到 `app/utils/text_utils.py` 统一维护
- 修正 `AI_HANDOFF.md` 中不存在的 `launcher.py` 引用、Tab 计数 6→7

### 文本提取修复
- `app/utils/docx_exporter._extract_original_text()`: 增加从 annotated_md 解析段落的 fallback，确保 .docx 导出包含原文内容

## v0.6.0 (2026-06-13) — Phase 4: 深度增强

### A3 推理链分解
- **A3 prompt 增强**: 思辨型/社科型/历史型论证新增推理链分解指导（Premise→Conclusion→Missing Step→Why Critical）
- 两个详细示例（自由贸易论证、工业革命煤炭论证）
- 按竞赛类型区分：科研/数模不需要推理链分解，金融/商科重点检查假设→预测→结论的逻辑

### 学生水平自适应
- **新增 `app/utils/student_level.py`**: 启发式估算学生水平（入门/进阶/高级）
- 基于三个维度评分：字数、平均句长、词汇多样性（TTR，已按 Zipf 定律调整阈值）
- 极短文本（<100 词）自动归类为入门
- 不同水平生成不同的 Agent 反馈指令（引导鼓励/诊断方向/深度挑战）
- 集成到 Orchestrator：所有 4 个 Agent（A2/A3/A4/A5）收到学生水平上下文
- 学生水平信息记录到 ReviewReport.meta

### 知识卡自动更新建议
- **新增 `GET /api/v1/feedback/suggestions`**: 基于反馈数据自动检测高频被纠正模式
- 按 Agent + item_type 聚合，可配置阈值（默认 3 次）
- 自动建议对应的知识卡类型（fatal_defect/pattern/pitfall/benchmark/scoring_anchor）
- Gradio 教师审核 Tab 新增「知识卡更新建议」面板（可调阈值 + 建议表格展示）

### 专家经验扩展覆盖全部竞赛类型
- 新增 4 个专家经验文件：`CTB_social_science.md`、`NHD_history.md`、`SIC_finance.md`、`FBLA_business_case.md`
- 每个文件 8 条洞察（2 pattern + 2 pitfall + 2 signal + 2 strategy），与现有 ISEF/John_Locke/HiMCM 格式完全兼容
- 现覆盖全部 7 种竞赛类型：research、discursive、math_modeling、social_science、history、finance、business_case

## v0.5.0 (2026-06-13) — Phase 3: 反馈闭环

### 老师反馈数据模型
- **TeacherFeedback ORM**: `teacher_feedback` 表，支持逐条记录老师对 AI 评审意见的审核动作
- 字段: review_id, teacher_id, agent_name, item_path, item_type, ai_content, ai_substitutability, teacher_action (CONFIRM/OVERRIDE/REFINE), teacher_note

### 反馈 API
- **`POST /api/v1/feedback`**: 提交老师审核反馈（批量），支持逐条确认/修正/细化
- **`GET /api/v1/reviews/{id}/feedback`**: 查询某次评审的历史反馈记录
- **`GET /api/v1/feedback/stats`**: 置信度校准统计 — 按 Agent 和置信度标签维度统计 AI 信心 vs 老师确认率

### Gradio 教师审核界面
- **新 Tab "教师审核"**: 加载评审 → 逐条审核 → 提交反馈
  - 自动提取 5 个 Agent 的全部审核项（section_issues, logic_issues, claims, fallacies, rewrites, suggestions, citation/originality issues）
  - 审核项表格展示：Agent/类型/置信度/AI判断
  - 全部确认快速通道
  - 逐条覆写支持（JSON 格式指定 index + action + note）
  - 反馈闭环统计看板（按 Agent、按置信度标签的确认率）

## v0.4.0 (2026-06-13) — Phase 2: 置信度标签 + 标注增强

### 置信度标签系统
- **Agent prompt 扩展**: A2/A3/A4/A5 输出格式新增 `substitutability` 和 `confidence_rationale` 字段
- **规则引擎 `confidence_engine.py`**: 按 Agent 类型 + 条目特征自动分配置信度标签（不依赖 LLM 自评）
  - A4 拼写/语法/标点修正 → FULL；风格/表达建议 → REVIEW
  - A3 结构性谬误（begging_question/false_dichotomy）→ FULL；语义性谬误 → REVIEW
  - A2 高严重度章节缺失 → FULL；逻辑衔接 → REVIEW
  - A5 引用匹配 → FULL；原创性评估 → ESCALATE
- **`annotation_builder.py` 分级显示**: 每条标注前显示置信度标记（🔴=ESCALATE / ⚡=REVIEW / 无标记=FULL）
- **Orchestrator 集成**: Round 1/2 采集 Agent 结果后自动运行置信度规则引擎

### 隐私声明完善
- README.md 和 Gradio UI 隐私声明扩展：明确列出所有 LLM 提供商、数据存储位置、同步传输说明

## v0.3.0 (2026-06-12)

### 竞赛类型公平性重构
- **校准引擎按类型切换特征集**: 科研型 21 特征，思辨/金融/商科 15 特征（移除 has_p_value/has_effect_size 等科研专用项）
- **fatal_defect 按类型分离**: John Locke 不再建议"缺少 p 值为致命缺陷"
- **Agent 权重按竞赛可配置**: John Locke 结构占 30%，ISEF 证据占 30%
- **配置映射按类型分离**: 8 种竞赛类型独立 FEATURE_TO_CONFIG_MAP
- **A4 加载 style_guides**: 不同竞赛使用不同语言标准（科研被动语态上限 40% vs 思辨 30%）
- **A3 type_hints JSON 化**: 硬编码 → `configs/competition_type_hints.json`

### 安全加固
- **Bearer Token 认证**: `API_TOKEN` 环境变量，不设则跳过
- **文件上传限制**: 50MB 上限 + 服务端类型白名单 (.txt/.md/.pdf/.docx)

### 技术债务
- **Gradio subprocess → 直接调用**: 校准引擎不再通过 CLI 子进程，改用 `run_calibration()` 直接调用
- **requirements-lock.txt**: 124 个依赖的精确版本锁文件

## v0.2.0 (2026-06-09)

### 教练型审稿反馈
- A2/A3 Prompt 升级为"教练型"风格：缺→问→改三步法
- 新增原文标注输出模式（逐段批注 Markdown + HTML）
- `thesis_coaching` → `main_argument_coaching`（科研=hypothesis 验证，思辨=thesis 稳定性）
- `counterargument_analysis` → `validation_point`（8 种类型语义切换）

### 赛事管理
- Gradio "赛事管理" Tab：可视化添加/编辑/删除竞赛
- 竞赛名称别名归一化引擎（同事用别名/缩写/中文也能正确汇总）
- 校准引擎支持 PDF/DOCX 上传

### 代码质量（Claude Code 评估改进）
- 6 项修复：score_key 类属性、路径遍历防护、缓存失效、Agent 导出
- 177 个单元测试 + CI/CD

## v0.1.0 (2026-05)

### 初始版本
- 5-Agent 并行审稿流水线（RubricParser + StructureLogic + ArgumentEvidence + LanguageStyle + AcademicIntegrity）
- 校准引擎：Cohen's d 效应量 + 特征提取 + 配置优化建议
- 团队协作：sync 上报 + 管理看板
- Gradio 图形界面
- 3 种 LLM Provider（DeepSeek/OpenAI/Gemini）
