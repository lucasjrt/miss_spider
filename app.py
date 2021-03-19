import os
import sys

from src.crawler import crawl

output_directory = './results/'

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

    print("Targeting the following URL's:")
    for target in initial_targets:
        print('  - {}'.format(target))

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for target in initial_targets:
        parsed_target = target.replace('/', '_')
        result_directory_path = output_directory + '{}/'.format(parsed_target)

        online_file_path = result_directory_path + 'online.csv'
        offline_file_path = result_directory_path + 'offline.csv'

        if not os.path.exists(result_directory_path):
            os.makedirs(result_directory_path)

        if not os.path.exists(online_file_path):
            with open(online_file_path, 'w') as online_file:
                online_file.write('Title,URL,Status\n')

        if not os.path.exists(offline_file_path):
            with open(offline_file_path, 'w') as offline_file:
                offline_file.write('URL\n')

        crawl(target, result_directory_path)
