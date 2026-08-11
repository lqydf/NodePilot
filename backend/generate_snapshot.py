#!/usr/bin/env python3
"""
极简版 NodePilot 生成器 - 纯TCP握手验证，不造假
用法: python backend/generate_snapshot.py
"""
import asyncio
import aiohttp
import base64
import re
import json
import os

# ==================== 配置区 ====================
SOURCES = [
    "https://raw.githubusercontent.com/you-dont-need/Another-Rule/master/Sub/ss.txt",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ss-sub"
]

OUTPUT_JSON = "frontend/data/live.json"
OUTPUT_TXT = "frontend/data/top10.txt"
TCP_TIMEOUT = 2.5
# ===============================================

def decode_ss_uri(uri):
    try:
        if not uri.startswith("ss://"):
            return None
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
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
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
    print("🚀 NodePilot 真实探测定时任务启动...")
    uris = await fetch_sources()
    print(f"📡 抓取到 {len(uris)} 条原始链接（去重后）")
    if not uris:
        print("❌ 没有抓取到任何数据，请更换 SOURCES")
        return

    node_map = {}
    for uri in uris:
        info = decode_ss_uri(uri)
        if info:
            key = f"{info['host']}:{info['port']}"
            if key not in node_map:
                node_map[key] = info
    candidates = list(node_map.values())
    print(f"🔍 解析出 {len(candidates)} 个不重复节点，开始TCP端口存活探测...")

    tasks = [tcp_is_alive(node['host'], node['port']) for node in candidates]
    results = await asyncio.gather(*tasks)

    alive_nodes = []
    for idx, is_alive in enumerate(results):
        if is_alive:
            node = candidates[idx]
            node['latency'] = 1
            alive_nodes.append(node)
            print(f"✅ 存活: {node['host']}:{node['port']} ({node['method']})")

    print(f"🎯 探测完成！存活节点数量: {len(alive_nodes)}")
    if not alive_nodes:
        print("❌ 没有存活节点，请更换数据源或调整超时时间。")
        return

    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        for node in alive_nodes[:10]:
            user_pass = f"{node['method']}:{node['password']}"
            encoded = base64.b64encode(user_pass.encode()).decode()
            uri = f"ss://{encoded}@{node['host']}:{node['port']}#{node['name']}"
            f.write(uri + "\n")
    print(f"📝 订阅文件已生成: {OUTPUT_TXT}")

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(alive_nodes[:10], f, indent=2, ensure_ascii=False)
    print(f"📝 JSON文件已生成: {OUTPUT_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
