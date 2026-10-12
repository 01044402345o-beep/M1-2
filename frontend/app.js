"use strict";

// ===== 설정 =====
const API_BASE = ((window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || "http://localhost:8000").replace(/\/+$/, "");
const REQUEST_TIMEOUT = 75_000; // Render 무료 티어 콜드 스타트(최대 ~1분) 고려
const WAKE_HINT_DELAY = 4_000;  // 이 시간 넘게 응답이 없으면 '서버 깨우는 중' 안내
const PAGE_SIZE = 30;

const $ = (sel) => document.querySelector(sel);
const state = {
  serverAwake: false,
  conversationId: null,
  conversationTitle: "새 대화",
  dataItems: [],     // 날짜 내림차순
  shown: PAGE_SIZE,
  editingId: null,
  stats: null,
  chart: null,
  sending: false,
};

// ===== 공통 유틸 =====
const fmt = (n, d = 2) => Number(n).toLocaleString("ko-KR", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? "" : d.toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c))); // textContent 로만 삽입 (XSS 방지)
  }
  return node;
}

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 2600);
}

function errorMessage(body, status) {
  if (!body) return `요청 실패 (HTTP ${status})`;
  if (Array.isArray(body.detail)) {
    // Pydantic 422 검증 오류
    return body.detail.map((d) => {
      const field = (d.loc || []).filter((x) => x !== "body").join(".");
      return field ? `${field}: ${d.msg}` : d.msg;
    }).join(" / ");
  }
  return body.detail || `요청 실패 (HTTP ${status})`;
}

function setServerStatus(kind, text) {
  const s = $("#server-status");
  s.className = `pill pill-${kind}`;
  s.textContent = text;
}

async function api(path, { method = "GET", body } = {}) {
  const ctrl = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT);
  const wakeTimer = setTimeout(() => { if (!state.serverAwake) $("#wake-banner").hidden = false; }, WAKE_HINT_DELAY);
  try {
    const res = await fetch(API_BASE + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    markAwake();
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error(errorMessage(data, res.status));
    return data;
  } catch (e) {
    if (e.name === "AbortError") throw new Error("서버 응답이 너무 늦습니다. 잠시 후 다시 시도해 주세요.");
    if (e instanceof TypeError) throw new Error("서버에 연결할 수 없습니다. (API 주소/CORS 설정을 확인하세요)");
    throw e;
  } finally {
    clearTimeout(timeout);
    clearTimeout(wakeTimer);
  }
}

function markAwake() {
  if (state.serverAwake) return;
  state.serverAwake = true;
  $("#wake-banner").hidden = true;
  setServerStatus("ok", "서버 연결됨");
}

// 페이지 진입 즉시 /health 호출해 잠든 서버를 미리 깨운다.
async function wakeServer() {
  try {
    await api("/health");
  } catch (e) {
    setServerStatus("err", "서버 연결 실패");
    $("#wake-banner").hidden = true;
    toast(e.message);
  }
}

// ===== 테마 =====
function effectiveTheme() {
  const t = document.documentElement.dataset.theme;
  if (t) return t;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function updateThemeIcon() {
  $("#theme-toggle").textContent = effectiveTheme() === "dark" ? "☀️" : "🌙";
}
$("#theme-toggle").addEventListener("click", () => {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) {}
  updateThemeIcon();
  renderChart();
});

// ===== 탭 =====
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((b) => {
    const on = b.dataset.tab === name;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on);
  });
  document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== `tab-${name}`));
  if (name === "history") loadHistory();
  if (name === "data") renderChart();
}
document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));

// ===== 데이터 요약 =====
const TREND_LABEL = { up: "▲ 상승", down: "▼ 하락", flat: "■ 보합", unknown: "-" };

async function loadSummary() {
  try {
    const s = await api("/api/data/summary");
    renderSummary(s);
  } catch (e) {
    $("#summary-cards").replaceChildren(el("div", { class: "card" }, el("div", { class: "label" }, "요약을 불러오지 못했습니다"), el("div", { class: "hint" }, e.message)));
  }
}

