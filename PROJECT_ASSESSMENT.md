# AcademicReviewer 项目评估报告

> **评估日期**: 2026-06-12（第二次评估）
> **上次评估**: 2026-06-10（7.4/10）
> **代码规模**: ~5,800 行 Python + 267 行 Prompt 模板 + 30 个 JSON 配置文件 + 20 个文档文件
> **技术栈**: Python 3.10+ / FastAPI / Gradio / SQLite / ChromaDB / httpx
> **评估方法**: 完整阅读全部源代码后多维度分析 + 改进计划执行验证

---

## 综合评分: 8.0/10（更新于 2026-06-12 v0.3.0 公平性重构后）

| 维度 | 评分 | 等级 | 变化（自 6/10） |
|------|------|------|------|
| 架构设计 | 8.5/10 | 优秀 — 类型感知已融入架构各层 | ↑ 0.5 |
| 代码质量 | 8.0/10 | 良好 — type_hints 配置化，style_guides 生效 | ↑ 0.5 |
| 安全性 & 鲁棒性 | 7.0/10 | 合格 — Bearer Token + 文件限制已落地 | ↑ 1.5 |
| 测试 & 质量保障 | 7.5/10 | 合格 — 166/177 通过（py3.14 兼容待修） | — |
| 文档质量 | 9.0/10 | 优秀 — CHANGELOG + CONTRIBUTING + .env.example | ↑ 0.5 |
| 可维护性 & 可扩展性 | 8.5/10 | 优秀 — 硬编码全部配置化，subprocess 已移除 | ↑ 1.0 |
| **竞赛类型公平性** | **7.5/10** | 良好 — 特征集/权重/映射/fatal_defect/style_guides 全部按类型切换 | **↑ 2.5** |
| 依赖 & 技术债务 | 7.5/10 | 良好 — lock 文件到位，Changelog 就绪 | ↑ 0.5 |

### v0.3.0 变更概述（2026-06-12）

Trae AI 基于 IMPROVEMENT_PLAN.md 执行了竞赛公平性重构，核心变化：

- **校准引擎按类型切换特征集**: 8 种类型独立 `FEATURES_BY_TYPE`（科研 21 特征，思辨/金融/商科 15 特征），`feature_names(competition_type)` 动态返回
- **fatal_defect 按类型分离**: 8 种类型独立 `BINARY_FEATURES_BY_TYPE`，John Locke 不再建议"缺少 p 值为致命缺陷"
- **Agent 权重按竞赛可配置**: `competition_registry.json` 中 10 场比赛各有 `agent_weights`，`_compute_total_score()` 以 `weight_sum` 归一化防止偏移
- **配置映射按类型分离**: `FEATURE_TO_CONFIG_MAP_BY_TYPE` 含全部 8 种类型，替换了全局统一映射
- **A4 加载 style_guides**: `_load_style_guide()` 加载各类型风格 JSON，传入 LanguageStyle Agent
- **A3 type_hints JSON 化**: 硬编码 → `competition_type_hints.json`，8 种类型各有独立 checks/skip/hint
- **安全加固**: Bearer Token 认证 + 50MB 文件限制 + 类型白名单
- **技术债务**: Gradio subprocess → 直接调用 + requirements-lock.txt + CHANGELOG/CONTRIBUTING

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

**1.5 配置驱动的竞赛可扩展性 (8/10)**
- `competition_registry.json` 作为单一真相源，映射竞赛名 → 类型 → 配置文件
- 添加竞赛：注册 JSON + 创建对应配置，无需修改代码
- 别名归一化引擎允许用户/同事使用不同称呼

### 需改进

**1.6 Agent 识别已改善 ✅（原依赖字符串比较）**
- 原先 `orchestrator.py` 中通过 `r.get("agent", "")` 字符串匹配来识别 Agent 返回结果
- **已修复**: 在 `BaseAgent` 添加 `score_key` 类属性，每个 Agent 子类声明自己的评分键名
- `_compute_total_score()` 现在通过 Agent 类属性而非硬编码字符串来提取评分

**1.7 两轮并行是硬编码的 (低)**
- 如果需要 3 轮或更复杂的依赖关系（如 A4 需要 A2 的某些输出），无法配置
- 对于当前 5-Agent 规模可以接受，但值得文档化这个限制

**1.8 配置缓存已改善 ✅（原全局单例无失效机制）**
- **已修复**: 添加 `clear_config_cache()` 函数，在测试或热加载场景下可重置缓存
- 全局缓存仍然存在（适合单机使用），但有了显式的失效入口

---

## 2. 代码质量 (7.5/10) ↑ 0.5

### 本次会话中修复的质量问题

**2.0 已完成的代码质量改进 (2026-06-10)**

