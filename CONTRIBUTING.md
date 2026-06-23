# Contributing

## 开发环境设置

```bash
# 1. 克隆仓库
git clone <repo-url>
cd AcademicReviewer

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. 安装依赖（推荐用 requirements.txt；lock 文件仅供参考）
pip install -r requirements.txt

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env，填入至少一个 LLM API Key
```

## 启动服务

```bash
# 终端 1：后端 API
python run.py

# 终端 2：前端 Gradio
python -m app.gradio_app
```

浏览器访问 `http://127.0.0.1:7860`。

## 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行所有测试
python -m pytest tests/ -q

# 仅运行校准引擎测试
python -m pytest tests/test_calibration/ -q

# 仅运行 Agent 测试
python -m pytest tests/test_agents/ -q
```

## 项目架构

详见 [AI_HANDOFF.md](AI_HANDOFF.md)。

## 添加新竞赛

1. 打开 Gradio → "赛事管理" Tab → 填写表单 → 保存
2. 或手动编辑 `configs/competition_registry.json`
3. 如果竞赛类型还不存在，需创建对应的 structure_schema + evidence_patterns + style_guide JSON 文件

## 添加新 LLM Provider

1. 在 `app/llm/` 新建 `myprovider.py`
2. 继承 `LLMAdapter`，实现 `chat_json()` 和 `model_name()`
3. 在模块底部 `LLMFactory.register("myprovider", MyProviderAdapter)`
4. 在 `.env` 设置 `LLM_PROVIDER=myprovider` + 对应 API Key

## 提交规范

- 提交前运行 `pytest tests/ -q` 确保所有测试通过
- Commit message 使用中文，简明描述改动
- PR 合入前需有人 review 代码变更
