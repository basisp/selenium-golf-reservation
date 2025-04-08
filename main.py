import time
import re
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv, dotenv_values
from kakao_send import send_kakao_message, get_access_token

# .env 파일 로드
load_dotenv()

# .env 파일에서 직접 값을 가져오기 (시스템 환경 변수와 충돌 방지)
env_values = dotenv_values()
GOLF_USERNAME = env_values.get("USERNAME") or os.getenv("GOLF_USERNAME")
GOLF_PASSWORD = env_values.get("PASSWORD") or os.getenv("GOLF_PASSWORD")

def perform_login(driver, wait, username, password):
    """
    로그인 페이지에서 로그인 처리
    사용자 아이디: name="UserID"
    비밀번호: name="Password"
    로그인 버튼: 이미지 src="/image/btn_login.jpg"
    """
    try:
        # 로그인 정보 확인
        print(f"로그인 시도: 사용자명={username}")
        
        # 로그인 페이지 로딩 대기 
        print("로그인 페이지 로딩 대기 중...")
        time.sleep(3)
        
        # 아이디 입력 (name="UserID")
        id_input = driver.find_element(By.NAME, "UserID")
        id_input.clear()
        id_input.send_keys(username)
        print("아이디 입력 완료")
        
        # 비밀번호 입력 (name="Password")
        pw_input = driver.find_element(By.NAME, "Password")
        pw_input.clear()
        pw_input.send_keys(password)
        print("비밀번호 입력 완료")
        
        # 로그인 버튼 클릭 (이미지 src="/image/btn_login.jpg")
        # 이미지 버튼이므로 이미지를 감싸고 있는 a 태그나 이미지 직접 클릭 시도
        try:
            # 방법 1: 이미지를 직접 찾아 클릭
            login_button = driver.find_element(By.XPATH, "//img[@src='/image/btn_login.jpg']")
            login_button.click()
            print("로그인 버튼 이미지 클릭")
        except Exception as e:
            print(f"이미지 직접 클릭 실패: {e}")
            try:
                # 방법 2: 이미지를 감싸는 a 태그 찾기
                login_link = driver.find_element(By.XPATH, "//a[img[@src='/image/btn_login.jpg']]")
                login_link.click()
                print("로그인 이미지 감싸는 링크 클릭")
            except Exception as e2:
                print(f"링크 클릭 실패: {e2}")
                try:
                    # 방법 3: JavaScript로 이미지 클릭
                    driver.execute_script("document.querySelector('img[src=\"/image/btn_login.jpg\"]').click();")
                    print("JavaScript로 로그인 이미지 클릭")
                except Exception as e3:
                    print(f"JavaScript 클릭 실패: {e3}")
                    # 방법 4: 비밀번호 필드에 Enter 키 입력 (onkeypress 이벤트 트리거)
                    pw_input.send_keys(Keys.ENTER)
                    print("Enter 키로 로그인 폼 제출")
        
        # 로그인 완료 후 로딩 대기
        print("로그인 처리 중...")
        time.sleep(5)
        
        print("로그인 완료!")
    except Exception as e:
        print(f"로그인 과정에서 오류 발생: {e}")
        # 페이지 소스 일부 출력하여 디버깅에 도움
        try:
            page_source = driver.page_source
            print("현재 페이지 소스 일부:")
            print(page_source[:1000])  # 처음 1000자만 출력
        except:
            print("페이지 소스를 가져올 수 없습니다.")

def select_date(driver, wait, target_date):
    """
    사용자가 원하는 날짜(예: '20250410')를 가진 <td class="on"> 요소를 찾아 클릭.
    """
    try:
        # select_date.html 페이지에서 현재 HTML 구조에 맞춰 XPATH 수정
        # td class="on" 요소를 찾아 클릭 (onclick 속성에 transDate_join 함수 호출 포함)
        date_elem = driver.find_element(By.XPATH, f"//td[@class='on' and contains(@onclick, 'transDate_join')]")
        date_elem.click()
        print(f"날짜 선택 클릭 완료.")
        
        # 날짜 선택 후, reservation02_1.asp 페이지 로딩 대기
        wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[td[@class='gray']]")))
        print("예약 가능 시간 페이지 로딩 완료")
    except Exception as e:
        print(f"날짜 선택 중 오류 발생:", e)

