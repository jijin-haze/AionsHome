/* ── Aion Common JS — 共享工具函数 ── */

const $ = id => document.getElementById(id);

// 在 iframe 子页面浮层中时，返回按钮改为关闭浮层回到聊天页
if (window.parent !== window) {
  document.addEventListener('DOMContentLoaded', () => {
    const backBtn = document.querySelector('.top-bar .back-btn');
    if (backBtn) backBtn.onclick = () => window.parent.closeSubPage();
  });
}

async function api(method, url, body) {
  const opts = { method, headers: {"Content-Type": "application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  return res.json();
}

function escHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

/* ── Toast ── */
let _toastTimer = null;
function showToast(msg) {
  let t = document.getElementById('commonToast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'commonToast';
    t.className = 'toast-msg';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.classList.remove('show'), 2000);
}

/* ── WebSocket（闹铃弹窗等全局事件） ── */
let _commonWs = null;
let _wsHandlers = {};

function connectCommonWS(extraHandler) {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  _commonWs = new WebSocket(`${proto}//${location.host}/ws`);
  _commonWs.onmessage = e => {
    const msg = JSON.parse(e.data);
    // 闹铃弹窗 — 全局
    if (msg.type === "schedule_alarm") {
      showAlarmPopup(msg.data);
      return;
    }
    // 监控提示音 — 全局
    if (msg.type === "monitor_alert") {
      const audio = new Audio('/public/AionMonitoralart.mp3');
      audio.play().catch(() => {});
      sendSystemNotification('📷 监控提醒', msg.data?.content || '哨兵监控即将分析');
      return;
    }
    // 页面自定义处理
    if (extraHandler) extraHandler(msg);
  };
  _commonWs.onclose = () => setTimeout(() => connectCommonWS(extraHandler), 2000);
}

/* ── 闹铃弹窗 ── */
let _alarmQueue = [];
function showAlarmPopup(data) {
  _alarmQueue.push(data);
  if (_alarmQueue.length === 1) _showNextAlarm();
  sendSystemNotification('⏰ 闹铃', data.content || '日程提醒');
}
function _showNextAlarm() {
  if (!_alarmQueue.length) return;
  // 确保 DOM 中有闹铃弹窗
  _ensureAlarmOverlay();
  const data = _alarmQueue[0];
  $("alarmContent").textContent = data.content || "日程提醒";
  $("alarmTime").textContent = data.trigger_at || "";
  $("alarmOverlay").classList.add("show");
}
function dismissAlarm() {
  $("alarmOverlay").classList.remove("show");
  _alarmQueue.shift();
  if (_alarmQueue.length) setTimeout(_showNextAlarm, 300);
}

function _ensureAlarmOverlay() {
  if ($("alarmOverlay")) return;
  const div = document.createElement('div');
  div.innerHTML = `
    <div class="alarm-overlay" id="alarmOverlay">
      <div class="alarm-box">
        <div class="alarm-icon">⏰</div>
        <h3>日程提醒</h3>
        <div class="alarm-content" id="alarmContent"></div>
        <div class="alarm-time" id="alarmTime"></div>
        <button onclick="dismissAlarm()">确认</button>
      </div>
    </div>`;
  document.body.appendChild(div.firstElementChild);
}

/* ── 系统通知 ── */
function sendSystemNotification(title, body) {
  if (!('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;
  try { new Notification(title, { body, icon: '/public/icon-192.png' }); } catch(e) {}
}

// 请求通知权限
if ('Notification' in window && Notification.permission === 'default') {
  Notification.requestPermission();
}
