# AcademicReviewer 改进计划

> **基于**: PROJECT_ASSESSMENT.md 评估报告（2026-06-10）
> **目标**: 消除竞赛类型偏差，让系统在所有类型的报告提交类竞赛中有效且公平
> **当前状态**: v0.6.0 — Phase 1-4 全部完成，仅剩 3 个低频优化项（pytest-asyncio 兼容/数据库迁移/配置热加载）
> **最后更新**: 2026-06-13

---

## 概览

本计划聚焦项目评估中识别的**四个层面的偏差来源**，按影响优先级排列：

| # | 改进项 | 影响 | 优先级 | 工作量 | 状态 |
|---|--------|------|--------|--------|------|
| 1 | 校准引擎按竞赛类型切换特征集 | 消除最大偏差源 | P0 | 2-3 天 | ✅ 完成 |
| 2 | Agent 权重按竞赛类型可配置 | 评分公平性 | P0 | 1 天 | ✅ 完成 |
| 3 | A4 加载并使用 style_guides | 语言审查学科差异 | P1 | 1 天 | ✅ 完成 |
| 4 | 校准引擎 FEATURE_TO_CONFIG_MAP 按类型分离 | 配置建议正确性 | P1 | 1 天 | ✅ 完成 |
| 5 | 安全加固（认证+上传限制+隐私声明） | 生产就绪 | P1 | 1 天 | ✅ 完成 |
| 6 | A3 type_hints 从代码移到配置文件 | 代码质量 | P2 | 0.5 天 | ✅ 完成 |
| 7 | 其他技术债务清理 | 可持续性 | P2-P3 | 2 天 | ✅ 完成（subprocess/lock/CHANGELOG/CONTRIBUTING/死代码清理已完成） |

---

## 改进 1: 校准引擎按竞赛类型切换特征集 (P0)

### 问题

`app/calibration/feature_extractor.py` 的 `feature_names()` 返回全局统一的 21 个特征。其中 8 个是纯科研专用（has_p_value, has_effect_size, has_control_group, has_sample_size 等）。对 John Locke 等非科研竞赛运行时，这些特征全是 0.0，不但无法产生有效的效应量，还会污染报告。

更严重的是 `generate_fatal_defect_updates()` 可能建议把「缺少 p 值」标记为致命缺陷——对 ISEF 合理，对 John Locke 是灾难。

### 方案

#### Step 1: 在 feature_extractor.py 中定义按类型分组的特征

```python
# app/calibration/feature_extractor.py

FEATURES_BY_TYPE = {
    "research": [
        "word_count", "avg_sentence_length", "sentence_length_std",
        "citation_density", "passive_voice_ratio", "vocabulary_diversity",
        "logical_marker_density", "transition_frequency",
        "avg_paragraph_length", "section_coverage",
        "has_p_value", "has_effect_size", "has_control_group", "has_sample_size",
        "evidence_diversity_score", "evidence_source_count", "claim_count_estimate",
        "hook_sentence_present", "gap_statement_present",
        "limitations_section_present", "future_work_mentioned",
    ],
    "research_advanced": [
        # Same as research
        ...
    ],
    "discursive": [
        "word_count", "avg_sentence_length", "sentence_length_std",
        "citation_density",  # still relevant
        "vocabulary_diversity",  # more important for essays
        "logical_marker_density",  # critical — tracks "therefore", "however" etc
        "transition_frequency",  # critical — argument flow
        "avg_paragraph_length", "section_coverage",
        "evidence_diversity_score", "evidence_source_count",
        "claim_count_estimate",
        "hook_sentence_present",  # important for discursive essays
        "gap_statement_present",
        "future_work_mentioned",
        # NOTE: NO has_p_value, has_effect_size, has_control_group, has_sample_size
    ],
    "math_modeling": [
        "word_count", "avg_sentence_length", "sentence_length_std",
        "citation_density", "vocabulary_diversity",
        "logical_marker_density", "transition_frequency",
        "avg_paragraph_length", "section_coverage",
        "has_sample_size",  # relevant: data N=
        "evidence_diversity_score", "evidence_source_count",
        "gap_statement_present", "limitations_section_present",
        "future_work_mentioned",
    ],
    "social_science": [
        # Similar to research but without hard quantitative requirements
        ...
    ],
    "history": [
        "word_count", "avg_sentence_length", "sentence_length_std",
        "citation_density", "vocabulary_diversity",
        "logical_marker_density", "transition_frequency",
        "avg_paragraph_length", "section_coverage",
        "evidence_diversity_score", "evidence_source_count",
        "claim_count_estimate", "hook_sentence_present",
        "gap_statement_present", "future_work_mentioned",
        # NOTE: no p_value, effect_size, control_group, sample_size
        # NOTE: limitations_section_present not typically required for history
    ],
    "finance": [
        "word_count", "avg_sentence_length", "sentence_length_std",
        "citation_density", "vocabulary_diversity",
        "logical_marker_density", "transition_frequency",
        "avg_paragraph_length", "section_coverage",
        "evidence_diversity_score", "evidence_source_count",
        "claim_count_estimate",
        "gap_statement_present", "limitations_section_present",
        "future_work_mentioned",
    ],
    "business_case": [
        "word_count", "avg_sentence_length", "sentence_length_std",
        "citation_density", "vocabulary_diversity",
        "logical_marker_density", "transition_frequency",
        "avg_paragraph_length", "section_coverage",
        "evidence_diversity_score", "evidence_source_count",
        "claim_count_estimate", "hook_sentence_present",
        "gap_statement_present", "future_work_mentioned",
    ],
}

# Updated function: accept competition_type parameter
def feature_names(competition_type: str = "research") -> list[str]:
    """Return the feature names relevant to the given competition type."""
    return FEATURES_BY_TYPE.get(competition_type, FEATURES_BY_TYPE["research"])
```

