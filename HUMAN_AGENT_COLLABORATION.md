# 人机协作：从"AI 辅助评审"到"替代专业老师"的工程路线图

> **目标**: 在任意项目制竞赛中，本系统能实现非常自然和精准的作品审核与反馈，贴合实际参赛要求，符合参赛标准，替代专业老师。
> **当前状态**: 架构准备就绪（v0.3.0），LLM 判断深度是核心瓶颈。本文识别可复用的现有功能，指出仅需功能性扩展的部分。
> **最后更新**: 2026-06-12

---

## 一、核心判断：AI 能替代老师的哪些部分？

专业老师在一篇竞赛论文上的工作可以分为五个层次：

| 层次 | 老师的能力 | AI 现状 | 可替代性 |
|------|-----------|---------|---------|
| **L1: 形式检查** | 语法、拼写、格式、引用规范 | ✅ 已达可用水平（A4/A5） | **95%** |
| **L2: 结构诊断** | 章节是否完整、比例是否合理、逻辑是否连贯 | ✅ 已达可用水平（A2） | **85%** |
| **L3: 论证评估** | 论点是否有证据、推理是否成立、反方是否回应 | ⚠️ 科研型较好，思辨型/商科型不足 | **60-75%** |

> **L3 子分层（Trae AI 补充）**：论证评估内部可分为两层——
> - **L3a 结构层**（是否有 counterargument、是否有 evidence、引用格式是否正确）→ AI 已能做好，可标 FULL
> - **L3b 质量层**（counterargument 是否真的打到核心反方、evidence 是否真的支撑 claim）→ AI 当前吃力，应标 REVIEW
> - 这个区分对方案 B（置信度标签）至关重要——不同类型的问题需要不同的人工审核策略
| **L4: 领域深度判断** | "这个实验设计真的解决了问题吗"、"这个哲学论证有原创性吗" | ❌ 当前 LLM 难以达到 | **30-40%** |
| **L5: 个性化教练** | 根据学生水平调整反馈、知道什么阶段该强调什么 | ❌ 未实现 | **10%** |

**结论**: AI 可以覆盖 L1-L3 的大部分工作，但 L4-L5 需要人机协作来弥补。策略不是"让 AI 变得和老师一样好"，而是**"让 AI 做它能做的，让老师做 AI 做不了的，并用工程手段最大化两者的协作效率"**。

---

## 二、各竞赛类型的替代程度分析

### 2.1 科研型（ISEF / STS / 丘成桐）— 替代度 85%

**AI 已经能做的**:
- L1: 学术格式、引用规范检查（A4/A5）
- L2: 科研论文结构化程度高（Abstract→Intro→Method→Results→Discussion），A2 对照 `structure_schemas/research.json` 检查非常有效
- L3: 证据评估（p 值/效应量/控制组/局限性讨论），A3 的 `quantitative_check` 直接适用
- 校准引擎: 21 特征全部适用，Cohen's d 能有效发现获奖/失败文章的差距

**AI 做不到的**:
- L4: 判断实验设计的原创性和科学性——"这个实验方案真的回答了研究问题吗？"、"这个统计学方法选对了吗？"
- L5: 针对学生科研水平的个性化指导

**工程策略**: 科研型的主要差距在 L4。解决方案：老师在现有的专家经验文档（`data/expert_insights/`）中补充 `[signal]` 和 `[benchmark]` 类型的条目——例如"什么样的实验设计才算严谨"、"好的 method section 长什么样 vs 差的"。AI 在评审时引用这些知识作为对比基准。

### 2.2 思辨型（John Locke / Marshall Society）— 替代度 65%

**AI 已经能做的**:
- L1: 语法/拼写/风格检查（A4 已按 `style_guides/discursive.json` 调整标准）
- L2: 结构完整性（A2 检查 thesis 陈述→argument 段落→counterargument→rebuttal→conclusion）
- L3: 部分论证评估（逻辑谬误检测、claim-evidence 匹配，A3 已有 `logical_fallacies` 输出）

**AI 做不到的**:
- L3: "这个 counterargument 真的反驳了最强反方吗？还只是打了一个稻草人？"——需要理解论证的**哲学深度**
- L4: "这个论证的原创性在哪里？它是在重复已有的哲学立场还是在推进新观点？"——需要领域知识
- L5: 区分"论证不成熟但方向对"和"论证方向本身有问题"

