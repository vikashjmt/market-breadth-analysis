import csv
import json
import argparse
import os

from time import sleep
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from icecream import ic
from pathlib import Path
from shutil import move
from datetime import datetime
from ordered_set import OrderedSet
from rich.console import Console

import pandas as pd

user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
console = Console()
options = Options()
options.add_argument("--headless")  # Run in headless mode
options.add_argument("--window-size=1920,1080")
options.add_argument(f'user-agent={user_agent}')
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

MB_CONSOLIDATION_FILE = "market_breadth/consolidated_market_breadth.csv"
INDEX_VALUE_FILE = "market_breadth/index_value.txt"
MB_ANALYSIS_FILE = "market_breadth/analysis.txt"


def download_screener(url, dashboard=False):
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    driver.get(url)
    # Let page load initial layout
    sleep(8)

    if dashboard:
        # Click the Market Breadth pane/title
        market_breadth_div = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(., 'Market Breadth')]"))
        )
        market_breadth_div.click()
        sleep(7)
        csv_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='CSV']"))
        )
        sleep(6)
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
        csv_button.click()
        # Use the below one if above click does not work
        # driver.execute_script("arguments[0].click();", csv_button)

    # Normal Screener Page (Non-dashboard)
    else:
        # Wait for screener’s download button
        dom = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(text(), 'Download csv')]"))
        )
        dom.click()
        # print("Downloading CSV...")

    # Give 10s time for download (safest across systems)
    sleep(10)
    driver.quit()


def get_latest_download():
    download_folder = Path.home() / 'Downloads'
    # Get all csv files
    files = download_folder.glob('*csv')
    # print(f'Download folder: {download_folder}')
    files = list(files)
    if not files:
        raise FileNotFoundError("No CSV files found in Downloads")

    return max(files,
               key=lambda item: item.stat().st_mtime)


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
    print('     Market Status:', end=' ')
    day1, day2, day3, day4, day5 = [int(val)
                                    for val in
                                    last_5_values]
    if day1 > 1400:
        if 0 <= day1-day2 <= 25:
            console.print('MB losing steam, may top out soon')
        elif day1-day2 < 0:
            console.print('MB topped out today')

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
                console.print('[red] Light Red. Could be right time'
                              ' to panic and tighten the stop loss')
            else:
                console.print('[green] Bright to Light Green,'
                              ' market losing momentum')
        elif all([(750 < int(val) < 1200) for val in last_5_values]):
            console.print('Yellow to Red', style='yellow')
        elif all([(900 < int(val) < 1300) for val in last_5_values]):
            console.print('[light_green] Yellow to Green.')
            if (day1 > max(day2, day3, day4, day5)):
                console.print('\t Market could be ready for minor rally')
        elif all([(450 < int(val) < 1100) for val in last_5_values]):
            console.print('[yellow] Red to Yellow')
        elif all([(1200 < int(val)) for val in last_5_values]):
            console.print('[light_green]Light Green')
        else:
            console.print('[light_green] Green-Yellow (non-trending phase)')
    elif day1 < 800:
        if day1 < 220:
            console.print('Extreme panic. Might see short/long term'
                          ' bottom soon')
        if (day1 < day2 < day3 < day4):
            console.print('[dark_red] Dark Red')
        elif (day1 > day2 > day3 > day4):
            console.print('[yellow] Red to Yellow')
            if (day5 < min(day2, day3, day4, day1)):
                console.print('Market might have bottomed for short/long '
                              'term. Beware of 3 phases of bear market '
                              'downfall')
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


