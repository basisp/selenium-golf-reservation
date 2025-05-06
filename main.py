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


class ReservationBot:
    def __init__(self, user_dates, monitor_interval=5, start_hour=8, end_hour=13):
        self.user_dates = user_dates
        self.monitor_interval = monitor_interval
        self.username = GOLF_USERNAME
        self.password = GOLF_PASSWORD
        self.start_time = datetime.now()
        self.reservation_url = "http://www.ddgolf.co.kr/03reservation/reservation02.asp"
        self.driver, self.wait = self._setup_driver()
        self.start_hour = start_hour
        self.end_hour = end_hour

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 10)
        return driver, wait

    def _login(self):
        try:
            self.driver.get(self.reservation_url)
            elem = self.driver.find_element(By.XPATH, "//a[contains(@href, 'member01.asp') and contains(text(), '로그인')]")
            elem.click()
            perform_login(self.driver, self.wait, self.username, self.password)
            self.driver.get(self.reservation_url)
        except:
            pass

    def _get_available_dates(self):
        raw = self.driver.find_elements(By.XPATH, "//td[@class='on' and contains(@onclick, 'transDate_join')]")
        avail = []
        for e in raw:
            m = re.search(r"'(\d{8})'", e.get_attribute("onclick"))
            if m and m.group(1) in self.user_dates:
                avail.append((m.group(1), e))
        return avail

    def _attempt_reserve(self, date, elem):
        try:
            elem.click()
            try:
                alert = self.wait.until(EC.alert_is_present(), timeout=5)
                if "로그인" in alert.text:
                    alert.accept()
                    self._login()
                    return False
            except:
                pass
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[td[@class='gray']]") ))
            ok, t = reserve_for_two_members(self.driver, self.wait, self.start_hour, self.end_hour)
            if ok:
                print(f"{date} {t} 예약 성공!")
                return True
        except:
            pass
        finally:
            self.driver.get(self.reservation_url)
        return False

    def run(self):
        if not self.username or not self.password:
            print("로그인 정보 누락")
            return
        self._login()
        while True:
            avail = self._get_available_dates()
            if not avail:
                print(f"예약가능 날짜 없음. {self.monitor_interval}초 후 재시도")
                time.sleep(self.monitor_interval)
                self.driver.refresh()
                continue
            for d, e in avail:
                if self._attempt_reserve(d, e):
                    self.driver.quit()
                    return
            time.sleep(self.monitor_interval)


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
        login_button = driver.find_element(By.XPATH, "//img[@src='/image/btn_login.jpg']")
        login_button.click()
        print("로그인 버튼 이미지 클릭")
        
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

def reserve_for_two_members(driver, wait, start_hour, end_hour):
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
                # 사용자 지정 범위만 고려
                if start_hour <= hour < end_hour:
                    print(f"시간대 {time_text}는 원하는 범위({start_hour}시~{end_hour}시) 내에 있습니다.")
                else:
                    print(f"시간대 {time_text}는 원하는 범위({start_hour}시~{end_hour}시)를 벗어납니다. 건너뜁니다.")
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


def main():
    user_dates = ["20250507", "20250509"]
    start_hour, end_hour = 8, 11 # 8시~11시
    bot = ReservationBot(user_dates, monitor_interval=5, start_hour=start_hour, end_hour=end_hour)
    bot.run()

if __name__ == "__main__":
    main()