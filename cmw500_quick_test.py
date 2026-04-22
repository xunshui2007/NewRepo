#!/usr/bin/env python3
"""CMW500 快速LTE信令测试"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.3):
    s.sendall(f"{cmd}\n".encode('utf-8'))
    time.sleep(wait)
    try:
        s.settimeout(2)
        response = s.recv(2048)
        return response.decode('utf-8').strip()
    except:
        return "TIMEOUT"

s = socket.socket()
s.settimeout(5)
s.connect((CMW_IP, CMW_PORT))
print("=== Quick LTE Test ===\n")

print(f"ID: {send_cmd(s, '*IDN?')}")

# 使用基本的LTE Analyzer模式
print("\n--- Basic LTE Test ---")
# 选择SAL模式
send_cmd(s, "ROUTe:LTE:MEAS:SCENario SAL")
print(f"Route: {send_cmd(s, 'ROUTe:LTE:MEAS:SCENario?')}")

# 设置频段
send_cmd(s, 'SYSTem:BAND:INDex LTE,3')
print(f"Band: {send_cmd(s, 'SYSTem:BAND:INDex?')}")

# 带宽
send_cmd(s, "CONF:LTE:DL:BANDwidth 20")
print(f"BW: {send_cmd(s, 'CONF:LTE:DL:BANDwidth?')}")

# 功率
send_cmd(s, "POW:RF:OUTP 23")

# 启用功率测量
send_cmd(s, "CONFigure:LTE:MEAS:POW:ENABLE ON")
time.sleep(0.5)

# 测量
send_cmd(s, "INIT:LTE:MEAS:POW")
time.sleep(1)
power = send_cmd(s, "FETCh:LTE:MEAS:POW:RF:RMS?")
print(f"Power: {power}")

# ACLR
send_cmd(s, "CONFigure:LTE:MEAS:ACLR:ENABLE ON")
time.sleep(0.5)
send_cmd(s, "INIT:LTE:MEAS:ACLR")
time.sleep(1)
aclr = send_cmd(s, "FETCh:LTE:MEAS:ACLR:REST?")
print(f"ACLR: {aclr}")

print(f"\nError: {send_cmd(s, 'SYSTem:ERRor?')}")

s.close()
print("Done")
