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
  `<label>${esc(f.replace(/_/g, " "))} (${lo} to ${hi})<input name="${esc(f)}" type="number" step="${ty === "int" ? 1 : "any"}" min="${lo}" max="${hi}" required value="${s.raw[f] ?? ""}"></label>`).join("");

function detail(id, msg) {
  const s = S.find(x => x.id === id); if (!s) return;
  $("#det").innerHTML = `<div class="card mt"><div class="split"><div><h3>${esc(s.id)}, ${esc(s.dept)}, year ${s.year}</h3><p class="mu" style="margin:0">${s.raw.cgpa === null ? "No academic record" : `CGPA ${s.raw.cgpa}, backlogs ${s.raw.backlogs}`}${s.raw.overall_pct === null ? "" : `, attendance ${Math.round(s.raw.overall_pct)}%`}</p></div><button class="g" id="x" type="button">Close</button></div>
  <div class="k" style="margin:10px 0 4px">${score(s)} ${badge(s.level)}</div>
  <div>${s.acadRisk ? '<span class="flag">Academic risk</span>' : ""}${s.plcRisk ? '<span class="flag">Placement risk</span>' : ""}${!s.acadRisk && !s.plcRisk ? '<span class="mu" style="font-size:14px">No risk flags</span>' : ""}</div>
  ${s.missing.length ? `<div class="note">Missing data: ${s.missing.map(k => esc(M.labels[k])).join(", ")}.${s.score === null ? " Too much is missing to give a score." : " The score uses the indicators that are present."}</div>` : ""}
  <h3 style="margin-top:8px">Score drivers (points earned of maximum)</h3>
  ${Object.keys(M.weights).filter(k => k in s.part).map(k => `<div class="row d"><span>${esc(M.labels[k])}</span><div class="bar"><i style="width:${s.part[k] / M.weights[k] * 100}%"></i></div><span>${f1(s.part[k])}/${M.weights[k]}</span></div>`).join("")}
  ${s.top.length ? `<p style="margin:10px 0 4px"><strong>Biggest losses:</strong> ${s.top.map(k => `${esc(M.labels[k])} (${f1(s.loss[k])} pts)`).join(", ")}.</p>` : ""}
  <p style="margin:0"><strong>Segment:</strong> ${esc(M.segments[s.seg][0])}. <span class="mu">${esc(M.segments[s.seg][1])}</span></p>
  <h3 style="margin-top:16px">Update data</h3>
  <form id="df"><label for="dt">Record</label><select id="dt">${Object.keys(M.fields).map(t => `<option${t === tab ? " selected" : ""}>${t}</option>`).join("")}</select>
  <div class="fgrid mt" id="dfl">${fieldsHtml(tab, s)}</div>
  <div class="acts"><button type="submit">Save</button>${ROLE === "admin" ? '<button class="g" type="button" id="del">Delete student</button>' : ""}<span id="dmsg" class="ok">${esc(msg || "")}</span></div></form></div>`;
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
  <h2>Explainability</h2>
  <p>For each student, the loss for an indicator is its weight minus the points earned. The three largest losses are shown as the reasons behind the score and flags.</p>
  <p class="mu">The weights and thresholds are starting points. Tune them with faculty input and your own data.</p>`;
}
async function admin() {
  const [U, A] = await Promise.all([api("/api/users"), api("/api/audit")]);
  return `<h1>Administration</h1>
  <h2>Accounts</h2><div class="tw"><table style="min-width:560px"><thead><tr><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th></th></tr></thead><tbody>${U.map(u => `<tr><td>${esc(u.username)}</td><td>${esc(u.full_name)}</td><td>${esc(u.role)}</td><td>${u.active ? "Active" : "Disabled"}</td><td><button class="g" data-act="toggle" data-id="${u.id}" data-active="${u.active}">${u.active ? "Disable" : "Enable"}</button><button class="g" data-act="reset" data-id="${u.id}">Set password</button></td></tr>`).join("")}</tbody></table></div>
  <div class="two"><form class="card mt" id="uf"><h3>Add account</h3><label>Username<input name="username" required pattern="[a-z0-9._-]{3,32}"></label><label>Full name<input name="full_name" required maxlength="80"></label><label>Role<select name="role"><option value="staff">staff</option><option value="admin">admin</option></select></label><label>Password (10 or more characters)<input name="password" type="password" required minlength="10" autocomplete="new-password"></label><div class="acts"><button type="submit">Create account</button><span id="umsg"></span></div></form>
  <form class="card mt" id="sf"><h3>Add student</h3><label>Roll number or ID<input name="id" required pattern="[A-Za-z0-9_-]{3,24}"></label><label>Department<select name="department">${M.departments.map(d => `<option>${esc(d)}</option>`).join("")}</select></label><label>Year<select name="year"><option>1</option><option>2</option><option>3</option><option>4</option></select></label><div class="acts"><button type="submit">Add student</button><span id="smsg"></span></div><p class="mu mt" style="font-size:13px">Then open the student under Students to enter their data.</p></form></div>
  <h2>Recent activity</h2><div class="tw"><table><thead><tr><th>Time (UTC)</th><th>User</th><th>Action</th><th>Detail</th></tr></thead><tbody>${A.map(a => `<tr><td>${esc(a.at)}</td><td>${esc(a.username)}</td><td>${esc(a.action)}</td><td>${esc(a.detail)}</td></tr>`).join("")}</tbody></table></div>`;
}

const views = {"": overview, students, segments, method, admin};
const binds = {
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
  const r = location.hash.replace(/^#\/?/, ""), v = (r in views && (r !== "admin" || ROLE === "admin")) ? r : "";
  try { app.innerHTML = await views[v](); } catch (e) { app.innerHTML = `<div class="err">${esc(e.message)}</div>`; return; }
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#/" + v));
  if (binds[v]) binds[v]();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
(async () => { try { M = await api("/api/meta"); await load(); route(); } catch (e) { app.innerHTML = `<div class="err">${esc(e.message)}</div>`; } })();
})();
