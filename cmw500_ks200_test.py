#!/usr/bin/env python3
"""CMW500 LTE信令详细测试 - 使用KS200"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.5):
    s.sendall(f"{cmd}\n".encode('utf-8'))
    time.sleep(wait)
    try:
        s.settimeout(5)
        response = s.recv(4096)
        return response.decode('utf-8').strip()
    except:
        return ""

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))
print("=== CMW500 LTE Signaling (KS200) ===\n")

print(f"ID: {send_cmd(s, '*IDN?')}")
print(f"Options: {send_cmd(s, '*OPT?')}")

# 复位
send_cmd(s, "*RST")
time.sleep(2)

# 检查可用场景
print("\n=== 场景列表 ===")
scenarios = [
    "ROUTe:LTE:SIGN:SCENario:CAT?",
    "ROUTe:LTE:MEAS:SCENario:CAT?",
    "ROUTe:LTE:MEAS:SCENario?",
]

for sc in scenarios:
    result = send_cmd(s, sc)
    print(f"{sc}: {result}")

# 尝试设置信令场景
print("\n=== 设置信令场景 ===")
# 先检查系统状态
result = send_cmd(s, "SYSTem:STATe?")
print(f"系统状态: {result}")

# 尝试不同的路由命令
result = send_cmd(s, "ROUTe:LTE:SIGN:SCENario:CONN")
print(f"Route CONN: {result}")
print(f"Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 查询支持的频段
print("\n=== 频段查询 ===")
bands = [
    "SYSTem:BAND:LTE:ALL?",
    "SYSTem:BAND:LTE?",
    "LIST:BAND:LTE?",
]

for b in bands:
    result = send_cmd(s, b)
    print(f"{b}: {result}")

# 尝试使用完整的信令路径
print("\n=== 完整信令路径 ===")
result = send_cmd(s, "CONN:LTE:MEAS:SCENario:SIGN")
print(f"CONN路径: {result}")
print(f"Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 列出所有LTE相关命令
print("\n=== LTE命令探索 ===")
cmds = [
    "CONFigure:LTE:MEAS:SCENario?",
    "CONFigure:LTE:SIGN?",
    "SOUR:LTE:SIGN:BAND?",
    "SOUR:LTE:SIGN:FREQuency?",
]

for c in cmds:
    result = send_cmd(s, c)
    print(f"{c}: {result}")

s.close()
print("\n=== Done ===")
