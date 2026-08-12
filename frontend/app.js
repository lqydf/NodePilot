const nodesRoot = document.getElementById('nodes');
const navStatus = document.getElementById('navStatus');
const updatedAt = document.getElementById('updatedAt');
const candidateCount = document.getElementById('candidateCount');
const reachableCount = document.getElementById('reachableCount');
const subUrl = document.getElementById('subUrl');
const subStatus = document.getElementById('subStatus');
const copyBtn = document.getElementById('copyBtn');
const qrBtn = document.getElementById('qrBtn');
const sourceUrl = document.getElementById('sourceUrl');
const addSourceBtn = document.getElementById('addSourceBtn');
const sourceMessage = document.getElementById('sourceMessage');
const sourceList = document.getElementById('sourceList');
const SOURCE_KEY = 'nodepilot.testSources.v1';

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[ch]);
}

function renderNodes(nodes) {
  if (!nodes.length) {
    nodesRoot.innerHTML = '<div class="empty">当前没有通过质量标准的真实测试结果。</div>';
    return;
  }
  const ranked = [...nodes].sort((a, b) => Number(a.latency_ms ?? Infinity) - Number(b.latency_ms ?? Infinity)).slice(0, 10);
  nodesRoot.innerHTML = ranked.map((node, index) => `
    <article class="node-card">
      <div class="rank">#${index + 1}</div>
      <div>
        <div class="node-name">${escapeHtml(node.region || node.name || '测试端点')}</div>
        <div class="node-region">真实网络质量测量</div>
      </div>
      <div class="metric"><div class="metric-label">延迟</div><div class="metric-value">${Number(node.latency_ms ?? 0).toFixed(1)} ms</div></div>
      <div class="metric"><div class="metric-label">状态</div><div class="metric-value">${escapeHtml(node.status || '可达')}</div></div>
      <div class="metric"><div class="metric-label">速度</div><div class="metric-value">${node.download_mbps == null ? '未测' : `${Number(node.download_mbps).toFixed(1)} Mbps`}</div></div>
      <div class="metric"><div class="metric-label">TTFB</div><div class="metric-value">${node.ttfb_ms == null ? '未测' : `${Number(node.ttfb_ms).toFixed(0)} ms`}</div></div>
      <div class="score">${index + 1}<small> / ${Math.min(10, ranked.length)}</small></div>
    </article>
  `).join('');
}

function getSources() {
  try { return JSON.parse(localStorage.getItem(SOURCE_KEY) || '[]'); } catch { return []; }
}

function saveSources(sources) { localStorage.setItem(SOURCE_KEY, JSON.stringify(sources)); }

function renderSources() {
  const sources = getSources();
  if (!sources.length) {
    sourceList.innerHTML = '<div class="source-empty">还没有添加自定义测试源。</div>';
    return;
  }
  sourceList.innerHTML = sources.map((item, index) => `
    <div class="source-item">
      <div><strong>${escapeHtml(item.url)}</strong><div class="source-meta">${escapeHtml(item.status || '已保存')} · ${escapeHtml(item.addedAt || '')}</div></div>
      <button type="button" data-remove-source="${index}">删除</button>
    </div>
  `).join('');
  sourceList.querySelectorAll('[data-remove-source]').forEach(button => {
    button.addEventListener('click', () => {
      const next = getSources().filter((_, i) => i !== Number(button.dataset.removeSource));
      saveSources(next);
      renderSources();
    });
  });
}

function addTestSource() {
  const value = sourceUrl.value.trim();
  let parsed;
  try { parsed = new URL(value); } catch { sourceMessage.textContent = '请输入有效的 HTTP/HTTPS 地址。'; return; }
  if (!['http:', 'https:'].includes(parsed.protocol)) { sourceMessage.textContent = '只支持 HTTP/HTTPS 测试地址。'; return; }
  const sources = getSources();
  if (sources.some(item => item.url === parsed.href)) { sourceMessage.textContent = '这个测试源已经添加。'; return; }
  sources.unshift({ url: parsed.href, status: '待测试', addedAt: new Date().toLocaleString('zh-CN') });
  saveSources(sources.slice(0, 20));
  sourceUrl.value = '';
  sourceMessage.textContent = '已保存。当前页面版本不会把该地址转换成代理节点，仅用于后续普通 HTTP/HTTPS 质量测试。';
  renderSources();
}

function setupSubscription() {
  const url = new URL('./sub/top10.txt', window.location.href).href;
  subUrl.textContent = url;
  copyBtn.disabled = false;
  qrBtn.disabled = false;
  subStatus.textContent = '当前结果地址。';
}

async function loadSnapshot() {
  try {
    const response = await fetch(`./data/live.json?ts=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const nodes = Array.isArray(data.top10) ? data.top10 : [];
    renderNodes(nodes);
    updatedAt.textContent = `最后更新：${data.generated_at || '未知'}`;
    candidateCount.textContent = `候选：${data.summary?.candidates ?? 0}`;
    reachableCount.textContent = `可达：${data.summary?.reachable ?? 0}`;
    const verified = Number(data.summary?.proxy_verified ?? 0);
    navStatus.innerHTML = verified > 0
      ? `<span class="dot"></span> 已有 ${verified} 个真实验证结果`
      : '<span class="dot"></span> 等待真实质量数据';
    setupSubscription();
  } catch (error) {
    nodesRoot.innerHTML = '<div class="empty">真实数据暂时不可用，请稍后刷新。</div>';
    navStatus.innerHTML = '<span class="dot"></span> 数据加载失败';
    subStatus.textContent = '当前没有可用的实时数据。';
    console.error(error);
  }
}

document.getElementById('refreshBtn').addEventListener('click', () => window.location.reload());
addSourceBtn.addEventListener('click', addTestSource);
sourceUrl.addEventListener('keydown', event => { if (event.key === 'Enter') addTestSource(); });
renderSources();

copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(subUrl.textContent);
    copyBtn.textContent = '已复制';
    setTimeout(() => { copyBtn.textContent = '复制地址'; }, 1200);
  } catch { copyBtn.textContent = '复制失败'; }
});

const qrModal = document.getElementById('qrModal');
const qrContainer = document.getElementById('qrcode');
const qrUrl = document.getElementById('qrUrl');
qrBtn.addEventListener('click', () => {
  const text = subUrl.textContent.trim();
  qrContainer.innerHTML = '';
  qrUrl.textContent = text;
  if (!window.QRCode) { qrUrl.textContent = '二维码组件加载失败，请刷新页面重试'; return; }
  new QRCode(qrContainer, { text, width: 220, height: 220, correctLevel: QRCode.CorrectLevel.M });
  qrModal.hidden = false;
});
document.getElementById('qrClose').addEventListener('click', () => { qrModal.hidden = true; });
qrModal.addEventListener('click', event => { if (event.target === qrModal) qrModal.hidden = true; });
document.addEventListener('keydown', event => { if (event.key === 'Escape') qrModal.hidden = true; });

loadSnapshot();
