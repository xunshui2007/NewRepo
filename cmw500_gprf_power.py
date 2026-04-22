#!/usr/bin/env python3
"""CMW500 使用GPRF进行功率和ACLR测量"""

import socket
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

class CMW500_GPRF:
    def __init__(self, ip, port=5025):
        self.ip = ip
        self.port = port
        self.sock = None
        
    def connect(self):
        self.sock = socket.socket()
        self.sock.settimeout(10)
        self.sock.connect((self.ip, self.port))
        logger.info(f"Connected to CMW500 at {self.ip}")
        
    def send_cmd(self, cmd, wait=0.3):
        self.sock.sendall(f"{cmd}\n".encode('utf-8'))
        time.sleep(wait)
        try:
            self.sock.settimeout(3)
            response = self.sock.recv(4096)
            return response.decode('utf-8').strip()
        except:
            return ""
    
    def measure_power(self, avg_count=10):
        """使用GPRF测量功率"""
        # 设置平均次数
        self.send_cmd(f"CONFigure:GPRf:MEAS:POW:AVG:SCOunt {avg_count}")
        
        # 触发测量
        self.send_cmd("INIT:GPRf:MEAS:POW")
        time.sleep(1)
        
        # 读取结果
        result = self.send_cmd("FETCh:GPRf:MEAS:POW:AVER?")
        
        if result:
            try:
                # 格式: "0,-75.24" 或 "status,power_dbm"
                parts = result.split(',')
                if len(parts) >= 2:
                    status = int(parts[0])
                    if status == 0:
                        power = float(parts[1])
                        return power
            except:
                pass
        return -999.0
    
    def measure_aclr(self):
        """使用GPRF测量ACLR - 简化版"""
        # 触发ACLR测量
        self.send_cmd("INIT:GPRf:MEAS:ACLR")
        time.sleep(2)
        
        # 读取结果
        result = self.send_cmd("FETCh:GPRf:MEAS:ACLR?")
        
        if result:
            return result
        return ""
    
    def close(self):
        if self.sock:
            self.sock.close()

def main():
    cmw = CMW500_GPRF(CMW_IP, CMW_PORT)
    cmw.connect()
    
    logger.info("\n=== 功率测试 (使用GPRF) ===")
    
    for i in range(3):
        power = cmw.measure_power()
        logger.info(f"测量 {i+1}: {power:.2f} dBm")
        time.sleep(0.5)
    
    logger.info("\n=== ACLR测试 ===")
    aclr = cmw.measure_aclr()
    logger.info(f"ACLR结果: {aclr}")
    
    cmw.close()
    logger.info("\n完成!")

if __name__ == "__main__":
    main()
