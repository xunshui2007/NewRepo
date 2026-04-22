#!/usr/bin/env python3
"""CMW500 简单调试"""

import socket
import sys

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def main():
    s = socket.socket()
    s.settimeout(5)
    s.connect((CMW_IP, CMW_PORT))
    print("Connected")
    
    cmds = [
        "*IDN?",
        "SYSTem:ERRor?",
        "ROUTe:LTE:MEAS:SCENario:CSP",
        "*OPC?",
    ]
    
    for cmd in cmds:
        print(f"\n> {cmd}")
        s.sendall(f"{cmd}\n".encode())
        try:
            data = s.recv(1024)
            print(f"< {data.decode().strip()}")
        except:
            print("< timeout")
    
    s.close()

if __name__ == "__main__":
    main()
