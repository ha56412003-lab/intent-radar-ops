// 雷达扫描器（ego-browser 侧）v2 —— 三平台配置驱动
// CFG 由 run.py 注入：{platform, preset{...}, keyword, searchUrl, videos, rounds, out, outDir, space, preScrolls, scrollWaitMs}
const fs = await import("node:fs/promises");
const CFG = __CFG__;
const P = CFG.preset;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...a) => console.log("[scan]", ...a);

const task = await taskSpace(CFG.space);
const page = task.page("p1");
const out = {
  keyword: CFG.keyword,
  platform: CFG.platform,
  platformName: P.label,
  scannedAt: new Date().toISOString(),
  videos: [],
};

/** 逐个试一组选择器，返回第一个有结果的那个 */
async function firstMatch(sels) {
  return await page.evaluate((a) => {
    for (const s of a.sels) {
      const n = document.querySelectorAll(s).length;
      if (n) return { sel: s, count: n };
    }
    return { sel: null, count: 0 };
  }, { sels });
}

/** 点开第 idx 个卡片：每次重查 + 重打标记（关闭详情会重建 DOM） */
async function openCard(idx) {
  const card = await page.evaluate((a) => {
    document.querySelectorAll("[data-radar-idx]").forEach((e) => e.removeAttribute("data-radar-idx"));
    let els = [];
    for (const s of a.sels) {
      els = Array.from(document.querySelectorAll(s));
      if (els.length) break;
    }
    const el = els[a.idx];
    if (!el) return null;
    const text = (el.innerText || "").replace(/\s+/g, " ").trim();
    // 小红书搜索页首块常是「大家都在搜」热搜块，不是笔记，点了不会跳转
    if (/^大家都在搜/.test(text)) return { skip: true, text: text.slice(0, 60) };
    el.setAttribute("data-radar-idx", "T");
    el.scrollIntoView({ block: "center" });
    return { text: text.slice(0, 160) };
  }, { sels: P.cardSels, idx });
  if (!card) return null;
  if (P.useRealMouse) {
    // 快手这类站内浮层播放器：DOM click 无效，必须真实鼠标事件
    const box = await page.evaluate(() => {
      const el = document.querySelector('[data-radar-idx="T"]');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
    });
    if (!box) return null;
    await page.cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y });
    await sleep(150);
    await page.cdp("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", clickCount: 1 });
    await sleep(120);
    await page.cdp("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.x, y: box.y, button: "left", clickCount: 1 });
  } else {
    await page.click('[data-radar-idx="T"]', { force: true, timeout: 8000, label: "打开内容" });
  }
  return card;
}

/** 展开评论区（有的平台详情页默认就显示）；返回 "ok" / "empty" / false */
async function openComments() {
  const check = async () => await page.evaluate((s) => !!document.querySelector(s), P.commentItemSel);
  if (await check()) return "ok";
  if (P.noCommentSel) {
    const isEmpty = await page.evaluate((s) => !!document.querySelector(s), P.noCommentSel);
    if (isEmpty) return "empty";
  }
  if (!P.commentIconSel) return false;
  for (const n of [0, 1]) {
    try {
      await page.click(`${P.commentIconSel} >> nth=${n}`, { force: true, timeout: 4000, label: "展开评论" });
      await sleep(2200);
      if (await check()) return "ok";
    } catch (e) {
      /* 试下一个 */
    }
  }
  if (await check()) return "ok";
  if (P.noCommentSel) {
    const isEmpty = await page.evaluate((s) => !!document.querySelector(s), P.noCommentSel);
    if (isEmpty) return "empty";
  }
  return false;
}

/** 滚动评论容器 N 屏，再抓文本；scrollTop 不生效时用 CDP 滚轮兜底 */
async function grabComments(rounds) {
  const cnt = async () => await page.evaluate((s) => document.querySelectorAll(s).length, P.commentItemSel);
  await sleep(2000); // 等评论区完成布局，否则 scrollHeight 还没长起来，滚不动
  let prev = await cnt();
  for (let i = 0; i < rounds; i++) {
    const diag = await page.evaluate((sels) => {
      let el = null;
      for (const s of sels) {
        el = document.querySelector(s);
        if (el) break;
      }
      if (!el) {
        window.scrollBy(0, 1200);
        return { found: false, scrolled: "window" };
      }
      const info = { found: true, cls: String(el.className || "").slice(0, 40), sh: el.scrollHeight, ch: el.clientHeight };
      let target = null;
      for (const c of [el, ...el.querySelectorAll("*")]) {
        if (c.scrollHeight > c.clientHeight + 50 && c.clientHeight > 100) {
          target = c;
          break;
        }
      }
      if (target) {
        target.scrollTop = target.scrollHeight;
        info.targetCls = String(target.className || "").slice(0, 40);
        info.mode = "inner";
      } else {
        // 评论区自己不可滚（小红书整页滚），推页面
        window.scrollBy(0, 1200);
        info.mode = "window";
      }
      const r = el.getBoundingClientRect();
      // 评论区一般在页面右侧，取右边界附近，避免滚轮落到左侧笔记内容上
      info.box = {
        x: Math.round(Math.min(r.right - 60, window.innerWidth - 40)),
        y: Math.round(window.innerHeight * 0.65),
      };
      return info;
    }, P.commentListSels);
    if (i === 0) log(`    滚动诊断: ${JSON.stringify(diag)}`);
    await sleep(CFG.scrollWaitMs);

    let now = await cnt();
    // 真实滚轮是最后手段：很多前端只监听 wheel，不理会 scrollTop
    if (P.useWheel !== false && (now <= prev || diag.mode === "window") && diag.box) {
      await page.cdp("Input.dispatchMouseEvent", {
        type: "mouseWheel",
        x: diag.box.x,
        y: diag.box.y,
        deltaX: 0,
        deltaY: 900,
        pointerType: "mouse",
      });
      await sleep(2600);
      now = await cnt();
    }
    if (now > prev) log(`    评论 ${prev} → ${now}`);
    if (now === prev && i > 0) break;
    prev = now;
  }
  return await page.evaluate((a) => {
    const items = Array.from(document.querySelectorAll(a.itemSel));
    const pick = (csv) => {
      if (!csv) return "";
      for (const one of csv.split(",")) {
        const el = document.querySelector(one.trim());
        if (el && (el.innerText || "").trim()) return (el.innerText || "").replace(/\s+/g, " ").trim();
      }
      return "";
    };
    const totalM = ((document.body.innerText || "").match(/(\d+)\s*条评论/) || [])[1];
    return {
      url: location.href,
      videoDesc: pick(a.descSel),
      author: pick(a.authorSel),
      commentTotal: totalM ? parseInt(totalM, 10) : null,
      comments: items.map((el) => (el.innerText || "").replace(/[ \t]+/g, " ").trim()).filter(Boolean),
    };
  }, { itemSel: P.commentItemSel, descSel: P.descSel, authorSel: P.authorSel });
}

