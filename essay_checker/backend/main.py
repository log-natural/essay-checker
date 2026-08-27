from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="자소서 컨펌 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://essay-checker-frontend.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 환경변수
# =========================================================

BASE = Path(__file__).resolve().parent

# backend/.env 읽기
#load_dotenv(BASE / ".env")

API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip()

print("API KEY 확인:", bool(API_KEY))
print("사용 모델:", MODEL)


# =========================================================
# OpenAI
# =========================================================

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =========================================================
# 학교 데이터
# =========================================================

try:
    with open(BASE / "schools.json", encoding="utf-8") as f:
        SCHOOLS = json.load(f)

except FileNotFoundError:
    print("경고: schools.json을 찾을 수 없습니다.")
    SCHOOLS = []


# =========================================================
# 요청 데이터
# =========================================================

class ReviewRequest(BaseModel):
    school: str
    question: str = ""
    essay: str


# =========================================================
# 제한 내용
# =========================================================

FORBIDDEN = {
    "공인어학성적": [
        "TOEFL",
        "TOEIC",
        "TEPS",
        "HSK",
        "JLPT",
        "JPT",
        "OPIc",
        "오픽",
        "어학성적",
    ],

    "교외 수상실적": [
        "올림피아드",
        "경시대회",
        "교외 수상",
        "수상실적",
        "대회에서 수상",
    ],

    "교과 인증시험": [
        "TOPIK",
        "한자능력검정",
        "컴퓨터활용능력",
        "인증시험",
    ],

    "영재교육원": [
        "영재교육원",
    ],

    "부모의 사회·경제적 지위": [
        "아버지는",
        "어머니는",
        "아빠는",
        "엄마는",
        "부모님은",
        "아버지께서",
        "어머니께서",
    ],

    "인적 사항": [
        "제 이름은",
        "출신 중학교",
        "출신 고등학교",
    ],
}


# =========================================================
# 기본 API
# =========================================================

@app.get("/")
def root():
    return {
        "message": "자소서 컨펌 API가 실행 중입니다."
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "openai_installed": OpenAI is not None,
        "api_key_configured": bool(API_KEY),
        "model": MODEL,
    }


# =========================================================
# 학교 검색
# =========================================================

@app.get("/api/schools")
def schools(q: str = ""):
    q = q.strip().lower()

    if not q:
        return SCHOOLS[:12]

    return [
        school
        for school in SCHOOLS
        if q in school.get("name", "").lower()
    ][:12]


# =========================================================
# 기본적인 제한 내용 검사
# =========================================================

def local_checks(essay: str):
    found = []

    essay_lower = essay.lower()

    for category, words in FORBIDDEN.items():

        hits = [
            word
            for word in words
            if word.lower() in essay_lower
        ]

        if hits:
            found.append({
                "category": category,
                "text": ", ".join(hits),
                "explanation": (
                    "자기소개서 작성 시 제한될 수 있는 내용이 "
                    "포함되어 있는지 확인해봐."
                ),
                "questions": [
                    "이 내용이 실제 자기소개서에서 반드시 필요한 내용인지 생각해봐.",
                    "이 내용을 대신해서 학교생활이나 활동에서 직접 경험한 일을 설명할 수 있을까?",
                ],
            })

    return found


# =========================================================
# AI 프롬프트
# =========================================================

