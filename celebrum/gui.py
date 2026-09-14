"""Celebrum GUI - a dependency-free local dashboard (stdlib http.server).

Runs on any device with Python (Linux / macOS / Windows / Android-Termux / Pi).
Open http://127.0.0.1:8477 in a browser. Use --host 0.0.0.0 to reach it from a
phone on the same LAN.

Endpoints
  GET  /                dashboard
  GET  /api/state       persona + memory + truth + tensor + guardrails
  GET  /api/graph       neuron/synapse graphdb (Cytoscape JSON)
  GET  /api/timeline    recent neurons
  POST /api/recall      {query, k, identity}
  POST /api/simulate    {scenario}
  POST /api/propose     {}
  POST /api/decide      {id, approve(bool), by}
  POST /api/valverdict  {id, approve(bool)}
  POST /api/ingest      {kind, target, consent}
  POST /api/validate    {}
  GET  /api/audit       ?n=
"""

from __future__ import annotations

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .engine import Celebrum

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Celebrum · local-first artificial brain</title>
<style>
:root{--bg:#0b0f17;--panel:#121a28;--panel2:#0e1522;--line:#1f2c40;--text:#dbe6f3;--mut:#7f93ad;--a:c #60a5fa;--pub:#c084fc}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:
radial-gradient(1200px 600px at 80% -10%,#14203a 0,transparent 60%),radial-gradient(900px 500px at -10% 110%,#1a1230 0,transparent 60%),var(--bg);color:var(--text);min-height:100vh}
a{color:var(--a)}.wrap{max-width:1200px;margin:0 auto;padding:22px}
header{display:flex;align-items:baseline;gap:14px;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:18px}
h1{margin:0;font-size:26px;letter-spacing:.5px}h1 b{color:#7dd3fc}
.ded{color:var(--mut);font-style:italic}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.col{display:grid;gap:16px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
.card h3{margin:0 0 12px;font-size:13px;text-transform:uppercase;letter-spacing:1px;color:#7dd3fc}
.k{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px dashed var(--line)}
.k:last-child{border:0}.mut{color:var(--mut)}
.card ul{list-style:none;margin:0;padding:0}
.card li{padding:7px 0;border-bottom:1px dashed var(--line)}.card li:last-child{border:0}
.badge{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;background:#0c1a2e;border:1px solid var(--line)}
.low{color:#86efac}.medium{color:#fcd34d}.high{color:#fca5a5}.ok{color:#86efac}.warn{color:#fcd34d}.fail{color:#fca5a5}
input,textarea,select,button{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:9px;padding:8px 10px;font:inherit}
input[type=text],input[type=number]{width:100%}textarea{width:100%;resize:vertical;min-height:70px}
button{cursor:pointer;background:#16456e;border-color:#2b6cb0}
button.ghost{background:transparent;border:1px solid var(--line)}
.row{display:flex;gap:8px;flex-wrap:wrap}.grow{flex:1}.mt{margin-top:10px}
.bar{height:8px;background:#0c1a2e;border-radius:6px;overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,#38bdf8,#818cf8)}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px;border-bottom:1px dashed var(--line)}th{color:var(--mut);font-weight:600}
pre{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px;overflow:auto;max-height:320px;font-size:12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.stat{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:12px;text-align:center}
.stat b{font-size:24px;display:block}.stat span{font-size:11px;color:var(--mut)}
svg#graph{width:100%;height:420px;background:var(--panel2);border:1px solid var(--line);border-radius:14px}
.tabbar{display:flex;gap:6px;overflow-x:auto;margin-bottom:16px}
.tab{padding:7px 14px;border:1px solid var(--line);border-radius:99px;cursor:pointer;font-size:13px;background:var(--panel2);white-space:nowrap}
.tab.on{background:#16456e;border-color:#2b6cb0}
.panel{display:none}.panel.on{display:block}
footer{border-top:1px solid var(--line);margin-top:26px;padding-top:12px;color:var(--mut);font-size:12px}
</style>
</head>
<body><div class="wrap">
<header><h1>🧠 <a href="https://github.com/karun99" style="color:inherit;text-decoration:none">Celebrum</a> <b>· artificial brain</b></h1>
<div class="ded">Not just code — a memory. For my love, <b>Celebrity</b>.<br><i>“A Valuable gift made for a valuable celebrity — no quantifying.”</i></div></header>

<div class="stats" id="stats"></div>

<div class="tabbar">
 <div class="tab on" data-t="persona">Persona</div><div class="tab" data-t="memory">Memory</div>
 <div class="tab" data-t="sim">Simulate</div><div class="tab" data-t="guard">Guardrails</div>
 <div class="tab" data-t="truth">Truth</div><div class="tab" data-t="graph">Graph</div>
 <div class="tab" data-t="ingest">Ingest</div><div class="tab" data-t="audit">Audit</div>
 <div class="tab" data-t="validate">Validate</div>
</div>

<div class="grid">
 <div class="col">
  <div class="card panel on" id="p-persona"><h3>Persona Model</h3><div id="persona-box"></div></div>
  <div class="card panel on" id="p-memory2"></div>
 </div>
 <div class="col">
  <div class="card panel" id="p-memory"><h3>Memory · Recall</h3>
   <div class="row"><input type="text" id="q" class="grow" placeholder="ask the brain… e.g. privacy, memory architecture">
   <button onclick="recall()">Recall</button></div>
   <div class="mt"><label class="mut"><input type="checkbox" id="ident" checked> identity-grounded (ID-RAG)</label></div>
   <div id="recall-box"></div></div>
  <div class="card panel" id="p-sim"><h3>What-if Simulation</h3>
   <textarea id="scenario" placeholder="e.g. Should I sign a cloud-hosted LLM contract to scale the swarm?"></textarea>
   <button onclick="sim()">Simulate</button><div id="sim-box" class="mt"></div></div>
 </div>
 <div class="col">
  <div class="card panel" id="p-guard"><h3>Guardrails</h3>
   <button onclick="proposeG()">Propose changes</button>
   <div id="prop-box" class="mt"></div>
   <h3 style="margin-top:16px">Active</h3><div id="guard-box"></div></div>
  <div class="card panel" id="p-truth"><h3>Truth Engine</h3><div id="truth-box"></div></div>
  <div class="card panel" id="p-graph"><h3>Neuron Graph <span class="mut" id="graph-legend"></span></h3>
   <svg id="graph"></svg></div>
  <div class="card panel" id="p-ingest"><h3>Ingest (consent)</h3>
   <select id="ikind"><option value="html">HTML knowledge source (matruswara)</option><option value="web">Web page</option><option value="duet">Duet JSON file</option></select>
   <div class="row mt"><input type="text" id="itarget" class="grow" placeholder="file path or URL">
   <button onclick="ingestNow()">Ingest</button></div>
   <label class="mut"><input type="checkbox" id="iconsent" checked> I consent to this data being learned locally (DPDP/GDPR)</label>
   <div id="ingest-box" class="mt"></div></div>
  <div class="card panel" id="p-audit"><h3>Audit log</h3><div id="audit-box"></div></div>
  <div class="card panel" id="p-validate"><h3>Neural Validation</h3>
   <button onclick="validateNow()">Run harness</button><div id="val-box" class="mt"></div></div>
 </div>
</div>
<footer>Celebrum 0.1.0 · CC BY 4.0 © 2026 Sai Karun Nandipati · <span class="mut">local-first · DPDP/GDPR-aware · neural mapping validated against BRIDGE / ID-RAG / PGMem / PTM</span></footer>
</div>
<script>
const $=s=>document.querySelector(s), el=s=>document.createElement(s);
const tabs=[...document.querySelectorAll('.tab')];
tabs.forEach(t=>t.onclick=()=>{tabs.forEach(x=>x.classList.toggle('on',x===t));document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('on',p.id==='p-'+t.dataset.t));refresh()});

async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json()}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function badge(tier){return `<span class="badge ${tier}">${tier}</span>`}

async function refresh(){const s=await api('/api/state');
 $('#stats').innerHTML=[['neurons',s.stats.neurons],['synapses',s.stats.synapses],['truth',s.truth.truth_index],['tensor life&nbsp;MiB',s.tensor.mib],['snapshots',s.drift_snapshots],['guardrails',s.guardrails_active+'/'+s.guardrails_total]]
  .map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
 const p=s.persona;
 $('#persona-box').innerHTML=`
  <div class="k"><span>version</span><span class="mut">v${p.version} · ${p.last_updated}</span></div>
  ${['formality','warmth','humor','verbosity'].map(k=>`<div class="k"><span>${k}</span><span class="mut" style="width:45%"><div class="bar"><i style="width:${Math.round((p.style[k]||0)*100)}%"></i></div></span></div>`).join('')}
  <div class="k"><span>tone</span><span>${Object.entries(p.tone).map(([k,v])=>`${k} ${Math.round(v*100)}%`).join(' · ')}</span></div>
  <div class="mt"><h3>Values</h3><ul>${p.values.map(v=>`<li>${esc(v.label)} <span class="badge">${v.strength}</span> <span class="mut">evidence×${v.evidence}</span></li>`).join('')}</ul></div>
  <div class="mt"><h3>Domains</h3><span class="mut">${p.knowledge_domains.join(' · ')}</span></div>
  <div class="mt"><h3>Heuristics</h3><ul>${p.heuristics.slice(0,6).map(h=>`<li><span class="mut">if</span> ${esc(h.trigger||h.rule).slice(0,70)} → <b>${esc(h.rule||h.choice||'').slice(0,80)}</b></li>`).join('')}</ul></div>`;
 $('#truth-box').innerHTML=`<div class="k"><span>truth index</span><span class="${s.truth.status==='solid'?'ok':(s.truth.status==='fragile'?'warn':'fail')}">${s.truth.truth_index} (${s.truth.status})</span></div>
  <div class="k"><span>contradiction ratio</span><span>${s.truth.contradiction_ratio}</span></div>`;
 renderGuard(s); renderTimeline(s);
}
async function renderGuard(s){const g=await api('/api/state');
 $('#guard-box').innerHTML=g.guardrails.map(x=>`<div class="k"><div><span class="mut">${x.tier}</span> ${esc(x.rule)}<div class="mut" style="font-size:11px">${esc(x.rationale)} · v${x.version} · ${x.reversible?'reversible':'fixed'}</div></div>
 <div class="row"><button class="ghost" onclick="decide('${x.id}',true)">✓</button><button class="ghost" onclick="decide('${x.id}',false)">✗</button><button class="ghost" onclick="revertG('${x.id}')">↺</button></div></div>`).join('')||'<div class="mut">no guardrails</div>'}
async function renderTimeline(s){$('#p-memory2').innerHTML=`<h3>Recent memory</h3><ul>${s.timeline.slice(0,10).map(n=>`<li><span class="badge">${n.kind}</span> ${esc(n.content).slice(0,110)} <span class="mut">${esc(n.source||'')}</span></li>`).join('')}</ul>`}

async function recall(){const r=await api('/api/recall',{query:$('#q').value,k:5,identity:$('#ident').checked});
 $('#recall-box').innerHTML=r.length?r.map(m=>`<div class="k"><span>${badge(m.kind)} ${esc(m.content).slice(0,90)}</span>
 <span class="mut" title="cosine × decay × grounding × evidence">${m.score}</span></div>`).join(''):'<div class="mut">no hits</div>'}
async function sim(){const r=await api('/api/simulate',{scenario:$('#scenario').value});
 $('#sim-box').innerHTML=`<div class="k"><span>stance</span><b class="${r.stance==='agree'?'ok':(r.stance==='oppose'?'fail':'warn')}">${r.stance} (${r.stance_score})</b></div>
 <div class="k"><span>draft</span><span class="mut">${esc(r.response_draft)}</span></div>
 ${r.value_conflicts.length?`<div class="mt"><h3>value conflicts</h3><ul>${r.value_conflicts.map(c=>`<li class="fail">${c.value} ← ${c.trigger}</li>`).join('')}</ul></div>`:''}
 <div class="mt"><h3>reasoning trace</h3><ul>${r.reasoning.map(x=>`<li>${esc(x.memory||x.heuristic||'').slice(0,100)}</li>`).join('')}</ul></div>`}
async function proposeG(){const p=await api('/api/propose',{});
 $('#prop-box').innerHTML=p.length?p.map((x,i)=>`<div class="k"><div><span class="badge ${x.tier}">${x.tier}</span> ${esc(x.rule)}<div class="mut" style="font-size:11px">${esc(x.rationale)}</div></div>
 <div class="row">${x.id?`<button class="ghost" onclick="decide('${x.id}',true)">✓</button>`:''}</div></div>`).join(''):'<div class="mut">aligned · no new proposals</div>'}
async function decide(id,approve){await api('/api/decide',{id,approve,by:'dashboard'});refresh()}
async function revertG(id){await api('/api/decide',{id,approve:null,revert:true,by:'dashboard'});refresh()}
async function ingestNow(){const r=await api('/api/ingest',{kind:$('#ikind').value,target:$('#itarget').value,consent:$('#iconsent').checked});
 $('#ingest-box').innerHTML=`<span class="ok">✔ ${r.detail||'memory ingested'}</span>`;refresh()}
async function validateNow(){const r=await api('/api/validate',{});
 $('#val-box').innerHTML=`<h3>${r.summary.status}</h3>`+r.checks.map(c=>`<div class="k"><span><span class="badge ${c.status==='PASS'?'ok':(c.status==='WARN'?'warn':'fail')}">${c.status}</span> ${c.name}</span><span class="mut">${JSON.stringify(c.details)}</span></div>`).join('')}
setInterval(()=>{if($('#p-graph').classList.contains('on'))drawGraph();refresh()},20000);
async function drawGraph(){const g=await api('/api/graph');
 const el=$('#graph');if(!el)return;
 const N=g.elements.neurons,E=g.elements.synapses;if(!N.length){el.innerHTML='';return}
 $('#graph-legend').innerHTML=`${N.length} neurons · ${E.length} synapses`;
 const W=el.clientWidth||900,H=el.clientHeight||420,n=N.length;
 const pos=N.map((_,i)=>({x:W/2+220*Math.cos(i*2.399963),y:H/2+130*Math.sin(i*2.399963)}));
 const idx={};N.forEach((nd,i)=>idx[nd.data.id]=i);
 for(let iter=0;iter<80;iter++){for(const e of E){const a=idx[e.data.source],b=idx[e.data.target];if(a===undefined||b===undefined)continue;
  const dx=pos[b].x-pos[a].x,dy=pos[b].y-pos[a].y,d=Math.hypot(dx,dy)||1,f=(d-90)*0.02;
  pos[a].x+=dx/d*f/2;pos[a].y+=dy/d*f/2;pos[b].x-=dx/d*f/2;pos[b].y-=dy/d*f/2;}
  N.forEach((nd,i)=>{pos[i].x+=(W/2-pos[i].x)*0.01;pos[i].y+=(H/2-pos[i].y)*0.01;});}
 const color={fact:'#38bdf8',note:'#38bdf8',preference:'#a78bfa',decision:'#fbbf24',milestone:'#f472b6',relationship:'#34d399',identity:'#f87171',value:'#f87171',trait:'#fb923c',persona_signal:'#e2e8f0'};
 let svg='';
 svg=E.map(e=>{const a=idx[e.data.source],b=idx[e.data.target];if(a===undefined||b===undefined)return '';return `<line x1="${pos[a].x}" y1="${pos[a].y}" x2="${pos[b].x}" y2="${pos[b].y}" stroke="#223">`}).join('');
 svg+=N.map((nd,i)=>`<g><circle cx="${pos[i].x}" cy="${pos[i].y}" r="9" fill="${color[nd.data.kind]||'#64748b'}"/><title>${esc(nd.data.kind)}: ${esc(nd.data.content).slice(0,80)}</title><text x="${pos[i].x+12}" y="${pos[i].y+4}" fill="#7f93ad" style="font-size:10px">${esc((nd.data.label||'').slice(0,22))}</text></g>`).join('');
 el.innerHTML=svg;}
setInterval(loadAudit,15000);loadAudit();
async function loadAudit(){$('#audit-box').innerHTML=`<table><tr><th>ts</th><th>actor</th><th>action</th><th>risk</th><th>result</th></tr>`+(await api('/api/audit')).map(a=>`<tr><td class="mut">${esc(a.ts)}</td><td>${esc(a.actor)}</td><td>${esc(a.action)}</td><td class="${a.risk||'low'}">${a.risk||''}</td><td>${esc(a.result)}</td></tr>`).join('')+'</table>'}
refresh();
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    engine: Celebrum = None
    server_version = "celebrum/0.1"

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if "text" in ctype else ""))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            return self._send(200, PAGE.encode("utf-8"), "text/html")
        if path == "/api/state":
            s = self.engine.snapshot()
            s["guardrails"] = self.engine.guardrails.all()
            s["timeline"] = self.engine.graph.timeline(15)
            return self._json(s)
        if path == "/api/graph":
            return self._json(self.engine.graph.graph_export(cytoscape=True))
        if path == "/api/audit":
            import urllib.parse as up
            q = up.parse_qs(urllib.parse.urlparse(self.path).query)
            n = int(q.get("n", [30])[0])
            return self._json(self.engine.store.audit_tail(n))
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0).decode("utf-8") or "{}")
        except Exception:
            body = {}
        try:
            if path == "/api/recall":
                return self._json(self.engine.recall(body.get("query", ""), k=body.get("k", 5),
                                                     identity=body.get("identity", True)))
            if path == "/api/simulate":
                return self._json(self.engine.simulate(body.get("scenario", "")))
            if path == "/api/propose":
                return self._json(self.engine.propose())
            if path == "/api/decide":
                if body.get("revert"):
                    return self._json(self.engine.revert(body["id"], by=body.get("by", "dashboard")))
                if body.get("approve"):
                    return self._json(self.engine.approve(body["id"], by=body.get("by", "dashboard")))
                return self._json(self.engine.reject(body["id"], by=body.get("by", "dashboard")))
            if path == "/api/ingest":
                kind, target, consent = body.get("kind"), body.get("target", ""), bool(body.get("consent", False))
                if not target:
                    return self._json({"error": "target required"}, 400)
                try:
                    if kind == "duet":
                        with open(target, encoding="utf-8") as fh:
                            res = self.engine.ingest_duet(json.load(fh), consent=consent)
                    elif kind == "web":
                        res = self.engine.ingest_web(target, consent=consent)
                    else:
                        res = self.engine.ingest_html(target, consent=consent)
                    res["detail"] = f"ingested +{res['neurons']} neurons"
                    return self._json(res)
                except FileNotFoundError:
                    return self._json({"error": "file not found"}, 404)
            if path == "/api/validate":
                return self._json(self.engine.validate())
        except PermissionError as e:
            return self._json({"error": str(e)}, 403)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 500)
        return self._json({"error": "not found"}, 404)


def run_gui(home=None, host="127.0.0.1", port=8477, db=None):
    engine = Celebrum(home=home, db=db)
    Handler.engine = engine
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"🧠 Celebrum dashboard → http://{host}:{port}  (brain: {engine.home})")
    engine.store.log("user", "gui_start", risk="low", details={"host": host, "port": port}, result="ok")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye. the brain remembers.")
        engine.store.log("user", "gui_stop", risk="low", result="ok")


if __name__ == "__main__":
    import sys
    run_gui(home=sys.argv[1] if len(sys.argv) > 1 else None)