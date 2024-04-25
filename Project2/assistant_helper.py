import os
import sys
import json
import time

def list_assistants(client) -> dict:
    """
    List all the assistants in the account

    Args:
        client: OpenAI client object
    
    Returns:
        dict: {assistant_name: assistant_id}
    """
    my_assistants = client.beta.assistants.list(
        order="desc",
        limit="20",
    )
    return {assistant.name : assistant.id for assistant in my_assistants.data}

def create_thread(client):
    """
    Create a new thread

    Args:
        client: OpenAI client object
    
    Returns:
        thread: OpenAI thread object
    """
    thread = client.beta.threads.create() # 채워넣기
    return thread

def add_message_run(client, assistant_id, thread, user_message):
    """
    Add a message to the thread and run the assistant
    
    Args:
        client: OpenAI client object
        assistant_id: str
        thread: OpenAI thread object
        user_message: str
    
    Returns:
        run: OpenAI run object
    """

    # 채워넣기
    run = client.beta.threads.messages.create(
        thread_id = thread.id,
        role = "user",
        content = user_message
    )
    run = client.beta.threads.runs.create(
        thread_id = thread.id,
        assistant_id = assistant_id
    )
    return run

def wait_on_run(client, run, thread):
    """
    Wait for the run to finish

    Args:
        client: OpenAI client object
        run: OpenAI run object
        thread: OpenAI thread object
    
    Returns:
        run: OpenAI run object
    """
    # 채워넣기
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

def get_response_pretty_print(client, thread, verbose=True):
    """
    Get the response messages from the thread

    Args:
        client: OpenAI client object
        thread: OpenAI thread object
        verbose: bool
    
    Returns:
        messages: OpenAI message object
    """
    messages = client.beta.threads.messages.list(thread_id=thread.id, order="asc") # message의 create_timestamp 기준으로 오름차순 정렬
    if verbose:
        for m in messages:
            try:
                print(f"[{m.role}]: {m.content[0].text.value}\n\n")
            except:
                print(f"[{m.role}]: {m.content[0]}\n\n")
            
    return messages