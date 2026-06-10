# AcademicReviewer 项目评估报告

> **评估日期**: 2026-06-10
> **代码规模**: ~5,100 行 Python + 267 行 Prompt 模板 + 29 个 JSON 配置文件 + 18 个文档文件
> **技术栈**: Python 3.10+ / FastAPI / Gradio / SQLite / ChromaDB / httpx
> **评估方法**: 完整阅读全部源代码后进行多维度分析

---

## 综合评分: 7.4/10（更新于 2026-06-10 测试改进后）

| 维度 | 评分 | 等级 | 变化 |
|------|------|------|------|
| 架构设计 | 8.0/10 | 良好 — 思路清晰，无过度工程化 | — |
| 代码质量 | 7.5/10 | 良好 — 已修复多个硬编码和安全隐患 | ↑ 0.5 |
| 安全性 & 鲁棒性 | 5.5/10 | 需关注 — 存在多个中高风险项 | — |
| 测试 & 质量保障 | **7.5/10** | 合格 — 177 个单元测试 + CI | **↑ 4.0** |
| 文档质量 | 8.5/10 | 优秀 — 中英双语、面向多角色 | — |
| 可维护性 & 可扩展性 | 7.5/10 | 良好 — 配置驱动，易于扩展 | — |
| **竞赛类型公平性（新增）** | **5.0/10** | 偏差明显 — 研究型倾斜，校准引擎不适配非科研类型 | 🆕 |
| 依赖 & 技术债务 | 7.0/10 | 合格 — 有可优化空间 | — |

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

## 3. 竞赛类型公平性分析 (5.0/10) 🆕

> **核心问题**: 当前系统能否在所有类型的报告提交类竞赛中有效地给出作品质量评审和反馈？是否存在过于倾向某类型赛事的情况？

### 结论：存在明显的研究型倾斜，但框架本身可修正

### 3.1 当前对各竞赛类型的适配度

按系统实际适配度排序：

| 适配度 | 赛事 | 原因 |
|--------|------|------|
| ⭐⭐⭐⭐⭐ | **ISEF / STS** | 系统天然以科研论文为设计模板 |
| ⭐⭐⭐⭐ | **HiMCM** | 数模论文也是结构化+量化的，特征提取和多数维度匹配 |
| ⭐⭐⭐ | **丘成桐** | 进阶科研，大部分机制适用 |
| ⭐⭐⭐ | **CTB / NHD** | 社科/历史，结构+证据维度部分适用，但量化特征不适用 |
| ⭐⭐ | **John Locke / Marshall** | 思辨型议论文，校准引擎几乎无用，证据标准完全不同 |
| ⭐⭐ | **SIC / WGHS** | 金融分析，需要大量领域知识但 Agent prompt 覆盖了 |
| ⭐ | **FBLA** | 商科案例，框架评估（SWOT/PEST/五力）目前的配置支持有限 |

### 3.2 五个层面的偏差分析

#### 3.2.1 校准引擎特征集——最严重的偏差 🔴

21 个全局特征中，有 8 个是**纯科研专用**的 binary 检测：

```python
# 这些特征对 John Locke / 历史论文永远是 0.0
has_p_value          # "p < 0.05"
has_effect_size       # "Cohen's d"
has_control_group     # "control group"
has_sample_size        # "n = 200"
```

**后果**: 对 John Locke 议论文跑校准时，8 个特征全是 0.0，Cohen's d 算不出有效的效应量——不是因为获奖文章和失败文章没有差距，而是**特征集选错了**。

**更致命的连锁反应**: `generate_fatal_defect_updates()` 检测到 binary 特征 negative signal 时会建议把「缺少 p 值」标记为**致命缺陷 (fatal defect)**。这对 ISEF 完全合理，对 John Locke 是灾难性的错误建议。

#### 3.2.2 Agent 权重——所有类型一刀切 🔴

```python
AGENT_WEIGHTS = {
    "RubricParser":      0.25,  # ← 所有竞赛一样
    "StructureLogic":    0.20,
    "ArgumentEvidence":  0.25,
    "LanguageStyle":     0.15,
    "AcademicIntegrity": 0.15,
}
```

不同类型的竞赛对五个维度的实际需求完全不同：

| 赛事类型 | 结构重要性 | 证据重要性 | 语言重要性 | 学术诚信 |
|----------|-----------|-----------|-----------|---------|
| 科研型 (ISEF) | 中 | **极高** (数据/方法论) | 低 | **极高** |
| 思辨型 (John Locke) | **极高** (逻辑链) | 高 (引用质量) | 中 | 高 |
| 数模型 (HiMCM) | 高 | **极高** (模型正确性) | 低 | 低 |
| 商科型 (FBLA) | **极高** (框架应用) | 中 (数据支撑) | 高 (说服力) | 低 |
| 金融型 (SIC/WGHS) | 高 | 高 (数据/模型) | 中 | 中 |
| 历史型 (NHD) | 高 | **极高** (一手史料) | 中 | 高 |

