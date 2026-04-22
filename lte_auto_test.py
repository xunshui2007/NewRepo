#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE 综合测试
自动尝试LTE和GPRF模式
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

def cmd(s, c, wait=0.3):
    s.sendall(f"{c}\n".encode())
    time.sleep(wait)
    s.settimeout(3)
    try:
        return s.recv(4096).decode().strip()
    except:
        return ""

def main():
    s = socket.socket()
    s.settimeout(10)
    s.connect((CMW_IP, CMW_PORT))
    
    logger.info(f"CMW500: {cmd(s, '*IDN?')}")
    
    results = {
        "time": datetime.now().isoformat(),
        "power": None,
        "aclr": None,
        "bler": None,
        "mode": ""
    }
    
    # ===== 尝试LTE功率 =====
    logger.info("\n=== 尝试LTE功率测量 ===")
    cmd(s, "CONFigure:LTE:MEAS:POW:ENABLE ON", 0.5)
    cmd(s, "INIT:LTE:MEAS:POW", 0.5)
    time.sleep(1)
    r = cmd(s, "FETCh:LTE:MEAS:POW:RF:RMS?", 0.5)
    logger.info(f"LTE功率响应: '{r}'")
    
    try:
        if r and ',' in r:
            vals = r.split(',')
            if int(vals[0]) == 0:
                results["power"] = float(vals[1])
                results["mode"] = "LTE"
    except:
        pass
    
    # ===== 如果LTE失败，使用GPRF =====
    if results["power"] is None:
        logger.info("\n=== 使用GPRF功率测量 ===")
        cmd(s, "CONFigure:GPRf:MEAS:POW:AVG:SCOunt 10", 0.5)
        cmd(s, "INIT:GPRf:MEAS:POW", 0.5)
        time.sleep(1)
        r = cmd(s, "FETCh:GPRf:MEAS:POW:AVER?", 0.5)
        logger.info(f"GPRF功率响应: '{r}'")
        
        try:
            if r and ',' in r:
                vals = r.split(',')
                if int(vals[0]) == 0:
                    results["power"] = float(vals[1])
                    results["mode"] = "GPRF"
        except:
            pass
    
    # ===== ACLR =====
    logger.info("\n=== ACLR测量 ===")
    cmd(s, "INIT:GPRf:MEAS:ACLR", 0.5)
    time.sleep(2)
    r = cmd(s, "FETCh:GPRf:MEAS:ACLR?", 0.5)
    logger.info(f"ACLR响应: '{r}'")
    
    try:
        if r:
            vals = [float(x) for x in r.split(',') if x.replace('.','').replace('-','').isdigit()]
            if len(vals) >= 3:
                results["aclr"] = {"lower": vals[1], "upper": vals[2]}
    except:
        pass
    
    # ===== BLER =====
    logger.info("\n=== BLER测量 ===")
    cmd(s, "INIT:GPRf:MEAS:BLER", 0.5)
    time.sleep(2)
    r = cmd(s, "FETCh:GPRf:MEAS:BLER:STAT?", 0.5)
    logger.info(f"BLER响应: '{r}'")
    
    try:
        if r and ',' in r:
            results["bler"] = float(r.split(',')[1])
    except:
        pass
    
    s.close()
    
    # 保存
    fname = f"lte_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n结果已保存: {fname}")
    
    # 打印
    logger.info("\n=== 测试结果 ===")
    logger.info(f"模式: {results['mode']}")
    logger.info(f"功率: {results['power']:.2f} dBm" if results['power'] else "功率: 失败")
    if results['aclr']:
        logger.info(f"ACLR: 下邻 {results['aclr']['lower']:.2f} dBc, 上邻 {results['aclr']['upper']:.2f} dBc")
    logger.info(f"BLER: {results['bler']:.2f}%" if results['bler'] else "BLER: 失败")

if __name__ == "__main__":
    main()
