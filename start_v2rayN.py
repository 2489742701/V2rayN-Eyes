import os
import subprocess
import sys

def run_as_admin(exe_path, cwd):
    powershell_cmd = f'Start-Process -FilePath "{exe_path}" -WorkingDirectory "{cwd}" -Verb RunAs'
    subprocess.run(['powershell', '-Command', powershell_cmd])

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(script_dir, 'v2rayN.exe')
    
    if not os.path.exists(exe_path):
        print(f"错误: 找不到 {exe_path}")
        sys.exit(1)
    
    try:
        run_as_admin(exe_path, script_dir)
        print("v2rayN 已启动（正在申请管理员权限）")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
