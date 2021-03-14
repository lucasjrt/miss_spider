import os
import requests

from fake_useragent import UserAgent
from stem import Signal
from stem.control import Controller

try:
    TOR_PASS = os.environ['TOR_PASS']
except KeyError:
    print('Expected TOR_PASS environment variable')
    exit(2)

tor_proxy = {
  "http": "socks5h://127.0.0.1:9050",
  "https": "socks5h://127.0.0.1:9050"
}

headers = {
  "User-Agent": UserAgent().random
}

def new_tor_id():
  with Controller.from_port(port=9051) as controller:
    controller.authenticate(password=TOR_PASS)
    controller.signal(Signal.NEWNYM)


def tor_get(url: str):
    new_tor_id()
    response = requests.get(url, headers=headers, proxies=tor_proxy, timeout=10)
    return response
