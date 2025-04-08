import time
import re
import os
import sys
import threading
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def perform_login(driver, wait, username, password):
    """
    예시: 로그인 폼이 존재하면 로그인 처리.
    실제 사이트의 ID/selector에 맞춰 수정하세요.
    """
    try:
        login_form = wait.until(EC.presence_of_element_located((By.ID, "login_form")))
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "login_button").click()
        print("로그인 시도 중...")
        
        # 로그인 완료 후 예약 페이지(또는 특정 요소) 로딩 대기
        wait.until(EC.presence_of_element_located((By.ID, "reservation_container")))
        print("로그인 성공!")
    except Exception as e:
        print("로그인 과정에서 오류 발생:", e)

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
    성공하면 True, 실패하면 False를 반환합니다.
    """
    try:
        # 테이블 행을 찾음 (gray 클래스를 가진 td가 포함된 tr 요소들)
        rows = driver.find_elements(By.XPATH, "//table/tbody/tr[td[@class='gray']]")
        
        if not rows:
            print("예약 가능한 시간 슬롯을 찾을 수 없습니다.")
            return False
            
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
                    
                    # 테스트 모드에서는 alert가 없을 수 있으므로 try/except로 처리
                    try:
                        # 팝업(Alert) 뜨면 메시지 확인 후 처리
                        alert = wait.until(EC.alert_is_present())
                        alert_text = alert.text
                        print(f"팝업 메시지: {alert_text}")
                        
                        # 팝업 메시지 분석
                        if "조인 가능한 타임이 아닙니다" in alert_text:
                            print("이미 예약된 시간대입니다. 다음 시간대로 넘어갑니다.")
                            alert.accept()
                            continue  # 다음 시간대로 넘어감
                        else:
                            # 일반적인 예약 확인 팝업 처리
                            alert.accept()
                            print(f"팝업 확인: {time_text}에 예약 신청 완료!")
                            return True
                    except:
                        # 테스트 모드에서는 alert가 없을 수 있음
                        print("테스트 모드: 팝업이 발생하지 않았거나 자동으로 처리되었습니다.")
                        return True
                    
            except Exception as row_e:
                print(f"행 처리 중 오류 발생: {row_e}")
                continue
        
        if not found_slot:
            print("8시부터 13시 사이에 2명 예약 가능한 슬롯을 찾지 못했습니다.")
            
    except Exception as e:
        print("2명 예약 진행 중 오류 발생:", e)
    return False

def main(test_mode=False, headless=True, local_server="http://localhost:8000"):
    """
    메인 함수 - 예약 시도를 처리합니다.
    
    Args:
        test_mode: 테스트 모드 활성화 여부
        headless: 헤드리스 모드 활성화 여부
        local_server: 테스트 서버 URL
    """
    # 사용자가 직접 지정한 예약 시도 날짜들 (형식: YYYYMMDD)
    # 여기에 원하는 날짜를 추가하거나 제거할 수 있습니다
    user_dates = [
        "20250410",  # 2025년 4월 10일
        "20250412",  # 2025년 4월 12일
        "20250415",  # 2025년 4월 15일
        # 필요한 만큼 날짜 추가 가능
    ]
    
    print(f"예약 시도할 날짜: {user_dates}")
    
    # 모니터링 설정
    monitoring = True  # 지속적인 모니터링 활성화
    monitor_interval = 10  # 모니터링 주기 (10초)
    
    # 로그인 정보 가져오기
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    
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
        # 테스트 모드와 실제 모드에 따라 URL 설정
        if test_mode:
            reservation_url = f"{local_server}/select_date.html"
            print(f"테스트 모드로 실행합니다. 로컬 서버 URL: {reservation_url}")
        else:
            reservation_url = "http://www.ddgolf.co.kr/03reservation/reservation02.asp"
        
        # 1. 예약 페이지로 이동
        driver.get(reservation_url)
        
        # 2. 테스트 모드일 때는 로그인 과정 생략
        if not test_mode:
            try:
                login_element = driver.find_element(By.XPATH, "//a[contains(@href, 'member01.asp') and contains(text(), '로그인')]")
                print("미로그인 상태로 감지되어 로그인 페이지로 전환합니다.")
                login_element.click()
                
                # 로그인 페이지에서 로그인 처리
                wait.until(EC.presence_of_element_located((By.ID, "login_form")))
                perform_login(driver, wait, username=username, password=password)
                
                # 로그인 후 다시 예약 페이지로 이동
                driver.get(reservation_url)
            except Exception:
                print("이미 로그인 상태이거나 로그인 요소를 찾을 수 없습니다.")
        
        # 예약 성공할 때까지 계속 모니터링 및 시도
        attempt_count = 0
        while monitoring:
            attempt_count += 1
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
                            
                            # 테스트 모드에서는 submit.html로 수동 이동 (날짜 클릭으로 페이지 전환이 안될 수 있음)
                            if test_mode:
                                driver.get(f"{local_server}/submit.html")
                            
                            # 페이지 로딩 대기
                            wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[td[@class='gray']]")))
                            print("예약 가능 시간 페이지 로딩 완료")
                            
                            # 해당 날짜에서 8시부터 13시까지 시간대 중 2명 예약 가능한 슬롯 찾기
                            reserve_success = reserve_for_two_members(driver, wait)
                            
                            # 예약 성공하면 모니터링 종료
                            if reserve_success:
                                print(f"{current_date} 날짜에 예약 성공! 모니터링을 종료합니다.")
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
                    
                # 테스트 모드에서는 한 번만 시도하고 종료
                if test_mode:
                    print("테스트 모드에서 한 번의 시도를 완료했습니다.")
                    break
            
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
        
        if monitoring and not test_mode:
            print("모든 시도가 완료되었지만 예약에 성공하지 못했습니다.")
        else:
            print("예약 성공! 프로그램을 종료합니다.")

# 테스트 서버 시작 헬퍼 함수 추가
def start_test_server():
    """
    select_date.html과 submit.html을 제공하는 간단한 HTTP 서버 시작
    """
    import http.server
    import socketserver
    import threading
    
    PORT = 8000
    handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"테스트 서버가 포트 {PORT}에서 시작되었습니다.")
        print(f"브라우저에서 http://localhost:{PORT}/select_date.html로 접속할 수 있습니다.")
        print("서버를 종료하려면 Ctrl+C를 누르세요.")
        httpd.serve_forever()

if __name__ == "__main__":
    # 명령행 인수 처리
    import argparse
    
    parser = argparse.ArgumentParser(description='골프장 예약 자동화 스크립트')
    parser.add_argument('--test', action='store_true', help='테스트 모드로 실행합니다')
    parser.add_argument('--visible', action='store_true', help='브라우저를 화면에 표시합니다(헤드리스 모드 비활성화)')
    
    args = parser.parse_args()
    
    if args.test:
        # 테스트 서버 시작
        server_thread = threading.Thread(target=start_test_server)
        server_thread.daemon = True  # 메인 스레드가 종료되면 같이 종료
        server_thread.start()
        
        print("5초 후 테스트 모드로 예약 스크립트를 시작합니다...")
        time.sleep(5)  # 서버가 완전히 시작될 때까지 대기
        
        # 테스트 모드로 메인 함수 실행 (args.visible이 True이면 headless=False로 설정)
        main(test_mode=True, headless=not args.visible)
    else:
        # 일반 모드로 실행 (args.visible이 True이면 headless=False로 설정)
        main(headless=not args.visible)