**工程策略**: 思辨型是**最需要人机协作**的类型。核心方案是"脚手架式反馈"——不像科研型那样直接判断，而是**逐层揭示论证的结构缺陷**（见 §3.4 方案 D），让学生自己和老师能看清问题在哪。同时需要在专家经验文档中写入思辨型特有的 `[fatal_defect]`（如"缺少 counterargument 总分上限 6/10"）和 `[benchmark]`（好 thesis vs 差 thesis 对照）。

### 2.3 数模型（HiMCM）— 替代度 70%

**AI 已经能做的**: L1-L2 结构检查、格式检查；L3 模型假设检查、灵敏度分析检查、公式引用检查；校准引擎特征集合适（保留 has_sample_size，去掉 p_value/effect_size/control_group）。

**AI 做不到的**: L4 "这个数学模型选型合适吗？ODE 模型和 agent-based model 哪种更适合这个问题？"、"这个灵敏度分析覆盖了真正敏感的参数吗？"

**工程策略**: 差距在数学直觉。老师通过专家经验文档的 `[pitfall]` 和 `[pattern]` 类型，列出"常见模型选型错误"和"好的假设段落 vs 差的假设段落"标杆案例。AI 在评审时对照检查，提出质疑但不做最终判断。

### 2.4 社科型（CTB）— 替代度 70%

**AI 已经能做的**: 结构化检查、调研方法论检查、案例深度检查（`social_science` 特征集适用）。AI 做不到 L4 方法论判断。工程策略同上——通过专家经验文档输入"调研方法论检查清单"。

### 2.5 历史型（NHD）— 替代度 65%

**AI 已经能做的**: 结构检查、一手史料引用检查（A3 type_hints: "一手史料引用、史学视角、时代语境还原"）。AI 做不到 L4 史料解读深度判断。工程策略：老师在专家经验文档中输入 `[pitfall]` "常见史料误读"和 `[benchmark]` "好的史料分析 vs 差的史料堆砌"。

### 2.6 金融型（SIC / WGHS）— 替代度 60%

领域知识最密集的类型之一。AI 可做结构检查和数据来源检查，L4 估值合理性判断需要老师的 `[fatal_defect]` 规则（如"估值模型假设无理由说明→证据维度上限 5/10"）和 `[pitfall]` 常见分析遗漏点。AI 无法判断"DCF 折现率选 8% vs 10% 哪个合理"，但可以检查"这个折现率有没有 justification"——这正是 `[fatal_defect]` 的价值所在。

### 2.7 商科型（FBLA）— 替代度 65%

AI 可做框架应用检查（SWOT/PEST/五力）、ROI 计算检查、alternative solutions 对比。L4 需要老师的 `[benchmark]` "正确的 SWOT 归类 vs 错误的 SWOT 归类"作为 AI 判断基准。

---

## 三、现有功能盘点：哪些已经在了，哪些只需扩展

在提出新方案之前，先盘点现有系统中已经存在的功能，避免"重复建设已有之物"。

### 3.1 专家经验输入系统 ✅ 已存在

**文件**: `app/calibration/expert_annotator.py` + `app/calibration/expert_freeform_parser.py`

这是系统中专门为"老师上传经验文档"设计的功能。它已经支持三种输入模式：

| 模式 | 格式 | 触发条件 | 适用场景 |
|------|------|---------|---------|
| **Mode 3（全结构化）** | `### [type] feature_name` 标记 | 文档包含 `### [` | 老师严格按模板写 |
| **Mode 2（半结构化）** | `## 常见问题` / `## 获奖经验` 等章节标题 | 包含已知章节标题但无 `### [` 标记 | 老师用自然章节但遵循分类 |
| **Mode 1（纯自由）** | 无任何结构标记的纯文本 | 以上都不满足 | 老师随手写的任意文字 |

解析器 `unify_parse()` 自动检测模式，Mode 1/2 使用 LLM 将自然语言拆分为结构化条目，但**特征映射始终走本地 `FEATURE_KEYWORDS` 关键词匹配**（确定性匹配，零幻觉风险）。

**现有的 5 种 Annotation 类型**:

