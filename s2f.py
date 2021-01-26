import asyncio
import requests
import time
import os
import json
import sys

out_path = ""
proxies = {}

endpoint = "https://chain.api.btc.com/v3/block/date/"
start_time = 1231430400 * 1000 # 2009/01/09, the 2nd block
step_time = 86400 * 1000
end_time = 1611331200 * 1000 # 2021/01/23, the end time
start_stock = 50
halving_schedule = {0 : 50, 210000 : 25, 420000 : 12.5, 630000 : 6.25, 840000 : 3.125}


def get_stock(height):
    stock = 0
    offset = height // 210000
    for idx in range(offset):
        stock = stock + 210000 * 50 / pow(2, idx)
    stock = stock + (height % 210000 + 1) * halving_schedule[offset * 210000]
    return stock

def accumulate_products(min_height, max_height):
    district = { "min_blocks" : 0, "min_unit_prod" : 0, "max_blocks" : 0, "max_unit_prod" : 0 }
    for idx in halving_schedule:
        if min_height >= idx:
            district["min_blocks"] = idx
            district["min_unit_prod"] = halving_schedule[idx]
        if max_height >= idx:
            district["max_blocks"] = idx
            district["max_unit_prod"] = halving_schedule[idx]
    if district["min_blocks"] == district["max_blocks"]:    # 两个区块高度落在同一区间，比如220000 和 240000，每个区块奖励为25btc
        return (max_height - min_height + 1) * district["max_unit_prod"]
    else:  # 两个区块高度落在不同区间，比如200000 和 220000，区块产量计算：200000~210000 每个区块奖励为50btc + 210000~220000 每个区块奖励为25btc
        return (district["max_blocks"] - min_height) * district["min_unit_prod"] + (max_height - district["max_blocks"] + 1) * district["min_unit_prod"]

def get_write_last_line():
    if not os.path.exists(out_path):
        return ""
    with open(out_path, "r") as read_file:
        lines = read_file.readlines()
        if len(lines) == 0:
            return ""
        last_line = lines[-1]
        if len(last_line) != 0:
            return last_line
        else:
            return ""

def convert_time_to_day(timestamp):
    time_obj = time.localtime(timestamp / 1000)
    log_datetime = time.strftime("%Y%m%d", time_obj)
    return log_datetime

def get_daily_btc_production(date_time):
    url = endpoint + date_time
    if proxies == {}:
        ret = requests.get(url)
    else:
        ret = requests.get(url, proxies=proxies)
    if ret.ok:
        # 解析json
        ret_data = json.loads(ret.text)
        min_height = ret_data["data"][-1]["height"]
        max_height = ret_data["data"][0]["height"]
        product_num = accumulate_products(min_height, max_height)
        return (max_height, product_num)
    else:
        return ()

def get_s2f(argv):

    if len(argv) < 2 or len(argv) > 3:
        print("Please enter parameters ！\n \
            format: python s2f.py outpath proxy(dict) \n \
            example1: python s2f.py s2f.txt \n \
            example2: python s2f.py s2f.txt \"{'http': 'http://127.0.0.1:1087', 'https': 'http://127.0.0.1:1087'}\" \n \
        ")
        return
    if len(argv) >= 2:
        global out_path
        out_path = argv[1]
    if len(argv) == 3:
        global proxies
        proxies = eval(argv[2])

    # 文件中写入info格式
    # 今日时间戳 今日时间 今日产量 当前存量 存量-日产量比 存量-年产量比

    # 1. 从start_time开始获取数据
    progress_time = start_time

    # 2. 如果发现文件，说明不是第一次获取数据，从文件中读取已经获得的数据
    last_line = get_write_last_line()
    if last_line != "":
        progress_time = int(last_line.split(" ")[0]) + step_time
    
    # 3. 获取比特币产量存量比
    with open(out_path, "a") as out_file:
        while progress_time < end_time:
            # 3.1 获取每日比特币产量
            date_time = convert_time_to_day(progress_time)
            daily_data = get_daily_btc_production(date_time)
            
            if daily_data == ():
                daily_production = 0
                progress_stock = 0
                s2f_rate = 0
            else:
                daily_production = daily_data[1]
                # 3.2 计算每日存量产量比
                progress_stock = get_stock(daily_data[0])
                s2f_rate = progress_stock / daily_production
            # 3.3 日志
            log = f"date_time: {date_time}  daily_production: {daily_production}  progress_stock: {progress_stock}  s2f_rate_day: {s2f_rate} s2f_rate_year: {s2f_rate / 365}"
            print(log)
            write_log = f"{progress_time} {date_time} {daily_production} {progress_stock} {s2f_rate} {s2f_rate / 365}\n"
            out_file.write(write_log)
            # 3.4 日期向后推进
            progress_time = progress_time + step_time

if __name__ == "__main__":
    get_s2f(sys.argv)
