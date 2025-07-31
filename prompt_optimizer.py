import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
import sqlite3
import json

load_dotenv()

# --- 数据库操作 ---
DB_FILE = "prompt_optimizer.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prompt_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            history TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_sessions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM prompt_sessions ORDER BY id DESC")
    sessions = c.fetchall()
    conn.close()
    return sessions

def create_session(name, history_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO prompt_sessions (name, history) VALUES (?, ?)", (name, json.dumps(history_data)))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_session_history(session_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT history FROM prompt_sessions WHERE id = ?", (session_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return None

def update_session_history(session_id, history):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE prompt_sessions SET history = ? WHERE id = ?", (json.dumps(history), session_id))
    conn.commit()
    conn.close()

# --- 后端逻辑函数 ---

def get_gemini_client(api_key: str, base_url: str = None):
    """
    初始化返回一个 Gemini 客户端。
    """
    http_options_args = {}
    if base_url:
        http_options_args['base_url'] = base_url
    
    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(**http_options_args) if http_options_args else None,
    )
    return client

def generate_content(client: genai.Client, model_name: str, prompt: str, temperature: float = 0.5) -> str:
    """
    使用给定的客户端、模型和 prompt 生成内容。
    """
    with st.spinner(f"正在向模型 '{model_name}' 发送请求..."):
        try:
            generation_config = genai_types.GenerateContentConfig(
                temperature=temperature,
                top_p=1,
                top_k=1,
                max_output_tokens=4096,
                safety_settings=[
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    ),
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    ),
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    ),
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    ),
                ]
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=generation_config
            )
            return response.text
        except Exception as e:
            st.error(f"调用 API 时发生错误: {e}")
            return None

def align_prompt_with_critique(
    client: genai.Client,
    aligning_model: str,
    initial_prompt: str,
    initial_response: str,
    critique: str
) -> str:
    """
    根据批评优化初始 Prompt。
    """
    alignment_prompt = f"""
# 任务：优化 Prompt

## 背景
我有一个初始 Prompt，它生成了一个我不完全满意的响应。现在我提供了一个批评，请根据这个批评来重写和优化初始 Prompt。

## 规则
- 新的 Prompt 应该能引导模型生成更符合批评内容的响应。
- 只返回优化后的 Prompt，不要包含任何额外的解释或文本。

## 输入

### 初始 Prompt:
{initial_prompt}

### 由初始 Prompt 生成的响应:
{initial_response}

### 对响应的批评:
{critique}

## 输出

### 优化后的 Prompt:
"""
    with st.spinner("正在对 Prompt 优化..."):
      optimized_prompt = generate_content(client, aligning_model, alignment_prompt, temperature=0.2)
      return optimized_prompt

# --- Streamlit UI ---

st.set_page_config(layout="wide")

st.title("✨ Prompt 优化器")

# --- 初始化 ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY 未设置，请在 .env 文件中或作为环境变量设置它。")
    st.stop()

base_url = os.getenv("GEMINI_BASE_URL")
aligning_model_name = os.getenv("ALIGNING_MODEL_NAME", "gemini-1.5-pro-latest")
target_model_name = os.getenv("TARGET_MODEL_NAME", "gemini-pro")

try:
    client = get_gemini_client(api_key, base_url)
except Exception as e:
    st.error(f"初始化 Gemini 客户端失败: {e}")
    st.stop()


# --- Session State 和数据库初始化 ---
init_db()

if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
    st.session_state.history_data = None

# --- UI 渲染函数 ---
def render_history_sidebar(history_data):
    st.sidebar.title("Prompt 历史树")
    if not history_data or not history_data.get("history"):
        st.sidebar.write("暂无历史记录")
        return

    history = history_data["history"]
    current_prompt_id = history_data["current_prompt_id"]

    history_items = list(history.items())[::-1]
    
    for index, (prompt_id, data) in enumerate(history_items):
        version_number = len(history_items) - index
        label = f"版本 {version_number}"
        
        if prompt_id == current_prompt_id:
            label += " (当前)"

        if st.sidebar.button(label, key=f"history_btn_{prompt_id}"):
            st.session_state.history_data["current_prompt_id"] = prompt_id
            update_session_history(st.session_state.current_session_id, st.session_state.history_data)
            st.rerun()

# --- 主界面 ---
st.sidebar.title("会话管理")

sessions = get_sessions()
session_options = {session[0]: session[1] for session in sessions}
session_options[0] = "--- 创建新会话 ---"

sorted_session_ids = sorted([sid for sid in session_options if sid != 0], reverse=True)
display_options = [f"{session_options[sid]} (ID: {sid})" for sid in sorted_session_ids]
display_options.append(session_options[0])

