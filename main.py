import cv2
import sys
import pytesseract
import os
import re
import ffmpeg

script_path = os.path.dirname(os.path.realpath(__file__))


class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_progress(index, total, frame):
    bar_length = 20
    percent = float(index) / total
    hashes = '#' * int(round(percent * bar_length))
    spaces = ' ' * (bar_length - len(hashes))
    sys.stdout.write("\r{0}[{1}]{2} Frame: {3}\t".format(BColors.OKCYAN, hashes + spaces, BColors.ENDC, int(frame)))
    sys.stdout.flush()


def read_time(path, area):
    cap = cv2.VideoCapture(path)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if abs(area) >= total_frames:
        print(BColors.FAIL + 'Area is longer than video!' + BColors.ENDC)
        cap.release()
        return None

    start_index = 0

    if area >= 0:
        end_index = area
    else:
        start_index = total_frames + area
        end_index = total_frames - 1

    results = []
    result_frames = {}

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_index)
    i = start_index
    while cap.isOpened() and i <= end_index:
        ret, frame = cap.read()

        if not ret:
            print(BColors.FAIL + 'Error reading frame {0}!'.format(int(i)) + BColors.ENDC)
            i += 1
            continue

        cropped = frame[430:472, 500:640]

        ocr = pytesseract.image_to_string(cropped,
                                          config='--psm 8 -c tessedit_char_whitelist=0123456789:').replace('\n',
                                                                                                           '')
        if re.match(r'^\d\d:\d\d$', ocr):
            results.append(ocr)
            result_frames[ocr] = i

        print_progress(i - start_index, end_index - start_index, i)

        i += 1

    cap.release()

    if len(results) == 0:
        print(BColors.FAIL + 'No time found!' + BColors.ENDC)
        return None

    most_common = max(set(results), key=results.count)
    print(BColors.WARNING + 'Time read: ' + most_common + BColors.ENDC, results)
    return most_common


def parse_time(time):
    time = time.split(':')
    return int(time[0]) * 60 + int(time[1])


def match_times(path1, path2, area=30, tolerance=10):
    print('Reading last {0} frames of {1}{2}{3}:'.format(area, BColors.HEADER, os.path.split(path1)[-1], BColors.ENDC))
    time1 = read_time(path1, -int(area))
    if time1 is None:
        return False
    print('Reading first {0} frames of {1}{2}{3}:'.format(area, BColors.HEADER, os.path.split(path2)[-1], BColors.ENDC))
    time2 = read_time(path2, int(area))
    if time2 is None:
        return False

    diff = abs(parse_time(time1) - parse_time(time2))
    match = diff <= tolerance
    print('Difference: {0} sec {1} Tolerance: {2} sec. {3}'
          .format(diff, '<' if match else '>', tolerance,
                  (BColors.OKGREEN + 'Matched!' if match else BColors.FAIL + 'No match!') + BColors.ENDC))

    return match


def get_files(path):
    files = []
    directory = os.fsencode(path)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".AVI"):
            files.append(os.path.join(path, filename))
    return files


# get files from path, try to match each file with the next one, if two files match, add them to an array in matches,
# if the next one matches as well, add it to that array
def get_matches(path, area=30, tolerance=10, use_cache=True):
    print('Searching for matches in {0}{1}{2} with area {3} and tolerance {4}...'.format(BColors.WARNING, path,
                                                                                         BColors.ENDC, area, tolerance))
    if use_cache:
        cache = set()
        if os.path.isfile(script_path + '/cache.txt'):
            with open(script_path + '/cache.txt', 'r') as f:
                cache = set(f.read().splitlines())
        print(BColors.BOLD + 'Using cache: {0} files are being excluded.'.format(len(cache)) + BColors.ENDC)

    files = get_files(path)
    matches = []
    if os.path.isfile(script_path + '/matches.txt'):
        with open(script_path + '/matches.txt', 'r') as f:
            matches = [x.split(',') for x in f.read().splitlines()]
    for i in range(len(files) - 1):
        if use_cache and files[i] in cache:
            continue
        if match_times(files[i], files[i + 1], area, tolerance):
            if len(matches) == 0 or matches[-1][-1] != files[i]:
                matches.append([files[i], files[i + 1]])
            else:
                matches[-1].append(files[i + 1])
            with open(script_path + '/matches.txt', 'w') as f:
                for match in matches:
                    f.write(','.join(match) + '\n')
        if use_cache:
            cache.add(files[i])
            with open(script_path + '/cache.txt', 'w') as f:
                for file in cache:
                    f.write(file + '\n')
            print(BColors.BOLD + 'Cache updated. Excluded files: {0}'.format(len(cache)) + BColors.ENDC)

    return matches


def merge_matches(matches, output_path, delete=False):
    print('Merging {0} matches into {1}:'.format(len(matches), output_path))
    for match in matches:
        print(
            'Merging {0}{1}{2}...'.format(BColors.WARNING, ' & '.join([os.path.split(x)[-1] for x in match]),
                                          BColors.ENDC))
        with open(script_path + '/tmp.txt', 'w') as f:
            for file in match:
                f.write("file '{0}'\n".format(file))
        ffmpeg \
            .input(script_path + '/tmp.txt', format='concat', safe=0) \
            .output(os.path.join(output_path, '_'.join([os.path.split(x)[-1].split('.')[0] for x in match]) + '.AVI'),
                    c='copy') \
            .global_args('-loglevel', 'error') \
            .global_args('-y') \
            .run()
        if delete:
            for file in match:
                os.remove(file)

    os.remove(script_path + '/tmp.txt')


merge_matches(get_matches(sys.argv[1]), sys.argv[2])
