환경 구축

```bat
py -3.14 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

설치 확인: 아래 명령어가 `Python 3.14.x`를 출력하면 됨.
```bat
.venv\Scripts\python --version
```

화면 조작

- 실행 시 전체화면으로 시작합니다.
- 메인·연습·게임 화면 어디서든 `F` 또는 `F11`을 누르면 전체화면으로, `Esc`를 누르면 일반 창 모드로 전환합니다.
- 게임 단어 카드는 36px 굵은 글씨와 가운데 정렬을 사용합니다. 작은 창에서는 글자가 잘리지 않도록 카드 최소 크기를 유지하며, 기존 스크롤 영역으로 전체 화면을 확인할 수 있습니다.