#!/usr/bin/env python3
"""CMW500 测量调试 v2"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd, wait=0.5):
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
    print("=== CMW500 Measurement Debug v2 ===\n")
    
    # 复位
    print("1. Reset...")
    send_cmd(s, "*RST")
    time.sleep(2)
    
    # 先查看错误
    print("2. Check initial errors...")
    print(f"   Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    # 查询可用的测量场景
    print("3. Query scenarios...")
    result = send_cmd(s, "ROUTe:LTE:MEAS:SCENario:CATalog?")
    print(f"   Scenarios: {result}")
    
    # 使用正确的场景 - 可能是SIGNCHECK或CW
    # 尝试使用SIGNCHECK模式进行信号分析
    print("4. Set scenario...")
    result = send_cmd(s, "ROUTe:LTE:MEAS:SCENario:SIGNCHECK")
    print(f"   Route result: {result}")
    print(f"   Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    # 设置频段
    print("5. Set band...")
    result = send_cmd(s, 'SYSTem:BAND:INDex LTE,3')
    print(f"   Band result: {result}")
    print(f"   Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    # 带宽
    print("6. Set bandwidth...")
    send_cmd(s, "CONF:LTE:DL:BANDwidth 20")
    print(f"   Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    # 信道
    print("7. Set channel...")
    send_cmd(s, "CONF:LTE:DL:FREQuency:CHANnel 1850")
    print(f"   Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    # 启用测量
    print("8. Enable measurements...")
    send_cmd(s, "CONFigure:LTE:MEAS:POW:ENABLE ON")
    print(f"   Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    time.sleep(1)
    
    # 触发测量
    print("9. Trigger power measurement...")
    send_cmd(s, "INIT:LTE:MEAS:POW")
    time.sleep(2)
    
    # 读取功率
    print("10. Read power...")
    result = send_cmd(s, "FETCh:LTE:MEAS:POW:RF:RMS?")
    print(f"    FETCh result: '{result}'")
    print(f"    Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    result = send_cmd(s, "MEAS:LTE:MEAS:POW:RF:RMS?")
    print(f"    MEAS result: '{result}'")
    print(f"    Error: {send_cmd(s, 'SYSTem:ERRor?')}")
    
    # 列出可用命令
    print("\n11. Query measurement list...")
    result = send_cmd(s, "CONFigure:LTE:MEAS:CATalog?")
    print(f"    Measurements: {result}")
    
    s.close()
    print("\n=== Done ===")

if __name__ == "__main__":
    main()
