import re
from http import HTTPStatus
from random import choice

import requests
from bs4 import BeautifulSoup

from models import LocationModel
from utils import (FailedRequestApi, logger, MatchNotFound,
                   TimeZoneNotFound)


def get_session():
    session = requests.Session()
    session.headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; '
                                     'x64) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                                     'Chrome/101.0.0.0 Safari/537.36'}
    return session


def get_proxy(session):
    html = session.get('https://free-proxy-list.net/').text
    soup = BeautifulSoup(html, 'lxml')

    trs = soup.find('tbody').find_all('tr')

    proxies = []

    for tr in trs:
        tds = tr.find_all('td')
        ip = tds[0].text.strip()
        port = tds[1].text.strip()
        schema = 'https' if 'yes' in tds[6].text.strip() else 'http'
        proxy = {'schema': schema, 'address': ip + ':' + port}
        proxies.append(proxy)

    return choice(proxies)


def get_csrf_token_and_cookies(proxy, session):
    url = 'https://www.maxmind.com/en/geoip2-precision-demo'
    response = session.get(url, proxies=proxy)

    if response.status_code != HTTPStatus.OK:
        logger.error(f'Ответ сервера: {response.status_code}')
        raise FailedRequestApi(f'Ответ сервера: {response.status_code}')

    soup = BeautifulSoup(response.text, 'html.parser')
    script = soup.find('div', id='geoip-demo').find_next_sibling('script').text
    pattern = r'window\.MaxMind\.X_CSRF_TOKEN = "(.*?)";'
    match = re.search(pattern, script)

    if match is None:
        logger.error('Csrf Token не найден')
        raise MatchNotFound('Csrf Token не найден')

    value = match.group(1)
    cookies = response.cookies.get_dict()
    return value, cookies


def get_ip_address(proxy, session):
    url = 'https://2ip.ru/'
    response = session.get(url, proxies=proxy)

    if response.status_code != HTTPStatus.OK:
        logger.error(f'Ответ сервера IP адреса: {response.status_code}')
        raise FailedRequestApi(f'Ответ сервера IP адреса:'
                               f'{response.status_code}')

    soup = BeautifulSoup(response.text, 'html.parser')
    ip_address = soup.find('div', class_='ip').find('span').text
    return ip_address


def get_token(proxy, session):
    csrf, cookies = get_csrf_token_and_cookies(proxy, session)
    session.headers['x-csrf-token'] = csrf
    response = session.post('https://www.maxmind.com/en/geoip2/demo/token',
                            cookies=cookies, proxies=proxy)

    if response.status_code != HTTPStatus.CREATED:
        logger.error(f'Ответ сервера получения токена: {response.status_code}')
        raise FailedRequestApi(f'Ответ сервера получения токена:'
                               f'{response.status_code}')

    result = response.json()

    if 'token' not in result:
        raise KeyError(
            'Ключ token отсутствует в ответе API.'
        )

    token = result['token']
    return token


def get_timezone(ip_address, proxy, session):
    url = f"https://geoip.maxmind.com/geoip/v2.1/city/{ip_address}?demo=1"
    session.headers['authorization'] = f"Bearer {get_token(proxy, session)}"
    response = session.get(url, proxies=proxy)

    if response.status_code != HTTPStatus.OK:
        logger.error(f'Ответ сервера получения time_zone:'
                     f'{response.status_code}')
        raise FailedRequestApi(f'Ответ сервера получения time_zone:'
                               f'{response.status_code}')

    result = response.json()

    if 'location' not in result:
        raise KeyError(
            'Ключ location отсутствует в ответе API.'
        )

    try:
        data = LocationModel.model_validate(response.json()['location'])
    except KeyError:
        logger.error('Ключ time-zone отсутствует')
        raise TimeZoneNotFound('Ключ time-zone отсутствует')

    return data.time_zone


def get_regions(timezone, proxy, session):
    url = 'https://gist.github.com/salkar/19df1918ee2aed6669e2'
    response = session.get(url, proxies=proxy)

    if response.status_code != HTTPStatus.OK:
        logger.error(f'Ответ сервера получения региона:'
                     f'{response.status_code}')
        raise FailedRequestApi(f'Ответ сервера получения региона:'
                               f'{response.status_code}')

    soup = BeautifulSoup(response.text, 'html.parser')
    regions = []
    table = soup.find('table', class_="highlight tab-size "
                                      "js-file-line-container "
                                      "js-code-nav-container "
                                      "js-tagsearch-file")
    tr = table.find_all('tr')
    for items in tr:
        for item in items.find_all('td'):
            if timezone in item.text:
                item = item.text.replace("[", "").replace("]", "").replace(",",
                                                                           "")
                regions.append(item.split('" "')[0].strip().replace('"', ''))

    return regions


def save_to_txt(timezone, regions):
    with open('result.txt', 'w', encoding='UTF-8') as file:
        file.write(timezone + '\n')
        if regions:
            file.write('\n'.join(regions))
        else:
            file.write("No regions found")
    return 'Готово'


def main():
    session = get_session()
    proxy = get_proxy(session)
    ip_address = get_ip_address(proxy, session)
    timezone = get_timezone(ip_address, proxy, session)
    regions = get_regions(timezone, proxy, session)
    result = save_to_txt(timezone, regions)
    return result


if __name__ == "__main__":
    print(main())