SYSTEM_PROMPT = """
너는 {school_info} 지원자의 자소서를 평가하는 면접관이다. 학교 홈페이지의 전형 요강과 자소서 내용을 바탕으로 지원자를 합격시킬지 말지를 판단하여 10점을 만점으로 하는 점수를 책정한다. 만약 책정 점수가 낮거나 불합격할 거라고 생각한다면, 그 이유도 함께 알려준다.

아래 원칙에 맞추어 자소서 수정 방향성을 제시한다.

1. 자기소개서 전체 수정본을 작성하지 않는다.
2. 학생이 하지 않은 경험을 만들어내도록 유도하지 않는다.
3. 경험을 과장하거나 부풀리도록 권하지 않는다.
4. 학생의 실제 경험과 생각을 존중한다.
5. 문제가 없는 문장은 억지로 수정하라고 하지 않는다.
6. 사소한 표현 차이를 지나치게 많이 지적하지 않는다.
7. 비속어, 혐오 표현, 오해의 소지가 있는 표현을 사용하지 않는다.
8. 마크다운 문법을 사용하지 않는다.

검토 항목:

1. 반복되는 표현에 대해서는 대체할 수 있는 유의어를 2~3개 제시한다.
2. 의미가 중첩되는 표현이 있다면 어떤 의미를 남기고 어떤 부분을 줄일지 설명한다.
3. 중의적인 표현이 있다면 독자가 어떻게 오해할 수 있는지 설명하고 수정 방향을 제시한다.
4. 문맥에 맞지 않는 단어가 있다면 문맥에 맞는 표현으로 바꾸는 방향을 설명한다.
5. 중간 내용이 생략되어 의미를 파악하기 어려운 부분이 있다면 어떤 정보를 보완하면 좋을지 설명한다.
6. 부수적인 표현이 지나치게 많은 문장은 핵심 내용을 남기는 방향을 제시한다.
7. 현대 국어 문법에 맞지 않는 표현을 지적한다.
8. 띄어쓰기 오류를 지적한다.
9. 비속어나 부적절한 표현이 있다면 수정 방향을 제시한다.
10. 한국어로 충분히 대체할 수 있는 일본어 잔재 표현이 있다면 대체 방향을 제시한다.
11. 지원 학교와 자소서 문항이 제공된 경우 그 맥락을 고려한다.

반복 표현에 대한 규칙:
단순히 같은 단어가 여러 번 등장한다는 이유만으로
반복 표현이라고 판단하지 않는다.
다음 중 하나에 해당할 때만 반복 표현으로 지적한다.
1. 거의 동일한 표현이 가까운 문장에서 반복되어 문장이 단조롭게 느껴지는 경우
2. 같은 의미의 표현이 불필요하게 반복되어 내용이 중복되는 경우
3. 특정 표현의 반복 때문에 글의 가독성이 실제로 떨어지는 경우

수정 우선순위:
높음: 의미가 잘못 전달되거나 문법적으로 명백한 문제가 있는 경우
중간: 문맥이 어색하거나 의미가 중복되어 수정할 가치가 있는 경우
낮음: 현재도 충분히 자연스럽지만 조금 더 다듬을 수 있는 경우
낮음 수준의 문제는 특별한 이유가 없다면 지적하지 않는다.

제한 내용에 대한 원칙:
다음 내용이 자기소개서에 포함되어 있다면
삭제하거나 다른 실제 경험으로 바꾸는 것을 권한다.

1. 올림피아드(KMO 등), 교내·외 각종 경시대회 등의 대회명 및 입상 실적, 영재교육원 교육 및 수료 여부 등
2. TOEFLㆍTOEICㆍTEPSㆍTESLㆍTOSELㆍPELT, HSK, JLPT 등 각종 어학인증시험 점수,   한국어(국어)ㆍ한자 등 능력시험 점수, 교과목의 점수·석차 등
3. 지원자 본인을 알 수 있는 이름, 출신중학교 등 인적사항을 암시하는 내용
4. 부모(친인척 포함)의 사회·경제적 지위를 암시하는 내용. 예) 부모 및 친인척의 구체적인 직장명이나 직위, 소득 수준 및 고비용 취미 활동(골프, 승마 등), 학교에서 주관하지 않은 모둠 및 프로젝트 활동(사설 학원 및 기관에서 추진하는 교과 관련 활동) 등 

대신 다음 예시와 같은 같은 질문을 제시한다.
'실제로 학교생활에서 비슷한 상황을 경험한 적이 있었을까?'
'그때 네가 직접 한 행동은 무엇이었을까?'
'그 과정에서 새롭게 알게 된 점은 무엇이었을까?'
'그 경험 이후 생각이나 행동이 어떻게 달라졌을까?'

질문은 실제 경험을 회상하도록 돕는 용도로만 사용한다.

말투:
중학생에게 설명하듯 자연스럽고 친절하게 작성한다.
지나치게 어려운 전문용어를 사용하지 않는다.

출력은 반드시 JSON 객체 하나만 반환한다.
JSON 이외의 설명은 절대 작성하지 않는다.

JSON 구조:

{
  "score": "점수/10"
  "summary": "전체적인 평가",
  "issues": [
    {
      "category": "반복 표현|문맥|표현|문법|띄어쓰기|중의적 표현|기타",
      "text": "문제가 되는 짧은 부분",
      "explanation": "왜 문제가 되는지",
      "direction": "어떤 방향으로 수정하면 좋을지",
      "alternatives": ["대안1", "대안2", "대안3"]
    }
  ],
  "restricted": [
    {
      "category": "분류",
      "text": "문제 내용",
      "explanation": "왜 확인이 필요한지",
      "questions": [
        "실제 경험을 돌아보는 질문1",
        "실제 경험을 돌아보는 질문2"
      ]
    }
  ],
  "questions": [
    "스스로 생각해볼 질문"
  ]
}

중요:
issues에는 실제로 수정할 가치가 있는 내용만 넣는다.
자소서 전체를 다시 작성하지 않는다.
원문의 문체를 존중한다.
문제가 없는 문장을 억지로 수정하지 않는다.
한두 단어가 반복되었다는 이유만으로 지적하지 않는다.
대체 표현이 꼭 필요한 경우에만 alternatives를 작성하고, 필요하지 않은 경우 여백으로 남겨둔다.
모든 응답은 한국어로 작성한다.
"""


# =========================================================
# AI 결과 정리
# =========================================================

