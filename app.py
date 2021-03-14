import sys

from src.crawler import crawl

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
    print(target)

  exit(0)
  crawl(initial_target)
