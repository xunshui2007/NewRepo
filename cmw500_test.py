#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 自动化测试系统
用于测试功率、ACLR（邻道泄漏比）和灵敏度

CMW500地址: TCPIP0::192.168.121.116::inst0::INSTR
"""

import socket
import time
import json
import csv
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import sys
import os

import time
import json
import csv
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BandType(Enum):
    """频段类型"""
    # 常用LTE频段
    B1 = "1"      # 2100MHz
    B3 = "3"      # 1800MHz
    B5 = "5"      # 850MHz
    B7 = "7"      # 2600MHz
    B8 = "8"      # 900MHz
    B20 = "20"    # 800MHz
    B28 = "28"    # 700MHz
    B38 = "38"    # 2600MHz TDD
    B40 = "40"    # 2300MHz TDD
    B41 = "41"    # 2500MHz TDD
    
    # 常用NR频段
    N1 = "n1"     # 2100MHz
    N3 = "n3"     # 1800MHz
    N5 = "n5"     # 850MHz
    N7 = "n7"     # 2600MHz
    N28 = "n28"   # 700MHz
    N41 = "n41"   # 2500MHz TDD
    N77 = "n77"   # 3300MHz
    N78 = "n78"   # 3500MHz
    N79 = "n79"   # 4900MHz
    
    @property
    def downlink_mhz(self) -> tuple:
        """获取下行频率范围 (MHz)"""
        band_freqs = {
            "1": (2110, 2170),
            "3": (1805, 1880),
            "5": (869, 894),
            "7": (2620, 2690),
            "8": (925, 960),
            "20": (791, 821),
            "28": (758, 803),
            "38": (2570, 2620),
            "40": (2300, 2400),
            "41": (2496, 2690),
            "n1": (2110, 2170),
            "n3": (1805, 1880),
            "n5": (869, 894),
            "n7": (2620, 2690),
            "n28": (758, 803),
            "n41": (2496, 2690),
            "n77": (3300, 4200),
            "n78": (3300, 3800),
            "n79": (4400, 5000),
        }
        return band_freqs.get(self.value, (0, 0))
    
    @property
    def uplink_mhz(self) -> tuple:
        """获取上行频率范围 (MHz)"""
        band_freqs = {
            "1": (1920, 1980),
            "3": (1710, 1785),
            "5": (824, 849),
            "7": (2500, 2570),
            "8": (880, 915),
            "20": (832, 862),
            "28": (703, 748),
            "38": (2570, 2620),
            "40": (2300, 2400),
            "41": (2496, 2690),
            "n1": (1920, 1980),
            "n3": (1710, 1785),
            "n5": (824, 849),
            "n7": (2500, 2570),
            "n28": (703, 748),
            "n41": (2496, 2690),
            "n77": (3300, 4200),
            "n78": (3300, 3800),
            "n79": (4400, 5000),
        }
        return band_freqs.get(self.value, (0, 0))


class SignalStandard(Enum):
    """信号标准"""
    LTE = "LTE"
    NR = "5G NR"
    WCDMA = "WCDMA"
    GSM = "GSM"


@dataclass
class TestConfig:
    """测试配置"""
    cmw_ip: str = "192.168.121.116"
    cmw_port: int = 5025
    signal_standard: str = "LTE"
    band: str = "3"
    bandwidth_mhz: int = 20  # 带宽 MHz
    dl_channel: int = 1850  # 下行信道
    ul_channel: int = 1950  # 上行信道
    output_power_dbm: int = 23  # 输出功率 dBm
    
    # ACLR设置
    aclr_limit_lower_db: float = -45.0  # ACLR下限 dBc
    aclr_limit_upper_db: float = -45.0
    
    # 灵敏度设置
    sensitivity_target_bler: float = 1.0  # 目标BLER %
    sensitivity_min_power_dbm: float = -120.0


@dataclass
class PowerResult:
    """功率测试结果"""
    frequency_mhz: float
    channel: int
    power_dbm: float
    limit_dbm: float
    passed: bool
    timestamp: str


@dataclass
class ACLRResult:
    """ACLR测试结果"""
    frequency_mhz: float = 0.0
    channel: int = 0
    lower_adj_power_dbm: float = 0.0
    lower_adj_power_dbch: float = 0.0
    upper_adj_power_dbm: float = 0.0
    upper_adj_power_dbch: float = 0.0
    lower_alt1_power_dbm: float = 0.0
    lower_alt1_power_dbch: float = 0.0
    upper_alt1_power_dbm: float = 0.0
    upper_alt1_power_dbch: float = 0.0
    lower_alt2_power_dbm: float = 0.0
    lower_alt2_power_dbch: float = 0.0
    upper_alt2_power_dbm: float = 0.0
    upper_alt2_power_dbch: float = 0.0
    limit_db: float = -45.0
    passed: bool = False
    timestamp: str = ""


@dataclass
class SensitivityResult:
    """灵敏度测试结果"""
    frequency_mhz: float = 0.0
    channel: int = 0
    sensitivity_power_dbm: float = 0.0
    bler_percent: float = 0.0
    passed: bool = False
    timestamp: str = ""


class CMW500:
    """CMW500仪器控制类 - 使用Socket连接"""
    
    def __init__(self, ip: str, port: int = 5025):
        self.ip = ip
        self.port = port
        self.resource_address = f"TCPIP0::{ip}::inst0::INSTR"
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
    def connect(self) -> bool:
        """连接CMW500"""
        try:
            logger.info(f"正在连接CMW500: {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((self.ip, self.port))
            
            # 测试连接 - 直接发送和接收
            self.socket.sendall(b"*IDN?\n")
            self.socket.settimeout(10)
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if chunk:
                        response += chunk
                        if response.endswith(b'\n'):
                            break
                    else:
                        break
                except socket.timeout:
                    break
            
            idn = response.decode('utf-8').strip()
            logger.info(f"CMW500连接成功: {idn}")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"连接CMW500失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            self.connected = False
            logger.info("CMW500已断开连接")
    
    def write(self, command: str):
        """发送SCPI命令"""
        if not self.connected:
            raise ConnectionError("未连接到CMW500")
        try:
            self.socket.sendall(f"{command}\n".encode('utf-8'))
        except Exception as e:
            logger.error(f"发送命令失败: {command}, 错误: {e}")
            raise
    
    def query(self, command: str) -> str:
        """查询SCPI命令"""
        if not self.connected:
            raise ConnectionError("未连接到CMW500")
        try:
            self.socket.sendall(f"{command}\n".encode('utf-8'))
            # 读取响应
            response = b""
            self.socket.settimeout(10)  # 设置超时
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    # 检查是否结束 (通常以\n结尾)
                    if response.endswith(b'\n'):
                        break
                except socket.timeout:
                    break
            return response.decode('utf-8').strip()
        except Exception as e:
            logger.error(f"查询命令失败: {command}, 错误: {e}")
            raise
    
    def reset(self):
        """复位仪器"""
        logger.info("复位CMW500...")
        self.write("*RST")
        time.sleep(2)
    
    def set_signal_standard(self, standard: str, band: str, bandwidth: int = 20):
        """设置信号标准"""
        logger.info(f"设置信号标准: {standard}, Band {band}, BW {bandwidth}MHz")
        
        if standard == "LTE":
            # 选择LTE FDD
            self.write("ROUTe:LTE:MEAS:SCENario:CSP")
            self.write(f"SYSTem:BAND:INDex LTE,{band}")
            self.write(f"CONF:LTE:DL:BANDwidth {bandwidth}")
            self.write(f"CONF:LTE:UL:BANDwidth {bandwidth}")
        elif standard == "5G NR":
            # 选择5G NR
            self.write("ROUTe:NR5G:MEAS:SCENario:CSP")
            self.write(f"SYSTem:BAND:INDex NR5G,{band}")
            self.write(f"CONF:NR5G:DL:BANDwidth {bandwidth}")
            self.write(f"CONF:NR5G:UL:BANDwidth {bandwidth}")
    
    def set_frequency(self, channel: int, direction: str = "DL"):
        """设置频率/信道"""
        if direction == "DL":
            self.write(f"CONF:LTE:DL:FREQuency:CHANnel {channel}")
        else:
            self.write(f"CONF:LTE:UL:FREQuency:CHANnel {channel}")
    
    def set_output_power(self, power_dbm: int):
        """设置输出功率"""
        logger.info(f"设置输出功率: {power_dbm} dBm")
        self.write(f"POW:RF:OUTP {power_dbm}")
    
    def measure_power(self) -> float:
        """测量功率 - 使用GPRF模式"""
        # 使用GPRF进行功率测量
        self.write(f"CONFigure:GPRf:MEAS:POW:AVG:SCOunt 10")
        
        # 触发测量
        self.write("INIT:GPRf:MEAS:POW")
        time.sleep(1)
        
        # 读取功率结果
        result = self.query("FETCh:GPRf:MEAS:POW:AVER?")
        try:
            parts = result.strip().split(',')
            if len(parts) >= 2:
                status = int(parts[0])
                if status == 0:
                    power = float(parts[1])
                    return power
        except:
            pass
        return -999.0
    
    def measure_aclr(self) -> ACLRResult:
        """测量ACLR"""
        # 触发ACLR测量
        self.write("INIT:LTE:MEAS:ACLR")
        time.sleep(2)
        
        # 读取ACLR结果 - 尝试READ命令
        result = self.query("READ:LTE:MEAS:ACLR:REST?")
        
        aclr = ACLRResult(timestamp=datetime.now().isoformat())
        
        if not result or result == "0":
            # 尝试FETCh命令
            result = self.query("FETCh:LTE:MEAS:ACLR:REST?")
        
        try:
            values = result.strip().split(',')
            if len(values) >= 4 and values[0] != "0":
                aclr.lower_adj_power_dbm = float(values[0])
                aclr.lower_adj_power_dbch = float(values[1])
                aclr.upper_adj_power_dbm = float(values[2])
                aclr.upper_adj_power_dbch = float(values[3])
                
                if len(values) >= 8:
                    aclr.lower_alt1_power_dbm = float(values[4])
                    aclr.lower_alt1_power_dbch = float(values[5])
                    aclr.upper_alt1_power_dbm = float(values[6])
                    aclr.upper_alt1_power_dbch = float(values[7])
                
                # 判断是否通过
                aclr.passed = (aclr.lower_adj_power_dbch >= aclr.limit_db and 
                              aclr.upper_adj_power_dbch >= aclr.limit_db)
        except Exception as e:
            logger.error(f"ACLR测量解析失败: {e}")
        
        return aclr
    
    def measure_sensitivity(self, target_bler: float = 1.0) -> float:
        """测量灵敏度"""
        # 设置BLER目标
        self.write(f"CONF:LTE:MEAS:BLER:TARG {target_bler}")
        
        # 开始BLER测量
        self.write("INIT:LTE:MEAS:BLER")
        
        # 等待测量完成
        time.sleep(3)
        
        # 读取灵敏度功率电平
        result = self.query("FETCh:LTE:MEAS:BLER:EVENt:PHYS?")
        
        try:
            # 解析结果
            values = result.strip().split(',')
            sensitivity = float(values[0])
            return sensitivity
        except:
            return -999.0
    
    def search_sensitivity(self, start_power: float = -80, 
                           target_bler: float = 1.0, 
                           step: int = 2) -> float:
        """搜索灵敏度"""
        logger.info(f"开始搜索灵敏度 (目标BLER: {target_bler}%)...")
        
        current_power = start_power
        self.set_output_power(int(current_power))
        
        while current_power > -120:
            self.set_output_power(int(current_power))
            time.sleep(0.5)
            
            # 测量BLER
            self.write("INIT:LTE:MEAS:BLER")
            time.sleep(2)
            
            result = self.query("FETCh:LTE:MEAS:BLER:STAT?")
            try:
                bler = float(result.strip())
                logger.info(f"功率: {current_power} dBm, BLER: {bler}%")
                
                if bler <= target_bler:
                    # 找到了灵敏度
                    return current_power
            except:
                pass
            
            current_power -= step
        
        return -999.0


class CMW500TestSystem:
    """CMW500自动化测试系统"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.cmw = CMW500(config.cmw_ip, config.cmw_port)
        self.results: Dict[str, Any] = {
            "config": asdict(config),
            "power_results": [],
            "aclr_results": [],
            "sensitivity_results": [],
            "test_time": ""
        }
    
    def connect(self) -> bool:
        """连接测试仪器"""
        return self.cmw.connect()
    
    def disconnect(self):
        """断开连接"""
        self.cmw.disconnect()
    
    def initialize(self):
        """初始化测试系统"""
        logger.info("初始化测试系统...")
        self.cmw.reset()
        time.sleep(3)
        
        # 设置信号标准
        self.cmw.set_signal_standard(
            self.config.signal_standard,
            self.config.band,
            self.config.bandwidth_mhz
        )
        
        # 设置信道
        self.cmw.set_frequency(self.config.dl_channel, "DL")
        self.cmw.set_frequency(self.config.ul_channel, "UL")
        
        # 设置输出功率
        self.cmw.set_output_power(self.config.output_power_dbm)
        
        # 启用功率测量
        self.cmw.write("CONFigure:LTE:MEAS:POW:ENABLE ON")
        self.cmw.write("CONFigure:LTE:MEAS:ACLR:ENABLE ON")
        
        time.sleep(2)
    
    def test_power(self, channel: int = None) -> PowerResult:
        """测试功率"""
        if channel:
            self.cmw.set_frequency(channel, "DL")
        
        logger.info("测试功率...")
        power = self.cmw.measure_power()
        
        # 根据频段计算频率
        band = BandType(self.config.band)
        freq_low, freq_high = band.downlink_mhz
        center_freq = (freq_low + freq_high) / 2
        
        result = PowerResult(
            frequency_mhz=center_freq,
            channel=channel or self.config.dl_channel,
            power_dbm=power,
            limit_dbm=self.config.output_power_dbm - 3,  # 允许3dB误差
            passed=abs(power - self.config.output_power_dbm) <= 3,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"功率测试结果: {power:.2f} dBm, 通过: {result.passed}")
        self.results["power_results"].append(asdict(result))
        return result
    
    def test_aclr(self, channel: int = None) -> ACLRResult:
        """测试ACLR"""
        if channel:
            self.cmw.set_frequency(channel, "DL")
        
        logger.info("测试ACLR...")
        result = self.cmw.measure_aclr()
        result.channel = channel or self.config.dl_channel
        
        # 计算频率
        band = BandType(self.config.band)
        freq_low, freq_high = band.downlink_mhz
        result.frequency_mhz = (freq_low + freq_high) / 2
        result.limit_db = self.config.aclr_limit_lower_db
        
        logger.info(f"ACLR测试结果: 下邻 {result.lower_adj_power_dbch:.2f} dBc, "
                   f"上邻 {result.upper_adj_power_dbch:.2f} dBc, 通过: {result.passed}")
        
        self.results["aclr_results"].append(asdict(result))
        return result
    
    def test_sensitivity(self, channel: int = None) -> SensitivityResult:
        """测试灵敏度"""
        if channel:
            self.cmw.set_frequency(channel, "DL")
        
        logger.info("测试灵敏度...")
        
        sensitivity_power = self.cmw.search_sensitivity(
            start_power=self.config.sensitivity_min_power_dbm,
            target_bler=self.config.sensitivity_target_bler
        )
        
        band = BandType(self.config.band)
        freq_low, freq_high = band.downlink_mhz
        center_freq = (freq_low + freq_high) / 2
        
        result = SensitivityResult(
            frequency_mhz=center_freq,
            channel=channel or self.config.dl_channel,
            sensitivity_power_dbm=sensitivity_power,
            bler_percent=self.config.sensitivity_target_bler,
            passed=sensitivity_power < -100,  # 根据具体要求设置
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"灵敏度测试结果: {sensitivity_power:.2f} dBm, 通过: {result.passed}")
        self.results["sensitivity_results"].append(asdict(result))
        return result
    
    def run_full_test(self, bands: List[str] = None) -> Dict:
        """运行完整测试"""
        if bands is None:
            bands = [self.config.band]
        
        self.results["test_time"] = datetime.now().isoformat()
        
        for band in bands:
            logger.info(f"\n{'='*50}")
            logger.info(f"测试频段: {band}")
            logger.info(f"{'='*50}")
            
            self.config.band = band
            
            # 根据频段设置信道
            # 这里需要根据具体频段的信道表来设置
            # 简化处理，使用默认信道
            self.initialize()
            
            # 功率测试
            self.test_power()
            
            # ACLR测试
            self.test_aclr()
            
            # 灵敏度测试
            self.test_sensitivity()
            
            time.sleep(1)
        
        return self.results
    
    def save_results(self, filename: str = None):
        """保存测试结果"""
        if filename is None:
            filename = f"cmw500_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"测试结果已保存到: {filename}")
        
        # 同时保存CSV格式
        csv_filename = filename.replace('.json', '.csv')
        self._save_csv(csv_filename)
        
        return filename
    
    def _save_csv(self, filename: str):
        """保存CSV格式结果"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['测试项目', '频率(MHz)', '信道', '结果', '限值', '通过/失败'])
            
            # 功率结果
            for r in self.results["power_results"]:
                writer.writerow([
                    '功率', r['frequency_mhz'], r['channel'],
                    f"{r['power_dbm']:.2f} dBm", f"{r['limit_dbm']:.2f} dBm",
                    'PASS' if r['passed'] else 'FAIL'
                ])
            
            # ACLR结果
            for r in self.results["aclr_results"]:
                writer.writerow([
                    'ACLR', r['frequency_mhz'], r['channel'],
                    f"{r['lower_adj_power_dbch']:.2f} dBc", f"{r['limit_db']:.2f} dBc",
                    'PASS' if r['passed'] else 'FAIL'
                ])
            
            # 灵敏度结果
            for r in self.results["sensitivity_results"]:
                writer.writerow([
                    '灵敏度', r['frequency_mhz'], r['channel'],
                    f"{r['sensitivity_power_dbm']:.2f} dBm", '< -100 dBm',
                    'PASS' if r['passed'] else 'FAIL'
                ])
        
        logger.info(f"CSV结果已保存到: {filename}")


def get_channel_for_band(band: str, band_type: str = "DL", bandwidth: int = 20) -> int:
    """根据频段获取默认信道"""
    # LTE频段信道映射表 (简化版)
    channels = {
        ("1", "DL"): 350, ("1", "UL"): 18250,
        ("3", "DL"): 1850, ("3", "UL"): 1950,
        ("5", "DL"): 245, ("5", "UL"): 20425,
        ("7", "DL"): 2850, ("7", "UL"): 2100,
        ("8", "DL"): 345, ("8", "UL"): 21450,
        ("20", "DL"): 6150, ("20", "UL"): 24150,
    }
    return channels.get((band, band_type), 1850)


def main():
    """主函数"""
    # 创建测试配置
    config = TestConfig(
        cmw_ip="192.168.121.116",
        cmw_port=5025,
        signal_standard="LTE",
        band="3",
        bandwidth_mhz=20,
        dl_channel=1850,
        ul_channel=1950,
        output_power_dbm=23,
        aclr_limit_lower_db=-45.0,
        sensitivity_target_bler=1.0
    )
    
    # 创建测试系统
    test_system = CMW500TestSystem(config)
    
    try:
        # 连接
        if not test_system.connect():
            logger.error("连接失败，退出测试")
            return
        
        # 测试频段列表
        test_bands = ["3", "7", "20"]  # 可以添加更多频段
        
        # 运行测试
        results = test_system.run_full_test(bands=test_bands)
        
        # 保存结果
        test_system.save_results()
        
        # 打印摘要
        logger.info("\n" + "="*50)
        logger.info("测试完成!")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_system.disconnect()


if __name__ == "__main__":
    main()
