import json
import re

from bs4 import BeautifulSoup
from requests.exceptions import Timeout

from src.tor_requests import tor_get

onion_pattern = '((?:https?://)?\\w+\\.onion)'

url_list = []

def crawl(url, result_file_path):
    response = tor_get(url)

    if response.status_code == 200:
        print('Success')
        content = response.text
        all_links = re.findall(onion_pattern, content, flags=re.MULTILINE)
        print('{} links found on first crawl, recursing'.format(len(all_links)))
        for link in all_links:
            if not link.startswith('http'):
                link = 'http://' + link

            print('Checking for {}'.format(link))
            try:
                child_response = tor_get(link)
                print('Response: {}'.format(child_response.status_code))
                if child_response.status_code == 200:
                    child_content = child_response.text

                    page = BeautifulSoup(child_content, 'html.parser')
                    title = page.title.string
                    if not title:
                        title = 'Unknown'
                    else:
                        if ',' in title:
                            title = '"{}"'.format(title)
                    
                    url_list.append(link)

                    with open(result_file_path, 'a') as result_file:
                        result_file.write('{},{}\n'.format(title, link))
            except (ConnectionError, Timeout):
                print('{} timeout'.format(link))

    else:
        print('{} did not respond as expected'.format(url))


