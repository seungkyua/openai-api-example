import os
import sys
import json
import base64
import subprocess
import yt_dlp
import openai

def download_youtube(youtube_url:str, output_path:str="./data/raw_data") -> None:
    """
    Download audio and video files from youtube video url

    youtube_url: youtube video url
    output_path: path to save the downloaded audio and video files
    """
    os.makedirs(output_path, exist_ok=True) # 폴더 생성 코드 추가
    output_path_audio = os.path.join(output_path, "audio.m4a")
    output_path_video = os.path.join(output_path, "video.mp4")

    # Define download options
    ydl_opts_audio = {
        'format': 'bestaudio/best',
        'outtmpl': output_path_audio,
    }

    ydl_opts_video = {
        'format': 'bestvideo/best',
        'outtmpl': output_path_video,
    }
    
    # Use yt-dlp to download the audio
    with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
        ydl.download([youtube_url])
    print("Audio Downloaded Successfully!")

    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
        ydl.download([youtube_url])
    print("Video Downloaded Successfully!")

def transcribe_audio(client, audio_path:str) -> list:
    """
    Transcribe audio file using OpenAI API
    
    client: OpenAI client
    audio_path: path to the audio file
    
    return: list of transcribed text segments
    """

    audio_file = open(audio_path, "rb")

    transcript = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-1",
        response_format="verbose_json",
        timestamp_granularities=["segment"]
        )
    
    # post-process the transcript
    erase_keys = ['id', 'seek', 'tokens', 'temperature', 'avg_logprob', 'compression_ratio', 'no_speech_prob']
    for x in transcript.segments:
        for k in erase_keys:
            del x[k]

    return transcript.segments

def run_gpt(client, model:str, messages:list, max_token:int=150, temperature:float=0.7, is_json:bool=False, seed:int=None, tools:list=None, tool_choice:str=None, stream:bool=False):

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_token,
        temperature=temperature,
        response_format = {'type' : 'json_object'} if is_json else {'type' : 'text'},
        seed=seed,
        tools=tools,
        tool_choice="auto" if tools else tool_choice,
        stream=stream
    )
    
    return response

def text_segmentation(client, topic_num:int, text_segments:list) -> dict:
    """
    Segment text segments into topic groups using OpenAI API

    client: OpenAI client
    text_segments: list of text segments
    topic_num: number of topics to be segmented

    return: dict of topic groups with start and end timestamps
    """

    # 코드 추가
    system_message = "Json Format: {'0' : {'start' : {start timestamp}, 'end' : {end timestamp}}, ...}" 
    user_message = f"""
    삼중 따옴표 안에 영상의 대본 텍스트가 리스트 형태로 담겨있어.
    텍스트를 보고 문맥적으로 유사한 하위 텍스트 그룹 {topic_num}개가 생성될 수 있도록 topic segmentation 을 진행해줘.
    텍스트 그룹은 반드시 비슷한 문맥 또는 하나의 주제로 묶어야 해.
    또한 텍스트 그룹간에 겹치는 부분이 없어야 해.
    텍스트 그룹을 분리한 후에는 그룹의 시작과 끝 timestmap를 제공된 JSON Format으로 반환해줘.
    JSON Format의 key에는 텍스트 그룹의 인덱스가, value에는 JSON이 들어가야 해.
    Value Json은 'stat' key에 텍스트 그룹의 시작 timestamp가, 'end' key에 텍스트 그룹의 종료 timestamp 를 넣어줘야 해.

    \"\"\"{text_segments}\"\"\"
    """
    model = "gpt-4-turbo"
    max_token = 1000
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

    response = run_gpt(client, model, messages, max_token, is_json=True, temperature=0.1, seed=100)
    segment_info = json.loads(response.choices[0].message.content)

    return segment_info

def seconds2hmd(x:float) -> str:
    """
    Convert seconds to hh:mm:ss format
    
    x: seconds
    
    return: time format in hh:mm:ss"""

    # Convert total_seconds to an integer since we're dealing with time
    total_seconds = int(x)

    # Calculate hours, minutes, and seconds
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format the time into hh:mm:ss
    time_format = "{:02}:{:02}:{:02}".format(hours, minutes, seconds)

    return time_format

