import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

# .env 파일 로드
load_dotenv()

# 카카오톡 API 설정
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")  # 카카오 REST API 키
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "https://example.com/oauth")  # 리다이렉트 URI

# 토큰 파일 경로
TOKEN_FILE = "kakao_token.json"

def save_tokens(token_data):
    """
    토큰 정보를 파일에 저장
    """
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(token_data, f)
    print(f"토큰이 {TOKEN_FILE}에 저장되었습니다.")

def load_tokens():
    """
    저장된 토큰 정보 로드
    """
    if not os.path.exists(TOKEN_FILE):
        return None
    
    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            token_data = json.load(f)
            
        # 만료 시간 확인
        if 'expires_at' in token_data and datetime.now().timestamp() > token_data['expires_at']:
            print("토큰이 만료되었습니다. 갱신을 시도합니다.")
            return refresh_tokens(token_data)
            
        return token_data
    except Exception as e:
        print(f"토큰 로드 실패: {e}")
        return None

def authorize_with_code(code):
    """
    인증 코드를 사용하여 액세스 토큰 및 리프레시 토큰 발급
    """
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code != 200:
        print(f"카카오 토큰 발급 실패: {response.text}")
        return None
    
    # 응답에서 토큰 정보 추출
    token_data = response.json()
    
    # 만료 시간 추가 (액세스 토큰 만료 시간은 약 6시간)
    token_data['expires_at'] = (datetime.now() + timedelta(seconds=token_data.get('expires_in', 21600))).timestamp()
    
    # 토큰 저장
    save_tokens(token_data)
    
    print("카카오 토큰 발급 성공!")
    return token_data

def refresh_tokens(token_data):
    """
    리프레시 토큰을 사용하여 액세스 토큰 갱신
    """
    if not token_data or 'refresh_token' not in token_data:
        print("리프레시 토큰이 없습니다. 새 인증 코드가 필요합니다.")
        return None
    
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": token_data['refresh_token']
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code != 200:
        print(f"카카오 토큰 갱신 실패: {response.text}")
        # 토큰 파일 삭제 (인증 코드 재발급 필요)
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return None
    
    # 응답에서 새 토큰 정보 추출
    new_token_data = response.json()
    
    # 기존 리프레시 토큰 유지 (응답에 포함되지 않은 경우)
    if 'refresh_token' not in new_token_data:
        new_token_data['refresh_token'] = token_data['refresh_token']
    
    # 만료 시간 갱신
    new_token_data['expires_at'] = (datetime.now() + timedelta(seconds=new_token_data.get('expires_in', 21600))).timestamp()
    
    # 새 토큰 저장
    save_tokens(new_token_data)
    
    print("카카오 토큰 갱신 성공!")
    return new_token_data

def get_access_token():
    """
    유효한 액세스 토큰 반환 (필요시 리프레시)
    """
    # 저장된 토큰 로드
    token_data = load_tokens()
    
    if token_data and 'access_token' in token_data:
        return token_data['access_token']
    
    # 토큰이 없거나 갱신 실패한 경우
    print("유효한 액세스 토큰이 없습니다.")
    
    # 환경변수에서 인증 코드 확인
    code = os.getenv("KAKAO_CODE")
    if code:
        print("환경변수에서 인증 코드를 발견했습니다. 이 코드로 토큰 발급을 시도합니다.")
        token_data = authorize_with_code(code)
        if token_data:
            return token_data['access_token']
    
    # 인증 코드 안내 메시지
    auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_REST_API_KEY}&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code&scope=profile_nickname,talk_message"
    print("\n유효한 토큰이 없습니다. 다음 URL에서 새 인증 코드를 발급받으세요:")
    print(auth_url)
    print("\n그 후 .env 파일에 KAKAO_CODE=발급받은코드 형식으로 추가하거나, 다음 명령어로 인증 코드를 설정하세요:")
    print(f"다음 방법 중 하나로 사용할 수 있습니다:")
    print("1. 직접 코드 입력")
    code = input("카카오 인증 코드를 붙여넣기 하세요 (취소하려면 엔터): ")
    if code.strip():
        token_data = authorize_with_code(code.strip())
        if token_data:
            return token_data['access_token']
    
    return None

def send_kakao_message(date, time_slot, success=True):
    """
    카카오톡 메시지 전송 함수
    
    Args:
        date: 예약 날짜 (YYYYMMDD 형식)
        time_slot: 예약 시간대
        success: 예약 성공 여부
    """
    # 유효한 액세스 토큰 가져오기
    token = get_access_token()
    
    if not token:
        print("카카오 토큰이 없어 메시지를 보낼 수 없습니다.")
        return False
    
    # 날짜 형식 변환 (YYYYMMDD -> YYYY년 MM월 DD일)
    formatted_date = f"{date[:4]}년 {date[4:6]}월 {date[6:8]}일"
    
    # 메시지 내용 설정
    status = "예약 완료" if success else "예약 실패"
    message = {
        "object_type": "text",
        "text": f"골프장 예약 {'성공' if success else '실패'} 알림\n\n"
                f"📅 날짜: {formatted_date}\n"
                f"⏰ 시간: {time_slot}\n"
                f"📝 상태: {status}",
        "link": {
            "web_url": "http://www.ddgolf.co.kr",
            "mobile_web_url": "http://www.ddgolf.co.kr"
        },
        "button_title": "예약 확인하기"
    }
    
    # 메시지 전송 API 호출
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "template_object": json.dumps(message)
    }
    
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            print("카카오톡 메시지 전송 성공!")
            return True
        else:
            print(f"카카오톡 메시지 전송 실패: {response.text}")
            error_data = response.json()
            
            # 토큰 만료로 인한 오류인 경우
            if 'code' in error_data and error_data['code'] in [-401, -2]:
                print("토큰이 만료되어 갱신을 시도합니다.")
                # 토큰 갱신 시도
                token = get_access_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    retry_count += 1
                    continue
            
            # 권한 부족 또는 기타 오류
            return False
    
    return False

# 메인 실행 부분
if __name__ == "__main__":
    print("카카오 메시지 전송 모듈 테스트")
    
    # 테스트 메시지 전송
    test_result = send_kakao_message("20250415", "10:30", True)
    print(f"테스트 메시지 전송 결과: {'성공' if test_result else '실패'}")
