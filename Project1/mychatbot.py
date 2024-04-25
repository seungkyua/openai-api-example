import streamlit as st
from gpt_helper import run_news_summary
from openai import OpenAI

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password", value="")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"
    client = OpenAI(api_key=openai_api_key)

st.title("📰 News For You")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "안녕하세요! 관심 있는 주제와 언어를 알려주세요. 오늘의 주요 뉴스를 요약해드립니다. 🌟"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

prompt = st.chat_input("답변을 입력해주세요.")
if prompt:
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    msg_generator = run_news_summary(client, prompt, st.session_state.messages)
    with st.chat_message("assistant"):
        assistant_msg = st.write_stream(msg_generator)
    st.session_state.messages.append({"role": "assistant", "content": assistant_msg})