function renderSummary(s) {
  const m = s.metrics;
  const card = (label, value, hint) => el("div", { class: "card" },
    el("div", { class: "label" }, label), el("div", { class: "value" }, value), hint ? el("div", { class: "hint" }, hint) : null);
  if (!m) {
    $("#summary-cards").replaceChildren(card("데이터", "없음", "데이터 관리 탭에서 추가하세요"));
    $("#summary-trend").textContent = "";
    return;
  }
  const changeCls = m.change > 0 ? "up-text" : m.change < 0 ? "down-text" : "";
  $("#summary-cards").replaceChildren(
    card("기간", s.period.replace(" ~ ", " ~\n"), `${s.label}`),
    card("데이터 수", `${s.count.toLocaleString()}개`, "영업일 기준"),
    el("div", { class: "card" },
      el("div", { class: "label" }, `최근 값 (${m.latest_date})`),
      el("div", { class: "value" }, fmt(m.latest)),
      el("div", { class: `hint ${changeCls}` }, `기간 변화 ${m.change > 0 ? "+" : ""}${fmt(m.change)} (${m.change_pct > 0 ? "+" : ""}${m.change_pct}%)`)),
    card("평균", fmt(m.average), `표준편차 ${fmt(m.std)}`),
    card("최고", fmt(m.max), m.max_date),
    card("최저", fmt(m.min), m.min_date),
  );
  $("#summary-cards").querySelector(".card .value").style.whiteSpace = "pre-line";
  $("#summary-cards").querySelector(".card .value").style.fontSize = "0.95rem";
  $("#summary-trend").replaceChildren(
    el("span", { class: `badge ${s.trend_direction}` }, TREND_LABEL[s.trend_direction] || s.trend_direction),
    s.trend.replace(/^(상승|하락|보합)\s*/, ""),
  );
}
$("#summary-refresh").addEventListener("click", () => { loadSummary(); loadStatistics(); });

// ===== 통계 + 그래프 (보너스) =====
async function loadStatistics() {
  try {
    state.stats = await api("/api/data/statistics");
    renderStatsMini();
    renderChart();
  } catch (e) {
    $("#stats-mini").textContent = e.message;
  }
}

function renderStatsMini() {
  const s = state.stats;
  if (!s || !s.count) { $("#stats-mini").textContent = ""; return; }
  const item = (label, value) => el("span", {}, `${label} `, el("b", {}, value));
  $("#stats-mini").replaceChildren(
    item("7일 이동평균", fmt(s.ma7)),
    item("30일 이동평균", s.ma30 ? fmt(s.ma30) : "-"),
    item("일간 변동성", s.volatility != null ? `${s.volatility}%` : "-"),
    item("전월 대비", s.mom_change_pct != null ? `${s.mom_change_pct > 0 ? "+" : ""}${s.mom_change_pct}%` : "-"),
    s.biggest_rise ? item("최대 상승", `${s.biggest_rise.date} +${fmt(s.biggest_rise.change)}`) : null,
    s.biggest_drop ? item("최대 하락", `${s.biggest_drop.date} ${fmt(s.biggest_drop.change)}`) : null,
  );
}

function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

