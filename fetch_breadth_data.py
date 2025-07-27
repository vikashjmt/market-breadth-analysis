import csv
import json
import argparse
import os

from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from icecream import ic
from pathlib import Path
from shutil import move
from datetime import datetime
from rich.console import Console

import pandas as pd

console = Console()
options = Options()
options.add_argument("--headless")  # Run in headless mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


def download_screener(url, dashboard=False):
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.get(url)
    sleep(10)
    # Locate the div containing "Market Breadth"
    if dashboard:
        market_breadth_div = driver.find_element(By.XPATH,
                                                 "//span[contains(text(), 'Market Breadth')]")
        # Click the div
        market_breadth_div.click()
        dom = driver.find_element(
            by=By.CSS_SELECTOR, value='a.flex.items-center')
    else:
        dom = driver.find_element(by=By.CSS_SELECTOR, value="a.btn-primary")

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


def process_ema_data(twenty_ema_data, Date, history_days):
    if not history_days:
        history_days = len(twenty_ema_data)
    ema_20_values = list(twenty_ema_data.values())[:history_days]
    ema_20_days = list(twenty_ema_data.keys())[:history_days]
    # ic(ema_20_values)
    # ic(ema_20_days)
    data_size = len(ema_20_values)
    # Reverse the date to show latest in last
    Date.reverse()
    Date = Date[-history_days:]
    start_index = -5
    end_index = 0
    index = 0
    while index <= data_size-5:
        if not index:
            last_5_values = ema_20_values[start_index:]
        else:
            last_5_values = ema_20_values[start_index:end_index]
        days = ema_20_days[start_index]
        print(f'\n{days.upper()} | {Date[index+4]}:')
        print(f'     #stocks > 20 ema (Last 5 days):\n'
              f'\t{", ".join(last_5_values[::-1])}')
        decide_market_status(last_5_values)
        index += 1
        start_index -= 1
        end_index -= 1


def decide_market_status(last_5_values):
    print(f'     Market Status:', end=' ')
    day1, day2, day3, day4, day5 = [int(val)
                                    for val in
                                    last_5_values]
    if day1 > 800:
        if (day1 > day2 > day3 > day4 > day5):
            if day1 < 1300:
                console.print('Light Green', style='green')
            if day1 > 1300:
                console.print('Bright Green', style='bold green')
                if day5 < 400:
                    console.print('Fresh Bullish trend possible',
                                  style='green')
        elif (day1 < day2 < day3 < max(day4, day5)):
            if day1 < 1200:
                console.print('[red] Light Red')
            else:
                console.print('[green] Bright to Light Green')
        elif all([(750 < int(val) < 1200) for val in last_5_values]):
            console.print('Yellow to Red', style='yellow')
        elif all([(900 < int(val) < 1300) for val in last_5_values]):
            console.print('[light_green] Yellow to Green')
        elif all([(450 < int(val) < 1100) for val in last_5_values]):
            console.print('[yellow] Red to Yellow')
        elif all([(1200 < int(val)) for val in last_5_values]):
            console.print('[light_green]Light Green')
        else:
            console.print('[light_green] Green to Yellow')
    elif day1 < 800:
        if (day1 < day2 < day3 < day4):
            console.print('[dark_red] Dark Red')
        elif (day1 > day2 > day3 > day4):
            console.print('[yellow] Red to Yellow')
        else:
            console.print('[red] Light Red')


def convert_to_json(csv_file):
    # Read the CSV and assign column names
    df = pd.read_csv(csv_file, header=None)
    df.columns = ['Datetime', 'Stock', 'Cap', 'Sector']

    # Group by 'Datetime' without sorting to preserve order
    counts = df.groupby('Datetime', sort=False).size()
    counts_dict = counts.to_dict()

    # Get json file name
    json_file = f"Report/{csv_file.rsplit('/')[-2]}.json"
    # Load existing data if the file exists
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    # Merge counts_dict into existing_data (update only changed/new keys)
    updated = False
    for k, v in counts_dict.items():
        if k not in existing_data or existing_data[k] != v:
            existing_data[k] = v
            updated = True
    # Write to JSON only if there's an update
    if updated:
        with open(json_file, 'w') as f:
            json.dump(existing_data, f, indent=2)
        # print(f"Updated {json_file}")
    else:
        # print(f"No update needed for {json_file}")
        pass
    return json_file