| 类型 | 含义 | 示例 |
|------|------|------|
| `pattern` | 老师观察到的获奖模式/成功规律 | "获奖论文引用密度在 15 条/千字以上" |
| `pitfall` | 学生常见错误/扣分陷阱 | "中国学生被动语态通常超过 35%，这是主要扣分原因" |
| `signal` | 高分信号/评审偏好 | "跨学科引用是 ISEF 决赛信号" |
| `strategy` | 教学策略/训练方法 | "方法论写作的 5 段式黄金框架" |
| `rubric` | 评分标准解读 | 对评分细则的理解 |

**已有数据**: `data/expert_insights/ISEF_research_example.md`（8 条洞察，张老师，8 年经验）、`data/expert_insights/John_Locke_example.md`（8 条洞察，李老师，5 年经验）、`data/expert_insights/HiMCM_Mode2_example.md`、`data/expert_insights/ISEF_Mode1_freeform_example.md`。

### 3.2 校准引擎中的专家经验集成 ✅ 已存在

**文件**: `app/calibration/engine.py:244-269`

`run_calibration()` 已在 Step 5 调用 `unify_parse()` 解析专家文档，并将 `expert_insights_report` 嵌入校准报告末尾。

```python
# 现有流程（engine.py）
if expert_doc_paths:
    for doc_path in expert_doc_paths:
        insights = unify_parse(doc_path, llm)  # 自动检测 Mode 1/2/3
        expert_insights_list.append(insights)
    merged = merge_insights(*expert_insights_list)
    expert_insights_report = insights_report_markdown(merged)
# → 嵌入校准报告
```

### 3.3 原文标注生成器 ✅ 已存在

**文件**: `app/utils/annotation_builder.py`

`build_annotated_markdown()` 已能将 5 个 Agent 的反馈映射回原始文档段落，生成带批注的 Markdown（如 Word 修订模式）。标注格式：`[A2—high]`、`[A3!!—逻辑谬误]`、`[A4-spelling]`、`[A5!—引用]`。

### 3.4 同步基础设施 ✅ 已存在

**文件**: `app/utils/sync.py`

`report_review()` 和 `report_calibration()` 已实现 fire-and-forget POST 到中央服务器。这个模式可直接复用于反馈数据的收集。

### 3.5 A2/A3 的结构化输出 ✅ 已存在

A2 输出已包含 `section_issues`（含 `should_only_do`/`what_to_move`）、`logic_issues`（含 `transition_suggestion`）、`main_argument_coaching`（含 `vulnerability`/`stronger_version`）、`duplication_report`。

A3 输出已包含 `claims`（含 `missing_chain`/`coach_rewrite`）、`logical_fallacies`（含 `why_it_fails`/`correct_form`）、`validation_point`（含 `coach_guidance`）、`source_quality`。

### 3.6 现有功能与需求对照总结

| 需求（HUMAN_AGENT_COLLABORATION.md 原方案） | 现有功能 | 需要做的 |
|-------------------------------------------|---------|---------|
| 老师上传经验文档 | ✅ `expert_annotator.py` + 3 种模式 | **无需新建** |
| 知识卡"领域检查清单"（what_excellence_looks_like） | ✅ 现有 `pattern`/`pitfall`/`signal` 类型覆盖 | **无需新建** |
| 知识卡"阈值与红线"（fatal_defects） | ❌ 缺少 `fatal_defect` annotation 类型 | **扩展 ANNOTATION_TYPES**（+1 行） |
| 知识卡"评分锚点"（scoring_anchors） | ❌ 缺少 `scoring_anchor` annotation 类型 | **扩展 ANNOTATION_TYPES**（+1 行） |
| 知识卡"标杆案例"（benchmarks） | ❌ 缺少 `benchmark` annotation 类型 | **扩展 ANNOTATION_TYPES**（+1 行） |
| 知识卡自动分层（Layer 1/2/3） | ❌ 未实现 | **新增 `build_knowledge_cards()`**（~30 行） |
| 知识卡注入 Review Pipeline | ❌ 仅在校准中集成，未在评审中集成 | **Orchestrator 调用 knowledge cards**（~20 行） |
| 反馈置信度标签 | ❌ 全新 | **需新建** |
| 老师反馈闭环 | ❌ 全新（但 sync.py 可复用） | **需新建** |
| 脚手架式论证分解 | ⚠️ A2/A3 已有结构化输出，但粒度不够 | **增强 prompt** |

