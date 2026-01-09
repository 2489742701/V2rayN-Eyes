import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import re
import threading
import json
import os
from datetime import datetime
from urllib.parse import urljoin

# --- 配置文件路径 ---
CONFIG_FILE = "v2ray_pro_config.json"

# --- 默认配置 ---
DEFAULT_CONFIG = {
    # 普通直连源 (直接抓取网页文字里的节点)
    "direct_sources": [
        {"name": "GitHub 免费源 (Alvin9999)", "url": "https://github.com/Alvin9999-newpac/fanqiang/wiki/v2ray%E5%85%8D%E8%B4%B9%E8%B4%A6%E5%8F%B7"},
        {"name": "GitHub 免费源 (Pawdroid)", "url": "https://github.com/pawdroid/Free-servers"}
    ],
    # 论坛/博客源 (抓取订阅文件地址)
    "forum_sources": [
        {
            "name": "米贝分享", 
            "url": "https://www.mibei77.com", 
            "keyword": "免费精选节点"
        }
    ],
    # 正则 (用于直连模式)
    "protocols": [
        r'vmess://[a-zA-Z0-9+/=]+',
        r'vless://[a-zA-Z0-9\-]+@[a-zA-Z0-9\.\-]+:\d+[^\s<>"]*',
        r'hysteria2?://[^\s<>"]+',
        r'trojan://[^\s<>"]+',
        r'ss://[a-zA-Z0-9+/=]+@[a-zA-Z0-9\.\-]+:\d+[^\s<>"]*',
        r'ss://[a-zA-Z0-9+/=]+(?![@])[^\s<>"]*'
    ]
}

