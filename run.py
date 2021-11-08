# --------------------------------------------------------------------------
# Wahlpypa
#
# A simple python script to create desktop wallpaper from the satellite
# landscapes extracted from Google Earth... with a slight Australian accent.
#
# See the README.md file for more information.
# -----------------------------------------------------------------------------
import sys
import requests
import random
import os
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from tqdm import trange
from PIL import Image, ImageEnhance
from configparser import ConfigParser

# -----------------------------------------------------------------------------
# CONFIGURATION
#
# If you want to change the default settings, you need to add a new section
# to the config.ini file in the same directory as this script. Once you have
# added the new section, you can edit the setting below to use the new values
# from config.ini by setting the USE_SECTION variable to the value of the
# new section name.
#
USE_SECTION = 'DEFAULT'
# -----------------------------------------------------------------------------

config = ConfigParser()
config.read('config.ini')
persistent_data_file = config.get(USE_SECTION, 'name_of_persistent_data_file')
starting_position = config.getint(USE_SECTION, 'starting_position')
days_to_keep_data = config.getint(USE_SECTION, 'days_to_keep_data')
ending_position = config.getint(USE_SECTION, 'ending_position')
max_images_to_download = config.getint(USE_SECTION, 'max_images_to_download')
img_path = Path(Path(__file__).parent, 'img').as_posix() + '/'


def create_data_file(file):
    path = Path(Path(__file__).parent, 'data', file)
    path.touch(exist_ok=True)
    return path


def check_last_update(file):
    mod_time = file.stat().st_mtime
    date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d')
    return date


def next_update_due(days):
    past = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    return past


def stale_data_check(file, frequency):
    boolean = next_update_due(frequency) > check_last_update(file)
    return boolean


def update_data_file(file, start_position, end_position):
    i = start_position
    end = start_position + end_position
    stem = 'https://earthview.withgoogle.com/download/'
    with open(file, 'w+') as f:
        while i < end:
            for _ in trange((end - start_position), desc='Updating Data File'):
                response = requests.head(stem + str(i) + '.jpg')
                if response.status_code == 200:
                    f.write(str(i) + '\n')
                i += 1


def select_image_set(file, number_of_images):
    i = 0
    id_list = []
    selections = []
    with open(file) as ids:
        for number in ids:
            id_list.append(number.strip())
    while i <= number_of_images:
        try:
            selection = random.choice(id_list)
            if selection not in selections:
                selections.append(selection)
                i += 1
            else:
                continue
        except IndexError:
            sys.exit(f'No image ids available. Check {file} for values. \n'
                     f'If empty, increase max_number_of_image_ids_in_file')

    return selections


def grab_wallpaper(file, save_path, max_per_day):
    stem = 'https://earthview.withgoogle.com/download/'
    random_selections = select_image_set(file, max_per_day)
    total = len(random_selections) - 1
    for _ in trange((total - 0), desc='Downloading & Processing Images'):
        for identifier in random_selections:
            file_name = str(identifier) + '.jpg'
            url = stem + file_name
            response = requests.head(url)
            if response.status_code == 200:
                with open(save_path + file_name, 'wb') as photo:
                    for chunk in requests.get(url, stream=True).iter_content(chunk_size=1024):
                        photo.write(chunk)
                darken_image(save_path, save_path + file_name)
            else:
                continue


def darken_image(path, file):
    img = Image.open(file)
    img = img.convert('RGB')
    img = ImageEnhance.Brightness(img).enhance(0.5)
    file_name = file.split('/')[-1]
    img.save(path + 'dark_' + file_name)
    for filename in os.listdir(path):
        if not filename.startswith('dark_') and filename.endswith('.jpg'):
            Path(path + filename).unlink()
        else:
            continue


def cleanup():
    for filename in os.listdir(img_path):
        if filename.endswith('.jpg'):
            Path(img_path + filename).unlink()
        else:
            continue
# -----------------------------------------------------------------------------


if __name__ == '__main__':
    # Remove any previously downloaded images to avoid
    # filling up the hard drive and causing errors
    cleanup()

    # If it doesn't exist, create the data file
    # that will store the image ids
    file = create_data_file(persistent_data_file)

    # If the persistent data file exceeds the days_to_keep_data value,
    # update it. This will allow the script to download the latest images
    # and process them. Note: depending on the range of image ids to be
    # checked, this may take a while.
    if stale_data_check(file, days_to_keep_data):
        update_data_file(file, starting_position, ending_position)
    else:
        print('Skipping... data file is up-to-date')

    # Download the images and process them.
    grab_wallpaper(file, img_path, max_images_to_download)