def reserve_for_two_members(driver, wait):
    """
    날짜 클릭 후 넘어온 페이지(예: reservation02_1.asp)의 테이블에서
    '2명'이 가능한 행을 찾아 '신청하기'까지 진행하고 팝업(Alert)을 '예'로 처리.
    시간 범위는 8시부터 13시까지만 고려합니다.
    성공하면 (True, 시간) 튜플, 실패하면 (False, None)을 반환합니다.
    """
    try:
        # 테이블 행을 찾음 (gray 클래스를 가진 td가 포함된 tr 요소들)
        rows = driver.find_elements(By.XPATH, "//table/tbody/tr[td[@class='gray']]")
        
        if not rows:
            print("예약 가능한 시간 슬롯을 찾을 수 없습니다.")
            return False, None
            
        print(f"총 {len(rows)}개의 시간 슬롯을 확인합니다.")
        found_slot = False
        
        for idx, row in enumerate(rows):
            try:
                # 시간 정보 추출
                time_elem = row.find_element(By.XPATH, "./td[@class='gray']/span")
                time_text = time_elem.text.strip()
                
                # 시간 형식이 "HH:MM"이라고 가정
                hour = int(time_text.split(':')[0])
                
                # 8시부터 13시까지의 시간대만 고려 (8:00 ~ 13:59)
                if 8 <= hour <= 13:
                    print(f"시간대 {time_text}는 원하는 범위(8시~13시) 내에 있습니다.")
                else:
                    print(f"시간대 {time_text}는 원하는 범위(8시~13시)를 벗어납니다. 건너뜁니다.")
                    continue
                
                # 예약 가능 인원 확인 (HTML 구조: td[3]/span)
                seat_count_elem = row.find_element(By.XPATH, "./td[3]/span")
                seat_count_text = seat_count_elem.text.strip()
                
                if "2명" in seat_count_text:
                    found_slot = True
                    print(f"{idx+1}번째 슬롯({time_text})에서 '2명' 예약 가능 발견. 예약 진행 시도 중...")
                    
                    # 해당 행의 인원 선택 드롭다운 가져오기 - j_person0, j_person1 등 ID 형식
                    select_elem = row.find_element(By.XPATH, ".//td[@class='price']/select")
                    select_id = select_elem.get_attribute("id")
                    select_obj = Select(select_elem)
                    
                    # "2명" 옵션 선택
                    select_obj.select_by_value("2")
                    print(f"드롭다운 ID: {select_id}에서 '2명' 옵션 선택 완료")
                    
                    # "신청하기" 버튼 클릭
                    apply_link = row.find_element(By.XPATH, ".//td/a[contains(@href, 'bookProsecc_join')]")
                    apply_link.click()
                    print("신청하기 버튼 클릭 완료, 팝업 대기 중...")
                    
                    # 첫 번째 팝업(조인 예약 확인) 처리
                    alert = wait.until(EC.alert_is_present())
                    alert_text = alert.text
                    print(f"첫 번째 팝업 메시지: {alert_text}")
                    
                    # 팝업 메시지 분석
                    if "조인 가능한 타임이 아닙니다" in alert_text:
                        print("이미 예약된 시간대입니다. 다음 시간대로 넘어갑니다.")
                        alert.accept()
                        continue  # 다음 시간대로 넘어감
                    elif "예약" in alert_text or "조인" in alert_text:
                        # 예약 확인 팝업 - '확인' 클릭
                        print(f"예약 확인 팝업 발견: {alert_text}")
                        alert.accept()
                        print("예약 확인 팝업 '확인' 버튼 클릭")
                        
                        # 두 번째 팝업(예약 성공) 처리 시도
                        try:
                            # 예약 성공 알림 팝업 대기 (최대 10초)
                            success_alert = wait.until(EC.alert_is_present())
                            success_text = success_alert.text
                            print(f"두 번째 팝업 메시지: {success_text}")
                            
                            # 예약 성공 메시지 확인
                            if "예약" in success_text and ("완료" in success_text or "성공" in success_text):
                                success_alert.accept()
                                print(f"예약 성공 확인! {time_text}에 예약이 완료되었습니다.")
                                return True, time_text
                            else:
                                # 예약 실패 메시지인 경우
                                success_alert.accept()
                                print(f"예약 실패 메시지: {success_text}")
                                continue  # 다음 시간대로 넘어감
                        except Exception as popup_e:
                            print(f"두 번째 팝업 대기 중 오류: {popup_e}")
                            # 팝업이 나타나지 않은 경우, 페이지 확인
                            try:
                                # 예약 성공 확인을 위한 페이지 체크
                                # 성공 페이지에 나타나는 요소 확인 (예: 예약 완료 메시지)
                                success_elem = driver.find_element(By.XPATH, "//div[contains(text(), '예약') and contains(text(), '완료')]")
                                if success_elem:
                                    print(f"페이지에서 예약 성공 확인! {time_text}에 예약이 완료되었습니다.")
                                    return True, time_text
                            except:
                                print("예약 성공 여부를 확인할 수 없습니다. 다음 시간대로 넘어갑니다.")
                                continue
                    else:
                        # 기타 예상치 못한 팝업 - 수락 후 다음 시간대로
                        alert.accept()
                        print(f"예상치 못한 팝업: {alert_text}. 다음 시간대로 넘어갑니다.")
                        continue
                    
            except Exception as row_e:
                print(f"행 처리 중 오류 발생: {row_e}")
                continue
        
        if not found_slot:
            print("8시부터 13시 사이에 2명 예약 가능한 슬롯을 찾지 못했습니다.")
            
    except Exception as e:
        print("2명 예약 진행 중 오류 발생:", e)
    return False, None

