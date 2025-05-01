import sys, os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# 프로젝트 루트를 PATH에 추가하여 main 모듈 import 가능하게 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import click_sajade_course, reserve_in_range

@pytest.fixture(scope="module")
def driver():
    # 헤드리스 크롬 브라우저
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_click_and_reserve_specific_slot(driver):
    """
    1) 로컬 예약 테이블(html/reservation_table.html) 로드
    2) '사자대' 링크 삽입 후 click_sajade_course 호출
    3) 2025-05-08 06:04 슬롯에 대해 reserve_in_range 호출하여
       fn_reserveForm 리다이렉트까지 정상 동작하는지 확인
    """
    wait = WebDriverWait(driver, 10)

    # 로컬 HTML 파일 경로
    project_root = os.path.dirname(os.path.dirname(__file__))
    html_file = os.path.join(project_root, "html", "reservation_table.html")
    file_url = f"file://{html_file}"
    driver.get(file_url)
    time.sleep(1)

    # 1) '사자대' 링크 DOM에 삽입 (테스트용)
    driver.execute_script("""
        const a = document.createElement('a');
        a.innerText = '사자대';
        a.href = '#';
        document.body.prepend(a);
    """)

    # 2) 예약 버튼 클릭 시 reserveForm.do 로 이동하도록 JS 함수 스텁
    driver.execute_script("""
        window.fn_reserveForm = function(ymd, entofcCd, golfCrsCd, teamNmbr, seq){
            window.location.href = "https://www.armywelfaregolf.mil.kr/reserve/reserveForm.do";
        };
    """)

    # 사자대 코스 클릭
    click_sajade_course(driver, wait)

    # 3) 지정 슬롯(2025-05-08 06:04) 예약 시도
    start_date, end_date = "20250508", "20250508"
    start_time, end_time = "06:04", "06:04"
    success, date_str, time_str, new_url = reserve_in_range(
        driver, wait, start_date, end_date, start_time, end_time
    )

    assert success, "지정한 슬롯에 대한 예약 클릭이 이루어지지 않았습니다."
    assert date_str == "20250508"
    assert time_str == "06:04"
    assert "reserveForm.do" in new_url, f"이동된 URL에 reserveForm.do가 없습니다: {new_url}" 