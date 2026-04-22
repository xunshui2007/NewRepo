#!/usr/bin/env python3
"""
CMW500 调试脚本 - 用于探索SCPI命令和状态
"""

import socket
import time

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def send_cmd(s, cmd):
    """发送命令并读取响应"""
    print(f"> {cmd}")
    s.sendall(f"{cmd}\n".encode('utf-8'))
    time.sleep(0.2)
    s.settimeout(5)
    try:
        response = b""
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
                if response.endswith(b'\n'):
                    break
            except socket.timeout:
                break
        result = response.decode('utf-8').strip()
        if result:
            print(f"< {result}")
        return result
    except Exception as e:
        print(f"< Error: {e}")
        return ""

def main():
    # 连接
    s = socket.socket()
    s.settimeout(10)
    s.connect((CMW_IP, CMW_PORT))
    print("=== CMW500 Debug Script ===\n")
    
    # 基本信息
    send_cmd(s, "*IDN?")
    send_cmd(s, "*OPT?")
    send_cmd(s, "*STB?")
    
    print("\n=== LTE 配置 ===")
    # 选择LTE测量场景
    send_cmd(s, "ROUTe:LTE:MEAS:SCENario:CSP")
    
    # 查询可用频段
    send_cmd(s, "SYSTem:BAND:CAT?")
    
    # 设置频段
    send_cmd(s, 'SYSTem:BAND:INDex LTE,3')
    
    # 查询状态
    send_cmd(s, "SYSTem:BAND:INDex?")
    
    # 带宽设置
    send_cmd(s, "CONF:LTE:DL:BANDwidth?")
    send_cmd(s, "CONF:LTE:DL:BANDwidth 20")
    
    # 信道设置
    send_cmd(s, "CONF:LTE:DL:FREQuency:CHANnel?")
    send_cmd(s, "CONF:LTE:DL:FREQuency:CHANnel 1850")
    
    print("\n=== 功率测量 ===")
    # 查询测量状态
    send_cmd(s, "CONFigure:LTE:MEAS:POW:ENABLE?")
    send_cmd(s, "CONFigure:LTE:MEAS:POW:ENABLE ON")
    
    # 触发测量
    send_cmd(s, "INIT:LTE:MEAS:POW")
    time.sleep(1)
    
    # 读取功率
    send_cmd(s, "FETCh:LTE:MEAS:POW:RF:RMS?")
    send_cmd(s, "FETCh:LTE:MEAS:POW:RF:AVG?")
    
    # 查询测量状态
    send_cmd(s, "STATus:LTE:MEAS:POW:EVENt?")
    
    print("\n=== ACLR测量 ===")
    send_cmd(s, "CONFigure:LTE:MEAS:ACLR:ENABLE?")
    send_cmd(s, "CONFigure:LTE:MEAS:ACLR:ENABLE ON")
    
    send_cmd(s, "INIT:LTE:MEAS:ACLR")
    time.sleep(1)
    
    send_cmd(s, "FETCh:LTE:MEAS:ACLR:REST?")
    send_cmd(s, "FETCh:LTE:MEAS:ACLR:OBW?")
    
    print("\n=== 错误查询 ===")
    send_cmd(s, "SYSTem:ERRor?")
    
    s.close()
    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()
