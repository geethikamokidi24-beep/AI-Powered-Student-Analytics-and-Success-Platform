(() => {
const $ = q => document.querySelector(q), app = $("#app"), B = document.body;
const CSRF = B.dataset.csrf, ROLE = B.dataset.role;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const mean = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0, f1 = x => Number(x).toFixed(1);
let M, S = [];
const F = {q: "", dept: "", yr: "", risk: "", seg: "", sort: "asc", n: 30};
let tab = "academic";

async function api(path, method = "GET", body) {
  const r = await fetch(path, {method, credentials: "same-origin",
    headers: {"Content-Type": "application/json", "X-CSRF-Token": CSRF},
    body: body ? JSON.stringify(body) : undefined});
  if (r.status === 401) { location.href = "/login"; throw new Error("Signed out"); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || "Request failed");
  return j;
}
const load = async () => { S = await api("/api/students"); };
const badge = l => `<span class="b ${esc(l)}">${esc(l)}</span>`;
const opt = (arr, all) => `<option value="">${all}</option>` + arr.map(v => `<option>${esc(v)}</option>`).join("");
const say = (el, msg, ok) => { el.textContent = msg; el.className = ok ? "ok" : "bad"; };
const score = s => s.score === null ? "n/a" : f1(s.score);

function overview() {
  if (!S.length) return `<h1>Student success overview</h1><div class="note">No students yet. ${ROLE === "admin" ? "Add students from the Admin page." : "Ask an administrator to add students."}</div>`;
  const R = S.filter(s => s.score !== null), hi = R.filter(s => s.level === "High"), bins = Array(8).fill(0);
  R.forEach(s => bins[Math.max(0, Math.min(7, Math.floor((s.score - 20) / 10)))]++);
  const mx = Math.max(1, ...bins);
  const dep = M.departments.map(d => { const g = R.filter(s => s.dept === d), c = l => g.filter(s => s.level === l).length; return {d, n: g.length, h: c("High"), m: c("Medium"), l: c("Low")}; }).filter(x => x.n);
  const drv = Object.keys(M.weights).map(k => ({k, v: mean(hi.map(s => s.loss[k]).filter(x => x !== undefined))})).sort((a, b) => b.v - a.v);
  return `<h1>Student success overview</h1>
  <p class="mu">One unified view of academic, attendance, LMS, engagement, placement, skills and feedback data, reduced to a Student Success Score from 0 to 100.</p>
  ${S.some(s => /^DEMO-/.test(s.id)) ? '<div class="note">Records with IDs starting DEMO- are synthetic demo data. No real student is represented.</div>' : ""}
  <div class="note"><strong>AI support insights</strong> · ${S.filter(s => s.ai.academic !== null && (s.ai.academic >= 50 || s.ai.placement >= 50)).length} students flagged by the demonstration model. Open a student for predictions, contributing indicators and recommended actions. Trained on synthetic data; faculty review is required.</div>
  <div class="grid">
  <div class="card"><div class="k">${S.length}</div><div class="kl">Students</div></div>
  <div class="card"><div class="k">${R.length ? f1(mean(R.map(s => s.score))) : "n/a"}</div><div class="kl">Average success score</div></div>
  <div class="card"><div class="k">${hi.length}</div><div class="kl">High risk overall</div></div>
  <div class="card"><div class="k">${S.filter(s => s.acadRisk).length}</div><div class="kl">Academic risk flags</div></div>
  <div class="card"><div class="k">${S.filter(s => s.plcRisk).length}</div><div class="kl">Placement risk flags</div></div>
  <div class="card"><div class="k">${S.length - R.length}</div><div class="kl">Unrated, data missing</div></div></div>
  <div class="two"><div class="card mt"><h3>Score distribution</h3><div class="hist">${bins.map((b, i) => `<div><span>${b}</span><i style="height:${b / mx * 80}%"></i><span>${20 + i * 10}s</span></div>`).join("")}</div></div>
  <div class="card mt"><h3>Risk level by department</h3>${dep.map(x => `<div class="row"><span>${esc(x.d)}</span><div class="bar"><i class="hi" style="width:${x.h / x.n * 100}%"></i><i class="md" style="width:${x.m / x.n * 100}%"></i><i class="lo" style="width:${x.l / x.n * 100}%"></i></div><span class="mu">${x.h}/${x.n}</span></div>`).join("")}<p class="mu" style="font-size:13px;margin:8px 0 0">Red high, amber medium, green low. Count shows high risk of rated students.</p></div></div>
  <div class="card mt"><h3>What pulls high-risk students down</h3><p class="mu" style="font-size:14px">Average points lost per indicator across ${hi.length} high-risk students, out of each indicator's weight.</p>${hi.length ? drv.map(x => `<div class="row d"><span>${esc(M.labels[x.k])}</span><div class="bar"><i style="width:${x.v / M.weights[x.k] * 100}%"></i></div><span>${f1(x.v)} of ${M.weights[x.k]}</span></div>`).join("") : '<p class="mu">No high-risk students.</p>'}</div>
  <p class="mt"><button id="goS">Open student list</button> <a href="/export.csv" download><button class="g" type="button">Export CSV</button></a></p>`;
}

function students() {
  return `<h1>Students</h1><p class="mu">Filter, search and open a student to see the indicators behind the score and to update their data.</p>
  <div class="ctl"><input id="q" placeholder="Search by ID" aria-label="Search by ID">
  <select id="dept" aria-label="Department">${opt(M.departments, "All departments")}</select>
  <select id="yr" aria-label="Year">${opt([1, 2, 3, 4], "All years")}</select>
  <select id="risk" aria-label="Risk">${opt(["High", "Medium", "Low", "Unrated", "Academic flag", "Placement flag"], "All risk levels")}</select>
  <select id="seg" aria-label="Segment"><option value="">All segments</option>${Object.keys(M.segments).map(k => `<option value="${k}">${esc(M.segments[k][0])}</option>`).join("")}</select>
  <select id="sort" aria-label="Sort"><option value="asc">Lowest score first</option><option value="desc">Highest score first</option></select></div>
  <div id="det"></div><div id="tbl"></div>`;
}
function drawTable() {
  const r = S.filter(s => (!F.q || s.id.toLowerCase().includes(F.q.toLowerCase())) && (!F.dept || s.dept === F.dept) && (!F.yr || s.year == F.yr) && (!F.seg || s.seg === F.seg) &&
    (!F.risk || (F.risk === "Academic flag" ? s.acadRisk : F.risk === "Placement flag" ? s.plcRisk : s.level === F.risk)));
  const val = s => s.score === null ? (F.sort === "asc" ? -1 : 101) : s.score;
  r.sort((a, b) => F.sort === "asc" ? val(a) - val(b) : val(b) - val(a));
  $("#tbl").innerHTML = `<p class="mu" style="font-size:14px">${r.length} students match</p><div class="tw"><table><thead><tr><th>ID</th><th>Dept</th><th>Year</th><th>Score</th><th>Risk</th><th>Segment</th></tr></thead><tbody>${r.slice(0, F.n).map(s => `<tr tabindex="0" data-id="${esc(s.id)}"><td>${esc(s.id)}</td><td>${esc(s.dept)}</td><td>${s.year}</td><td>${score(s)}</td><td>${badge(s.level)}</td><td>${esc(M.segments[s.seg][0])}</td></tr>`).join("")}</tbody></table></div>${r.length > F.n ? '<p class="mt"><button class="g" id="more">Show more</button></p>' : ""}`;
  document.querySelectorAll("#tbl tbody tr").forEach(t => { const o = () => detail(t.dataset.id); t.onclick = o; t.onkeydown = e => { if (e.key === "Enter") o(); }; });
  const m = $("#more"); if (m) m.onclick = () => { F.n += 30; drawTable(); };
}
const fieldsHtml = (t, s) => Object.entries(M.fields[t]).map(([f, [lo, hi, ty]]) =>
  `<label>${esc(f.replace(/_/g, " "))} (${lo} to ${hi})<input name="${esc(f)}" type="number" step="${ty === "int" ? 1 : "any"}" min="${lo}" max="${hi}" required ${ROLE === "student" ? "disabled" : ""} value="${s.raw[f] ?? ""}"></label>`).join("");

function detail(id, msg) {
  const s = S.find(x => x.id === id); if (!s) return;
  $("#det").innerHTML = `<div class="card mt"><div class="split"><div><h3>${esc(s.id)}, ${esc(s.dept)}, year ${s.year}</h3><p class="mu" style="margin:0">${s.raw.cgpa === null ? "No academic record" : `CGPA ${s.raw.cgpa}, backlogs ${s.raw.backlogs}`}${s.raw.overall_pct === null ? "" : `, attendance ${Math.round(s.raw.overall_pct)}%`}</p></div><button class="g" id="x" type="button">Close</button></div>
  <div class="k" style="margin:10px 0 4px">${score(s)} ${badge(s.level)}</div>
  <div>${s.acadRisk ? '<span class="flag">Academic risk</span>' : ""}${s.plcRisk ? '<span class="flag">Placement risk</span>' : ""}${!s.acadRisk && !s.plcRisk ? '<span class="mu" style="font-size:14px">No observed risk flags</span>' : ""}</div>
  ${s.missing.length ? `<div class="note">Missing data: ${s.missing.map(k => esc(M.labels[k])).join(", ")}.${s.score === null ? " Too much is missing to give a score." : " The score uses the indicators that are present."}</div>` : ""}
  <h3 style="margin-top:8px">Score drivers (points earned of maximum)</h3>
  ${Object.keys(M.weights).filter(k => k in s.part).map(k => `<div class="row d"><span>${esc(M.labels[k])}</span><div class="bar"><i style="width:${s.part[k] / M.weights[k] * 100}%"></i></div><span>${f1(s.part[k])}/${M.weights[k]}</span></div>`).join("")}
  ${s.top.length ? `<p style="margin:10px 0 4px"><strong>Biggest losses:</strong> ${s.top.map(k => `${esc(M.labels[k])} (${f1(s.loss[k])} pts)`).join(", ")}.</p>` : ""}
  <p style="margin:0"><strong>Segment:</strong> ${esc(M.segments[s.seg][0])}. <span class="mu">${esc(M.segments[s.seg][1])}</span></p>
  ${s.risk_reasons.length ? `<div class="note"><strong>Why flagged:</strong> ${s.risk_reasons.map(esc).join("; ")}</div>` : ""}${aiCard(s)}<div id="studentHistory" class="mt"></div><div id="interventions" class="mt"></div><h3 style="margin-top:16px">${ROLE === "student" ? "My records (read only)" : "Update data"}</h3>
  <form id="df"><label for="dt">Record</label><select id="dt">${Object.keys(M.fields).map(t => `<option${t === tab ? " selected" : ""}>${t}</option>`).join("")}</select>
  <div class="fgrid mt" id="dfl">${fieldsHtml(tab, s)}</div>
  <div class="acts">${ROLE !== "student" ? '<button type="submit">Save</button>' : ""}${ROLE === "admin" ? '<button class="g" type="button" id="del">Delete student</button>' : ""}<span id="dmsg" class="ok">${esc(msg || "")}</span></div></form></div>`;
  loadInterventions(s.id);
  loadStudentHistory(s.id);
  $("#x").onclick = () => { $("#det").innerHTML = ""; };
  $("#dt").onchange = e => { tab = e.target.value; $("#dfl").innerHTML = fieldsHtml(tab, s); };
  $("#df").onsubmit = async e => {
    e.preventDefault(); const d = {}; new FormData(e.target).forEach((v, k) => { d[k] = v; });
    try { await api(`/api/students/${encodeURIComponent(id)}/${tab}`, "POST", d); await load(); drawTable(); detail(id, "Saved."); }
    catch (x) { say($("#dmsg"), x.message, false); }
  };
  const del = $("#del");
  if (del) del.onclick = async () => {
    if (!confirm(`Delete ${id} and all of their records? This cannot be undone.`)) return;
    try { await api(`/api/students/${encodeURIComponent(id)}`, "DELETE"); await load(); $("#det").innerHTML = ""; drawTable(); }
    catch (x) { say($("#dmsg"), x.message, false); }
  };
  $("#det").scrollIntoView({behavior: "auto", block: "start"});
}

function segments() {
  return `<h1>Segments</h1><p class="mu">Rule-based groups with a suggested action. A student belongs to the first segment whose rule they meet.</p>
  <div class="two">${Object.keys(M.segments).map(k => { const g = S.filter(s => s.seg === k), r = g.filter(s => s.score !== null);
    return `<div class="card"><h3>${esc(M.segments[k][0])}</h3><div class="k">${g.length}</div><div class="kl">${S.length ? Math.round(g.length / S.length * 100) : 0}% of students${r.length ? `, average score ${f1(mean(r.map(s => s.score)))}` : ""}</div><p style="margin:10px 0">${esc(M.segments[k][1])}</p><button class="g" data-seg="${k}">View students</button></div>`; }).join("")}</div>`;
}
function method() {
  const rows = {acad: "CGPA times 10, minus 8 per backlog", att: "Overall attendance percentage", lms: "Average of login score and assignment completion",
    plc: "Average of aptitude, coding and mock interview scores", skl: "Average of technical and soft-skill scores", eng: "Events times 10, clubs times 15, hackathons times 20, certifications times 15, capped at 100",
    fb: "Average of student satisfaction and faculty feedback, each out of 5, times 20"};
  return `<h1>How the Student Success Score works</h1>
  <p>The score is a weighted sum of seven indicators, each converted to a 0 to 100 index. Points earned equal weight times index divided by 100, so every point can be traced to an indicator.</p>
  <div class="tw"><table style="min-width:420px"><thead><tr><th>Indicator</th><th>Weight</th><th>Index built from</th></tr></thead><tbody>${Object.keys(rows).map(k => `<tr><td>${esc(M.labels[k])}</td><td>${M.weights[k]}</td><td>${rows[k]}</td></tr>`).join("")}</tbody></table></div>
  <h2>Risk levels and flags</h2>
  <ul><li>High risk: score below 52. Medium: 52 to 63.9. Low: 64 and above.</li>
  <li>Academic risk flag: CGPA below 6, two or more backlogs, or attendance below 75%.</li>
  <li>Placement risk flag: placement readiness index below 50.</li></ul>
  <h2>Missing data</h2>
  <p>If some records are missing, the score is rescaled over the indicators present, provided they carry at least 60 of the 100 weight. Otherwise the student is shown as Unrated and the missing records are listed.</p>
  <h2>AI model</h2><p>Two logistic regression models estimate academic and placement risk using the seven normalized indicators. Training uses 4,000 synthetic examples, not institutional outcomes. Predictions are demonstrations, not validated real-world probabilities. Missing indicators suppress predictions. The AI estimate is separate from the weighted Success Score. Recommendations use transparent indicator rules.</p><h2>Explainability</h2>
  <p>For each student, the loss for an indicator is its weight minus the points earned. The three largest losses are shown as the reasons behind the score and flags.</p>
  <p class="mu">The weights and thresholds are starting points. Tune them with faculty input and your own data.</p>`;
}
async function admin() {
  const [U, A] = await Promise.all([api("/api/users"), api("/api/audit")]);
  return `<h1>Administration</h1>
  <h2>Accounts</h2><div class="tw"><table style="min-width:560px"><thead><tr><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th></th></tr></thead><tbody>${U.map(u => `<tr><td>${esc(u.username)}</td><td>${esc(u.full_name)}</td><td>${esc(u.role)}${u.department ? " / " + esc(u.department) : ""}${u.student_id ? " / " + esc(u.student_id) : ""}</td><td>${u.active ? "Active" : "Disabled"}</td><td><button class="g" data-act="toggle" data-id="${u.id}" data-active="${u.active}">${u.active ? "Disable" : "Enable"}</button><button class="g" data-act="reset" data-id="${u.id}">Set password</button></td></tr>`).join("")}</tbody></table></div>
  <div class="two"><form class="card mt" id="uf"><h3>Add account</h3><label>Username<input name="username" required pattern="[a-z0-9._-]{3,32}"></label><label>Full name<input name="full_name" required maxlength="80"></label><label>Role<select name="role"><option value="faculty">Faculty</option><option value="student">Student / User</option><option value="admin">admin</option></select></label><label>Faculty department<select name="department">${M.departments.map(d => `<option>${esc(d)}</option>`).join("")}</select></label><label>Student ID (required for Student / User)<input name="student_id" placeholder="DEMO-0001"></label><label>Password (10 or more characters)<input name="password" type="password" required minlength="10" autocomplete="new-password"></label><div class="acts"><button type="submit">Create account</button><span id="umsg"></span></div></form>
  <form class="card mt" id="sf"><h3>Add student</h3><label>Roll number or ID<input name="id" required pattern="[A-Za-z0-9_-]{3,24}"></label><label>Department<select name="department">${M.departments.map(d => `<option>${esc(d)}</option>`).join("")}</select></label><label>Year<select name="year"><option>1</option><option>2</option><option>3</option><option>4</option></select></label><div class="acts"><button type="submit">Add student</button><span id="smsg"></span></div><p class="mu mt" style="font-size:13px">Then open the student under Students to enter their data.</p></form></div>
  <h2>Recent activity</h2><div class="tw"><table><thead><tr><th>Time (UTC)</th><th>User</th><th>Action</th><th>Detail</th></tr></thead><tbody>${A.map(a => `<tr><td>${esc(a.at)}</td><td>${esc(a.username)}</td><td>${esc(a.action)}</td><td>${esc(a.detail)}</td></tr>`).join("")}</tbody></table></div>`;
}


function aiCard(s) {
  const a = s.ai;
  return `<div class="note"><h3>AI risk insights</h3>${a.academic === null ? '<p>Complete all seven areas to generate a prediction.</p>' : `<p><strong>Academic risk:</strong> ${a.academic}% · <strong>Placement risk:</strong> ${a.placement}%</p><p><strong>Top model contributions:</strong> ${a.drivers.map(x => esc(M.labels[x])).join(", ")}</p>`}<ul>${a.recommendations.map(x => `<li>${esc(x)}</li>`).join("")}</ul><small>Demonstration model trained on synthetic data. Review with faculty before taking action.</small></div>`;
}
async function loadInterventions(id) {
  const box = $("#interventions");
  try {
    const list = await api(`/api/students/${encodeURIComponent(id)}/interventions`);
    if (!box.isConnected) return;
    box.innerHTML = `<h3>Support action plan</h3>${list.length ? list.map(a => `<div class="note"><strong>${esc(a.status)}</strong> · ${esc(a.action)}<br><small>${esc(a.created_at)}</small>${ROLE !== "student" && a.status !== "Completed" ? `<button type="button" class="g" data-complete="${a.id}">Mark completed</button>` : ""}</div>`).join("") : '<p class="mu">No support actions recorded.</p>'}${ROLE !== "student" ? '<form id="actionform"><label>Support action<textarea name="action" required maxlength="1000" placeholder="For example, schedule a weekly mentoring session"></textarea></label><button>Add action</button><span id="actionmsg"></span></form>' : ""}`;
    box.querySelectorAll('[data-complete]').forEach(b => b.onclick = async () => {
      const a = list.find(x => String(x.id) === b.dataset.complete);
      try { await api(`/api/students/${encodeURIComponent(id)}/interventions`, "POST", {id:a.id, action:a.action, status:"Completed"}); loadInterventions(id); } catch(e) { alert(e.message); }
    });
    const form = $("#actionform");
    if(form) form.onsubmit = async e => { e.preventDefault(); try {await api(`/api/students/${encodeURIComponent(id)}/interventions`, "POST", Object.fromEntries(new FormData(form))); loadInterventions(id);} catch(x){say($("#actionmsg"), x.message, false);} };
  } catch(e) { box.textContent = e.message; }
}
function account() {
  return `<h1>My account</h1><div class="card"><p>${esc(M.user.name)} · ${esc(M.user.role)}${M.user.department ? " · " + esc(M.user.department) : ""}${M.user.student_id ? " · " + esc(M.user.student_id) : ""}</p><form id="pwform"><label>Current password<input name="current" type="password" required autocomplete="current-password"></label><label>New password<input name="password" type="password" required minlength="10" autocomplete="new-password"></label><button>Change password</button> <span id="pwmsg"></span></form></div>`;
}

async function integration() {
  const q = await api('/api/quality');
  return `<h1>Data integration and quality</h1><p class="mu">Import a roster, then join seven source exports by student ID. Preview validates every row before any database change. Faculty imports stay within their department.</p>
  <div class="grid"><div class="card"><div class="k">${q.total}</div><div class="kl">Accessible students</div></div><div class="card"><div class="k">${q.complete}</div><div class="kl">All seven areas complete</div></div><div class="card"><div class="k">${q.unrated}</div><div class="kl">Too little data to score</div></div></div>
  <div class="card mt"><h3>Source coverage</h3>${Object.keys(q.coverage).map(k=>`<div class="row d"><span>${esc(M.labels[k])}</span><div class="bar"><i style="width:${q.total?100*q.coverage[k]/q.total:0}%"></i></div><span>${q.coverage[k]}/${q.total}</span></div>`).join('')}</div>
  <form id="importform" class="card mt"><h3>CSV import</h3><label>Source<select id="isource">${[...(ROLE==='admin'?['students']:[]),...Object.keys(M.fields)].map(x=>`<option>${x}</option>`).join('')}</select></label><p id="columns" class="mu"></p><label>CSV file (UTF-8, up to 1,000 rows)<input id="ifile" type="file" accept=".csv,text/csv" required></label><button>Preview and validate</button> <span id="imsg"></span></form><div id="preview"></div>
  <h2>Recent imports</h2><div class="tw"><table><thead><tr><th>Time</th><th>Source</th><th>File</th><th>Accepted</th><th>Rejected</th><th>Skipped</th></tr></thead><tbody>${q.imports.map(x=>`<tr><td>${esc(x.created_at)}</td><td>${esc(x.source)}</td><td>${esc(x.filename)}</td><td>${x.accepted}</td><td>${x.rejected}</td><td>${x.skipped}</td></tr>`).join('')}</tbody></table></div>`;
}
function bindImport() {
  let pending=null;
  const reset=()=>{pending=null;$('#preview').innerHTML='';const src=$('#isource').value;$('#columns').textContent='Required columns: '+(src==='students'?['student_id','department','year']:['student_id',...Object.keys(M.fields[src])]).join(', ');};
  $('#isource').onchange=reset;$('#ifile').onchange=reset;reset();
  $('#importform').onsubmit=async e=>{
    e.preventDefault(); pending=null;$('#preview').innerHTML='';
    const file=$('#ifile').files[0];if(!file)return;
    if(file.size>800000){say($('#imsg'),'Use a CSV file smaller than 800 KB.',false);return;}
    try{
      const d={source:$('#isource').value,csv:await file.text(),filename:file.name};
      const r=await api('/api/import','POST',d);pending=d;
      say($('#imsg'),'Preview ready. No data changed.',true);
      $('#preview').innerHTML=`<div class="card mt"><h3>Import preview</h3><p>${r.accepted} accepted · ${r.rejected} rejected · ${r.skipped} blank records skipped · ${r.normalized} rows normalized</p><p class="mu">Valid rows update existing records. Blank module rows preserve existing data. Duplicate IDs keep the first occurrence. ${r.ignored_columns.length?'Ignored columns: '+r.ignored_columns.map(esc).join(', '):''}</p><div class="tw"><table><thead><tr><th>CSV row</th><th>Student</th><th>Normalized values (first 10 valid rows)</th></tr></thead><tbody>${r.preview.map(x=>`<tr><td>${x.row}</td><td>${esc(x.id)}</td><td>${esc(JSON.stringify(x.values))}</td></tr>`).join('')}</tbody></table></div>${r.errors.length?`<h3 class="mt">Rejected rows</h3><ul>${r.errors.map(x=>`<li>Row ${x.row}, ${esc(x.id)}: ${esc(x.reason)}</li>`).join('')}</ul>`:''}${r.skipped_rows.length?`<p class="mu">Skipped CSV rows: ${r.skipped_rows.map(x=>x.row).join(', ')}</p>`:''}${r.accepted?`<button id="applyimport">Import ${r.accepted} accepted rows</button>`:''}<span id="applymsg"></span></div>`;
      const b=$('#applyimport');if(b)b.onclick=async()=>{b.disabled=true;try{const result=await api('/api/import','POST',{...pending,apply:true});pending=null;await load();$('#applymsg').textContent=` Imported ${result.accepted} rows. Reopen Data import to refresh coverage and history.`;}catch(x){say($('#applymsg'),x.message,false);b.disabled=false;}};
    }catch(x){say($('#imsg'),x.message,false);}
  };
}
function trendChart(rows) {
  if(!rows.length)return '<p class="mu">No snapshots yet. Faculty or Admin can record the first month.</p>';
  const n=rows.length, x=i=>50+i*660/Math.max(1,n-1), y=v=>220-v*1.8;
  const points=rows.map((r,i)=>r.score===null?null:`${x(i)},${y(r.score)}`).filter(Boolean).join(' ');
  return `<svg viewBox="0 0 760 270" role="img" aria-label="Average Student Success Score over recorded months" style="width:100%;max-height:330px"><line x1="50" y1="40" x2="50" y2="220" stroke="#b7c5dc"/><line x1="50" y1="220" x2="710" y2="220" stroke="#b7c5dc"/><text x="8" y="46" fill="#586780" font-size="13">100</text><text x="20" y="222" fill="#586780" font-size="13">0</text><polyline points="${points}" fill="none" stroke="#5368ce" stroke-width="3"/>${rows.map((r,i)=>`${r.score!==null?`<circle cx="${x(i)}" cy="${y(r.score)}" r="5" fill="#5368ce"/><text x="${x(i)}" y="${y(r.score)-12}" text-anchor="middle" font-size="14" fill="#303f8f">${r.score}</text>`:''}<text x="${x(i)}" y="246" text-anchor="middle" font-size="12" fill="#586780">${esc(r.period)}</text>`).join('')}</svg>`;
}
async function trends() {
  const rows=await api('/api/trends');
  return `<h1>Student success trends</h1><p class="mu">Monthly snapshots retain the score and risk flags at the time of capture. Compare cohort sizes before interpreting changes. Trends show association, not proof of intervention impact.</p>${rows.some(x=>x.simulated)?'<div class="note">Included historical snapshots are simulated demo data, not measured improvement.</div>':''}<div class="card">${trendChart(rows.slice(-12))}</div><div class="tw mt"><table><thead><tr><th>Month</th><th>Students</th><th>Rated</th><th>Mean score</th><th>High risk</th><th>Academic flags</th><th>Placement flags</th><th>Data</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${esc(x.period)}</td><td>${x.count}</td><td>${x.rated}</td><td>${x.score??'Unrated'}</td><td>${x.high}</td><td>${x.academic}</td><td>${x.placement}</td><td>${x.simulated?'Simulated':'Recorded'}</td></tr>`).join('')}</tbody></table></div>${ROLE!=='student'?'<form id="snapshotform" class="card mt"><h3>Record a monthly snapshot</h3><p class="mu">Saves current data for your accessible students. Recording the same month replaces those students’ earlier snapshot for that month.</p><label>Reporting month<input type="month" id="month" required></label><button>Save snapshot</button><span id="snapmsg"></span></form>':''}`;
}
function bindTrends(){const form=$('#snapshotform');if(form){const now=new Date();$('#month').value=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;form.onsubmit=async e=>{e.preventDefault();try{await api('/api/trends','POST',{period:$('#month').value});await route();}catch(x){say($('#snapmsg'),x.message,false);}};}}
async function loadStudentHistory(id){const box=$('#studentHistory');try{const rows=await api(`/api/students/${encodeURIComponent(id)}/history`);if(!box.isConnected)return;box.innerHTML='<h3>Student score history</h3>'+trendChart(rows.slice(-12))+(rows.some(x=>x.source==='Simulated demo history')?'<small>Historical example values are simulated.</small>':'');}catch(e){box.textContent=e.message;}}

const views = {"": overview, students, segments, method, admin, account, integration, trends};
const binds = {
  integration: bindImport,
  trends: bindTrends,
  account: () => { $("#pwform").onsubmit = async e => {
    e.preventDefault(); const d = Object.fromEntries(new FormData(e.target));
    try { await api("/api/password", "POST", d); e.target.reset(); say($("#pwmsg"), "Password changed.", true); }
    catch(x) { say($("#pwmsg"), x.message, false); }
  }; },
  "": () => { const g = $("#goS"); if (g) g.onclick = () => { location.hash = "#/students"; }; },
  students: () => {
    ["dept", "yr", "risk", "seg", "sort"].forEach(k => { const e = $("#" + k); e.value = F[k]; e.onchange = () => { F[k] = e.value; F.n = 30; drawTable(); }; });
    $("#q").value = F.q; $("#q").oninput = e => { F.q = e.target.value; F.n = 30; drawTable(); }; drawTable();
  },
  segments: () => document.querySelectorAll("[data-seg]").forEach(b => { b.onclick = () => { F.seg = b.dataset.seg; location.hash = "#/students"; }; }),
  admin: () => {
    document.querySelectorAll("[data-act]").forEach(b => { b.onclick = async () => {
      try {
        if (b.dataset.act === "toggle") await api(`/api/users/${b.dataset.id}`, "PATCH", {active: b.dataset.active === "1" ? 0 : 1});
        else { const p = prompt("New password (10 or more characters)"); if (!p) return; await api(`/api/users/${b.dataset.id}`, "PATCH", {password: p}); alert("Password updated."); }
        route();
      } catch (x) { alert(x.message); }
    }; });
    const form = (id, msgId, url, after) => { $(id).onsubmit = async e => {
      e.preventDefault(); const d = {}; new FormData(e.target).forEach((v, k) => { d[k] = v; });
      try { await api(url, "POST", d); await after(); await route(); } catch (x) { say($(msgId), x.message, false); } }; };
    form("#uf", "#umsg", "/api/users", async () => {});
    form("#sf", "#smsg", "/api/students", load);
  },
};
async function route() {
  const r = location.hash.replace(/^#\/?/, ""), v = (r in views && (r !== "admin" || ROLE === "admin") && (r !== "integration" || ROLE !== "student")) ? r : "";
  try { app.innerHTML = await views[v](); } catch (e) { app.innerHTML = `<div class="err">${esc(e.message)}</div>`; return; }
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#/" + v));
  if (binds[v]) binds[v]();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
(async () => { try { M = await api("/api/meta"); await load(); route(); } catch (e) { app.innerHTML = `<div class="err">${esc(e.message)}</div>`; } })();
})();
