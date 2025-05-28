#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAVR FSI Analysis System 安装脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    return True

def create_directories():
    """创建必要的目录结构"""
    directories = [
        'data',
        'data/patients',
        'data/templates',
        'results',
        'logs',
        'cache',
        'resources',
        'resources/icons',
        'docs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"创建目录: {directory}")

def install_dependencies():
    """安装依赖包"""
    print("\n安装依赖包...")
    
    # 升级pip
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # 安装requirements.txt中的包
    if os.path.exists("requirements.txt"):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("依赖包安装完成")
    else:
        print("警告: 未找到requirements.txt文件")

def download_resources():
    """下载必要的资源文件"""
    print("\n准备资源文件...")
    
    # 创建示例图标文件
    icon_path = Path("resources/icons")
    
    icons = [
        'icon.png',
        'import.png',
        'segment.png',
        'mesh.png',
        'simulate.png',
        'report.png'
    ]
    
    # 这里应该下载实际的图标文件
    # 现在只是创建占位文件
    for icon in icons:
        icon_file = icon_path / icon
        if not icon_file.exists():
            icon_file.touch()
            print(f"创建图标占位文件: {icon}")

def create_shortcuts():
    """创建快捷方式"""
    print("\n创建启动脚本...")
    
    # Windows批处理文件
    if sys.platform == "win32":
        bat_content = """@echo off
echo 启动TAVR流固耦合分析系统...
python tavr_fsi_gui.py
pause
"""
        with open("启动TAVR分析系统.bat", "w", encoding="gbk") as f:
            f.write(bat_content)
        print("创建Windows启动脚本: 启动TAVR分析系统.bat")
    
    # Linux/Mac shell脚本
    else:
        sh_content = """#!/bin/bash
echo "启动TAVR流固耦合分析系统..."
python3 tavr_fsi_gui.py
"""
        with open("launch_tavr.sh", "w") as f:
            f.write(sh_content)
        
        # 设置执行权限
        os.chmod("launch_tavr.sh", 0o755)
        print("创建Unix启动脚本: launch_tavr.sh")

def create_config():
    """创建默认配置文件"""
    print("\n创建配置文件...")
    
    config_content = """# TAVR FSI Analysis System Configuration
# 系统默认配置文件

[General]
work_directory = ./data
auto_save = true
save_interval = 10
language = zh_CN

[Simulation]
solver = internal
threads = 4
convergence_residual = 1e-4
max_iterations = 1000
time_step = 0.001
simulation_cycles = 3

[Display]
antialiasing = true
transparency = true
background = gradient
velocity_colormap = jet
pressure_colormap = coolwarm

[Advanced]
debug_mode = false
verbose_logging = false
save_intermediate = false
gpu_acceleration = false
cache_size = 1000
"""
    
    with open("config.ini", "w") as f:
        f.write(config_content)
    print("创建配置文件: config.ini")

def create_sample_data():
    """创建示例数据"""
    print("\n创建示例数据...")
    
    # 创建示例患者数据模板
    template_content = {
        "patient_id": "SAMPLE001",
        "patient_name": "示例患者",
        "age": 75,
        "sex": "男",
        "diagnosis": "重度主动脉瓣狭窄",
        "valve_parameters": {
            "annulus_diameter": 24.5,
            "sov_height": 12.0,
            "stj_diameter": 28.0
        }
    }
    
    import json
    with open("data/templates/patient_template.json", "w", encoding="utf-8") as f:
        json.dump(template_content, f, ensure_ascii=False, indent=2)
    print("创建患者数据模板")

def test_installation():
    """测试安装是否成功"""
    print("\n测试安装...")
    
    # 测试导入主要模块
    try:
        import PyQt5
        print("✓ PyQt5 安装成功")
    except ImportError:
        print("✗ PyQt5 安装失败")
        return False
    
    try:
        import SimpleITK
        print("✓ SimpleITK 安装成功")
    except ImportError:
        print("✗ SimpleITK 安装失败")
        return False
    
    try:
        import vtk
        print("✓ VTK 安装成功")
    except ImportError:
        print("✗ VTK 安装失败")
        return False
    
    try:
        import numpy
        import scipy
        import matplotlib
        print("✓ 科学计算库安装成功")
    except ImportError:
        print("✗ 科学计算库安装失败")
        return False
    
    return True

def main():
    """主安装函数"""
    print("="*60)
    print("TAVR流固耦合分析系统 - 安装程序")
    print("="*60)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    print(f"\nPython版本: {sys.version}")
    print(f"安装目录: {os.getcwd()}")
    
    # 确认安装
    response = input("\n是否继续安装? (y/n): ")
    if response.lower() != 'y':
        print("安装已取消")
        sys.exit(0)
    
    try:
        # 执行安装步骤
        create_directories()
        install_dependencies()
        download_resources()
        create_shortcuts()
        create_config()
        create_sample_data()
        
        # 测试安装
        if test_installation():
            print("\n" + "="*60)
            print("安装成功！")
            print("="*60)
            print("\n使用说明:")
            if sys.platform == "win32":
                print("1. 双击 '启动TAVR分析系统.bat' 运行程序")
            else:
                print("1. 运行 './launch_tavr.sh' 启动程序")
            print("2. 或直接运行: python tavr_fsi_gui.py")
            print("\n首次使用建议查看用户手册")
        else:
            print("\n安装未完全成功，请检查错误信息")
            
    except Exception as e:
        print(f"\n安装过程中出现错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()