// ==UserScript==
// @name         获客采集器 · 作品清单 & 多平台私信
// @namespace    youha-collector
// @version      1.0.10
// @description  采集抖音/小红书/快手搜索页的作品清单、采集抖音/小红书/视频号/快手后台的私信列表，导出CSV喂给获客工作台。只读，不发送任何消息。
// @author       悠哈 · 罗小黑
// @match        https://www.douyin.com/*
// @match        https://douyin.com/*
// @match        https://creator.douyin.com/*
// @match        https://e.douyin.com/*
// @match        https://www.xiaohongshu.com/*
// @match        https://xiaohongshu.com/*
// @match        https://pro.xiaohongshu.com/*
// @match        https://creator.xiaohongshu.com/*
// @match        https://channels.weixin.qq.com/*
// @match        https://www.kuaishou.com/*
// @match        https://kuaishou.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

/* ============================================================
   ⛔⛔⛔  请勿修改本脚本  ⛔⛔⛔

   这段代码是工具本体，改错一个字符整个工具就失效。
   需要加平台/改抓取规则 → 找罗小黑改，不要自己动手。

   万一改坏了怎么恢复：
   1) 把本脚本整条删掉
   2) 重新粘贴母本文件：
      E:\Hermes\company\projects\测试方向\获客工作台\采集器_获客采集.user.js
   3) Ctrl+S 保存，关掉标签页重开

   面板版本：见面板标题右侧 v1.0.8
   ============================================================ */