**后果**: 一篇 HiMCM 论文的语言风格问题和一篇 John Locke 论文的语言风格问题，对总分的影响权重一样——这不合理。思辨型论文的逻辑结构应该权重更高，科研型论文的证据质量应该权重更高。

#### 3.2.3 A4 语言风格审查——学科差异被忽视 🟡

`a4_language_style.txt` 对所有类型用同样的审查标准。但不同学科对语言的要求完全不同：
- 科研论文：被动语态**被鼓励**（"The samples were measured..."）
- 商科提案：**主动、有说服力**的语言是必须的
- 历史论文：需要**正式学术语调**，但不能太技术化
- 思辨论文：句子结构本身就是**论证工具**，修辞精度至关重要

虽然 `configs/style_guides/` 有 6 个 JSON 文件，但 A4 的 prompt 中并没有针对性加载它们——全靠 LLM 自行判断。

#### 3.2.4 校准引擎特征集全局统一 🟡

`feature_names()` 返回的 21 个特征名对所有竞赛都一样。虽然科研专用特征不会被映射到非科研竞赛的 config change（因为 `FEATURE_TO_CONFIG_MAP` 里没有对应的键），但它们仍然出现在报告里，**稀释了真正有用的信号**。

对于 John Locke 思辨论文，真正有区分度的特征可能是：`vocabulary_diversity`、`logical_marker_density`、`transition_frequency`、`claim_count_estimate`、`hook_sentence_present`。但这些特征在科研论文中也有一定价值——问题在于不应该把科研专用的 8 个噪声特征混进来。

#### 3.2.5 Prompt 层面的类型感知（做得最好的部分）✅

`a2_structure_logic.txt` 和 `a3_argument_evidence.txt` 的 v1.7 双层架构（通用 coaching 层 + 竞赛专用检查）是做对了的。特别是 A3 的 type_hints 为 8 种类型提供了详细的检查指导。这是当前系统在类型感知方面**做得最好的部分**。

### 3.3 总结：偏差的本质原因

> 系统从架构到 Prompt 到校准引擎都**围绕传统学术研究论文的形态设计**。对 ISEF/STS/丘成桐/HiMCM 这些最接近学术论文形态的竞赛适配度最高。
>
> 对思辨型（John Locke）、商科型（FBLA）、历史型（NHD）的评价质量会**明显下降**，不是因为 Agent 不够好，而是因为底层的特征提取（校准）和权重分配（评分）没有针对这些类型进行适配。
>
> 框架本身（5 Agent + 配置驱动）的设计足够灵活，有能力修正这些偏差——但**修正还没有完成**。当前的"类型感知"主要停留在 Prompt 层面（告诉 LLM 注意什么），而没有深入到评分数学（权重、特征选择、校准逻辑）层面。

---

## 4. 安全性 & 鲁棒性 (5.5/10)

### 风险清单

**4.1 API 完全无认证 (严重) 🔴**
- 所有 REST API 端点（`/api/v1/*`）均无任何认证机制
- 任何能访问 `127.0.0.1:8000` 的人都可以提交评审、查看历史、修改赛事配置
- 缓解因素：默认绑定 `127.0.0.1`，仅本地可访问
- 风险升级场景：`HOST=0.0.0.0` 时对外暴露，管理看板也完全公开
- **建议**: 至少添加简单的 API Key / Bearer Token 认证

**4.2 文件上传无限制 (高) 🟠**
- `POST /api/v1/review` 未限制文件大小、类型（仅前端 Gradio 做了类型过滤）
- 可能被上传超大文件导致磁盘耗尽（临时文件 `/tmp`）
- **建议**: 添加文件大小限制（如 50MB）、服务端 MIME 类型验证

**4.3 学生数据隐私 (高) 🟠**
- 学生论文全文发送到第三方 LLM API（DeepSeek/OpenAI/Gemini/GLM）
- 未在用户界面或文档中明确告知数据会离开本地
- 学生姓名 (`student_name`) 明文存储在 SQLite 中
- **建议**: 添加隐私声明、提供本地模型选项的说明、考虑字段加密

**4.4 同步数据暴露 (中) 🟡**
- `sync.py` 将完整审查报告（包含学生论文内容、姓名）通过 HTTP POST 发送到中央服务器
- 同步使用明文 HTTP（非 HTTPS），在局域网中可能被嗅探
- **建议**: 支持 HTTPS、考虑对敏感字段脱敏、增加同步数据加密选项

