import csv
import json

from time import sleep
from selenium.webdriver.common.by import By
from selenium import webdriver
from icecream import ic
from pathlib import Path
from shutil import move
from datetime import datetime


def download_screener(url):
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    driver.get(url)
    sleep(10)
    dom = driver.find_element(by=By.CSS_SELECTOR, value='a.flex.items-center')
    ic(dom)
    sleep(10)
    dom.click()
    sleep(10)
    driver.quit()


def get_latest_download():
    download_folder = Path.home() / 'Downloads'
    # Get all csv files
    files = download_folder.glob('*csv')
    return max([file for file in files],
               key=lambda item: item.stat().st_ctime)


def get_data(config_file):
    with open(config_file) as fd:
        data = json.load(fd)
    return data


def get_ema_data(input_csv):
    with open(input_csv) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        breadth_details = {}
        Date = []
        for row in csv_reader:
            if line_count:
                day_num, day, num_above_20_ema = (f'day{line_count}', row[0],
                                                  row[5])
                breadth_details[day_num] = num_above_20_ema
                Date.append(day)
                line_count += 1
            else:
                line_count += 1

        return breadth_details, Date


def process_ema_data(twenty_ema_data, Date):
    num_days_data = 400
    ema_20_values = list(twenty_ema_data.values())[:num_days_data]
    ema_20_days = list(twenty_ema_data.keys())[:num_days_data]
    ic(ema_20_values)
    ic(ema_20_days)
    data_size = len(ema_20_values)
    # Reverse the date to show latest in last
    Date.reverse()
    Date = Date[-num_days_data:]
    start_index = -5
    end_index = 0
    index = 0
    while index <= data_size-5:
        if not index:
            last_5_values = ema_20_values[start_index:]
        else:
            last_5_values = ema_20_values[start_index:end_index]
        days = ema_20_days[start_index]
        print('---------------------------')
        print(days)
        print(Date[index+4])
        print(last_5_values[::-1])
        decide_market_status(last_5_values)
        index += 1
        start_index -= 1
        end_index -= 1


def decide_market_status(last_5_values):
    day1, day2, day3, day4, day5 = [int(val)
                                    for val in
                                    last_5_values]
    if day1 > 800:
        if (day1 > day2 > day3 > day4 > day5):
            if day1 < 1300:
                print('Light Green')
            if day1 > 1300:
                print('Bright Green')
                if day5 < 400:
                    print('Fresh Bullish trend possible')
        elif (day1 < day2 < day3 < max(day4, day5)):
            if day1 < 1200:
                print('Light Red')
            else:
                print('Bright to Light Green')
        elif all([(750 < int(val) < 1200) for val in last_5_values]):
            print('Yellow to Red')
        elif all([(900 < int(val) < 1300) for val in last_5_values]):
            print('Yellow to Green')
        elif all([(450 < int(val) < 1100) for val in last_5_values]):
            print('Red to Yellow')
        elif all([(1200 < int(val)) for val in last_5_values]):
            print('Light Green')
        else:
            print('Green to Yellow')
    elif day1 < 800:
        if (day1 < day2 < day3 < day4):
            print('Dark Red')
        elif (day1 > day2 > day3 > day4):
            print('Red to Yellow')
        else:
            print('Light Red')


if __name__ == "__main__":
    # Map screener url with screener type and its destination folder
    data_dir = Path(__file__).parent
    config_file = f"{data_dir}/data_config.json"
    ic(config_file)
    # Download screeners csvs
    data = get_data(config_file)
    ic(data)
    for screener in data:
        screener_url = data[screener]['url']
        destination_folder = f"{data_dir}/{data[screener]['folder']}"
        Path(destination_folder).mkdir(parents=True,
                                       exist_ok=True)
        destination_file = (f"{destination_folder}/"
                            f"{datetime.today().strftime('%Y.%m.%d')}.csv")
        download_screener(screener_url)
        latest_file = get_latest_download()
        ic(latest_file)
        fetched_file = move(latest_file, destination_file)
        ic(fetched_file)

    # Get number of stocks above 20 ema data
    twenty_ema_data, Date = get_ema_data(fetched_file)
    print(twenty_ema_data)
    ic(Date)
    process_ema_data(twenty_ema_data, Date)
