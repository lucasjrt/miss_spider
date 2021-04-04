import os
import re
import sys
import time

from queue import Queue
from threading import Event, Lock, Thread

from bs4 import BeautifulSoup
from requests.exceptions import Timeout, SSLError
from requests.exceptions import ConnectionError as ConnError

from src.tor_requests import tor_get

processing_links = Queue()
all_known_links = []

MAX_THREADS = 5
TIME_BETWEEN_REQUESTS = 5000
current_threads = 0

list_lock = Lock()
count_lock = Lock()
online_lock = Lock()
offline_lock = Lock()
error_lock = Lock()

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
    error_file_path = result_folder_path + 'error.csv'

    load_known_links(result_folder_path)
    load_pending_links(result_folder_path)

    print('Using a limit of {} threads'.format(MAX_THREADS))
    print('The interval between each request is {} milliseconds'.format(
        TIME_BETWEEN_REQUESTS))

    try:
        try:
            response = tor_get(url)
        except Timeout:
            print('Failed to connect to {}. Timeout'.format(url))
            return
        except ConnError as e:
            print('Failed to connect to {}. {}'.format(url, e))
            if not os.path.exists(error_file_path):
                with open(error_file_path, 'w') as error_file:
                    error_file.write('URL,Error')

            with open(error_file_path, 'a') as error_file:
                formatted_error = str(e).replace('\n', '\\n')
                if ',' in formatted_error:
                    formatted_error = '"{}"'.format(formatted_error)
                error_file.write('{},{}\n'.format(url, formatted_error))
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
                    link, result_folder_path))
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


def scrape(link, result_folder_path):
    global current_threads
    if not link.startswith('http'):
        link = 'http://' + link

    online_file_path = result_folder_path + 'online.csv'
    offline_file_path = result_folder_path + 'offline.csv'
    error_file_path = result_folder_path + 'error.csv'

    print('Scraping {}. Current threads: {} / {}. Links in queue: {}'.format(link,
          current_threads, MAX_THREADS, processing_links.qsize()))
    try:
        response = tor_get(link)

        status_code = response.status_code
        content = response.text

        if content:
            discovered_links = get_onion_links(content)
            new_links = 0
            for child_link in discovered_links:
                if child_link not in all_known_links:
                    new_links += 1
                    list_lock.acquire()
                    all_known_links.append(child_link)
                    processing_links.put(child_link)
                    list_lock.release()

            if running:
                print('Result: {} has {} child links ({} new)'.format(
                    link, len(discovered_links), new_links))

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
            print('[WARNING] No content. Status code {}: {} response status'.format(
                link, response.status_code))
            online_lock.acquire()
            with open(online_file_path, 'a') as result_file:
                result_file.write('{},{},{}\n'.format(
                    'No content', link, status_code))
            online_lock.release()
    except SSLError:
        print('[WARNING] {} has invalid SSL certificate'.format(link))
        status_code = 0
        title = 'Invalid SSL certificate'
        online_lock.acquire()
        with open(online_file_path, 'a') as result_file:
            result_file.write('{},{},{}\n'.format(
                'Invalid SSL Certificate', link, status_code))
        online_lock.release()
    except Timeout:
        print('[WARNING] {} timed out'.format(link))
        offline_lock.acquire()
        with open(offline_file_path, 'a') as result_file:
            result_file.write('{}\n'.format(link))
        offline_lock.release()
    except ConnError as e:
        print('[WARNING] {} cannot establish connection to host'.format(link))
        error_lock.acquire()
        if not os.path.exists(error_file_path):
            with open(error_file_path, 'w') as error_file:
                error_file.write('URL,Error')

        with open(error_file_path, 'a') as error_file:
            formatted_error = str(e).replace('\n', '\\n')
            if ',' in formatted_error:
                formatted_error = '"{}"'.format(formatted_error)
            error_file.write('{},{}\n'.format(link, formatted_error))
        error_lock.release()
    except Exception as e:
        print('[WARNING] {} exception {}'.format(link, e))
        error_lock.acquire()
        if not os.path.exists(error_file_path):
            with open(error_file_path, 'w') as error_file:
                error_file.write('URL,Error')

        with open(error_file_path, 'a') as error_file:
            formatted_error = str(e).replace('\n', '\\n')
            if ',' in formatted_error:
                formatted_error = '"{}"'.format(formatted_error)
            error_file.write('{},{}\n'.format(link, formatted_error))
        error_lock.release()

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


def load_known_links(result_folder_path, read_only=False):
    online_file_path = result_folder_path + 'online.csv'
    offline_file_path = result_folder_path + 'offline.csv'

    total_online = 0
    total_offline = 0

    known_links = []

    if not read_only:
        print('Loading known links')

    with open(online_file_path, 'r') as online_file:
        all_lines = online_file.readlines()[1:]
        total_online = len(all_lines)
        invalid = []
        for i, line in enumerate(all_lines):
            try:
                url = line.split(',')[1]
                known_links.append(url)
            except IndexError:
                invalid.append((i + 2, line.strip()))

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
            known_links.append(line)

    if read_only:
        return known_links

    all_known_links = known_links

    print('Found {} known links ({} online, {} offline)'.format(
        len(all_known_links), total_online, total_offline))


def load_pending_links(result_folder_path, read_only=False):
    pending_file_path = result_folder_path + 'pending.dat'

    if os.path.exists(pending_file_path):
        if not read_only:
            print('Loading pending links')

        with open(pending_file_path, 'r') as pending_file:
            links = [link.strip() for link in pending_file.readlines()
                     if link not in all_known_links]

        if read_only:
            return links

        for line in links:
            processing_links.put(line)
            all_known_links.append(line)

        print('Restored {} pending links'.format(len(links)))


def thread_pulse():
    global running
    interval = TIME_BETWEEN_REQUESTS / 1000
    while running:
        thread_throttle.set()
        time.sleep(interval)
