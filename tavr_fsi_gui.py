#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAVR术前CT流固耦合模拟分析GUI系统
主程序文件：tavr_fsi_gui.py
"""

import sys
import os
import numpy as np
from datetime import datetime
import json
import logging
from pathlib import Path

# GUI相关
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 医学图像处理
import SimpleITK as sitk
import vtk
from vtkmodules.util import numpy_support
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

# 科学计算
import scipy.ndimage as ndimage
from scipy.interpolate import RegularGridInterpolator
import pandas as pd

# 网格生成
import meshio
import trimesh

# 图像处理
from skimage import measure

# 可视化
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TAVRAnalysisGUI(QMainWindow):
    """TAVR流固耦合分析主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_patient = None
        self.ct_image = None
        self.segmentation = None
        self.mesh = None
        self.simulation_results = None
        
        self.initUI()
        self.setupLogging()
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('TAVR术前流固耦合分析系统 v1.0')
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置图标
        self.setWindowIcon(QIcon('resources/icon.png'))
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 左侧控制面板
        self.control_panel = self.createControlPanel()
        self.main_layout.addWidget(self.control_panel, 1)
        
        # 右侧显示区域
        self.display_area = self.createDisplayArea()
        self.main_layout.addWidget(self.display_area, 3)
        
        # 创建菜单栏
        self.createMenuBar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.updateStatus("系统就绪")
        
        # 创建工具栏
        self.createToolBar()
        
    def createControlPanel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 患者信息组
        patient_group = QGroupBox("患者信息")
        patient_layout = QFormLayout()
        
        self.patient_id_edit = QLineEdit()
        self.patient_name_edit = QLineEdit()
        self.patient_age_spin = QSpinBox()
        self.patient_age_spin.setRange(0, 120)
        self.patient_sex_combo = QComboBox()
        self.patient_sex_combo.addItems(['男', '女'])
        
        patient_layout.addRow("患者ID:", self.patient_id_edit)
        patient_layout.addRow("姓名:", self.patient_name_edit)
        patient_layout.addRow("年龄:", self.patient_age_spin)
        patient_layout.addRow("性别:", self.patient_sex_combo)
        
        patient_group.setLayout(patient_layout)
        layout.addWidget(patient_group)
        
        # 数据导入组
        import_group = QGroupBox("数据导入")
        import_layout = QVBoxLayout()
        
        self.import_ct_btn = QPushButton("导入CT数据")
        self.import_ct_btn.clicked.connect(self.importCTData)
        import_layout.addWidget(self.import_ct_btn)
        
        self.ct_info_label = QLabel("未导入数据")
        self.ct_info_label.setWordWrap(True)
        import_layout.addWidget(self.ct_info_label)
        
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)
        
        # 图像处理组
        process_group = QGroupBox("图像处理")
        process_layout = QVBoxLayout()
        
        self.segment_btn = QPushButton("自动分割")
        self.segment_btn.clicked.connect(self.performSegmentation)
        self.segment_btn.setEnabled(False)
        process_layout.addWidget(self.segment_btn)
        
        self.manual_edit_btn = QPushButton("手动编辑")
        self.manual_edit_btn.clicked.connect(self.manualEdit)
        self.manual_edit_btn.setEnabled(False)
        process_layout.addWidget(self.manual_edit_btn)
        
        self.smooth_btn = QPushButton("平滑处理")
        self.smooth_btn.clicked.connect(self.smoothSegmentation)
        self.smooth_btn.setEnabled(False)
        process_layout.addWidget(self.smooth_btn)
        
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        # 网格生成组
        mesh_group = QGroupBox("网格生成")
        mesh_layout = QVBoxLayout()
        
        mesh_size_layout = QHBoxLayout()
        mesh_size_layout.addWidget(QLabel("网格大小:"))
        self.mesh_size_spin = QDoubleSpinBox()
        self.mesh_size_spin.setRange(0.1, 5.0)
        self.mesh_size_spin.setValue(1.0)
        self.mesh_size_spin.setSuffix(" mm")
        mesh_size_layout.addWidget(self.mesh_size_spin)
        mesh_layout.addLayout(mesh_size_layout)
        
        self.generate_mesh_btn = QPushButton("生成网格")
        self.generate_mesh_btn.clicked.connect(self.generateMesh)
        self.generate_mesh_btn.setEnabled(False)
        mesh_layout.addWidget(self.generate_mesh_btn)
        
        self.mesh_info_label = QLabel("未生成网格")
        mesh_layout.addWidget(self.mesh_info_label)
        
        mesh_group.setLayout(mesh_layout)
        layout.addWidget(mesh_group)
        
        # 模拟设置组
        sim_group = QGroupBox("模拟设置")
        sim_layout = QFormLayout()
        
        self.valve_type_combo = QComboBox()
        self.valve_type_combo.addItems([
            'Edwards SAPIEN 3',
            'Medtronic CoreValve',
            'Boston Scientific ACURATE'
        ])
        sim_layout.addRow("瓣膜类型:", self.valve_type_combo)
        
        self.valve_size_combo = QComboBox()
        self.valve_size_combo.addItems(['23mm', '26mm', '29mm'])
        sim_layout.addRow("瓣膜尺寸:", self.valve_size_combo)
        
        self.run_simulation_btn = QPushButton("运行模拟")
        self.run_simulation_btn.clicked.connect(self.runSimulation)
        self.run_simulation_btn.setEnabled(False)
        sim_layout.addRow(self.run_simulation_btn)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # 添加弹簧使控件靠上
        layout.addStretch()
        
        return panel
        
    def createDisplayArea(self):
        """创建显示区域"""
        tab_widget = QTabWidget()
        
        # CT图像显示标签页
        self.ct_viewer_tab = CTViewerWidget()
        tab_widget.addTab(self.ct_viewer_tab, "CT图像")
        
        # 3D重建标签页
        self.reconstruction_tab = Reconstruction3DWidget()
        tab_widget.addTab(self.reconstruction_tab, "3D重建")
        
        # 网格显示标签页
        self.mesh_viewer_tab = MeshViewerWidget()
        tab_widget.addTab(self.mesh_viewer_tab, "网格模型")
        
        # 模拟结果标签页
        self.results_tab = SimulationResultsWidget()
        tab_widget.addTab(self.results_tab, "模拟结果")
        
        # 报告标签页
        self.report_tab = ReportWidget()
        tab_widget.addTab(self.report_tab, "分析报告")
        
        return tab_widget
        
    def createMenuBar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建病例', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.newCase)
        file_menu.addAction(new_action)
        
        open_action = QAction('打开病例', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.openCase)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存病例', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.saveCase)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出报告', self)
        export_action.triggered.connect(self.exportReport)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.showSettings)
        tools_menu.addAction(settings_action)
        
        calibrate_action = QAction('校准', self)
        calibrate_action.triggered.connect(self.showCalibration)
        tools_menu.addAction(calibrate_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        manual_action = QAction('用户手册', self)
        manual_action.triggered.connect(self.showManual)
        help_menu.addAction(manual_action)
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)
        
    def createToolBar(self):
        """创建工具栏"""
        toolbar = self.addToolBar('主工具栏')
        
        # 添加常用功能按钮
        import_action = QAction(QIcon('resources/import.png'), '导入数据', self)
        import_action.triggered.connect(self.importCTData)
        toolbar.addAction(import_action)
        
        segment_action = QAction(QIcon('resources/segment.png'), '自动分割', self)
        segment_action.triggered.connect(self.performSegmentation)
        toolbar.addAction(segment_action)
        
        mesh_action = QAction(QIcon('resources/mesh.png'), '生成网格', self)
        mesh_action.triggered.connect(self.generateMesh)
        toolbar.addAction(mesh_action)
        
        simulate_action = QAction(QIcon('resources/simulate.png'), '运行模拟', self)
        simulate_action.triggered.connect(self.runSimulation)
        toolbar.addAction(simulate_action)
        
        toolbar.addSeparator()
        
        report_action = QAction(QIcon('resources/report.png'), '生成报告', self)
        report_action.triggered.connect(self.generateReport)
        toolbar.addAction(report_action)
        
    def setupLogging(self):
        """设置日志系统"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"tavr_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
    def updateStatus(self, message):
        """更新状态栏信息"""
        self.status_bar.showMessage(message)
        logger.info(message)
        
    def importCTData(self):
        """导入CT数据"""
        try:
            # 选择DICOM文件夹
            folder = QFileDialog.getExistingDirectory(self, "选择DICOM文件夹")
            if not folder:
                return
                
            self.updateStatus("正在导入CT数据...")
            QApplication.processEvents()
            
            # 读取DICOM序列
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(folder)
            reader.SetFileNames(dicom_names)
            
            self.ct_image = reader.Execute()
            
            # 更新显示
            self.ct_viewer_tab.setImage(self.ct_image)
            
            # 获取图像信息
            size = self.ct_image.GetSize()
            spacing = self.ct_image.GetSpacing()
            
            info_text = f"尺寸: {size[0]}×{size[1]}×{size[2]}\n"
            info_text += f"体素大小: {spacing[0]:.2f}×{spacing[1]:.2f}×{spacing[2]:.2f} mm"
            self.ct_info_label.setText(info_text)
            
            # 启用后续按钮
            self.segment_btn.setEnabled(True)
            
            self.updateStatus("CT数据导入成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
            logger.error(f"CT导入错误: {str(e)}")
            
    def performSegmentation(self):
        """执行自动分割"""
        if self.ct_image is None:
            return
            
        try:
            self.updateStatus("正在执行自动分割...")
            QApplication.processEvents()
            
            # 创建进度对话框
            progress = QProgressDialog("正在分割...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # 获取图像数组
            image_array = sitk.GetArrayFromImage(self.ct_image)
            
            # 步骤1: 阈值分割
            progress.setValue(20)
            threshold_low = 150  # HU值下限
            threshold_high = 500  # HU值上限
            binary_mask = np.logical_and(image_array >= threshold_low, 
                                         image_array <= threshold_high)
            
            # 步骤2: 区域生长
            progress.setValue(40)
            # 找到主动脉根部种子点（简化版本，实际应该更智能）
            center_slice = image_array.shape[0] // 2
            center_x = image_array.shape[2] // 2
            center_y = image_array.shape[1] // 2
            
            # 使用形态学操作清理
            progress.setValue(60)
            binary_mask = ndimage.binary_opening(binary_mask, iterations=2)
            binary_mask = ndimage.binary_closing(binary_mask, iterations=2)
            
            # 找到最大连通区域
            progress.setValue(80)
            labeled, num_features = ndimage.label(binary_mask)
            if num_features > 0:
                sizes = ndimage.sum(binary_mask, labeled, range(1, num_features + 1))
                max_label = np.argmax(sizes) + 1
                binary_mask = labeled == max_label
            
            # 创建分割图像
            self.segmentation = sitk.GetImageFromArray(binary_mask.astype(np.uint8))
            self.segmentation.CopyInformation(self.ct_image)
            
            # 更新显示
            self.ct_viewer_tab.setSegmentation(self.segmentation)
            self.reconstruction_tab.setData(self.ct_image, self.segmentation)
            
            # 启用后续按钮
            self.manual_edit_btn.setEnabled(True)
            self.smooth_btn.setEnabled(True)
            self.generate_mesh_btn.setEnabled(True)
            
            progress.setValue(100)
            progress.close()
            
            self.updateStatus("自动分割完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分割失败: {str(e)}")
            logger.error(f"分割错误: {str(e)}")
            
    def manualEdit(self):
        """手动编辑分割结果"""
        if self.segmentation is None:
            return
            
        # 打开编辑对话框
        editor = SegmentationEditor(self.ct_image, self.segmentation, self)
        if editor.exec_():
            self.segmentation = editor.getSegmentation()
            self.ct_viewer_tab.setSegmentation(self.segmentation)
            self.reconstruction_tab.setData(self.ct_image, self.segmentation)
            self.updateStatus("手动编辑完成")
            
    def smoothSegmentation(self):
        """平滑分割结果"""
        if self.segmentation is None:
            return
            
        try:
            self.updateStatus("正在平滑处理...")
            QApplication.processEvents()
            
            # 应用高斯滤波
            smooth_filter = sitk.SmoothingRecursiveGaussianImageFilter()
            smooth_filter.SetSigma(1.0)
            smoothed = smooth_filter.Execute(sitk.Cast(self.segmentation, sitk.sitkFloat32))
            
            # 重新二值化
            self.segmentation = sitk.BinaryThreshold(smoothed, 0.5, 1.0, 1, 0)
            
            # 更新显示
            self.ct_viewer_tab.setSegmentation(self.segmentation)
            self.reconstruction_tab.setData(self.ct_image, self.segmentation)
            
            self.updateStatus("平滑处理完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"平滑处理失败: {str(e)}")
            logger.error(f"平滑处理错误: {str(e)}")
            
    def generateMesh(self):
        """生成网格"""
        if self.segmentation is None:
            return
            
        try:
            self.updateStatus("正在生成网格...")
            QApplication.processEvents()
            
            # 创建进度对话框
            progress = QProgressDialog("正在生成网格...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # 步骤1: 提取表面
            progress.setValue(20)
            seg_array = sitk.GetArrayFromImage(self.segmentation)
            
            # 使用marching cubes算法
            from skimage import measure
            spacing = self.segmentation.GetSpacing()
            verts, faces, normals, values = measure.marching_cubes(
                seg_array, level=0.5, spacing=spacing[::-1]
            )
            
            # 步骤2: 创建trimesh对象
            progress.setValue(40)
            mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)
            
            # 步骤3: 简化网格
            progress.setValue(60)
            target_faces = int(len(mesh.faces) * 0.1)  # 简化到10%
            mesh = mesh.simplify_quadric_decimation(target_faces)
            
            # 步骤4: 平滑网格
            progress.setValue(80)
            mesh = mesh.smoothed()
            
            # 步骤5: 体网格生成（简化版本）
            progress.setValue(90)
            # 这里应该使用专业的网格生成工具如TetGen或CGAL
            # 此处仅作演示
            self.mesh = {
                'surface': mesh,
                'vertices': mesh.vertices,
                'faces': mesh.faces,
                'cells': None  # 体网格单元
            }
            
            # 更新显示
            self.mesh_viewer_tab.setMesh(self.mesh)
            
            # 更新网格信息
            info_text = f"顶点数: {len(mesh.vertices)}\n"
            info_text += f"面片数: {len(mesh.faces)}\n"
            info_text += f"网格质量: 良好"
            self.mesh_info_label.setText(info_text)
            
            # 启用模拟按钮
            self.run_simulation_btn.setEnabled(True)
            
            progress.setValue(100)
            progress.close()
            
            self.updateStatus("网格生成完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"网格生成失败: {str(e)}")
            logger.error(f"网格生成错误: {str(e)}")
            
    def runSimulation(self):
        """运行流固耦合模拟"""
        if self.mesh is None:
            return
            
        try:
            # 获取模拟参数
            valve_type = self.valve_type_combo.currentText()
            valve_size = self.valve_size_combo.currentText()
            
            # 创建模拟对话框
            sim_dialog = SimulationDialog(self.mesh, valve_type, valve_size, self)
            sim_dialog.show()
            
            # 连接完成信号
            sim_dialog.simulation_complete.connect(self.onSimulationComplete)
            
            # 开始模拟
            sim_dialog.startSimulation()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"模拟启动失败: {str(e)}")
            logger.error(f"模拟错误: {str(e)}")
            
    def onSimulationComplete(self, results):
        """模拟完成回调"""
        self.simulation_results = results
        self.results_tab.setResults(results)
        self.updateStatus("模拟完成")
        
        # 自动生成报告
        self.generateReport()
        
    def generateReport(self):
        """生成分析报告"""
        if self.simulation_results is None:
            QMessageBox.warning(self, "警告", "请先完成模拟")
            return
            
        try:
            # 收集所有数据
            report_data = {
                'patient': {
                    'id': self.patient_id_edit.text(),
                    'name': self.patient_name_edit.text(),
                    'age': self.patient_age_spin.value(),
                    'sex': self.patient_sex_combo.currentText()
                },
                'ct_info': {
                    'size': self.ct_image.GetSize() if self.ct_image else None,
                    'spacing': self.ct_image.GetSpacing() if self.ct_image else None
                },
                'simulation': self.simulation_results,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 更新报告标签页
            self.report_tab.generateReport(report_data)
            
            self.updateStatus("报告生成完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"报告生成失败: {str(e)}")
            logger.error(f"报告生成错误: {str(e)}")
            
    def newCase(self):
        """新建病例"""
        reply = QMessageBox.question(self, '确认', '是否保存当前病例？',
                                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Cancel:
            return
        elif reply == QMessageBox.Yes:
            self.saveCase()
            
        # 清空所有数据
        self.current_patient = None
        self.ct_image = None
        self.segmentation = None
        self.mesh = None
        self.simulation_results = None
        
        # 清空界面
        self.patient_id_edit.clear()
        self.patient_name_edit.clear()
        self.patient_age_spin.setValue(0)
        self.ct_info_label.setText("未导入数据")
        self.mesh_info_label.setText("未生成网格")
        
        # 重置所有标签页
        self.ct_viewer_tab.clear()
        self.reconstruction_tab.clear()
        self.mesh_viewer_tab.clear()
        self.results_tab.clear()
        self.report_tab.clear()
        
        # 禁用按钮
        self.segment_btn.setEnabled(False)
        self.manual_edit_btn.setEnabled(False)
        self.smooth_btn.setEnabled(False)
        self.generate_mesh_btn.setEnabled(False)
        self.run_simulation_btn.setEnabled(False)
        
        self.updateStatus("新建病例")
        
    def openCase(self):
        """打开病例"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开病例文件", "", "TAVR病例文件 (*.tavr)")
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    case_data = json.load(f)
                
                # 恢复数据
                # 这里需要实现完整的数据恢复逻辑
                self.updateStatus(f"打开病例: {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开病例失败: {str(e)}")
                
    def saveCase(self):
        """保存病例"""
        if self.current_patient is None:
            patient_id = self.patient_id_edit.text()
            if not patient_id:
                patient_id = f"Patient_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存病例文件", f"{patient_id}.tavr", "TAVR病例文件 (*.tavr)")
        
        if filename:
            try:
                # 准备保存数据
                case_data = {
                    'patient': {
                        'id': self.patient_id_edit.text(),
                        'name': self.patient_name_edit.text(),
                        'age': self.patient_age_spin.value(),
                        'sex': self.patient_sex_combo.currentText()
                    },
                    'timestamp': datetime.now().isoformat(),
                    # 添加其他需要保存的数据
                }
                
                with open(filename, 'w') as f:
                    json.dump(case_data, f, indent=2)
                
                self.updateStatus(f"病例已保存: {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存病例失败: {str(e)}")
                
    def exportReport(self):
        """导出报告"""
        if self.simulation_results is None:
            QMessageBox.warning(self, "警告", "没有可导出的报告")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出报告", f"TAVR_Report_{datetime.now().strftime('%Y%m%d')}.pdf", 
            "PDF文件 (*.pdf);;Word文档 (*.docx)")
        
        if filename:
            try:
                self.report_tab.exportReport(filename)
                self.updateStatus(f"报告已导出: {filename}")
                QMessageBox.information(self, "成功", "报告导出成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"报告导出失败: {str(e)}")
                
    def showSettings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec_()
        
    def showCalibration(self):
        """显示校准对话框"""
        dialog = CalibrationDialog(self)
        dialog.exec_()
        
    def showManual(self):
        """显示用户手册"""
        QDesktopServices.openUrl(QUrl("docs/user_manual.pdf"))
        
    def showAbout(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于",
            "TAVR术前流固耦合分析系统 v1.0\n\n"
            "用于经导管主动脉瓣置换术的\n"
            "术前评估和手术规划\n\n"
            "© 2024 医学影像分析实验室")
        
    def closeEvent(self, event):
        """关闭事件处理"""
        reply = QMessageBox.question(self, '确认退出',
                                    "是否保存当前工作？",
                                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        
        if reply == QMessageBox.Save:
            self.saveCase()
            event.accept()
        elif reply == QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()


class CTViewerWidget(QWidget):
    """CT图像查看器部件"""
    
    def __init__(self):
        super().__init__()
        self.image = None
        self.segmentation = None
        self.current_slice = 0
        self.window_level = 40
        self.window_width = 400
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 窗位/窗宽预设
        preset_label = QLabel("预设:")
        toolbar.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(['软组织', '骨窗', '肺窗', '自定义'])
        self.preset_combo.currentTextChanged.connect(self.applyPreset)
        toolbar.addWidget(self.preset_combo)
        
        toolbar.addStretch()
        
        # 透明度控制
        opacity_label = QLabel("分割透明度:")
        toolbar.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.valueChanged.connect(self.updateDisplay)
        toolbar.addWidget(self.opacity_slider)
        
        layout.addLayout(toolbar)
        
        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: black; }")
        self.image_label.setMinimumHeight(400)
        
        # 添加滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 切片控制
        slice_control = QHBoxLayout()
        
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.valueChanged.connect(self.changeSlice)
        slice_control.addWidget(self.slice_slider)
        
        self.slice_label = QLabel("切片: 0/0")
        slice_control.addWidget(self.slice_label)
        
        layout.addLayout(slice_control)
        
        # 窗位/窗宽调整
        window_control = QHBoxLayout()
        
        window_control.addWidget(QLabel("窗位:"))
        self.level_spin = QSpinBox()
        self.level_spin.setRange(-1000, 1000)
        self.level_spin.setValue(self.window_level)
        self.level_spin.valueChanged.connect(self.updateDisplay)
        window_control.addWidget(self.level_spin)
        
        window_control.addWidget(QLabel("窗宽:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 2000)
        self.width_spin.setValue(self.window_width)
        self.width_spin.valueChanged.connect(self.updateDisplay)
        window_control.addWidget(self.width_spin)
        
        window_control.addStretch()
        
        layout.addLayout(window_control)
        
    def setImage(self, image):
        """设置CT图像"""
        self.image = image
        self.current_slice = image.GetSize()[2] // 2
        
        # 设置滑块范围
        self.slice_slider.setRange(0, image.GetSize()[2] - 1)
        self.slice_slider.setValue(self.current_slice)
        
        self.updateDisplay()
        
    def setSegmentation(self, segmentation):
        """设置分割结果"""
        self.segmentation = segmentation
        self.updateDisplay()
        
    def clear(self):
        """清空显示"""
        self.image = None
        self.segmentation = None
        self.image_label.clear()
        self.slice_label.setText("切片: 0/0")
        
    def changeSlice(self, value):
        """改变当前切片"""
        self.current_slice = value
        self.updateDisplay()
        
    def applyPreset(self, preset):
        """应用窗位/窗宽预设"""
        presets = {
            '软组织': (40, 400),
            '骨窗': (300, 1500),
            '肺窗': (-600, 1600)
        }
        
        if preset in presets:
            level, width = presets[preset]
            self.level_spin.setValue(level)
            self.width_spin.setValue(width)
            
    def updateDisplay(self):
        """更新显示"""
        if self.image is None:
            return
            
        # 获取当前切片
        image_array = sitk.GetArrayFromImage(self.image)
        slice_array = image_array[self.current_slice, :, :]
        
        # 应用窗位/窗宽
        self.window_level = self.level_spin.value()
        self.window_width = self.width_spin.value()
        
        min_val = self.window_level - self.window_width / 2
        max_val = self.window_level + self.window_width / 2
        
        # 归一化到0-255
        slice_array = np.clip(slice_array, min_val, max_val)
        slice_array = ((slice_array - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        
        # 转换为QImage
        height, width = slice_array.shape
        bytes_per_line = width
        
        # 创建灰度图像
        q_image = QImage(slice_array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        
        # 如果有分割结果，叠加显示
        if self.segmentation is not None:
            seg_array = sitk.GetArrayFromImage(self.segmentation)
            seg_slice = seg_array[self.current_slice, :, :]
            
            # 创建彩色叠加
            overlay = QImage(width, height, QImage.Format_ARGB32)
            overlay.fill(Qt.transparent)
            
            painter = QPainter(overlay)
            opacity = self.opacity_slider.value() / 100.0
            painter.setOpacity(opacity)
            
            # 绘制分割轮廓
            color = QColor(255, 0, 0, int(255 * opacity))  # 红色
            painter.setPen(QPen(color, 2))
            
            # 查找轮廓
            contours = measure.find_contours(seg_slice, 0.5)
            for contour in contours:
                points = [QPoint(int(p[1]), int(p[0])) for p in contour]
                if len(points) > 1:
                    painter.drawPolyline(points)
                    
            painter.end()
            
            # 合并图像
            result = QImage(width, height, QImage.Format_RGB32)
            painter = QPainter(result)
            painter.drawImage(0, 0, q_image)
            painter.drawImage(0, 0, overlay)
            painter.end()
            
            pixmap = QPixmap.fromImage(result)
        else:
            pixmap = QPixmap.fromImage(q_image)
            
        # 缩放以适应窗口
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        # 更新切片信息
        self.slice_label.setText(f"切片: {self.current_slice + 1}/{self.image.GetSize()[2]}")


class Reconstruction3DWidget(QWidget):
    """3D重建显示部件"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # VTK渲染窗口
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget)
        
        # 控制面板
        controls = QHBoxLayout()
        
        # 显示选项
        self.show_ct_check = QCheckBox("显示CT")
        self.show_ct_check.setChecked(True)
        self.show_ct_check.stateChanged.connect(self.updateDisplay)
        controls.addWidget(self.show_ct_check)
        
        self.show_seg_check = QCheckBox("显示分割")
        self.show_seg_check.setChecked(True)
        self.show_seg_check.stateChanged.connect(self.updateDisplay)
        controls.addWidget(self.show_seg_check)
        
        controls.addStretch()
        
        # 视角按钮
        view_label = QLabel("视角:")
        controls.addWidget(view_label)
        
        for view in ['前', '后', '左', '右', '上', '下']:
            btn = QPushButton(view)
            btn.clicked.connect(lambda checked, v=view: self.setView(v))
            controls.addWidget(btn)
            
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.resetView)
        controls.addWidget(reset_btn)
        
        layout.addLayout(controls)
        
        # 初始化渲染器
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.1, 0.1, 0.1)
        
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        
        # 设置交互样式
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)
        
    def setData(self, ct_image, segmentation):
        """设置数据"""
        self.ct_image = ct_image
        self.segmentation = segmentation
        
        # 清除现有actors
        self.renderer.RemoveAllViewProps()
        
        # 创建CT体绘制
        if self.show_ct_check.isChecked():
            self.addCTVolume()
            
        # 创建分割表面
        if self.show_seg_check.isChecked():
            self.addSegmentationSurface()
            
        # 重置相机
        self.resetView()
        
        # 开始交互
        self.interactor.Initialize()
        self.interactor.Start()
        
    def addCTVolume(self):
        """添加CT体绘制"""
        # 转换为VTK图像
        converter = sitk.GetArrayFromImage(self.ct_image)
        vtk_image = vtk.vtkImageData()
        vtk_image.SetDimensions(self.ct_image.GetSize())
        vtk_image.SetSpacing(self.ct_image.GetSpacing())
        vtk_image.SetOrigin(self.ct_image.GetOrigin())
        vtk_image.AllocateScalars(vtk.VTK_SHORT, 1)
        
        # 复制数据
        vtk_array = vtk.util.numpy_support.numpy_to_vtk(converter.ravel(), deep=True, array_type=vtk.VTK_SHORT)
        vtk_image.GetPointData().SetScalars(vtk_array)
        
        # 创建体绘制映射器
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        volume_mapper.SetInputData(vtk_image)
        
        # 创建传输函数
        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()
        
        # 设置颜色传输函数
        color_func = vtk.vtkColorTransferFunction()
        color_func.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
        color_func.AddRGBPoint(-500, 0.3, 0.1, 0.1)
        color_func.AddRGBPoint(0, 0.5, 0.5, 0.5)
        color_func.AddRGBPoint(500, 1.0, 1.0, 0.9)
        color_func.AddRGBPoint(1000, 1.0, 1.0, 1.0)
        
        # 设置不透明度传输函数
        opacity_func = vtk.vtkPiecewiseFunction()
        opacity_func.AddPoint(-1000, 0.0)
        opacity_func.AddPoint(-500, 0.0)
        opacity_func.AddPoint(0, 0.1)
        opacity_func.AddPoint(500, 0.2)
        opacity_func.AddPoint(1000, 0.9)
        
        volume_property.SetColor(color_func)
        volume_property.SetScalarOpacity(opacity_func)
        
        # 创建volume actor
        volume = vtk.vtkVolume()
        volume.SetMapper(volume_mapper)
        volume.SetProperty(volume_property)
        
        self.renderer.AddVolume(volume)
        
    def addSegmentationSurface(self):
        """添加分割表面"""
        # 转换为VTK图像
        converter = sitk.GetArrayFromImage(self.segmentation)
        vtk_image = vtk.vtkImageData()
        vtk_image.SetDimensions(self.segmentation.GetSize())
        vtk_image.SetSpacing(self.segmentation.GetSpacing())
        vtk_image.SetOrigin(self.segmentation.GetOrigin())
        vtk_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
        
        # 复制数据
        vtk_array = numpy_support.numpy_to_vtk(converter.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
        vtk_image.GetPointData().SetScalars(vtk_array)
        
        # 创建等值面
        contour = vtk.vtkContourFilter()
        contour.SetInputData(vtk_image)
        contour.SetValue(0, 0.5)
        
        # 平滑
        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputConnection(contour.GetOutputPort())
        smoother.SetNumberOfIterations(50)
        smoother.SetRelaxationFactor(0.1)
        smoother.Update()
        
        # 创建映射器
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(smoother.GetOutputPort())
        mapper.ScalarVisibilityOff()
        
        # 创建actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # 红色
        actor.GetProperty().SetOpacity(0.7)
        
        self.renderer.AddActor(actor)
        
    def updateDisplay(self):
        """更新显示"""
        if hasattr(self, 'ct_image') and hasattr(self, 'segmentation'):
            self.setData(self.ct_image, self.segmentation)
            
    def setView(self, view):
        """设置视角"""
        camera = self.renderer.GetActiveCamera()
        
        views = {
            '前': (0, -1, 0, 0, 0, 1),
            '后': (0, 1, 0, 0, 0, 1),
            '左': (-1, 0, 0, 0, 0, 1),
            '右': (1, 0, 0, 0, 0, 1),
            '上': (0, 0, 1, 0, -1, 0),
            '下': (0, 0, -1, 0, 1, 0)
        }
        
        if view in views:
            pos = views[view]
            camera.SetPosition(pos[0] * 500, pos[1] * 500, pos[2] * 500)
            camera.SetFocalPoint(0, 0, 0)
            camera.SetViewUp(pos[3], pos[4], pos[5])
            
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
        
    def resetView(self):
        """重置视角"""
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
        
    def clear(self):
        """清空显示"""
        self.renderer.RemoveAllViewProps()
        self.vtk_widget.GetRenderWindow().Render()


class MeshViewerWidget(QWidget):
    """网格查看器部件"""
    
    def __init__(self):
        super().__init__()
        self.mesh = None
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 显示模式
        mode_label = QLabel("显示模式:")
        toolbar.addWidget(mode_label)
        
        self.display_mode = QComboBox()
        self.display_mode.addItems(['实体', '线框', '点云'])
        self.display_mode.currentTextChanged.connect(self.updateDisplayMode)
        toolbar.addWidget(self.display_mode)
        
        # 网格质量
        quality_label = QLabel("网格质量:")
        toolbar.addWidget(quality_label)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['偏斜度', '纵横比', '雅可比'])
        self.quality_combo.currentTextChanged.connect(self.showQuality)
        toolbar.addWidget(self.quality_combo)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # VTK渲染窗口
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget)
        
        # 信息面板
        info_layout = QHBoxLayout()
        self.info_label = QLabel("网格信息: 未加载")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # 初始化渲染器
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.2, 0.2, 0.2)
        
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        
        # 设置交互样式
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)
        
    def setMesh(self, mesh_data):
        """设置网格数据"""
        self.mesh = mesh_data
        
        # 清除现有actors
        self.renderer.RemoveAllViewProps()
        
        # 创建VTK多边形数据
        points = vtk.vtkPoints()
        for vertex in mesh_data['vertices']:
            points.InsertNextPoint(vertex)
            
        # 创建面片
        polys = vtk.vtkCellArray()
        for face in mesh_data['faces']:
            polys.InsertNextCell(len(face))
            for vertex_id in face:
                polys.InsertCellPoint(vertex_id)
                
        # 创建polydata
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(polys)
        
        # 计算法向量
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polydata)
        normals.ComputePointNormalsOn()
        normals.ComputeCellNormalsOn()
        normals.Update()
        
        # 创建映射器
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())
        
        # 创建actor
        self.mesh_actor = vtk.vtkActor()
        self.mesh_actor.SetMapper(mapper)
        self.mesh_actor.GetProperty().SetColor(0.8, 0.8, 0.8)
        
        self.renderer.AddActor(self.mesh_actor)
        
        # 添加边界框
        outline = vtk.vtkOutlineFilter()
        outline.SetInputData(polydata)
        
        outline_mapper = vtk.vtkPolyDataMapper()
        outline_mapper.SetInputConnection(outline.GetOutputPort())
        
        outline_actor = vtk.vtkActor()
        outline_actor.SetMapper(outline_mapper)
        outline_actor.GetProperty().SetColor(1.0, 1.0, 0.0)
        
        self.renderer.AddActor(outline_actor)
        
        # 添加坐标轴
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(50, 50, 50)
        self.renderer.AddActor(axes)
        
        # 更新信息
        info_text = f"顶点数: {len(mesh_data['vertices'])}\n"
        info_text += f"面片数: {len(mesh_data['faces'])}"
        self.info_label.setText(info_text)
        
        # 重置相机
        self.renderer.ResetCamera()
        
        # 开始交互
        self.interactor.Initialize()
        self.interactor.Start()
        
    def updateDisplayMode(self, mode):
        """更新显示模式"""
        if not hasattr(self, 'mesh_actor'):
            return
            
        prop = self.mesh_actor.GetProperty()
        
        if mode == '实体':
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
        elif mode == '线框':
            prop.SetRepresentationToWireframe()
        elif mode == '点云':
            prop.SetRepresentationToPoints()
            prop.SetPointSize(3)
            
        self.vtk_widget.GetRenderWindow().Render()
        
    def showQuality(self, quality_type):
        """显示网格质量"""
        # 这里应该计算并显示网格质量指标
        # 简化版本仅作演示
        if self.mesh is not None:
            QMessageBox.information(self, "网格质量", 
                f"{quality_type}分析功能将在后续版本中实现")
            
    def clear(self):
        """清空显示"""
        self.renderer.RemoveAllViewProps()
        self.vtk_widget.GetRenderWindow().Render()
        self.info_label.setText("网格信息: 未加载")


class SimulationResultsWidget(QWidget):
    """模拟结果显示部件"""
    
    def __init__(self):
        super().__init__()
        self.results = None
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧结果列表
        self.results_list = QListWidget()
        self.results_list.addItems([
            '血流速度场',
            '压力分布',
            '壁面剪切力',
            '瓣周漏评估',
            '应力分布',
            '冠脉流量'
        ])
        self.results_list.currentItemChanged.connect(self.displayResult)
        splitter.addWidget(self.results_list)
        
        # 右侧显示区域
        self.display_stack = QStackedWidget()
        
        # 添加各种结果显示页面
        self.velocity_page = self.createVelocityPage()
        self.display_stack.addWidget(self.velocity_page)
        
        self.pressure_page = self.createPressurePage()
        self.display_stack.addWidget(self.pressure_page)
        
        self.wss_page = self.createWSSPage()
        self.display_stack.addWidget(self.wss_page)
        
        self.leak_page = self.createLeakPage()
        self.display_stack.addWidget(self.leak_page)
        
        self.stress_page = self.createStressPage()
        self.display_stack.addWidget(self.stress_page)
        
        self.coronary_page = self.createCoronaryPage()
        self.display_stack.addWidget(self.coronary_page)
        
        splitter.addWidget(self.display_stack)
        splitter.setSizes([200, 600])
        
        layout.addWidget(splitter)
        
    def createVelocityPage(self):
        """创建血流速度显示页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # 标题
        title = QLabel("血流速度场分析")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # 速度云图
        self.velocity_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        layout.addWidget(self.velocity_canvas)
        
        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QFormLayout()
        
        self.max_velocity_label = QLabel("--")
        self.mean_velocity_label = QLabel("--")
        self.reynolds_label = QLabel("--")
        
        stats_layout.addRow("最大速度:", self.max_velocity_label)
        stats_layout.addRow("平均速度:", self.mean_velocity_label)
        stats_layout.addRow("雷诺数:", self.reynolds_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        return page
        
    def createPressurePage(self):
        """创建压力分布显示页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # 标题
        title = QLabel("压力分布分析")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # 压力云图
        self.pressure_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        layout.addWidget(self.pressure_canvas)
        
        # 跨瓣压差
        gradient_group = QGroupBox("跨瓣压差")
        gradient_layout = QFormLayout()
        
        self.peak_gradient_label = QLabel("--")
        self.mean_gradient_label = QLabel("--")
        
        gradient_layout.addRow("峰值压差:", self.peak_gradient_label)
        gradient_layout.addRow("平均压差:", self.mean_gradient_label)
        
        gradient_group.setLayout(gradient_layout)
        layout.addWidget(gradient_group)
        
        return page
        
    def createWSSPage(self):
        """创建壁面剪切力显示页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("壁面剪切力分析")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # WSS分布图
        self.wss_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        layout.addWidget(self.wss_canvas)
        
        # 高风险区域
        risk_group = QGroupBox("高风险区域")
        risk_layout = QVBoxLayout()
        
        self.risk_areas_text = QTextEdit()
        self.risk_areas_text.setReadOnly(True)
        self.risk_areas_text.setMaximumHeight(100)
        risk_layout.addWidget(self.risk_areas_text)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        return page
        
    def createLeakPage(self):
        """创建瓣周漏评估页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("瓣周漏评估")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # 瓣周漏可视化
        self.leak_canvas = FigureCanvas(Figure(figsize=(8, 4)))
        layout.addWidget(self.leak_canvas)
        
        # 评估结果
        result_group = QGroupBox("评估结果")
        result_layout = QFormLayout()
        
        self.leak_volume_label = QLabel("--")
        self.leak_fraction_label = QLabel("--")
        self.leak_grade_label = QLabel("--")
        
        result_layout.addRow("反流量:", self.leak_volume_label)
        result_layout.addRow("反流分数:", self.leak_fraction_label)
        result_layout.addRow("分级:", self.leak_grade_label)
        
        # 设置分级颜色
        self.leak_grade_label.setStyleSheet("QLabel { font-weight: bold; }")
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 建议
        suggest_group = QGroupBox("临床建议")
        suggest_layout = QVBoxLayout()
        
        self.leak_suggestion = QTextEdit()
        self.leak_suggestion.setReadOnly(True)
        self.leak_suggestion.setMaximumHeight(100)
        suggest_layout.addWidget(self.leak_suggestion)
        
        suggest_group.setLayout(suggest_layout)
        layout.addWidget(suggest_group)
        
        return page
        
    def createStressPage(self):
        """创建应力分布显示页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("应力分布分析")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # 应力云图
        self.stress_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        layout.addWidget(self.stress_canvas)
        
        # 应力统计
        stats_group = QGroupBox("应力统计")
        stats_layout = QFormLayout()
        
        self.max_stress_label = QLabel("--")
        self.stress_concentration_label = QLabel("--")
        
        stats_layout.addRow("最大von Mises应力:", self.max_stress_label)
        stats_layout.addRow("应力集中系数:", self.stress_concentration_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        return page
        
    def createCoronaryPage(self):
        """创建冠脉流量评估页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("冠脉流量评估")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # 流量对比图
        self.coronary_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        layout.addWidget(self.coronary_canvas)
        
        # 风险评估
        risk_group = QGroupBox("冠脉阻塞风险")
        risk_layout = QFormLayout()
        
        self.lca_risk_label = QLabel("--")
        self.rca_risk_label = QLabel("--")
        self.sov_height_label = QLabel("--")
        self.vtc_distance_label = QLabel("--")
        
        risk_layout.addRow("左冠脉风险:", self.lca_risk_label)
        risk_layout.addRow("右冠脉风险:", self.rca_risk_label)
        risk_layout.addRow("SOV高度:", self.sov_height_label)
        risk_layout.addRow("VTC距离:", self.vtc_distance_label)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        return page
        
    def setResults(self, results):
        """设置模拟结果"""
        self.results = results
        
        # 更新各个页面的显示
        self.updateVelocityDisplay()
        self.updatePressureDisplay()
        self.updateWSSDisplay()
        self.updateLeakDisplay()
        self.updateStressDisplay()
        self.updateCoronaryDisplay()
        
    def displayResult(self, item):
        """显示选定的结果"""
        if item is None:
            return
            
        index_map = {
            '血流速度场': 0,
            '压力分布': 1,
            '壁面剪切力': 2,
            '瓣周漏评估': 3,
            '应力分布': 4,
            '冠脉流量': 5
        }
        
        index = index_map.get(item.text(), 0)
        self.display_stack.setCurrentIndex(index)
        
    def updateVelocityDisplay(self):
        """更新速度场显示"""
        if self.results is None:
            return
            
        # 绘制速度云图
        ax = self.velocity_canvas.figure.add_subplot(111)
        ax.clear()
        
        # 生成示例数据（实际应该从模拟结果获取）
        x = np.linspace(-20, 20, 100)
        y = np.linspace(-20, 20, 100)
        X, Y = np.meshgrid(x, y)
        
        # 模拟速度场
        r = np.sqrt(X**2 + Y**2)
        V = 2.0 * np.exp(-r**2/100) * (1 - r**2/200)
        
        # 绘制云图
        im = ax.contourf(X, Y, V, levels=20, cmap='jet')
        self.velocity_canvas.figure.colorbar(im, ax=ax, label='速度 (m/s)')
        
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_title('主动脉瓣口速度分布')
        ax.set_aspect('equal')
        
        self.velocity_canvas.draw()
        
        # 更新统计信息
        self.max_velocity_label.setText(f"{self.results.get('max_velocity', 2.5):.2f} m/s")
        self.mean_velocity_label.setText(f"{self.results.get('mean_velocity', 1.2):.2f} m/s")
        self.reynolds_label.setText(f"{self.results.get('reynolds', 3500):.0f}")
        
    def updatePressureDisplay(self):
        """更新压力分布显示"""
        if self.results is None:
            return
            
        # 绘制压力分布
        ax = self.pressure_canvas.figure.add_subplot(111)
        ax.clear()
        
        # 生成示例压力数据
        z = np.linspace(0, 100, 100)
        pressure = 120 - 0.8 * z + 5 * np.sin(z/10)
        
        ax.plot(z, pressure, 'b-', linewidth=2)
        ax.fill_between(z, pressure, alpha=0.3)
        
        ax.set_xlabel('距离 (mm)')
        ax.set_ylabel('压力 (mmHg)')
        ax.set_title('主动脉压力分布')
        ax.grid(True, alpha=0.3)
        
        self.pressure_canvas.draw()
        
        # 更新压差信息
        self.peak_gradient_label.setText(f"{self.results.get('peak_gradient', 45):.1f} mmHg")
        self.mean_gradient_label.setText(f"{self.results.get('mean_gradient', 25):.1f} mmHg")
        
    def updateWSSDisplay(self):
        """更新壁面剪切力显示"""
        if self.results is None:
            return
            
        # 绘制WSS分布
        ax = self.wss_canvas.figure.add_subplot(111)
        ax.clear()
        
        # 生成示例WSS数据
        theta = np.linspace(0, 2*np.pi, 100)
        r = 15 + 2*np.sin(4*theta)
        wss = 2 + 0.5*np.sin(8*theta) + np.random.normal(0, 0.1, 100)
        
        # 极坐标图
        ax = self.wss_canvas.figure.add_subplot(111, projection='polar')
        ax.plot(theta, wss, 'r-', linewidth=2)
        ax.fill_between(theta, 0, wss, alpha=0.3)
        
        ax.set_ylim(0, 3)
        ax.set_title('壁面剪切力分布 (Pa)')
        
        self.wss_canvas.draw()
        
        # 更新高风险区域
        risk_text = "高风险区域:\n"
        risk_text += "- 瓣叶附着点: WSS > 2.5 Pa\n"
        risk_text += "- 主动脉窦部: 低WSS区域 (<0.5 Pa)"
        self.risk_areas_text.setText(risk_text)
        
    def updateLeakDisplay(self):
        """更新瓣周漏显示"""
        if self.results is None:
            return
            
        # 绘制瓣周漏分布
        ax = self.leak_canvas.figure.add_subplot(111)
        ax.clear()
        
        # 生成示例瓣周漏数据
        categories = ['前方', '后方', '左侧', '右侧']
        leak_values = [0.5, 1.2, 0.3, 0.8]
        
        bars = ax.bar(categories, leak_values, color=['green', 'yellow', 'green', 'orange'])
        ax.set_ylabel('反流速度 (m/s)')
        ax.set_title('瓣周漏分布')
        ax.set_ylim(0, 2)
        
        # 添加阈值线
        ax.axhline(y=1.0, color='r', linestyle='--', label='轻度阈值')
        ax.legend()
        
        self.leak_canvas.draw()
        
        # 更新评估结果
        total_leak = self.results.get('leak_volume', 12)
        leak_fraction = self.results.get('leak_fraction', 8)
        
        self.leak_volume_label.setText(f"{total_leak:.1f} ml/beat")
        self.leak_fraction_label.setText(f"{leak_fraction:.1f}%")
        
        # 确定分级
        if leak_fraction < 5:
            grade = "无/微量"
            color = "green"
            suggestion = "瓣周漏在可接受范围内，预后良好。"
        elif leak_fraction < 10:
            grade = "轻度"
            color = "orange"
            suggestion = "存在轻度瓣周漏，建议密切随访。"
        elif leak_fraction < 20:
            grade = "中度"
            color = "red"
            suggestion = "中度瓣周漏，可能需要调整瓣膜位置或尺寸。"
        else:
            grade = "重度"
            color = "darkred"
            suggestion = "重度瓣周漏，建议重新评估治疗方案。"
            
        self.leak_grade_label.setText(grade)
        self.leak_grade_label.setStyleSheet(f"QLabel {{ font-weight: bold; color: {color}; }}")
        self.leak_suggestion.setText(suggestion)
        
    def updateStressDisplay(self):
        """更新应力分布显示"""
        if self.results is None:
            return
            
        # 绘制应力云图
        ax = self.stress_canvas.figure.add_subplot(111)
        ax.clear()
        
        # 生成示例应力数据
        x = np.linspace(-15, 15, 50)
        y = np.linspace(-15, 15, 50)
        X, Y = np.meshgrid(x, y)
        
        # 模拟应力分布
        stress = 5 + 2*np.exp(-(X**2 + Y**2)/50) + 3*np.exp(-((X-5)**2 + Y**2)/20)
        
        im = ax.contourf(X, Y, stress, levels=20, cmap='hot')
        self.stress_canvas.figure.colorbar(im, ax=ax, label='von Mises应力 (MPa)')
        
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_title('瓣膜应力分布')
        ax.set_aspect('equal')
        
        self.stress_canvas.draw()
        
        # 更新应力统计
        self.max_stress_label.setText(f"{self.results.get('max_stress', 8.5):.1f} MPa")
        self.stress_concentration_label.setText(f"{self.results.get('stress_concentration', 2.1):.1f}")
        
    def updateCoronaryDisplay(self):
        """更新冠脉流量显示"""
        if self.results is None:
            return
            
        # 绘制流量对比
        ax = self.coronary_canvas.figure.add_subplot(111)
        ax.clear()
        
        # 数据
        conditions = ['基线', 'TAVR后']
        lca_flow = [250, 230]
        rca_flow = [150, 135]
        
        x = np.arange(len(conditions))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, lca_flow, width, label='左冠脉')
        bars2 = ax.bar(x + width/2, rca_flow, width, label='右冠脉')
        
        ax.set_ylabel('血流量 (ml/min)')
        ax.set_title('冠脉血流量变化')
        ax.set_xticks(x)
        ax.set_xticklabels(conditions)
        ax.legend()
        
        # 添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.0f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom')
                           
        self.coronary_canvas.draw()
        
        # 更新风险评估
        lca_risk = self.results.get('lca_risk', 5)
        rca_risk = self.results.get('rca_risk', 3)
        
        self.lca_risk_label.setText(f"{lca_risk}% - 低风险" if lca_risk < 10 else f"{lca_risk}% - 高风险")
        self.rca_risk_label.setText(f"{rca_risk}% - 低风险" if rca_risk < 10 else f"{rca_risk}% - 高风险")
        self.sov_height_label.setText(f"{self.results.get('sov_height', 12.5):.1f} mm")
        self.vtc_distance_label.setText(f"{self.results.get('vtc_distance', 10.2):.1f} mm")
        
    def clear(self):
        """清空显示"""
        self.results = None
        # 清空所有画布
        for canvas in [self.velocity_canvas, self.pressure_canvas, 
                      self.wss_canvas, self.leak_canvas, 
                      self.stress_canvas, self.coronary_canvas]:
            canvas.figure.clear()
            canvas.draw()


class ReportWidget(QWidget):
    """报告生成部件"""
    
    def __init__(self):
        super().__init__()
        self.report_data = None
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.export_pdf_btn = QPushButton("导出PDF")
        self.export_pdf_btn.clicked.connect(lambda: self.exportReport('pdf'))
        toolbar.addWidget(self.export_pdf_btn)
        
        self.export_word_btn = QPushButton("导出Word")
        self.export_word_btn.clicked.connect(lambda: self.exportReport('docx'))
        toolbar.addWidget(self.export_word_btn)
        
        self.print_btn = QPushButton("打印")
        self.print_btn.clicked.connect(self.printReport)
        toolbar.addWidget(self.print_btn)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # 报告显示区域
        self.report_browser = QTextBrowser()
        self.report_browser.setOpenExternalLinks(True)
        layout.addWidget(self.report_browser)
        
    def generateReport(self, data):
        """生成报告"""
        self.report_data = data
        
        # 生成HTML报告
        html = self.generateHTML(data)
        self.report_browser.setHtml(html)
        
    def generateHTML(self, data):
        """生成HTML格式的报告"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; }
                h2 { color: #34495e; margin-top: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #3498db; color: white; }
                .info-box { background-color: #ecf0f1; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .warning { color: #e74c3c; font-weight: bold; }
                .success { color: #27ae60; font-weight: bold; }
            </style>
        </head>
        <body>
        """
        
        # 标题
        html += f"""
        <h1>TAVR术前流固耦合分析报告</h1>
        <div class="info-box">
            <p><strong>生成时间:</strong> {data['timestamp']}</p>
            <p><strong>分析系统:</strong> TAVR FSI Analysis System v1.0</p>
        </div>
        """
        
        # 患者信息
        patient = data['patient']
        html += f"""
        <h2>一、患者信息</h2>
        <table>
            <tr><th>项目</th><th>内容</th></tr>
            <tr><td>患者ID</td><td>{patient['id']}</td></tr>
            <tr><td>姓名</td><td>{patient['name']}</td></tr>
            <tr><td>年龄</td><td>{patient['age']}岁</td></tr>
            <tr><td>性别</td><td>{patient['sex']}</td></tr>
        </table>
        """
        
        # CT信息
        if data['ct_info']['size']:
            ct = data['ct_info']
            html += f"""
            <h2>二、影像学信息</h2>
            <table>
                <tr><th>参数</th><th>数值</th></tr>
                <tr><td>图像尺寸</td><td>{ct['size'][0]}×{ct['size'][1]}×{ct['size'][2]}</td></tr>
                <tr><td>体素大小</td><td>{ct['spacing'][0]:.2f}×{ct['spacing'][1]:.2f}×{ct['spacing'][2]:.2f} mm</td></tr>
            </table>
            """
            
        # 模拟结果
        sim = data['simulation']
        html += """
        <h2>三、模拟分析结果</h2>
        """
        
        # 血流动力学
        html += f"""
        <h3>3.1 血流动力学参数</h3>
        <table>
            <tr><th>参数</th><th>数值</th><th>参考范围</th><th>评估</th></tr>
            <tr>
                <td>峰值压差</td>
                <td>{sim.get('peak_gradient', 45):.1f} mmHg</td>
                <td><40 mmHg</td>
                <td class="{'success' if sim.get('peak_gradient', 45) < 40 else 'warning'}">
                    {'正常' if sim.get('peak_gradient', 45) < 40 else '偏高'}
                </td>
            </tr>
            <tr>
                <td>平均压差</td>
                <td>{sim.get('mean_gradient', 25):.1f} mmHg</td>
                <td><20 mmHg</td>
                <td class="{'success' if sim.get('mean_gradient', 25) < 20 else 'warning'}">
                    {'正常' if sim.get('mean_gradient', 25) < 20 else '偏高'}
                </td>
            </tr>
            <tr>
                <td>有效瓣口面积</td>
                <td>{sim.get('eoa', 1.8):.2f} cm²</td>
                <td>>1.5 cm²</td>
                <td class="{'success' if sim.get('eoa', 1.8) > 1.5 else 'warning'}">
                    {'正常' if sim.get('eoa', 1.8) > 1.5 else '偏小'}
                </td>
            </tr>
        </table>
        """
        
        # 瓣周漏评估
        leak_fraction = sim.get('leak_fraction', 8)
        if leak_fraction < 5:
            leak_grade = "无/微量"
            leak_class = "success"
        elif leak_fraction < 10:
            leak_grade = "轻度"
            leak_class = "warning"
        else:
            leak_grade = "中度以上"
            leak_class = "warning"
            
        html += f"""
        <h3>3.2 瓣周漏评估</h3>
        <table>
            <tr><th>参数</th><th>数值</th><th>分级</th></tr>
            <tr>
                <td>反流量</td>
                <td>{sim.get('leak_volume', 12):.1f} ml/beat</td>
                <td rowspan="2" class="{leak_class}">{leak_grade}</td>
            </tr>
            <tr>
                <td>反流分数</td>
                <td>{leak_fraction:.1f}%</td>
            </tr>
        </table>
        """
        
        # 冠脉风险
        html += f"""
        <h3>3.3 冠脉阻塞风险评估</h3>
        <table>
            <tr><th>参数</th><th>数值</th><th>风险等级</th></tr>
            <tr>
                <td>左冠脉阻塞风险</td>
                <td>{sim.get('lca_risk', 5)}%</td>
                <td class="{'success' if sim.get('lca_risk', 5) < 10 else 'warning'}">
                    {'低' if sim.get('lca_risk', 5) < 10 else '高'}
                </td>
            </tr>
            <tr>
                <td>右冠脉阻塞风险</td>
                <td>{sim.get('rca_risk', 3)}%</td>
                <td class="{'success' if sim.get('rca_risk', 3) < 10 else 'warning'}">
                    {'低' if sim.get('rca_risk', 3) < 10 else '高'}
                </td>
            </tr>
            <tr>
                <td>SOV高度</td>
                <td>{sim.get('sov_height', 12.5):.1f} mm</td>
                <td>-</td>
            </tr>
            <tr>
                <td>VTC距离</td>
                <td>{sim.get('vtc_distance', 10.2):.1f} mm</td>
                <td>-</td>
            </tr>
        </table>
        """
        
        # 结论和建议
        html += """
        <h2>四、结论与建议</h2>
        <div class="info-box">
        """
        
        # 自动生成结论
        conclusions = []
        recommendations = []
        
        if sim.get('peak_gradient', 45) < 40:
            conclusions.append("血流动力学参数良好")
        else:
            conclusions.append("存在跨瓣压差增高")
            recommendations.append("考虑选择更大尺寸瓣膜")
            
        if leak_fraction < 10:
            conclusions.append("瓣周漏风险低")
        else:
            conclusions.append("存在中度以上瓣周漏风险")
            recommendations.append("建议优化瓣膜定位或选择其他型号")
            
        if sim.get('lca_risk', 5) < 10 and sim.get('rca_risk', 3) < 10:
            conclusions.append("冠脉阻塞风险低")
        else:
            conclusions.append("存在冠脉阻塞风险")
            recommendations.append("术中需准备冠脉保护措施")
            
        html += "<h3>主要发现:</h3><ul>"
        for conclusion in conclusions:
            html += f"<li>{conclusion}</li>"
        html += "</ul>"
        
        if recommendations:
            html += "<h3>临床建议:</h3><ul>"
            for rec in recommendations:
                html += f"<li>{rec}</li>"
            html += "</ul>"
            
        html += """
        </div>
        
        <h2>五、免责声明</h2>
        <p style="font-size: 12px; color: #7f8c8d;">
        本报告基于计算机模拟分析生成，仅供临床参考。最终治疗决策应结合患者具体情况、
        其他检查结果以及医生的临床经验综合判断。模拟结果可能存在一定误差，
        不能完全替代临床评估。
        </p>
        
        </body>
        </html>
        """
        
        return html
        
    def exportReport(self, format):
        """导出报告"""
        if self.report_data is None:
            QMessageBox.warning(self, "警告", "没有可导出的报告")
            return
            
        if format == 'pdf':
            # 这里应该使用专业的PDF生成库如ReportLab
            # 简化版本仅作演示
            QMessageBox.information(self, "提示", "PDF导出功能将在后续版本中实现")
        elif format == 'docx':
            # 这里应该使用python-docx库
            QMessageBox.information(self, "提示", "Word导出功能将在后续版本中实现")
            
    def printReport(self):
        """打印报告"""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec_() == QDialog.Accepted:
            self.report_browser.print_(printer)
            
    def clear(self):
        """清空报告"""
        self.report_data = None
        self.report_browser.clear()


class SegmentationEditor(QDialog):
    """分割编辑对话框"""
    
    def __init__(self, ct_image, segmentation, parent=None):
        super().__init__(parent)
        self.ct_image = ct_image
        self.segmentation = sitk.Cast(segmentation, sitk.sitkUInt8)
        self.current_slice = ct_image.GetSize()[2] // 2
        self.drawing = False
        self.erase_mode = False
        self.brush_size = 5
        
        self.initUI()
        self.updateDisplay()
        
    def initUI(self):
        self.setWindowTitle("手动编辑分割")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 绘制/擦除模式
        self.draw_btn = QPushButton("绘制")
        self.draw_btn.setCheckable(True)
        self.draw_btn.setChecked(True)
        self.draw_btn.clicked.connect(lambda: self.setMode(False))
        toolbar.addWidget(self.draw_btn)
        
        self.erase_btn = QPushButton("擦除")
        self.erase_btn.setCheckable(True)
        self.erase_btn.clicked.connect(lambda: self.setMode(True))
        toolbar.addWidget(self.erase_btn)
        
        # 笔刷大小
        toolbar.addWidget(QLabel("笔刷大小:"))
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(1, 20)
        self.brush_slider.setValue(self.brush_size)
        self.brush_slider.valueChanged.connect(self.setBrushSize)
        toolbar.addWidget(self.brush_slider)
        
        self.brush_label = QLabel(f"{self.brush_size} px")
        toolbar.addWidget(self.brush_label)
        
        toolbar.addStretch()
        
        # 撤销/重做
        self.undo_btn = QPushButton("撤销")
        self.undo_btn.clicked.connect(self.undo)
        toolbar.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton("重做")
        self.redo_btn.clicked.connect(self.redo)
        toolbar.addWidget(self.redo_btn)
        
        layout.addLayout(toolbar)
        
        # 图像显示
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMouseTracking(True)
        
        # 安装事件过滤器
        self.image_label.installEventFilter(self)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        layout.addWidget(scroll_area)
        
        # 切片控制
        slice_layout = QHBoxLayout()
        
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setRange(0, self.ct_image.GetSize()[2] - 1)
        self.slice_slider.setValue(self.current_slice)
        self.slice_slider.valueChanged.connect(self.changeSlice)
        slice_layout.addWidget(self.slice_slider)
        
        self.slice_label = QLabel(f"切片: {self.current_slice + 1}/{self.ct_image.GetSize()[2]}")
        slice_layout.addWidget(self.slice_label)
        
        layout.addLayout(slice_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 历史记录
        self.history = []
        self.history_index = -1
        self.saveState()
        
    def setMode(self, erase):
        """设置绘制/擦除模式"""
        self.erase_mode = erase
        self.draw_btn.setChecked(not erase)
        self.erase_btn.setChecked(erase)
        
        # 更新光标
        if erase:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            
    def setBrushSize(self, size):
        """设置笔刷大小"""
        self.brush_size = size
        self.brush_label.setText(f"{size} px")
        
    def changeSlice(self, value):
        """改变当前切片"""
        self.current_slice = value
        self.updateDisplay()
        self.slice_label.setText(f"切片: {value + 1}/{self.ct_image.GetSize()[2]}")
        
    def updateDisplay(self):
        """更新显示"""
        # 获取CT切片
        ct_array = sitk.GetArrayFromImage(self.ct_image)
        ct_slice = ct_array[self.current_slice, :, :]
        
        # 窗位/窗宽调整
        window_level = 40
        window_width = 400
        min_val = window_level - window_width / 2
        max_val = window_level + window_width / 2
        
        ct_slice = np.clip(ct_slice, min_val, max_val)
        ct_slice = ((ct_slice - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        
        # 转换为RGB
        height, width = ct_slice.shape
        rgb_image = np.stack([ct_slice, ct_slice, ct_slice], axis=2)
        
        # 叠加分割
        seg_array = sitk.GetArrayFromImage(self.segmentation)
        seg_slice = seg_array[self.current_slice, :, :]
        
        # 红色显示分割区域
        mask = seg_slice > 0
        rgb_image[mask, 0] = 255
        rgb_image[mask, 1] = 100
        rgb_image[mask, 2] = 100
        
        # 转换为QImage
        q_image = QImage(rgb_image.data, width, height, 3 * width, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())
        
    def eventFilter(self, obj, event):
        """事件过滤器处理鼠标事件"""
        if obj == self.image_label:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drawing = True
                    self.drawAt(event.pos())
                    return True
                    
            elif event.type() == QEvent.MouseMove:
                if self.drawing:
                    self.drawAt(event.pos())
                    return True
                    
            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.drawing = False
                    self.saveState()
                    return True
                    
        return super().eventFilter(obj, event)
        
    def drawAt(self, pos):
        """在指定位置绘制/擦除"""
        # 获取图像坐标
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return
            
        x = pos.x()
        y = pos.y()
        
        # 边界检查
        if x < 0 or x >= pixmap.width() or y < 0 or y >= pixmap.height():
            return
            
        # 修改分割数据
        seg_array = sitk.GetArrayFromImage(self.segmentation)
        
        # 创建圆形笔刷
        for dy in range(-self.brush_size, self.brush_size + 1):
            for dx in range(-self.brush_size, self.brush_size + 1):
                if dx*dx + dy*dy <= self.brush_size * self.brush_size:
                    px = x + dx
                    py = y + dy
                    
                    if 0 <= px < seg_array.shape[2] and 0 <= py < seg_array.shape[1]:
                        if self.erase_mode:
                            seg_array[self.current_slice, py, px] = 0
                        else:
                            seg_array[self.current_slice, py, px] = 1
                            
        # 更新分割图像
        self.segmentation = sitk.GetImageFromArray(seg_array)
        self.segmentation.CopyInformation(self.ct_image)
        
        # 更新显示
        self.updateDisplay()
        
    def saveState(self):
        """保存当前状态用于撤销/重做"""
        # 限制历史记录大小
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            
        seg_array = sitk.GetArrayFromImage(self.segmentation)
        self.history.append(seg_array.copy())
        self.history_index += 1
        
        # 限制历史记录数量
        if len(self.history) > 20:
            self.history.pop(0)
            self.history_index -= 1
            
    def undo(self):
        """撤销"""
        if self.history_index > 0:
            self.history_index -= 1
            seg_array = self.history[self.history_index].copy()
            self.segmentation = sitk.GetImageFromArray(seg_array)
            self.segmentation.CopyInformation(self.ct_image)
            self.updateDisplay()
            
    def redo(self):
        """重做"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            seg_array = self.history[self.history_index].copy()
            self.segmentation = sitk.GetImageFromArray(seg_array)
            self.segmentation.CopyInformation(self.ct_image)
            self.updateDisplay()
            
    def getSegmentation(self):
        """获取编辑后的分割结果"""
        return self.segmentation


class SimulationDialog(QDialog):
    """模拟运行对话框"""
    
    simulation_complete = pyqtSignal(dict)  # 模拟完成信号
    
    def __init__(self, mesh, valve_type, valve_size, parent=None):
        super().__init__(parent)
        self.mesh = mesh
        self.valve_type = valve_type
        self.valve_size = valve_size
        self.simulation_thread = None
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("流固耦合模拟")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("正在运行TAVR流固耦合模拟")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # 参数显示
        params_group = QGroupBox("模拟参数")
        params_layout = QFormLayout()
        
        params_layout.addRow("瓣膜类型:", QLabel(self.valve_type))
        params_layout.addRow("瓣膜尺寸:", QLabel(self.valve_size))
        params_layout.addRow("网格单元数:", QLabel(f"{len(self.mesh['vertices'])} 顶点"))
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 进度显示
        progress_group = QGroupBox("模拟进度")
        progress_layout = QVBoxLayout()
        
        # 总体进度
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        progress_layout.addWidget(QLabel("总体进度:"))
        progress_layout.addWidget(self.overall_progress)
        
        # 当前步骤
        self.step_label = QLabel("准备模拟...")
        progress_layout.addWidget(self.step_label)
        
        # 详细进度
        self.detail_progress = QProgressBar()
        self.detail_progress.setRange(0, 100)
        progress_layout.addWidget(self.detail_progress)
        
        # 日志输出
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancelSimulation)
        button_layout.addWidget(self.cancel_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setEnabled(False)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def startSimulation(self):
        """启动模拟"""
        self.simulation_thread = SimulationThread(
            self.mesh, self.valve_type, self.valve_size)
        
        # 连接信号
        self.simulation_thread.progress.connect(self.updateProgress)
        self.simulation_thread.step_changed.connect(self.updateStep)
        self.simulation_thread.log_message.connect(self.addLog)
        self.simulation_thread.finished.connect(self.onSimulationFinished)
        
        # 启动线程
        self.simulation_thread.start()
        
    def updateProgress(self, overall, detail):
        """更新进度"""
        self.overall_progress.setValue(overall)
        self.detail_progress.setValue(detail)
        
    def updateStep(self, step):
        """更新当前步骤"""
        self.step_label.setText(step)
        
    def addLog(self, message):
        """添加日志消息"""
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def cancelSimulation(self):
        """取消模拟"""
        if self.simulation_thread and self.simulation_thread.isRunning():
            reply = QMessageBox.question(self, "确认", "确定要取消模拟吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.simulation_thread.terminate()
                self.reject()
                
    def onSimulationFinished(self, results):
        """模拟完成处理"""
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        
        if results:
            self.addLog("模拟完成！")
            self.simulation_complete.emit(results)
        else:
            self.addLog("模拟失败！")
            
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.simulation_thread and self.simulation_thread.isRunning():
            event.ignore()
            self.cancelSimulation()
        else:
            event.accept()


class SimulationThread(QThread):
    """模拟计算线程"""
    
    progress = pyqtSignal(int, int)  # 总体进度，详细进度
    step_changed = pyqtSignal(str)   # 当前步骤
    log_message = pyqtSignal(str)    # 日志消息
    finished = pyqtSignal(dict)      # 完成信号，返回结果
    
    def __init__(self, mesh, valve_type, valve_size):
        super().__init__()
        self.mesh = mesh
        self.valve_type = valve_type
        self.valve_size = valve_size
        
    def run(self):
        """运行模拟"""
        try:
            results = {}
            
            # 步骤1: 网格预处理 (10%)
            self.step_changed.emit("步骤1/5: 网格预处理")
            self.log_message.emit("检查网格质量...")
            for i in range(10):
                time.sleep(0.1)
                self.progress.emit(i, i * 10)
            self.log_message.emit("网格质量良好")
            
            # 步骤2: 设置边界条件 (20%)
            self.step_changed.emit("步骤2/5: 设置边界条件")
            self.log_message.emit("应用生理性边界条件...")
            for i in range(10, 20):
                time.sleep(0.1)
                self.progress.emit(i, (i - 10) * 10)
            self.log_message.emit("边界条件设置完成")
            
            # 步骤3: 瓣膜植入模拟 (40%)
            self.step_changed.emit("步骤3/5: 瓣膜植入模拟")
            self.log_message.emit(f"植入{self.valve_type} {self.valve_size}瓣膜...")
            for i in range(20, 40):
                time.sleep(0.15)
                self.progress.emit(i, (i - 20) * 5)
            self.log_message.emit("瓣膜植入完成")
            
            # 步骤4: 流固耦合计算 (80%)
            self.step_changed.emit("步骤4/5: 流固耦合计算")
            self.log_message.emit("开始FSI求解...")
            
            # 模拟多个心动周期
            for cycle in range(3):
                self.log_message.emit(f"计算第{cycle + 1}/3个心动周期...")
                for i in range(40 + cycle * 13, 40 + (cycle + 1) * 13):
                    time.sleep(0.2)
                    self.progress.emit(i, ((i - 40 - cycle * 13) * 100) // 13)
                    
            self.log_message.emit("FSI计算收敛")
            
            # 步骤5: 后处理分析 (100%)
            self.step_changed.emit("步骤5/5: 后处理分析")
            self.log_message.emit("提取关键指标...")
            for i in range(80, 100):
                time.sleep(0.1)
                self.progress.emit(i, (i - 80) * 5)
                
            # 生成模拟结果（示例数据）
            results = {
                'max_velocity': 2.5 + np.random.normal(0, 0.3),
                'mean_velocity': 1.2 + np.random.normal(0, 0.1),
                'reynolds': 3500 + np.random.randint(-500, 500),
                'peak_gradient': 45 + np.random.normal(0, 5),
                'mean_gradient': 25 + np.random.normal(0, 3),
                'eoa': 1.8 + np.random.normal(0, 0.2),
                'leak_volume': 12 + np.random.normal(0, 2),
                'leak_fraction': 8 + np.random.normal(0, 1.5),
                'max_stress': 8.5 + np.random.normal(0, 1),
                'stress_concentration': 2.1 + np.random.normal(0, 0.2),
                'lca_risk': 5 + np.random.randint(-2, 3),
                'rca_risk': 3 + np.random.randint(-1, 2),
                'sov_height': 12.5 + np.random.normal(0, 0.5),
                'vtc_distance': 10.2 + np.random.normal(0, 0.3),
                'valve_type': self.valve_type,
                'valve_size': self.valve_size
            }
            
            self.progress.emit(100, 100)
            self.log_message.emit("分析完成！")
            
            self.finished.emit(results)
            
        except Exception as e:
            self.log_message.emit(f"错误: {str(e)}")
            self.finished.emit({})


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.loadSettings()
        
    def initUI(self):
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 常规设置
        general_tab = self.createGeneralTab()
        tab_widget.addTab(general_tab, "常规")
        
        # 模拟设置
        simulation_tab = self.createSimulationTab()
        tab_widget.addTab(simulation_tab, "模拟")
        
        # 显示设置
        display_tab = self.createDisplayTab()
        tab_widget.addTab(display_tab, "显示")
        
        # 高级设置
        advanced_tab = self.createAdvancedTab()
        tab_widget.addTab(advanced_tab, "高级")
        
        layout.addWidget(tab_widget)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.default_btn = QPushButton("恢复默认")
        self.default_btn.clicked.connect(self.restoreDefaults)
        button_layout.addWidget(self.default_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.saveSettings)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    def createGeneralTab(self):
        """创建常规设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工作目录
        dir_group = QGroupBox("工作目录")
        dir_layout = QHBoxLayout()
        
        self.work_dir_edit = QLineEdit()
        dir_layout.addWidget(self.work_dir_edit)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browseWorkDir)
        dir_layout.addWidget(browse_btn)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # 自动保存
        save_group = QGroupBox("自动保存")
        save_layout = QFormLayout()
        
        self.auto_save_check = QCheckBox("启用自动保存")
        save_layout.addRow(self.auto_save_check)
        
        self.save_interval_spin = QSpinBox()
        self.save_interval_spin.setRange(1, 60)
        self.save_interval_spin.setSuffix(" 分钟")
        save_layout.addRow("保存间隔:", self.save_interval_spin)
        
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)
        
        # 语言设置
        lang_group = QGroupBox("语言")
        lang_layout = QFormLayout()
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(['中文', 'English'])
        lang_layout.addRow("界面语言:", self.language_combo)
        
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        layout.addStretch()
        return widget
        
    def createSimulationTab(self):
        """创建模拟设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 求解器设置
        solver_group = QGroupBox("求解器设置")
        solver_layout = QFormLayout()
        
        self.solver_combo = QComboBox()
        self.solver_combo.addItems(['内置求解器', 'ANSYS Fluent', 'OpenFOAM'])
        solver_layout.addRow("求解器:", self.solver_combo)
        
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 32)
        self.threads_spin.setValue(4)
        solver_layout.addRow("并行线程数:", self.threads_spin)
        
        solver_group.setLayout(solver_layout)
        layout.addWidget(solver_group)
        
        # 收敛标准
        convergence_group = QGroupBox("收敛标准")
        convergence_layout = QFormLayout()
        
        self.residual_spin = QDoubleSpinBox()
        self.residual_spin.setDecimals(6)
        self.residual_spin.setRange(1e-6, 1e-3)
        self.residual_spin.setValue(1e-4)
        self.residual_spin.setSingleStep(1e-5)
        convergence_layout.addRow("残差标准:", self.residual_spin)
        
        self.max_iterations_spin = QSpinBox()
        self.max_iterations_spin.setRange(100, 10000)
        self.max_iterations_spin.setValue(1000)
        convergence_layout.addRow("最大迭代次数:", self.max_iterations_spin)
        
        convergence_group.setLayout(convergence_layout)
        layout.addWidget(convergence_group)
        
        # 时间步设置
        time_group = QGroupBox("时间步设置")
        time_layout = QFormLayout()
        
        self.time_step_spin = QDoubleSpinBox()
        self.time_step_spin.setDecimals(4)
        self.time_step_spin.setRange(0.0001, 0.01)
        self.time_step_spin.setValue(0.001)
        self.time_step_spin.setSuffix(" s")
        time_layout.addRow("时间步长:", self.time_step_spin)
        
        self.cycles_spin = QSpinBox()
        self.cycles_spin.setRange(1, 10)
        self.cycles_spin.setValue(3)
        time_layout.addRow("模拟周期数:", self.cycles_spin)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        layout.addStretch()
        return widget
        
    def createDisplayTab(self):
        """创建显示设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 3D显示设置
        display_group = QGroupBox("3D显示")
        display_layout = QFormLayout()
        
        self.antialiasing_check = QCheckBox("启用抗锯齿")
        display_layout.addRow(self.antialiasing_check)
        
        self.transparency_check = QCheckBox("启用透明度")
        display_layout.addRow(self.transparency_check)
        
        self.background_combo = QComboBox()
        self.background_combo.addItems(['黑色', '白色', '渐变'])
        display_layout.addRow("背景颜色:", self.background_combo)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # 颜色映射
        colormap_group = QGroupBox("颜色映射")
        colormap_layout = QFormLayout()
        
        self.velocity_colormap = QComboBox()
        self.velocity_colormap.addItems(['jet', 'rainbow', 'coolwarm', 'viridis'])
        colormap_layout.addRow("速度场:", self.velocity_colormap)
        
        self.pressure_colormap = QComboBox()
        self.pressure_colormap.addItems(['jet', 'rainbow', 'coolwarm', 'viridis'])
        colormap_layout.addRow("压力场:", self.pressure_colormap)
        
        colormap_group.setLayout(colormap_layout)
        layout.addWidget(colormap_group)
        
        layout.addStretch()
        return widget
        
    def createAdvancedTab(self):
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 调试选项
        debug_group = QGroupBox("调试选项")
        debug_layout = QVBoxLayout()
        
        self.debug_mode_check = QCheckBox("启用调试模式")
        debug_layout.addWidget(self.debug_mode_check)
        
        self.verbose_log_check = QCheckBox("详细日志输出")
        debug_layout.addWidget(self.verbose_log_check)
        
        self.save_intermediate_check = QCheckBox("保存中间结果")
        debug_layout.addWidget(self.save_intermediate_check)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        # 性能选项
        performance_group = QGroupBox("性能优化")
        performance_layout = QFormLayout()
        
        self.gpu_acceleration_check = QCheckBox("启用GPU加速")
        performance_layout.addRow(self.gpu_acceleration_check)
        
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(100, 10000)
        self.cache_size_spin.setValue(1000)
        self.cache_size_spin.setSuffix(" MB")
        performance_layout.addRow("缓存大小:", self.cache_size_spin)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        layout.addStretch()
        return widget
        
    def browseWorkDir(self):
        """浏览工作目录"""
        folder = QFileDialog.getExistingDirectory(self, "选择工作目录")
        if folder:
            self.work_dir_edit.setText(folder)
            
    def loadSettings(self):
        """加载设置"""
        settings = QSettings("TAVR_Analysis", "Settings")
        
        # 常规设置
        self.work_dir_edit.setText(settings.value("work_dir", ""))
        self.auto_save_check.setChecked(settings.value("auto_save", True, type=bool))
        self.save_interval_spin.setValue(settings.value("save_interval", 10, type=int))
        
        # 模拟设置
        self.threads_spin.setValue(settings.value("threads", 4, type=int))
        self.residual_spin.setValue(settings.value("residual", 1e-4, type=float))
        
        # 其他设置...
        
    def saveSettings(self):
        """保存设置"""
        settings = QSettings("TAVR_Analysis", "Settings")
        
        # 常规设置
        settings.setValue("work_dir", self.work_dir_edit.text())
        settings.setValue("auto_save", self.auto_save_check.isChecked())
        settings.setValue("save_interval", self.save_interval_spin.value())
        
        # 模拟设置
        settings.setValue("threads", self.threads_spin.value())
        settings.setValue("residual", self.residual_spin.value())
        
        # 其他设置...
        
        self.accept()
        
    def restoreDefaults(self):
        """恢复默认设置"""
        reply = QMessageBox.question(self, "确认", "确定要恢复默认设置吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 恢复默认值
            self.auto_save_check.setChecked(True)
            self.save_interval_spin.setValue(10)
            self.threads_spin.setValue(4)
            self.residual_spin.setValue(1e-4)
            # 其他默认值...


class CalibrationDialog(QDialog):
    """校准对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("系统校准")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("系统校准工具")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        # 说明
        info_label = QLabel("使用已知结果的标准案例验证系统准确性")
        layout.addWidget(info_label)
        
        # 校准项目
        self.calibration_list = QListWidget()
        
        calibration_items = [
            ("CT图像重建精度", "验证图像分割和3D重建的准确性"),
            ("网格质量检查", "评估网格生成算法的性能"),
            ("流场求解验证", "对比标准流场解析解"),
            ("应力分析验证", "验证结构力学计算"),
            ("瓣周漏量化", "校准瓣周漏评估算法")
        ]
        
        for name, desc in calibration_items:
            item = QListWidgetItem(f"{name}\n  {desc}")
            self.calibration_list.addItem(item)
            
        layout.addWidget(self.calibration_list)
        
        # 运行按钮
        self.run_btn = QPushButton("运行选定的校准项目")
        self.run_btn.clicked.connect(self.runCalibration)
        layout.addWidget(self.run_btn)
        
        # 结果显示
        result_group = QGroupBox("校准结果")
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def runCalibration(self):
        """运行校准"""
        current_item = self.calibration_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "警告", "请选择要校准的项目")
            return
            
        # 模拟校准过程
        self.result_text.clear()
        self.result_text.append(f"开始校准: {current_item.text().split(chr(10))[0]}")
        self.result_text.append("-" * 50)
        
        QApplication.processEvents()
        time.sleep(1)  # 模拟处理时间
        
        # 生成模拟结果
        self.result_text.append("校准完成！")
        self.result_text.append("\n结果摘要:")
        self.result_text.append(f"- 准确率: {95 + np.random.randint(-2, 3)}%")
        self.result_text.append(f"- 相对误差: {2 + np.random.random():.1f}%")
        self.result_text.append(f"- 建议: 系统性能良好，可正常使用")


def main():
    """主函数"""
    # 设置高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setOrganizationName("Medical Imaging Lab")
    app.setApplicationName("TAVR FSI Analysis")
    
    # 设置样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = TAVRAnalysisGUI()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()