function renderChart() {
  if (!window.Chart || !state.stats || $("#tab-data").hidden) return;
  const series = state.stats.series;
  const text = cssVar("--muted"), grid = cssVar("--border");
  const data = {
    labels: series.map((p) => p.date),
    datasets: [
      { label: "일별 값", data: series.map((p) => p.value), borderColor: cssVar("--accent"), backgroundColor: "transparent", borderWidth: 1.5, pointRadius: 0, tension: 0.2 },
      { label: "7일 이동평균", data: series.map((p) => p.ma7), borderColor: "#f79009", borderWidth: 1.5, pointRadius: 0, borderDash: [4, 3] },
      { label: "30일 이동평균", data: series.map((p) => p.ma30), borderColor: "#12b76a", borderWidth: 2, pointRadius: 0 },
    ],
  };
  const options = {
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { labels: { color: text, boxWidth: 14 } },
      tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y == null ? "-" : fmt(c.parsed.y)}원` } },
    },
    scales: {
      x: { ticks: { color: text, maxTicksLimit: 8 }, grid: { color: grid } },
      y: { ticks: { color: text, callback: (v) => fmt(v, 0) }, grid: { color: grid } },
    },
  };
  if (state.chart) state.chart.destroy();
  state.chart = new Chart($("#chart"), { type: "line", data, options });
}

// ===== 데이터 관리 (CRUD) =====
async function loadData() {
  const params = new URLSearchParams({ order: "desc" });
  if ($("#q-start").value) params.set("start", $("#q-start").value);
  if ($("#q-end").value) params.set("end", $("#q-end").value);
  try {
    const res = await api(`/api/data?${params}`);
    state.dataItems = res.items;
    state.shown = PAGE_SIZE;
    renderTable();
  } catch (e) {
    $("#data-tbody").replaceChildren(el("tr", {}, el("td", { colspan: 5, class: "empty" }, e.message)));
  }
}

function renderTable(flashId) {
  const items = state.dataItems;
  const rows = items.slice(0, state.shown).map((it, i) => {
    const prev = items[i + 1]; // 내림차순이므로 다음 항목이 전일
    const diff = prev ? it.value - prev.value : null;
    const diffCell = diff == null ? "-" : `${diff > 0 ? "▲" : diff < 0 ? "▼" : ""} ${fmt(Math.abs(diff))}`;
    return el("tr", { class: it.id === flashId ? "flash" : "" },
      el("td", {}, it.date),
      el("td", { class: "num" }, fmt(it.value)),
      el("td", { class: `num ${diff > 0 ? "up-text" : diff < 0 ? "down-text" : ""}` }, diffCell),
      el("td", { class: "memo" }, it.memo || ""),
      el("td", {}, el("div", { class: "row-actions" },
        el("button", { class: "ghost-btn", type: "button", onclick: () => startEdit(it) }, "수정"),
        el("button", { class: "ghost-btn danger", type: "button", onclick: () => removeData(it) }, "삭제"))),
    );
  });
  $("#data-tbody").replaceChildren(...(rows.length ? rows : [el("tr", {}, el("td", { colspan: 5, class: "empty" }, "데이터가 없습니다."))]));
  $("#data-count").textContent = `${Math.min(state.shown, items.length)} / ${items.length}개 표시`;
  $("#data-more").hidden = state.shown >= items.length;
}
$("#data-more").addEventListener("click", () => { state.shown += PAGE_SIZE; renderTable(); });
$("#q-apply").addEventListener("click", loadData);
$("#q-reset").addEventListener("click", () => { $("#q-start").value = ""; $("#q-end").value = ""; loadData(); });

function formMsg(text, kind) {
  const m = $("#data-msg");
  m.textContent = text;
  m.className = `form-msg ${kind || ""}`;
}

function startEdit(it) {
  state.editingId = it.id;
  $("#data-form-title").textContent = `데이터 수정 (${it.date})`;
  $("#f-date").value = it.date;
  $("#f-value").value = it.value;
  $("#f-memo").value = it.memo || "";
  $("#data-submit").textContent = "수정 저장";
  $("#data-cancel").hidden = false;
  formMsg("");
  $("#data-form").scrollIntoView({ behavior: "smooth", block: "center" });
  $("#f-value").focus();
}

function resetForm() {
  state.editingId = null;
  $("#data-form").reset();
  const today = new Date().toLocaleDateString("sv-SE"); // 로컬 기준 YYYY-MM-DD
  $("#f-date").value = today;
  $("#f-date").max = today; // 서버도 미래 날짜를 거부한다 (Pydantic 검증)
  $("#data-form-title").textContent = "새 데이터 추가";
  $("#data-submit").textContent = "추가";
  $("#data-cancel").hidden = true;
}
$("#data-cancel").addEventListener("click", () => { resetForm(); formMsg(""); });

$("#data-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = { date: $("#f-date").value, value: Number($("#f-value").value), memo: $("#f-memo").value };
  const btn = $("#data-submit");
  btn.disabled = true;
  formMsg("저장 중…");
  try {
    const editing = state.editingId;
    const saved = editing
      ? await api(`/api/data/${editing}`, { method: "PUT", body })
      : await api("/api/data", { method: "POST", body });
    formMsg(editing ? `✔ ${saved.date} 데이터를 수정했습니다.` : `✔ ${saved.date} 데이터를 추가했습니다.`, "ok");
    resetForm();
    await afterDataChange(saved.id);
  } catch (err) {
    formMsg(`✖ ${err.message}`, "err");
  } finally {
    btn.disabled = false;
  }
});

async function removeData(it) {
  if (!confirm(`${it.date} (${fmt(it.value)}원) 데이터를 삭제할까요?`)) return;
  try {
    await api(`/api/data/${it.id}`, { method: "DELETE" });
    formMsg(`✔ ${it.date} 데이터를 삭제했습니다.`, "ok");
    if (state.editingId === it.id) resetForm();
    await afterDataChange();
  } catch (e) {
    formMsg(`✖ ${e.message}`, "err");
  }
}

async function afterDataChange(flashId) {
  await loadData();
  if (flashId) renderTable(flashId);
  loadSummary();
  loadStatistics();
}

// ===== 내보내기 (보너스) =====
function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = el("a", { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function exportRows() {
  return [...state.dataItems].reverse().map(({ date, value, memo }) => ({ date, value, memo: memo || "" }));
}
$("#export-csv").addEventListener("click", () => {
  const rows = exportRows();
  if (!rows.length) return toast("내보낼 데이터가 없습니다.");
  const esc = (v) => /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const csv = ["date,value,memo", ...rows.map((r) => [r.date, r.value, esc(r.memo)].join(","))].join("\n");
  download(`usd_krw_${new Date().toISOString().slice(0, 10)}.csv`, "﻿" + csv, "text/csv;charset=utf-8"); // BOM: 엑셀 한글 깨짐 방지
});
$("#export-json").addEventListener("click", () => {
  const rows = exportRows();
  if (!rows.length) return toast("내보낼 데이터가 없습니다.");
  download(`usd_krw_${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(rows, null, 2), "application/json");
});

