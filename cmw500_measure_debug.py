#!/usr/bin/env python3
"""CMW500 测量调试"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.3):
    """发送命令并读取响应"""
    s.sendall(f"{cmd}\n".encode('utf-8'))
    time.sleep(wait)
    try:
        s.settimeout(3)
        response = s.recv(4096)
        return response.decode('utf-8').strip()
    except:
        return ""

def main():
    s = socket.socket()
    s.settimeout(10)
    s.connect((CMW_IP, CMW_PORT))
    print("=== CMW500 Measurement Debug ===\n")
    
    # 复位
    print("1. Reset...")
    send_cmd(s, "*RST")
    time.sleep(2)
    
    # 配置LTE
    print("2. Configure LTE...")
    send_cmd(s, "ROUTe:LTE:MEAS:SCENario:CSP")
    send_cmd(s, 'SYSTem:BAND:INDex LTE,3')
    send_cmd(s, "CONF:LTE:DL:BANDwidth 20")
    send_cmd(s, "CONF:LTE:DL:FREQuency:CHANnel 1850")
    send_cmd(s, "POW:RF:OUTP 23")
    
    # 启用测量
    print("3. Enable measurements...")
    send_cmd(s, "CONFigure:LTE:MEAS:POW:ENABLE ON")
    send_cmd(s, "CONFigure:LTE:MEAS:ACLR:ON")
    
    time.sleep(1)
    
    # 检查错误
    print("4. Check errors...")
    print(f"   Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    # 触发功率测量
    print("5. Trigger power measurement...")
    send_cmd(s, "INIT:LTE:MEAS:POW")
    time.sleep(2)
    
    # 读取状态
    print("6. Read status...")
    print(f"   POW STAT: {send_cmd(s, 'STATus:LTE:MEAS:POW:EVENt?')}")
    print(f"   POW COND: {send_cmd(s, 'STATus:LTE:MEAS:POW:CONDition?')}")
    
    # 读取功率
    print("7. Read power...")
    result = send_cmd(s, "FETCh:LTE:MEAS:POW:RF:RMS?", wait=1)
    print(f"   FETCh result: '{result}'")
    
    result = send_cmd(s, "READ:LTE:MEAS:POW:RF:RMS?", wait=1)
    print(f"   READ result: '{result}'")
    
    # 查询可用的参数
    print("8. Query available...")
    result = send_cmd(s, "CONFigure:LTE:MEAS:POW:SCOunt?", wait=0.5)
    print(f"   SCOunt: {result}")
    
    s.close()
    print("\n=== Done ===")

if __name__ == "__main__":
    main()
