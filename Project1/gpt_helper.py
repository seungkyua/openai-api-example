import os
import sys
import json
import requests
from slack_helper import send_message_to_slack

RapidAPI_KEY = os.environ.get("RAPIDAPI_KEY", "5e2236446emshb04ffd7cef7d164p1f7f37jsnf92bac5a8714") # set juptyer notebook system variable

def postprocessing_news_data(news_data:dict) -> dict:
    """
    API 응답에서 뉴스 데이터 후처리

    Args:
    news_data (dict): 뉴스 API의 응답

    Returns:
    dict: 뉴스 제목을 키로, 스니펫을 값으로 하는 딕셔너리 반환
    """
    snippets = {}
    for item in news_data['items']:
        cur_snippet = "Main Content: "+item["snippet"]+ "\nURL: "+item["newsUrl"]
        if item["hasSubnews"]:
            cur_snippet += "\nSub Content: "
            for sub_item in item["subnews"]:
                cur_snippet += " " + sub_item["snippet"]
        snippets[item["title"]] = cur_snippet
    return snippets

def call_news_api(category:str, language_location:str) -> dict:
    """
    뉴스 API 호출

    Args:
    category (str): 뉴스 카테고리
    language_location (str): 뉴스의 언어 및 위치

    Returns:
    dict: 뉴스 제목을 키로, 스니펫을 값으로 하는 딕셔너리 반환
    """
    assert category in ["entertainment", "world", "business", "health", "science", "sport", "technology"], "category should be one of 'entertainment', 'world', 'business', 'health', 'science', 'sport', 'technology'"
    url = "https://google-news13.p.rapidapi.com/" + category

    assert language_location in ["ko-KR", "en-US"], "language_location should be one of 'ko-KR', 'en-US'"
    querystring = {"lr":language_location}

    headers = {
		"X-RapidAPI-Key": RapidAPI_KEY,
		"X-RapidAPI-Host": "google-news13.p.rapidapi.com"
	}

    response = requests.get(url, headers=headers, params=querystring)
    # print(f"API run successful: {len(response.json()['items'])} news items found.")
    output = postprocessing_news_data(response.json())
    return output

def execute_function_call(message) -> dict:
    """
    GPT 응답에서 함수 호출 실행

    Args:
    message (dict): GPT 응답의 메시지

    Returns:
    dict: 뉴스 제목을 키로, 스니펫을 값으로 하는 딕셔너리 반환
    """
    # 함수 호출 및 결과 처리 로직 구현
    if message.tool_calls[0].function.name == "call_news_api":
        cat = json.loads(message.tool_calls[0].function.arguments)["category"]
        lang = json.loads(message.tool_calls[0].function.arguments)["language_location"]
        results = call_news_api(cat, lang)
    elif message.tool_calls[0].function.name == "send_message_to_slack":
        text = json.loads(message.tool_calls[0].function.arguments)["text"]
        results = send_message_to_slack(text)
    return results

def run_gpt(client, model:str, messages:list, max_token:int=150, temperature:float=0.7, is_json:bool=False, seed:int=None, tools:list=None, tool_choice:str=None, stream:bool=False):
    """
    GPT 모델 실행

    Args:
    client (object): API 클라이언트 객체
    model (str): 모델 식별자
    messages (list): GPT에 전달할 메시지 목록
    max_token (int): 최대 토큰 수
    temperature (float): 생성 다양성 조절
    is_json (bool): 응답 형식이 JSON인지 여부
    seed (int): 결과 재현성을 위한 시드
    tools (list): 사용할 도구 목록
    tool_choice (str): 도구 선택 방법
    stream (bool): 스트리밍 모드 사용 여부

    Returns:
    object: GPT 응답 객체
    """
    # GPT 실행 및 응답 반환 로직 구현
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

