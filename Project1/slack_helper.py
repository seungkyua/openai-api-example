import requests
slack_token = ""
channel_id = ""

def send_message_to_slack(text:str, channel_id:str=channel_id, slack_token:str=slack_token):
    url = 'https://slack.com/api/chat.postMessage'
    headers = {'Authorization': 'Bearer ' + slack_token}
    data = {'channel': channel_id, 'text': text}
    response = requests.post(url, headers=headers, data=data)
    return response.json()  # You can print or log the response to see if it was successful

if __name__ == "__main__":
    response = send_message_to_slack("Hello, world!")
    print(response)