---

## 四、工程方案

### 4.1 方案总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    人机协作审稿系统架构                              │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ 老师上传  │ → │  AI 自动评审  │ → │ 老师审核 & 标注       │  │
│  │ 经验文档  │    │ (每次评审)    │    │ (按需/抽查)          │  │
│  │ (已存在)  │    └──────────────┘    └──────────────────────┘  │
│  └──────────┘           │                       │               │
│       │                 ▼                       ▼               │
│       ▼          ┌──────────────┐    ┌──────────────────────┐  │
│  ┌──────────┐    │ 标注报告      │    │ 反馈闭环（新增）       │  │
│  │ 解析器   │    │ + 置信度标签  │    │ → 老师逐条确认/修正    │  │
│  │ (已存在)  │    │ + 人审标记区  │    │ → 置信度自动校准      │  │
│  └──────────┘    └──────────────┘    │ → 触发经验文档更新     │  │
│       │                              └──────────────────────┘  │
│       ▼                                                         │
│  ┌──────────┐                                                    │
│  │ 知识卡   │ ← build_knowledge_cards() (新增 ~30行)             │
│  │ Layer 1/2/3                                                  │
│  └──────────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │ Orchestrator                                                  │
│  │ 注入Agent │ (新增 ~20行)                                       │
│  │ prompt   │                                                    │
│  └──────────┘                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 方案 A: 知识卡系统（扩展现有专家经验输入，不另起炉灶）

> **核心原则**: 老师的工作流不变——仍然是上传同一个 `.md` 文件。系统的 `expert_annotator.py` 解析器已经能处理结构化/半结构化/自由文本三种输入。只需要做三件事。

#### Step 1: 扩展 ANNOTATION_TYPES（3 行代码）

```python
# app/calibration/expert_annotator.py

ANNOTATION_TYPES = (
    "pattern", "pitfall", "rubric", "signal", "strategy",
    "fatal_defect",    # 🆕 致命缺陷 / 硬红线 — 总分自动受限
    "benchmark",        # 🆕 好/差对照案例 — AI 判断质量的参照物
    "scoring_anchor",   # 🆕 分数锚点 — 各分数段的典型特征描述
)
```

同时扩展 `expert_freeform_parser.py` 中 Mode 2 的 `SECTION_TITLE_PATTERNS`：

```python
"fatal_defect": ["致命缺陷", "一票否决", "红线", "硬性标准"],
"benchmark": ["标杆案例", "范例", "好文案例", "差文对比", "范文片段"],
"scoring_anchor": ["评分锚点", "打分参考", "各分数段标准"],
```

#### Step 2: 老师文档格式（与现有格式完全兼容）

老师不需要学任何新东西。在这份**同一个 `.md` 文件**里，增加以下三种 section：

```markdown
## 竞赛: John Locke
## 作者: 李老师

### [pattern] logical_marker_density
**标题**: 逻辑连接词密度决定论证质量
...（现有内容不变）...

### [fatal_defect]
**标题**: 缺少 counterargument 总分上限 6/10
**描述**: John Locke 评审标准明确要求回应反方。全文无任何 counterargument 的论文，无论其他部分多好，总分不得超过 6/10。如果 counterargument 存在但明显是稻草人（歪曲反方立场），论证维度分数上限 4/10。

### [scoring_anchor]
**标题**: 9-10分段：论证链完整且原创
**描述**: 论证链条完整且原创性强、counterargument 回应了反方最强主张、rebuttal 展示了深层推理、结论超出题目本身进行了哲学升华。

### [scoring_anchor]
**标题**: 5-6分段：方向对但论证链不完整
**描述**: 方向大致正确但论证链不完整——有论点但缺乏充分证据或 rebuttal 缺失。或者论点本身有价值但被淹没在大量不必要的背景描述中。

### [benchmark]
**标题**: 优秀 thesis — 争议性主张 + 论证路径暗示
**描述**: "This essay argues that Rawls' difference principle, while normatively appealing, fails to account for motivational constraints — a gap Cohen's critique identifies but does not fully resolve."
**为什么好**: 不是描述事实，而是提出可争议的主张；暗示了论证路径；概念使用精准（difference principle, weak incentives）。

### [benchmark]
**标题**: 薄弱 thesis — 事实陈述，无法争论
**描述**: "Rawls' theory of justice is important. In this essay I will discuss his main ideas."
**为什么差**: 无争议性——没有理性人会反驳'Rawls很重要'。没有做出分析性承诺。读者看完不知道文章要论证什么。
```

