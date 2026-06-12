# AcademicReviewer 项目评估报告

> **评估日期**: 2026-06-13（第三次评估 — v0.6.0 人机协作完整实现）
> **上次评估**: 2026-06-12（8.0/10，v0.3.0 公平性重构）
> **代码规模**: ~7,200 行 Python + 267 行 Prompt 模板 + 30 个 JSON 配置文件 + 24 个文档文件
> **技术栈**: Python 3.10+ / FastAPI / Gradio / SQLite / ChromaDB / httpx
> **评估方法**: 完整阅读全部源代码 + 新增文件逐行审查 + 测试套件验证 + 改进计划执行对照

---

## 综合评分: 8.4/10（更新于 2026-06-13 v0.6.0 人机协作完成）

| 维度 | 评分 | 等级 | 变化（自 6/12） |
|------|------|------|------|
| 架构设计 | 9.0/10 | 优秀 — 知识卡+置信度+学生水平全管线贯通 | ↑ 0.5 |
| 代码质量 | 8.5/10 | 优秀 — 置信度引擎规则驱动、知识卡分层清晰 | ↑ 0.5 |
| 安全性 & 鲁棒性 | 7.5/10 | 良好 — 隐私声明已完善，反馈端点受认证保护 | ↑ 0.5 |
| 测试 & 质量保障 | 7.5/10 | 合格 — 193/204 通过（py3.14 兼容依旧，新功能测试待补充） | — |
| 文档质量 | 9.5/10 | 卓越 — 面向多角色的完整文档体系 | ↑ 0.5 |
| 可维护性 & 可扩展性 | 9.0/10 | 优秀 — 知识卡系统零侵入已有架构 | ↑ 0.5 |
| **竞赛类型公平性** | **8.0/10** | 良好 — 7 种类型全部有专家经验覆盖 | **↑ 0.5** |
| 依赖 & 技术债务 | 8.0/10 | 良好 — 反馈闭环+自动建议已落地 | ↑ 0.5 |

### v0.4.0–v0.6.0 变更概述（2026-06-13）

Trae AI 基于 HUMAN_AGENT_COLLABORATION.md 执行了 Phase 1-4 全部实施，核心变化：

**v0.4.0 — 置信度标签系统（Phase 2）**:
- 新增 `app/utils/confidence_engine.py`（188 行）：规则引擎按 Agent 类型 + 条目特征自动分配置信度（FULL/REVIEW/ESCALATE），不依赖 LLM 自评
- L3a/L3b 子分层落地：结构性检测→FULL（拼写/语法/高严重度章节缺失/引用匹配），语义性判断→REVIEW（论证强度/逻辑连贯性），领域深度→ESCALATE（原创性/哲学立场）
- `annotation_builder.py` 扩展：置信度分级显示（🔴=ESCALATE / ⚡=REVIEW / 无标记=FULL）
- 隐私声明完善：README + Gradio UI

**v0.5.0 — 反馈闭环（Phase 3）**:
- 新增 `TeacherFeedback` ORM 模型（`app/models/submission.py`）
- 新增 `POST /api/v1/feedback`：批量提交老师审核反馈
- 新增 `GET /api/v1/reviews/{id}/feedback`：查询历史反馈
- 新增 `GET /api/v1/feedback/stats`：置信度校准统计（按 Agent/置信度标签维度）
- 新增 `GET /api/v1/feedback/suggestions`：自动检测高频被纠正模式，建议更新知识卡
- Gradio 新增「教师审核」Tab：逐条审核+全部确认+批次覆写+统计看板

**v0.6.0 — 深度增强（Phase 4）**:
- A3 prompt 增强推理链分解指导（Premise→Conclusion→Missing Step→Why Critical），按竞赛类型区分适用性
- 新增 `app/utils/student_level.py`（168 行）：启发式估算学生水平（入门/进阶/高级），LLM-Free，基于字数+句长+TTR三维评分，考虑 Zipf 定律
- Orchestrator 全管线注入：知识卡 → A2/A3 + 学生水平 → A2/A3/A4/A5 + 置信度标签采集
- 新增 4 个专家经验文件：CTB、NHD、SIC、FBLA，覆盖全部 7 种竞赛类型
- `knowledge_cards.py` 含 `render_knowledge_cards_for_prompt()`：知识卡自动渲染为 prompt 文本块