class V2RayProManager:
    def __init__(self, root):
        self.root = root
        self.root.title("V2RayN 全能采集器 (订阅链接提取版)")
        self.root.geometry("1000x700")
        
        self.config = DEFAULT_CONFIG.copy()
        
        # --- 顶部控制栏 ---
        top_frame = ttk.Frame(root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # 模式选择
        ttk.Label(top_frame, text="采集模式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="forum") # 默认改为论坛模式方便你测试
        self.mode_combo = ttk.Combobox(top_frame, textvariable=self.mode_var, state="readonly", width=12)
        self.mode_combo['values'] = ('forum', 'direct')
        self.mode_combo.current(0)
        self.mode_combo.pack(side=tk.LEFT, padx=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self.refresh_source_combo)
        
        # 数据源选择
        ttk.Label(top_frame, text="选择源:").pack(side=tk.LEFT, padx=(10, 0))
        self.source_combo = ttk.Combobox(top_frame, width=30, state="readonly")
        self.source_combo.pack(side=tk.LEFT, padx=5)
        
        # 管理按钮
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
        
        # 右侧结果
        self.res_group_label = tk.StringVar(value="采集结果")
        res_group = ttk.LabelFrame(paned, text="采集结果", width=600) # 标题动态化
        paned.add(res_group, weight=2)
        self.result_text = scrolledtext.ScrolledText(res_group, height=20, width=70, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 底部状态
        self.status_var = tk.StringVar(value="就绪")
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

    # --- 逻辑1: 普通直连抓取 (抓取单个节点) ---
    def worker_direct(self, source):
        self.ui_toggle(False)
        try:
            url = source['url']
            self.log(f"正在访问普通源: {url}")
            text = self.http_get(url)
            
            # 提取节点
            all_nodes = []
            patterns = self.config.get('protocols', [])
            for p in patterns:
                all_nodes.extend(re.findall(p, text))
            
            unique_nodes = self.smart_deduplicate(all_nodes)
            self.show_results(unique_nodes, "直连节点采集完成")
            
        except Exception as e:
            self.log(f"错误: {e}")
        finally:
            self.ui_toggle(True)

    # --- 逻辑2: 论坛/博客 (提取订阅地址) ---
    def worker_forum(self, source):
        self.ui_toggle(False)
        try:
            base_url = source['url']
            keyword = source.get('keyword', '')
            self.log(f"正在扫描博客目录: {base_url}")
            
            # 1. 获取目录页
            index_html = self.http_get(base_url)
            
            # 2. 寻找最新文章
            links = re.findall(r'<a[^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>', index_html, re.IGNORECASE | re.DOTALL)
            candidates = []
            today_str = datetime.now().strftime("%Y年%m月%d日") 
            
            self.log(f"正在寻找包含 '{keyword}' 的最新文章...")
            
            target_post_url = None
            
            for href, title in links:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                if keyword in clean_title:
                    full_url = urljoin(base_url, href)
                    candidates.append((full_url, clean_title))
            
            if not candidates:
                self.log("❌ 未找到符合关键词的文章")
                return

            # 优先找今天的
            for url, title in candidates:
                if today_str in title:
                    target_post_url = url
                    self.log(f"✅ 找到今日文章: {title}")
                    break
            
            # 找不到今天的就找最新的
            if not target_post_url and candidates:
                target_post_url = candidates[0][0]
                self.log(f"⚠️ 使用最新文章: {candidates[0][1]}")

            if not target_post_url: return

            # 3. 进入文章页，只提取 txt/yaml 链接
            self.log(f"读取文章: {target_post_url}")
            post_html = self.http_get(target_post_url)
            
            # 正则匹配订阅文件链接
            sub_links = re.findall(r'(https?://[^\s"\'<>]+?\.(?:txt|yaml|yml))', post_html, re.IGNORECASE)
            sub_links = list(set(sub_links)) # 去重
            
            # --- 关键修改：直接显示地址，不下载 ---
            if sub_links:
                self.log(f"🎉 发现 {len(sub_links)} 个订阅地址，已列出！")
                self.show_results(sub_links, f"成功提取 {len(sub_links)} 个订阅地址")
            else:
                self.log("❌ 文章中未发现 .txt 或 .yaml 链接")

        except Exception as e:
            self.log(f"❌ 流程错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.ui_toggle(True)

    # --- UI 更新辅助 ---
    def show_results(self, lines, status_msg="完成"):
        def _update():
            # 追加模式，先加换行
            current_text = self.result_text.get(1.0, tk.END)
            if len(current_text) > 1: self.result_text.insert(tk.END, "\n")
            
            self.result_text.insert(tk.END, "\n".join(lines))
            self.result_text.see(tk.END)
            self.status_var.set(status_msg)
        self.root.after(0, _update)

    # 智能去重 (用于直连模式)
    def smart_deduplicate(self, links):
        node_map = {}
        for raw_link in links:
            clean_link = raw_link.strip()
            if clean_link.endswith("&amp"): clean_link = clean_link[:-4]
            elif clean_link.endswith("&"): clean_link = clean_link[:-1]
            if not clean_link: continue
            try:
                core = clean_link.split("://")[1].split("#")[0].split("?")[0]
                if "@" in core: core = core.split("@")[1]
                fingerprint = core
            except: fingerprint = clean_link
            if fingerprint in node_map:
                if len(clean_link) > len(node_map[fingerprint]): node_map[fingerprint] = clean_link
            else: node_map[fingerprint] = clean_link
        return list(node_map.values())

    # 网络请求
    def http_get(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text

    # --- 配置管理窗口 ---
    def open_config_manager(self):
        win = tk.Toplevel(self.root)
        win.title("配置与地址管理")
        win.geometry("700x500")
        
        tabs = ttk.Notebook(win)
        tabs.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        f1 = ttk.Frame(tabs); tabs.add(f1, text="论坛/博客(抓取订阅地址)")
        self.create_list_editor(f1, "forum_sources", ["name", "url", "keyword"], ["名称", "目录URL", "标题关键词"])
        
        f2 = ttk.Frame(tabs); tabs.add(f2, text="直连源(抓取节点)")
        self.create_list_editor(f2, "direct_sources", ["name", "url"], ["名称", "URL"])
        
        f3 = ttk.Frame(tabs); tabs.add(f3, text="正则(直连模式)")
        self.create_protocol_editor(f3)

    def create_list_editor(self, parent, config_key, keys, headers):
        tree = ttk.Treeview(parent, columns=keys, show="headings")
        for k, h in zip(keys, headers):
            tree.heading(k, text=h)
            tree.column(k, width=150)
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        def reload():
            for i in tree.get_children(): tree.delete(i)
            for item in self.config[config_key]:
                vals = [item.get(k, "") for k in keys]
                tree.insert("", tk.END, values=vals)
        reload()
        
        edit_frame = ttk.Frame(parent)
        edit_frame.pack(fill=tk.X, padx=5, pady=5)
        entries = {}
        for k, h in zip(keys, headers):
            ttk.Label(edit_frame, text=h).pack(side=tk.LEFT)
            e = ttk.Entry(edit_frame, width=15 if k!='url' else 25)
            e.pack(side=tk.LEFT, padx=2)
            entries[k] = e
            
        def add_item():
            new_item = {k: entries[k].get().strip() for k in keys}
            if not new_item[keys[0]]: return
            self.config[config_key].append(new_item)
            self.save_config()
            reload()
            self.refresh_source_combo()
            for e in entries.values(): e.delete(0, tk.END)

        def del_item():
            sel = tree.selection()
            if not sel: return
            val = tree.item(sel[0])['values']
            self.config[config_key] = [x for x in self.config[config_key] if x[keys[0]] != val[0]]
            self.save_config()
            reload()
            self.refresh_source_combo()

        ttk.Button(edit_frame, text="添加", command=add_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(edit_frame, text="删除选中", command=del_item).pack(side=tk.LEFT, padx=5)

    def create_protocol_editor(self, parent):
        listbox = tk.Listbox(parent)
        listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        def reload():
            listbox.delete(0, tk.END)
            for p in self.config['protocols']: listbox.insert(tk.END, p)
        reload()
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=5)
        entry = ttk.Entry(frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        def add():
            val = entry.get().strip()
            if val and val not in self.config['protocols']:
                self.config['protocols'].append(val)
                self.save_config()
                reload()
                entry.delete(0, tk.END)
        def delete():
            idx = listbox.curselection()
            if idx:
                self.config['protocols'].remove(listbox.get(idx))
                self.save_config()
                reload()
        ttk.Button(frame, text="添加正则", command=add).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame, text="删除选中", command=delete).pack(side=tk.LEFT, padx=2)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
            except: pass
        self.refresh_source_combo()

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e: messagebox.showerror("保存失败", str(e))

    def refresh_source_combo(self, event=None):
        mode = self.mode_var.get()
        if mode == 'direct':
            items = self.config['direct_sources']
            vals = [x['name'] for x in items]
        else:
            items = self.config['forum_sources']
            vals = [f"{x['name']} (关键词:{x.get('keyword','')})" for x in items]
        self.source_combo['values'] = vals
        if vals: self.source_combo.current(0)
        else: self.source_combo.set('')

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

def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = V2RayProManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()