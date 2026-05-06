"""
DART 공시 키워드 모니터링 봇 (배포 버전)
- 10분마다 실행되어 DART 신규 공시 확인
- Google Sheets에 등록된 키워드(회사명) 매칭 시 Google Chat으로 알림
- 운영시간: 평일 9시~20시 (한국 시간 기준)

설정 방법: README.md 참고
"""

import os
import json
import re
import sys
import requests
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ============ 필수 환경변수 검증 ============
REQUIRED_ENV_VARS = [
    'DART_API_KEY',
    'GOOGLE_CHAT_WEBHOOK_URL',
    'SPREADSHEET_ID',
    'GOOGLE_SERVICE_ACCOUNT_JSON',
]

missing_vars = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
if missing_vars:
    print("=" * 60)
    print("❌ 필수 환경변수가 누락되었습니다!")
    print("=" * 60)
    for v in missing_vars:
        print(f"  - {v}")
    print()
    print("GitHub Secrets에 위 값들을 모두 등록해주세요.")
    print("자세한 방법: README.md 참고")
    print("=" * 60)
    sys.exit(1)

# ============ 설정값 ============
DART_API_KEY = os.environ['DART_API_KEY']
GOOGLE_CHAT_WEBHOOK_URL = os.environ['GOOGLE_CHAT_WEBHOOK_URL']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']

# ============ DART API ============
DART_LIST_URL = 'https://opendart.fss.or.kr/api/list.json'

# ============ 운영 시간 (한국 시간 기준) ============
KST = timezone(timedelta(hours=9))
WORK_START_HOUR = 9
WORK_END_HOUR = 20

# ============ 마지막 처리 공시 접수번호 저장 파일 ============
STATE_FILE = 'last_rcept_no.json'


def get_keywords_from_sheets():
    """Google Sheets에서 키워드(회사명) 목록 가져오기"""
    try:
        creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    except json.JSONDecodeError:
        print("❌ GOOGLE_SERVICE_ACCOUNT_JSON 형식 오류")
        print("   JSON 파일 내용 전체를 정확히 복사했는지 확인하세요.")
        sys.exit(1)
    
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=creds)
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='A2:A1000'
        ).execute()
    except Exception as e:
        print(f"❌ Google Sheets 접근 실패: {e}")
        print()
        print("확인할 점:")
        print("  1. SPREADSHEET_ID가 정확한가?")
        print("  2. 서비스 계정 이메일에 시트 '뷰어' 권한이 있는가?")
        print("  3. Google Sheets API가 활성화되어 있는가?")
        sys.exit(1)
    
    rows = result.get('values', [])
    keywords = [row[0].strip() for row in rows if row and row[0].strip()]
    print(f"[키워드 로드] {len(keywords)}개: {keywords}")
    return keywords


def normalize(text):
    """대소문자/공백 무시 비교를 위한 정규화"""
    if not text:
        return ''
    return re.sub(r'\s+', '', text.lower())


def find_matching_keywords(corp_name, report_nm, keywords):
    """회사명 또는 공시 제목에 키워드가 있는지 확인"""
    target = normalize(corp_name) + normalize(report_nm)
    matched = []
    for keyword in keywords:
        if normalize(keyword) in target:
            matched.append(keyword)
    return matched


def load_last_rcept_no():
    """이전 실행에서 처리한 마지막 접수번호 가져오기"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('last_rcept_no', '')
    return ''


def save_last_rcept_no(rcept_no):
    """마지막 처리한 접수번호 저장"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'last_rcept_no': rcept_no,
            'updated_at': datetime.now(KST).isoformat()
        }, f, ensure_ascii=False, indent=2)


def is_working_hour():
    """현재가 운영시간(9시~20시 한국시간)인지 확인"""
    now = datetime.now(KST)
    return WORK_START_HOUR <= now.hour < WORK_END_HOUR


def fetch_dart_list():
    """오늘 DART 공시 전체 가져오기"""
    today = datetime.now(KST).strftime('%Y%m%d')
    all_disclosures = []
    page_no = 1
    page_count = 100
    
    while True:
        params = {
            'crtfc_key': DART_API_KEY,
            'bgn_de': today,
            'end_de': today,
            'page_no': page_no,
            'page_count': page_count,
        }
        try:
            response = requests.get(DART_LIST_URL, params=params, timeout=30)
            data = response.json()
        except Exception as e:
            print(f"❌ DART API 호출 실패: {e}")
            return []
        
        status = data.get('status')
        if status != '000':
            if status == '013':
                # 데이터 없음 (정상)
                break
            elif status in ('010', '011'):
                print(f"❌ DART API 키 오류 (status={status})")
                print("   DART_API_KEY가 올바른지 확인하세요.")
                print("   Open DART 사이트(https://opendart.fss.or.kr)에서 키 재발급 가능합니다.")
                sys.exit(1)
            elif status == '020':
                print(f"⚠️ DART API 일일 호출 한도 초과 (20,000건)")
                return []
            else:
                print(f"⚠️ DART API 오류: status={status}, message={data.get('message')}")
                break
        
        items = data.get('list', [])
        all_disclosures.extend(items)
        
        total_page = data.get('total_page', 1)
        if page_no >= total_page:
            break
        page_no += 1
    
    print(f"[DART] 오늘({today}) 공시 총 {len(all_disclosures)}건 수신")
    return all_disclosures


