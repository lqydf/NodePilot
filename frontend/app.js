const nodes = [
  {rank:1,flag:'🇯🇵',name:'Tokyo Premium 01',region:'日本 · 东京',latency:62,speed:86,loss:0.6,stable:99.2,score:96},
  {rank:2,flag:'🇭🇰',name:'Hong Kong Fast 03',region:'中国香港',latency:74,speed:79,loss:0.8,stable:98.7,score:94},
  {rank:3,flag:'🇸🇬',name:'Singapore Edge 02',region:'新加坡',latency:88,speed:72,loss:0.9,stable:98.4,score:92},
  {rank:4,flag:'🇯🇵',name:'Tokyo Stable 08',region:'日本 · 东京',latency:91,speed:68,loss:1.0,stable:98.1,score:91},
  {rank:5,flag:'🇰🇷',name:'Seoul Connect 01',region:'韩国 · 首尔',latency:96,speed:64,loss:1.1,stable:97.8,score:89},
  {rank:6,flag:'🇭🇰',name:'Hong Kong Core 07',region:'中国香港',latency:103,speed:61,loss:1.2,stable:97.5,score:88},
  {rank:7,flag:'🇸🇬',name:'Singapore Fast 05',region:'新加坡',latency:112,speed:58,loss:1.3,stable:97.2,score:87},
  {rank:8,flag:'🇯🇵',name:'Osaka Line 04',region:'日本 · 大阪',latency:119,speed:55,loss:1.4,stable:96.9,score:86},
  {rank:9,flag:'🇰🇷',name:'Busan Route 02',region:'韩国 · 釜山',latency:128,speed:51,loss:1.5,stable:96.4,score:84},
  {rank:10,flag:'🇹🇼',name:'Taipei Route 06',region:'中国台湾',latency:137,speed:48,loss:1.7,stable:95.9,score:82}
];

function render(){
  const root=document.getElementById('nodes');
  root.innerHTML=nodes.map(n=>`<article class="node-card">
    <div class="rank">#${n.rank}</div>
    <div><div class="node-name">${n.flag} ${n.name}</div><div class="node-region">${n.region}</div></div>
    <div class="metric"><div class="metric-label">延迟</div><div class="metric-value">${n.latency} ms</div></div>
    <div class="metric"><div class="metric-label">下载</div><div class="metric-value">${n.speed} Mbps</div></div>
    <div class="metric"><div class="metric-label">丢包</div><div class="metric-value">${n.loss}%</div></div>
    <div class="metric"><div class="metric-label">稳定性</div><div class="metric-value">${n.stable}%</div></div>
    <div class="score">${n.score}<small>/ 100</small></div>
  </article>`).join('');
}

document.getElementById('refreshBtn').addEventListener('click',()=>{
  const btn=document.getElementById('refreshBtn');
  btn.textContent='已刷新';
  setTimeout(()=>btn.textContent='刷新排名',1000);
});

document.getElementById('copyBtn').addEventListener('click',async()=>{
  const text=document.getElementById('subUrl').textContent;
  try{await navigator.clipboard.writeText(text)}catch{}
  document.getElementById('copyBtn').textContent='已复制';
  setTimeout(()=>document.getElementById('copyBtn').textContent='复制地址',1200);
});

const qrModal=document.getElementById('qrModal');
const qrContainer=document.getElementById('qrcode');
const qrUrl=document.getElementById('qrUrl');

document.getElementById('qrBtn').addEventListener('click',()=>{
  const text=document.getElementById('subUrl').textContent.trim();
  qrContainer.innerHTML='';
  qrUrl.textContent=text;
  if(window.QRCode){
    new QRCode(qrContainer,{text,width:220,height:220,correctLevel:QRCode.CorrectLevel.M});
    qrModal.hidden=false;
  }else{
    qrUrl.textContent='二维码组件加载失败，请稍后重试';
  }
});

document.getElementById('qrClose').addEventListener('click',()=>{qrModal.hidden=true;});
qrModal.addEventListener('click',(event)=>{if(event.target===qrModal)qrModal.hidden=true;});

document.addEventListener('keydown',(event)=>{if(event.key==='Escape')qrModal.hidden=true;});

render();