def get_market_status(counts, avg_10, avg_25, avg_50):
    last = counts[-1]
    last_5 = counts[-5:]
    ascending_5 = all(earlier < later for earlier,
                      later in zip(last_5, last_5[1:]))
    descending_5 = all(earlier > later for earlier,
                       later in zip(last_5, last_5[1:]))
    above_all_mas = all(last > ma for ma in [avg_10, avg_25, avg_50])
    below_all_mas = all(last < ma for ma in [avg_10, avg_25, avg_50])

    # last, third last, and fifth last
    # indices: -1, -3, -5
    pos = [counts[-1], counts[-3], counts[-5]]
    inc = pos[0] > pos[1] > pos[2]
    dec = pos[0] < pos[1] < pos[2]

    if last > 150:
        if ascending_5 and above_all_mas:
            return "Very Bullish. Consider adding fresh entry."
        elif inc or above_all_mas:
            return "Bullish."
        elif below_all_mas or descending_5:
            return "Trend changing from Bullish to Bearish!"
        else:
            return "Non trending with Bullish bias."
    else:
        if (descending_5 or below_all_mas):
            if last > 100:
                return ("Very Bearish. Consider reducing portfolio "
                        "and avoid fresh entry.")
            else:
                return "Very Bearish."
        elif dec or below_all_mas:
            return "Bearish."
        elif above_all_mas or ascending_5:
            return "Trend changing from Bearish to Bullish!"
        else:
            return "Non-trending with Bearish bias."


def get_market_status_by_macdxover(count_list):
    last = count_list[-1]
    last_3 = count_list[-3:]
    ascending_3 = all(earlier < later for earlier,
                      later in zip(last_3, last_3[1:]))
    descending_3 = all(earlier > later for earlier,
                       later in zip(last_3, last_3[1:]))
    ma_5 = sum(count_list[-5:])/5
    if ascending_3 and last > ma_5:
        status = 'Very Bullish'
    elif descending_3 and last < ma_5:
        status = 'Very Bearish'
    elif last > ma_5:
        status = 'Neutral with Bullish bias'
    else:
        status = 'Neutral with Bearish bias'
    return status


def analyze_weekly_macd_xover_data(json_file, screener_url):
    count_list = []
    prev_status = ''
    weekly_date_status = {}
    with open(json_file) as fd:
        json_data = json.load(fd)
    # Update the summary of the MACD analysis to other txt file
    fd_other = open(f"continuity_screener_hourly_"
                    f"{datetime.now().strftime('%d-%m-%Y')}.txt", 'a')
    # Write to txt file
    fd = open("continuity_macd_data_"
              f"{datetime.now().strftime('%d-%m-%Y')}.txt", 'a')
    # Writing a comment
    fd.write(f'\nAnalysis on the weekly macd xOver screener: {screener_url}')
    fd_other.write(
        f'\n\nAnalysis on the weekly macd xOver screener: {screener_url}')
    for date, stock_count in list(json_data.items()):
        count_list.append(stock_count)
        if len(count_list) < 5:
            continue
        # fd.write(f'\n{date}: {stock_count}')
        # Write a function here to get market status of past
        status = get_market_status_by_macdxover(count_list)
        weekly_date_status[date] = status
    fd.write(f'\n    Current market status: {status}')
    fd_other.write(f'\n    Current market status: {status}')
    fd.write('\n\nHistorical MACD data:')
    same_status_date = OrderedSet()
    for date in reversed(weekly_date_status):
        curr_status = weekly_date_status[date]
        if prev_status == curr_status:
            same_status_date.add(prev_date)
            same_status_date.add(date)
        else:
            if not same_status_date:
                pass  # Skip first iteration
            else:
                same_status_date.items.reverse()
                fd.write(f'\n\n    {prev_status} since {len(same_status_date)}'
                         f' weeks: {same_status_date.items}')
            same_status_date = OrderedSet([date])
            prev_date = date
        prev_status = curr_status


def get_market_status_by_macdxdown(count_list):
    last = count_list[-1]
    last_3 = count_list[-3:]
    ascending_3 = all(earlier < later for earlier,
                      later in zip(last_3, last_3[1:]))
    descending_3 = all(earlier > later for earlier,
                       later in zip(last_3, last_3[1:]))
    ma_5 = sum(count_list[-5:])/5
    if ascending_3 and last > ma_5:
        status = 'Very Bearish'
    elif descending_3 and last < ma_5:
        status = 'Very Bullish'
    elif last > ma_5:
        status = 'Neutral with Bearish bias'
    else:
        status = 'Neutral with Bullish bias'
    return status