def send_to_google_chat(disclosure, matched_keywords):
    """Google Chat으로 카드 형식 알림 전송"""
    corp_name = disclosure.get('corp_name', '')
    report_nm = disclosure.get('report_nm', '').strip()
    rcept_no = disclosure.get('rcept_no', '')
    rcept_dt = disclosure.get('rcept_dt', '')
    stock_code = disclosure.get('stock_code', '')
    corp_cls = disclosure.get('corp_cls', '')
    
    market_label = {
        'Y': '코스피', 'K': '코스닥', 'N': '코넥스', 'E': '기타'
    }.get(corp_cls, corp_cls)
    
    if len(rcept_dt) == 8:
        rcept_dt_fmt = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}"
    else:
        rcept_dt_fmt = rcept_dt
    
    dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
    
    subtitle_parts = [f"[{market_label}]"]
    if stock_code:
        subtitle_parts.append(f"({stock_code})")
    subtitle_parts.append(f"| {rcept_dt_fmt}")
    subtitle = ' '.join(subtitle_parts)
    
    card = {
        "cardsV2": [{
            "cardId": f"dart-{rcept_no}",
            "card": {
                "header": {
                    "title": f"📊 [DART] {corp_name}",
                    "subtitle": subtitle
                },
                "sections": [{
                    "widgets": [
                        {"decoratedText": {
                            "topLabel": "공시 제목",
                            "text": report_nm,
                            "wrapText": True
                        }},
                        {"decoratedText": {
                            "topLabel": "매칭된 키워드",
                            "text": ', '.join(matched_keywords),
                            "wrapText": True
                        }},
                        {"decoratedText": {
                            "topLabel": "접수번호",
                            "text": rcept_no
                        }},
                        {"buttonList": {"buttons": [{
                            "text": "DART에서 원문 보기",
                            "onClick": {"openLink": {"url": dart_url}}
                        }]}}
                    ]
                }]
            }
        }]
    }
    
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json=card, timeout=10)
        if response.status_code == 200:
            print(f"  ✓ 알림 전송: {corp_name} - {report_nm[:30]}")
        else:
            print(f"  ✗ 알림 전송 실패: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"  ✗ 알림 전송 예외: {e}")


def main():
    print(f"\n{'='*60}")
    print(f"DART 봇 실행 시작: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    print(f"{'='*60}\n")
    
    if not is_working_hour():
        print(f"운영시간(09:00~20:00)이 아닙니다. 종료.")
        return
    
    keywords = get_keywords_from_sheets()
    
    if not keywords:
        print("⚠️ 키워드가 비어있습니다.")
        print("   Google Sheets의 A2 셀부터 키워드를 입력해주세요.")
        return
    
    last_rcept_no = load_last_rcept_no()
    print(f"[상태] 마지막 처리 접수번호: {last_rcept_no or '(없음 - 첫 실행)'}")
    
    disclosures = fetch_dart_list()
    if not disclosures:
        print("처리할 공시 없음. 종료.")
        return
    
    disclosures.sort(key=lambda x: x.get('rcept_no', ''))
    
    if not last_rcept_no:
        latest_rcept_no = disclosures[-1].get('rcept_no', '')
        save_last_rcept_no(latest_rcept_no)
        print(f"⚠️ 첫 실행입니다. 최신 접수번호({latest_rcept_no})만 기록하고 다음 실행부터 정상 작동합니다.")
        print("   다음 실행(최대 10분 후)부터 신규 공시 알림이 옵니다.")
        return
    
    new_disclosures = [d for d in disclosures if d.get('rcept_no', '') > last_rcept_no]
    print(f"[신규 공시] {len(new_disclosures)}건")
    
    notified_count = 0
    new_last = last_rcept_no
    for d in new_disclosures:
        matched = find_matching_keywords(d.get('corp_name', ''), d.get('report_nm', ''), keywords)
        if matched:
            print(f"  → 매칭: [{d.get('corp_name')}] {d.get('report_nm', '').strip()[:40]} | 키워드: {matched}")
            send_to_google_chat(d, matched)
            notified_count += 1
        rcept_no = d.get('rcept_no', '')
        if rcept_no > new_last:
            new_last = rcept_no
    
    if new_last > last_rcept_no:
        save_last_rcept_no(new_last)
    
    print(f"\n[결과] 신규 {len(new_disclosures)}건 중 {notified_count}건 알림 전송")
    print(f"DART 봇 실행 종료\n")


if __name__ == '__main__':
    main()