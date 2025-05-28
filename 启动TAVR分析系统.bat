@echo off
REM ===================================
REM TAVR������Ϸ���ϵͳ�����ű�
REM Windows�������ļ�
REM �ļ���: ����TAVR����ϵͳ.bat
REM ===================================

echo ============================================
echo    TAVR��ǰ������Ϸ���ϵͳ v1.0
echo ============================================
echo.

REM ���Python�Ƿ�װ
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [����] δ��⵽Python��װ��
    echo ���Ȱ�װPython 3.7����߰汾
    echo ���ص�ַ: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [��Ϣ] ��⵽Python�汾:
python --version

REM ����������ļ�
if not exist "tavr_fsi_gui.py" (
    echo [����] δ�ҵ��������ļ� tavr_fsi_gui.py
    echo ��ȷ������ȷ��Ŀ¼�����д˽ű�
    pause
    exit /b 1
)

REM �������
echo.
echo [��Ϣ] ���ϵͳ����...
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo [����] PyQt5δ��װ�����԰�װ����...
    echo.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [����] ������װʧ�ܣ�
        echo ���ֶ�����: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

REM ������Ҫ��Ŀ¼
if not exist "data" mkdir data
if not exist "results" mkdir results
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache

REM ��������
echo.
echo [��Ϣ] ����TAVR����ϵͳ...
echo ============================================
echo.

python tavr_fsi_gui.py

if %errorlevel% neq 0 (
    echo.
    echo [����] �����쳣�˳���
    echo ��鿴logsĿ¼�µ���־�ļ�
    pause
)

REM ===================================
REM Linux/Mac Shell�ű�
REM �ļ���: launch_tavr.sh
REM ===================================
#!/bin/bash

echo "============================================"
echo "   TAVR��ǰ������Ϸ���ϵͳ v1.0"
echo "============================================"
echo ""

# ���Python�汾
if ! command -v python3 &> /dev/null; then
    echo "[����] δ��⵽Python3��װ��"
    echo "���Ȱ�װPython 3.7����߰汾"
    exit 1
fi

echo "[��Ϣ] ��⵽Python�汾:"
python3 --version

# ����������ļ�
if [ ! -f "tavr_fsi_gui.py" ]; then
    echo "[����] δ�ҵ��������ļ� tavr_fsi_gui.py"
    echo "��ȷ������ȷ��Ŀ¼�����д˽ű�"
    exit 1
fi

# ������⻷��
if [ -d "venv" ]; then
    echo "[��Ϣ] �������⻷��..."
    source venv/bin/activate
fi

# �������
echo ""
echo "[��Ϣ] ���ϵͳ����..."
python3 -c "import PyQt5" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[����] PyQt5δ��װ�����԰�װ����..."
    echo ""
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[����] ������װʧ�ܣ�"
        echo "���ֶ�����: pip3 install -r requirements.txt"
        exit 1
    fi
fi

# ������Ҫ��Ŀ¼
mkdir -p data results logs cache

# ���û��������������Ҫ��
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# ��������
echo ""
echo "[��Ϣ] ����TAVR����ϵͳ..."
echo "============================================"
echo ""

python3 tavr_fsi_gui.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[����] �����쳣�˳���"
    echo "��鿴logsĿ¼�µ���־�ļ�"
fi

REM ===================================
REM �����ߵ��Խű�
REM �ļ���: debug_tavr.bat
REM ===================================
@echo off
echo [����ģʽ] TAVR����ϵͳ
echo.

REM ���õ��Ի�������
set PYTHONPATH=%CD%
set QT_DEBUG_PLUGINS=1
set TAVR_DEBUG=1

REM ʹ�õ��Բ�������
python -u tavr_fsi_gui.py --debug

pause

REM ===================================
REM ���ٲ��Խű�
REM �ļ���: test_tavr.sh
REM ===================================
#!/bin/bash

echo "TAVRϵͳ���ٲ���"
echo "================="
echo ""

# ���е�Ԫ����
echo "[����] ����ģ��..."
python3 -c "
import sys
try:
    import PyQt5
    print('�7�7 PyQt5')
    import SimpleITK
    print('�7�7 SimpleITK')
    import vtk
    print('�7�7 VTK')
    import numpy
    print('�7�7 NumPy')
    import matplotlib
    print('�7�7 Matplotlib')
    print('')
    print('��������ģ�鵼��ɹ���')
except ImportError as e:
    print(f'�7�1 ����ʧ��: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "[����] ���ɲ�������..."
    python3 generate_test_data.py << EOF
1
0
EOF
    
    echo ""
    echo "������ɣ�ϵͳ������"
else
    echo ""
    echo "����ʧ�ܣ�����������װ��"
fi