| 文件 | 问题 | 修复 |
|------|------|------|
| `app/agents/base.py` | 无评分键名声明 | 新增 `score_key` 类属性 |
| `app/agents/*.py` (5 个 Agent) | 每个 Agent 未声明自己的评分键 | 各添加 `score_key` 属性 (rubric_score / structure_score / overall_score / language_score / integrity_score) |
| `app/orchestrator.py:202-228` | `_compute_total_score()` 硬编码评分键名映射 | 改用 Agent 类的 `score_key` 属性，消除魔法字符串 |
| `app/orchestrator.py:238-243` | `_load_rubric_config()` 存在路径遍历风险 | 添加 `Path(safe_name).name` 防护 |
| `app/config.py` | 全局缓存无失效机制 | 添加 `clear_config_cache()` 函数 |
| `app/agents/__init__.py` | 空白文件，无导出 | 显式导出所有 6 个类，包含 `__all__` |

### 优势

**2.1 良好的错误处理模式 (7/10)**
- API 层统一捕获异常，返回 400/500 响应
- Agent 错误通过 `return_exceptions=True` 收集到 `report.errors`，不中断流水线
- 数据库 session 使用 try/finally 确保关闭
- 临时文件使用 finally + `unlink(missing_ok=True)` 清理

**2.2 一致的编码风格 (8/10)**
- 全项目遵循命名规范（PascalCase 类、snake_case 函数、UPPER_SNAKE 常量）
- 导入顺序一致：标准库 → 第三方 → app.*
- 文件编码统一使用 `encoding="utf-8"`

**2.3 资源管理 (7/10)**
- 数据库连接池由 SQLAlchemy 管理
- ChromaDB 客户端懒初始化（`_get_chroma()`）
- 广告-hoc 的 sync 调用使用 `asyncio.ensure_future()` 而非阻塞

### 仍需改进

**2.4 循环导入处理方式需要文档化 (中)**
- `orchestrator.py` 在方法体内进行 lazy import（`from app.agents.rubric_parser import RubricParserAgent`）
- 这是实际可行的方案，但如果没有 AI_HANDOFF.md 的说明，新开发者会困惑

**2.5 Gradio UI 中的 subprocess 调用 (中)**
- `gradio_app.py:374` 校准功能通过 `subprocess.run` 调用 CLI 脚本
- 这绕过了 Python 导入机制，增加了调试难度
- 建议：直接调用 `run_calibration()` 函数

**2.6 类型提示不完整 (低)**
- 公共函数签名有类型提示，但私有方法、lambda、部分变量缺少

**2.7 ArgumentEvidence 中的 type_hints 硬编码 (中)**
- `app/agents/argument_evidence.py:23-31` 包含硬编码的 8 种类型提示字典
- 建议：移到 `configs/` JSON 配置文件中

---

## 3. 竞赛类型公平性分析 (7.5/10) ↑2.5

> **核心问题**: 当前系统能否在所有类型的报告提交类竞赛中有效地给出作品质量评审和反馈？是否存在过于倾向某类型赛事的情况？
> **v0.3.0 更新**: 特征集、权重、配置映射、fatal_defect 检测、style_guides、type_hints 全部完成按类型切换。

### 结论：研究型倾斜已基本修正，框架层面的类型感知已覆盖全部环节

### 3.1 当前对各竞赛类型的适配度（v0.3.0 更新）

按系统实际适配度排序：

| 适配度 | 赛事 | 原因 |
|--------|------|------|
| ⭐⭐⭐⭐⭐ | **ISEF / STS** | 系统天然以科研论文为设计模板，21 特征全部适用，权重偏证据 |
| ⭐⭐⭐⭐⭐ | **丘成桐** | 进阶科研，同 ISEF，research_advanced 特征集和 evidence config 覆盖 |
| ⭐⭐⭐⭐ | **HiMCM** | 数模论文结构化+量化，特征集保留 has_sample_size，权重偏证据(30%) |
| ⭐⭐⭐⭐ | **CTB / NHD** | 社科/历史，独立特征集（去科研专用项），权重适配（NHD 证据 30%） |
| ⭐⭐⭐⭐ | **John Locke / Marshall** | 思辨型，discursive 特征集（15 特征，highlight 逻辑/过渡/词汇多样性），权重偏结构(30%) |
| ⭐⭐⭐ | **SIC / WGHS** | 金融型，finance 特征集，权重分布均衡，style_guide=biz_finance |
| ⭐⭐⭐ | **FBLA** | 商科型，business_case 特征集，权重偏结构(30%)，type_hints 覆盖 SWOT/PEST/ROI |

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

## 4. 安全性 & 鲁棒性 (7.0/10) ↑1.5

### 风险清单（v0.3.0 更新）

