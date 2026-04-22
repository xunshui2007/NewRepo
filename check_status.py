#!/usr/bin/env python3
"""检查CMW500当前状态"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def cmd(s, c, wait=0.3):
    s.sendall(f"{c}\n".encode())
    time.sleep(wait)
    s.settimeout(3)
    try:
        return s.recv(4096).decode().strip()
    except:
        return ""

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))

print(f"ID: {cmd(s, '*IDN?')}")

# 检查当前模式
print(f"\n当前LTE场景: {cmd(s, 'ROUTe:LTE:MEAS:SCENario?')}")

# 检查系统错误
print(f"错误: {cmd(s, 'SYSTem:ERRor?')}")

# 检查状态
print(f"\nLTE信令状态: {cmd(s, 'STATus:LTE:SIGN:PS?')}")

# 尝试简单的LTE查询
print(f"\n=== 简单查询 ===")
queries = [
    "FETCh:LTE:MEAS:POW:RF:RMS?",
    "CONFigure:LTE:MEAS:POW:ENABLE?",
    "STATus:LTE:MEAS:POW:CONDition?",
]

for q in queries:
    print(f"{q}: {cmd(s, q)}")

# 检查GPRF
print(f"\nGPRF功率: {cmd(s, 'FETCh:GPRf:MEAS:POW:AVER?')}")

s.close()
print("\n完成")
