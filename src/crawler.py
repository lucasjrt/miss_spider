import json

from src.tor_requests import tor_get


def crawl(url):
    response = tor_get(url)

    if response.status_code == 200:
        print('Success')

        # print(response.text)