def analyze_weekly_macd_xdown_data(json_file, screener_url):
    count_list = []
    prev_status = ''
    weekly_date_status = {}
    with open(json_file) as fd:
        json_data = json.load(fd)
    # Write to txt file
    fd = open("continuity_macd_data_"
              f"{datetime.now().strftime('%d-%m-%Y')}.txt", 'a')
    # Update the summary of the MACD analysis to other txt file
    fd_other = open(f"continuity_screener_hourly_"
                    f"{datetime.now().strftime('%d-%m-%Y')}.txt", 'a')
    # Writing a comment
    fd.write(f"\n\n{'*'*80}")
    fd.write(f'\nAnalysis on the weekly macd xDown screener: {screener_url}')
    fd_other.write(
        f'\n\nAnalysis on the weekly macd xDown screener: {screener_url}')
    for date, stock_count in list(json_data.items()):
        count_list.append(stock_count)
        if len(count_list) < 5:
            continue
        # fd.write(f'\n{date}: {stock_count}')
        # Write a function here to get market status of past
        status = get_market_status_by_macdxdown(count_list)
        weekly_date_status[date] = status
    fd.write(f'\n    Current market status: {status}')
    fd_other.write(f'\n    Current market status: {status}')
    fd.write('\n\nHistorical MACD data:')
    same_status_date = OrderedSet()
    for date in reversed(weekly_date_status):
        curr_status = weekly_date_status[date]
        if prev_status == curr_status:
            same_status_date.add(prev_date)
            same_status_date.add(date)
        else:
            if not same_status_date:
                pass  # Skip first iteration
            else:
                same_status_date.items.reverse()
                fd.write(f'\n\n    "{prev_status}" since {len(same_status_date)}'
                         f' weeks: {same_status_date.items}')
            same_status_date = OrderedSet([date])
            prev_date = date
        prev_status = curr_status


