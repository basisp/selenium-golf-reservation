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

# .env 파일 로드
load_dotenv()

# .env 파일에서 직접 값을 가져오기 (시스템 환경 변수와 충돌 방지)
env_values = dotenv_values()
GOLF_USERNAME = env_values.get("USERNAME") or os.getenv("GOLF_USERNAME")
GOLF_PASSWORD = env_values.get("PASSWORD") or os.getenv("GOLF_PASSWORD")

def perform_login(driver, wait, username, password):
    """
    수정: login.html 구조에 맞춘 locator
    """
    try:
        print(f"로그인 시도: 사용자명={username}")
        # 로그인 페이지 로딩 대기
        wait.until(EC.presence_of_element_located((By.NAME, "mmbrId")))

        # 1) 아이디 입력 (수정)
        id_input = driver.find_element(By.NAME, "mmbrId")
        id_input.clear()
        id_input.send_keys(username)
        print("아이디 입력 완료")

        # 2) 비밀번호 입력 (수정)
        pw_input = driver.find_element(By.NAME, "pwd")
        pw_input.clear()
        pw_input.send_keys(password)
        print("비밀번호 입력 완료")

        # 3) 로그인 버튼 클릭 (수정)
        login_button = driver.find_element(By.CSS_SELECTOR, "button.btn_blue_big")
        login_button.click()
        print("로그인 버튼 클릭")

        # 로그인 처리 대기
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
    시간 범위는 8시부터 13시까지만 고려하며, 9홀만 예약합니다.
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
                if 8 <= hour <= 10:
                    print(f"시간대 {time_text}는 원하는 범위(8시~13시) 내에 있습니다.")
                else:
                    print(f"시간대 {time_text}는 원하는 범위(8시~13시)를 벗어납니다. 건너뜁니다.")
                    continue
                
                # 9홀 여부 확인
                try:
                    course_elem = row.find_element(By.XPATH, "./td[@class='course']")
                    course_text = course_elem.text.strip()
                    if "9홀" not in course_text:
                        print(f"시간대 {time_text}는 9홀이 아닙니다 ({course_text}). 건너뜁니다.")
                        continue
                    print(f"시간대 {time_text}는 9홀입니다. 조건에 맞습니다.")
                except Exception as course_e:
                    print(f"코스 정보를 찾을 수 없습니다: {course_e}. 다음 시간대로 넘어갑니다.")
                    continue
                
                # 예약 가능 인원 확인 (HTML 구조: td[3]/span)
                seat_count_elem = row.find_element(By.XPATH, "./td[3]/span")
                seat_count_text = seat_count_elem.text.strip()
                
                if "2명" in seat_count_text or "3명" in seat_count_text:
                    found_slot = True
                    print(f"{idx+1}번째 슬롯({time_text})에서 '2명' or '3명' 예약 가능 발견. 예약 진행 시도 중...")
                    
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
            print("8시부터 13시 사이에 9홀 2명 예약 가능한 슬롯을 찾지 못했습니다.")
            
    except Exception as e:
        print("2명 예약 진행 중 오류 발생:", e)
    return False, None

def setup_driver():
    chrome_options = Options()
    # GUI 모드로 실행
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    return driver, wait

def navigate_to_reservation(driver, url):
    """
    예약 페이지로 이동 후 짧게 대기
    """
    driver.get(url)
    time.sleep(1)

def ensure_logged_in(driver, wait, reservation_url, username, password):
    """
    리디렉션된 로그인 페이지가 보이면 perform_login 후
    다시 예약 페이지로 복귀
    """
    current_url = driver.current_url
    if "login/loginForm.do" in current_url or "loginForm.do" in current_url:
        print("로그인 페이지 감지 → 로그인 처리")
        wait.until(EC.presence_of_element_located((By.NAME, "mmbrId")))
        perform_login(driver, wait, username, password)
        driver.get(reservation_url)
    else:
        print("로그인 불필요 (이미 로그인 상태)")