#### Step 2: 在 engine.py 中传递 competition_type

```python
# app/calibration/engine.py

def run_calibration(..., competition_type: str, ...):
    fnames = feature_names(competition_type)  # was: feature_names()
    ...
```

#### Step 3: 在校准 API/Gradio UI 中确保 competition_type 正确传递

已有的 `competition_type` 参数已经在传递——只需确保 `feature_names()` 调用方都传入该参数。

#### Step 4: 为每种类型构造 fatal_defect 的白名单

```python
# app/calibration/diff_generator.py

# 原来硬编码的 binary_features 应该按类型区分
BINARY_FEATURES_BY_TYPE = {
    "research": ["has_p_value", "has_effect_size", "has_control_group",
                  "has_sample_size", "gap_statement_present",
                  "limitations_section_present"],
    "discursive": ["hook_sentence_present", "gap_statement_present"],
    "math_modeling": ["has_sample_size", "gap_statement_present",
                      "limitations_section_present"],
    # ...
}
```

#### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `app/calibration/feature_extractor.py` | 添加 `FEATURES_BY_TYPE`，修改 `feature_names()` |
| `app/calibration/diff_generator.py` | 添加 `BINARY_FEATURES_BY_TYPE`，修改 `generate_fatal_defect_updates()` |
| `app/calibration/engine.py` | 传递 `competition_type` 给 `feature_names()` 和 diff 函数 |
| `cli/calibrate.py` | 确保 `competition_type` 参数传递到 `run_calibration()` |
| `tests/test_calibration/test_feature_extractor.py` | 为每种类型添加特征数量验证测试 |
| `tests/test_calibration/test_diff_generator.py` | 为每种类型添加 fatal_defect 测试 |

#### 验证

```bash
# 确认 research 类型有 21 个特征，discursive 类型不含 has_p_value 等
pytest tests/test_calibration/ -v -k "feature"

# 确认对 John Locke 论文跑校准时不会出现 p 值相关建议
python cli/calibrate.py --competition "John Locke" --type discursive ...
```

---

## 改进 2: Agent 权重按竞赛类型可配置 (P0)

### 问题

当前 `app/orchestrator.py` 中的 `AGENT_WEIGHTS` 对所有竞赛类型完全相同。但科研型论文的证据权重应该更高，思辨型论文的结构权重应该更高。

### 方案

#### Step 1: 在 competition_registry.json 中添加 agent_weights

```json
// configs/competition_registry.json
{
  "competitions": {
    "ISEF": {
      "type": "research",
      "agent_weights": {
        "RubricParser": 0.20,
        "StructureLogic": 0.15,
        "ArgumentEvidence": 0.30,
        "LanguageStyle": 0.15,
        "AcademicIntegrity": 0.20
      }
    },
    "John Locke": {
      "type": "discursive",
      "agent_weights": {
        "RubricParser": 0.15,
        "StructureLogic": 0.30,
        "ArgumentEvidence": 0.25,
        "LanguageStyle": 0.15,
        "AcademicIntegrity": 0.15
      }
    }
    // ... 每个竞赛都可以有自己的权重
  }
}
```

