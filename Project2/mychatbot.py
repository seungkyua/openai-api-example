import streamlit as st
from assistant_helper import list_assistants, create_thread, add_message_run, wait_on_run, get_response_pretty_print
from openai import OpenAI

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password", value="")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    st.session_state = {}
    if openai_api_key:
        client = OpenAI(api_key=openai_api_key)
        # 계정의 모든 assistant를 가져와 st.selectbox에 넣기
        # 채워 넣기
        st.session_state["open_api_key"] = openai_api_key
        assistant_name2id = list_assistants(client)
        assistant_name = st.selectbox("Assistant 를 선택하세요.", assistant_name2id.keys()) # 유저가 선택한 assistant_name
        st.write(f"당신은 {assistant_name}을 선택했군요! ") 
        assistant_id = assistant_name2id[assistant_name] # 유저가 선택한 assistant_id
        st.session_state["assistant_id"] = assistant_id
        st.session_state["assistant_name"] = assistant_name

st.title("Ask Me Anything! 🤖")

if st.session_state.get("open_api_key", None) and st.session_state.get("assistant_id", None):
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": f"안녕하세요! 저는 {st.session_state['assistant_name']}입니다. 무엇을 도와드릴까요? 🤖"}]
        # thread 생성
        thread = create_thread(client) # 채워 넣기
        st.session_state["thread"] = thread

    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    prompt = st.chat_input("질문을 입력하세요.")
    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # user의 prompt를 assistant에게 전달 (message 생성 후 run)
        run = add_message_run(client, assistant_id, thread, prompt) # 채워 넣기
        run = wait_on_run(client, run, thread) # 채워 넣기
        messages = get_response_pretty_print(client, thread, verbose=True) # 채워 넣기
        
        with st.chat_message("assistant"):
            if messages.data[-1].content[0].type == "image_file":
                file_id = messages.data[-1].content[0].image_file.file_id
                image_encoded = client.files.content(file_id).content
                st.image(image_encoded)
                st.session_state["messages"].append({"role": "assistant", "content": file_id})
            elif messages.data[-1].content[0].type == "text":
                st.write(messages.data[-1].content[0].text.value)
                st.session_state["messages"].append({"role": "assistant", "content": messages.data[-1].content[0].text.value})