def update_breadth_csv(old_path: str, new_path: str, out_path: str = None) -> None:
    """
    old_path: path to existing (previous) CSV
    new_path: path to newly downloaded CSV (newest date at top)
    out_path: where to write updated CSV; if None, overwrite old_path
    """

    # 1. Read previous file completely (header + rows)
    with open(old_path, newline="", encoding="utf-8") as f_old:
        reader_old = list(csv.reader(f_old))

    if not reader_old:
        # No data in previous file, just copy new file over it
        if out_path is None:
            out_path = old_path
        with open(new_path, newline="", encoding="utf-8") as f_new, \
                open(out_path, "w", newline="", encoding="utf-8") as f_out:
            for line in f_new:
                f_out.write(line)
        return

    header_old = reader_old[0]
    old_rows = reader_old[1:]

    # Top row date in previous file (first data row, column 0)
    if not old_rows:
        top_prev_date = None
    else:
        top_prev_date = old_rows[0][0]

    # 2. Read new downloaded file completely
    with open(new_path, newline="", encoding="utf-8") as f_new:
        reader_new = list(csv.reader(f_new))

    if not reader_new:
        # New file is empty; nothing to do
        return

    header_new = reader_new[0]
    new_rows = reader_new[1:]

    # if header_old != header_new:
    #     raise ValueError("Header mismatch between old and new CSV files")

    if top_prev_date is None:
        # No old rows; all new_rows are new, just use new file
        if out_path is None:
            out_path = old_path
        with open(out_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(header_new)
            writer.writerows(new_rows)
        return

    # 3. Compare top dates: if same, exit (no update)
    if not new_rows:
        # New file has only header and no data; nothing to do
        return

    top_new_date = new_rows[0][0]

    if top_new_date == top_prev_date:
        # Top dates are same, no new data; exit
        return

    # 4. Traverse new_rows and collect rows until top_prev_date is found
    temp_rows = []  # rows to prepend
    found_top_prev = False

    for row in new_rows:
        row_date = f"{row[0]} {datetime.now().year}"


        if row_date == top_prev_date:
            found_top_prev = True
            break
        else:
            # Temporarily record this row
            temp_rows.append(row)

    # If never found, you have two choices:
    # (a) treat all rows as new, or
    # (b) do nothing because something is inconsistent.
    # Here, use (a): all rows are new.
    if not found_top_prev:
        temp_rows = new_rows

    # 5. Write updated file with new rows on top (recorded order, then old data)
    if out_path is None:
        out_path = old_path

    with open(out_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header_old)
        # new rows first (on top)
        for row in temp_rows:
            writer.writerow(row)
        # then all previous rows
        for row in old_rows:
            writer.writerow(row)


def analyze_json_data(json_file, screener_url):
    count_list = []
    all_counts = []
    if '10-21-50-200' in screener_url:
        file_prefix = 'continuity_screener_hourly_'
    else:
        file_prefix = 'continuity_screener_multi_interval_'
    with open(json_file) as fd:
        json_data = json.load(fd)
    # Write to txt file
    fd = open(f"{file_prefix}"
              f"{datetime.now().strftime('%d-%m-%Y')}.txt", 'a')
    if not json_data:
        # print('There is no data in the json')
        pass
    # Writing a comment
    fd.write(f'\nNumber of stocks screened from screener: {screener_url}')
    for date, stock_count in list(json_data.items())[-50:]:
        if '11:15' in date or ' 2:15' in date:
            # fd.write(f'\n\t{date}: {stock_count}')
            count_list.append(stock_count)
    fd.write(f'\n\nLast 15 3-hour stock counts:\n{count_list}\n')
    for date, stock_count in list(json_data.items()):
        if '11:15' in date or ' 2:15' in date:
            all_counts.append(stock_count)
    ten_days_avg = sum(all_counts[-20:])/20
    ma_25_days = sum(all_counts[-50:])/50
    ma_50_days = sum(all_counts[-100:])/100
    fd.write(f'\nAvg of last 10 days: {ten_days_avg}')
    fd.write(f'\nAvg of last 25 days: {ma_25_days}')
    fd.write(f'\nAvg of last 50 days: {ma_50_days}')
    if '10-21-50-200' in screener_url:
        status = get_market_status(count_list, ten_days_avg, ma_25_days,
                                   ma_50_days)
        star_pattern = '*'*25
        fd.write(f'\n{star_pattern}\nStatus: {status}\n{star_pattern}\n')


def moving_averages(data, periods=[10, 20, 50, 200]):
    n = len(data)

    # Compute prefix sums for O(1) range-sum
    prefix = [0]
    for x in data:
        prefix.append(prefix[-1] + int(x))

    result = []

    for i in range(n):
        idx_result = {}
        for p in periods:
            end = i + p
            if end <= n:
                # Average = (sum from i to i+p-1) / p
                s = prefix[end] - prefix[i]
                idx_result[f"ma{p}"] = s / p
            else:
                idx_result[f"ma{p}"] = 0   # Not enough data
        result.append(idx_result)

    return result


def detect_crossovers(ma_list, Date):
    # Process from oldest → newest
    rev = list(ma_list)
    # Print
    with open(INDEX_VALUE_FILE, 'w') as index_file:
        for index in range(len(rev)):
            print(f'{index}: Date: {Date[index]}, Values={rev[index]}',
                  file=index_file)
        """
        current = rev[index]
        print(f"Index:{index}", end=' ')
        if current['ma10'] > current['ma20']:
            print('ma10 > ma20', end=' ')
        else:
            print('ma10 < ma20', end=' ')
        if current['ma20'] > current['ma50']:
            print('ma20 > ma50', end=' ')
        else:
            print('ma20 < ma50', end=' ')
        if current['ma50'] > current['ma200']:
            print('ma50 > ma200')
        else:
            print('ma50 < ma200')
        """
    list_line = []
    for i in range(len(rev)-1, -1, -1):
        prev = rev[i]
        curr = rev[i-1]
        # print(f"{i}:", end=' ', file=analysis_file)
        line = f'\t{Date[i]:15}: '
        if prev['ma10'] > prev['ma20']:
            # print('ma10 > ma20', end=' ', file=analysis_file)
            line += 'ma10 > ma20'
        else:
            # print('ma10 < ma20', end=' ', file=analysis_file)
            line += 'ma10 < ma20'
        if prev['ma20'] > prev['ma50']:
            # print(' > ma50', end=' ', file=analysis_file)
            line += ' > ma50'
        else:
            # print(' < ma50', end=' ', file=analysis_file)
            line += ' < ma50'
        if prev['ma50'] > prev['ma200']:
            # print(' > ma200', file=analysis_file)
            line += ' > ma200'
        else:
            # print(' < ma200', file=analysis_file)
            line += ' < ma200'

        # Short-term bullish
        if prev["ma20"] < prev["ma50"] and curr["ma20"] > curr["ma50"]:
            if curr["ma50"] > curr["ma200"]:
                # print(f"Index {i}: Strong Bullish momentum", file=analysis_file)
                line += f"\nIndex {i}({Date[i]}): Strong Bullish momentum"
            else:
                # print(f"Index {i}: Weak Bullish momentum", file=analysis_file)
                line += f"\nIndex {i}({Date[i]}): Weak Bullish momentum"

        # Short-term bearish
        if prev["ma20"] > prev["ma50"] and curr["ma20"] < curr["ma50"]:
            if curr["ma50"] > curr["ma200"]:
                # print(f"Index {i}: Short-term Bearish momentum", file=analysis_file)
                line += f"\nIndex {i}({Date[i]}): Short-term Bearish momentum"
            else:
                # print(f"Index {i}: Strong Bearish momentum", file=analysis_file)
                line += f"\nIndex {i}({Date[i]}): Strong Bearish momentum"

        # Long-term bullish
        if prev["ma50"] < prev["ma200"] and curr["ma50"] > curr["ma200"]:
            if curr["ma20"] > curr["ma50"]:
                # print(f"Index {i}: Start of Long-term Bullish market", file=analysis_file)
                line += f"\nIndex {i}({Date[i]}): Start of Long-term Bullish market"
        # Long-term bearish
        if prev["ma50"] > prev["ma200"] and curr["ma50"] < curr["ma200"]:
            if curr["ma20"] < curr["ma50"]:
                # print(f"Index {i}: Start of Long-term Bearish market", file=analysis_file)
                line += f"\nIndex {i}({Date[i]}): Start of Long-term Bearish market"
        # Update to list
        list_line.append(line)
        # Update to file in reverse order
    with open(MB_ANALYSIS_FILE, 'w') as analysis_file:
        for line in reversed(list_line):
            print(line, file=analysis_file)
    print(f"\nToday's MB status:\n{list_line[-1]}")
    print(('\nMarket Breadth MA analysis link: '
           'https://github.com/vikashjmt/market-breadth-analysis/blob/main/market_breadth/analysis.txt'))


def get_and_process_ma_values(twenty_ema_data, Date):
    ema_20_values = list(twenty_ema_data.values())
    out = moving_averages(ema_20_values)
    # ic(out)
    # for index in range(len(out)):
    #    print(f'{index}: {out[index]}')
    detect_crossovers(out, Date)


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
        # print(f'Destination folder: {destination_folder}')
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
            print(f'Processing url : {screener_url}')
            download_screener(screener_url, dashboard=True)
            latest_file = get_latest_download()
            fetched_file = move(latest_file, destination_file)
        else:
            download_screener(screener_url)
            latest_file = get_latest_download()
            fetched_file = move(latest_file, destination_file)

        if 'dashboard' in screener_url:
            # Update the consolidated csv
            update_breadth_csv(MB_CONSOLIDATION_FILE,
                               fetched_file)
            # Get number of stocks above 20 ema data
            twenty_ema_data, Date = get_ema_data(MB_CONSOLIDATION_FILE)
            # print(twenty_ema_data)
            # ic(Date)
            get_and_process_ma_values(twenty_ema_data, Date)
            process_ema_data(twenty_ema_data, Date, history_days)
        else:
            json_file = convert_to_json(fetched_file)
            if 'macd-crossover' in screener_url:
                if (datetime.today().weekday() == 2 or datetime.today().weekday() == 5 or
                        datetime.today().weekday() == 4):
                    analyze_weekly_macd_xover_data(json_file,
                                                   screener_url)
            elif 'macd-crossdown' in screener_url:
                if (datetime.today().weekday() == 2 or datetime.today().weekday() == 5 or
                        datetime.today().weekday() == 4):
                    analyze_weekly_macd_xdown_data(json_file,
                                                   screener_url)
            else:
                analyze_json_data(json_file, screener_url)