**4.1 API 认证 — 已修复 ✅**
- **已修复**: Bearer Token 认证已实现。`_verify_api_token()` 检查 `Authorization: Bearer <token>`，与 `.env` 中 `API_TOKEN` 比对。`API_TOKEN` 未设置时向后兼容（跳过认证）。
- 所有 `/api/v1/*` 敏感端点已添加 `Depends(_verify_api_token)`。

**4.2 文件上传限制 — 已修复 ✅**
- **已修复**: 服务端验证 `_validate_file(suffix, size)`：50MB 上限 + `.txt/.md/.pdf/.docx` 白名单。`await file.read(_MAX_FILE_SIZE + 1)` 避免无限读取。

**4.3 学生数据隐私 (高) 🟠 — 未完全解决**
- 学生论文全文仍发送到第三方 LLM API（DeepSeek/OpenAI/Gemini/GLM）
- CHANGELOG 声称了隐私声明，但需验证 README 和 Gradio UI 是否实际添加
- **建议**: 在 Gradio 提交界面和 README 中添加明确的隐私提示

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

## 5. 测试 & 质量保障 (7.5/10) ↑ 4.0

> **2026-06-10 更新**: 本次会话中完成了全面的测试基础设施建设和单元测试覆盖。

### 改进前 vs 改进后

| 指标 | 之前 | 之后 |
|------|------|------|
| 单元测试文件数 | 1 (e2e only) | **13** |
| 测试总数 | 0 (e2e 需 API Key) | **177** |
| 测试通过率 | N/A | **177/177 ✅** |
| Pytest 配置 | 无 | `pytest.ini` 含 markers + asyncio |
| Mock/Fixture 基础设施 | 无 | `tests/conftest.py` 含 `MockLLMAdapter` + 样例数据 |
| CI/CD | 无 | `.github/workflows/test.yml`（多版本矩阵） |
| 运行时间 | N/A | ~62s（零 API 调用、零网络依赖） |

### 新增测试清单