---

## 1. 架构设计 (8.0/10)

### 优势

**1.1 无框架依赖的简洁 Agent 编排 (9/10)**
- 不依赖 LangChain、LlamaIndex 等重型框架，自行实现的 Orchestrator 仅 ~260 行
- Agent 为纯 async 函数，状态清晰、可调试
- 这是一个清醒的架构决策：对于 5 个固定 Agent 的流水线，LangChain 的灵活性反而是负担

**1.2 适配器模式的 LLM 抽象 (8/10)**
- `LLMAdapter` ABC + `LLMFactory` 注册表模式设计干净
- 每个适配器自注册（模块底部 `LLMFactory.register("deepseek", DeepSeekAdapter)`）
- 添加新模型只需新建一个 ~60 行的适配器类
- 四个适配器（DeepSeek/OpenAI/Gemini/GLM）仅 ~250 行总计

**1.3 两轮并行流水线 (8/10)**
- Round 1: A1 (Rubric) + A2 (Structure) + A3 (Argument) 并行 → Round 2: A4 (Language) + A5 (Integrity) 并行
- 这个设计合理：A4/A5 可能需要 A1/A2/A3 的结果（如 A5 需要 citation check 结果）
- `asyncio.gather(*tasks, return_exceptions=True)` 确保单个 Agent 失败不会阻塞整个流水线

**1.4 校准引擎的 LLM-Free 设计 (9/10)**
- 特征提取、Cohen's d 计算、配置差异生成全部使用纯数学/正则
- 仅教师文档解析的 Mode 1/2 调用 LLM，且特征映射仍使用本地关键词匹配防止幻觉
- 这是一个精心设计的架构决策，确保了校准结果的可复现性和计算效率

**1.5 配置驱动的竞赛可扩展性 (9/10) ↑1**
- 添加竞赛零代码改动；v0.6.0 专家经验文件自动匹配 + 知识卡自动分层进一步强化了配置驱动

**1.6 人机协作管线的优雅集成 (9/10) 🆕**
- 三条新增管线独立注入、互不耦合：知识卡→Agent prompt（`_load_knowledge_cards_for_competition()`）、学生水平→Agent prompt（`estimate_student_level()`）、置信度标签→后处理（`apply_confidence_labels()`）
- 关键架构决策：`confidence_engine.py` 选择规则引擎而非 LLM 自评置信度——避免了"AI 判断 AI 判断可靠性"的循环依赖
- 知识卡通过 `render_knowledge_cards_for_prompt()` 渲染为纯文本注入，Agent 零改动兼容

### 需改进

**1.7 Agent 识别已改善 ✅（原依赖字符串比较）**
- 原先 `orchestrator.py` 中通过 `r.get("agent", "")` 字符串匹配来识别 Agent 返回结果
- **已修复**: 在 `BaseAgent` 添加 `score_key` 类属性，每个 Agent 子类声明自己的评分键名
- `_compute_total_score()` 现在通过 Agent 类属性而非硬编码字符串来提取评分

**1.8 两轮并行是硬编码的 (低)**
- 如果需要 3 轮或更复杂的依赖关系（如 A4 需要 A2 的某些输出），无法配置
- 对于当前 5-Agent 规模可以接受，但值得文档化这个限制

**1.8 配置缓存已改善 ✅（原全局单例无失效机制）**
- **已修复**: 添加 `clear_config_cache()` 函数，在测试或热加载场景下可重置缓存
- 全局缓存仍然存在（适合单机使用），但有了显式的失效入口

---

## 2. 代码质量 (8.5/10) ↑0.5

### v0.4.0–v0.6.0 新增代码质量评估

**`confidence_engine.py` (188 行) — 9/10**
- 规则驱动而非 LLM 自评——这是正确的架构选择。`_AGENT_FIELD_DEFAULTS` 表 + 三个细化映射（`_A4_REWRITE_ISSUE_MAP`/`_A4_SUGGESTION_TYPE_MAP`/`_A3_FALLACY_TYPE_MAP`）覆盖了 L3a/L3b 的分层逻辑
- `apply_confidence_labels()` shallow copy 避免修改调用者数据——细节正确
- 结构性谬误→FULL、语义性谬误→REVIEW——分类准确

