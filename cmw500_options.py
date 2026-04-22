#!/usr/bin/env python3
"""CMW500 查询选项"""

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
print("=== CMW500 Options ===\n")

# ID
print(f"ID: {send_cmd(s, '*IDN?')}")

# Options
print(f"Options: {send_cmd(s, '*OPT?')}")

# Software version
print(f"Software: {send_cmd(s, '*OPT?')}")

# 列出所有模块
print("\n=== Modules ===")
result = send_cmd(s, "SYSTem:INFormation:OPTion:LIST?")
print(f"Options: {result}")

# 尝试查询GPRS模块
print("\n=== GPRS Test ===")
result = send_cmd(s, "SYSTem:BAND:GPRs:CATalog?")
print(f"GSM Bands: {result}")

# 查询仪器状态
print("\n=== Instrument Status ===")
result = send_cmd(s, "STATus:QUEStion?")
print(f"Questionable: {result}")

s.close()
