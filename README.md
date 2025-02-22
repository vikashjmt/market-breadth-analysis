## Market-breadth-analysis of Indian Equity Market

This tool downloads market breadth data from [chartink](https://chartink.com/dashboard/86550) and make use of `the number of stocks above 20 dma` to analysze the status of the market.

It automatically generates the market report daily at 4:10 PM IST [here](Report/latest) using Github Action on this repo.

## Install and Setup Env
```
git clone https://github.com/vikashjmt/market-breadth-analysis.git
cd market-breadth-analysis
pip install -r requirements.txt

```

## Usage
```
market-breadth-analysis$ python3 fetch_breadth_data.py -h
usage: fetch_breadth_data.py [-h] [--history-days HISTORY_DAYS]

options:
  -h, --help            show this help message and exit
  --history-days HISTORY_DAYS
                        Get the analysis for the past given days


```

## Illustration
```
market-breadth-analysis$ python3 fetch_breadth_data.py --history-days 11               
                                                                                                                                       
DAY7 | 13th Feb:                                                                                                                       
     #stocks > 20 ema (Last 5 days):                                                                                                   
        732, 427, 189, 222, 228                                                                                                        
     Market Status:  Light Red                                                                                                         
                                                                                                                                       
DAY6 | 14th Feb:                                                                                                                       
     #stocks > 20 ema (Last 5 days):
        427, 189, 222, 228, 140
     Market Status:  Light Red

DAY5 | 17th Feb:
     #stocks > 20 ema (Last 5 days):
        189, 222, 228, 140, 156
     Market Status:  Light Red

DAY4 | 18th Feb:
     #stocks > 20 ema (Last 5 days):
        222, 228, 140, 156, 140
     Market Status:  Light Red

DAY3 | 19th Feb:
     #stocks > 20 ema (Last 5 days):
        228, 140, 156, 140, 233
     Market Status:  Light Red

DAY2 | 20th Feb:
     #stocks > 20 ema (Last 5 days):
        140, 156, 140, 233, 316
     Market Status:  Light Red

DAY1 | 21st Feb:
     #stocks > 20 ema (Last 5 days):
        156, 140, 233, 316, 304
     Market Status:  Light Red
```