def notify_reservation_success(date, time_slot):
    """
    예약 성공 시 카카오톡 메시지 전송 함수
    성공 또는 실패 여부를 반환합니다.
    """
    # 토큰이 있는지 먼저 확인
    token = get_access_token()
    if not token:
        print("카카오톡 토큰이 없습니다. 인증 과정을 진행하세요.")
        # 인증 과정 유도
        get_access_token()  # 인증 URL 표시 및 코드 입력 요청
        # 다시 토큰 확인
        token = get_access_token()
        if not token:
            print("카카오톡 인증에 실패했습니다. 예약은 성공했으나 알림 메시지는 전송되지 않았습니다.")
            return False
    
    # 메시지 전송 시도
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"카카오톡 메시지 전송 시도 중... ({attempt}/{max_retries})")
            if send_kakao_message(date, time_slot, True):
                print("카카오톡 메시지 전송 성공!")
                return True
            else:
                print(f"카카오톡 메시지 전송 실패! 재시도 중...")
                time.sleep(2)  # 잠시 대기 후 재시도
        except Exception as e:
            print(f"카카오톡 메시지 전송 중 오류 발생: {e}")
            if attempt < max_retries:
                print(f"2초 후 재시도합니다... ({attempt}/{max_retries})")
                time.sleep(2)
            else:
                print("최대 시도 횟수를 초과했습니다. 메시지 전송에 실패했습니다.")
                return False
    
    print("카카오톡 메시지 전송이 모든 시도에서 실패했습니다.")
    return False

