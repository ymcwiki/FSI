#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAVR分析系统实用工具集
提供系统维护、数据管理等功能
"""

import os
import sys
import shutil
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import zipfile

class TAVRUtilities:
    """TAVR系统实用工具类"""
    
    def __init__(self):
        self.base_dir = Path.cwd()
        self.data_dir = self.base_dir / "data"
        self.results_dir = self.base_dir / "results"
        self.logs_dir = self.base_dir / "logs"
        self.cache_dir = self.base_dir / "cache"
        
    def clean_cache(self, days_old=7):
        """
        清理缓存文件
        
        参数:
            days_old: 清理多少天前的文件
        """
        print(f"清理{days_old}天前的缓存文件...")
        
        if not self.cache_dir.exists():
            print("缓存目录不存在")
            return
            
        cutoff_time = datetime.now() - timedelta(days=days_old)
        removed_count = 0
        removed_size = 0
        
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    removed_count += 1
                    removed_size += file_size
                    
        print(f"已删除 {removed_count} 个文件，释放 {removed_size/1024/1024:.2f} MB 空间")
        
    def clean_logs(self, days_old=30):
        """
        清理日志文件
        
        参数:
            days_old: 清理多少天前的日志
        """
        print(f"清理{days_old}天前的日志文件...")
        
        if not self.logs_dir.exists():
            print("日志目录不存在")
            return
            
        cutoff_time = datetime.now() - timedelta(days=days_old)
        removed_count = 0
        
        for log_file in self.logs_dir.glob("*.log"):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_time:
                log_file.unlink()
                removed_count += 1
                
        print(f"已删除 {removed_count} 个日志文件")
        
    def export_patient_data(self, patient_id, output_file=None):
        """
        导出患者数据
        
        参数:
            patient_id: 患者ID
            output_file: 输出文件名
        """
        print(f"导出患者数据: {patient_id}")
        
        if output_file is None:
            output_file = f"export_{patient_id}_{datetime.now().strftime('%Y%m%d')}.zip"
            
        patient_dir = self.data_dir / "patients" / patient_id
        
        if not patient_dir.exists():
            print(f"错误: 未找到患者 {patient_id} 的数据")
            return False
            
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加患者数据
            for file_path in patient_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.data_dir)
                    zipf.write(file_path, arcname)
                    
            # 添加相关结果
            results_pattern = f"*{patient_id}*"
            for result_file in self.results_dir.glob(results_pattern):
                if result_file.is_file():
                    arcname = Path("results") / result_file.name
                    zipf.write(result_file, arcname)
                    
        print(f"数据已导出到: {output_file}")
        return True
        
    def import_patient_data(self, import_file):
        """
        导入患者数据
        
        参数:
            import_file: 导入的zip文件
        """
        print(f"导入患者数据: {import_file}")
        
        if not os.path.exists(import_file):
            print(f"错误: 文件 {import_file} 不存在")
            return False
            
        try:
            with zipfile.ZipFile(import_file, 'r') as zipf:
                # 解压到临时目录
                temp_dir = self.base_dir / "temp_import"
                temp_dir.mkdir(exist_ok=True)
                
                zipf.extractall(temp_dir)
                
                # 移动文件到正确位置
                for item in temp_dir.rglob("*"):
                    if item.is_file():
                        relative_path = item.relative_to(temp_dir)
                        target_path = self.base_dir / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(target_path))
                        
                # 清理临时目录
                shutil.rmtree(temp_dir)
                
            print("数据导入成功")
            return True
            
        except Exception as e:
            print(f"导入失败: {str(e)}")
            return False
            
    def list_patients(self):
        """列出所有患者"""
        print("患者列表:")
        print("-" * 60)
        
        patients_dir = self.data_dir / "patients"
        if not patients_dir.exists():
            print("无患者数据")
            return
            
        patient_count = 0
        for patient_dir in patients_dir.iterdir():
            if patient_dir.is_dir():
                patient_id = patient_dir.name
                
                # 查找元数据
                metadata_file = patient_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    patient_name = metadata.get('name', '未知')
                    study_date = metadata.get('study_date', '未知')
                else:
                    patient_name = "未知"
                    study_date = "未知"
                    
                print(f"ID: {patient_id:<15} 姓名: {patient_name:<20} 检查日期: {study_date}")
                patient_count += 1
                
        print("-" * 60)
        print(f"共 {patient_count} 位患者")
        
    def generate_statistics(self):
        """生成系统使用统计"""
        print("系统使用统计")
        print("=" * 60)
        
        # 统计患者数
        patients_dir = self.data_dir / "patients"
        patient_count = len(list(patients_dir.glob("*"))) if patients_dir.exists() else 0
        print(f"患者总数: {patient_count}")
        
        # 统计结果文件
        if self.results_dir.exists():
            result_files = list(self.results_dir.glob("*"))
            print(f"结果文件数: {len(result_files)}")
            
            # 按类型统计
            file_types = {}
            for file in result_files:
                ext = file.suffix
                file_types[ext] = file_types.get(ext, 0) + 1
                
            print("\n文件类型分布:")
            for ext, count in file_types.items():
                print(f"  {ext}: {count}")
                
        # 磁盘使用统计
        print("\n磁盘使用:")
        for dir_name, dir_path in [
            ("数据目录", self.data_dir),
            ("结果目录", self.results_dir),
            ("缓存目录", self.cache_dir),
            ("日志目录", self.logs_dir)
        ]:
            if dir_path.exists():
                size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                print(f"  {dir_name}: {size/1024/1024:.2f} MB")
                
        # 最近活动
        print("\n最近活动:")
        recent_files = []
        for dir_path in [self.results_dir, self.logs_dir]:
            if dir_path.exists():
                for file in dir_path.glob("*"):
                    if file.is_file():
                        recent_files.append((file, file.stat().st_mtime))
                        
        recent_files.sort(key=lambda x: x[1], reverse=True)
        
        print("最近修改的文件:")
        for file, mtime in recent_files[:5]:
            time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {time_str} - {file.name}")
            
    def backup_system(self, backup_name=None):
        """
        备份系统数据
        
        参数:
            backup_name: 备份文件名
        """
        if backup_name is None:
            backup_name = f"tavr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
        print(f"创建系统备份: {backup_name}")
        
        with zipfile.ZipFile(backup_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 备份数据目录
            for dir_path in [self.data_dir, self.results_dir]:
                if dir_path.exists():
                    for file_path in dir_path.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(self.base_dir)
                            zipf.write(file_path, arcname)
                            
            # 备份配置文件
            config_files = ["config.ini", "*.json"]
            for pattern in config_files:
                for file in self.base_dir.glob(pattern):
                    if file.is_file():
                        zipf.write(file, file.name)
                        
        file_size = os.path.getsize(backup_name) / 1024 / 1024
        print(f"备份完成: {backup_name} ({file_size:.2f} MB)")
        
    def check_integrity(self):
        """检查系统完整性"""
        print("检查系统完整性...")
        print("-" * 60)
        
        issues = []
        
        # 检查必要目录
        required_dirs = [
            self.data_dir,
            self.results_dir,
            self.logs_dir,
            self.cache_dir,
            self.base_dir / "resources"
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                issues.append(f"缺少目录: {dir_path}")
                
        # 检查主要文件
        required_files = [
            "tavr_fsi_gui.py",
            "requirements.txt",
            "config.ini"
        ]
        
        for file_name in required_files:
            if not (self.base_dir / file_name).exists():
                issues.append(f"缺少文件: {file_name}")
                
        # 检查Python模块
        try:
            import PyQt5
        except ImportError:
            issues.append("PyQt5未安装")
            
        try:
            import SimpleITK
        except ImportError:
            issues.append("SimpleITK未安装")
            
        try:
            import vtk
        except ImportError:
            issues.append("VTK未安装")
            
        # 报告结果
        if issues:
            print("发现以下问题:")
            for issue in issues:
                print(f"  ✗ {issue}")
            print("\n建议运行 setup.py 修复问题")
            return False
        else:
            print("✓ 系统完整性检查通过")
            return True
            
    def reset_settings(self):
        """重置系统设置"""
        print("重置系统设置...")
        
        # 备份当前设置
        config_file = self.base_dir / "config.ini"
        if config_file.exists():
            backup_file = self.base_dir / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ini"
            shutil.copy(config_file, backup_file)
            print(f"当前设置已备份到: {backup_file}")
            
        # 创建默认设置
        default_config = """# TAVR FSI Analysis System Configuration
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
        
        with open(config_file, 'w') as f:
            f.write(default_config)
            
        print("设置已重置为默认值")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TAVR分析系统实用工具')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 清理缓存命令
    clean_parser = subparsers.add_parser('clean', help='清理缓存和日志')
    clean_parser.add_argument('--cache-days', type=int, default=7,
                            help='清理多少天前的缓存（默认7天）')
    clean_parser.add_argument('--log-days', type=int, default=30,
                            help='清理多少天前的日志（默认30天）')
    
    # 导出命令
    export_parser = subparsers.add_parser('export', help='导出患者数据')
    export_parser.add_argument('patient_id', help='患者ID')
    export_parser.add_argument('-o', '--output', help='输出文件名')
    
    # 导入命令
    import_parser = subparsers.add_parser('import', help='导入患者数据')
    import_parser.add_argument('file', help='导入的zip文件')
    
    # 列出患者命令
    list_parser = subparsers.add_parser('list', help='列出所有患者')
    
    # 统计命令
    stats_parser = subparsers.add_parser('stats', help='显示系统统计')
    
    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='备份系统数据')
    backup_parser.add_argument('-o', '--output', help='备份文件名')
    
    # 检查命令
    check_parser = subparsers.add_parser('check', help='检查系统完整性')
    
    # 重置命令
    reset_parser = subparsers.add_parser('reset', help='重置系统设置')
    
    args = parser.parse_args()
    
    # 创建工具实例
    utils = TAVRUtilities()
    
    # 执行命令
    if args.command == 'clean':
        utils.clean_cache(args.cache_days)
        utils.clean_logs(args.log_days)
        
    elif args.command == 'export':
        utils.export_patient_data(args.patient_id, args.output)
        
    elif args.command == 'import':
        utils.import_patient_data(args.file)
        
    elif args.command == 'list':
        utils.list_patients()
        
    elif args.command == 'stats':
        utils.generate_statistics()
        
    elif args.command == 'backup':
        utils.backup_system(args.output)
        
    elif args.command == 'check':
        utils.check_integrity()
        
    elif args.command == 'reset':
        response = input("确定要重置设置吗？(y/n): ")
        if response.lower() == 'y':
            utils.reset_settings()
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()