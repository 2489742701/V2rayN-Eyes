@echo off
chcp 65001 >nul
echo ========================================
echo   V2RayN全能采集器 - 打包工具
echo ========================================
echo.

echo [1/4] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python，请先安装Python
    pause
    exit /b 1
)
echo ✅ Python环境正常

echo.
echo [2/4] 检查PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  未找到PyInstaller，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ 安装PyInstaller失败
        pause
        exit /b 1
    )
)
echo ✅ PyInstaller已就绪

echo.
echo [3/4] 开始打包美化版...
python -m PyInstaller v2rayN_manager_美化版.spec --clean

if errorlevel 1 (
    echo ❌ 打包失败
    pause
    exit /b 1
)

echo.
echo [4/4] 复制配置文件...
if not exist "dist\V2RayN全能采集器\v2ray_pro_config.json" (
    copy "v2ray_pro_config.json" "dist\V2RayN全能采集器\" >nul
)
if not exist "dist\V2RayN全能采集器\v2ray_sources.json" (
    copy "v2ray_sources.json" "dist\V2RayN全能采集器\" >nul
)
if not exist "dist\V2RayN全能采集器\address_list.json" (
    copy "address_list.json" "dist\V2RayN全能采集器\" >nul
)

echo.
echo ========================================
echo   ✅ 打包完成！
echo ========================================
echo.
echo 输出目录: dist\V2RayN全能采集器\
echo.
echo 生成的文件:
echo   - V2RayN全能采集器.exe (主程序)
echo   - v2ray_pro_config.json (配置文件)
echo   - v2ray_sources.json (源列表)
echo   - address_list.json (地址列表)
echo   - 其他依赖文件...
echo.
echo 📁 文件夹模式：所有文件都在同一个目录下
echo    可以直接复制整个文件夹使用
echo.
pause
