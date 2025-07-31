# ✨ Prompt 优化器

这是一个使用 Streamlit 和 Google Gemini API 构建的交互式 Prompt 优化工具。它能帮助您通过迭代反馈，系统地改进和优化您的大语言模型（LLM）Prompt。

## 核心功能

- **多会话管理**: 创建和管理多个独立的 Prompt 优化项目，每个项目都有自己的历史记录。
- **数据持久化**: 所有会话数据都保存在本地 SQLite 数据库 (`prompt_optimizer.db`) 中，刷新页面或重启应用后不会丢失。
- **迭代式优化**: 输入一个初始 Prompt，根据模型生成的响应提供反馈，工具会自动生成一个优化后的新版本 Prompt。
- **版本历史树**: 在每个会话中，所有的 Prompt 修改都会被记录在一个版本树中，您可以轻松地在不同版本之间切换和比较。
- **可配置模型**: 您可以自由选择用于生成响应的“目标模型”和用于优化 Prompt 的“优化模型”。
- **交互式界面**: 基于 Streamlit 构建，提供友好、直观的用户操作界面。

## 工作原理

本工具的核心思想是利用更强大的 LLM（优化模型）来根据人类的反馈（批评）去优化另一个 LLM（目标模型）的 Prompt。

1.  **输入初始 Prompt**: 您首先提供一个想要优化的初始 Prompt。
2.  **生成响应**: 工具使用您选择的“目标模型”来执行该 Prompt，并展示生成的响应。
3.  **提供反馈**: 您审查该响应。如果不满意，您可以写下具体的“批评”或改进建议。
4.  **自动优化**: 工具会将您的“初始 Prompt”、“模型响应”以及您的“批评”三者整合，发送给“优化模型”。
5.  **生成新 Prompt**: “优化模型”会理解您的意图，并生成一个经过改进的新 Prompt，旨在解决您在批评中指出的问题。
6.  **创建新版本**: 这个新 Prompt 会被添加为历史树中的一个新版本（分支），您可以继续在此基础上进行测试和优化。

## 安装与配置

1.  **克隆项目**
    ```bash
    git clone https://github.com/zongmi/prompt_optimizer.git
    cd prompt_optimizer
    ```

2.  **创建虚拟环境并安装依赖**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **配置环境变量**
    - 复制 `.env.example` 文件为 `.env`，或者直接创建一个新的 `.env` 文件。
    - 在 `.env` 文件中设置您的 Google Gemini API 密钥：
      ```
      GEMINI_API_KEY="YOUR_API_KEY_HERE"
      ```
    - （可选）您还可以配置特定的模型名称和基础 URL：
      ```
      TARGET_MODEL_NAME="gemini-pro"
      ALIGNING_MODEL_NAME="gemini-1.5-pro-latest"
      # GEMINI_BASE_URL="YOUR_CUSTOM_BASE_URL"
      ```

## 如何运行

确保您的虚拟环境已激活，然后运行以下命令：

```bash
streamlit run prompt_optimizer.py
```

应用将在您的本地浏览器中打开。
