# openai-api-example
2024년 4월 openai api 교육 샘플 코드

- chatgpt 영어 배우기 동영상: https://www.youtube.com/watch?v=QMnKZYX39Aw

# 환경 설정
```
1. virtualenv 로 환경 만들기
$ mkvirtualenv openapi-api


2. jupyter notebook 설치
$ pip install notebook


3. IPython kernel 설치
$ pip install ipykernel


4. kernel 에 openapi-api 가상환경 붙히기
$ python -m ipykernel install --user --name openapi-api --display-name "Python (openapi-api)"

5. openai 설치
$ pip install -U openai

6. ffmpeg 다운로드
https://ffmpeg.org/download.html
$ mv ffmpeg ~/bin


7. urllib3 다운그레이드
$ pip install 'urllib3<2.0'
```