import sqlite3
import os
import json
import base64
import re
import subprocess
import sys
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError

def get_clipboard_text():
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return data
    except:
        try:
            return subprocess.check_output(['powershell', '-command', 'Get-Clipboard'], 
                                          text=True).strip()
        except:
            return None

def fetch_url_content(url):
    try:
        # 对中文URL进行编码
        encoded_url = urllib.parse.quote(url, safe=':/')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(encoded_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
        return content
    except (URLError, HTTPError) as e:
        print(f"获取网页内容失败: {e}")
        return None
    except Exception as e:
        print(f"发生错误: {e}")
        return None

def extract_links_from_html(html_content):
    links = []
    
    # 只提取 vmess://、vless:// 和 hysteria2:// 三种协议
    # 改进的正则表达式，处理Base64编码和换行符
    vmess_pattern = r'vmess://[a-zA-Z0-9+/=\n\r]+(?:[a-zA-Z0-9+/=\n\r]|%[0-9A-Fa-f]{2})*'
    vless_pattern = r'vless://[^\s<>"\'\)]+'
    hysteria2_pattern = r'hysteria2://[^\s<>"\'\)]+'
    
    # 从HTML中提取所有可能的链接
    all_patterns = [vmess_pattern, vless_pattern, hysteria2_pattern]
    
    for pattern in all_patterns:
        matches = re.findall(pattern, html_content)
        links.extend(matches)
    
    # 处理vmess链接中的换行符
    processed_links = []
    for link in links:
        # 移除换行符和空格
        clean_link = link.replace('\n', '').replace('\r', '').replace(' ', '')
        if len(clean_link) > 20 and ('@' in clean_link or '?' in clean_link or '//' in clean_link):
            processed_links.append(clean_link)
    
    return list(set(processed_links))

def extract_links_from_text(text_content):
    """从纯文本中提取分享链接"""
    links = []
    
    # 在文本中查找以协议开头的行
    lines = text_content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith(('vmess://', 'vless://', 'hysteria2://')):
            links.append(line)
    
    return links

def parse_vmess_url(url):
    try:
        if not url.startswith('vmess://'):
            return None
        
        data = url[8:]
        json_data = base64.b64decode(data).decode('utf-8')
        config = json.loads(json_data)
        
        return {
            'address': config.get('add', ''),
            'port': config.get('port', 0),
            'id': config.get('id', ''),
            'alterId': config.get('aid', 0),
            'security': config.get('scy', 'auto'),
            'network': config.get('net', 'tcp'),
            'type': config.get('net', 'tcp'),
            'host': config.get('host', ''),
            'path': config.get('path', ''),
            'tls': config.get('tls', ''),
            'sni': config.get('sni', ''),
            'ps': config.get('ps', 'VMess节点'),
            'headerType': config.get('type', 'none')
        }
    except Exception as e:
        print(f"解析VMess失败: {e}")
        return None

def parse_vless_url(url):
    try:
        if not url.startswith('vless://'):
            return None
        
        data = url[8:]
        parts = data.split('?')
        address_part = parts[0]
        params = parts[1] if len(parts) > 1 else ''
        
        # 处理HTML实体编码
        params = params.replace('&amp;', '&')
        
        address_parts = address_part.split('@')
        uuid = address_parts[0]
        server_part = address_parts[1]
        
        server_parts = server_part.split(':')
        address = server_parts[0]
        port = server_parts[1]
        
        param_dict = {}
        for param in params.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                param_dict[key] = value
        
        # 处理security参数，用于StreamSecurity字段
        stream_security = param_dict.get('security', 'none')
        
        return {
            'address': address,
            'port': int(port),
            'id': uuid,
            'security': param_dict.get('security', 'none'),
            'encryption': param_dict.get('encryption', 'none'),
            'type': param_dict.get('type', 'tcp'),
            'host': param_dict.get('host', ''),
            'path': param_dict.get('path', ''),
            'sni': param_dict.get('sni', ''),
            'ps': param_dict.get('ps', 'VLESS节点'),
            'flow': param_dict.get('flow', ''),
            'fingerprint': param_dict.get('fp', ''),
            'publicKey': param_dict.get('pbk', ''),
            'shortId': param_dict.get('sid', ''),
            'spiderX': param_dict.get('spx', '/'),
            'tls': stream_security
        }
    except Exception as e:
        print(f"解析VLESS失败: {e}")
        return None

def parse_hysteria2_url(url):
    try:
        if not url.startswith('hysteria2://'):
            return None
        
        data = url[12:]
        parts = data.split('?', 1)
        auth_part = parts[0]
        params = parts[1] if len(parts) > 1 else ''
        
        # 处理HTML实体编码
        params = params.replace('&amp;', '&')
        
        # 解析认证部分
        if '@' in auth_part:
            password, server_part = auth_part.split('@', 1)
        else:
            password = ''
            server_part = auth_part
        
        # 解析服务器和端口
        if ':' in server_part:
            server_parts = server_part.split(':', 1)
            address = server_parts[0]
            port = server_parts[1]
        else:
            address = server_part
            port = '80'
        
        # 解析参数
        param_dict = {}
        for param in params.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                param_dict[key] = value
        
        return {
            'address': address,
            'port': int(port),
            'id': password,
            'security': 'hysteria2',
            'type': 'hysteria2',
            'tls': 'tls',
            'ps': param_dict.get('name', 'Hysteria2节点'),
            'sni': param_dict.get('sni', ''),
            'insecure': param_dict.get('insecure', '0')
        }
    except Exception as e:
        print(f"解析Hysteria2失败: {e}")
        return None

def parse_trojan_url(url):
    try:
        if not url.startswith('trojan://'):
            return None
        
        data = url[9:]
        parts = data.split('#')
        server_part = parts[0]
        remarks = parts[1] if len(parts) > 1 else 'Trojan节点'
        
        if '@' in server_part:
            password, server_part = server_part.split('@', 1)
        
        if ':' in server_part:
            address, port = server_part.split(':', 1)
        else:
            address, port = server_part, '443'
        
        return {
            'address': address,
            'port': int(port),
            'id': password,
            'security': 'tls',
            'sni': address,
            'ps': remarks,
            'type': 'tcp'
        }
    except Exception as e:
        print(f"解析Trojan失败: {e}")
        return None

def add_server_to_db(config):
    db_path = os.path.join(os.path.dirname(__file__), 'guiConfigs', 'guiNDB.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(CAST(IndexId AS INTEGER)) FROM ProfileItem")
    result = cursor.fetchone()
    max_id = int(result[0]) if result[0] else 0
    new_id = str(max_id + 1)
    
    # 获取配置参数
    address = config.get('address', '')
    port = config.get('port', 0)
    remarks = config.get('ps', '未命名节点')
    security = config.get('security', 'none')
    network = config.get('type', 'tcp')
    id_value = config.get('id', '')
    alterId = config.get('alterId', 0)
    headerType = config.get('headerType', 'none')
    requestHost = config.get('host', '')
    path = config.get('path', '')
    streamSecurity = config.get('tls', '')
    allowInsecure = 0
    flow = config.get('flow', '')
    sni = config.get('sni', '')
    fingerprint = config.get('fingerprint', '')
    publicKey = config.get('publicKey', '')
    shortId = config.get('shortId', '')
    spiderX = config.get('spiderX', '')
    
    # Configuration type mapping
    config_type = 1
    if network == 'tcp':
        config_type = 1
    elif network == 'kcp':
        config_type = 2
    elif network == 'ws':
        config_type = 3
    elif network == 'http':
        config_type = 4
    elif network == 'grpc':
        config_type = 5
    elif network == 'xhttp':
        config_type = 5
    elif network == 'hysteria2':
        config_type = 7
    
    # Insert into database
    cursor.execute("""
        INSERT INTO ProfileItem (
            IndexId, ConfigType, ConfigVersion, Address, Port, 
            Id, AlterId, Security, Network, Remarks,
            HeaderType, RequestHost, Path, StreamSecurity, AllowInsecure,
            Flow, Sni, Fingerprint, PublicKey, ShortId, SpiderX,
            DisplayLog
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_id, config_type, 2, address, port,
        id_value, alterId, security, network, remarks,
        headerType, requestHost, path, streamSecurity, allowInsecure,
        flow, sni, fingerprint, publicKey, shortId, spiderX,
        1
    ))
    
    conn.commit()
    conn.close()
    
    print(f"节点已添加: {remarks}")
    print(f"  地址: {address}:{port}")
    print(f"  ID: {new_id}")
    return new_id

def copy_to_clipboard(text):
    """复制文本到剪贴板"""
    try:
        subprocess.run(f'echo "{text}" | clip', shell=True, check=True)
        return True
    except Exception as e:
        print(f"复制到剪贴板失败: {e}")
        return False

def main():
    target_url = 'https://alvin9999.com/v2ray免费账号'
    
    print(f"正在从网站获取节点地址...")
    print(f"目标网址: {target_url}")
    
    html_content = fetch_url_content(target_url)
    
    if not html_content:
        print("无法获取网页内容，尝试从剪贴板读取...")
        clipboard_content = get_clipboard_text()
        
        if not clipboard_content:
            print("剪贴板为空或读取失败")
            sys.exit(1)
        
        print(f"从剪贴板读取到内容: {clipboard_content[:100]}...")
        
        # 尝试从剪贴板内容中提取链接
        links = extract_links_from_text(clipboard_content)
        if not links:
            print("剪贴板中未找到有效的分享链接")
            sys.exit(1)
    else:
        print("网页内容获取成功，正在提取分享链接...")
        links = extract_links_from_html(html_content)
        
        if not links:
            print("未找到有效的分享链接")
            sys.exit(1)
        
        print(f"找到 {len(links)} 个分享链接")
    
    # 收集所有原始链接
    all_links = []
    added_count = 0
    
    for url in links:
        print(f"处理链接: {url[:80]}...")
        
        config = None
        
        if url.startswith('vmess://'):
            config = parse_vmess_url(url)
        elif url.startswith('vless://'):
            config = parse_vless_url(url)
        elif url.startswith('hysteria2://'):
            config = parse_hysteria2_url(url)
        else:
            print("  不支持的链接格式，跳过")
            continue
        
        if not config:
            print("  解析链接失败，跳过")
            continue
        
        # 只收集原始链接
        all_links.append(url)
        
        try:
            add_server_to_db(config)
            added_count += 1
            print("  节点添加成功")
        except Exception as e:
            print(f"  添加失败: {e}")
    
    # 将所有原始链接复制到剪贴板
    if all_links:
        all_links_text = "\n".join(all_links)
        
        if copy_to_clipboard(all_links_text):
            print(f"\n所有节点地址已复制到剪贴板！")
            print(f"包含 {len(all_links)} 个原始链接")
            print("\n剪贴板内容:")
            for link in all_links:
                print(f"  {link}")
        else:
            print(f"\n节点地址复制失败")
    
    print(f"\n完成！共添加 {added_count} 个节点到数据库")
    print("请在 v2rayN 中重新加载配置以查看新节点")

if __name__ == "__main__":
    main()