def generate_news_summary(client, user_prompt:str, news_result:dict, model:str):
    """
    이 함수는 사용자의 입력을 받아 GPT 모델을 이용하여 관련 뉴스를 요약하여 반환합니다.
    주어진 뉴스 데이터를 기반으로 사용자가 이해하기 쉽게 주요 뉴스 주제를 요약하고,
    각 뉴스의 구체적인 정보와 원본 URL을 포함한 요약본을 생성합니다.

    Args:
    client (object): GPT 모델을 호출하기 위한 클라이언트 인스턴스.
    user_prompt (str): 사용자로부터 입력받은 프롬프트 문자열. 사용자의 관심사와 언어 정보가 포함되어 있습니다.
    selected_topic (str): 사용자가 선택한 뉴스의 주제.
    news_result (dict): API로부터 받은 뉴스 데이터 딕셔너리로 call_news_api 함수의 결과 값입니다.
    model (str): 사용할 GPT 모델의 식별자.

    Returns:
    generator: 요약된 뉴스 내용을 순차적으로 반환하는 제너레이터. 각 청크는 특정 뉴스 아이템의 요약을 포함합니다. (yield 사용)

    주요 작업:
    1. 시스템 메시지를 설정하여 GPT에 전달할 목적을 정의합니다. 여기서는 '뉴스 앵커' 역할을 수행하도록 설정.
    2. 사용자 메시지를 포맷하여 GPT에 전달할 입력을 생성합니다. 이 메시지에는 사용자의 요구 사항과 API로부터 받은 뉴스 데이터가 포함됩니다.
    3. 'run_gpt' 함수를 호출하여 GPT 모델을 실행합니다. 이 때, 필요한 매개변수를 전달하며 스트리밍 모드를 사용하여 응답을 받습니다.
    4. 응답받은 데이터를 순차적으로 처리하여 외부로 반환합니다. 각 청크에서는 뉴스의 요약 정보가 포함되어 있습니다.
    """
    system_message = "너는 사람들의 관심에 맞는 오늘의 뉴스를 간결하고 재미있게 요약해서 전달하는 뉴스 앵커야."# 뉴스 앵커로서 관심사에 맞는 뉴스 요약 제공 역할 부여
    user_message = f"""
    유저의 관심 주제와 원하는 언어는 {user_prompt}이야.
    
    아래 삼중 따옴표 안에 오늘의 뉴스를 제공할게.  
    Key는 뉴스의 제목, Value는 뉴스 내용으로 구성되어 있어.
    다양한 주제 중 너가 가장 중요하다고 생각되는 대표적인 주제 7가지를 뽑아서 내가 이해하기 쉽도록 비슷한 주제끼리 묶어서 요약해줘.
    단, 요약을 할 땐 일반적인 내용이 아닌 구체적인 정보를 포함해서 제공해야해.
    사용자가 읽기 쉽도록 위트를 섞어서 재미있게 정보를 전달해줘.
    원본 뉴스 URL 정보를 요약본에 반드시 함께 제공해줘.

    \"\"\"{news_result}\"\"\"
    """
    max_token = 3000
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    response = run_gpt(client, model, messages, max_token, stream=True)
    for chunk in response:
        yield chunk.choices[0].delta.content
        

def run_news_summary(client, user_prompt:str, messages:list):
    """
    뉴스 요약 실행

    Args:
    client (object): API 클라이언트 객체
    user_prompt (str): 사용자 프롬프트
    messages (list): GPT에 전달할 메시지 목록

    Returns:
    str: 뉴스 요약 결과
    """
    # 뉴스 요약 로직 구현
    # 뉴스 스니펫 생성 후 generate_news_summary 함수를 실행해 최종 요약 결과를 반환

    system_message = "너는 유저가 입력한 요청을 보고 적절한 function을 불러주는 유능한 비서야."# RapidAPI를 통해 관심사에 맞는 뉴스 찾는 역할 부여
    user_message = f"""
    만약 유저 메세지가 관심 주제와 언어-지역 정보를 포함하고 있다면, RapidAPI 가이드라인을 참고해서 뉴스 데이터를 가져오는 function을 불러줘.
    만약 유저 메세지가 Slack 메시지를 보내고 싶어라고 요청하면, Slack API를 사용해서 메시지를 보내는 function을 불러줘.

    # RapidAPI 가이드라인

    ## 유저 메시지
    {user_prompt}
    
    ## Guideline
    너는 다음 단계에 따라서 뉴스 요약본을 생성해줘.
    1. 나의 관심 주제를 보고 이를 [entertainment, world, business, health, science, sports, technology] 중 하나로 변환해줘.
    2. 변환된 뉴스 카테고리와 내가 설정한 언어를 기반으로 RapidAPI를 사용해서 뉴스 데이터를 가져와줘.

    # Slack API 가이드라인

    ## 유저 메시지
    {user_prompt}

    ## Message History
    {messages}

    ## Guideline
    너는 Message History에서 assiatant message 중에서 마지막 content (뉴스 요약본)을 Slack 메시지로 보내줘.
    """
    model = "gpt-4-turbo"
    max_token = 3000
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    tools = [
        { # OpenAPI schema
        "type" : "function",
        "function": {
                "name": "call_news_api",
                "description": "call news_api with the given category", # function의 description을 보고 실행할 함수를 결정
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "news cateogry to get the news. list of categories: entertainment, world, business, health, science, sports, technology"
                        },
                        "language_location": {
                            "type": "string",
                            "description": "language and location of the news. default is 'ko-KR'. list of language and location: 'en-US', 'ko-KR'"
                        }
                    },
                    "required": ["category", "language_location"],
                },
        } 
        },
        { # OpenAPI schema
        "type" : "function",
        "function": {
                "name": "send_message_to_slack",
                "description": "send the message to Slack", # function의 description을 보고 실행할 함수를 결정
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "text to send to Slack"
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "channel id to send the message"
                        },
                        "slack_token": {
                            "type": "string",
                            "description": "Slack bot token id"
                        }
                    },
                    "required": ["text"],
                },
        } 
        }
    ]
    response = run_gpt(client, model, messages, max_token, tools=tools)
    assistant_message = response.choices[0].message
    assistant_message.content = str(assistant_message.tool_calls[0].function) 
    messages.append({"role": assistant_message.role, "content": assistant_message.content})

    if assistant_message.tool_calls:
        results = execute_function_call(assistant_message)
        messages.append({"role": "tool", "tool_call_id": assistant_message.tool_calls[0].id, "name": assistant_message.tool_calls[0].function.name, "content": results})

    # function 이름에 따라서 결과를 처리(후처리)하는 로직을 추가
    if assistant_message.tool_calls[0].function.name == "call_news_api":
        return generate_news_summary(client, user_prompt, news_result=results, model=model)
    elif assistant_message.tool_calls[0].function.name == "send_message_to_slack":
        return results
