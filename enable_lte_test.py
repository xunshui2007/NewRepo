#!/usr/bin/env python3
"""启用LTE测量并测试"""

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

# 启用LTE功率测量
print("\n=== 启用LTE测量 ===")
print(f"POW ENABLE: {cmd(s, 'CONFigure:LTE:MEAS:POW:ENABLE ON')}")
print(f"Error: {cmd(s, 'SYSTem:ERRor?')}")

# 检查启用状态
print(f"POW ENABLE?: {cmd(s, 'CONFigure:LTE:MEAS:POW:ENABLE?')}")

# 触发测量
print("\n=== 触发测量 ===")
print(f"INIT: {cmd(s, 'INIT:LTE:MEAS:POW')}")
time.sleep(2)

# 读取
print(f"FETCh: {cmd(s, 'FETCh:LTE:MEAS:POW:RF:RMS?')}")
print(f"Error: {cmd(s, 'SYSTem:ERRor?')}")

# ACLR
print("\n=== ACLR ===")
print(f"ACLR ENABLE: {cmd(s, 'CONFigure:LTE:MEAS:ACLR:ENABLE ON')}")
print(f"Error: {cmd(s, 'SYSTem:ERRor?')}")

print(f"INIT: {cmd(s, 'INIT:LTE:MEAS:ACLR')}")
time.sleep(2)
print(f"FETCh: {cmd(s, 'FETCh:LTE:MEAS:ACLR:REST?')}")
print(f"Error: {cmd(s, 'SYSTem:ERRor?')}")

# BLER
print("\n=== BLER ===")
print(f"INIT: {cmd(s, 'INIT:LTE:MEAS:BLER')}")
time.sleep(2)
print(f"FETCh: {cmd(s, 'FETCh:LTE:MEAS:BLER:STAT?')}")
print(f"Error: {cmd(s, 'SYSTem:ERRor?')}")

s.close()
print("\n完成")
