#!/usr/bin/env python3
"""CMW500 LTE信令探索"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.5):
    s.sendall(f"{cmd}\n".encode('utf-8'))
    time.sleep(wait)
    try:
        s.settimeout(3)
        response = s.recv(4096)
        return response.decode('utf-8').strip()
    except:
        return ""

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))
print("=== CMW500 LTE Signaling Explore ===\n")

print(f"ID: {send_cmd(s, '*IDN?')}")

# 复位
send_cmd(s, "*RST")
time.sleep(2)

# 尝试不同的路由命令
print("\n=== Route Commands ===")
routes = [
    "ROUTe:LTE:MEAS:SCENario:CATalog?",
    "ROUTe:LTE:SIGN:SCENario:CATalog?",
    "ROUTe:LTE:MEAS:SCENario?",
]

for r in routes:
    print(f"\n{r}")
    result = send_cmd(s, r)
    print(f"  {result}")
    print(f"  Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 尝试不同的频段设置
print("\n=== Band Commands ===")
bands = [
    "SYSTem:BAND:CAT?",
    "SYSTem:BAND:LTE:CAT?",
    "SYSTem:LTE:BAND:CAT?",
]

for b in bands:
    print(f"\n{b}")
    result = send_cmd(s, b)
    print(f"  {result}")

# 尝试建立信令连接的不同命令
print("\n=== Signaling Start ===")
signals = [
    "SOUR:LTE:SIGN:SCENario:STARt",
    "SOUR:LTE:SIGN:STARt",
    "INIT:LTE:SIGN",
]

for sig in signals:
    print(f"\n{sig}")
    result = send_cmd(s, sig)
    print(f"  Result: {result}")
    print(f"  Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 尝试信令状态查询
print("\n=== Status Queries ===")
statuses = [
    "STATus:LTE:SIGN:CONNection?",
    "STATus:LTE:SIGN:STATe?",
    "STATus:LTE:SIGN:PS?",
    "FETCh:LTE:SIGN:STATus?",
]

for st in statuses:
    print(f"\n{st}")
    result = send_cmd(s, st)
    print(f"  {result}")

s.close()
print("\n=== Done ===")