def main(headless=True):
    # 사용자가 직접 지정한 예약 시도 날짜들 (형식: YYYYMMDD)
    # 여기에 원하는 날짜를 추가하거나 제거할 수 있습니다
    user_dates = [
        "20250414",  # 2025년 4월 14일
        "20250416",  # 2025년 4월 16일
        "20250418",  # 2025년 4월 18일
        # 필요한 만큼 날짜 추가 가능
    ]
    
    print(f"예약 시도할 날짜: {user_dates}")
    
    # 모니터링 설정
    monitoring = True  # 지속적인 모니터링 활성화
    monitor_interval = 10  # 모니터링 주기 (10초)
    
    # 시작 시간 기록 (터미널 클리어 후 요약 정보용)
    start_time = datetime.now()
    
    # 카카오톡 토큰 사전 확인 (선택적)
    try:
        token = get_access_token()
        if token:
            print("카카오톡 토큰이 유효합니다. 예약 성공 시 카카오톡 메시지를 보낼 수 있습니다.")
        else:
            print("카카오톡 토큰이 없습니다. 예약 성공 시 알림을 받으려면 먼저 인증을 진행해주세요.")
    except Exception as e:
        print(f"카카오톡 토큰 확인 중 오류: {e}")
    
    # 로그인 정보 가져오기 (.env 파일에서 직접 가져온 값 사용)
    username = GOLF_USERNAME
    password = GOLF_PASSWORD
    
    # 로그인 정보 확인
    if not username or not password:
        print("오류: 로그인 정보가 없습니다. .env 파일을 확인하세요.")
        print("현재 설정된 값: GOLF_USERNAME=", username)
        return
    
    # Chrome 웹드라이버 옵션 설정
    chrome_options = Options()
    if headless:
        print("헤드리스 모드로 실행합니다.")
        chrome_options.add_argument("--headless=new")  # 새로운 헤드리스 모드 사용
    
    # 추가 옵션 설정
    chrome_options.add_argument("--disable-gpu")  # GPU 가속 비활성화
    chrome_options.add_argument("--no-sandbox")  # 샌드박스 모드 비활성화
    chrome_options.add_argument("--disable-dev-shm-usage")  # /dev/shm 파티션 사용 비활성화
    chrome_options.add_argument("--window-size=1920,1080")  # 창 크기 설정
    chrome_options.add_argument("--log-level=3")  # 로그 레벨 최소화
    
    # 일반적인 브라우저처럼 보이게 사용자 에이전트 설정
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # 1. 예약 페이지로 이동
        reservation_url = "http://www.ddgolf.co.kr/03reservation/reservation02.asp"
        driver.get(reservation_url)
        
        # 2. 로그인 여부 확인 (사이트 구조에 따라 예외 처리)
        try:
            login_element = driver.find_element(By.XPATH, "//a[contains(@href, 'member01.asp') and contains(text(), '로그인')]")
            print("미로그인 상태로 감지되어 로그인 페이지로 전환합니다.")
            login_element.click()
            
            # 로그인 페이지에서 로그인 처리
            # login_form을 기다리지 않고 직접 필드에 접근
            perform_login(driver, wait, username=username, password=password)
            
            # 로그인 후 다시 예약 페이지로 이동
            driver.get(reservation_url)
        except Exception:
            print("이미 로그인 상태이거나 로그인 요소를 찾을 수 없습니다.")
        
        # 예약 성공할 때까지 계속 모니터링 및 시도
        attempt_count = 0
        while monitoring:
            attempt_count += 1
            
            # 1,000회 시도마다 터미널 로그 클리어
            if attempt_count % 1000 == 0:
                # 터미널 클리어 명령 (Windows: cls, 그 외: clear)
                os.system('cls' if os.name=='nt' else 'clear')
                
                # 클리어 후 요약 정보 출력
                current_time = datetime.now()
                elapsed_time = current_time - start_time
                hours, remainder = divmod(elapsed_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                print(f"==================================================")
                print(f"프로그램 실행 중 - 터미널 로그 클리어됨")
                print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"경과 시간: {hours}시간 {minutes}분 {seconds}초")
                print(f"시도 횟수: {attempt_count}회")
                print(f"예약 시도 날짜: {user_dates}")
                print(f"모니터링 간격: {monitor_interval}초")
                print(f"==================================================")
            
            print(f"====== 모니터링 시도 {attempt_count}번째 ======")
            
            try:
                # 3. 사용 가능한 날짜 확인 (td class="on" 요소들)
                available_dates = driver.find_elements(By.XPATH, "//td[@class='on' and contains(@onclick, 'transDate_join')]")
                
                if not available_dates:
                    print(f"예약 가능한 날짜가 없습니다. {monitor_interval}초 후 페이지를 새로고침 후 재시도합니다.")
                    time.sleep(monitor_interval)
                    driver.refresh()
                    time.sleep(3)  # 새로고침 후 잠시 대기
                    continue
                
                print(f"총 {len(available_dates)}개의 예약 가능한 날짜를 찾았습니다.")
                
                # 날짜별로 예약 시도 (사용자 지정 날짜들만)
                reserve_success = False
                current_date = None
                time_slot = None
                
                for date_elem in available_dates:
                    try:
                        # 날짜 요소에서 날짜 정보 추출 (onclick 속성에서 날짜 값 파싱)
                        onclick_attr = date_elem.get_attribute("onclick")
                        date_match = re.search(r"'(\d{8})'", onclick_attr)
                        
                        if date_match:
                            current_date = date_match.group(1)
                            
                            # 사용자가 지정한 날짜 목록에 있는지 확인
                            if current_date not in user_dates:
                                print(f"날짜 {current_date}는 지정한 날짜 목록에 없어 건너뜁니다.")
                                continue
                            
                            print(f"\n{current_date} 날짜에 대한 예약 시도 중...")
                            
                            # 날짜 클릭
                            date_elem.click()
                            
                            # 날짜 클릭 후 로그인 팝업이 뜨는지 확인
                            try:
                                alert = wait.until(EC.alert_is_present())
                                alert_text = alert.text
                                print(f"팝업 발생: {alert_text}")
                                
                                # '로그인을 하셔야 예약가능합니다.' 팝업 처리
                                if "로그인" in alert_text:
                                    alert.accept()  # '예' 버튼 클릭
                                    print("로그인 페이지로 이동합니다.")
                                    
                                    # 로그인 진행
                                    perform_login(driver, wait, username=username, password=password)
                                    
                                    # 로그인 후 다시 예약 페이지로 이동
                                    driver.get(reservation_url)
                                    print("예약 페이지로 돌아왔습니다.")
                                    break  # 다시 날짜 선택부터 시작
                            except:
                                # 팝업이 없으면 정상 진행
                                pass
                            
                            # 페이지 로딩 대기
                            wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[td[@class='gray']]")))
                            print("예약 가능 시간 페이지 로딩 완료")
                            
                            # 해당 날짜에서 8시부터 13시까지 시간대 중 2명 예약 가능한 슬롯 찾기
                            reserve_success, time_slot = reserve_for_two_members(driver, wait)
                            
                            # 예약 성공하면 모니터링 종료
                            if reserve_success:
                                print(f"{current_date} 날짜에 {time_slot} 시간에 예약 성공! 모니터링을 종료합니다.")
                                
                                # 카카오톡 메시지 전송 - 개선된 함수 사용
                                print("예약 성공 알림을 카카오톡으로 전송합니다...")
                                notify_result = notify_reservation_success(current_date, time_slot)
                                if notify_result:
                                    print("예약 성공 알림이 성공적으로 전송되었습니다.")
                                else:
                                    print("예약은 성공했으나, 카카오톡 알림 전송에 실패했습니다.")
                                
                                monitoring = False
                                break
                            
                            # 다시 예약 페이지로 돌아가기
                            driver.get(reservation_url)
                            
                            # 페이지 로딩 대기
                            wait.until(EC.presence_of_element_located((By.XPATH, "//td[@class='on']")))
                        
                    except Exception as e:
                        print(f"날짜 예약 시도 중 오류 발생: {e}")
                        # 오류 발생 시 다시 예약 페이지로 돌아가서 다음 날짜 시도
                        driver.get(reservation_url)
                        # 페이지 로딩 대기
                        wait.until(EC.presence_of_element_located((By.XPATH, "//td[@class='on']")))
                
                # 모든 날짜를 시도했지만 예약 실패한 경우
                if monitoring and not reserve_success:
                    print(f"이번 시도에서 모든 날짜를 확인했지만 예약하지 못했습니다. {monitor_interval}초 후 다시 시도합니다.")
                    time.sleep(monitor_interval)
                    driver.get(reservation_url)  # 다시 예약 페이지로 이동
            
            except Exception as e:
                print(f"모니터링 중 오류 발생: {e}")
                print(f"{monitor_interval}초 후 다시 시도합니다.")
                time.sleep(monitor_interval)
                driver.get(reservation_url)  # 다시 예약 페이지로 이동
        
    except KeyboardInterrupt:
        print("사용자에 의해 프로그램이 중단되었습니다.")
    
    except Exception as e:
        print(f"예약 프로세스 중 오류 발생: {e}")
    
    finally:
        # 종료 전 잠시 대기
        time.sleep(5)
        driver.quit()
        
        if monitoring:
            print("모든 시도가 완료되었지만 예약에 성공하지 못했습니다.")
        else:
            print("예약 성공! 프로그램을 종료합니다.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='골프장 예약 자동화 스크립트')
    parser.add_argument('--visible', action='store_true', help='브라우저를 화면에 표시합니다(헤드리스 모드 비활성화)')
    
    args = parser.parse_args()
    
    # args.visible이 True이면 headless=False로 설정하여 브라우저가 화면에 표시됨
    main(headless=not args.visible)
