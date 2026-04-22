#!/usr/bin/env python3
"""CMW500 LTE信令探索 v2"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.5):
    s.sendall(f"{cmd}\n".encode('utf-8'))
    time.sleep(wait)
    try:
        s.settimeout(3)
        return s.recv(4096).decode('utf-8').strip()
    except:
        return ""

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))

print(f"ID: {send_cmd(s, '*IDN?')}")
print(f"Options: {send_cmd(s, '*OPT?')}")

# 复位
send_cmd(s, "*RST")
time.sleep(2)

# 尝试不同的路由
print("\n=== Route ===")
result = send_cmd(s, "ROUTe:LTE:MEAS:SCENario?")
print(f"Current: {result}")

# 尝试设置
routes = ["SIGN", "SIGNalling", "CONN", "CSP"]
for r in routes:
    result = send_cmd(s, f"ROUTe:LTE:MEAS:SCENario {r}")
    print(f"Route {r}: {result}")
    print(f"  Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 查看系统状态
print("\n=== System ===")
result = send_cmd(s, "SYSTem:STATe?")
print(f"State: {result}")

# 尝试另一种命令路径
print("\n=== Alternative ===")
alts = [
    "CONN:LTE:MEAS:SCENario",
    "SOUR:LTE:MEAS:SCENario",
    "CONF:LTE:MEAS:SCENario",
]

for a in alts:
    result = send_cmd(s, a)
    print(f"{a}: {result}")

# 列出所有可用命令
print("\n=== Command Search ===")
# 尝试常见的频段命令
bands = [
    "SYSTem:BAND:INDex?",
    "SYSTem:BAND?",
    "BAND:LTE?",
]

for b in bands:
    result = send_cmd(s, b)
    print(f"{b}: {result}")

# 尝试不同的频段设置方式
print("\n=== Band Config ===")
result = send_cmd(s, "LIST:BAND:LTE?")
print(f"LIST:BAND:LTE?: {result}")

result = send_cmd(s, "SYSTem:BAND:LIST?")
print(f"LIST?: {result}")

s.close()
print("\nDone")
