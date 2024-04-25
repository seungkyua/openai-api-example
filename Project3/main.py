import os
import streamlit as st
from openai import OpenAI
from gpt_tools import download_youtube, transcribe_audio, text_segmentation, extract_image_frames, make_video_summary


# 사이드바 설정
with st.sidebar:
    st.sidebar.header('Sidebar')
    openai_api_key = st.text_input('API키를 입력하세요.', type="password", value="")
    if openai_api_key:
        client = OpenAI(api_key=openai_api_key)

# 메인 페이지 설정
st.header('유튜브 영상 요약 서비스 🤖')  # Korean characters for "The title of the main page"
url = st.text_input('URL:', '')  # 텍스트 입력란
summary_number = st.number_input('Summary number:', min_value=1)  # 숫자 입력란
summarize_button = st.button('Summarize')  # 요약 버튼 # True, False

# 요약 버튼을 누를 때의 작업
if summarize_button:

    folder_path = "./data"
    raw_data_path = folder_path + "/raw_data"

    # 데이터 삭제
    os.system(f"rm -rf {folder_path}/*")

    with st.spinner('영상 요약 중... 🚀'):
        ## gpt tools 코드를 이용하여 요약 작업을 수행 ## 
        # 1. 유튜브 영상 다운로드
        download_youtube(youtube_url=url, output_path=raw_data_path)
        # 2. 오디오를 텍스트로 변환(전사)
        text_segments = transcribe_audio(client, os.path.join(raw_data_path, "audio.m4a"))
        # 3. 텍스트 세그먼트로 나누기
        segment_info = text_segmentation(client, topic_num=summary_number, text_segments=text_segments)
        # 4. 비디오에서 이미지 프레임을 추출
        paragraphs = extract_image_frames(topic_start_end_info=segment_info, transcript_segments=text_segments, img_folder_path=folder_path, video_path=os.path.join(raw_data_path, "video.mp4"))
        # 5. 비디오 요약
        outputs = make_video_summary(client, paragraphs=paragraphs, img_folder_path=folder_path)
        ########################################
    
    # 요약 결과 출력
    for idx, output in enumerate(outputs):
        gpt_pick_img_index = int(output["image index"])+1
        col1, col2 = st.columns(2)
        with col1:
            st.image(os.path.join(folder_path, f"topic{idx+1}", f"output{gpt_pick_img_index}.png"), caption=f'주제 {idx+1}')
        with col2:
            st.write(output["summary"])
