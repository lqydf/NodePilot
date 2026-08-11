#!/usr/bin/env python3
"""
NodePilot 真实节点探测脚本（完整版）
功能：从公共源抓取 ss:// 链接，通过 TCP 握手验证端口存活，生成订阅文件
可自定义：保底节点、超时时间、数据源列表
"""

import asyncio
import aiohttp
import base64
import re
import json
import os

# ============================================
# 用户可配置区
# ============================================

# 数据源列表（优先公共源，最后可加保底节点）
SOURCES = [
    # 公共源（2026-08-12 验证可访问）
    "https://raw.githubusercontent.com/justchoking/free-ss/main/ss.txt",
    "https://raw.githubusercontent.com/freefq/free/master/ss",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/ss",
    "https://raw.githubusercontent.com/linyingong/Free-Sub/main/ss.txt",
    
    # 保底节点（手动注入，确保至少有一个可用）
    # 如果你有自己确认可用的 ss:// 链接，请取消下面一行的注释，并替换为你的真实链接
    # "ss://YOUR_BASE64_ENCODED@your-server:port#name",
]

TCP_TIMEOUT = 8.0          # TCP 握手超时（秒），亚洲访问欧美节点建议 8 秒
OUTPUT_JSON = "frontend/data/live.json"
OUTPUT_TXT  = "frontend/data/top10.txt"
MAX_NODES   = 10           # 最终输出的节点数量

# ============================================

def decode_ss_uri(uri):
    """解析 ss:// 链接，提取 host, port, method, password"""
    try:
        if not uri.startswith("ss://"):
            return None
        # 去除可能的额外空白
        uri = uri.strip()
        # 分割 user:pass 部分和 host:port 部分
        parts = uri[5:].split("@")
        if len(parts) != 2:
            return None
        user_pass_b64 = parts[0]
        # 补齐 Base64 填充
        user_pass_b64 += "=" * (4 - len(user_pass_b64) % 4)
        user_pass = base64.b64decode(user_pass_b64).decode('utf-8')
        method, password = user_pass.split(":", 1)
        # host:port 可能带有 #tag 或 ?plugin 等，需要去除
        host_port = parts[1].split("#")[0].split("?")[0]
        host, port = host_port.split(":")
        return {
            "host": host,
            "port": int(port),
            "method": method,
            "password": password,
            "name": f"{host}:{port}"
        }
    except Exception as e:
        # 打印解析失败的信息（便于调试）
        # print(f"解析失败: {uri} -> {e}")
        return None

async def tcp_is_alive(host, port):
    """纯 TCP 三次握手，握手成功即为端口存活"""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=TCP_TIMEOUT
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

async def fetch_sources():
    """并发抓取所有数据源，返回去重后的 ss:// URI 列表"""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
        tasks = [session.get(url) for url in SOURCES]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_uris = []
        for resp in responses:
            if isinstance(resp, Exception):
                print(f"⚠️ 抓取失败: {resp}")
                continue
            if resp.status == 200:
                text = await resp.text()
                # 正则匹配所有 ss:// 开头的链接
                found = re.findall(r'ss://[^\s]+', text)
                all_uris.extend(found)
                print(f"✅ 从 {resp.url} 获取到 {len(found)} 条链接")
            else:
                print(f"⚠️ 数据源 {resp.url} 返回状态码 {resp.status}")
        # 去重并返回
        return list(set(all_uris))

async def main():
    print("🚀 NodePilot 真实节点探测启动")
    print(f"⏱️  TCP 超时设置为 {TCP_TIMEOUT} 秒")
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)

    # 1. 抓取原始 URI
    uris = await fetch_sources()
    print(f"📡 总共抓取到 {len(uris)} 条 ss:// 链接（去重后）")
    
    if not uris:
        print("⚠️ 没有任何 ss:// 链接，可能数据源全部失效或内容格式不符")
        # 写入占位文件，避免前端空白
        with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
            f.write("# 暂无可用 ss 节点\n")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return

    # 2. 解析并去重（按 host:port 去重）
    node_map = {}
    for uri in uris:
        info = decode_ss_uri(uri)
        if info:
            key = f"{info['host']}:{info['port']}"
            if key not in node_map:
                node_map[key] = info

    candidates = list(node_map.values())
    print(f"🔍 解析出 {len(candidates)} 个不重复节点，开始 TCP 端口存活探测...")

    if not candidates:
        print("⚠️ 解析出的节点为空，请检查 ss:// 链接格式是否正确")
        with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
            f.write("# 解析失败，请检查数据源格式\n")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return

    # 3. 并发 TCP 握手
    tasks = [tcp_is_alive(node['host'], node['port']) for node in candidates]
    results = await asyncio.gather(*tasks)

    alive_nodes = []
    for idx, is_alive in enumerate(results):
        if is_alive:
            node = candidates[idx]
            node['latency'] = 1   # 占位值，后续可改为真实延迟
            alive_nodes.append(node)
            print(f"✅ 存活: {node['host']}:{node['port']} ({node['method']})")

    print(f"🎯 探测完成！存活节点数量: {len(alive_nodes)}")

    # 4. 输出订阅文件（最多 MAX_NODES 个）
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        if alive_nodes:
            for node in alive_nodes[:MAX_NODES]:
                user_pass = f"{node['method']}:{node['password']}"
                encoded = base64.b64encode(user_pass.encode()).decode()
                uri = f"ss://{encoded}@{node['host']}:{node['port']}#{node['name']}"
                f.write(uri + "\n")
        else:
            f.write("# 未探测到存活节点\n")
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(alive_nodes[:MAX_NODES], f, indent=2, ensure_ascii=False)
    
    print(f"📝 订阅文件已生成: {OUTPUT_TXT}")
    print(f"📝 JSON 文件已生成: {OUTPUT_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