def extract_image_frames(topic_start_end_info:dict, transcript_segments:list, img_folder_path:str, video_path:str, number_pic_per_topic:int=3) -> list:
    """
    Extract image frames from video based on the topic start and end timestamps
    
    topic_start_end_info: dict of topic groups with start and end timestamps
    transcript_segments: list of text segments
    img_folder_path: path to save the extracted images
    video_path: path to the video file
    number_pic_per_topic: number of images to be extracted per topic

    return: list of paragraph segments
    """

    paragraphs = []
    for i, timestamp_item in enumerate(topic_start_end_info.values()):
        s,e = timestamp_item["start"], timestamp_item["end"]
        
        # split segment
        ADD_FLAG = False
        for segment in transcript_segments:
            if segment["start"] == s:
                paragraphs.append([]) # 새로운 paragraph segment 생성
                ADD_FLAG=True

            if ADD_FLAG:
                paragraphs[-1].append(segment) # segment를 담기

            if segment["end"] == e: # timestamp end를 만나면 해당 루프 종료
                break
                
        # format timestamp
        s_format, e_format = seconds2hmd(s), seconds2hmd(e)

        # image extraction
        cur_img_dir = os.path.join(img_folder_path, f"topic{i+1}")
        os.makedirs(cur_img_dir, exist_ok=True) # 폴더 생성
        
        fps_ratio = number_pic_per_topic / round(e-s) # 예를 들어 30초 분량이라고 하면, 10초마다 1 이미지씩 생성.
        command = f"ffmpeg -ss {s_format} -to {e_format} -i '{video_path}' -vf \"fps={fps_ratio}\" \"{cur_img_dir}/output%d.png\""
        subprocess.run(command, shell=True)

        print(f"Paragraph {i+1} sucess!")
    return paragraphs

def encode_image(image_path:str) -> str:
  """
  Encode image to base64 format
  
  image_path: path to the image file
  
  return: base64 encoded image
  """

  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def make_video_summary(client, paragraphs:list, img_folder_path:str):
    """
    Generate response for each paragraph segment
    
    paragraphs: list of paragraph segments
    img_folder_path: path to the image folder
    
    return: list of generated responses from all paragraph segments
    """

    outputs = []
    for i in range(len(paragraphs)):
        # 코드 추가
        image_outputs = []
        cur_dir = f"{img_folder_path}/topic{i+1}"
        for file_name in os.listdir(cur_dir):
            if file_name.endswith(".png"):
                encoded_image = encode_image(os.path.join(cur_dir, file_name))
                image_outputs.append({"type" : "image_url", "image_url" : {"url" : "data:image/png;base64,"+encoded_image}})

        transcription = "".join([item["text"] for item in paragraphs[i]])
        system_message = """
            너는 비디오의 대본과 이미지를 보고 핵심을 요약하는 비서야. Json Format: {"image index" : {image index number}, "summary" : {summary text}}
        """

        user_message = f"""
            삼중 따옴표 안에 비디오의 특정 구간의 대본 텍스트를 제공할.
            메시지에 비디오에서 구간 별로 추출한 3개의 썸네일 이미지를 보고 입력된 순서대로 0부터 시작해서 순차적으로 이미지 인덱스를 생성해줘.
            먼저, 비디오의 주제를 가장 잘 설명하는 이미지를 선택하고 이미지 인덱스 번호를 반환해줘.
            다음으로, 비디오의 전체 맥락을 가장 잘 설명하는 요약본을 작성해줘. 요약은 한국어로 작성하되, 대본에서 중용한 정보는 모두 포함해줘.
            그리고 요약본에는 반드시 대표 이미지에 대한 설명도 포함시켜줘.

            \"\"\"{transcription}\"\"\"
        """

        model = "gpt-4-turbo"
        max_token = 2000
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": [{"type" : "text", "text" : user_message}] + image_outputs}
        ]

        response = run_gpt(client, model, messages, max_token, is_json=True)
        outputs.append(json.loads(response.choices[0].message.content))

    return outputs