**`student_level.py` (168 行) — 8/10**
- 启发式规则，零 LLM 调用。三维评分（字数/句长/TTR），Zipf 定律 aware
- 极短文本（<100词）强制 beginner——防守型处理
- 缺少对非英语文本的适配（中文的 TTR 计算方式不同）——这是一个已知局限

**`knowledge_cards.py` (137 行) — 9/10**
- `build_knowledge_cards()` 严格遵循设计 spec，annotation_type → layer 映射清晰
- `render_knowledge_cards_for_prompt()` 将三层知识卡渲染为结构化 markdown 文本——Agent 无需理解新数据格式
- `_format_annotation()` 按类型分配 emoji 前缀（🔴/📊/📋/📌/⚠️/📡）——prompt 中的视觉结构化

**Orchestrator 增量 (~30 行) — 8/10**
- 知识卡加载、学生水平估算、置信度采集三条管线独立注入，无交叉依赖
- lazy import 保持项目风格一致（函数内 import）
- 小瑕疵：`_load_knowledge_cards_for_competition()` 中 expert_insights dir 路径硬编码

### 修复更新

**2.5 subprocess 调用 — 已修复 ✅ (v0.3.0)**
**2.7 type_hints 硬编码 — 已修复 ✅ (v0.3.0)**

### 仍需改进

**2.4 循环导入 (中)** — 不变
**2.6 类型提示不完整 (低)** — 不变
**2.8 A4 动态 Style Guide 注入 (低) 🆕**: Prompt 中风格指导为硬编码文本，未引用 JSON style_guide 中的具体数值参数。如果 style_guide JSON 修改了，prompt 不会自动更新

---

## 3. 竞赛类型公平性分析 (8.0/10) ↑0.5

> **v0.6.0 更新**: 全部 7 种竞赛类型（research, discursive, math_modeling, social_science, history, finance, business_case）现已有专家经验文件覆盖。`confidence_engine.py` 的 L3a/L3b 分层 + A3 推理链分解（科研/数模 skip，思辨/社科/历史 full 模式，金融/商科 hypothesis→prediction 模式）进一步减少了跨类型偏差。

### 3.1 当前适配度（v0.6.0 更新）

| 适配度 | 赛事 | 新增优势 |
|--------|------|---------|
| ⭐⭐⭐⭐⭐ | **ISEF / STS / 丘成桐** | 专家经验已覆盖，research/advanced 全特征 |
| ⭐⭐⭐⭐ | **HiMCM** | 专家经验已覆盖（HiMCM_Mode2），学生水平自适应可识别公式密度 |
| ⭐⭐⭐⭐ | **CTB / NHD** | 🆕 专家经验新增（CTB_social_science / NHD_history），推理链→full |
| ⭐⭐⭐⭐ | **John Locke / Marshall** | 专家经验已覆盖（John_Locke_李老师），推理链→full，L3a/L3b 分层 |
| ⭐⭐⭐ | **SIC / WGHS** | 🆕 专家经验新增（SIC_finance），推理链→hypothesis模式 |
| ⭐⭐⭐ | **FBLA** | 🆕 专家经验新增（FBLA_business_case），推理链→hypothesis模式 |

### 3.2 新增偏差防护（v0.4.0–v0.6.0）

**L3a/L3b 分层 — 防止 AI 过度自信 🆕**
`confidence_engine.py` 明确区分结构性检测（FULL）和语义判断（REVIEW），确保非科研类型的论证质量判断不会错误地标为"AI可替代"。思辨型 counterargument 质量→REVIEW，结构性谬误（begging_question/false_dichotomy）→FULL。

**专家经验全覆盖 — 消除"盲飞" 🆕**
v0.6.0 新增 4 个文件，7 种竞赛类型全部有至少 8 条专家洞察 + 若干策略建议。这确保 AI 在评审任何类型时都有领域知识卡可供对照。

### 3.2 五个层面的偏差分析（v0.3.0 更新）

#### 3.2.1 校准引擎特征集 — 已修复 ✅

原问题：21 个全局特征中 8 个纯科研专用（has_p_value/has_effect_size/has_control_group/has_sample_size），对非科研竞赛永远为 0.0。

