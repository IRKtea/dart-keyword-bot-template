# 📊 DART 공시 키워드 알림 봇

DART(전자공시시스템)에 신규 공시가 올라올 때, 미리 등록한 키워드(회사명)와 매칭되면 **Google Chat으로 알림**을 보내주는 자동 봇입니다.

- ⏰ **10분마다 자동 실행** (운영시간: 평일 09:00~20:00)
- 💰 **완전 무료** (GitHub Actions, Google Sheets, DART API 모두 무료 티어 활용)
- 🔧 **코드 수정 없이** Google Sheets에서 키워드만 추가/수정
- 📱 휴대폰/PC 어디서든 Google Chat으로 실시간 알림 수신

---
## 🎯 알림 예시
```
📊 [DART] 삼성전자
[코스피] (005930) | 2026-05-06

공시 제목
주요사항보고서(자기주식취득결정)

매칭된 키워드
삼성전자

접수번호
20260506000123

[ DART에서 원문 보기 ]
```
---

## 📋 사전 준비물

셋업하기 전에 다음이 필요합니다:

- **Google 계정** (Gmail)
- **GitHub 계정** ([github.com](https://github.com)에서 무료 가입)
- **휴대폰** (DART API 키 발급 시 본인인증)

총 셋업 소요 시간: **약 30~45분**

---
## 🚀 셋업 가이드

### 1단계. 이 템플릿으로 본인 저장소 만들기
1. 이 페이지 우측 상단 **"Use this template"** → **"Create a new repository"** 클릭
2. 입력:
   - **Repository name**: 자유롭게 (예: `my-dart-bot`)
   - **Visibility**: **Private** ⚠️ (★중요)
3. **"Create repository"** 클릭

---

### 2단계. DART API 키 발급
1. [https://opendart.fss.or.kr](https://opendart.fss.or.kr) 접속 → **회원가입**
2. 로그인 후 상단 **"인증키 신청/관리"** → **"인증키 신청"**
3. 양식 작성 (활용 목적: 개인 모니터링) → **신청** (즉시 승인)
4. **"인증키 관리"**에서 발급된 키 복사 → 메모장에 보관

> 💡 발급된 키는 40자 영문/숫자 문자열입니다.

---

### 3단계. Google Chat 스페이스 + 웹훅 만들기
1. [https://chat.google.com](https://chat.google.com) 접속
2. 좌측 **스페이스** → **➕** → **"스페이스 만들기"**
   - 이름: `DART 공시 알림` (자유)
3. 만든 스페이스 → 상단 이름 클릭 → **"앱 및 통합"** → **"웹훅 추가"**
   - 이름: `DART 봇`
4. **"저장"** 클릭 → 생성된 웹훅 URL 복사 → 메모장에 보관

> ⚠️ **웹훅 URL은 비밀번호처럼 다루세요.** 외부 노출 시 누구나 본인 스페이스에 메시지 전송 가능.

---
### 4단계. Google Sheets 키워드 시트 만들기
1. [https://sheets.google.com](https://sheets.google.com) 접속 → **빈 스프레드시트** 만들기
2. 시트 이름: `DART 키워드` (자유)
3. **A1 셀**에 `keyword` 입력 (헤더)
4. **A2 셀부터** 모니터링할 회사명을 한 줄에 하나씩 입력
5. 브라우저 주소창의 URL에서 **Spreadsheet ID 복사**:
```
   https://docs.google.com/spreadsheets/d/[이 부분이 ID]/edit ~
```
   메모장에 보관.
---

### 5단계. Google Cloud 프로젝트 + 서비스 계정 만들기
봇이 Google Sheets를 읽으려면 Google Cloud의 인증 정보가 필요합니다.

#### 5-1. Cloud Console 접속 & 프로젝트 생성
1. [https://console.cloud.google.com](https://console.cloud.google.com) 접속 (Google Sheets와 같은 계정)
2. 상단 좌측 **"프로젝트 선택"** → **"새 프로젝트"**
3. 프로젝트 이름: `dart-bot` (자유) → **만들기**
4. 생성 완료 후 상단 드롭다운에서 방금 만든 프로젝트 선택

> 💡 결제 계정 등록은 **불필요**합니다. (무료 티어 사용)

#### 5-2. Google Sheets API 활성화
1. 상단 검색창에 `Google Sheets API` 입력 → 검색 결과 클릭
2. **"사용 설정"** 버튼 클릭 (1분 정도 대기)

#### 5-3. 서비스 계정 만들기
1. 좌측 메뉴 ☰ → **"API 및 서비스"** → **"사용자 인증 정보"**
2. 상단 **"+ 사용자 인증 정보 만들기"** → **"서비스 계정"**
3. 입력:
   - 서비스 계정 이름: `dart-bot-account`
   - 나머지: 자동 채워짐
4. **"만들기 및 계속"** → **역할 선택 건너뛰기** ("계속") → **"완료"**

#### 5-4. JSON 키 다운로드
1. 방금 만든 서비스 계정 **클릭**
2. 상단 **"키"** 탭 → **"키 추가"** → **"새 키 만들기"** → **JSON** → **만들기**
3. JSON 파일이 자동 다운로드됨 → **안전하게 보관** (비밀번호와 동일 취급)

#### 5-5. 서비스 계정 이메일 복사 후 Sheets에 공유
1. 서비스 계정 화면에서 이메일 주소 복사 (예: `dart-bot-account@xxx.iam.gserviceaccount.com`)
2. **Google Sheets로 돌아가서** → 우측 상단 **"공유"**
3. 복사한 이메일 붙여넣기 → 권한: **"뷰어"** → **"알림 보내기" 체크 해제** → **"공유"**

---
### 6단계. GitHub Secrets 등록
본인의 봇 저장소(1단계에서 만든 것) → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

다음 4개를 등록:
| Name | Secret 값 |
|---|---|
| `DART_API_KEY` | 2단계에서 발급받은 DART API 키 |
| `GOOGLE_CHAT_WEBHOOK_URL` | 3단계에서 복사한 웹훅 URL |
| `SPREADSHEET_ID` | 4단계에서 복사한 Spreadsheet ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 5-4에서 다운로드한 JSON 파일 **내용 전체** |

> 💡 **JSON 파일 여는 법**: 파일 우클릭 → 메모장(Windows) 또는 텍스트 편집기(Mac)로 열기 → 전체 내용(`{` 부터 `}` 까지) 복사

---

### 7단계. 봇 실행 및 확인
1. 본인 저장소 → 상단 **"Actions"** 탭
2. (안내 메시지가 뜨면) **"I understand my workflows, go ahead and enable them"** 클릭
3. 좌측 **"DART Keyword Bot"** 선택
4. 우측 **"Run workflow"** → 초록 **"Run workflow"** 클릭
5. 30초~1분 후 실행 결과 확인:
   - 🟢 초록색 (성공): OK
   - 🔴 빨간색 (실패): 로그 확인 후 [트러블슈팅](#-트러블슈팅) 참고
> ⚠️ **첫 실행은 알림이 가지 않습니다.** 첫 실행은 "현재 시점 기록"용이고, **다음 실행부터 신규 공시 알림**이 시작됩니다.

---

## ✅ 셋업 완료 후
- 봇은 **자동으로 10분마다 실행**됩니다 (평일 09:00~20:00)
- 키워드 수정/추가는 **Google Sheets에서 직접** (재시작 불필요)
- 컴퓨터를 꺼도 봇은 GitHub 서버에서 계속 작동
- 자동화 안정까지 2~3일 소요

### 키워드 추가/수정
1. 4단계에서 만든 Google Sheets 열기
2. A열에 키워드 추가/삭제
3. 다음 실행(최대 10분 후)부터 자동 반영
> 💡 즉시 적용하려면 GitHub Actions에서 **Run workflow** 수동 실행

---
## 🔧 트러블슈팅

### ❌ "KeyError: 'DART_API_KEY'" 또는 비슷한 에러
→ Secret 이름 오타 확인. **대소문자 정확히** 일치해야 함.

### ❌ "DART API 키 오류 (status=011)"
→ DART_API_KEY 값이 잘못됨. Open DART 사이트에서 키 재확인.

### ❌ "Google Sheets API has not been used in project"
→ 5-2 단계의 Google Sheets API 활성화가 안 됨. 활성화 후 1~2분 대기 후 재실행.

### ❌ "googleapiclient.errors.HttpError: 403"
→ 5-5 단계의 시트 공유가 안 됨. 서비스 계정 이메일이 시트에 **뷰어**로 추가됐는지 확인.

### ❌ 첫 실행 후 알림이 안 와요
→ 정상입니다. **첫 실행은 알림 안 보내고**, 다음 실행부터 신규 공시 알림이 옵니다. 10분 더 기다려보세요.

### ❌ 자동 실행이 안 돌아요
→ GitHub Actions의 자동 스케줄은 **첫 24시간 동안 들쭉날쭉**할 수 있습니다. 그때까지는 **Run workflow** 수동 실행으로 보충하세요.

### ❌ 알림이 너무 많이 와요
→ 키워드를 더 좁혀주세요. 예: `삼성` → `삼성전자` (`삼성`은 삼성SDS, 삼성중공업 등 다 매칭됨)

### ❌ 알림이 안 와요 (특정 공시)
→ DART에 그 공시가 정말 등록됐는지 [DART 사이트](https://dart.fss.or.kr)에서 확인. 회사명 띄어쓰기/철자 확인.

---
## 📝 라이선스

MIT License

자유롭게 사용/수정/배포 가능. 책임은 사용자에게 있습니다.

---

## 🤝 도움이 필요하면

이 템플릿 작성자에게 문의: [본인 GitHub 또는 이메일 적기]