def clear_terminal_if_needed(attempt_count, start_time, user_dates, monitor_interval):
    """
    1000회마다 터미널을 클리어하고 요약 정보 출력
    """
    if attempt_count % 1000 == 0:
        os.system('cls' if os.name=='nt' else 'clear')
        current_time = datetime.now()
        elapsed = current_time - start_time
        hours, rem = divmod(elapsed.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        print("==================================================")
        print(f"시도 횟수: {attempt_count}회 | 경과 시간: {hours}h {minutes}m {seconds}s")
        print(f"예약 날짜: {user_dates} | 모니터링 주기: {monitor_interval}s")
        print("==================================================")

def check_and_relogin(driver, wait, last_login_check, reservation_url, username, password):
    """
    한 시간마다 세션 만료 체크 후 재로그인
    """
    if (datetime.now() - last_login_check).total_seconds() >= 3600:
        try:
            login_el = driver.find_element(By.XPATH, "//a[contains(text(),'로그인')]")
            print("세션 만료 감지 → 재로그인 진행")
            login_el.click()
            perform_login(driver, wait, username, password)
            driver.get(reservation_url)
        except:
            print("계속 로그인 상태 유지됨")
        return datetime.now()
    return last_login_check

def find_available_dates(driver):
    """
    예약 가능한 날짜 요소 목록 반환
    """
    return driver.find_elements(
        By.XPATH, "//td[@class='on' and contains(@onclick, 'transDate_join')]"
    )

def try_reserve_for_dates(driver, wait, available_dates, user_dates, reservation_url, username, password):
    """
    user_dates에 포함된 날짜만 순회하며 reserve_for_two_members 호출
    """
    for elem in available_dates:
        onclick = elem.get_attribute("onclick")
        date_match = re.search(r"'(\d{8})'", onclick)
        if not date_match:
            continue
        date = date_match.group(1)
        if date not in user_dates:
            continue
        print(f"{date} 예약 시도...")
        elem.click()
        # 로그인 팝업 나올 경우 처리
        try:
            alert = wait.until(EC.alert_is_present())
            if "로그인" in alert.text:
                alert.accept()
                print("로그인 필요 → 로그인 진행")
                perform_login(driver, wait, username, password)
                driver.get(reservation_url)
                break
        except:
            pass
        # 테이블 로딩 대기
        wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[td[@class='gray']]")))
        # 실제 예약 로직 호출
        success, time_slot = reserve_for_two_members(driver, wait)
        if success:
            return True, time_slot
        # 실패 시 다시 예약 페이지로 복귀
        driver.get(reservation_url)
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//td[@class='on']")))
    return False, None

def monitor_loop(driver, wait, reservation_url, user_dates, monitor_interval, username, password):
    """
    메인 모니터링 루프: 로그인 세션 체크, 터미널 클리어,
    예약 가능한 날짜 조회 및 예약 시도
    """
    last_login_check = datetime.now()
    attempt_count = 0
    start_time = datetime.now()
    while True:
        attempt_count += 1
        last_login_check = check_and_relogin(
            driver, wait, last_login_check, reservation_url, username, password
        )
        clear_terminal_if_needed(attempt_count, start_time, user_dates, monitor_interval)
        available_dates = find_available_dates(driver)
        if not available_dates:
            print("예약 가능한 날짜 없음 → 새로고침 후 재시도")
            time.sleep(monitor_interval)
            driver.refresh()
            continue
        success, slot = try_reserve_for_dates(
            driver, wait, available_dates, user_dates, reservation_url, username, password
        )
        if success:
            return True, slot
        time.sleep(monitor_interval)

# ── edit: 지정 범위 내 '공티예약접수' 버튼 클릭 함수 추가 ──
def reserve_in_range(driver, wait, date_list, start_time, end_time):
    """
    '공티 일자 및 시간' 테이블에서 날짜 목록과 시간이 지정된 범위에 있으면
    해당 행의 '공티예약접수' 버튼을 클릭합니다.

    Parameters:
      date_list            : 예약할 날짜 리스트 (['YYYYMMDD', ...])
      start_time, end_time : 'HH:MM' 형식 문자열
    Returns:
      (True, date_str, time_str, url) 클릭 성공 시
      (False, None, None, None)    클릭 실패 또는 리스트 내 슬롯 없을 때
    """
    try:
        rows = driver.find_elements(
            By.CSS_SELECTOR,
            "div.float_left.W100 table.tbl_st1 tbody tr"
        )
        for row in rows:
            # 헤더 행이면 건너뛰기
            if row.find_elements(By.TAG_NAME, "th"):
                continue
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 4:
                continue

            # 날짜/시간 텍스트 파싱 (예: '2025.05.04 (일)  05:43')
            dt_text   = cells[0].text.strip()
            date_m    = re.search(r'(\d{4})\.(\d{2})\.(\d{2})', dt_text)
            time_m    = re.search(r'(\d{2}:\d{2})', dt_text)
            if not date_m or not time_m:
                continue

            date_str = date_m.group(1) + date_m.group(2) + date_m.group(3)
            time_str = time_m.group(1)

            # 지정한 날짜 리스트 및 시간 범위 내에 있으면 버튼 클릭
            if date_str in date_list and start_time <= time_str <= end_time:
                btn = cells[3].find_element(By.TAG_NAME, "button")
                btn.click()
                print(f"{date_str} {time_str} → 공티예약접수 버튼 클릭 완료")
                # 클릭 후 reserveForm.do 페이지로 이동 대기
                wait.until(lambda d: "reserveForm.do" in d.current_url)
                new_url = driver.current_url
                print(f"이동된 URL: {new_url}")
                return True, date_str, time_str, new_url

        print("지정된 날짜 리스트 내 예약 가능한 슬롯이 없습니다.")
    except Exception as e:
        print(f"reserve_in_range 실행 중 오류 발생: {e}")
    return False, None, None, None

def click_reserve_save_and_cancel(driver, wait):
    """
    '공티접수' 버튼 클릭 후
    1) '현재 내용으로 신청하시겠습니까?' 팝업이 뜨면 '예'를 누르고,
    2) '신청접수 되었습니다.' 팝업이 뜨면 '확인'을 누릅니다.
    """
    try:
        # 1) '공티접수' 버튼 클릭
        save_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.btn_blue_big[onclick*='fn_reserveSave']")
        ))
        save_btn.click()
        print("공티접수 버튼 클릭")

        # 2) 첫 번째 팝업 대기 및 '예' 선택
        alert = wait.until(EC.alert_is_present())
        print(f"첫 번째 팝업 메시지: {alert.text}")
        alert.accept()
        print("첫 번째 팝업에서 '예' 선택 완료")

        # 3) 두 번째 팝업 대기 및 '확인' 선택
        second_alert = wait.until(EC.alert_is_present())
        print(f"두 번째 팝업 메시지: {second_alert.text}")
        second_alert.accept()
        print("두 번째 팝업에서 '확인' 선택 완료")

    except Exception as e:
        print(f"공티접수 및 팝업 처리 중 오류 발생: {e}")

