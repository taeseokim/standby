(function () {
  "use strict";

  var STORAGE_KEY = "induk-vibecoding-standby-v1";

  /** @type {{nextNumber:number, waiting:Array<{number:number,name:string,issuedAt:number}>, serving:{number:number,name:string,issuedAt:number,calledAt:number}|null, servedToday:Array<{number:number,name:string}>, cancelledCount:number}} */
  var state = null;

  function freshState() {
    return {
      nextNumber: 1,
      waiting: [],
      serving: null,
      servedToday: [],
      cancelledCount: 0
    };
  }

  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return freshState();
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return freshState();
      return Object.assign(freshState(), parsed);
    } catch (e) {
      return freshState();
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      /* storage unavailable (private mode, quota) — state stays in-memory */
    }
  }

  // ---------- helpers ----------

  function $(sel) {
    return document.querySelector(sel);
  }

  function pad2(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function formatClock(d) {
    return pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds());
  }

  function formatElapsed(fromTs) {
    var mins = Math.floor((Date.now() - fromTs) / 60000);
    if (mins <= 0) return "방금 접수";
    if (mins < 60) return mins + "분 대기중";
    var h = Math.floor(mins / 60);
    var m = mins % 60;
    return h + "시간 " + m + "분 대기중";
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function ticket(n) {
    return "#" + String(n).padStart(3, "0");
  }

  // ---------- actions ----------

  function issueTicket(name) {
    var entry = {
      number: state.nextNumber,
      name: (name || "").trim().slice(0, 24),
      issuedAt: Date.now()
    };
    state.nextNumber += 1;
    state.waiting.push(entry);
    saveState();
    render();
    return entry;
  }

  function callSpecific(number) {
    var idx = state.waiting.findIndex(function (w) {
      return w.number === number;
    });
    if (idx === -1) return;
    if (state.serving) {
      // return current serving entry to the front of the waiting line
      state.waiting.unshift(state.serving);
    }
    var entry = state.waiting.splice(idx, 1)[0];
    entry.calledAt = Date.now();
    state.serving = entry;
    saveState();
    render();
  }

  function callNext() {
    if (state.waiting.length === 0) return;
    if (state.serving) {
      state.waiting.unshift(state.serving);
    }
    var entry = state.waiting.shift();
    entry.calledAt = Date.now();
    state.serving = entry;
    saveState();
    render();
  }

  function completeServing() {
    if (!state.serving) return;
    state.servedToday.unshift({ number: state.serving.number, name: state.serving.name });
    state.serving = null;
    saveState();
    render();
  }

  function cancelWaiting(number) {
    var idx = state.waiting.findIndex(function (w) {
      return w.number === number;
    });
    if (idx === -1) return;
    state.waiting.splice(idx, 1);
    state.cancelledCount += 1;
    saveState();
    render();
  }

  function resetAll() {
    if (!window.confirm("모든 대기열과 기록을 초기화할까요? 이 작업은 되돌릴 수 없습니다.")) return;
    state = freshState();
    saveState();
    render();
  }

  // ---------- render ----------

  function renderStats() {
    $("#stat-waiting").textContent = state.waiting.length;
    $("#stat-served").textContent = state.servedToday.length;
    $("#stat-issued").textContent = state.nextNumber - 1;
    $("#stat-serving").textContent = state.serving ? ticket(state.serving.number) : "—";
  }

  function renderServing() {
    var numEl = $("#serving-number");
    var nameEl = $("#serving-name");
    var metaEl = $("#serving-meta");
    var completeBtn = $("#btn-complete");

    if (state.serving) {
      var hasName = !!state.serving.name;
      nameEl.textContent = hasName ? state.serving.name : ticket(state.serving.number);
      nameEl.classList.remove("empty");
      numEl.textContent = ticket(state.serving.number);
      numEl.hidden = !hasName;
      metaEl.textContent = "호출 시각 " + formatClock(new Date(state.serving.calledAt));
      completeBtn.disabled = false;
    } else {
      nameEl.textContent = "대기 중인 참가자 없음";
      nameEl.classList.add("empty");
      numEl.hidden = true;
      metaEl.textContent = "\"다음 참가자 호출\"을 눌러 시작하세요";
      completeBtn.disabled = true;
    }

    $("#btn-call-next").disabled = state.waiting.length === 0;
  }

  function renderQueue() {
    var list = $("#queue-list");
    $("#queue-count-badge").textContent = state.waiting.length + "명 대기";
    if (state.waiting.length === 0) {
      list.innerHTML = '<li class="queue-empty">대기 중인 참가자가 없습니다.<br>번호표를 발급하면 이곳에 표시됩니다.</li>';
      return;
    }
    var html = state.waiting
      .map(function (w, i) {
        var waited = Math.floor((Date.now() - w.issuedAt) / 60000);
        var waitClass = waited >= 10 ? "wait long" : "wait";
        return (
          '<li class="queue-row">' +
          '<span class="pos">' + (i + 1) + '</span>' +
          '<span class="info">' +
          '<span class="name">' + (w.name ? escapeHtml(w.name) : "이름 미입력") + '</span>' +
          '<span class="meta">' +
          '<span class="num">' + ticket(w.number) + '</span>' +
          '<span class="' + waitClass + '">' + formatElapsed(w.issuedAt) + '</span>' +
          '</span>' +
          '</span>' +
          '<span class="row-actions">' +
          '<button class="btn-outline btn-sm" data-call="' + w.number + '">호출</button>' +
          '<button class="btn-danger-outline btn-sm" data-cancel="' + w.number + '">취소</button>' +
          '</span>' +
          '</li>'
        );
      })
      .join("");
    list.innerHTML = html;
  }

  function renderHistory() {
    var wrap = $("#history-list");
    $("#history-count-badge").textContent = state.servedToday.length + "건";
    if (state.servedToday.length === 0) {
      wrap.innerHTML = '<span class="history-empty">아직 완료된 체험이 없습니다.</span>';
      return;
    }
    wrap.innerHTML = state.servedToday
      .slice(0, 40)
      .map(function (h) {
        var label = h.name ? escapeHtml(h.name) : ticket(h.number);
        return '<li class="history-chip">' + label + '</li>';
      })
      .join("");
  }

  function render() {
    renderStats();
    renderServing();
    renderQueue();
    renderHistory();
  }

  // ---------- clock ----------

  function tickClock() {
    $("#clock").textContent = formatClock(new Date());
  }

  // ---------- wire up ----------

  function init() {
    state = loadState();
    render();
    tickClock();
    setInterval(tickClock, 1000);
    setInterval(function () {
      renderQueue();
      renderServing();
    }, 15000);

    $("#issue-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var input = $("#issue-name");
      var entry = issueTicket(input.value);
      input.value = "";
      input.focus();
      var numEl = $("#serving-number");
      void numEl; // ticket issued silently into the queue; no forced call
      void entry;
    });

    $("#btn-call-next").addEventListener("click", callNext);
    $("#btn-complete").addEventListener("click", completeServing);
    $("#btn-reset").addEventListener("click", resetAll);

    $("#queue-list").addEventListener("click", function (e) {
      var callBtn = e.target.closest("[data-call]");
      if (callBtn) {
        callSpecific(Number(callBtn.getAttribute("data-call")));
        return;
      }
      var cancelBtn = e.target.closest("[data-cancel]");
      if (cancelBtn) {
        cancelWaiting(Number(cancelBtn.getAttribute("data-cancel")));
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
