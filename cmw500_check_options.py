#!/usr/bin/env python3
"""CMW500 选件和功能查询"""

import socket

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.3):
    s.sendall(f"{cmd}\n".encode('utf-8'))
    time.sleep(wait)
    try:
        s.settimeout(3)
        response = s.recv(4096)
        return response.decode('utf-8').strip()
    except:
        return ""

import time

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))

print("=== CMW500 功能检查 ===\n")

# ID
print(f"ID: {send_cmd(s, '*IDN?')}")

# Options
opts = send_cmd(s, '*OPT?')
print(f"Options: {opts}")

# 解析选项
option_list = [o.strip() for o in opts.split(',')]

print("\n=== 选件分析 ===")
lte_options = [o for o in option_list if 'KM' in o]
print(f"LTE/5G相关选件: {lte_options}")

# 检查是否有信令选件
has_signaling = any(o in ['KS200', 'KS300'] for o in option_list)
print(f"信令选件: {'有' if has_signaling else '无'}")

# 复位
send_cmd(s, "*RST")
time.sleep(2)

# 检查当前模式
print("\n=== 当前配置 ===")
result = send_cmd(s, "ROUTe:LTE:MEAS:SCENario?")
print(f"LTE模式: {result}")

# 检查可用模块
print("\n=== 可用测量模块 ===")
result = send_cmd(s, "SYSTem:COMM:MEAS:CAT?")
print(f"测量模块: {result}")

s.close()
print("\n=== 完成 ===")
