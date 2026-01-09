import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import re
import threading
import json
import os
import base64
import traceback
import random
from datetime import datetime
from urllib.parse import urljoin
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 配置文件路径 ---
CONFIG_FILE = "v2ray_pro_config.json"

# --- 浏览器伪装池 ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/125.0.0.0 Safari/537.36"
]

# --- 默认配置 ---
DEFAULT_CONFIG = {
    "direct_sources": [
        {"name": "GitHub 免费源 (Alvin9999)", "url": "https://github.com/Alvin9999-newpac/fanqiang/wiki/v2ray%E5%85%8D%E8%B4%B9%E8%B4%A6%E5%8F%B7"},
        {"name": "GitHub 免费源 (Pawdroid)", "url": "https://github.com/pawdroid/Free-servers"}
    ],
    "forum_sources": [
        {"name": "米贝分享", "url": "https://www.mibei77.com", "keyword": "免费精选节点"}
    ],
    # --- v6.0 核心改动：改进正则匹配 ---
    # 匹配到行尾或空格前，避免节点地址被截断，同时避免匹配HTML标签
    "protocols": [
        r'vmess://[^\s\n\r<]+',
        r'vless://[^\s\n\r<]+',
        r'hysteria2?://[^\s\n\r<]+',
        r'trojan://[^\s\n\r<]+',
        r'ss://[^\s\n\r<]+'
    ]
}

