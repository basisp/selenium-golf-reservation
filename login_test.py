import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from main import perform_login, GOLF_USERNAME, GOLF_PASSWORD

@pytest.fixture(scope="module")
def driver():
    # 헤드리스 크롬 브라우저 실행
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_perform_login(driver):
    wait = WebDriverWait(driver, 10)
    login_url = "https://www.armywelfaregolf.mil.kr/login/loginForm.do"

    # 1) 로그인 페이지로 이동
    driver.get(login_url)

    # 2) 로그인 수행
    perform_login(driver, wait, GOLF_USERNAME, GOLF_PASSWORD)

    # 3) 로그인 후 URL이 여전히 loginForm.do가 아니어야 함
    time.sleep(2)  # 로그인 리다이렉션 대기
    current_url = driver.current_url
    assert "loginForm.do" not in current_url, "로그인 실패: 여전히 로그인 페이지에 머물러 있습니다."

    # (옵션) 페이지 상단에 '로그아웃' 링크가 있는지 확인
    # logout_elem = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "로그아웃")))
    # assert logout_elem is not None, "로그아웃 링크를 찾을 수 없습니다."

    print(f"로그인 성공 확인: 현재 URL = {current_url}") 