selected_display_option = st.sidebar.selectbox(
    "选择或创建会话",
    display_options,
    index=0
)

if selected_display_option == session_options[0]:
    new_session_name = st.sidebar.text_input("新会话名称", key="new_session_name")
    if st.sidebar.button("创建", key="create_session"):
        if new_session_name:
            initial_history = {
                "history": {}, "root_prompt_id": None, "current_prompt_id": None
            }
            new_id = create_session(new_session_name, initial_history)
            st.session_state.current_session_id = new_id
            st.session_state.history_data = initial_history
            st.rerun()
        else:
            st.sidebar.warning("请输入会话名称。")
else:
    selected_id = int(selected_display_option.split("(ID: ")[1][:-1])
    if st.session_state.current_session_id != selected_id:
        st.session_state.current_session_id = selected_id
        st.session_state.history_data = get_session_history(selected_id)
        st.rerun()


st.sidebar.title("配置")
target_model_name = st.sidebar.selectbox(
    "选择目标模型",
    ("gemini-2.5-pro", "gemini-2.5-flash"),
    index=0,
    key='target_model'
)
aligning_model_name = st.sidebar.selectbox(
    "选择优化模型",
    ("gemini-2.5-pro", "gemini-2.5-flash"),
    index=0,
    key='aligning_model'
)

if st.session_state.current_session_id:
    render_history_sidebar(st.session_state.history_data)


# --- 主流程 ---
if not st.session_state.current_session_id:
    st.info("请在左侧选择一个会话，或创建一个新会话以开始。")
else:
    history_data = st.session_state.history_data
    current_prompt_id = history_data.get("current_prompt_id")

    if not current_prompt_id:
        st.header("1. 输入初始 Prompt")
        initial_prompt_input = st.text_area("在这里输入你的初始 Prompt", height=150, key="initial_prompt")
        if st.button("开始优化", key="start_button"):
            if initial_prompt_input:
                prompt_id = os.urandom(8).hex()
                history_data["history"][prompt_id] = {
                    "prompt": initial_prompt_input,
                    "response": None,
                    "critiques": {},
                    "parent": None,
                    "children": []
                }
                history_data["root_prompt_id"] = prompt_id
                history_data["current_prompt_id"] = prompt_id
                update_session_history(st.session_state.current_session_id, history_data)
                st.rerun()
            else:
                st.warning("请输入一个初始 Prompt。")
    else:
        history = history_data["history"]
        current_data = history[current_prompt_id]

        st.header("当前 Prompt")
        st.markdown(f"```\n{current_data['prompt']}\n```")

        if current_data["response"] is None:
            response = generate_content(client, target_model_name, current_data["prompt"])
            if response:
                current_data["response"] = response
                update_session_history(st.session_state.current_session_id, history_data)
                st.rerun()
        
        if current_data["response"]:
            st.subheader("Prompt 响应")
            st.markdown(current_data["response"])

            critiques_dict = current_data.get("critiques", {})
            if critiques_dict:
                st.header("反馈历史")
                history_items = list(history.items())[::-1]
                id_to_version = {prompt_id: len(history_items) - index for index, (prompt_id, data) in enumerate(history_items)}

                for child_id, critique_text in critiques_dict.items():
                    child_version = id_to_version.get(child_id, "N/A")
                    if child_id in history:
                        with st.expander(f"基于此反馈生成了 **版本 {child_version}**"):
                            st.info(critique_text)

            st.header("提供反馈以优化")
            critique_input = st.text_area("输入你的批评或反馈...", height=100, key=f"critique_{current_prompt_id}")

            if st.button("优化 Prompt (创建新分支)", key=f"optimize_{current_prompt_id}"):
                if critique_input:
                    new_prompt_text = align_prompt_with_critique(
                        client=client,
                        aligning_model=aligning_model_name,
                        initial_prompt=current_data["prompt"],
                        initial_response=current_data["response"],
                        critique=critique_input
                    )
                    if new_prompt_text:
                        new_prompt_id = os.urandom(8).hex()
                        
                        history[current_prompt_id]["children"].append(new_prompt_id)
                        if "critiques" not in history[current_prompt_id]:
                            history[current_prompt_id]["critiques"] = {}
                        history[current_prompt_id]["critiques"][new_prompt_id] = critique_input
                        
                        history[new_prompt_id] = {
                            "prompt": new_prompt_text,
                            "response": None,
                            "critiques": {},
                            "parent": current_prompt_id,
                            "children": []
                        }
                        
                        history_data["current_prompt_id"] = new_prompt_id
                        update_session_history(st.session_state.current_session_id, history_data)
                        st.success("已创建新的 Prompt 分支！")
                        st.rerun()
                else:
                    st.warning("请输入反馈内容。")