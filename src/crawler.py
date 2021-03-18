import json
import re

from bs4 import BeautifulSoup
from requests.exceptions import Timeout

from src.tor_requests import tor_get

url_list = []

def crawl(url, result_file_path):
    response = tor_get(url)

    if response.status_code == 200:
        print('Success')
        content = response.text
        all_links = get_onion_links(content)
        print('{} links found on first crawl, recursing'.format(len(all_links)))
        for link in all_links:
            if not link.startswith('http'):
                link = 'http://' + link

            print('Checking for {}'.format(link))
            try:
                child_response = tor_get(link)
                print('Response: {}'.format(child_response.status_code))

                child_content = child_response.text
                if child_content:
                    child_links = get_onion_links(child_content)
                    print('Found {} child links'.format(len(child_links)))

                if child_response.status_code == 200:

                    page = BeautifulSoup(child_content, 'html.parser')

                    title = page.title.string
                    if not title:
                        title = 'Unknown title'
                    else:
                        title = title.replace('\n', '\\n')
                        if ',' in title:
                            title = '"{}"'.format(title)
                    
                    url_list.append(link)

                    with open(result_file_path, 'a') as result_file:
                        result_file.write('{},{}\n'.format(title, link))
                else:
                    print('{}: {} response status'.format(link, child_response.status_code))
            except (ConnectionError, Timeout):
                print('{} timeout'.format(link))

    else:
        print('{} did not respond as expected'.format(url))


def get_onion_links(html):
    onion_pattern = '((?:https?://)?\\w+\\.onion)'
    return re.findall(onion_pattern, html, flags=re.MULTILINE)
