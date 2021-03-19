import os
import re
import sys
import time

from queue import Queue
from threading import Event, Lock, Thread

from bs4 import BeautifulSoup
from requests.exceptions import Timeout, SSLError

from src.tor_requests import tor_get

processing_links = Queue()
all_known_links = []

MAX_THREADS = 20
TIME_BETWEEN_REQUESTS = 5000
current_threads = 0

list_lock = Lock()
count_lock = Lock()
online_lock = Lock()
offline_lock = Lock()

thread_control = Event()
thread_control.set()

thread_throttle = Event()
thread_throttle.set()

running = True


def crawl(url, result_folder_path):
    global current_threads
    global running

    online_file_path = result_folder_path + 'online.csv'
    offline_file_path = result_folder_path + 'offline.csv'

    load_known_links(result_folder_path)
    load_pending_links(result_folder_path)

    print('Using a limit of {} threads'.format(MAX_THREADS))
    print('The interval between each request is {} milliseconds'.format(
        TIME_BETWEEN_REQUESTS))

    try:
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

        throttler = Thread(target=thread_pulse)
        throttler.start()
        threads = []
        while not processing_links.empty():
            while not processing_links.empty():
                list_lock.acquire()
                link = processing_links.get()
                list_lock.release()

                thread_throttle.wait()
                if current_threads >= MAX_THREADS:
                    thread_control.clear()
                thread_control.wait()

                count_lock.acquire()
                current_threads += 1
                count_lock.release()

                thread = Thread(target=scrape, args=(
                    link, online_file_path, offline_file_path))
                threads.append(thread)
                thread_throttle.clear()
                thread.start()

            for thread in threads:
                thread.join()

            processing_links.join()

        running = False
        throttler.join()
    except KeyboardInterrupt:
        running = False
        print('Saving progress, please wait for graceful stop.')
        pending_file_path = result_folder_path + "pending.dat"

        with open(pending_file_path, 'w') as pending_file:
            content = '\n'.join(list(processing_links.queue))
            pending_file.write(content)

        print('Progress saved, wait until execution ends so no links are skipped.')


def scrape(link, online_file_path, offline_file_path):
    global current_threads
    if not link.startswith('http'):
        link = 'http://' + link

    print('Scraping {}. Current threads: {} / {}. Links in queue: {}'.format(link,
          current_threads, MAX_THREADS, processing_links.qsize()))
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

            if running:
                print('Result: {} has {} child links ({} new)'.format(
                    link, len(new_links), discovered))

            page = BeautifulSoup(content, 'html.parser')

            if page.title:
                title = page.title.string
            else:
                title = None
            title = get_title(title)

            online_lock.acquire()
            with open(online_file_path, 'a') as result_file:
                result_file.write('{},{},{}\n'.format(
                    title, link, status_code))
            online_lock.release()
        else:
            print('[WARNING] Unexpected status code {}: {} response status'.format(
                link, response.status_code))
    except (ConnectionError, Timeout):
        print('Result: {} timed out'.format(link))
        offline_lock.acquire()
        with open(offline_file_path, 'a') as result_file:
            result_file.write('{}\n'.format(link))
        offline_lock.release()
    except SSLError:
        print('Result: {} has invalid SSL certificate'.format(link))
        status_code = 0
        title = 'Invalid SSL certificate'
        online_lock.acquire()
        with open(online_file_path, 'a') as result_file:
            result_file.write('{}\n'.format(link))
        online_lock.release()
    except Exception as e:
        error_file_path = 'errors.txt'
        if not os.path.exists(error_file_path):
            with open(error_file_path, 'w'):
                pass
        with open(error_file_path, 'a') as error_file:
            error_file.write(link + '\n')
            error_file.write(str(e) + '\n')
            error_file.write(status_code)

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
    online_file_path = result_folder_path + 'online.csv'
    offline_file_path = result_folder_path + 'offline.csv'

    total_online = 0
    total_offline = 0

    print('Loading known links')

    with open(online_file_path, 'r') as online_file:
        all_lines = online_file.readlines()[1:]
        total_online = len(all_lines)
        invalid = []
        for i, line in enumerate(all_lines):
            try:
                url = line.split(',')[1]
            except IndexError:
                invalid.append((i + 2, line.strip()))
            all_known_links.append(url)

    if invalid:
        plural = 's' if len(invalid) > 1 else ''
        print('[ERROR] Found {} invalid line{}:'.format(len(invalid), plural))

        for line_number, line in invalid:
            print('Line {}: {}'.format(line_number, line))

        sys.exit(10)

    with open(offline_file_path, 'r') as offline_file:
        all_lines = offline_file.readlines()[1:]
        total_offline = len(all_lines)
        for line in all_lines:
            all_known_links.append(line)

    print('Found {} known links ({} online, {} offline)'.format(
        len(all_known_links), total_online, total_offline))


def load_pending_links(result_folder_path):
    pending_file_path = result_folder_path + 'pending.dat'

    if os.path.exists(pending_file_path):
        print('Loading pending links')
        with open(pending_file_path, 'r') as pending_file:
            links = [link.strip() for link in pending_file.readlines()
                     if link not in all_known_links]

        for line in links:
            processing_links.put(line)

        print('Restored {} pending links'.format(len(links)))


def thread_pulse():
    global running
    interval = TIME_BETWEEN_REQUESTS / 1000
    while running:
        thread_throttle.set()
        time.sleep(interval)
