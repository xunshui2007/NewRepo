# CMW500 自动化测试系统使用说明

## 简介

本程序实现对罗德与施瓦茨(R&S) CMW500无线通信测试仪的自动化控制，支持：
- **功率测试 (Power)**: 测量发射功率
- **ACLR测试**: 测量邻道泄漏比
- **灵敏度测试 (Sensitivity)**: 测量接收灵敏度

## 安装

1. 安装Python 3.8或更高版本

2. 安装依赖包:
```bash
pip install -r requirements.txt
```

或者使用pyvisa-py（纯Python实现，无需NI-VISA）:
```bash
pip install pyvisa pyvisa-py
```

## 连接配置

CMW500 IP地址: `192.168.121.116`

确保:
1. CMW500已连接到网络
2. CMW500的SCPI端口已开启 (默认5025)
3. 电脑与CMW500在同一网络段

## 使用方法

### 方法1: 运行完整测试

```bash
python cmw500_test.py
```

### 方法2: 自定义测试

```python
from cmw500_test import CMW500TestSystem, TestConfig, BandType

# 创建配置
config = TestConfig(
    cmw_ip="192.168.121.116",
    signal_standard="LTE",      # LTE 或 5G NR
    band="3",                   # 频段
    bandwidth_mhz=20,           # 带宽
    output_power_dbm=23,        # 输出功率
    aclr_limit_lower_db=-45.0,  # ACLR限值
)

# 创建测试系统
test_system = CMW500TestSystem(config)

# 连接
if test_system.connect():
    # 测试多个频段
    results = test_system.run_full_test(bands=["3", "7", "20"])
    
    # 保存结果
    test_system.save_results("my_test_results.json")
    
    # 断开连接
    test_system.disconnect()
```

### 方法3: 单独测试

```python
# 连接
test_system.connect()
test_system.initialize()

# 单独测试
power_result = test_system.test_power()
aclr_result = test_system.test_aclr()
sensitivity_result = test_system.test_sensitivity()

test_system.disconnect()
```

## 频段支持

支持的LTE频段:
- B1 (2100MHz), B3 (1800MHz), B5 (850MHz), B7 (2600MHz)
- B8 (900MHz), B20 (800MHz), B28 (700MHz)
- B38, B40, B41 (TDD频段)

支持的5G NR频段:
- N1, N3, N5, N7, N28, N41, N77, N78, N79

## 输出结果

程序会生成两种格式的测试结果:
1. **JSON格式**: 完整的测试数据
2. **CSV格式**: 方便查看和导入Excel

## 常见问题

### 1. 连接失败
- 检查IP地址是否正确
- 确认防火墙允许5025端口
- 确认CMW500网络配置正确

### 2. 测量结果异常
- 确认被测设备(DUT)已正确连接
- 检查射频线缆是否完好
- 确认信号标准设置正确

### 3. PyVISA安装问题
Windows建议安装NI-VISA:
https://www.ni.com/zh-cn/support/downloads/drivers/download.ni-visa.html

或者使用纯Python版本:
```bash
pip install pyvisa-py
```