// ===== 채팅 =====
function clearEmptyState() {
  const empty = $("#messages .empty-chat");
  if (empty) empty.remove();
}

function addMessage(role, content, { meta, toolCalls, error } = {}) {
  clearEmptyState();
  const node = el("div", { class: `msg ${role}${error ? " error" : ""}` },
    el("div", { class: "bubble" }, content),
    (meta || (toolCalls && toolCalls.length)) ? el("div", { class: "meta" },
      ...(toolCalls || []).map((t) => el("span", { class: "tool-tag", title: JSON.stringify(t.arguments) }, `🔧 ${t.name}`)),
      meta || "") : null,
  );
  $("#messages").append(node);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return node;
}

function addTyping() {
  clearEmptyState();
  const node = el("div", { class: "msg assistant" },
    el("div", { class: "bubble" }, el("span", { class: "typing" }, el("i"), el("i"), el("i")), "  데이터 요약을 반영해 답변을 생성하는 중…"));
  $("#messages").append(node);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return node;
}

function setChatTitle(title) {
  state.conversationTitle = title;
  $("#chat-title").textContent = title;
}

async function sendMessage(text) {
  if (state.sending || !text.trim()) return;
  state.sending = true;
  $("#chat-send").disabled = true;
  $("#chat-input").value = "";
  autoGrow();
  addMessage("user", text);
  const typing = addTyping();
  try {
    const res = await api("/api/chat", { method: "POST", body: { message: text, conversation_id: state.conversationId } });
    typing.remove();
    addMessage("assistant", res.reply, { toolCalls: res.tool_calls, meta: `요약 기간 ${res.summary_period} 반영 · 자동 저장됨` });
    if (!state.conversationId) setChatTitle(text.length > 30 ? text.slice(0, 30) + "…" : text);
    state.conversationId = res.conversation_id;
  } catch (e) {
    typing.remove();
    addMessage("assistant", `⚠ ${e.message}`, { error: true });
    $("#chat-input").value = text; // 실패 시 입력 복구
  } finally {
    state.sending = false;
    $("#chat-send").disabled = false;
    $("#chat-input").focus();
  }
}

