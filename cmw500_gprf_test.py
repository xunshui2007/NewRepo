#!/usr/bin/env python3
"""CMW500 测量测试 - 使用不同命令"""

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
print("=== CMW500 Command Test ===\n")

# 测试不同的命令格式
print("1. Test basic commands...")
result = send_cmd(s, "*IDN?")
print(f"   *IDN?: {result}")

result = send_cmd(s, "SYSTem:ERRor?")
print(f"   Error: {result}")

# 测试GSM/EDGE命令 (通常CMW500默认支持)
print("\n2. Test GSM commands...")
result = send_cmd(s, "CONFigure:GPRf:MEAS:SCENario?")
print(f"   GPRF Scenario: {result}")

result = send_cmd(s, "CONFigure:GPRf:MEAS:SCENario:CSWitched")
print(f"   Set GPRF: {result}")

result = send_cmd(s, "SYSTem:ERRor?")
print(f"   Error: {result}")

# 尝试使用GPRF进行功率测量
print("\n3. Test GPRF power...")
result = send_cmd(s, "CONFigure:GPRf:MEAS:POW:ENABLE ON")
print(f"   Enable GPRF Power: {result}")

result = send_cmd(s, "SYSTem:ERRor?")
print(f"   Error: {result}")

result = send_cmd(s, "INIT:GPRf:MEAS:POW")
time.sleep(2)

result = send_cmd(s, "FETCh:GPRf:MEAS:POW:AVER?")
print(f"   GPRF Power: {result}")

result = send_cmd(s, "SYSTem:ERRor?")
print(f"   Error: {result}")

# 尝试LIST命令查看可用的测试
print("\n4. Browse available...")
result = send_cmd(s, "SYSTem:COMM:Help:TITLe?")
print(f"   Help: {result}")

s.close()
print("\n=== Done ===")
