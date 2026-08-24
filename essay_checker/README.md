# 자소서 컨펌받기

## 실행

1. Python 3.10 이상을 설치합니다.
2. `backend` 폴더에서 가상환경을 만들고 의존성을 설치합니다.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

3. `backend/.env.example`을 `.env`로 복사하고 `OPENAI_API_KEY`를 입력합니다.
4. 백엔드 실행:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

5. `frontend/index.html`을 브라우저에서 엽니다. 로컬 파일 정책 때문에 브라우저에 따라 API 요청이 제한되면 별도 정적 서버를 사용하세요.

예:

```bash
cd frontend
python -m http.server 5500
```

그 뒤 `http://127.0.0.1:5500` 접속.

## 포트폴리오 링크

`frontend/index.html`의 `YOUR_PORTFOLIO_URL`을 실제 포트폴리오 주소로 바꿉니다.

## 참고

이 예제의 학교 목록은 시작용 데이터입니다. 실제 서비스에서는 최신 학교 목록과 학교별 공식 입학전형 자료를 별도로 관리하세요.

API 키는 프론트엔드에 넣지 말고 백엔드 환경변수로만 관리하세요.
