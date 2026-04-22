#!/usr/bin/env python3
"""CMW500 状态检查"""

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
        return "TIMEOUT"

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))

print(f"ID: {cmd(s, '*IDN?')}")

# 检查错误
print(f"\n错误: {cmd(s, 'SYSTem:ERRor?')}")

# 检查LTE模式
print(f"\n=== LTE状态 ===")
print(f"场景: {cmd(s, 'ROUTe:LTE:MEAS:SCENario?')}")

# 检查测量状态
print(f"\n=== 测量状态 ===")
print(f"GPRF POW: {cmd(s, 'STATus:GPRf:MEAS:POW:CONDition?')}")
print(f"GPRF ACLR: {cmd(s, 'STATus:GPRf:MEAS:ACLR:CONDition?')}")

# 不初始化直接读取
print(f"\n=== 直接读取 ===")
print(f"POW: {cmd(s, 'FETCh:GPRf:MEAS:POW:RF:RMS?')}")
print(f"ACLR: {cmd(s, 'FETCh:GPRf:MEAS:ACLR:RESult?')}")

# 检查正在进行
print(f"\n=== 进行中检查 ===")
print(f"POW ACT: {cmd(s, 'STATus:GPRf:MEAS:POW:ACTive?')}")

s.close()
print("\n完成")
