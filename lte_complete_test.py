#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE 完整测试 - GPRF模式
适用于DUT已连接或未连接的情况
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
        
    def cmd(self, c, wait=0.3):
        self.sock.sendall(f"{c}\n".encode())
        time.sleep(wait)
        self.sock.settimeout(3)
        try:
            return self.sock.recv(4096).decode().strip()
        except:
            return ""
    
    def power(self):
        self.cmd("CONFigure:GPRf:MEAS:POW:AVG:SCOunt 10")
        self.cmd("INIT:GPRf:MEAS:POW")
        time.sleep(1)
        r = self.cmd("FETCh:GPRf:MEAS:POW:AVER?")
        try:
            p = r.split(',')
            if int(p[0])==0: return float(p[1])
        except: pass
        return -999.0
    
    def aclr(self):
        self.cmd("INIT:GPRf:MEAS:ACLR")
        time.sleep(2)
        r = self.cmd("FETCh:GPRf:MEAS:ACLR?", wait=1)
        try:
            vals = [float(x) for x in r.split(',') if x.replace('.','').replace('-','').isdigit()]
            return vals[1] if len(vals)>1 else 0.0, vals[2] if len(vals)>2 else 0.0
        except: pass
        return 0.0, 0.0
    
    def bler(self):
        """BLER测量 - 简化版"""
        self.cmd("INIT:GPRf:MEAS:BLER")
        time.sleep(2)
        r = self.cmd("FETCh:GPRf:MEAS:BLER:STAT?")
        try:
            vals = r.split(',')
            if int(vals[0])==0:
                return float(vals[1])
        except: pass
        return 100.0
    
    def close(self):
        self.sock.close()

def test_bands(bands):
    cmw = CMW500()
    cmw.connect()
    
    results = {
        "time": datetime.now().isoformat(),
        "power": [],
        "aclr": [],
        "bler": []
    }
    
    for band in bands:
        logger.info(f"\n=== Band {band} ===")
        
        p = cmw.power()
        logger.info(f"功率: {p:.2f} dBm")
        results["power"].append({"band": band, "power_dbm": round(p,2)})
        
        lower, upper = cmw.aclr()
        logger.info(f"ACLR: 下邻 {lower:.2f} dBc, 上邻 {upper:.2f} dBc")
        results["aclr"].append({"band": band, "lower": round(lower,2), "upper": round(upper,2)})
        
        b = cmw.bler()
        logger.info(f"BLER: {b:.2f}%")
        results["bler"].append({"band": band, "bler": round(b,2)})
    
    cmw.close()
    return results

if __name__ == "__main__":
    # 测试频段
    bands = ["3", "7", "20"]
    
    logger.info("=== LTE 功率/ACLR/BLER 测试 ===")
    results = test_bands(bands)
    
    # 保存
    fname = f"lte_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n结果已保存: {fname}")
    
    # 摘要
    logger.info("\n=== 结果摘要 ===")
    for i, band in enumerate(bands):
        p = results["power"][i]["power_dbm"]
        a = results["aclr"][i]
        b = results["bler"][i]["bler"]
        logger.info(f"Band {band}: 功率={p:.2f}dBm, ACLR={a['lower']:.2f}dBc/{a['upper']:.2f}dBc, BLER={b:.2f}%")
