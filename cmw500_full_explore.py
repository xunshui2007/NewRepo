#!/usr/bin/env python3
"""CMW500 完整探索"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.3):
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

# 检查所有错误
print("\n=== Error Queue ===")
result = send_cmd(s, "SYSTem:ERRor:ALL?")
print(f"All Errors: {result}")

# 复位
send_cmd(s, "*RST")
time.sleep(2)

# 查看仪器状态
print("\n=== Instrument Status ===")
result = send_cmd(s, "STATus:PRESet?")
print(f"Preset: {result}")

# 尝试用完整路径设置
print("\n=== Full Path Commands ===")
cmds = [
    "CONFigure:LTE:SIGN:SCENario",
    "SOURce:LTE:SIGN:SCENario",
    "ROUTe:LTE:SIGN:SCENario",
]

for c in cmds:
    result = send_cmd(s, c)
    print(f"{c}: {result}")
    print(f"  Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 查看help
print("\n=== Help ===")
result = send_cmd(s, "SYSTem:COMM:Help:TITLe? ALL?")
print(f"Help: {result}")

# 尝试不返回错误的方式 - 直接发送命令不管错误
print("\n=== Direct Commands ===")
s.sendall(b"ROUTe:LTE:SIGN:SCENario:SIGN\n")
time.sleep(0.5)
result = s.recv(4096).decode('utf-8').strip()
print(f"Direct: {result}")

# 查看可用的测量模式
print("\n=== MEAS Modes ===")
result = send_cmd(s, "CONFigure:LTE:MEAS:SCENario:CAT?")
print(f"CAT: {result}")

s.close()
print("\nDone")