async function closeDetail() {
  try {
    if (P.closeSel) {
      try {
        await page.click(P.closeSel, { force: true, timeout: 2500, label: "关闭详情" });
        await sleep(1200);
      } catch (e) {
        /* 落到下一步 */
      }
    }
    let still = await page.evaluate((s) => (s ? !!document.querySelector(s) : false), P.detailOpenSel);
    if (still) {
      await page.keyboard.press(P.closeKey || "Escape");
      await sleep(1200);
      still = await page.evaluate((s) => (s ? !!document.querySelector(s) : false), P.detailOpenSel);
    }
    if (still) {
      await page.goto(CFG.searchUrl);
      await page.waitForLoadState("load");
      await sleep(2500);
    }
  } catch (e) {
    /* 忽略 */
  }
}

async function scanKeyword() {
  await page.goto(CFG.searchUrl);
  await page.waitForLoadState("load");
  await sleep(P.firstWaitMs || 4000);

  for (let i = 0; i < CFG.preScrolls; i++) {
    await page.evaluate((y) => window.scrollTo(0, y), (i + 1) * 800);
    await sleep(2000);
  }

  const found = await firstMatch(P.cardSels);
  const guard = await page.evaluate(() => {
    const b = (document.body.innerText || "").replace(/\s+/g, " ");
    return /扫码登录|立即登录|登录即可|设备登录超限|手机号登录|登录后查看/.test(b);
  });

  if (!found.count) {
    if (guard) {
      log(`⚠ ${P.label} 未登录（或登录失效）：页面只有登录框，先在 ego 里扫码登录再跑`);
      out.loginRequired = true;
    } else {
      log(`⚠ ${P.label} 没找到结果卡片（选择器可能过期，或该关键词没结果）`);
      out.noCards = true;
    }
  }

  const want = Math.min(CFG.videos, found.count);
  const maxAttempts = Math.min(found.count, want * 3);
  log(`关键词「${CFG.keyword}」${P.label}：卡片 ${found.count} 个（${found.sel || "无"}），目标 ${want} 个（最多试 ${maxAttempts} 个）`);
  if (!want) return;

  let okCount = 0;
  for (let i = 0; i < maxAttempts && okCount < want; i++) {
    let rec = { idx: i, ok: false, error: null };
    try {
      const card = await openCard(i);
      if (!card) {
        log(`  #${i} 拿不到卡片，跳过`);
        continue;
      }
      if (card.skip) {
        log(`  #${i} 跳过（非笔记卡片：${card.text}）`);
        continue;
      }
      rec.cardText = card.text;
      await sleep(P.detailWaitMs || 4000);
      const url = await page.url();
      const inDetail = P.detailDomSel
        ? await page.evaluate((s) => !!document.querySelector(s), P.detailDomSel)
        : new RegExp(P.detailRe).test(url);
      if (!inDetail) {
        rec.error = "未进入详情页: " + url.slice(0, 70);
      } else {
        const opened = await openComments();
        if (opened === "empty") {
          rec = { ...rec, ok: true, count: 0, comments: [], note: "无评论" };
          log(`  #${i} 无评论（跳过）`);
        } else if (opened !== "ok") {
          rec.error = "评论区没出现（可能无评论，或选择器过期）";
        } else {
          const d = await grabComments(CFG.rounds);
          rec = { ...rec, ...d, ok: true, count: d.comments.length };
          log(`  #${i} ${d.author || "?"} 抓到 ${d.comments.length} 条评论${d.commentTotal ? `（该内容共 ${d.commentTotal} 条）` : ""}`);
        }
      }
    } catch (e) {
      rec.error = String(e.message || e).slice(0, 160);
      log(`  #${i} 失败: ${rec.error}`);
    }
    out.videos.push(rec);
    if (rec.ok) okCount++;
    await closeDetail();
    await sleep(1500);
  }
}

try {
  await scanKeyword();
} catch (e) {
  out.fatal = String(e.message || e);
  log("扫描中断: " + out.fatal);
}

await fs.mkdir(CFG.outDir, { recursive: true }).catch(() => {});
await fs.writeFile(CFG.out, JSON.stringify(out, null, 2), "utf8");
const okV = out.videos.filter((v) => v.ok);
const totalComments = okV.reduce((n, v) => n + (v.comments ? v.comments.length : 0), 0);
log(`已写入 ${CFG.out}（尝试 ${out.videos.length} 个，成功 ${okV.length} 个，共 ${totalComments} 条评论）`);