#### Step 3: 自动分层函数（~30 行新代码）

现有的 `parse_expert_document()` 已经能解析 `### [type]` 格式，`unify_parse()` 已经能自动检测三种模式。新增三种类型后，解析出的是统一的 `ExpertInsights`。只需要加一个分层函数：

```python
# app/calibration/knowledge_cards.py（新建，~30行）

def build_knowledge_cards(insights: ExpertInsights) -> dict:
    """将 ExpertInsights 自动分层为三层知识卡。"""
    cards = {
        "layer_1_core": {
            "what_excellence_looks_like": [],
            "fatal_defects": [],
            "scoring_anchors": [],
        },
        "layer_2_benchmarks": [],
        "layer_3_notes": [],
    }

    for a in insights.annotations:
        if a.annotation_type in ("pattern", "pitfall", "signal"):
            cards["layer_1_core"]["what_excellence_looks_like"].append(a)
        elif a.annotation_type == "fatal_defect":
            cards["layer_1_core"]["fatal_defects"].append(a)
        elif a.annotation_type == "scoring_anchor":
            cards["layer_1_core"]["scoring_anchors"].append(a)
        elif a.annotation_type == "benchmark":
            cards["layer_2_benchmarks"].append(a)
        else:
            cards["layer_3_notes"].append(a)

    return cards
```

#### Step 4: 注入 Review Pipeline（~20 行）

当前专家经验**只在校准引擎中使用**（`engine.py` 的 `run_calibration()`）。需要让它在评审时也生效：

```python
# app/orchestrator.py（新增方法）

def _load_knowledge_cards_for_competition(self, competition: str) -> dict:
    """从专家经验文档加载并分层知识卡。"""
    comp_config = self.lookup_competition(competition)
    expert_docs_dir = Path(__file__).resolve().parent.parent / "data" / "expert_insights"
    # 按文件名中的竞赛名匹配，或从 competition_registry.json 的 knowledge_cards_ref 读取
    # ...
    insights = merge_insights(*[unify_parse(p) for p in matched_files])
    return build_knowledge_cards(insights)
```

然后在 `review()` 方法中，将知识卡注入 Agent 的 prompt（作为 `knowledge_cards` 参数，Agent 的 `_build_user_message()` 中拼接到 prompt 末尾）。

#### 知识卡三层设计

| 层级 | 内容 | 来源（Annotation 类型） | 必填 | 更新频率 |
|------|------|----------------------|------|---------|
| **Layer 1: 核心必填** | what_excellence_looks_like + fatal_defects + scoring_anchors | pattern / pitfall / signal / fatal_defect / scoring_anchor | 是（3 项 core） | 竞赛标准变化时（一年一两次） |
| **Layer 2: 标杆案例** | 好/差段落对照文本 | benchmark | 建议至少 1 对 | 每届比赛后补充 2-3 个 |
| **Layer 3: 自由笔记** | 教学策略、随手记、未分类经验 | strategy / rubric / 其他 | 否 | 任意时间 |

#### 老师的工作流

1. **上线前**（一次性 15-20 分钟）：打开 `data/expert_insights/[竞赛名]_[老师名].md`，至少填写 Layer 1 的 3 项 core（what_excellence_looks_like 用 `[pattern]`/`[pitfall]`、fatal_defects 用 `[fatal_defect]`、scoring_anchors 用 `[scoring_anchor]`），建议至少 1 对 `[benchmark]`
2. **日常使用中**（随时 3 分钟）：想到新的经验，打开同一个文件，加一个 section。Mode 1/2/3 都支持——可以写严格格式的 `### [type]`，也可以写 `## 常见问题` 半结构化，甚至可以纯文本丢进去
3. **每届比赛后**（一次 30 分钟）：审核 10-20 篇 AI 评审结果，发现 AI 反复判错的地方，补充或修正知识卡中对应的条目
4. **自由笔记→正式知识卡**：Layer 3 中的 `[strategy]` 条目累计到一定量后，由维护者判断哪些值得"提升"到 Layer 1 或 Layer 2，修改 annotation type 即可

