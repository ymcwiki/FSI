@echo off
REM ===================================
REM TAVR流固耦合分析系统启动脚本
REM Windows批处理文件
REM 文件名: 启动TAVR分析系统.bat
REM ===================================

echo ============================================
echo    TAVR术前流固耦合分析系统 v1.0
echo ============================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python安装！
    echo 请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [信息] 检测到Python版本:
python --version

REM 检查主程序文件
if not exist "tavr_fsi_gui.py" (
    echo [错误] 未找到主程序文件 tavr_fsi_gui.py
    echo 请确保在正确的目录下运行此脚本
    pause
    exit /b 1
)

REM 检查依赖
echo.
echo [信息] 检查系统依赖...
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] PyQt5未安装，尝试安装依赖...
    echo.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败！
        echo 请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

REM 创建必要的目录
if not exist "data" mkdir data
if not exist "results" mkdir results
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache

REM 启动程序
echo.
echo [信息] 启动TAVR分析系统...
echo ============================================
echo.

python tavr_fsi_gui.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序异常退出！
    echo 请查看logs目录下的日志文件
    pause
)

REM ===================================
REM Linux/Mac Shell脚本
REM 文件名: launch_tavr.sh
REM ===================================
#!/bin/bash

echo "============================================"
echo "   TAVR术前流固耦合分析系统 v1.0"
echo "============================================"
echo ""

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3安装！"
    echo "请先安装Python 3.7或更高版本"
    exit 1
fi

echo "[信息] 检测到Python版本:"
python3 --version

# 检查主程序文件
if [ ! -f "tavr_fsi_gui.py" ]; then
    echo "[错误] 未找到主程序文件 tavr_fsi_gui.py"
    echo "请确保在正确的目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "[信息] 激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖
echo ""
echo "[信息] 检查系统依赖..."
python3 -c "import PyQt5" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[警告] PyQt5未安装，尝试安装依赖..."
    echo ""
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败！"
        echo "请手动运行: pip3 install -r requirements.txt"
        exit 1
    fi
fi

# 创建必要的目录
mkdir -p data results logs cache

# 设置环境变量（如果需要）
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# 启动程序
echo ""
echo "[信息] 启动TAVR分析系统..."
echo "============================================"
echo ""

python3 tavr_fsi_gui.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序异常退出！"
    echo "请查看logs目录下的日志文件"
fi

REM ===================================
REM 开发者调试脚本
REM 文件名: debug_tavr.bat
REM ===================================
@echo off
echo [调试模式] TAVR分析系统
echo.

REM 设置调试环境变量
set PYTHONPATH=%CD%
set QT_DEBUG_PLUGINS=1
set TAVR_DEBUG=1

REM 使用调试参数启动
python -u tavr_fsi_gui.py --debug

pause

REM ===================================
REM 快速测试脚本
REM 文件名: test_tavr.sh
REM ===================================
#!/bin/bash

echo "TAVR系统快速测试"
echo "================="
echo ""

# 运行单元测试
echo "[测试] 导入模块..."
python3 -c "
import sys
try:
    import PyQt5
    print('✓ PyQt5')
    import SimpleITK
    print('✓ SimpleITK')
    import vtk
    print('✓ VTK')
    import numpy
    print('✓ NumPy')
    import matplotlib
    print('✓ Matplotlib')
    print('')
    print('所有依赖模块导入成功！')
except ImportError as e:
    print(f'✗ 导入失败: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "[测试] 生成测试数据..."
    python3 generate_test_data.py << EOF
1
0
EOF
    
    echo ""
    echo "测试完成！系统就绪。"
else
    echo ""
    echo "测试失败！请检查依赖安装。"
fi