#### Step 2: 在 orchestrator.py 中读取权重

```python
# app/orchestrator.py

# 默认权重作为 fallback
DEFAULT_AGENT_WEIGHTS = {
    "RubricParser": 0.25,
    "StructureLogic": 0.20,
    "ArgumentEvidence": 0.25,
    "LanguageStyle": 0.15,
    "AcademicIntegrity": 0.15,
}

class Orchestrator:
    def _get_agent_weights(self, competition: str) -> dict:
        """Load agent weights from competition config, fall back to defaults."""
        comp_config = self.lookup_competition(competition)
        weights = comp_config.get("agent_weights", {})
        if weights:
            return weights
        return DEFAULT_AGENT_WEIGHTS

    def _compute_total_score(self, report: ReviewReport) -> float | None:
        weights = self._get_agent_weights(report.competition)
        # ... rest uses weights dict instead of module-level AGENT_WEIGHTS
```

#### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `configs/competition_registry.json` | 为每个竞赛添加 `agent_weights` 字段 |
| `app/orchestrator.py` | 用 `_get_agent_weights()` 替代模块级 `AGENT_WEIGHTS` |
| `tests/test_calibration/test_diff_generator.py` | 确保向后兼容（无 agent_weights 时用默认值） |

---

## 改进 3: A4 LanguageStyle 加载并使用 style_guides (P1)

### 问题

`configs/style_guides/` 有 6 个 JSON 文件（social_science.json, discursive.json, history.json 等），但 A4 agent 并没有加载它们。当前 prompt (`a4_language_style.txt`) 对所有类型用同样的审查标准，忽视了学科间语言规范的根本差异。

### 方案

#### Step 1: 让 Orchestrator 在调用 A4 时传入 style guide

```python
# app/orchestrator.py (in review() method)

# Load style guide based on competition type
style_template = comp_config.get("style_template", "")
style_guide = {}
if style_template:
    style_path = CONFIGS_DIR / "style_guides" / style_template
    if style_path.exists():
        style_guide = json.loads(style_path.read_text(encoding="utf-8"))

# Pass to A4
self._get_agent(LanguageStyleAgent).run(
    document_text=doc.text,
    style_guide=style_guide,  # ← previously not passed
)
```

#### Step 2: 增强 A4 prompt 以利用 style guide

在 `a4_language_style.txt` 中添加 type-aware 指导：

```
【风格审查原则 — 根据提供的风格指南调整权重】

- 科研论文 (tech_academic): 被动语态可接受，强调精确性和术语一致性。
  Iron Law 例外：被动→主动转换只做建议，不做修改。
  
- 商科提案 (biz_proposal): 语言应有说服力。被动语态过多是问题。
  Iron Law 例外：可以建议句子结构重组以增强说服力。
  
- 思辨论文 (discursive): 修辞精度至关重要。句子结构就是论证工具。
  关注逻辑连接词的精确性和论证节奏。
```

#### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `app/orchestrator.py` | `review()` 方法中加载 style_guide 并传给 A4 |
| `prompts/a4_language_style.txt` | 添加类型感知的风格审查指导 |
| `configs/style_guides/*.json` | 审查并完善各风格的审查标准 |

---

## 改进 4: 校准引擎配置映射按类型分离 (P1)

### 问题

`FEATURE_TO_CONFIG_MAP` 是全局统一的。加上改进 1 的特征集按类型切换后，这个映射也需要相应调整——一个映射不可能同时适用于「科研特征 → 科研配置」和「思辨特征 → 思辨配置」。

### 方案

```python
# app/calibration/engine.py

FEATURE_TO_CONFIG_MAP_BY_TYPE = {
    "research": {
        "citation_density": "evidence_standards.min_total_citations",
        "has_p_value": "quantitative_requirements.expects_p_value",
        # ... 原有的 16 个映射
    },
    "discursive": {
        "citation_density": "evidence_standards.min_total_citations",
        "logical_marker_density": "logic_checks.min_logical_markers_per_1000w",
        "transition_frequency": "logic_checks.min_transitions_per_1000w",
        "vocabulary_diversity": "style_vocabulary.min_ttr",
        "claim_count_estimate": "argument_standards.min_distinct_claims",
        "hook_sentence_present": "structure_requirements.requires_hook",
        "gap_statement_present": "logic_checks.gap_statement_required",
        "evidence_diversity_score": "evidence_standards.min_source_types",
        "section_coverage": "required_sections.coverage_ratio",
        "avg_sentence_length": "style_sentence.target_sentence_length",
        "sentence_length_std": "style_sentence.max_std",
        "avg_paragraph_length": "style_paragraph.target_paragraph_length",
        # NO has_p_value, has_effect_size, has_control_group, has_sample_size
    },
    # ... 其他类型
}

# engine.py 中根据 competition_type 选择映射
config_mapping = FEATURE_TO_CONFIG_MAP_BY_TYPE.get(competition_type,
    FEATURE_TO_CONFIG_MAP_BY_TYPE["research"])
changes = generate_rule_updates(effect_sizes, fnames, config_mapping, cfg_data)
```

#### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `app/calibration/engine.py` | 将 `FEATURE_TO_CONFIG_MAP` 改为按类型分组的 dict |

---

## 改进 5: 安全加固 (P1)

### 5.1 API 认证 (Bearer Token)

```python
# app/main.py
from fastapi import Depends, HTTPException, Header

async def verify_token(authorization: str = Header(None)):
    if settings.api_token:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing token")
        token = authorization[7:]
        if token != settings.api_token:
            raise HTTPException(status_code=403, detail="Invalid token")
    # If no token configured, allow all (backward compatible)

# Apply to all /api/v1/* routes via dependency
app = FastAPI(dependencies=[Depends(verify_token)])
```

```env
# .env
API_TOKEN=your-secret-token  # 留空则跳过认证（向后兼容）
```

### 5.2 文件上传限制

```python
# app/main.py

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

@router.post("/api/v1/review")
async def review_document(file: UploadFile = File(...)):
    # Check extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {suffix}")
    
    # Check size by reading into buffer
    contents = await file.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 50MB)")
    # ... write to temp file
```

### 5.3 隐私声明

在 README.md 和 Gradio 界面添加：
- 说明学生论文会发送到所选 LLM 提供商的 API 进行评审
- 建议不要上传包含个人敏感信息的学生作品
- 对数据保留政策做说明

---

## 改进 6: A3 type_hints 移到配置文件 (P2)

### 问题

`app/agents/argument_evidence.py:23-31` 的 8 种类型提示硬编码在代码中。

### 方案

```json
// configs/competition_type_hints.json
{
  "research": {
    "name_cn": "科研型论文",
    "checks": [
      "hypothesis 可验证性",
      "p值/效应量",
      "控制组",
      "统计检验",
      "局限性讨论"
    ],
    "skip": ["counterargument", "rebuttal"]
  },
  "discursive": {
    "name_cn": "思辨型议论文",
    "checks": [
      "counterargument 质量",
      "rebuttal 强度",
      "逻辑链完整性",
      "哲学引用深度"
    ],
    "skip": []
  },
  // ... 其他类型
}
```

然后 `argument_evidence.py` 从 JSON 加载：

```python
def _load_type_hints(self):
    path = CONFIGS_DIR / "competition_type_hints.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
```

---

## 改进 7: 其他技术债务 (P2-P3)

| 改进项 | 说明 | 优先级 | 状态 |
|--------|------|--------|------|
| `subprocess` → 直接调用 | `gradio_app.py` 中校准功能用 `subprocess.run` 调 CLI，改为直接调 `run_calibration()` | P3 | ✅ 完成 |
| requirements-lock.txt | 用 `pip freeze` 生成精确版本锁文件 | P2 | ✅ 完成 |
| Changelog | 添加 `CHANGELOG.md`，从 git log 反向生成 | P3 | ✅ 完成 |
| Contributing 指南 | 添加 `CONTRIBUTING.md` 说明开发环境设置、运行测试、提 PR 流程 | P3 | ✅ 完成 |
| 数据库迁移 | 从 `create_all()` 迁移到 Alembic 或至少记录 schema 变更 | P3 | 未开始 |
| 配置热加载 | 检测 JSON 文件修改时间，自动刷新缓存 | P3 | 未开始 |
| pytest-asyncio 兼容 | Python 3.14 下 11 个 async 测试失败，需修复 | P2 | 🆕 待处理 |

---

## 执行顺序建议

### ✅ 第一批 (已完成): 消除偏差的核心改进

1. **改进 1**: 校准引擎特征集按类型切换 ✅
2. **改进 2**: Agent 权重按类型可配置 ✅

### ✅ 第二批 (已完成): 质量提升

3. **改进 3**: A4 加载 style_guides ✅
4. **改进 4**: 校准引擎配置映射按类型分离 ✅