### 4.3 方案 B: 反馈分级与置信度标签（全新）

> **现有功能**: 无。`annotation_builder.py` 已有标注格式但无置信度维度。

AI 的每条评审意见标注**置信度**和**替代程度**，让老师知道哪些可以直接信任、哪些需要人工审核。

#### 输出格式扩展

在每个 Agent 的输出中增加 `confidence` 和 `substitutability` 字段：

```json
{
  "claims": [
    {
      "claim": "论证缺少 rebuttal",
      "confidence": "HIGH",
      "substitutability": "FULL",
      "rationale": "A3 在全文未找到 counterargument 结构标记"
    },
    {
      "claim": "这个 rebuttal 没有真正回应反方的核心论证",
      "confidence": "MEDIUM",
      "substitutability": "REVIEW",
      "rationale": "检测到 rebuttal 结构，但 rebuttal 内容和反方主张之间的逻辑关联较弱"
    },
    {
      "claim": "论文的哲学立场缺乏原创性",
      "confidence": "LOW",
      "substitutability": "ESCALATE",
      "rationale": "原创性判断属于 L4 领域深度层级，超出当前 AI 能力"
    }
  ]
}
```

`substitutability` 三级定义：

| 级别 | 含义 | 标注显示 | 老师行动 |
|------|------|---------|---------|
| **FULL** | AI 判断可完全替代老师 | 绿色，无特殊标记 | 无需审核 |
| **REVIEW** | AI 判断需要老师确认 | ⚡ 黄色 | 抽查或批量确认 |
| **ESCALATE** | AI 无法判断，必须老师 | 🔴 红色 | 必须逐条审核 |

> **Trae AI 实现注意**：置信度标签不应该让 LLM 自己判断（LLM 对自己输出的置信度评估本身不可靠）。应该用**规则引擎**确定置信度——
> - 结构检测（格式、拼写、章节完整性）→ `FULL`
> - 语义判断（论证强度、逻辑连贯性）→ `REVIEW`  
> - 领域深度判断（原创性、哲学立场、模型选型合理性）→ `ESCALATE`
> - 规则引擎在 Agent 输出后、annotation_builder 组装前运行，不依赖 LLM 自评。

#### `annotation_builder.py` 扩展

在现有标注格式基础上增加置信度标记：

```markdown
### 段落 5
原文内容...

> **[A3-FULL]** rebuttal 缺失。建议在第 5 段后添加 counterargument 段落。
> **[A3-REVIEW]** ⚡ rebuttal 逻辑关联可能不足。
> **[A4-FULL]** `recieve` → `receive`
> **[A5-ESCALATE]** 🔴 引用哲学立场原创性评估需人工。
```

### 4.4 方案 C: 人类反馈闭环（全新）

> **现有功能**: `sync.py` 已实现 fire-and-forget 数据上报。反馈闭环可复用此传输层。
> 
> **Trae AI 实施建议**：Phase 3 建议拆为两个子阶段，因为 Gradio 审核界面比预期复杂——
> - **3a**（数据 API + 存储，1-2 天）：`POST /api/v1/feedback` 端点 + SQLite 存储 + 简单确认逻辑
> - **3b**（Gradio 审核界面 + 统计，2 天）：加载评审结果 → 可交互表单 → 逐条确认/修正 → 按 Agent/竞赛类型/confidence 维度聚合统计

每一次老师审核 AI 的评审结果，都产生一个数据点。

#### 反馈数据结构

```json
{
  "review_id": "uuid",
  "teacher_id": "张老师",
  "corrections": [
    {
      "agent_output_path": "argument.claims[2]",
      "ai_confidence": "MEDIUM",
      "ai_claim": "rebuttal 逻辑关联弱",
      "teacher_action": "OVERRIDE",
      "teacher_correction": "rebuttal 确实回应了核心主张但推理步骤不完整",
      "teacher_rationale": "回应了'损害'但未回应'为什么替代方案更差'"
    }
  ],
  "timestamp": "2026-06-12T10:30:00"
}
```

#### 闭环产出

1. **置信度校准**: 统计每种 Agent/竞赛类型组合下的 AI 信心 vs 老师确认率，自动调整方案 B 的置信度标注
2. **知识卡更新建议**: 老师多次纠正同一模式后，系统提示"是否将此类纠正写入专家经验文档？"
3. **Prompt 优化建议**: 反馈数据积累到阈值后，自动识别"AI 反复被纠正的领域"，建议增强响应的 prompt 部分

