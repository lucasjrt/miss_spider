import os
import sys

from src.crawler import crawl
from src.crawler import load_known_links, load_pending_links

output_directory = './results/'

def sanitize_pending(results_path):
    if results_path[-1] != '/':
        results_path += '/'

    pending_path = '{}pending.dat'.format(results_path)

    if not os.path.exists(pending_path):
        return

    print('Sanitizing pending links')
    pending_links = load_pending_links(results_path, read_only=True)
    known_links = load_known_links(results_path, read_only=True)

    print('Total pending before sanitizing: {}'.format(len(pending_links)))

    pending_links = list(dict.fromkeys(pending_links))

    for link in list(pending_links):
        if link in known_links:
            pending_links.remove(link)

    with open(pending_path, 'w') as pending:
        pending.writelines('\n'.join(pending_links))

    print('Total pending after sanitizing: {}'.format(len(pending_links)))


if __name__ == "__main__":
    initial_targets = []
    if len(sys.argv) <= 1:
        if not sys.stdin.isatty():
            for target in sys.stdin:
                initial_targets.append(target.strip())
        else:
            print('Usage: python app.py [URL]')
            sys.exit(1)
    else:
        for target in sys.argv[1:]:
            initial_targets.append(target.strip())

    sanitize_pending(output_directory)

    print("Targeting the following URL's:")
    for target in initial_targets:
        print('  - {}'.format(target))

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for target in initial_targets:
        online_file_path = output_directory + 'online.csv'
        offline_file_path = output_directory + 'offline.csv'

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        if not os.path.exists(online_file_path):
            with open(online_file_path, 'w') as online_file:
                online_file.write('Title,URL,Status\n')

        if not os.path.exists(offline_file_path):
            with open(offline_file_path, 'w') as offline_file:
                offline_file.write('URL\n')

        crawl(target, output_directory)