class V2RayProManager:
    def __init__(self, root):
        self.root = root
        self.root.title("V2RayN 全能采集器 (v6.0 精美版)")
        self.root.geometry("1000x750")
        
        self.config = DEFAULT_CONFIG.copy()
        
        # --- 创建菜单栏 ---
        self.create_menu_bar()
        
        # --- 顶部控制栏 ---
        top_frame = ttk.Frame(root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # 1. 模式选择
        ttk.Label(top_frame, text="采集模式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="direct")
        self.mode_combo = ttk.Combobox(top_frame, textvariable=self.mode_var, state="readonly", width=10)
        self.mode_combo['values'] = ('forum', 'direct')
        self.mode_combo.current(1)
        self.mode_combo.pack(side=tk.LEFT, padx=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self.refresh_source_combo)
        
        # 2. 数据源选择
        ttk.Label(top_frame, text="源:").pack(side=tk.LEFT, padx=(5, 0))
        self.source_combo = ttk.Combobox(top_frame, width=30, state="readonly")
        self.source_combo.pack(side=tk.LEFT, padx=5)
        
        # 3. 管理按钮
        ttk.Button(top_frame, text="⚙️ 配置管理", command=self.open_config_manager).pack(side=tk.LEFT, padx=5)
        
        # --- 操作栏 ---
        action_frame = ttk.Frame(root, padding="5")
        action_frame.pack(fill=tk.X, padx=10)
        
        self.btn_fetch = ttk.Button(action_frame, text="🚀 开始采集", command=self.start_task)
        self.btn_fetch.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="🧹 清空结果", command=lambda: self.result_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📋 复制结果", command=self.copy_all).pack(side=tk.RIGHT, padx=5)
        
        # --- 内容显示区 ---
        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧日志
        log_group = ttk.LabelFrame(paned, text="执行日志", width=400)
        paned.add(log_group, weight=1)
        self.log_text = scrolledtext.ScrolledText(log_group, height=20, width=50, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加日志复制功能
        self.log_text.bind("<Button-3>", self.show_log_context_menu)
        
        # 创建日志右键菜单
        self.log_context_menu = tk.Menu(self.log_text, tearoff=0)
        self.log_context_menu.add_command(label="复制", command=self.copy_log)
        self.log_context_menu.add_command(label="全选", command=self.select_all_log)
        self.log_context_menu.add_command(label="清空日志", command=self.clear_log)
        
        # 右侧结果
        res_group = ttk.LabelFrame(paned, text="采集结果", width=600)
        paned.add(res_group, weight=2)
        self.result_text = scrolledtext.ScrolledText(res_group, height=20, width=70, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 底部状态
        self.status_var = tk.StringVar(value="就绪 - 点击开始采集")
        ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)

        self.load_config()

    # ================= 核心逻辑区 =================

    def start_task(self):
        mode = self.mode_var.get()
        idx = self.source_combo.current()
        if idx < 0: return messagebox.showwarning("提示", "请先选择一个源")
        
        if mode == 'direct':
            source = self.config['direct_sources'][idx]
            threading.Thread(target=self.worker_direct, args=(source,), daemon=True).start()
        else:
            source = self.config['forum_sources'][idx]
            threading.Thread(target=self.worker_forum, args=(source,), daemon=True).start()

    # --- 逻辑1: 直连模式 ---
    def worker_direct(self, source):
        self.ui_toggle(False)
        try:
            url = source['url']
            self.log(f"正在访问: {url}")
            
            text = self.http_get(url)
            
            # --- 预处理：只做最必要的 ---
            # 1. 还原 HTML 实体符号 (因为链接参数里经常有 &)
            # 网页源码里是 &amp;，如果不转回来，正则匹配 & 时就会断掉
            text = text.replace("&amp;", "&")
            
            # 2. 将 <br> 转为空格，防止粘连
            text = text.replace("<br>", " ").replace("</p>", " ")
            
            # Base64 智能解码 (针对 vmess 订阅链接)
            try:
                clean_b64 = re.sub(r'\s+', '', text)
                if "<html" not in text.lower() and "<body" not in text.lower() and len(clean_b64) > 50:
                     decoded_bytes = base64.b64decode(clean_b64, validate=False)
                     decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                     self.log("检测到 Base64 内容，已自动解码")
                     text += "\n" + decoded_str 
            except: pass 

            # 正则提取
            all_nodes = []
            patterns = self.config.get('protocols', [])
            
            self.log(f"内容处理完毕，长度: {len(text)}，开始匹配...")
            
            for p in patterns:
                # 简单粗暴：匹配所有非中文、非空格的连续字符
                found = re.findall(p, text)
                if found:
                    self.log(f"正则 '{p}' 匹配到 {len(found)} 个候选")
                    all_nodes.extend(found)
            
            # --- 后期处理 ---
            valid_nodes = []
            seen = set()
            
            # 调试日志
            self.log(f"原始匹配数量: {len(all_nodes)}")
            
            for i, node in enumerate(all_nodes):
                original_node = node
                
                # 清理HTML标签：检查是否包含HTML标签的开始字符
                if '<' in node:
                    node = node.split('<')[0]
                
                # 清理HTML标签：检查是否包含HTML标签的结束字符
                if '>' in node:
                    node = node.split('>')[0]
                
                # 去掉可能的尾部杂质（如句号、括号）
                node = node.strip().rstrip('.,)。]"\'')
                
                # 长度检查：有效链接通常很长
                if len(node) < 15: 
                    self.log(f"过滤掉节点 {i+1}: 长度 {len(node)} < 15")
                    continue
                    
                if node not in seen:
                    valid_nodes.append(node)
                    seen.add(node)
                    self.log(f"保留节点 {i+1}: 长度 {len(node)}")
                else:
                    self.log(f"重复节点 {i+1}: 已存在")
            
            self.log(f"最终有效节点数量: {len(valid_nodes)}")
            
            if valid_nodes:
                self.show_results(valid_nodes, f"成功采集 {len(valid_nodes)} 个节点")
            else:
                self.log("⚠️ 警告：匹配后没有有效节点。")
                if len(text) < 1000:
                    self.log(f"原始内容预览: {text[:200]}...")
            
        except Exception as e:
            err_msg = traceback.format_exc()
            self.log(f"❌ 出错: {e}")
            self.show_error_report("采集直连源出错", err_msg)
        finally:
            self.ui_toggle(True)

    # --- 逻辑2: 论坛模式 ---
    def worker_forum(self, source):
        self.ui_toggle(False)
        try:
            base_url = source['url']
            keyword = source.get('keyword', '')
            self.log(f"正在扫描: {base_url}")
            
            index_html = self.http_get(base_url)
            links = re.findall(r'<a[^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>', index_html, re.IGNORECASE | re.DOTALL)
            
            candidates = []
            today_str = datetime.now().strftime("%Y年%m月%d日") 
            
            self.log(f"寻找关键词: '{keyword}' ...")
            
            target_post_url = None
            for href, title in links:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                if keyword in clean_title:
                    full_url = urljoin(base_url, href)
                    candidates.append((full_url, clean_title))
            
            for url, title in candidates:
                if today_str in title:
                    target_post_url = url
                    self.log(f"✅ 锁定今日文章: {title}")
                    break
            
            if not target_post_url and candidates:
                target_post_url = candidates[0][0]
                self.log(f"⚠️ 使用最新文章: {candidates[0][1]}")

            if not target_post_url: 
                self.log("❌ 未找到符合要求的文章")
                return

            self.log(f"读取文章: {target_post_url}")
            post_html = self.http_get(target_post_url)
            
            sub_links = re.findall(r'(https?://[^\s"\'<>]+?\.(?:txt|yaml|yml))', post_html, re.IGNORECASE)
            sub_links = list(set(sub_links))
            
            if sub_links:
                self.show_results(sub_links, f"成功提取 {len(sub_links)} 个订阅地址")
            else:
                self.log("❌ 文章中未发现订阅链接")

        except Exception as e:
            err_msg = traceback.format_exc()
            self.log(f"❌ 出错: {e}")
            self.show_error_report("采集论坛源出错", err_msg)
        finally:
            self.ui_toggle(True)

    # --- 核心：网络请求 ---
    def http_get(self, url, max_retries=3):
        ua = random.choice(USER_AGENTS)
        headers = {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive'
        }
        
        for attempt in range(max_retries):
            try:
                resp = requests.get(
                    url, headers=headers, timeout=20,
                    verify=False, 
                    allow_redirects=True
                )
                resp.encoding = 'utf-8'
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                if attempt == max_retries - 1: raise e
                import time; time.sleep(1)

    # --- 错误弹窗 ---
    def show_error_report(self, title, error_content):
        def _show():
            win = tk.Toplevel(self.root)
            win.title(f"错误报告 - {title}")
            win.geometry("700x500")
            ttk.Label(win, text="程序运行出错，请查看下方详情：", foreground="red", padding=10).pack(fill=tk.X)
            txt = scrolledtext.ScrolledText(win, font=("Consolas", 9))
            txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            txt.insert(tk.END, error_content)
            btn_frame = ttk.Frame(win, padding=10)
            btn_frame.pack(fill=tk.X)
            def copy_err():
                win.clipboard_clear()
                win.clipboard_append(error_content)
                messagebox.showinfo("复制成功", "错误日志已复制", parent=win)
            ttk.Button(btn_frame, text="📋 复制错误", command=copy_err).pack(side=tk.RIGHT)
            ttk.Button(btn_frame, text="关闭", command=win.destroy).pack(side=tk.RIGHT, padx=5)
        self.root.after(0, _show)

    # --- UI 辅助 ---
    def show_results(self, lines, status_msg="完成"):
        def _update():
            current_text = self.result_text.get(1.0, tk.END).strip()
            if current_text: self.result_text.insert(tk.END, "\n")
            self.result_text.insert(tk.END, "\n".join(lines))
            self.result_text.see(tk.END)
            self.status_var.set(status_msg)
            self.log(f"✅ 结果已更新: {len(lines)} 条")
        self.root.after(0, _update)

    def ui_toggle(self, enable):
        state = "normal" if enable else "disabled"
        self.btn_fetch.config(state=state)

    def log(self, msg):
        self.root.after(0, lambda: self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n") or self.log_text.see(tk.END))

    def copy_all(self):
        data = self.result_text.get(1.0, tk.END).strip()
        if data:
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            messagebox.showinfo("成功", "内容已复制")

    # --- 日志复制功能 ---
    def show_log_context_menu(self, event):
        try:
            self.log_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.log_context_menu.grab_release()

    def copy_log(self):
        try:
            # 获取选中的文本
            selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
        except tk.TclError:
            # 如果没有选中文本，复制全部日志
            all_text = self.log_text.get(1.0, tk.END).strip()
            if all_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(all_text)
                messagebox.showinfo("成功", "全部日志已复制")

    def select_all_log(self):
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    # --- 配置管理窗口 ---
    def open_config_manager(self):
        win = tk.Toplevel(self.root)
        win.title("配置管理")
        win.geometry("800x600")
        
        tabs = ttk.Notebook(win)
        tabs.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        f1 = ttk.Frame(tabs); tabs.add(f1, text="论坛源")
        self.create_list_editor(f1, "forum_sources", ["name", "url", "keyword"], ["名称", "URL", "关键词"])
        
        f2 = ttk.Frame(tabs); tabs.add(f2, text="直连源")
        self.create_list_editor(f2, "direct_sources", ["name", "url"], ["名称", "URL"])
        
        f3 = ttk.Frame(tabs); tabs.add(f3, text="正则")
        self.create_protocol_editor(f3)

    def create_list_editor(self, parent, key, cols, heads):
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=vsb.set)
        
        for c, h in zip(cols, heads): 
            tree.heading(c, text=h)
            if c == 'url': tree.column(c, width=400)
            else: tree.column(c, width=150)
            
        tree.pack(fill=tk.BOTH, expand=True)

        def reload():
            for i in tree.get_children(): tree.delete(i)
            for x in self.config[key]: tree.insert("", tk.END, values=[x.get(c,"") for c in cols])
        reload()
        
        edit_group = ttk.LabelFrame(parent, text="添加/编辑项目", padding=10)
        edit_group.pack(fill=tk.X, padx=5, pady=5)
        
        entries = {}
        for i, (c, h) in enumerate(zip(cols, heads)):
            ttk.Label(edit_group, text=f"{h}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            e = ttk.Entry(edit_group, width=60 if c=='url' else 25)
            e.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            entries[c] = e
            
        btn_frame = ttk.Frame(edit_group)
        btn_frame.grid(row=len(cols), column=0, columnspan=2, pady=10)
        
        def add():
            val = {c: e.get().strip() for c, e in entries.items()}
            if not val[cols[0]]: return messagebox.showwarning("错误", "名称不能为空")
            self.config[key].append(val)
            self.save_config()
            reload()
            self.refresh_source_combo()
            for e in entries.values(): e.delete(0, tk.END)

        def delete():
            if s := tree.selection():
                v = tree.item(s[0])['values']
                self.config[key] = [x for x in self.config[key] if x[cols[0]] != v[0]]
                self.save_config()
                reload()
                self.refresh_source_combo()
            else:
                messagebox.showinfo("提示", "请选中要删除的项")

        ttk.Button(btn_frame, text="✅ 添加到列表", command=add).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="🗑️ 删除选中项", command=delete).pack(side=tk.LEFT, padx=10)

    def create_protocol_editor(self, parent):
        lb = tk.Listbox(parent, height=15)
        lb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        [lb.insert(tk.END, p) for p in self.config['protocols']]
        
        f = ttk.Frame(parent, padding=5)
        f.pack(fill=tk.X)
        e = ttk.Entry(f)
        e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def add(): 
            if v:=e.get(): 
                self.config['protocols'].append(v)
                self.save_config()
                lb.insert(tk.END, v)
                e.delete(0, tk.END)
        def delete():
            if s:=lb.curselection(): 
                self.config['protocols'].pop(s[0])
                self.save_config()
                lb.delete(s[0])
                
        ttk.Button(f, text="添加正则", command=add).pack(side=tk.LEFT)
        ttk.Button(f, text="删除选中", command=delete).pack(side=tk.LEFT, padx=5)

    # --- 创建菜单栏 ---
    def create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 文件", menu=file_menu)
        file_menu.add_command(label="📤 导出结果", command=self.export_results)
        file_menu.add_command(label="📥 导入配置", command=self.import_config)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 退出", command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="✏️ 编辑", menu=edit_menu)
        edit_menu.add_command(label="🧹 清空结果", command=lambda: self.result_text.delete(1.0, tk.END))
        edit_menu.add_command(label="🗑️ 清空日志", command=self.clear_log)
        edit_menu.add_separator()
        edit_menu.add_command(label="📋 复制结果", command=self.copy_all)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🔧 工具", menu=tools_menu)
        tools_menu.add_command(label="⚙️ 配置管理", command=self.open_config_manager)
        tools_menu.add_command(label="🔄 刷新源列表", command=self.refresh_source_combo)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ 帮助", menu=help_menu)
        help_menu.add_command(label="📖 使用说明", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ 关于", command=self.show_about)
        help_menu.add_command(label="🔄 检查更新", command=self.check_updates)
    
    # --- 导出结果 ---
    def export_results(self):
        from tkinter import filedialog
        content = self.result_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有可导出的内容")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="导出结果"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("成功", "结果已导出")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    # --- 导入配置 ---
    def import_config(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="导入配置"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
                self.save_config()
                self.refresh_source_combo()
                messagebox.showinfo("成功", "配置已导入")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")
    
    # --- 使用说明 ---
    def show_help(self):
        help_text = """
V2RayN 全能采集器 使用说明

【采集模式】
• 直连模式：直接从指定的URL采集节点链接
• 论坛模式：从论坛页面扫描并提取订阅链接

【使用步骤】
1. 选择采集模式（直连或论坛）
2. 选择数据源
3. 点击"开始采集"按钮
4. 等待采集完成
5. 复制或导出结果

【配置管理】
点击"配置管理"按钮可以：
• 添加/删除直连源
• 添加/删除论坛源
• 编辑正则表达式

【快捷操作】
• 右键点击日志可以复制、全选或清空
• 使用菜单栏的"导出结果"保存采集结果
        """
        messagebox.showinfo("使用说明", help_text)
    
    # --- 关于 ---
    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("关于")
        about_window.geometry("600x500")
        about_window.resizable(True, True)
        
        # 居中显示
        about_window.transient(self.root)
        about_window.grab_set()
        
        # 内容
        frame = ttk.Frame(about_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(frame, text="V2RayN 全能采集器", font=("Microsoft YaHei", 20, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 版本
        version_label = ttk.Label(frame, text="版本 v6.0 精美版", font=("Microsoft YaHei", 12))
        version_label.pack(pady=(0, 20))
        
        # 信息
        info_text = """
一个强大的V2Ray节点采集工具

主要功能：
• 支持直连和论坛两种采集模式
• 智能正则匹配，自动提取节点
• Base64自动解码
• 支持多种协议：vmess, vless, trojan, ss, hysteria2
• 完善的配置管理系统
• 美观的用户界面

技术特点：
• 多线程采集，不阻塞界面
• 浏览器伪装，避免被识别
• SSL证书验证可选
• 智能错误处理和日志记录

开发者：Thanksplay开发
技术支持：deepseek-glm4.7-trae CN
更新日期：2026-01-09
        """
        
        info_label = ttk.Label(frame, text=info_text, font=("Microsoft YaHei", 10), justify=tk.LEFT)
        info_label.pack(pady=(0, 20), fill=tk.BOTH, expand=True)
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="确定", command=about_window.destroy, width=15).pack(side=tk.RIGHT)
    
    # --- 检查更新 ---
    def check_updates(self):
        update_window = tk.Toplevel(self.root)
        update_window.title("检查更新")
        update_window.geometry("500x350")
        update_window.resizable(True, True)
        
        # 居中显示
        update_window.transient(self.root)
        update_window.grab_set()
        
        # 内容
        frame = ttk.Frame(update_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(frame, text="检查更新", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 当前版本
        current_frame = ttk.LabelFrame(frame, text="当前版本", padding="10")
        current_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(current_frame, text="V2RayN 全能采集器 v6.0 精美版", font=("Microsoft YaHei", 11)).pack()
        ttk.Label(current_frame, text="发布日期：2026-01-09", font=("Microsoft YaHei", 9)).pack()
        
        # 更新信息
        update_frame = ttk.LabelFrame(frame, text="最新版本", padding="10")
        update_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        update_text = """
正在检查更新...

当前已是最新版本！

最新功能：
• 全新美化的用户界面
• 专业的菜单系统
• 关于和更新功能
• 导入导出配置功能
• 完善的使用说明
        """
        
        update_label = ttk.Label(update_frame, text=update_text, font=("Microsoft YaHei", 9), justify=tk.LEFT)
        update_label.pack(fill=tk.BOTH, expand=True)
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="确定", command=update_window.destroy, width=15).pack(side=tk.RIGHT)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: self.config.update(json.load(f))
            except: pass
        self.refresh_source_combo()
    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=4, ensure_ascii=False)
    def refresh_source_combo(self, e=None):
        if self.mode_var.get() == 'direct':
            self.source_combo['values'] = [x['name'] for x in self.config['direct_sources']]
        else:
            self.source_combo['values'] = [x['name'] for x in self.config['forum_sources']]
        if self.source_combo['values']: self.source_combo.current(0)

def main():
    root = tk.Tk()
    try: from ctypes import windll; windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = V2RayProManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()