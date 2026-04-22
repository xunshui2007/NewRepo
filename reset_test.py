#!/usr/bin/env python3
"""CMW500 复位后测试"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def cmd(s, c, wait=0.5):
    s.sendall(f"{c}\n".encode())
    time.sleep(wait)
    s.settimeout(5)
    try:
        return s.recv(4096).decode().strip()
    except:
        return ""

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))

print(f"ID: {cmd(s, '*IDN?')}")

# 复位
print("\n复位...")
cmd(s, "*RST")
time.sleep(3)

# GPRF功率
print("\nGPRF功率...")
cmd(s, "CONFigure:GPRf:MEAS:POW:AVG:SCOunt 10")
cmd(s, "INIT:GPRf:MEAS:POW")
time.sleep(1)
r = cmd(s, "FETCh:GPRf:MEAS:POW:AVER?")
print(f"功率: {r}")

# 功率结果解析
try:
    if r:
        p = r.split(',')
        if len(p) >= 2:
            status = int(p[0])
            if status == 0:
                power = float(p[1])
                print(f">>> 功率: {power:.2f} dBm")
            else:
                print(f">>> 状态: {status}")
except Exception as e:
    print(f"解析错误: {e}")

s.close()
print("\n完成")