### ⚠️ 第三批 (部分完成): 安全与完善

5. **改进 5**: 安全加固（认证+文件限制 ✅，隐私声明待验证）
6. **改进 6**: type_hints 移到配置文件 ✅
7. **改进 7**: 技术债务清理（subprocess/lock/CHANGELOG/CONTRIBUTING ✅，数据库迁移/pytest-asyncio 待做）

### 🆕 第四批 (新增 — v0.4.0 目标): 提升 LLM 判断质量

详见配套文档 **[HUMAN_AGENT_COLLABORATION.md](HUMAN_AGENT_COLLABORATION.md)**。

| # | 改进项 | 影响 | 优先级 | 工作量 |
|---|--------|------|--------|--------|
| 8 | Prompt 标杆案例（每种竞赛类型 2-3 对"好/差"样本注入 few-shot） | 直接提升 LLM 判断质量 | P0 | 2 天 | ✅ 已完成（知识卡系统 + ISEF+JL 示例） |
| 9 | 反馈分级与置信度标签（Agent 输出 confidence/substitutability） | 让老师知道哪些需要人工审核 | P1 | 1 天 | ✅ 已完成（Phase 2: confidence_engine.py + prompt 扩展 + annotation_builder 分级显示） |
| 10 | 老师知识卡系统（领域检查清单 + 阈值红线 JSON schema） | 弥补 L4 领域深度差距 | P1 | 1-2 天 | ✅ 已完成（与 #8 合并） |
| 11 | 人类反馈闭环（老师审核 → 数据收集 → 置信度校准） | 系统自我优化 | P2 | 2-3 天 | ✅ 已完成（Phase 3: TeacherFeedback ORM + 审核 API + Gradio 教师审核 Tab + 反馈统计） |
| 12 | A3 quantitative_check 按类型动态输出 | 消除非科研类型输出噪声 | P1 | 0.5 天 | ✅ 已完成（已在 competition_type_hints.json 中按类型配置 applicable 字段） |
| 13 | A3 推理链分解增强 | 思辨型/社科型/历史型论证深度分析 | P1 | 1 天 | ✅ 已完成（Phase 4: prompt 增强 Premise→Conclusion→Missing Step→Why Critical） |
| 14 | 学生水平自适应 | 按字数/复杂度调整反馈粒度 | P2 | 1 天 | ✅ 已完成（Phase 4: app/utils/student_level.py + Orchestrator 集成） |
| 15 | 知识卡自动更新建议 | 反馈数据驱动的知识卡优化 | P2 | 0.5 天 | ✅ 已完成（Phase 4: GET /api/v1/feedback/suggestions + Gradio 面板） |
| 16 | 专家经验全竞赛覆盖 | 7 种竞赛类型专家经验示例 | P2 | 1 天 | ✅ 已完成（Phase 4: CTB/NHD/SIC/FBLA 4 个新文件） |
| 17 | 修复 pytest-asyncio 兼容性 | Python 3.14 async 测试 | P2 | 4-6 小时 | 待开始 |
| 18 | 数据库迁移 | Alembic 方案 | P3 | 0.5 天 | 未开始 |
| 19 | 配置热加载 | 自动检测并刷新缓存 | P3 | 0.5 天 | 未开始 |
| 20 | 速率限制 | FastAPI middleware | P2 | 2 小时 | 未开始 |
| 21 | 学生水平中文适配 | 当前 TTR 基于英文分词 | P2 | 0.5 天 | 未开始 |
| 22 | 知识卡质量自动化检查 | 上线前验证必填项完整性 | P3 | 0.5 天 | 未开始 |

---

## 验证方法（更新）

每次改进后应通过以下方式验证：

```bash
# 1. 现有 177 个测试仍然通过
pytest tests/ -v

# 2. 对每种竞赛类型跑一次完整 e2e 测试（需要 API Key）
python tests/test_e2e.py  # ISEF 对照
# 手动测试: John Locke / HiMCM / FBLA 的评审

# 3. 对非科研竞赛跑校准引擎，确认不再出现科研专用建议
python cli/calibrate.py \
  --competition "John Locke" \
  --type discursive \
  --winners data/calibration/jl_winners \
  --losers data/calibration/jl_losers
# 检查报告中无 has_p_value / has_control_group 相关建议

# 4. 确认各竞赛类型的权重生效
# 提交 John Locke 论文评审 → 检查 total_score 计算中 Structure 权重是否高于 ISEF
```