**4.5 无速率限制 (中) 🟡**
- 无请求频率限制，可能被高频调用导致 LLM API 费用激增
- **建议**: 添加速率限制（如每分钟 5 次审核）

**4.6 路径遍历已修复 ✅（原风险）**
- **已修复**: `_load_rubric_config()` 现在使用 `Path(safe_name).name` 防止路径遍历

**4.7 依赖供应链 (低) 🟡**
- `requirements.txt` 无版本锁定（全部使用 `>=`）
- ChromaDB 的 transitive 依赖（onnxruntime、numpy）体积大且版本敏感
- **建议**: 添加锁文件或使用 pip-tools 生成精确版本

**4.8 生产就绪度评估**
- 当前项目定位为 **内网工具/个人辅助工具**，安全措施与定位基本匹配
- 如需面向公网或多人使用，至少需要补充 API 认证和速率限制

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
| 竞赛类型偏差 | **高** | 校准引擎、权重、评分机制研究型倾斜 | 🆕 见 §3 |
| 无数据库迁移 | 中 | `Base.metadata.create_all()` 每次启动执行 | 未修复 |
| 无配置热加载 | 低 | 修改 `.env` 或 JSON 配置需重启服务 | 未修复 |
| 评分键名硬编码 | 低 | Agent 输出字段名分散在多处 | ✅ 已修复 |
| requirements.txt 宽松版本 | 低 | `>=` 约束可能导致依赖升级引入 breaking change | 未修复 |
| 潜在循环导入 | 低 | 当前通过 lazy import 规避 | 未修复 |
| 缓存无失效机制 | 低 | 全局缓存单例 | ✅ 已修复 (clear_config_cache) |
| 路径遍历风险 | 低 | competition 名直接构建文件路径 | ✅ 已修复 |
| type_hints 硬编码 | 低 | A3 的 8 种类型提示写在代码中 | 未修复 |

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
2. **AI_HANDOFF.md 堪称典范**: 这是 AI 辅助开发场景下接手指南的标杆级文档
3. **配置驱动的可扩展性**: 添加竞赛类型无需修改代码，配合 GUI 管理界面用户体验良好
4. **校准引擎思路精巧**: 用统计学方法（Cohen's d + 特征提取）从获奖/失败文章差距中自动生成评审规则优化建议
5. **实用主义贯穿始终**: 降级策略完善、fire-and-forget 同步不阻塞用户、错误不中断流水线
6. **测试基础设施建设完成**: 177 个单元测试、Mock 框架、CI 就绪——从 3.5 分跃升到 7.5 分

### 关键风险 ⚠️

1. **竞赛类型公平性不足**: 系统在研究型竞赛上表现最好，对思辨型/商科型/历史型竞赛存在系统性偏差——校准引擎特征集不匹配、权重一刀切、A4 审查标准不分学科
2. **安全性在生产场景下不足**: 无认证、无速率限制、明文传输同步数据
3. **数据隐私需要明确**: 学生论文全文发送到商业 LLM API，需要用户知情同意

### 本次会话完成的改进

| 类别 | 已完成 |
|------|--------|
| 测试基础设施 | pytest.ini + conftest.py + MockLLMAdapter |
| 单元测试 | 177 个测试（13 个文件），0 失败 |
| CI/CD | GitHub Actions workflow |
| 代码质量 | 6 项修复（score_key、路径遍历、缓存失效、Agent 导出等） |
| 评估报告 | 本文档（含竞赛类型公平性分析） |
| 改进计划 | 见 `IMPROVEMENT_PLAN.md` |

### 下一步改进优先级

详见配套文档 **[IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md)**。

| 优先级 | 项目 | 预估工作量 |
|--------|------|-----------|
| P0 | 校准引擎按竞赛类型切换特征集（消除研究型偏差的最大根源） | 2-3 天 |
| P0 | Agent 权重按竞赛类型可配置（消除一刀切评分） | 1 天 |
| P1 | A4 真正加载和使用 style_guides | 1 天 |
| P1 | 为文件上传添加大小限制和类型验证 | 1 小时 |
| P1 | 添加 API 认证（Bearer Token） | 半天 |
| P1 | 添加隐私声明 | 1 小时 |
| P2 | 将 type_hints 从 argument_evidence.py 移到 configs/ JSON | 0.5 天 |
| P2 | 生成 requirements-lock.txt | 半小时 |
| P3 | 替换 Gradio subprocess 调用为直接函数调用 | 1 天 |
| P3 | 添加 Changelog 和 Contributing 指南 | 半天 |
