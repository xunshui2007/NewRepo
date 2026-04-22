#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE 信令测试系统
使用正确的SCPI命令格式

基于用户提供的参考代码
"""

import socket
import time
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# CMW500地址 - 用户的实际地址
CMW_IP = "192.168.121.116"
CMW_PORT = 5025


class CMW500_LTE:
    def __init__(self, ip: str, port: int = 5025):
        self.ip = ip
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect(self) -> bool:
        try:
            logger.info(f"连接CMW500: {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.ip, self.port))
            
            # 测试连接
            self.socket.sendall(b"*IDN?\n")
            time.sleep(0.3)
            self.socket.settimeout(5)
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if chunk:
                        response += chunk
                        if response.endswith(b'\n'):
                            break
                except:
                    break
            
            idn = response.decode('utf-8').strip()
            logger.info(f"CMW500: {idn}")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def send_cmd(self, cmd: str, wait: float = 0.3) -> str:
        """发送命令"""
        if not self.connected:
            return ""
        try:
            self.socket.sendall(f"{cmd}\n".encode('utf-8'))
            time.sleep(wait)
            self.socket.settimeout(5)
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b'\n'):
                        break
                except:
                    break
            return response.decode('utf-8').strip()
        except Exception as e:
            logger.error(f"命令失败: {cmd}, 错误: {e}")
            return ""
    
    def write(self, cmd: str):
        """发送写命令"""
        self.send_cmd(cmd, 0.2)
    
    def query(self, cmd: str) -> str:
        """发送查询命令"""
        return self.send_cmd(cmd, 0.5)
    
    def check_connection(self) -> bool:
        """检查DUT连接状态"""
        # 使用正确的命令格式: FETC:LTE:SIGN:PSW:STAT?
        result = self.query("FETC:LTE:SIGN:PSW:STAT?")
        logger.info(f"DUT状态: {result}")
        
        s = result.strip()
        if s == "CEST" or s == "ATT":
            return True
        return False
    
    def connect_dut(self) -> bool:
        """连接DUT"""
        # 先检查状态
        if self.check_connection():
            return True
        
        # 发起连接
        logger.info("发起连接...")
        self.write("CALL:LTE:SIGN:PSW:ACT CONN")
        time.sleep(1)
        
        # 等待连接
        for i in range(10):
            time.sleep(1)
            if self.check_connection():
                logger.info("DUT已连接!")
                return True
        
        return False
    
    def measure_power(self) -> float:
        """测量功率"""
        # 使用EVM测量中的功率
        result = self.query("FETC:LTE:MEAS:MEV:MOD:AVER?")
        
        try:
            if result:
                values = result.split(',')
                # 功率通常在第5个位置 (根据参考代码)
                if len(values) >= 5:
                    power = float(values[4])
                    return power
        except Exception as e:
            logger.error(f"功率解析失败: {e}")
        
        return -999.0
    
    def measure_aclr(self) -> tuple:
        """测量ACLR - 返回 (E-UTRA Lower, E-UTRA Upper, etc)"""
        result = self.query("FETC:LTE:MEAS:MEV:ACLR:AVER?")
        
        aclr = {"EUTRA_lower": 0, "EUTRA_upper": 0, "UTRA_lower": 0, "UTRA_upper": 0}
        
        try:
            if result:
                values = result.split(',')
                if len(values) >= 8:
                    # 根据参考代码格式
                    aclr["EUTRA_upper"] = float(values[1])  # 下邻
                    aclr["EUTRA_lower"] = float(values[2])  # 上邻
                    aclr["UTRA_upper"] = float(values[5])   # 交替
                    aclr["UTRA_lower"] = float(values[6])
        except Exception as e:
            logger.error(f"ACLR解析失败: {e}")
        
        return aclr
    
    def measure_evm(self) -> float:
        """测量EVM"""
        result = self.query("FETC:LTE:MEAS:MEV:MOD:AVER?")
        
        try:
            if result:
                values = result.split(',')
                if len(values) >= 4:
                    evm = float(values[3])
                    return evm
        except Exception as e:
            logger.error(f"EVM解析失败: {e}")
        
        return -999.0
    
    def measure_all(self) -> dict:
        """测量所有参数 (功率, ACLR, EVM)"""
        # 先配置测量
        self.write("CONF:LTE:MEAS:MEValuation:RESult:ALL ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON,ON")
        self.write("CONFigure:LTE:MEAS:MEValuation:RESult:EVMagnitude:EVMSymbol ON, 3, LOW")
        self.write("CONF:LTE:MEAS:MEV:REP SING")
        self.write("CONFigure:LTE:SIGN:UL:PUSCH:TPC:SET MAXP")
        self.write("INIT:LTE:MEAS:MEValuation")
        
        # 等待测量完成
        time.sleep(2)
        
        # 读取结果
        result = {
            "power_dbm": 0,
            "evm_percent": 0,
            "aclr": {}
        }
        
        # EVM
        evm_result = self.query("FETC:LTE:MEAS:MEV:MOD:AVER?")
        try:
            if evm_result:
                values = evm_result.split(',')
                if len(values) >= 5:
                    result["power_dbm"] = float(values[4])  # 功率
                    result["evm_percent"] = float(values[3]) # EVM
        except:
            pass
        
        # ACLR
        aclr_result = self.query("FETC:LTE:MEAS:MEV:ACLR:AVER?")
        try:
            if aclr_result:
                values = aclr_result.split(',')
                if len(values) >= 8:
                    result["aclr"] = {
                        "EUTRA_lower_adj": float(values[1]),
                        "EUTRA_upper_adj": float(values[2]),
                        "UTRA_lower_adj": float(values[5]),
                        "UTRA_upper_adj": float(values[6])
                    }
        except:
            pass
        
        return result
    
    def measure_sensitivity(self, level_dbm: float = -100) -> float:
        """测量灵敏度 - 设置不同电平进行BLER测试"""
        # 设置电平
        self.write(f"CONF:LTE:SIGN:DL:RSEP:LEV {level_dbm}")
        
        # 进行BLER测试
        self.write("CONF:LTE:SIGN:EBL:REP SING")
        self.write("CONF:LTE:SIGN:EBL:SFR 200")  # 包数量
        self.write("INIT:LTE:SIGN:EBL")
        
        time.sleep(1)
        
        # 查询状态
        for i in range(10):
            time.sleep(0.5)
            status = self.query("FETC:LTE:SIGN:EBL:STAT?")
            if status and status.strip() != "":
                break
        
        # 读取BLER
        ber_result = self.query("FETC:LTE:SIGN:EBL:REL?")
        
        try:
            if ber_result:
                values = ber_result.split(',', 5)
                if len(values) >= 2:
                    bler = float(values[1])
                    return bler
        except:
            pass
        
        return 100.0
    
    def close(self):
        if self.socket:
            self.socket.close()
            self.connected = False


def run_test():
    """运行测试"""
    cmw = CMW500_LTE(CMW_IP, CMW_PORT)
    
    if not cmw.connect():
        logger.error("连接CMW500失败")
        return
    
    logger.info("\n=== 检查DUT连接 ===")
    connected = cmw.check_connection()
    
    if not connected:
        logger.info("DUT未连接，尝试连接...")
        connected = cmw.connect_dut()
    
    results = {
        "time": datetime.now().isoformat(),
        "dut_connected": connected,
        "power_dbm": 0,
        "evm_percent": 0,
        "aclr": {},
        "sensitivity_dbm": 0
    }
    
    if connected:
        logger.info("\n=== 测量功率/ACLR/EVM ===")
        measure_results = cmw.measure_all()
        
        results["power_dbm"] = measure_results.get("power_dbm", 0)
        results["evm_percent"] = measure_results.get("evm_percent", 0)
        results["aclr"] = measure_results.get("aclr", {})
        
        logger.info(f"功率: {results['power_dbm']:.2f} dBm")
        logger.info(f"EVM: {results['evm_percent']:.2f}%")
        
        if results["aclr"]:
            logger.info(f"ACLR E-UTRA: 下邻 {results['aclr'].get('EUTRA_lower_adj', 0):.2f} dBc, "
                       f"上邻 {results['aclr'].get('EUTRA_upper_adj', 0):.2f} dBc")
        
        # 灵敏度测试
        logger.info("\n=== 灵敏度测试 ===")
        # 二分查找
        low = -120
        high = -70
        target_bler = 1.0
        
        while high - low > 2:
            mid = (low + high) / 2
            bler = cmw.measure_sensitivity(mid)
            logger.info(f"电平 {mid:.1f} dBm, BLER: {bler:.2f}%")
            
            if bler <= target_bler:
                high = mid
            else:
                low = mid
        
        results["sensitivity_dbm"] = high
        logger.info(f"灵敏度: {results['sensitivity_dbm']:.2f} dBm (BLER <= 1%)")
    else:
        logger.error("DUT未连接，无法测试")
    
    cmw.close()
    
    # 保存结果
    filename = f"lte_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n结果已保存: {filename}")
    
    # 打印
    logger.info("\n=== 测试结果 ===")
    logger.info(f"DUT连接: {'是' if results['dut_connected'] else '否'}")
    logger.info(f"功率: {results['power_dbm']:.2f} dBm")
    logger.info(f"EVM: {results['evm_percent']:.2f}%")
    if results['aclr']:
        logger.info(f"ACLR: {results['aclr']}")
    logger.info(f"灵敏度: {results['sensitivity_dbm']:.2f} dBm")


if __name__ == "__main__":
    run_test()