#### 纯函数测试 (127 个) — 零网络依赖、零 LLM 调用

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `tests/test_utils/test_citation_checker.py` | 20 | 引文提取 (APA/MLA/Chicago/numeric)、参考文献行分割、匹配/未匹配检测、CitationReport 属性、边界条件 |
| `tests/test_calibration/test_cohens_d.py` | 22 | Cohen's d 计算（大效应/无效应/负效应/零方差/小样本）、效应分类（critical/major/minor/none）、compute_effect_sizes 含排序和置信度、cross_validate 含一致/不一致/无外部样本 |
| `tests/test_calibration/test_feature_extractor.py` | 33 | 句子分割与短句过滤、分词与小写、全部 21 个特征维度（citation_density / passive_voice_ratio / TTR / logical_marker_density / transition_frequency / section_coverage / has_p_value / has_effect_size / has_control_group / has_sample_size / evidence_diversity / gap_statement / limitations / future_work / hook_sentence / claim_count / avg_sentence_length / avg_paragraph_length）、features_to_dict 四舍五入、feature_names 21 元素验证 |
| `tests/test_calibration/test_diff_generator.py` | 18 | `_get_nested_value` 简单/嵌套/缺失、rule updates 生成 (critical 触发/none 跳过/unknown 跳过/新增)、fatal defect (binary+negative+critical 触发/非 binary 跳过/正向信号跳过/minor 跳过/低 gap 跳过)、config diff (新增键/删除键/值变更/嵌套变更/列表变更/完全一致) |
| `tests/test_config.py` | 15 | `normalize_competition_name` (精确匹配/大小写/英文别名/中文别名/未知穿透/空字符串)、`get_competition_list` (数量/必要字段/主要赛事)、缓存失效 |
| `tests/test_utils/test_doc_parser.py` | 10 | TXT/MD 解析、不支持格式报错、元数据文件名和格式、ParsedDocument 段落分割与修剪、文本截断 |
| `tests/test_llm/test_base.py` | 16 | JSON 解析 (干净/```json```/```/文本包围/嵌套花括号/无效/不完整/数组/尾部逗号/单引号/中文)、chat_json 端到端、Factory 注册+创建+未知 provider+隔离 |

#### Mock 集成测试 (50 个) — 使用 MockLLMAdapter

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `tests/test_agents/test_base.py` | 12 | Prompt 加载 (存在/缺失)、_build_system_prompt、_build_user_message (kwargs JSON/空)、run (成功/元数据/调用记录/temperature)、LLM 错误处理、_load_json (绝对路径/相对路径/不存在文件) |
| `tests/test_agents/test_structure_logic.py` | 4 | 用户消息含文档文本/竞赛类型/结构 schema、mock run 全流程 |
| `tests/test_agents/test_argument_evidence.py` | 7 | 含 research/discursive/math_modeling/business_case/unknown 五种类型的提示词检查、mock run 验证 overall_score |
| `tests/test_agents/test_academic_integrity.py` | 5 | 用户消息含引文数据/相似度报告、跳过原创性检查、ChromaDB 空时优雅降级 |
| `tests/test_agents/test_language_style.py` | 4 | 用户消息含/不含风格指南、mock run 验证 rewrites + suggestions |
| `tests/test_agents/test_rubric_parser.py` | 3 | 用户消息含评分标准文本、mock run 验证 dimensions + rubric_score |

### 测试基础设施

- **`pytest.ini`**: 配置了 testpaths、pythonpath、asyncio_mode=auto、markers (unit/integration/slow)
- **`tests/conftest.py`**: 共享 Fixtures — `MockLLMAdapter`（可控响应、调用记录跟踪）、`sample_isef_text`、`sample_jl_text`、`sample_refs_section`、`sample_winners_features` (3 篇获奖)、`sample_losers_features` (3 篇失败)、`feature_name_list`
- **`.github/workflows/test.yml`**: Python 3.10/3.11/3.12 矩阵，push + PR 触发

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

1. **架构决策清醒**: 拒绝 LangChain、校准引擎 LLM-Free、无框架依赖——每个技术选择都有明确原因
2. **类型公平性已落地**: 从 Prompt 到权重到校准引擎到 style_guides，六层全部按类型切换——这是 v0.3.0 的最重要成就
3. **AI_HANDOFF.md 堪称典范**: 这是 AI 辅助开发场景下接手指南的标杆级文档
4. **配置驱动的可扩展性**: 添加竞赛类型无需修改代码，配合 GUI 管理界面用户体验良好
5. **校准引擎思路精巧**: 用统计学方法（Cohen's d + 特征提取）从获奖/失败文章差距中自动生成评审规则优化建议，现在按类型正确选择特征集
6. **实用主义贯穿始终**: 降级策略完善、fire-and-forget 同步不阻塞用户、错误不中断流水线
7. **原文标注输出**: `annotation_builder.py` 将 5 个 Agent 的反馈映射回原文段落，生成 Word 修订模式般的 Markdown——这是"替代专业老师"目标的关键体验创新

### 关键风险 ⚠️

1. **LLM 判断深度不足**: 架构层面已准备就绪，但 LLM 能否在思辨型/商科型/历史型竞赛中做出专业级判断，仍取决于 Prompt 质量（标杆案例）和 LLM 自身领域知识。详见 [HUMAN_AGENT_COLLABORATION.md](HUMAN_AGENT_COLLABORATION.md)
2. **安全性在公网场景下仍不足**: 无速率限制、同步使用明文 HTTP
3. **数据隐私声明需要验证**: 学生论文发送到商业 LLM API，需在 UI 和 README 中明确告知用户
4. **测试基础设施需维护**: Python 3.14 下 11 个 async 测试因 pytest-asyncio 兼容性失败

### v0.2.0 → v0.3.0 完成的改进

| 类别 | 已完成 |
|------|--------|
| 校准引擎特征集 | FEATURES_BY_TYPE 含 8 种类型，feature_names() 动态返回 |
| fatal_defect | BINARY_FEATURES_BY_TYPE 含 8 种类型，按类型过滤 |
| Agent 权重 | 10 场比赛独立 agent_weights，weight_sum 归一化 |
| 配置映射 | FEATURE_TO_CONFIG_MAP_BY_TYPE 含 8 种类型 |
| A4 style_guides | _load_style_guide() 加载 JSON 传入 Agent |
| A3 type_hints | competition_type_hints.json 含 8 种类型 |
| 安全加固 | Bearer Token + 50MB 限制 + 类型白名单 |
| 技术债务 | subprocess 移除 + lock 文件 + CHANGELOG + CONTRIBUTING |

### 下一步改进优先级

| 优先级 | 项目 | 预估工作量 |
|--------|------|-----------|
| P0 | Prompt 标杆案例（每种竞赛类型 2-3 对"好/差"样本注入 few-shot） | 2 天 |
| P0 | 验证并完善隐私声明（README + Gradio UI） | 2 小时 |
| P1 | A3 quantitative_check 按类型动态输出 | 0.5 天 |
| P1 | 修复 pytest-asyncio 兼容性（Python 3.14） | 1-2 小时 |
| P2 | 学生水平自适应（按字数/复杂度估级） | 1 天 |
| P2 | 扩展 data/expert_insights/ 覆盖全部 7 种竞赛类型 | 1 天 |
| P3 | 数据库迁移方案（Alembic） | 0.5 天 |
| P3 | A4 prompt 动态注入 style_guide 数值参数 | 0.5 天 |