**v0.3.0 修复**: `FEATURES_BY_TYPE` 为 8 种类型定义了独立特征集，`feature_names(competition_type)` 动态返回。discursive/history/finance/business_case 均为 13-15 特征（移除了科研 4 项 + limitations_section_present 按需保留）。

**残留风险**: 低。特征集现在按类型正确选择了，实现完整。

#### 3.2.2 Agent 权重 — 已修复 ✅

原问题：所有竞赛一刀切 `AGENT_WEIGHTS`。

**v0.3.0 修复**: `competition_registry.json` 中每场比赛有独立的 `agent_weights`。示例：John Locke Structure=30%/Argument=25%（偏结构），ISEF Structure=15%/Argument=30%（偏证据），FBLA Structure=30%/Language=20%（偏框架+说服力）。`_compute_total_score()` 按 `weight_sum` 归一化防止偏移。

**残留风险**: 低。当前权重基于理论分析设定（结构重要性 vs 证据重要性 vs 语言重要性），需要真实使用数据验证。校准引擎可以在积累足够评审记录后通过 `agent_weights_override` 机制自动建议修正。

#### 3.2.3 A4 语言风格审查 — 已修复 ✅

原问题：`a4_language_style.txt` 对所有类型用同样的审查标准。

**v0.3.0 修复**: `orchestrator._load_style_guide()` 根据 `competition_registry.json` 中的 `style_template` 加载对应 JSON（如 discursive.json 设定 max_passive_ratio=0.30/preferred_voice="active, conversational-academic hybrid"），传入 A4 Agent。Prompt 中新增了 6 种类型的风格审查原则（科研被动 40%上限、思辨主动优先 30%上限、商科主动有说服力、金融精确数据叙述等）。

**残留风险**: 低-中。Prompt 中的类型指导是硬编码文本，未直接引用 JSON style_guide 中的具体数值（如 max_passive_ratio）。如果 style_guide JSON 的参数调整了，prompt 文本不会自动更新。建议：在 prompt 构建时动态注入 style_guide 中的数值参数。

#### 3.2.4 校准引擎配置映射 — 已修复 ✅

原问题：`FEATURE_TO_CONFIG_MAP` 全局统一。

**v0.3.0 修复**: `FEATURE_TO_CONFIG_MAP_BY_TYPE` 含全部 8 种类型的独立映射。discursive 类型下 `logical_marker_density` → `logic_checks.min_logical_markers_per_1000w`，`hook_sentence_present` → `structure_requirements.requires_hook`。不包含 has_p_value/has_effect_size/has_control_group 等科研专用映射。

**v0.3.0 修复（fatal_defect）**: `BINARY_FEATURES_BY_TYPE` 含全部 8 种类型的独立白名单。`generate_fatal_defect_updates(competition_type)` 按类型过滤 binary feature，确保对 John Locke 不检查 has_p_value/has_control_group。

**残留风险**: 低。完整实现。

#### 3.2.5 Prompt 层面的类型感知 — 已增强 ✅

原为系统做得最好的部分（A2/A3 的 v1.7 双层架构）。

**v0.3.0 增强**: A3 type_hints 从硬编码迁移到 `competition_type_hints.json`，每种类型有独立的 `checks`/`skip`/`hint`。A2 的结构检查继续从 `structure_schemas/*.json` 动态读取 `required_sections`/`expected_ratio`/`logic_checks`。

**残留风险**: 低。Prompt 层的类型感知是最完善的。

### 3.3 总结：偏差已基本修正，框架层面的类型感知覆盖完整

> ~~系统从架构到 Prompt 到校准引擎都**围绕传统学术研究论文的形态设计**。~~
>
> **v0.3.0 后**: 系统从 Prompt（type_hints JSON）、评分权重（agent_weights per competition）、特征提取（FEATURES_BY_TYPE）、配置映射（FEATURE_TO_CONFIG_MAP_BY_TYPE）、fatal_defect 检测（BINARY_FEATURES_BY_TYPE）、风格审查（style_guides JSON）六个层面全部实现了按竞赛类型切换。研究型倾斜问题在**架构层面**已解决。
>
> 剩余工作不在架构层面，而在于**内容质量**——LLM 是否能在各类型中做出专业级判断（见 [HUMAN_AGENT_COLLABORATION.md](HUMAN_AGENT_COLLABORATION.md)）。

