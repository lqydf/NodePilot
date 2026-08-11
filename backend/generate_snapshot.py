#!/usr/bin/env python3
import asyncio
import aiohttp
import base64
import re
import json
import os

# ==================== 配置区 ====================
SOURCES = [
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/yaney01/autoproxy/master/ss.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2ray-ssr/master/ss"
]

OUTPUT_JSON = "frontend/data/live.json"
OUTPUT_TXT = "frontend/data/top10.txt"
TCP_TIMEOUT = 5.0  # 从 2.5 秒延长到 5 秒，提高握手成功率
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
    except Exception as e:
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
                # 只抓 ss:// 开头的链接
                found = re.findall(r'ss://[^\s]+', text)
                all_uris.extend(found)
        return list(set(all_uris))

async def main():
    print("🚀 NodePilot 真实探测定时任务启动...")
    
    # ⭐ 关键修复：提前创建目录，确保 git add 永远能找到路径
    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)

    uris = await fetch_sources()
    print(f"📡 抓取到 {len(uris)} 条 ss:// 链接")
    
    if not uris:
        print("⚠️ 没有抓到任何 ss:// 链接，可能数据源已失效或全是 vmess/trojan 格式")
        # 写入空文件，让工作流能继续提交（虽然空，但目录存在）
        with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
            f.write("# 暂无可用 ss 节点\n")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return

    node_map = {}
    for uri in uris:
        info = decode_ss_uri(uri)
        if info:
            key = f"{info['host']}:{info['port']}"
            if key not in node_map:
                node_map[key] = info

    candidates = list(node_map.values())
    print(f"🔍 解析出 {len(candidates)} 个不重复节点，开始TCP端口存活探测（超时 {TCP_TIMEOUT}秒）...")

    if not candidates:
        print("⚠️ 解析出的节点为空，可能 ss:// 格式不标准")
        with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
            f.write("# 解析失败\n")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return

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

    # 写入订阅文件（即使为空也写）
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        if alive_nodes:
            for node in alive_nodes[:10]:
                user_pass = f"{node['method']}:{node['password']}"
                encoded = base64.b64encode(user_pass.encode()).decode()
                uri = f"ss://{encoded}@{node['host']}:{node['port']}#{node['name']}"
                f.write(uri + "\n")
        else:
            f.write("# 未探测到存活节点\n")
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(alive_nodes[:10], f, indent=2, ensure_ascii=False)
    
    print(f"📝 订阅文件已生成: {OUTPUT_TXT}")
    print(f"📝 JSON文件已生成: {OUTPUT_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
