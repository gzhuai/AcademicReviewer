# Changelog

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
