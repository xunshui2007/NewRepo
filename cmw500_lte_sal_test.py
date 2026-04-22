#!/usr/bin/env python3
"""CMW500 LTE Signal Analyzer 模式测试"""

import socket
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

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
print("=== CMW500 LTE Signal Analyzer Test ===\n")

# 复位
send_cmd(s, "*RST")
time.sleep(2)

print(f"ID: {send_cmd(s, '*IDN?')}")

# 使用SAL模式（Signal Analyzer）
print("\n=== Configure LTE SAL Mode ===")
result = send_cmd(s, "ROUTe:LTE:MEAS:SCENario:SAL")
print(f"Route: {result}")
print(f"Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 设置频段
print("\n=== Set Band ===")
result = send_cmd(s, "SYSTem:BAND:INDex LTE,3")
print(f"Band: {result}")
print(f"Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 查询频段
result = send_cmd(s, "SYSTem:BAND:INDex?")
print(f"Current Band: {result}")

# 设置带宽
print("\n=== Set Bandwidth ===")
result = send_cmd(s, "CONF:LTE:DL:BANDwidth 20")
print(f"DL BW: {result}")
result = send_cmd(s, "CONF:LTE:UL:BANDwidth 20")
print(f"UL BW: {result}")

# 设置信道
print("\n=== Set Channel ===")
result = send_cmd(s, "CONF:LTE:DL:FREQuency:CHANnel 1850")
print(f"DL Channel: {result}")
result = send_cmd(s, "CONF:LTE:UL:FREQuency:CHANnel 1950")
print(f"UL Channel: {result}")

# 查询配置
print("\n=== Query Config ===")
result = send_cmd(s, "CONF:LTE:DL:BANDwidth?")
print(f"DL BW: {result}")
result = send_cmd(s, "CONF:LTE:DL:FREQuency:CHANnel?")
print(f"DL Channel: {result}")

# 设置功率
print("\n=== Set Power ===")
result = send_cmd(s, "POW:RF:OUTP 23")
print(f"Output Power: {result}")
print(f"Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 启用测量
print("\n=== Enable Measurements ===")
result = send_cmd(s, "CONFigure:LTE:MEAS:POW:ENABLE ON")
print(f"Enable Power: {result}")
print(f"Error: {send_cmd(s, 'SYSTem:ERRor?')}")

# 测量功率
print("\n=== Measure Power ===")
result = send_cmd(s, "INIT:LTE:MEAS:POW")
print(f"Init: {result}")
time.sleep(2)

# 查询测量值
result = send_cmd(s, "FETCh:LTE:MEAS:POW:RF:RMS?")
print(f"Power RMS: {result}")

result = send_cmd(s, "FETCh:LTE:MEAS:POW:RF:AVER?")
print(f"Power Avg: {result}")

# 读取状态
result = send_cmd(s, "STATus:LTE:MEAS:POW:CONDition?")
print(f"POW Condition: {result}")

# ACLR
print("\n=== Measure ACLR ===")
result = send_cmd(s, "CONFigure:LTE:MEAS:ACLR:ENABLE ON")
print(f"Enable ACLR: {result}")
print(f"Error: {send_cmd(s, 'SYSTem:ERRor?')}")

result = send_cmd(s, "INIT:LTE:MEAS:ACLR")
print(f"Init ACLR: {result}")
time.sleep(2)

result = send_cmd(s, "FETCh:LTE:MEAS:ACLR:REST?")
print(f"ACLR: {result}")

print(f"\nFinal Error: {send_cmd(s, 'SYSTem:ERRor?')}")

s.close()
print("\n=== Done ===")
