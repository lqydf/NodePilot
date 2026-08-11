const nodesRoot = document.getElementById('nodes');
const navStatus = document.getElementById('navStatus');
const updatedAt = document.getElementById('updatedAt');
const candidateCount = document.getElementById('candidateCount');
const reachableCount = document.getElementById('reachableCount');
const subUrl = document.getElementById('subUrl');
const subStatus = document.getElementById('subStatus');
const copyBtn = document.getElementById('copyBtn');
const qrBtn = document.getElementById('qrBtn');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[ch]);
}

function renderNodes(nodes) {
  if (!nodes.length) {
    nodesRoot.innerHTML = '<div class="empty">本次扫描没有找到通过真实代理验证的节点。</div>';
    return;
  }
  nodesRoot.innerHTML = nodes.map(node => {
    const verified = node.verification === 'proxy_verified';
    const youtubeStatus = verified ? '通过' : '未验证';
    const youtubeClass = verified ? 'verified' : '';
    const connectionStatus = verified ? '代理可用' : 'TCP 可达';
    return `
    <article class="node-card">
      <div class="rank">#${node.rank}</div>
      <div>
        <div class="node-name">${escapeHtml(node.region || '未知地区')}</div>
        <div class="node-region">NodePilot 自动筛选</div>
      </div>
      <div class="metric"><div class="metric-label">延迟</div><div class="metric-value">${Number(node.latency_ms).toFixed(1)} ms</div></div>
      <div class="metric"><div class="metric-label">状态</div><div class="metric-value">${connectionStatus}</div></div>
      <div class="metric"><div class="metric-label">速度</div><div class="metric-value">${node.download_mbps == null ? '未测' : `${Number(node.download_mbps).toFixed(1)} Mbps`}</div></div>
      <div class="metric"><div class="metric-label">YouTube</div><div class="metric-value ${youtubeClass}">${youtubeStatus}</div></div>
      <div class="score">${node.rank}<small> / 10</small></div>
    </article>
  `;
  }).join('');
}

function setupSubscription() {
  const url = new URL('./sub/top10.txt', window.location.href).href;
  subUrl.textContent = url;
  copyBtn.disabled = false;
  qrBtn.disabled = false;
  subStatus.textContent = '订阅地址只包含 NodePilot 自动验证后的 TOP 10。节点详细地址不会在网页公开展示。';
}

async function loadSnapshot() {
  try {
    const response = await fetch(`./data/live.json?ts=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const nodes = Array.isArray(data.top10) ? data.top10 : [];
    renderNodes(nodes);
    updatedAt.textContent = `最后更新：${data.generated_at || '未知'}`;
    candidateCount.textContent = `候选节点：${data.summary?.candidates ?? 0}`;
    reachableCount.textContent = `TCP 可达：${data.summary?.reachable ?? 0}`;
    const verified = Number(data.summary?.proxy_verified ?? 0);
    navStatus.innerHTML = verified > 0
      ? `<span class="dot"></span> 已验证 ${verified} 个可用节点`
      : '<span class="dot"></span> 正在等待真实代理验证';
    setupSubscription();
  } catch (error) {
    nodesRoot.innerHTML = '<div class="empty">真实数据暂时不可用，请稍后刷新。</div>';
    navStatus.innerHTML = '<span class="dot"></span> 数据加载失败';
    subStatus.textContent = '当前没有可用的实时扫描快照。';
    console.error(error);
  }
}

document.getElementById('refreshBtn').addEventListener('click', () => window.location.reload());

copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(subUrl.textContent);
    copyBtn.textContent = '已复制';
    setTimeout(() => { copyBtn.textContent = '复制地址'; }, 1200);
  } catch {
    copyBtn.textContent = '复制失败';
  }
});

const qrModal = document.getElementById('qrModal');
const qrContainer = document.getElementById('qrcode');
const qrUrl = document.getElementById('qrUrl');

qrBtn.addEventListener('click', () => {
  const text = subUrl.textContent.trim();
  qrContainer.innerHTML = '';
  qrUrl.textContent = text;
  if (!window.QRCode) {
    qrUrl.textContent = '二维码组件加载失败，请刷新页面重试';
    return;
  }
  new QRCode(qrContainer, { text, width: 220, height: 220, correctLevel: QRCode.CorrectLevel.M });
  qrModal.hidden = false;
});

document.getElementById('qrClose').addEventListener('click', () => { qrModal.hidden = true; });
qrModal.addEventListener('click', event => { if (event.target === qrModal) qrModal.hidden = true; });
document.addEventListener('keydown', event => { if (event.key === 'Escape') qrModal.hidden = true; });

loadSnapshot();