#### 与现有 sync.py 的关系

`sync.py` 的 `report_review()` / `report_calibration()` 是现有的 HTTP POST 通道。反馈数据上报遵循同一模式——`report_teacher_feedback()`，fire-and-forget，不影响评审主流程。

### 4.5 方案 D: 脚手架式反馈（增强现有 A2/A3 prompt）

> **现有功能**: A2 已有 `section_issues`+`logic_issues`+`main_argument_coaching`+`duplication_report`；A3 已有 `claims`（含 `missing_chain`+`coach_rewrite`）+`logical_fallacies`（含 `why_it_fails`+`correct_form`）+`validation_point`。差距在于"推理步骤分解"的粒度。

思辨型论文（John Locke/Marshall）的最大难题：AI 无法判断论证的哲学深度。方案不是让 AI 做深度判断，而是让 AI **逐层揭示论证的结构**，把判断权交给老师/学生。

#### 只需增强 prompt，不改数据结构

A3 现有的 `claims[].missing_chain` 字段已经能承载"缺失推理步骤"的描述。只需在 `a3_argument_evidence.txt` prompt 中增强推理分解的指导：

```markdown
【推理链分解 — 适用于思辨型】
对于每个论证 claim，请将推理链分解为"从 A 到 C"的步骤：
- from: 学生的前提 A
- to: 学生声称的结论 C
- missing_step: A→C 之间缺少的中间步骤 B
- why_critical: 为什么缺少这一步会导致论证不成立

示例：
学生写："自由贸易促进发展（Smith 2010），因此发展中国家应全面开放市场。"
→ from: 自由贸易促进发展
→ to: 发展中国家应全面开放市场
→ missing_step: "自由贸易促进发展"的前提是市场机制健全——“发展中国家”是否满足这个前提？
→ why_critical: Smith 的理论假设了竞争性市场和要素流动性，这在许多发展中国家不成立。
如果不检验这个前提，论证就建立在未声明的假设上。
```

A2 现有的 `logic_issues[].transition_suggestion` 已经能给出具体过渡句——这个"给具体方案"的模式扩展到 A3 的 missing_chain 分析即可。

#### 学生的视角

学生收到的不是"你的论证不好"，而是（由 `annotation_builder.py` 组装）：

> 你的论证结构我们已经梳理出来了。注意第 2 条论证链中的 **缺失步骤**：你从"技术传播"跳到了"发展中国家受益"，但缺了一个关键环节——**技术传播需要吸收能力**。请补充这个推理步骤，回答：发展中国家是否有足够的制度/人力来吸收技术？
>
> 另外，你的 **counterargument 部分**回应了'技术依赖'但不是最核心的反方论证。最强力的反方是 **"比较优势固化"**——自由贸易可能让发展中国家锁定在低端产业。请直接回应这个挑战。

这比"论证质量 6/10"有用得多，而且是 AI 能力范围内可以做到的。

---

## 五、实施路线图

### Phase 1: 知识卡功能上线（2-3 天）— ✅ 已完成（2026-06-12）

- [x] **扩展 `ANNOTATION_TYPES`**: `fatal_defect` + `benchmark` + `scoring_anchor`（`expert_annotator.py` 1 行 + `expert_freeform_parser.py` 3 行）
- [x] **新建 `build_knowledge_cards()`**: 将 `ExpertInsights` 自动分层为三层知识卡（`app/calibration/knowledge_cards.py`，~90 行）
- [x] **Orchestrator 集成**: `_load_knowledge_cards_for_competition()` + 注入 A2/A3 Agent prompt（`orchestrator.py` ~40 行）
- [x] **为 ISEF 和 John Locke 编写完整知识卡示例**: ISEF 9 条（2 pattern/pitfall/signal + 2 fatal_defect + 2 scoring_anchor + 2 benchmark）、JL 10 条（3 pattern/pitfall/signal + 2 fatal_defect + 2 scoring_anchor + 3 benchmark）

### Phase 2: 置信度标签 + 标注增强（1-2 天）— ✅ 已完成（2026-06-13）