---

## 4. 安全性 & 鲁棒性 (7.5/10) ↑0.5

### 风险清单（v0.3.0 更新）

**4.1 API 认证 — 已修复 ✅**
- **已修复**: Bearer Token 认证已实现。`_verify_api_token()` 检查 `Authorization: Bearer <token>`，与 `.env` 中 `API_TOKEN` 比对。`API_TOKEN` 未设置时向后兼容（跳过认证）。
- 所有 `/api/v1/*` 敏感端点已添加 `Depends(_verify_api_token)`。

**4.2 文件上传限制 — 已修复 ✅**
- **已修复**: 服务端验证 `_validate_file(suffix, size)`：50MB 上限 + `.txt/.md/.pdf/.docx` 白名单。`await file.read(_MAX_FILE_SIZE + 1)` 避免无限读取。

**4.3 学生数据隐私 (高) 🟠 — 已改善 ✅**
- **v0.4.0 已添加**: README + Gradio UI 隐私声明扩展，明确列出所有 LLM 提供商、数据存储位置、同步传输说明

**4.4 同步数据暴露 (中) 🟡 — 未变**
- 同步仍使用明文 HTTP，需考虑 HTTPS/加密

**4.5 无速率限制 (中) 🟡 — 未变**
- 无请求频率限制

**4.6 路径遍历 — 已修复 ✅（v0.2.0）**
**4.7 依赖供应链 — 已改进 🟡**
- `requirements-lock.txt` 已添加，精确版本锁定了 124 个依赖

**4.8 生产就绪度评估**
- 当前定位仍为内网工具/个人辅助工具。如需公网部署仍需：HTTPS、速率限制、更完整的数据隐私声明。

---

## 5. 测试 & 质量保障 (7.5/10)

> **2026-06-13 更新**: 从 177 个测试增至 **204 个**（193 pass / 11 fail）。新增测试覆盖校准引擎特征集、competition_type_hints 等。11 个失败仍是 pytest-asyncio + Python 3.14 兼容性问题，非代码逻辑缺陷。

### 改进前后对比

| 指标 | v0.2.0 | v0.6.0 |
|------|--------|--------|
| 单元测试文件数 | 1 (e2e only) | **13+** |
| 测试总数 | 0 (e2e 需 API Key) | **204** |
| 测试通过率 | N/A | **193/204 (94.6%)** |
| Pytest 配置 | 无 | `pytest.ini` 含 markers + asyncio |
| Mock/Fixture 基础设施 | 无 | `tests/conftest.py` 含 `MockLLMAdapter` + 样例数据 |
| CI/CD | 无 | `.github/workflows/test.yml`（多版本矩阵） |

### 测试覆盖缺口 🆕

v0.4.0–v0.6.0 新增的以下模块**缺少专门的单元测试**：
- `confidence_engine.py` (188 行) — 无测试
- `student_level.py` (168 行) — 无测试
- `knowledge_cards.py` (137 行) — 无测试
- `POST /api/v1/feedback` 等 4 个新端点 — 无集成测试

**建议**: 参照已有测试模式（纯函数 → 零依赖单测；Agent → MockLLMAdapter 集成测试），为这三个模块补充测试。`confidence_engine.py` 的规则表是纯函数，测试成本极低。

---

## 6. 文档质量 (8.5/10)

### 优势

**6.1 AI_HANDOFF.md — 面向 AI 助手的专业接手指南 (10/10)**
- 这是一份极其详尽的代码库文档（~300 行）
- 模块地图、API 参考、数据流图、编码规范、常见陷阱、"如何添加"指南——俱全
- 中英双语策略明智：源码注释用中文（面向国内开发者），AI_HANDOFF 用英文（面向 AI 工具）
- 每个文件的功能说明清晰，职责明确

**6.2 README.md (8/10)**
- 中文，结构清晰：功能概览 → 安装 → 配置 → 团队协作 → 项目结构
- 团队协作的架构图（ASCII 图）直观
- 缺少：Badge、Contributing 指南、Changelog

