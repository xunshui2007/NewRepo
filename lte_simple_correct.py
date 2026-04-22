#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE 简化测试
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

def cmd(sock, c, wait=0.5):
    sock.sendall(f"{c}\n".encode())
    time.sleep(wait)
    sock.settimeout(5)
    try:
        return sock.recv(4096).decode().strip()
    except:
        return ""

sock = socket.socket()
sock.settimeout(10)
sock.connect((CMW_IP, CMW_PORT))

logger.info(f"CMW500: {cmd(sock, '*IDN?')}")

# 检查DUT状态
logger.info("\n=== DUT状态 ===")
status = cmd(sock, "FETC:LTE:SIGN:PSW:STAT?")
logger.info(f"状态: {status}")

results = {"dut_status": status}

if status in ["CEST", "ATT"]:
    logger.info("\n=== 配置测量 ===")
    
    # 配置测量
    cmd(sock, "CONF:LTE:MEAS:MEValuation:RESult:ALL ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON", 0.5)
    cmd(sock, "CONFigure:LTE:MEAS:MEValuation:RESult:EVMagnitude:EVMSymbol ON, 3, LOW", 0.5)
    cmd(sock, "CONF:LTE:MEAS:MEV:REP SING", 0.5)
    cmd(sock, "INIT:LTE:MEAS:MEValuation", 0.5)
    
    time.sleep(3)
    
    # 读取功率
    logger.info("\n=== 功率 ===")
    r = cmd(sock, "FETC:LTE:MEAS:MEV:MOD:AVER?")
    logger.info(f"原始: {r}")
    
    try:
        if r:
            vals = r.split(',')
            logger.info(f"解析: {vals}")
            if len(vals) >= 5:
                results["power_dbm"] = float(vals[4])
                results["evm_percent"] = float(vals[3])
    except Exception as e:
        logger.error(f"解析错误: {e}")
    
    # 读取ACLR
    logger.info("\n=== ACLR ===")
    r = cmd(sock, "FETC:LTE:MEAS:MEV:ACLR:AVER?")
    logger.info(f"原始: {r}")
    
    try:
        if r:
            vals = r.split(',')
            logger.info(f"解析: {vals}")
            if len(vals) >= 8:
                results["aclr_lower"] = float(vals[1])
                results["aclr_upper"] = float(vals[2])
    except Exception as e:
        logger.error(f"解析错误: {e}")
    
    # 灵敏度
    logger.info("\n=== 灵敏度 ===")
    cmd(sock, f"CONF:LTE:SIGN:DL:RSEP:LEV -95", 0.5)
    cmd(sock, "CONF:LTE:SIGN:EBL:REP SING", 0.5)
    cmd(sock, "CONF:LTE:SIGN:EBL:SFR 100", 0.5)
    cmd(sock, "INIT:LTE:SIGN:EBL", 0.5)
    
    time.sleep(3)
    
    r = cmd(sock, "FETC:LTE:SIGN:EBL:REL?")
    logger.info(f"BLER原始: {r}")
    
    try:
        if r:
            vals = r.split(',')
            if len(vals) >= 2:
                results["bler_percent"] = float(vals[1])
    except:
        pass

sock.close()

# 保存
fname = f"lte_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(fname, 'w') as f:
    json.dump(results, f, indent=2)

logger.info(f"\n结果: {fname}")
logger.info(f"\n=== 结果 ===")
logger.info(f"状态: {results.get('dut_status', 'N/A')}")
logger.info(f"功率: {results.get('power_dbm', 0):.2f} dBm")
logger.info(f"EVM: {results.get('evm_percent', 0):.2f}%")
logger.info(f"ACLR: {results.get('aclr_lower', 0):.2f} / {results.get('aclr_upper', 0):.2f} dBc")
logger.info(f"BLER: {results.get('bler_percent', 100):.2f}%")
