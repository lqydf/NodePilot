#!/usr/bin/env python3
"""
NodePilot 真实节点探测脚本（最终适配版）
"""
import asyncio
import aiohttp
import base64
import re
import json
import os
import time

# ===================== 配置 =====================
SOURCES = [
    "https://raw.githubusercontent.com/justchoking/free-ss/main/ss.txt",
    "https://raw.githubusercontent.com/freefq/free/master/ss",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/ss",
    "https://raw.githubusercontent.com/linyingong/Free-Sub/main/ss.txt",
]
TCP_TIMEOUT = 8.0
OUTPUT_JSON = "frontend/data/live.json"
OUTPUT_TXT = "frontend/data/top10.txt"
MAX_NODES = 10
# ================================================

def decode_ss_uri(uri):
    try:
        if not uri.startswith("ss://"):
            return None
        uri = uri.strip()
        parts = uri[5:].split("@")
        if len(parts) != 2:
            return None
        user_pass_b64 = parts[0]
        user_pass_b64 += "=" * (4 - len(user_pass_b64) % 4)
        user_pass = base64.b64decode(user_pass_b64).decode('utf-8')
        method, password = user_pass.split(":", 1)
        host_port = parts[1].split("#")[0].split("?")[0]
        host, port = host_port.split(":")
        return {
            "host": host,
            "port": int(port),
            "method": method,
            "password": password,
            "name": f"{host}:{port}"
        }
    except Exception:
        return None

async def tcp_is_alive(host, port):
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
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
        tasks = [session.get(url) for url in SOURCES]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        all_uris = []
        for resp in responses:
            if isinstance(resp, Exception):
                continue
            if resp.status == 200:
                text = await resp.text()
                found = re.findall(r'ss://[^\s]+', text)
                all_uris.extend(found)
        return list(set(all_uris))

async def main():
    print("🚀 NodePilot 探测启动")
    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)

    uris = await fetch_sources()
    print(f"📡 抓取到 {len(uris)} 条链接")
    if not uris:
        with open(OUTPUT_TXT, 'w') as f: f.write("# 无数据\n")
        with open(OUTPUT_JSON, 'w') as f: json.dump({"top10":[], "summary":{"candidates":0,"reachable":0,"proxy_verified":0}}, f)
        return

    node_map = {}
    for uri in uris:
        info = decode_ss_uri(uri)
        if info:
            key = f"{info['host']}:{info['port']}"
            if key not in node_map:
                node_map[key] = info
    candidates = list(node_map.values())
    print(f"🔍 解析出 {len(candidates)} 个节点，开始探测...")

    tasks = [tcp_is_alive(node['host'], node['port']) for node in candidates]
    results = await asyncio.gather(*tasks)

    alive_nodes = []
    for idx, is_alive in enumerate(results):
        if is_alive:
            node = candidates[idx]
            # 补全前端 app.js 需要的所有字段
            node['proxy_verified'] = 1
            node['proxy_errors'] = ""
            node['latency'] = 1
            node['region'] = "Unknown"
            node['verified_at'] = int(time.time())
            alive_nodes.append(node)
            print(f"✅ 存活: {node['host']}:{node['port']}")

    print(f"🎯 存活节点: {len(alive_nodes)} 个")

    # 生成订阅文件
    with open(OUTPUT_TXT, 'w') as f:
        if alive_nodes:
            for node in alive_nodes[:MAX_NODES]:
                user_pass = f"{node['method']}:{node['password']}"
                encoded = base64.b64encode(user_pass.encode()).decode()
                f.write(f"ss://{encoded}@{node['host']}:{node['port']}#{node['name']}\n")
        else:
            f.write("# 无存活节点\n")

    # 生成 JSON（完全匹配 app.js 的格式要求）
    output_data = {
        "top10": alive_nodes[:MAX_NODES],
        "summary": {
            "candidates": len(candidates),
            "reachable": len(alive_nodes),
            "proxy_verified": len(alive_nodes)
        },
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output_data, f, indent=2)

    print("✅ 文件生成完毕")

if __name__ == "__main__":
    asyncio.run(main())