(function () {
  "use strict";

  // —— 致命错误兜底：脚本挂掉也要把错误显示出来，而不是静默消失 ——
  function showFatal(err) {
    try {
      var d = document.createElement("div");
      d.style.cssText = "position:fixed;left:10px;top:10px;z-index:2147483647;background:#c0392b;color:#fff;" +
        "padding:10px 12px;font:11px/1.5 Consolas,monospace;border-radius:8px;max-width:430px;white-space:pre-wrap;" +
        "box-shadow:0 4px 16px rgba(0,0,0,.3)";
      d.textContent = "获客采集器出错（v1.0.6）\n" + (err && err.message ? err.message : String(err)) + "\n" +
        (err && err.stack ? String(err.stack).split("\n").slice(1, 4).join("\n") : "") +
        "\n\n← 把这块截图发给罗小黑";
      document.body.appendChild(d);
    } catch (e) {}
  }

  try {

  // ============ 模式识别 ============
  var host = location.hostname;
  var MODE = "";        // "list" = 作品清单 | "dm" = 私信
  var PLATFORM = "";

  if (/creator\.douyin\.com|e\.douyin\.com/.test(host)) {
    MODE = "dm"; PLATFORM = "抖音";
  } else if (/pro\.xiaohongshu\.com|creator\.xiaohongshu\.com/.test(host)) {
    MODE = "dm"; PLATFORM = "小红书";
  } else if (/channels\.weixin\.qq\.com/.test(host)) {
    MODE = "dm"; PLATFORM = "视频号";
  } else if (/douyin\.com/.test(host)) {
    MODE = "list"; PLATFORM = "抖音";
  } else if (/xiaohongshu\.com/.test(host)) {
    MODE = "list"; PLATFORM = "小红书";
  } else if (/kuaishou\.com/.test(host)) {
    MODE = "list"; PLATFORM = "快手";
  }

  if (!MODE) return;

  // ============ 工具 ============
  function fmt(n) {
    n = String(n).replace(/[,\s]/g, "");
    var m = n.match(/^([\d.]+)\s*万$/);
    if (m) return Math.round(parseFloat(m[1]) * 10000);
    m = n.match(/^([\d.]+)\s*亿$/);
    if (m) return Math.round(parseFloat(m[1]) * 100000000);
    m = n.match(/^([\d.]+)\s*w$/i);
    if (m) return Math.round(parseFloat(m[1]) * 10000);
    var v = parseInt(n.replace(/[^\d]/g, ""), 10);
    return isNaN(v) ? 0 : v;
  }

  function numFromText(t) {
    if (!t) return 0;
    var m = String(t).match(/([\d.]+\s*[万w亿])|(\d{1,})/);
    return m ? fmt(m[0]) : 0;
  }

  function txt(el) {
    return (el && el.innerText ? el.innerText : "").replace(/\s+/g, " ").trim();
  }

  function csvCell(v) {
    return '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"';
  }

  function fallbackDownload(filename, content) {
    var blob = new Blob([content], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  }

  // 保存 CSV：优先「另存为」对话框（不动浏览器默认下载目录），第一次选好位置后浏览器会记住
  function download(name, header, rows) {
    var lines = [header.join(",")];
    rows.forEach(function (r) { lines.push(r.map(csvCell).join(",")); });
    var filename = name + "_" + new Date().toISOString().slice(0, 10) + ".csv";
    var content = "\uFEFF" + lines.join("\n");
    if (window.showSaveFilePicker && window.isSecureContext) {
      try {
        window.showSaveFilePicker({
          suggestedName: filename,
          types: [{ description: "CSV 文件", accept: { "text/csv": [".csv"] } }]
        }).then(function (handle) {
          return handle.createWritable().then(function (w) {
            return w.write(new Blob([content], { type: "text/csv;charset=utf-8" }))
              .then(function () { return w.close(); });
          });
        }).catch(function (e) {
          if (e && e.name === "AbortError") return;   // 用户取消
          fallbackDownload(filename, content);
        });
        return;
      } catch (e) { /* 落到下面的普通下载 */ }
    }
    fallbackDownload(filename, content);
  }

  // 按选择器优先级取第一个非空文本
  function pickFirst(card, sels) {
    for (var i = 0; i < sels.length; i++) {
      var el = card.querySelector(sels[i]);
      if (el) {
        var t = txt(el);
        if (t && t.length > 1) return t;
      }
    }
    return "";
  }

  // 从卡片里尽力找作品链接（抖音/小红书多种形式）
  function findUrl(card) {
    var a = card.querySelector('a[href*="/video/"], a[href*="/note/"], a[href*="/explore/"], a[href*="/discovery/item/"]');
    if (a && a.href) return a.href.split("?")[0];
    var h = "";
    try { h = card.outerHTML.slice(0, 4000); } catch (e) { return ""; }
    var m = h.match(/\/video\/(\d{15,25})/) || h.match(/modal_id=(\d{15,25})/) ||
            h.match(/"(?:aweme_id|item_id|video_id)"\s*:\s*"?(\d{15,25})/);
    if (m) return "https://www.douyin.com/video/" + m[1];
    // 抖音常在 data-* 属性里塞 19 位作品 id
    var m3 = h.match(/data-[a-z-]*(?:id|aweme)[a-z-]*="(\d{15,25})"/i) ||
             h.match(/="(\d{19})"/) || h.match(/\b(\d{19})\b/);
    if (m3) return "https://www.douyin.com/video/" + m3[1];
    var m2 = h.match(/\/(?:explore|discovery\/item)\/([0-9a-f]{20,32})/i);
    if (m2) return "https://www.xiaohongshu.com/explore/" + m2[1];
    // 快手：/short-video/<photoId>，id 是字母数字混合
    var m4 = h.match(/\/short-video\/([0-9a-zA-Z_-]{10,32})/) || h.match(/data-photo-id="([0-9a-zA-Z_-]{10,32})"/);
    if (m4) return "https://www.kuaishou.com/short-video/" + m4[1];
    return "";
  }

  // 兜底策略：找出"重复出现的卡片容器"（SPA 页面没有 a 链接时用）
  function findCardParent() {
    var best = null, bestScore = 0;
    var all = document.querySelectorAll("div, ul, section");
    for (var i = 0; i < all.length && i < 4000; i++) {
      var el = all[i];
      if (el.id && el.id.indexOf("yc-") === 0) continue;
      var kids = el.children;
      if (!kids || kids.length < 3 || kids.length > 80) continue;
      var score = 0;
      for (var k = 0; k < kids.length; k++) {
        var t = txt(kids[k]);
        if (t.length >= 10 && t.length <= 400) score++;
      }
      if (score >= 3 && score > bestScore) { bestScore = score; best = el; }
    }
    return best ? { parent: best, score: bestScore } : null;
  }

  // 上一次采集的统计（没抓到东西时显示出来，方便定位问题）
  var lastStats = { links: 0, cards: 0, taken: 0, dup: 0, method: "" };

  // —— 去重：记住采集过的条目，下次自动跳过 ——
  var SEEN_KEY = "yhc_seen_v1";
  function loadSeen() {
    try { return JSON.parse(localStorage.getItem(SEEN_KEY) || "{}") || {}; }
    catch (e) { return {}; }
  }
  function saveSeen(map) {
    try {
      var keys = Object.keys(map);
      if (keys.length > 5000) {   // 防无限增长：只留最近 5000 条
        var trimmed = {};
        keys.slice(-5000).forEach(function (k) { trimmed[k] = 1; });
        map = trimmed;
      }
      localStorage.setItem(SEEN_KEY, JSON.stringify(map));
    } catch (e) {}
  }

  // ============ 采集：作品清单 ============
  function collectWorks() {
    var seen = {}, out = [];
    var links = document.querySelectorAll('a[href*="/video/"], a[href*="/note/"], a[href*="/explore/"], a[href*="/discovery/item/"]');
    lastStats = { links: links.length, cards: 0, taken: 0, method: "链接" };

    // ===== 路线 A：按链接找卡片 =====
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      var href = a.href.split("?")[0];
      if (seen[href]) continue;
      var card = a, best = null;
      for (var d = 0; d < 6 && card; d++) {
        card = card.parentElement;
        if (!card || card === document.body || card.tagName === "BODY" || card.tagName === "HTML") break;
        var t = txt(card);
        if (t.length >= 8 && t.length <= 400) { best = card; break; }
      }
      if (!best) continue;
      seen[href] = 1;
      lastStats.cards++;
      out.push(buildRow(best, href));
    }

    // ===== 路线 A2：按卡片 class 抓（小红书 .note-item，补全 A 漏掉的） =====
    var noteCards = document.querySelectorAll('.note-item, [class*="note-item"], [class*="noteItem"]');
    lastStats.noteCards = noteCards.length;
    if (noteCards.length) {
      if (!out.length) lastStats.method = "卡片class";
      for (var n = 0; n < noteCards.length; n++) {
        var nc = noteCards[n];
        // 只要最内层卡片，避免父子重复
        if (nc.querySelector('.note-item, [class*="note-item"]')) continue;
        var nt = txt(nc);
        if (nt.length < 5 || nt.length > 400) continue;
        var a0 = nc.querySelector('a');
        var nurl = (a0 && a0.href) ? a0.href.split("?")[0] : findUrl(nc);
        var nkey = nurl || nt.slice(0, 40);
        if (seen[nkey]) continue;
        seen[nkey] = 1;
        lastStats.cards++;
        out.push(buildRow(nc, nurl));
      }
    }

    // ===== 路线 B：没链接 → 找重复卡片容器（抖音/小红书 SPA 弹层） =====
    if (!out.length) {
      lastStats.method = "容器";
      var found = findCardParent();
      if (found) {
        var kids = found.parent.children;
        lastStats.cards = 0;
        lastStats.containerClass = String(found.parent.className || "").slice(0, 80);
        for (var j = 0; j < kids.length; j++) {
          var kid = kids[j];
          var kt = txt(kid);
          if (kt.length < 10 || kt.length > 400) continue;
          var url = findUrl(kid);
          var key = (url || kt.slice(0, 40));
          if (seen[key]) continue;
          seen[key] = 1;
          lastStats.cards++;
          out.push(buildRow(kid, url));
        }
      }
    }
    // ===== 统一去重：跳过以前采集过的条目 =====
    var seenStore = loadSeen();
    var dupCount = 0, fresh = [];
    for (var q = 0; q < out.length; q++) {
      var key = out[q].url || (out[q].platform + "|" + out[q].title);
      if (seenStore[key]) { dupCount++; continue; }
      seenStore[key] = 1;
      fresh.push(out[q]);
    }
    lastStats.dup = dupCount;
    saveSeen(seenStore);
    return fresh;
  }

  // 从卡片元素抽出标题/作者/点赞/评论
  function buildRow(cardEl, url) {
    var title = pickFirst(cardEl, ['[class*="title"]', '[class*="desc"]', '[class*="caption"]', 'h3', 'h2']);
    if (!title) {
      title = txt(cardEl).replace(/[\d.]+\s*[万w亿]/g, "").replace(/\d{2,}/g, "").trim();
    }
    var author = pickFirst(cardEl, ['[class*="author"] [class*="name"]', '[class*="nickname"]', '[class*="user"] [class*="name"]', '[class*="author"]', '[class*="name"]', '[class*="account"]']);
    if (!author) {
      var am = txt(cardEl).match(/@([^\s|]+)/);
      if (am) author = am[1];
    }
    author = author.replace(/^@/, "").replace(/[\d.]+\s*[万w亿]$/, "").trim();

    var nums = [];
    var numSel = '[class*="like"], [class*="count"], [class*="digg"], [class*="num"], [class*="view"]';
    var els = cardEl.querySelectorAll(numSel);
    for (var k = 0; k < els.length; k++) {
      if (els[k].querySelector(numSel)) continue;
      var v = numFromText(txt(els[k]));
      if (v) nums.push(v);
    }
    if (!nums.length) {
      var m = txt(cardEl).match(/[\d.]+\s*[万w亿]|\d{2,}/g) || [];
      nums = m.slice(-2).map(fmt);
    }

    return {
      date: new Date().toISOString().slice(0, 10),
      platform: PLATFORM,
      title: title.slice(0, 60),
      author: author.slice(0, 20),
      likes: nums[0] || 0,
      comments: nums.length > 1 ? nums[1] : 0,
      url: url || ""
    };
  }

  // ============ 采集：私信列表 ============
  function collectDM() {
    var out = [];
    var seen = {};
    // 启发式：找"看起来像私信条目"的可点击块
    // 特征：有 2-4 个子元素、文本 10-300 字、含时间或未读标记
    var cands = document.querySelectorAll('li, [class*="conversation"], [class*="session"], [class*="chat-item"], [class*="msg-item"], [class*="contact"], [class*="list-item"], [class*="dialogue"]');
    lastStats = { cands: cands.length, taken: 0 };
    for (var i = 0; i < cands.length; i++) {
      var el = cands[i];
      var t = txt(el);
      if (t.length < 8 || t.length > 300) continue;
      // 排除"装着其他条目"的外层容器（否则同一条会被采两次）
      if (el.querySelectorAll('li, [class*="item"], [class*="session"], [class*="conversation"]').length > 0) continue;
      var r = el.getBoundingClientRect();
      if (r.width < 80 || r.height < 24 || r.height > 160) continue;
      var key = t.slice(0, 60);
      if (seen[key]) continue;
      seen[key] = 1;
      // 昵称 / 消息 / 时间：优先按子元素拆（比整块文本靠谱）
      var kids = [];
      for (var k = 0; k < el.children.length; k++) {
        var kt = txt(el.children[k]);
        if (kt) kids.push(kt);
      }
      var name = "", msg = "";
      if (kids.length >= 2) {
        name = kids[0];
        msg = kids.slice(1).join(" ");
      } else {
        var lines = t.split(/\s{2,}|\n/).map(function (s) { return s.trim(); }).filter(Boolean);
        name = lines[0] || t.slice(0, 20);
        msg = lines.length > 1 ? lines.slice(1).join(" ") : "";
      }
      var tm = t.match(/(\d{1,2}:\d{2})|(昨天)|(\d{1,2}月\d{1,2}日)|(\d{4}-\d{2}-\d{2})/);
      var time = tm ? tm[0] : "";
      out.push({
        collected: new Date().toLocaleString("zh-CN"),
        platform: PLATFORM,
        name: name.slice(0, 30),
        last_msg: msg.slice(0, 120),
        time: time,
        raw: t.slice(0, 160)
      });
      if (out.length >= 200) break;
    }
    // ===== 去重：同一个人同一条最后消息只留一次 =====
    var seenStore2 = loadSeen();
    var dup2 = 0, fresh2 = [];
    for (var q2 = 0; q2 < out.length; q2++) {
      var k2 = out[q2].platform + "|" + out[q2].name + "|" + (out[q2].last_msg || "").slice(0, 40);
      if (seenStore2[k2]) { dup2++; continue; }
      seenStore2[k2] = 1;
      fresh2.push(out[q2]);
    }
    lastStats.dup = dup2;
    saveSeen(seenStore2);
    return fresh2;
  }

  // ============ 诊断：页面结构快照（DOM 不准时用，直接显示在面板里） ============
  function snapshot() {
    var L = [];
    L.push("URL: " + location.href);
    L.push("模式: " + MODE + " / " + PLATFORM);
    var links = document.querySelectorAll('a[href*="/video/"], a[href*="/note/"], a[href*="/explore/"], a[href*="/discovery/item/"]');
    L.push("作品链接(a标签): " + links.length);
    // data-e2e 属性（抖音的测试属性，最可靠）
    var e2e = {};
    var e2eEls = document.querySelectorAll("[data-e2e]");
    for (var i = 0; i < e2eEls.length && i < 2000; i++) {
      var v = e2eEls[i].getAttribute("data-e2e");
      if (v) e2e[v] = (e2e[v] || 0) + 1;
    }
    var e2eStr = Object.keys(e2e).map(function (k) { return k + "×" + e2e[k]; }).join(", ");
    L.push("data-e2e: " + (e2eStr.slice(0, 300) || "(无)"));
    // 最佳卡片容器
    var found = findCardParent();
    if (found) {
      L.push("最佳容器 class: " + String(found.parent.className || "").slice(0, 100));
      L.push("容器 tag: " + found.parent.tagName + " · 子元素 " + found.parent.children.length + " 个 · 命中 " + found.score);
      var kids = found.parent.children, shown = 0;
      for (var j = 0; j < kids.length && shown < 3; j++) {
        var kt = txt(kids[j]);
        if (kt.length < 10 || kt.length > 400) continue;
        L.push("── 卡片 " + (shown + 1) + " class=" + String(kids[j].className || "").slice(0, 60));
        L.push("   文本: " + kt.slice(0, 120));
        L.push("   HTML: " + String(kids[j].outerHTML || "").slice(0, 260));
        shown++;
      }
    } else {
      L.push("最佳容器: 没找到（页面上没有 ≥3 个相似子块）");
      // 兜一下：列出页面上 class 最多的三个
      var cnt = {};
      var els = document.querySelectorAll("div[class]");
      for (var q = 0; q < els.length && q < 3000; q++) {
        var c = String(els[q].className || "").slice(0, 50);
        if (c) cnt[c] = (cnt[c] || 0) + 1;
      }
      var top = Object.keys(cnt).sort(function (a, b) { return cnt[b] - cnt[a]; }).slice(0, 5);
      L.push("最常见 class: " + top.map(function (k) { return k + "×" + cnt[k]; }).join(" | "));
    }
    return L.join("\n");
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // ============ 面板 ============
  var panel, cnt = 0;

  function build() {
    if (document.getElementById("yc-panel")) return;
    panel = document.createElement("div");
    panel.id = "yc-panel";
    var defaultTop = window.innerHeight > 900 ? 470 : Math.max(300, window.innerHeight - 420);
    panel.style.cssText = "position:fixed;right:12px;top:" + defaultTop + "px;width:290px;background:#fff;border:1px solid #d9d9d9;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.16);z-index:999999;font-size:12.5px;color:#222;overflow:hidden;";
    var title = MODE === "list" ? "📡 作品清单采集" : "💬 私信采集";
    var tip = MODE === "list" ? "在搜索结果页/精选页/主页点「采集」" : "在私信管理页点「采集」";
    panel.innerHTML =
      '<div id="yc-head" style="background:#14342B;color:#fff;padding:8px 12px;font-weight:700;display:flex;justify-content:space-between;cursor:pointer;">' +
        '<span>' + title + ' <span id="yc-cnt" style="font-size:11px;font-weight:400;"></span>' +
        '<span style="font-size:9.5px;font-weight:400;opacity:.65;margin-left:4px;">v1.0.10</span></span>' +
        '<span id="yc-min" style="font-size:11px;font-weight:400;">收起</span></div>' +
      '<div id="yc-body" style="padding:10px 12px;">' +
        '<div style="color:#888;font-size:10.5px;margin-bottom:7px;">' + PLATFORM + ' · ' + tip + '</div>' +
        '<button id="yc-go" style="width:100%;padding:8px;border:none;border-radius:6px;background:#14342B;color:#fff;cursor:pointer;font-size:13px;">采集当前页</button>' +
        '<div id="yc-list" style="max-height:150px;overflow:auto;margin-top:8px;font-size:11px;color:#555;line-height:1.6;"></div>' +
        '<button id="yc-export" style="width:100%;margin-top:6px;padding:7px;border:1px solid #d9d9d9;border-radius:6px;background:#fff;cursor:pointer;color:#666;font-size:12px;" disabled>导出 CSV（丢进工作台 data/）</button>' +
        '<button id="yc-diag" style="width:100%;margin-top:6px;padding:6px;border:1px dashed #ccc;border-radius:6px;background:#fafafa;cursor:pointer;color:#999;font-size:11px;">抓不到？点这里看页面结构（截图发我）</button>' +
        '<button id="yc-reset" style="width:100%;margin-top:6px;padding:5px;border:none;border-radius:6px;background:#f2f2f2;cursor:pointer;color:#999;font-size:10.5px;">清空去重记录（下次重新采集全部）</button>' +
        '<div style="color:#aaa;font-size:10px;margin-top:7px;line-height:1.5;">只读采集，不点任何按钮、不发任何消息。</div>' +
      '</div>';
    document.body.appendChild(panel);

    var data = [];

    // 标题栏：可拖动 + 记住位置；收起按钮单独绑
    (function () {
      var POS_KEY = "yhc_pos_v1";
      try {
        var saved = JSON.parse(localStorage.getItem(POS_KEY) || "null");
        if (saved && typeof saved.l === "number") {
          panel.style.left = saved.l + "px";
          panel.style.top = saved.t + "px";
          panel.style.right = "auto";
        }
      } catch (e) {}
      var head = document.getElementById("yc-head");
      var drag = null;
      head.style.cursor = "move";
      head.addEventListener("mousedown", function (e) {
        if (e.target && e.target.id === "yc-min") return;
        var r = panel.getBoundingClientRect();
        drag = { x: e.clientX - r.left, y: e.clientY - r.top };
        e.preventDefault();
      });
      document.addEventListener("mousemove", function (e) {
        if (!drag) return;
        panel.style.left = Math.max(0, e.clientX - drag.x) + "px";
        panel.style.top = Math.max(0, e.clientY - drag.y) + "px";
        panel.style.right = "auto";
        panel.style.bottom = "auto";
      });
      document.addEventListener("mouseup", function () {
        if (!drag) return;
        drag = null;
        try {
          localStorage.setItem(POS_KEY, JSON.stringify({
            l: parseInt(panel.style.left, 10) || 0,
            t: parseInt(panel.style.top, 10) || 0
          }));
        } catch (e) {}
      });
      document.getElementById("yc-min").onclick = function (e) {
        e.stopPropagation();
        var b = document.getElementById("yc-body"), m = document.getElementById("yc-min");
        var hide = b.style.display !== "none";
        b.style.display = hide ? "none" : "block";
        m.textContent = hide ? "展开" : "收起";
      };
    })();

    document.getElementById("yc-go").onclick = function () {
      var box = document.getElementById("yc-list");
      try {
        data = MODE === "list" ? collectWorks() : collectDM();
        lastStats.taken = data.length;
        var cntTxt = data.length ? "新增 " + data.length + " 条" : "";
        if (lastStats.dup) cntTxt += (cntTxt ? " · " : "") + "跳过重复 " + lastStats.dup;
        document.getElementById("yc-cnt").textContent = cntTxt;
        document.getElementById("yc-export").disabled = !data.length;
        if (!data.length) {
          var s = lastStats;
          if (s.dup) {
            box.innerHTML = '<span style="color:#c0392b">没有新内容。</span><br>' +
              '<span style="color:#666;font-size:10.5px">这一页的 ' + s.dup + ' 条之前都采过了（已自动去重）。<br>' +
              '想重新采全部，点最下面「清空去重记录」。</span>';
          } else {
          var diag = MODE === "list"
            ? "找到作品链接 <b>" + s.links + "</b> 个 · 成功识别卡片 <b>" + s.cards + "</b> 个"
            : "找到候选条目 <b>" + (s.cands || 0) + "</b> 个";
          box.innerHTML = '<span style="color:#c0392b">没抓到。</span><br>' +
            '<span style="color:#666;font-size:10.5px">' + diag + '<br>' +
            (MODE === "list"
              ? (s.links === 0
                  ? '→ 一个链接都没有：页面还没加载完，往下滚一屏再点一次。'
                  : '→ 有链接但没识别出卡片：页面结构变了，点下面「导出页面结构」发我。')
              : '→ 没识别出私信条目：这个后台结构我还没适配，点下面「导出页面结构」发我。') +
            '</span>';
          }
        } else {
          box.innerHTML = data.slice(0, 8).map(function (d) {
            return MODE === "list"
              ? "· " + (d.title || "").slice(0, 24) + " <span style='color:#999'>赞" + d.likes + " 评" + d.comments + "</span>"
              : "· " + d.name + "：<span style='color:#999'>" + (d.last_msg || "").slice(0, 22) + "</span>";
          }).join("<br>") + (data.length > 8 ? "<br><span style='color:#999'>…共 " + data.length + " 条</span>" : "");
        }
      } catch (err) {
        box.innerHTML = '<span style="color:#c0392b">脚本报错：</span><br><span style="font-size:10.5px;color:#666">' +
          (err && err.message ? err.message : String(err)) + '<br>点下面「导出页面结构」发我即可。</span>';
      }
    };

    document.getElementById("yc-export").onclick = function () {
      if (!data.length) return;
      if (MODE === "list") {
        download("works_" + (PLATFORM === "抖音" ? "douyin" : "xhs"),
          ["日期", "平台", "标题", "作者", "点赞", "评论数", "链接"],
          data.map(function (d) { return [d.date, d.platform, d.title, d.author, d.likes, d.comments, d.url]; }));
      } else {
        download("inbox_" + (PLATFORM === "抖音" ? "douyin" : PLATFORM === "小红书" ? "xhs" : "channels"),
          ["采集时间", "平台", "客户昵称", "最后消息", "时间", "原始文本"],
          data.map(function (d) { return [d.collected, d.platform, d.name, d.last_msg, d.time, d.raw]; }));
      }
      document.getElementById("yc-export").textContent = "已导出 ✓（再点一次可重导）";
    };

    document.getElementById("yc-diag").onclick = function () {
      var s = snapshot();
      var box = document.getElementById("yc-list");
      box.style.maxHeight = "320px";
      box.style.fontFamily = "Consolas,monospace";
      box.style.fontSize = "9px";
      box.style.whiteSpace = "pre-wrap";
      box.innerHTML = esc(s.slice(0, 1600));
      // 同时下载完整版备查
      try {
        var blob = new Blob([s], { type: "text/plain;charset=utf-8" });
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "页面诊断_" + PLATFORM + "_" + new Date().toISOString().slice(0, 10) + ".txt";
        a.click();
      } catch (e) {}
    };

    document.getElementById("yc-reset").onclick = function () {
      try { localStorage.removeItem(SEEN_KEY); } catch (e) {}
      document.getElementById("yc-list").innerHTML =
        '<span style="color:#2e7d32">✅ 去重记录已清空。下次采集会把这一页所有作品重新收录一遍。</span>';
      document.getElementById("yc-cnt").textContent = "";
    };
  }

  // 启动
  build();
  // 私信页/搜索页常常是 SPA 后加载，滚动时重建面板（防止被覆盖）
  var lastBuild = Date.now();
  window.addEventListener("scroll", function () {
    if (Date.now() - lastBuild > 3000) { lastBuild = Date.now(); build(); }
  }, { passive: true, capture: true });

  } catch (__fatal) {
    showFatal(__fatal);
  }

})();