def normalize_result(data):
    if not isinstance(data, dict):
        return {
            "summary": "AI가 분석 결과를 올바른 형식으로 반환하지 않았습니다.",
            "issues": [],
            "restricted": [],
            "questions": [],
        }

    result = {
        "summary": str(
            data.get("summary", "분석 결과가 없습니다.")
        ),

        "issues": (
            data.get("issues", [])
            if isinstance(data.get("issues", []), list)
            else []
        ),

        "restricted": (
            data.get("restricted", [])
            if isinstance(data.get("restricted", []), list)
            else []
        ),

        "questions": (
            data.get("questions", [])
            if isinstance(data.get("questions", []), list)
            else []
        ),
    }

    return result


# =========================================================
# OpenAI AI 분석
# =========================================================

def ai_review(req: ReviewRequest, school_info: dict):

    # OpenAI 패키지 확인
    if OpenAI is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "openai 패키지가 설치되어 있지 않습니다. "
                "터미널에서 pip install openai 를 실행해 주세요."
            ),
        )

    # API 키 확인
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "OPENAI_API_KEY를 찾을 수 없습니다. "
                "backend/.env 파일을 확인해 주세요."
            ),
        )

    try:

        client = OpenAI(api_key=API_KEY)

        user_prompt = f"""
지원 학교:
{req.school}

학교 분류:
{school_info.get("type", "정보 없음")}

학교 홈페이지:
{school_info.get("website", "정보 없음")}

자소서 문항:
{req.question if req.question.strip() else "(선택 입력 없음)"}

자기소개서:
{req.essay}
"""

        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_PROMPT,
            input=user_prompt,
        )

        text = response.output_text.strip()

        if not text:
            raise HTTPException(
                status_code=502,
                detail="AI가 빈 응답을 반환했습니다.",
            )

        # JSON 코드 블록이 혹시 포함된 경우 제거
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        try:
            data = json.loads(text)

        except json.JSONDecodeError:

            print("AI 원본 응답:")
            print(text)

            raise HTTPException(
                status_code=502,
                detail=(
                    "AI가 JSON 형식의 결과를 반환하지 않았습니다. "
                    "터미널의 AI 원본 응답을 확인해 주세요."
                ),
            )

        return normalize_result(data)

    except HTTPException:
        raise

    except Exception as e:

        # 터미널에는 실제 오류를 그대로 출력
        # 개발자가 원인을 확인할 수 있도록 하기 위한 부분
        print()
        print("=" * 60)
        print("OpenAI API 오류")
        print(repr(e))
        print("=" * 60)
        print()

        error_text = str(e)

        # -----------------------------------------------------
        # API 사용 한도 / 크레딧 부족
        # -----------------------------------------------------
        if (
            "insufficient_quota" in error_text
            or "credit_balance_exhausted" in error_text
            or "no credits remaining" in error_text.lower()
            or "429" in error_text
        ):
            raise HTTPException(
                status_code=429,
                detail="AI 컨펌을 사용할 수 없습니다. API 사용 한도를 확인해주세요."
            )

        # -----------------------------------------------------
        # API 키 관련 오류
        # -----------------------------------------------------
        if (
            "invalid_api_key" in error_text
            or "Incorrect API key" in error_text
            or "401" in error_text
        ):
            raise HTTPException(
                status_code=401,
                detail="AI 컨펌을 사용할 수 없습니다. API 키 설정을 확인해주세요."
            )

        # -----------------------------------------------------
        # 모델 관련 오류
        # -----------------------------------------------------
        if (
            "model_not_found" in error_text
            or "does not exist" in error_text
        ):
            raise HTTPException(
                status_code=502,
                detail="AI 컨펌을 사용할 수 없습니다. 설정된 AI 모델을 확인해주세요."
            )

        # -----------------------------------------------------
        # 그 외 예상하지 못한 오류
        # -----------------------------------------------------
        raise HTTPException(
            status_code=502,
            detail="AI 컨펌 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )


# =========================================================
# 자기소개서 컨펌
# =========================================================

@app.post("/api/review")
def review(req: ReviewRequest):

    # 자기소개서 확인
    if not req.essay.strip():
        raise HTTPException(
            status_code=400,
            detail="자기소개서를 입력해 주세요.",
        )

    # 학교 확인
    if not req.school.strip():
        raise HTTPException(
            status_code=400,
            detail="지원 학교를 입력해 주세요.",
        )

    # 학교 정보 찾기
    school_info = next(
        (
            school
            for school in SCHOOLS
            if school.get("name") == req.school.strip()
        ),
        {
            "name": req.school.strip(),
            "type": "학교 정보 없음",
            "website": "",
        },
    )

    # 제한 내용 기본 검사
    restricted = local_checks(req.essay)

    # AI 분석
    result = ai_review(
        req,
        school_info,
    )

    # 기본 검사 결과와 AI 결과 합치기
    existing_restricted = result.get("restricted", [])

    result["restricted"] = (
        restricted + existing_restricted
    )[:20]

    return {
        "school": school_info,
        "result": result,
    }


# =========================================================
# 실행 확인용
# =========================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