def get_market_status(counts):
    last = counts[-1]
    last_5 = counts[-5:]
    ascending_5 = all(earlier < later for earlier,
                      later in zip(last_5, last_5[1:]))
    descending_5 = all(earlier > later for earlier,
                       later in zip(last_5, last_5[1:]))

    # last, third last, and fifth last
    # indices: -1, -3, -5
    pos = [counts[-1], counts[-3], counts[-5]]
    inc = pos[0] > pos[1] > pos[2]
    dec = pos[0] < pos[1] < pos[2]

    if last > 150:
        if ascending_5:
            return "Very Bullish. Consider adding fresh entry"
        elif inc:
            return "Bullish"
        else:
            return "Neutral with Bullish bias"
    else:
        if descending_5:
            return "Very Bearish. Consider reducing portfolio and avoid fresh entry"
        elif dec:
            return "Bearish"
        else:
            return "Neutral with Bearish bias"


def analyze_json_data(json_file, screener_url):
    count_list = []
    with open(json_file) as fd:
        json_data = json.load(fd)
    # Write to txt file
    fd = open("continuity_screener_data_"
              f"{datetime.now().strftime('%d-%m-%Y')}.txt", 'a')
    if not json_data:
        # print('There is no data in the json')
        pass
    # Writing a comment
    fd.write(f'\nNumber of stocks screened from screener: {screener_url}')
    for date, stock_count in list(json_data.items())[-50:]:
        if '11:15' in date or ' 2:15' in date:
            fd.write(f'\n\t{date}: {stock_count}')
            count_list.append(stock_count)
    print('Stock_count :', count_list)
    if '10-21-50-200' in screener_url:
        status = get_market_status(count_list)
        fd.write(f'\nStatus: {status}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-days", type=int,
                        help="Get the analysis for the past given days")
    args = parser.parse_args()
    history_days = args.history_days
    # Map screener url with screener type and its destination folder
    data_dir = Path(__file__).parent
    config_file = f"{data_dir}/data_config.json"
    # Download screeners csvs
    data = get_data(config_file)
    # ic(data)
    for screener in data:
        screener_url = data[screener]['url']
        destination_folder = f"{data_dir}/{data[screener]['folder']}"
        Path(destination_folder).mkdir(parents=True,
                                       exist_ok=True)
        if 'dashboard' in screener_url:
            destination_file = (f"{destination_folder}/"
                                f"{datetime.today().strftime('%Y.%m.%d')}.csv")
        else:
            destination_file = (f"{destination_folder}/"
                                f"{datetime.today().strftime('%Y.%m.%d-%H')}.csv")
        if 'dashboard' in screener_url:
            # Check if file already exists
            # if not Path(destination_file).exists():
            download_screener(screener_url, dashboard=True)
            latest_file = get_latest_download()
            fetched_file = move(latest_file, destination_file)
            # else:
            #    fetched_file = destination_file
            #    print(f'It is coming here as {fetched_file}')
        else:
            download_screener(screener_url)
            latest_file = get_latest_download()
            fetched_file = move(latest_file, destination_file)

        if 'dashboard' in screener_url:
            # Get number of stocks above 20 ema data
            twenty_ema_data, Date = get_ema_data(fetched_file)
            # print(twenty_ema_data)
            # ic(Date)
            process_ema_data(twenty_ema_data, Date, history_days)
        else:
            json_file = convert_to_json(fetched_file)
            analyze_json_data(json_file, screener_url)
