// ==UserScript==
// @name         意向雷达 · 评论区助手（云南旅游 V1.0）
// @namespace    youha-intent-radar
// @version      1.0.7
// @description  在小红书/抖音/视频号/快手自动高亮意向评论、一键生成话术、记录已回、导出派单CSV。只读辅助，不发送任何消息。
// @author       悠哈 · 罗小黑
// @match        https://www.xiaohongshu.com/*
// @match        https://xiaohongshu.com/*
// @match        https://www.douyin.com/*
// @match        https://douyin.com/*
// @match        https://channels.weixin.qq.com/*
// @match        https://www.kuaishou.com/*
// @match        https://kuaishou.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

/* ============================================================
   ⛔⛔⛔  请勿修改本脚本  ⛔⛔⛔

   这段代码是工具本体，改错一个字符整个工具就失效。
   需要改词库/话术/平台 → 找罗小黑改，不要自己动手。

   万一改坏了怎么恢复：
   1) 把本脚本整条删掉
   2) 重新粘贴母本文件：
      E:\Hermes\company\projects\测试方向\意向雷达V1\意向雷达-评论区助手.user.js
   3) Ctrl+S 保存，关掉标签页重开

   面板版本：见面板标题右侧 v1.0.5
   ============================================================ */

(function () {
  "use strict";

  // ================== 配置区（改词库改这里） ==================
  // ==== INDUSTRY-PACK-START ====  ← 行业包生成器会替换这两行之间的全部内容
  const PROD_WORDS = [];  // 行业产品词（非空时：评论必须提到产品才算意向，防误报；空=不限制）
  const STAFF_DEFAULT = "员工";          // 员工名，首次可改
  const A_WORDS = ["拼团","报团","跟团","组团","结伴","找搭子","多少钱","价格","报价","费用","人均","团费","怎么报名","如何报名","在哪报名","怎么参加","求带","包车","包团","私人团","小包团","定制行程","定制游","行程安排","帮我排","帮我做攻略","帮忙规划","几号出发","什么时候有团","最近有团吗","带老人","带爸妈","带小孩","亲子","一家几口","高反","会高反吗","纯玩","不购物","有没有购物"];
  const B_WORDS = ["求攻略","攻略求","有攻略吗","求推荐","怎么玩","怎么去","路线","行程","几天合适","玩几天","门票","住宿","住哪里","交通","求组队","有人一起吗","避坑","防坑","被坑","踩雷","淡季","旺季","几月去","最佳时间"];
  const RED_WORDS = ["微信","vx","V信","wechat","手机号","电话","二维码","加我好友"]; // 命中=该评论不建议接（可能是同行/灰产/高风险话术）

  const SCRIPTS = {
    "拼团": "我们有固定发团的纯玩小团，你大概几号方便、几个人？我看看能不能给你拼上，行程表发你看看～",
    "结伴": "我们有固定发团的纯玩小团，你大概几号方便、几个人？我看看能不能给你拼上～",
    "找搭子": "我们在组同期出发的小团，你几号方便？人数告诉我，我看看能不能拼上～",
    "钱": "费用看人数和天数差别挺大。你们几个人、想去哪几个地方？我按你的情况发一份明细，纯玩无购物的～",
    "报名": "报名很简单，告诉我人数和大致日期，我把行程安排和细节发你，你看了再决定～",
    "带老人": "带老人完全没问题，我们排过慢节奏版本：每天车程2小时内、不早起、不爬坡。告诉我老人年纪和天数，我给你排一版～",
    "带爸妈": "带爸妈玩很合适，我们排过慢节奏版本：不早起、不赶路、景点都选平缓的。告诉我天数，我给你排一版～",
    "带小孩": "亲子线路我们做过很多，节奏会放慢、加互动项目。孩子多大？玩几天？我给你推荐合适的走法～",
    "高反": "怕高反关键是行程顺序：先昆明→大理（海拔低）适应两三天，再上丽江/香格里拉，基本没反应。需要的话我发你防高反行程～",
    "定制": "可以定制。几个人、玩几天、想不想去雨崩/泸沽湖这种远线？我按你的节奏排一版行程和报价～",
    "包车": "包车看车型和天数，你们几个人？要跑哪几站？我发一份包车明细给你～",
    "攻略": "我主页合集里有按天数分的攻略（2天/5天/环线版），先看看，有不清楚的随时问我～",
    "求推荐": "看你想要哪种玩法：轻度假（大理+洱海）还是深度环线（丽江+香格里拉+泸沽湖）？告诉我天数，我给你推荐～",
    "避坑": "云南玩得舒不舒服主要看三点：行程节奏、隐形购物、司机服务。我写了篇避坑清单在主页，可以先对照～",
    "纯玩": "我们是纯玩无购物的，行程里没有任何店。你要几天、几个人？我发行程给你看看～",
    "几天": "看你想怎么玩：大理丽江5天经典线，加香格里拉7天，深度环线9-10天。你假期几天？我帮你选～",
    "门票": "热门景点门票建议提前约，我主页攻略里写了各点的预约方式和小贴士，可以对照着来～",
    "交通": "云南各城市间有高铁也有包车，看人数：2人高铁方便，4人以上包车反而划算。你的行程大概怎么走？"
  };
  // ==== INDUSTRY-PACK-END ====

  // 话术匹配：按评论命中词找最相关模板
  function pickScript(text) {
    for (const k of Object.keys(SCRIPTS)) {
      if (text.includes(k)) return SCRIPTS[k];
    }
    if (/(带老人|爸妈|小孩|亲子|一家)/.test(text)) return SCRIPTS["带老人"];
    if (/(拼|结伴|搭子|组队)/.test(text)) return SCRIPTS["拼团"];
    if (/(钱|价格|费用|报价|人均)/.test(text)) return SCRIPTS["钱"];
    if (/(攻略|怎么玩|路线|行程)/.test(text)) return SCRIPTS["攻略"];
    return "你好呀～看到你对云南感兴趣！你们几个人、大概什么时候方便？我按你的情况给你排个行程参考～";
  }

  // ================== 状态存储 ==================
  const LS_KEY = "yhradar_records_v1";
  function loadRecords() { try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch (e) { return []; } }
  function saveRecords(arr) { localStorage.setItem(LS_KEY, JSON.stringify(arr)); }
  function staffName() { return localStorage.getItem("yhradar_staff") || STAFF_DEFAULT; }

  function findWords(text, words) {
    const hit = [];
    for (const w of words) if (text.includes(w)) hit.push(w);
    return hit;
  }
  function grade(text) {
    if (findWords(text, RED_WORDS).length) return "R"; // 高风险话术，不建议接
    // 产品词闸门：配了产品词就要求评论必须提到产品（防止「多少钱」这种泛词误报）
    if (PROD_WORDS.length && !findWords(text, PROD_WORDS).length) return null;
    if (findWords(text, A_WORDS).length) return "A";
    if (findWords(text, B_WORDS).length) return "B";
    return null;
  }

  // ================== 评论扫描（只读 DOM，不改动平台逻辑） ==================
  const marked = new WeakSet();
  let counts = { A: 0, B: 0, R: 0 };

  // 跳过导航/侧边栏/工具栏里的文字（视频号后台这类管理页文字多，不排除会误报）
  function inChrome(node) {
    let el = node.parentElement, depth = 0;
    while (el && depth < 8) {
      const tag = el.tagName || "";
      const cls = String(el.className || "") + " " + String(el.id || "");
      if (/^(NAV|ASIDE|HEADER|FOOTER)$/.test(tag)) return true;
      if (/(sidebar|side-bar|sider|menu|navbar|nav-|header|breadcrumb|toolbar|tabbar|tab-bar|topbar|data-card)/i.test(cls)) return true;
      el = el.parentElement; depth++;
    }
    return false;
  }

  function scan() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const targets = [];
    while (walker.nextNode()) {
      const n = walker.currentNode;
      if (!n.textContent || n.textContent.length < 4 || n.textContent.length > 500) continue;
      if (inChrome(n)) continue;
      const g = grade(n.textContent);
      if (!g) continue;
      const box = n.parentElement && n.parentElement.closest("div,span,p") ? n.parentElement.closest("div,span,p") : n.parentElement;
      if (!box || marked.has(box)) continue;
      targets.push({ node: n, box, text: n.textContent.trim(), g });
    }
    for (const t of targets) {
      marked.add(t.box);
      counts[t.g] = (counts[t.g] || 0) + 1;
      const color = t.g === "A" ? "#ff4d4f" : (t.g === "B" ? "#faad14" : "#999");
      t.box.style.outline = "2px solid " + color;
      t.box.style.borderRadius = "6px";
      // ★ 关键：不绑点击、不拦事件 —— 评论本身照常点击跳转
      // 改成右上角一个小圆点按钮，只有点它才生成话术
      if (getComputedStyle(t.box).position === "static") t.box.style.position = "relative";
      const dot = document.createElement("span");
      dot.textContent = "话";
      dot.title = "点这里生成话术（点评论本身正常跳转）";
      dot.style.cssText = "position:absolute;top:-7px;right:-6px;width:16px;height:16px;line-height:16px;" +
        "text-align:center;font-size:9.5px;font-family:sans-serif;background:" + color + ";color:#fff;" +
        "border-radius:50%;cursor:pointer;z-index:10;user-select:none;box-shadow:0 1px 3px rgba(0,0,0,.35);";
      dot.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        showPanel(t.text, t.g);
      }, true);
      t.box.appendChild(dot);
    }
    updateBadge();
  }

  // ================== 侧边面板 UI ==================
  let panelEl = null, currentText = "", currentGrade = "";

  function buildPanel() {
    if (document.getElementById("yhradar-panel")) return;
    panelEl = document.createElement("div");
    panelEl.id = "yhradar-panel";
    panelEl.style.cssText = "position:fixed;right:12px;top:80px;width:300px;background:#fff;border:1px solid #d9d9d9;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.15);z-index:999999;font-size:13px;color:#222;overflow:hidden;";
    panelEl.innerHTML = `
      <div id="yr-head" style="background:#14342B;color:#fff;padding:8px 12px;font-weight:700;display:flex;justify-content:space-between;align-items:center;cursor:pointer;">
        <span>🎯 意向雷达 <span id="yr-badge" style="font-size:11px;font-weight:400;">A:0 B:0</span><span style="font-size:9.5px;font-weight:400;opacity:.65;margin-left:4px;">v1.0.7</span></span>
        <span id="yr-min" style="font-size:11px;font-weight:400;">收起</span>
      </div>
      <div id="yr-body" style="padding:10px 12px;">
        <div style="color:#888;font-size:11px;margin-bottom:6px;">员工：<span id="yr-staff" style="color:#14342B;font-weight:700;"></span>（点击改名）</div>
        <div style="max-height:120px;overflow:auto;border:1px solid #eee;border-radius:6px;padding:6px;background:#fafafa;" id="yr-comment"></div>
        <textarea id="yr-draft" rows="4" style="width:100%;margin-top:8px;border:1px solid #d9d9d9;border-radius:6px;padding:6px;font-size:12px;box-sizing:border-box;" placeholder="点击红色/黄色评论后，这里出话术"></textarea>
        <div style="display:flex;gap:6px;margin-top:8px;">
          <button id="yr-copy" style="flex:1;padding:6px;border:none;border-radius:6px;background:#14342B;color:#fff;cursor:pointer;">复制话术</button>
          <button id="yr-done" style="flex:1;padding:6px;border:none;border-radius:6px;background:#B8860B;color:#fff;cursor:pointer;">已回复 ✓</button>
        </div>
        <button id="yr-export" style="width:100%;margin-top:6px;padding:6px;border:1px solid #d9d9d9;border-radius:6px;background:#fff;cursor:pointer;color:#666;">导出记录 CSV（汇报用）</button>
        <div style="color:#aaa;font-size:10px;margin-top:6px;line-height:1.5;">点评论右上角的彩色小圆点「话」生成话术；<b>点评论本身照常跳转，不受影响</b>。<br>只读辅助，不代发消息。</div>
      </div>`;
    document.body.appendChild(panelEl);

    document.getElementById("yr-staff").textContent = staffName();
    document.getElementById("yr-staff").onclick = function () {
      const n = prompt("输入员工名（用于派单统计）：", staffName());
      if (n) { localStorage.setItem("yhradar_staff", n); document.getElementById("yr-staff").textContent = n; }
    };

    // ===== 位置记忆 + 拖动（默认右上角，拖到哪记住哪） =====
    (function () {
      const POS_KEY = "yhradar_pos_v1";
      try {
        const saved = JSON.parse(localStorage.getItem(POS_KEY) || "null");
        if (saved && typeof saved.l === "number") {
          panelEl.style.left = saved.l + "px";
          panelEl.style.top = saved.t + "px";
          panelEl.style.right = "auto";
        }
      } catch (e) {}
      const head = document.getElementById("yr-head");
      let drag = null;
      head.style.cursor = "move";
      head.addEventListener("mousedown", function (e) {
        if (e.target && e.target.id === "yr-min") return;
        const r = panelEl.getBoundingClientRect();
        drag = { x: e.clientX - r.left, y: e.clientY - r.top };
        e.preventDefault();
      });
      document.addEventListener("mousemove", function (e) {
        if (!drag) return;
        panelEl.style.left = Math.max(0, e.clientX - drag.x) + "px";
        panelEl.style.top = Math.max(0, e.clientY - drag.y) + "px";
        panelEl.style.right = "auto";
      });
      document.addEventListener("mouseup", function () {
        if (!drag) return;
        drag = null;
        try {
          localStorage.setItem(POS_KEY, JSON.stringify({
            l: parseInt(panelEl.style.left, 10) || 0,
            t: parseInt(panelEl.style.top, 10) || 0
          }));
        } catch (e) {}
      });
      // 收起/展开：绑定在「收起」文字上，避免和拖动打架
      document.getElementById("yr-min").onclick = function (e) {
        e.stopPropagation();
        const b = document.getElementById("yr-body"), m = document.getElementById("yr-min");
        const hide = b.style.display !== "none";
        b.style.display = hide ? "none" : "block";
        m.textContent = hide ? "展开" : "收起";
      };
    })();

    document.getElementById("yr-copy").onclick = function () {
      const v = document.getElementById("yr-draft").value;
      if (!v) return;
      navigator.clipboard.writeText(v).then(function () {
        document.getElementById("yr-copy").textContent = "已复制 ✓";
        setTimeout(function () { document.getElementById("yr-copy").textContent = "复制话术"; }, 1200);
      });
    };
    document.getElementById("yr-done").onclick = function () {
      const rec = loadRecords();
      rec.push({
        time: new Date().toLocaleString("zh-CN"),
        staff: staffName(),
        platform: location.hostname.includes("douyin") ? "抖音" : (location.hostname.includes("weixin") ? "视频号" : (location.hostname.includes("kuaishou") ? "快手" : "小红书")),
        grade: currentGrade || "?",
        comment: (currentText || "").slice(0, 120),
        script: document.getElementById("yr-draft").value.slice(0, 200),
        url: location.href.split("?")[0]
      });
      saveRecords(rec);
      document.getElementById("yr-done").textContent = "已记录 " + rec.length + " 条 ✓";
      setTimeout(function () { document.getElementById("yr-done").textContent = "已回复 ✓"; }, 1200);
    };
    document.getElementById("yr-export").onclick = function () {
      const rec = loadRecords();
      if (!rec.length) { alert("暂无记录"); return; }
      const head = "时间,员工,平台,等级,原评论,使用话术,作品链接\n";
      const rows = rec.map(r => [r.time, r.staff, r.platform, r.grade, r.comment, r.script, r.url]
        .map(v => '"' + String(v).replace(/"/g, '""') + '"').join(",")).join("\n");
      const fname = "回复记录_" + staffName().replace(/[\\/:*?"<>|]/g, "") + "_" + new Date().toISOString().slice(0, 10) + ".csv";
      const btn = document.getElementById("yr-export");
      saveCsv(fname, head + rows).then(function (how) {
        if (how === "saved") { btn.textContent = "已保存 ✓"; }
        else if (how === "cancel") { btn.textContent = "已取消"; }
        else { btn.textContent = "已下载 ✓"; }
        setTimeout(function () { btn.textContent = "导出记录 CSV（汇报用）"; }, 1500);
      });
    };
  }

  // ================== 保存 CSV：优先「另存为」，不影响浏览器默认下载目录 ==================
  // 第一次选到汇总文件夹（data\_incoming），Chrome 会记住这个位置，以后点保存即可
  function saveCsv(filename, text) {
    const content = "\uFEFF" + text;   // BOM，Excel 打开不乱码
    function fallback() {
      try {
        const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        return "download";
      } catch (e) { return "fail"; }
    }
    if (window.showSaveFilePicker && window.isSecureContext) {
      try {
        return window.showSaveFilePicker({
          suggestedName: filename,
          types: [{ description: "CSV 文件", accept: { "text/csv": [".csv"] } }]
        }).then(function (handle) {
          return handle.createWritable().then(function (w) {
            return w.write(new Blob([content], { type: "text/csv;charset=utf-8" }))
              .then(function () { return w.close(); })
              .then(function () { return "saved"; });
          });
        }).catch(function (e) {
          if (e && e.name === "AbortError") return "cancel";
          return fallback();   // 不支持或被拦 → 退回普通下载
        });
      } catch (e) {
        return Promise.resolve(fallback());
      }
    }
    return Promise.resolve(fallback());
  }

  // ================== 触发机制（v1.0.2 重写） ==================
  // 抖音/小红书是单页应用（SPA）：从首页点进搜索页不会刷新页面，
  // 所以必须：① 全站注入 ② 监听 URL 变化 ③ 用 MutationObserver
  // 监听评论区 DOM 变化 ④ 滚动用捕获模式（评论区是独立滚动容器）

  let lastScan = 0;
  function throttledScan() {
    const now = Date.now();
    if (now - lastScan > 2500) { lastScan = now; scan(); }
  }

  // ① 评论区是独立滚动容器，window.scroll 抓不到 —— 用捕获模式监听所有滚动
  window.addEventListener("scroll", throttledScan, { passive: true, capture: true });

  // ② DOM 变化监听：新评论加载出来就自动扫（节流 2.5 秒）
  const mo = new MutationObserver(throttledScan);
  function startObserver() {
    if (document.body) mo.observe(document.body, { childList: true, subtree: true });
    else setTimeout(startObserver, 500);
  }
  startObserver();

  // ③ SPA 导航监听：抖音/小红书站内跳转不刷新页面，钩住 history
  ["pushState", "replaceState"].forEach(function (fn) {
    const orig = history[fn];
    history[fn] = function () {
      const r = orig.apply(this, arguments);
      setTimeout(throttledScan, 800);
      setTimeout(throttledScan, 2500);
      return r;
    };
  });
  window.addEventListener("popstate", function () { setTimeout(throttledScan, 800); });

  function showPanel(text, g) {
    buildPanel();
    const body = document.getElementById("yr-body");
    if (body && body.style.display === "none") document.getElementById("yr-head").click();
    currentText = text; currentGrade = g;
    document.getElementById("yr-comment").textContent = "【" + g + "级】" + text.slice(0, 120);
    document.getElementById("yr-draft").value = (g === "R")
      ? "⚠️ 此评论含高风险词（可能是同行/灰产），不建议回复。"
      : pickScript(text);
  }

  function updateBadge() {
    const b = document.getElementById("yr-badge");
    if (b) b.textContent = "A:" + (counts.A || 0) + " B:" + (counts.B || 0) + (counts.R ? " ⚠R:" + counts.R : "");
  }

  // 启动：面板常驻；扫描交给 MutationObserver + 滚动 + SPA 导航触发
  // （另外保留一个低频保底扫描，防止某些场景 DOM 无变化但内容更新）
  buildPanel();
  scan();
  setInterval(function () { scan(); }, 15000);

})();
