import os
import sys

from src.crawler import crawl

output_directory = './results/'

if __name__ == "__main__":
  initial_targets = []
  if not len(sys.argv) > 1:
    if not sys.stdin.isatty():
      for target in sys.stdin:
        initial_targets.append(target.strip())
    else:
      print('Usage: python app.py [URL]')
      exit(1)
  else:
    for target in sys.argv[1:]:
      initial_targets.append(target.strip())

  print("Targeting the following URL's:")
  for target in initial_targets:
    print('    - {}'.format(target))

  if not os.path.exists(output_directory):
    os.makedirs(output_directory)

  for target in initial_targets:
    parsed_target = target.replace('/', '_')
    result_file_path = output_directory + parsed_target + '.csv'
    if not os.path.exists(result_file_path):
      with open(result_file_path, 'w') as result_file:
        result_file.write('Title,URL\n')
    crawl(target, result_file_path)