**6.3 架构设计文档 (8/10)**
- `docs/architecture/` 下有 8 个文件，覆盖 v1.0 到 v1.7 的架构演进
- 包含决策备忘（v1.4 7vs5Agent 对比），这对理解设计权衡非常有价值
- 建议：将最新版本标注为 `CURRENT`，避免混淆

**6.4 代码注释 (6/10)**
- 模块级 docstring 在复杂文件中有
- 函数级 docstring 稀疏——许多公开函数缺少文档
- 关键决策点（如 lazy import、fire-and-forget sync）有注释说明意图

### 需补充

- 缺少 API 文档——FastAPI 自动生成的 Swagger UI 可用，但未定制
- 没有 Changelog
- 没有 Contributing 指南（如何设置开发环境、运行测试、提 PR）

---

## 7. 可维护性 & 可扩展性 (7.5/10)

### 优势

**7.1 清晰的新功能添加路径 (9/10)**
- AI_HANDOFF.md §10 明确给出添加 Agent、LLM Provider、Competition 的分步指南
- 竞赛管理有 Gradio GUI 图形界面（无需手动编辑 JSON）
- LLM 适配器自注册机制确保添加新 Provider 零耦合

**7.2 配置备份机制 (8/10)**
- 赛事注册修改自动备份到 `.json.bak`
- 配置同步覆盖前备份到 `data/configs_backup_TIMESTAMP/`
- 这是一个用心设计的细节

**7.3 降级策略 (7/10)**
- 未知竞赛 fallback 到 `research` 类型默认配置
- ChromaDB 不可用时跳过原创性检查
- Rubric 文件缺失时 fallback 到 `isef_2026.json`

### 技术债务

| 债务项 | 严重度 | 说明 | 状态 |
|--------|--------|------|------|
| 竞赛类型偏差 | ~~高~~ | ~~校准引擎、权重、评分机制研究型倾斜~~ | ✅ 已修复 (v0.3.0) |
| 无数据库迁移 | 中 | `Base.metadata.create_all()` 每次启动执行 | 未修复 |
| 无配置热加载 | 低 | 修改 `.env` 或 JSON 配置需重启服务 | 未修复 |
| 评分键名硬编码 | 低 | Agent 输出字段名分散在多处 | ✅ 已修复 (v0.2.0) |
| requirements.txt 宽松版本 | 低 | `>=` 约束可能导致依赖升级引入 breaking change | ✅ 已修复 (lock 文件) |
| 潜在循环导入 | 低 | 当前通过 lazy import 规避 | 未修复 |
| 缓存无失效机制 | 低 | 全局缓存单例 | ✅ 已修复 (v0.2.0 clear_config_cache) |
| 路径遍历风险 | 低 | competition 名直接构建文件路径 | ✅ 已修复 (v0.2.0) |
| type_hints 硬编码 | 低 | A3 的 8 种类型提示写在代码中 | ✅ 已修复 (v0.3.0 JSON 化) |
| Gradio subprocess 调用 | 低 | 校准功能通过子进程 | ✅ 已修复 (v0.3.0) |
| pytest-asyncio 兼容 | 新 | Python 3.14 下 11 个 async 测试失败 | 🆕 待修复 |

---

## 8. 依赖分析 & 性能 (7.0/10)

### 依赖评估

```
fastapi + uvicorn     — 合理选择，轻量 Web 框架
sqlalchemy 2.0        — 成熟的 ORM
gradio 5.0            — 快速搭建 ML 演示界面，适合目标用户
chromadb 0.5          — 向量检索，但 transitive deps 重（onnxruntime ~200MB）
httpx                 — 统一 HTTP 客户端（LLM API + 内部通信）
pydantic-settings     — 环境变量管理
```

**潜在冗余**: `openai`、`google-generativeai`、`zhipuai` 三个包在 `requirements.txt` 中列出，但实际 LLM 调用全部走 `httpx`（AI_HANDOFF.md 也指出这一点）。这些包可能不是必需的。

**ChromaDB 体积**: 含 `onnxruntime`、`numpy`、`tokenizers` 等依赖，venv 约 400MB。对于本地部署可接受，但值得文档化说明。

### 性能特征

- Agent 调用耗时主要取决于 LLM API 响应时间（秒级）
- 两轮并行将总时间从 5×串行降低到 ~2×串行（Round 1: max(A1, A2, A3) + Round 2: max(A4, A5)）
- 校准引擎纯计算，本地执行毫秒级
- SQLite 在单机场景下性能充足
- ChromaDB HNSW 索引搜索为亚秒级