function resetChat() {
  state.conversationId = null;
  setChatTitle("새 대화");
  $("#messages").replaceChildren(emptyChatNode.cloneNode(true));
  bindChips();
}

function bindChips() {
  document.querySelectorAll("#messages .chip").forEach((c) => c.addEventListener("click", () => sendMessage(c.textContent)));
}

function autoGrow() {
  const t = $("#chat-input");
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 140) + "px";
}

const emptyChatNode = $("#messages .empty-chat").cloneNode(true);
bindChips();
$("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendMessage($("#chat-input").value); });
$("#chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMessage($("#chat-input").value); }
});
$("#chat-input").addEventListener("input", autoGrow);
$("#new-chat").addEventListener("click", resetChat);

// ===== 대화 기록 =====
async function loadHistory() {
  const list = $("#history-list");
  list.replaceChildren(el("li", { class: "empty" }, "불러오는 중…"));
  try {
    const res = await api("/api/conversations");
    if (!res.items.length) {
      list.replaceChildren(el("li", { class: "empty" }, "저장된 대화가 없습니다. 채팅을 시작하면 자동으로 저장돼요."));
      return;
    }
    list.replaceChildren(...res.items.map((c) => el("li", { class: `history-item${c.id === state.conversationId ? " current" : ""}` },
      el("div", { class: "h-main", onclick: () => openConversation(c.id) },
        el("div", { class: "h-title" }, c.title),
        el("div", { class: "h-last" }, `${c.message_count}개 메시지 · ${fmtTime(c.updated_at)} · ${c.last_message}`)),
      el("div", { class: "h-actions" },
        el("button", { class: "ghost-btn", type: "button", onclick: () => openConversation(c.id) }, "불러오기"),
        el("button", { class: "ghost-btn danger", type: "button", onclick: () => deleteConversation(c) }, "삭제")),
    )));
  } catch (e) {
    list.replaceChildren(el("li", { class: "empty" }, e.message));
  }
}
$("#history-refresh").addEventListener("click", loadHistory);

async function openConversation(id) {
  try {
    const conv = await api(`/api/conversations/${id}`);
    state.conversationId = conv.id;
    setChatTitle(conv.title);
    $("#messages").replaceChildren();
    conv.messages.forEach((m) => addMessage(m.role, m.content, { meta: fmtTime(m.created_at) }));
    switchTab("chat");
    toast(`'${conv.title}' 대화를 불러왔습니다. 이어서 질문할 수 있어요.`);
  } catch (e) {
    toast(e.message);
  }
}

async function deleteConversation(c) {
  if (!confirm(`'${c.title}' 대화를 삭제할까요?`)) return;
  try {
    await api(`/api/conversations/${c.id}`, { method: "DELETE" });
    if (c.id === state.conversationId) resetChat();
    toast("대화를 삭제했습니다.");
    loadHistory();
  } catch (e) {
    toast(e.message);
  }
}

// ===== 시작 =====
updateThemeIcon();
resetForm();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { updateThemeIcon(); renderChart(); });
window.addEventListener("load", renderChart); // Chart.js(defer) 로드 이후 한 번 더 시도
wakeServer().then(() => {
  loadSummary();
  loadStatistics();
  loadData();
});
