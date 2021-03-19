import re

from queue import Queue
from threading import Event, Lock, Thread

from bs4 import BeautifulSoup
from requests.exceptions import Timeout

from src.tor_requests import tor_get

processing_links = Queue()
all_known_links = []

MAX_THREADS = 10
current_threads = 0

list_lock = Lock()
count_lock = Lock()
online_lock = Lock()
offline_lock = Lock()

thread_control = Event()
thread_control.set()


def crawl(url, result_folder_path):
    global current_threads

    online_file_path = result_folder_path + 'online.csv'
    offline_file_path = result_folder_path + 'offline.csv'

    load_known_links(result_folder_path)

    print('Using a limit of {} threads'.format(MAX_THREADS))

    try:
        response = tor_get(url)
    except (ConnectionError, Timeout):
        print('Failed to connect to {}'.format(url))
        return

    content = response.text
    if content:
        all_links = [link for link in get_onion_links(
            content) if link not in all_known_links]
        for link in all_links:
            processing_links.put(link)
            all_known_links.append(link)
    else:
        print('Could not scrape {}'.format(url))
        return

    threads = []
    while not processing_links.empty():
        while not processing_links.empty():
            list_lock.acquire()
            link = processing_links.get()
            list_lock.release()

            if current_threads >= MAX_THREADS:
                thread_control.clear()
            thread_control.wait()

            count_lock.acquire()
            current_threads += 1
            count_lock.release()

            thread = Thread(target=scrape, args=(link, online_file_path, offline_file_path))
            threads.append(thread)
            thread.start()
            #scrape(link, online_file_path, offline_file_path)

        for thread in threads:
            thread.join()

        processing_links.join()


def scrape(link, online_file_path, offline_file_path):
    global current_threads
    if not link.startswith('http'):
        link = 'http://' + link

    print('Scraping {}'.format(link))
    try:
        response = tor_get(link)

        status_code = response.status_code

        content = response.text
        if content:
            new_links = get_onion_links(content)
            discovered = 0
            for child_link in new_links:
                if child_link not in all_known_links:
                    discovered += 1
                    list_lock.acquire()
                    all_known_links.append(child_link)
                    processing_links.put(child_link)
                    list_lock.release()

            print('Found {} child links ({} new) in {}'.format(
                len(new_links), discovered, link))

            page = BeautifulSoup(content, 'html.parser')
            title = get_title(page.title.string)
        else:
            print('{}: {} response status'.format(
                link, response.status_code))

        online_lock.acquire()
        with open(online_file_path, 'a') as result_file:
            result_file.write('{},{},{}\n'.format(title, link, status_code))
        online_lock.release()

    except (ConnectionError, Timeout):
        print('{} timed out'.format(link))
        status_code = None
        title = 'Offline'
        offline_lock.acquire()
        with open(offline_file_path, 'a') as result_file:
            result_file.write('{}\n'.format(link))
        offline_lock.release()

    list_lock.acquire()
    processing_links.task_done()
    list_lock.release()

    count_lock.acquire()
    current_threads -= 1
    thread_control.set()
    count_lock.release()


def get_title(title):
    if title:
        title = title.replace('\n', '\\n')
        if ',' in title:
            title = '"{}"'.format(title)
        return title
    return 'Unknown title'


def get_onion_links(html):
    onion_pattern = '((?:https?://)?\\w+\\.onion)'
    return re.findall(onion_pattern, html, flags=re.MULTILINE)


def load_known_links(result_folder_path):
    print('Loading known links')
    online_file_path = result_folder_path + 'online.csv'
    offline_file_path = result_folder_path + 'offline.csv'

    with open(online_file_path, 'r') as online_file:
        all_lines = online_file.readlines()[1:]
        for line in all_lines:
            url = line.split(',')[1]
            all_known_links.append(url)

    with open(offline_file_path, 'r') as offline_file:
        all_lines = offline_file.readlines()[1:]
        for line in all_lines:
            all_known_links.append(line)

    print('Found {} known links'.format(len(all_known_links)))