---

## 9. 综合评估

### 项目亮点 ✨

1. **架构决策每步都清醒**: 拒绝 LangChain、校准 LLM-Free、置信度规则引擎而非 LLM 自评——每个技术选择有明确原因
2. **类型公平性从六层落地**: 特征集/权重/配置映射/fatal_defect/style_guides/type_hints 全部按类型切换（v0.3.0），加上 L3a/L3b 分层 + 推理链分解 + 专家经验全覆盖（v0.4.0–v0.6.0）
3. **人机协作全管线贯通**: 知识卡注入（Layer 1/2→Agent prompt）→ 学生水平自适应（3 级→4 个 Agent）→ 置信度分级（FULL/REVIEW/ESCALATE→标注报告）→ 反馈闭环（老师审核→API→统计看板→知识卡更新建议）
4. **零架构冲击的增量开发**: v0.3→v0.6 三次迭代，Orchestrator 仅增 ~30 行，三个新文件（confidence_engine/student_level/knowledge_cards）零耦合
5. **AI_HANDOFF.md 堪称标杆**: AI 辅助开发接手指南的范本
6. **专家经验文件化 + 知识卡自动分层**: 老师上传一份 .md → 自动检测模式 → 解析为 ExpertInsights → build_knowledge_cards() → 分层 → 渲染为 prompt → Agent 引用。流程全自动化
7. **原文标注机制**: `annotation_builder.py` 生成 Word 修订模式般逐段批注 + 置信度 emoji 标记

### 关键风险 ⚠️

1. **LLM 判断深度仍是天花板**: 架构已就绪，但 LLM 能否在思辨型/商科型/历史型做出专业级 L4 判断，取决于知识卡质量和 LLM 自身能力。v0.6.0 的推理链分解缓解了这个问题（AI 不做判断而是分解结构），但未解决
2. **安全在公网场景下仍有缺口**: 无速率限制、同步明文 HTTP
3. **新功能测试覆盖为零**: `confidence_engine.py`、`student_level.py`、`knowledge_cards.py`、4 个新 API 端点皆无专门测试
4. **pytest-asyncio 兼容**: Python 3.14 下 11 个 async 测试持续失败，从 v0.2.0 遗留至今

### v0.3.0 → v0.6.0 完成的改进

| 类别 | 已完成 |
|------|--------|
| 置信度标签 | `confidence_engine.py` 规则引擎 (FULL/REVIEW/ESCALATE)，L3a/L3b 分层 |
| 标注增强 | `annotation_builder.py` 分级显示（🔴/⚡/无标记） |
| 隐私声明 | README + Gradio UI（v0.4.0） |
| 反馈闭环 | TeacherFeedback ORM + 4 个 API + Gradio 教师审核 Tab |
| 知识卡系统 | `knowledge_cards.py` build + render + 3 个新 annotation 类型 |
| 学生水平自适应 | `student_level.py` 启发式估算 + 4 个 Agent 注入 |
| A3 推理链分解 | prompt 增强（Premise→Conclusion→Missing→Why），按类型区分 |
| 专家经验扩展 | 4 个新文件，7 种竞赛类型全覆盖 |
| 知识卡更新建议 | `GET /api/v1/feedback/suggestions` 自动检测高频被纠正模式 |

### 下一步改进优先级

| 优先级 | 项目 | 预估工作量 |
|--------|------|-----------|
| P0 | 为 `confidence_engine`/`student_level`/`knowledge_cards` 添加单元测试 | 1 天 |
| P0 | 修复 pytest-asyncio 兼容性（upgrade 插件或降级 Python） | 1-2 小时 |
| P1 | A4 prompt 动态注入 style_guide 参数（从 JSON 读数值而非硬编码） | 0.5 天 |
| P1 | 速率限制（FastAPI middleware） | 2 小时 |
| P2 | 数据库迁移方案（Alembic） | 0.5 天 |
| P2 | 学生水平中文适配（当前 TTR 计算基于英文分词） | 0.5 天 |
| P3 | 知识卡质量自动化检查（上线前验证必填项完整性） | 0.5 天 |
