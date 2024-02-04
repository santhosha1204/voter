from bs4 import BeautifulSoup
from flask import Flask, render_template, request, send_file, Response, flash, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from twocaptcha import TwoCaptcha
from selenium.common.exceptions import TimeoutException

# initial setup for the webdriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument("--start-maximized")
options.add_argument(
    f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36')
options.add_argument('window-size=2560,1440')
browser = webdriver.Chrome(options=options)


def captcha_solver(img_name):
    """
    solve the cpatcha using 2captcha service
    :param img_name: image file name
    :return:
    """
    try:
        solver = TwoCaptcha('90c3fe4585e5e0b71f670295f7ea4923')
        captcha = solver.normal(img_name)
        captcha.update({"status": 200})
    except Exception as e:
        captcha = {'status': 400, 'exception': e}
    return captcha


def get_data():
    """
    get data from the final page
    :return:
    """
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    if 'No Record Found' in soup.text:
        return {'status': 400, 'reason': 'No Record Found'}
    items = soup.find_all('tr', {'class': 'tr_bg_primary'}) + soup.find_all('tr', {'class': 'tr_bg_secondary'})
    print('all', len(items))
    data = {}
    [data.update({_.td.text.split('/ ')[-1].strip(): _.find_all('td')[1].text.strip()}) for _ in items if
     _.td.text.strip() != '']
    data.update({'status': 200})
    return data


def process(voter_id):
    """
    process the input to output
    :param voter_id:
    :return:
    """
    browser.get('https://tnsec.tn.nic.in/tn_election_urban2021/find_your_polling_station.php')

    browser.find_element(By.ID, "voter_id").send_keys(voter_id)
    browser.find_element(By.ID, "capt").screenshot('captcha.png')
    data = {}
    captcha = captcha_solver('captcha.png')
    print(captcha)
    if captcha['status'] == 200:
        browser.find_element(By.ID, "corp_t1").send_keys(captcha['code'])
        browser.find_element(By.ID, "show_voter").click()
        try:
            WebDriverWait(browser, 2).until(EC.alert_is_present())
            alert = browser.switch_to.alert
            return {'status': 409, 'exception': alert.text}
        except TimeoutException:
            data = get_data()
            return data

    else:
        return {'status': 409, 'exception': captcha['exception']}


app = Flask(__name__)

# your security code
SECURITY_CODE = 'secret'


@app.route('/voter', methods=['GET'])
def voter_info():
    """
    get input from the user and send output
    :return:
    """
    voter_id = request.args.get('voterid')
    security = request.args.get('code')
    if security != SECURITY_CODE:
        return jsonify({'status': 401, 'exception': 'Your security code is invalid'})
    print('Voter ID:', voter_id)
    z = process(voter_id)
    return jsonify(z)