- [x] **Agent prompt 增加 `confidence`/`substitutability` 输出字段**: A2/A3/A4/A5 各 prompt 追加格式要求
- [x] **`annotation_builder.py` 按置信度分级显示**: FULL/REVIEW/ESCALATE 三种标记样式
- [x] **验证并完善隐私声明**: README + Gradio UI 添加"学生论文发送至 LLM API"的明确说明

### Phase 3: 反馈闭环（4 天）— ✅ 已完成（2026-06-13）

- [x] **3a 数据 API + 存储（1-2 天）**: `POST /api/v1/feedback` 端点 + SQLite 存储
- [x] **3b Gradio 审核界面（2 天）**: 加载评审结果 → 可交互逐条确认/修正 → 按 Agent/类型/confidence 聚合统计
- [x] **置信度校准统计**: 按 Agent/竞赛类型统计 AI 信心 vs 老师确认率

### Phase 4: 深度增强（持续）— ✅ 已完成（2026-06-13）

- [x] **A3 prompt 增强推理链分解**: 思辨型论文的 from→to→missing_step→why_critical（不改数据结构，只增强 prompt）
- [x] **学生水平自适应**: 按字数/复杂度/往年成绩估级
- [x] **知识卡自动更新建议**: 当老师多次纠正同一模式时触发
- [x] **扩展 `data/expert_insights/`**: 覆盖全部 7 种竞赛类型的专家经验示例

---

## 六、关键指标

| 指标 | 当前 | Phase 1 目标 | Phase 2 目标 | Phase 4 目标 |
|------|------|-------------|-------------|-------------|
| 老师审核时间占比 | 100%（无 AI） | 40%（AI 初审+老师复核） | 20%（高置信度免审） | 10%（仅 ESCALATE 项目） |
| L1-L2 自动化率 | 95% | 95% | 98% | 99% |
| L3 自动化率 | 60-75% | 70-80%（知识卡辅助） | 75-85% | 85-90% |
| L4 辅助率 | 0% | 20%（知识卡对照 AI） | 40% | 60%（闭环优化后） |
| 知识卡覆盖率 | ISEF + JL（2/10 场比赛） | 10/10 场比赛 | 全部有标杆案例 | 全部≥3 对标杆 + 持续更新 |

---

## 七、结论

**四个方案中，方案 A（知识卡）75% 的基础设施已经存在。** `expert_annotator.py` + `expert_freeform_parser.py` 的三种输入模式 + 特征映射 + `ExpertInsights` 数据结构 + `unify_parse()` + `merge_insights()` + 校准引擎中的专家经验集成——这些都不是"需要建的"，而是"已经能用的"。

需要新增的只有：
- 3 个 annotation 类型（`fatal_defect`、`benchmark`、`scoring_anchor`）—— **3 行代码**
- `build_knowledge_cards()` 分层函数—— **~30 行代码**
- Orchestrator 加载并注入 prompt—— **~20 行代码**

其余方案 B/C/D 是真正的新建工作，但它们的价值在于：**让老师的每一次审核都不浪费**——每一条确认/修正在统计层面校准了 AI 的置信度，在内容层面优化了未来的知识卡。

**AI 不应该被设计为"替代"老师，而应该被设计为"放大"老师。** 这套人机协作方案的目标是：让一个老师批改 200 篇论文的质量，超过他独自批改 30 篇。

### 补充：AI 作为"一筛"的实际工作流（Trae AI）

在当前阶段，AI 评审可以理解为"一筛"——把论文结构化，让老师从梳理好的结果出发做判断：

1. AI 标记为 **FULL** 的（如语法错误、格式问题）→ 老师直接跳过，无需确认
2. AI 标记为 **REVIEW** 的（如论证不够强、rebuttal 逻辑关联弱）→ 老师快速确认（每条约 10-15 秒）
3. AI 标记为 **ESCALATE** 的（如原创性判断、实验设计科学性）→ 老师仔细审读原始论文（每条 1-2 分钟）

这样老师不需要从头通读 200 篇论文，而是从 AI 已经梳理好的问题列表出发。保守估计效率提升 5 倍：原本 200 小时（每篇 1 小时通读+批改）→ 40 小时（审核 AI 结果 + 聚焦 ESCALATE 项目）。这不是 10 倍的激进目标，而是务实可达的 5 倍提升。