def main():
    # 예약할 날짜 목록 (YYYYMMDD 형식)
    user_date_list = ["20250512", "20250513", "20250515", "20250516"]  # 원하는 날짜를 여기에 추가하세요
    # 로그인 정보
    username = GOLF_USERNAME
    password = GOLF_PASSWORD
    if not username or not password:
        print("오류: 로그인 정보가 설정되지 않았습니다.")
        return

    reservation_urls = [
        "https://www.armywelfaregolf.mil.kr/"
        "reserve/reserveEmptyTee.do?entofcCd=12&golfCrsCd=1",  # 사자대
        "https://www.armywelfaregolf.mil.kr/"
        "reserve/reserveEmptyTee.do?entofcCd=11&golfCrsCd=1",  # 다른 코스
        
    ]
    driver, wait = setup_driver()

    # 터미널 클리어 주기
    clear_interval = 10
    attempt_count = 0

    try:
        while True:
            attempt_count += 1

            if attempt_count % clear_interval == 0:
                os.system('cls' if os.name == 'nt' else 'clear')

            for url in reservation_urls:
                navigate_to_reservation(driver, url)
                ensure_logged_in(driver, wait, url, username, password)
                success, date_str, time_str, _ = reserve_in_range(
                    driver, wait,
                    user_date_list,
                    "07:30", "11:00"
                )

                if success:
                    print(f"[{attempt_count}] {date_str} {time_str} 슬롯 클릭 성공 → 팝업 처리")
                    click_reserve_save_and_cancel(driver, wait)
                    return  # 성공 시 루프 탈출

            print(f"[{attempt_count}] 모든 코스 검사 완료, 1초 대기 후 재시도")
            time.sleep(1)

    finally:
        print("예약 완료, 프로그램 종료")
        driver.quit()

if __name__ == "__main__":
    main()