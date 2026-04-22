#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE 信令测试 - 直接测量模式
假设LTE小区已在前面板配置好并连接DUT
"""

import socket
import time
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

class CMW500:
    def __init__(self):
        self.sock = None
        
    def connect(self):
        self.sock = socket.socket()
        self.sock.settimeout(10)
        self.sock.connect((CMW_IP, CMW_PORT))
        idn = self.cmd("*IDN?")
        logger.info(f"CMW500: {idn}")
        
    def cmd(self, c, wait=0.3):
        self.sock.sendall(f"{c}\n".encode())
        time.sleep(wait)
        self.sock.settimeout(3)
        try:
            return self.sock.recv(4096).decode().strip()
        except:
            return ""
    
    def check_connection(self):
        """检查DUT连接状态"""
        result = self.cmd("STATus:LTE:SIGN:PS?")
        logger.info(f"DUT状态: {result}")
        return result
    
    def measure_power(self):
        """LTE功率测量"""
        self.cmd("INIT:LTE:MEAS:POW")
        time.sleep(1.5)
        r = self.cmd("FETCh:LTE:MEAS:POW:RF:RMS?")
        logger.info(f"功率查询: {r}")
        try:
            if ',' in r:
                p = r.split(',')
                if int(p[0]) == 0:
                    return float(p[1])
            return float(r)
        except:
            return -999.0
    
    def measure_aclr(self):
        """ACLR测量"""
        self.cmd("INIT:LTE:MEAS:ACLR")
        time.sleep(2)
        r = self.cmd("FETCh:LTE:MEAS:ACLR:REST?")
        logger.info(f"ACLR查询: {r}")
        try:
            vals = r.split(',')
            lower = float(vals[1]) if len(vals) > 1 else 0
            upper = float(vals[3]) if len(vals) > 3 else 0
            return lower, upper
        except:
            return 0.0, 0.0
    
    def measure_sensitivity(self):
        """灵敏度测试 - BLER测量"""
        self.cmd("INIT:LTE:MEAS:BLER")
        time.sleep(2)
        r = self.cmd("FETCh:LTE:MEAS:BLER:STAT?")
        logger.info(f"BLER查询: {r}")
        try:
            if ',' in r:
                return float(r.split(',')[1])
            return float(r)
        except:
            return 100.0
    
    def close(self):
        self.sock.close()

def main():
    cmw = CMW500()
    cmw.connect()
    
    # 检查DUT连接
    logger.info("\n=== 检查DUT连接 ===")
    status = cmw.check_connection()
    
    if status and status != "0":
        logger.info("DUT已连接！")
    else:
        logger.warning("DUT未连接，但继续测试...")
    
    # 测量
    results = {
        "time": datetime.now().isoformat(),
        "dut_connected": status != "0" if status else False,
        "power": {},
        "aclr": {},
        "bler": {}
    }
    
    # 功率
    logger.info("\n=== 功率测试 ===")
    power = cmw.measure_power()
    logger.info(f"功率: {power:.2f} dBm")
    results["power"] = {"value": round(power,2), "unit": "dBm"}
    
    # ACLR
    logger.info("\n=== ACLR测试 ===")
    lower, upper = cmw.measure_aclr()
    logger.info(f"ACLR: 下邻 {lower:.2f} dBc, 上邻 {upper:.2f} dBc")
    results["aclr"] = {"lower": round(lower,2), "upper": round(upper,2), "unit": "dBc"}
    
    # BLER/灵敏度
    logger.info("\n=== BLER测试 ===")
    bler = cmw.measure_sensitivity()
    logger.info(f"BLER: {bler:.2f}%")
    results["bler"] = {"value": round(bler,2), "unit": "%"}
    
    cmw.close()
    
    # 保存
    fname = f"lte_signaling_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n结果已保存: {fname}")
    
    # 打印
    logger.info("\n=== 测试结果 ===")
    logger.info(f"功率: {results['power']['value']:.2f} dBm")
    logger.info(f"ACLR: {results['aclr']['lower']:.2f} / {results['aclr']['upper']:.2f} dBc")
    logger.info(f"BLER: {results['bler']['value']:.2f}%")

if __name__ == "__main__":
    main()
