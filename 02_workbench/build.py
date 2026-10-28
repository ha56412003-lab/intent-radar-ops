# -*- coding: utf-8 -*-
"""获客工作台 · build.py
零依赖（只要 Python 3.9+）。读 data/ 目录，生成 site/ 静态页面。
用法：python build.py
"""
import json
import csv
import os
import sys
import html
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"

# ============ 读数据 ============
def read_json(name, default=None):
    p = DATA / name
    if not p.exists():
        return default if default is not None else []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"warning: {name} 读取失败 {e}", file=sys.stderr)
        return default if default is not None else []

def read_csv_glob(pattern):
    """读 data/ 和 data/_incoming/ 下所有匹配的文件（多台电脑各自导出时，统一丢进 _incoming）"""
    rows = []
    files = []
    for base in (DATA, DATA / "_incoming"):
        if base.exists():
            files.extend(sorted(base.glob(pattern)))
    for p in files:
        try:
            with open(p, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    r["_src"] = p.name
                    rows.append(r)
        except Exception as e:
            print(f"warning: {p.name} 解析失败 {e}", file=sys.stderr)
    return rows

def read_replies():
    """雷达导出的回复记录：兼容新文件名（回复记录_员工_日期.csv）和旧文件名（replies_*.csv）"""
    rows = []
    for pat in ("replies*.csv", "回复记录_*.csv"):
        rows.extend(read_csv_glob(pat))
    return rows

def to_int(x):
    try:
        return int(float(str(x).replace(",", "").replace(" ", "") or 0))
    except Exception:
        return 0

works = read_json("works.json")
staff = read_json("staff.json")
leads = read_json("leads.json")
demands = read_json("demands.json")
scripts_lib = read_json("scripts.json")
replies = read_replies()

# 采集器导出的作品清单（works*.csv）→ 合并进清单，状态默认"待派"
# 按链接去重：json 里已有的、或前面 CSV 已收录过的，不再重复加
works_csv = read_csv_glob("works*.csv")
_seen_urls = set(w.get("url", "") for w in works if w.get("url"))
_dup_rows = 0
for r in works_csv:
    _url = (r.get("链接") or "").strip()
    if _url and _url in _seen_urls:
        _dup_rows += 1
        continue
    if _url:
        _seen_urls.add(_url)
    works.append({
        "id": "csv-" + str(len(works)),
        "date": r.get("日期", ""),
        "platform": r.get("平台", ""),
        "title": r.get("标题", ""),
        "url": _url,
        "views": to_int(r.get("点赞")) * 20,   # 点赞估播放，仅排序用
        "comments": to_int(r.get("评论数")),
        "a_count": 0,
        "b_count": 0,
        "staff": "",
        "status": "待派",
        "_from": "csv"
    })

# 采集器导出的私信列表（inbox*.csv）→ 私信收件箱
inbox = read_csv_glob("inbox*.csv")

# ============ 算指标 ============
def n(x, d=0):
    try:
        return int(x)
    except Exception:
        return d

# 雷达回复记录：按 等级 统计
A_cnt = sum(1 for r in replies if r.get("等级") == "A")
B_cnt = sum(1 for r in replies if r.get("等级") == "B")
R_cnt = sum(1 for r in replies if r.get("等级") == "R")
replied_cnt = len(replies)
# 线索
lead_cnt = len(leads)
lead_wx = sum(1 for l in leads if "微信" in l.get("stage", "") or "留资" in l.get("stage", ""))
# 作品/派单
work_cnt = len(works)
pending = sum(1 for w in works if w.get("status") in ("待派", "未开始"))
doing = sum(1 for w in works if w.get("status") == "进行中")
done = sum(1 for w in works if w.get("status") == "已完成")
# 意向总量（来自作品清单的预估）
intent_all = sum(n(w.get("a_count")) + n(w.get("b_count")) for w in works)
# 转化率
reply_rate = (replied_cnt / intent_all) if intent_all else 0
lead_rate = (lead_cnt / replied_cnt) if replied_cnt else 0
wx_rate = (lead_wx / lead_cnt) if lead_cnt else 0

today = datetime.now().strftime("%Y-%m-%d")

# ============ 样式 ============
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--green:#0F5C45;--green2:#14785a;--gold:#9A7118;--bg:#f4f6f4;--card:#fff;
--line:#e3e8e4;--txt:#1d2b24;--muted:#7a8a80;--red:#c0392b;--amber:#c98a00}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--txt);font-size:14px;-webkit-font-smoothing:antialiased}
a{color:var(--green);text-decoration:none}
.wrap{display:flex;min-height:100vh}
/* 侧栏 */
.side{width:196px;background:var(--green);color:#fff;flex-shrink:0;padding:18px 0;position:sticky;top:0;height:100vh;display:flex;flex-direction:column}
.logo{padding:0 18px 16px;border-bottom:1px solid rgba(255,255,255,.15);margin-bottom:10px}
.logo b{font-size:15px;letter-spacing:.3px}
.logo small{display:block;font-size:10px;color:rgba(255,255,255,.55);letter-spacing:1.4px;margin-top:3px}
.nav a{display:flex;align-items:center;gap:9px;padding:10px 18px;color:rgba(255,255,255,.78);font-size:13px;border-left:3px solid transparent}
.nav a:hover{background:rgba(255,255,255,.07);color:#fff}
.nav a.on{background:rgba(255,255,255,.12);color:#fff;border-left-color:#d4af37;font-weight:600}
.nav .ic{width:16px;text-align:center;font-size:14px}
.side .foot{margin-top:auto;padding:12px 18px;font-size:11px;color:rgba(255,255,255,.72);line-height:1.85;
  border-top:1px solid rgba(255,255,255,.14)}
.side .foot b{color:#e8c96a;font-weight:700}
/* 主区 */
.main{flex:1;padding:22px 26px 40px;min-width:0}
.hd{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:18px}
.hd h1{font-size:20px;font-weight:800;color:var(--green)}
.hd p{font-size:12px;color:var(--muted);margin-top:4px}
.hd .date{font-size:11px;color:var(--muted)}
/* 卡片 */
.grid{display:grid;gap:12px;margin-bottom:18px}
.g6{grid-template-columns:repeat(6,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
.g3{grid-template-columns:repeat(3,1fr)}
.g2{grid-template-columns:repeat(2,1fr)}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 15px;position:relative}
.kpi .lb{font-size:11.5px;color:var(--muted);margin-bottom:6px}
.kpi .v{font-size:24px;font-weight:800;color:var(--green);line-height:1.1}
.kpi .v small{font-size:11px;font-weight:400;color:var(--muted);margin-left:3px}
.kpi .sub{font-size:10.5px;color:var(--muted);margin-top:5px}
.kpi.key{border-color:#c9b26a;background:linear-gradient(180deg,#fffdf5,#fff)}
.kpi.key .v{color:var(--gold)}
.kpi.alert{border-color:#e8b4ae;background:#fff8f7}
.kpi.alert::after{content:"";position:absolute;left:0;top:10px;bottom:10px;width:4px;background:var(--red);border-radius:0 3px 3px 0}
.kpi.alert .v{color:var(--red)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 18px;margin-bottom:16px}
.card h2{font-size:14px;font-weight:800;color:var(--green);margin-bottom:12px;display:flex;align-items:center;gap:7px}
.card h2 .tip{font-size:10px;font-weight:400;color:var(--muted)}
/* 表格 */
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{background:#f0f4f2;color:#4a5d54;font-weight:600;padding:9px 10px;text-align:left;font-size:11px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid #f0f2f1;vertical-align:top;line-height:1.6}
tr:hover td{background:#fafcfb}
td.num{text-align:right;font-variant-numeric:tabular-nums}
/* 标签 */
.tag{display:inline-block;padding:1px 7px;border-radius:3px;font-size:10.5px;font-weight:600;white-space:nowrap}
.tA{background:#fdecea;color:#b03a2e}
.tB{background:#fff6e0;color:#9a7118}
.tR{background:#eee;color:#777}
.tok{background:#e8f5e9;color:#2e7d32}
.twait{background:#f0f0f0;color:#777}
.tdo{background:#e3f2fd;color:#1565c0}
.tbad{background:#fdecea;color:#b03a2e}
.bar{height:7px;background:#eef1ef;border-radius:4px;overflow:hidden;min-width:70px;display:inline-block;vertical-align:middle}
.bar i{display:block;height:100%;background:var(--green);border-radius:4px}
.empty{color:var(--muted);font-size:12.5px;padding:22px;text-align:center;background:#fafbfa;border-radius:6px}
.note{font-size:11.5px;color:var(--muted);line-height:1.9;background:#fafbfa;border-left:3px solid #d4af37;padding:10px 14px;border-radius:0 6px 6px 0;margin-top:12px}
.btn{display:inline-block;padding:6px 13px;background:var(--green);color:#fff;border-radius:5px;font-size:12px;font-weight:600}
.flow{display:flex;gap:0;margin:6px 0 4px}
.flow .s{flex:1;min-width:0;border:1px solid var(--line);padding:9px 6px;text-align:center;position:relative;background:#fdfefd}
.flow .s:not(:last-child)::after{content:"›";position:absolute;right:-7px;top:50%;transform:translateY(-50%);
  color:#8aa79a;font-size:17px;font-weight:700;z-index:2;line-height:1}
.flow .s b{display:block;font-size:10.5px;color:var(--green);margin-bottom:2px;white-space:nowrap}
.flow .s span{font-size:9px;color:var(--muted);line-height:1.4;display:block;white-space:nowrap}
.flow .s em{display:block;font-size:14px;font-weight:800;color:var(--gold);font-style:normal;margin-top:3px}
@media(max-width:1200px){.g6{grid-template-columns:repeat(3,1fr)}.g4{grid-template-columns:repeat(2,1fr)}}
"""

NAV = [
    ("index.html", "◎", "总台"),
    ("radar.html", "📡", "今日清单"),
    ("tasks.html", "📋", "派单台"),
    ("leads.html", "💬", "私信承接"),
    ("funnel.html", "📊", "漏斗复盘"),
    ("demands.html", "💡", "需求池"),
    ("scripts.html", "🗣", "话术库"),
    ("pack.html", "🎁", "行业包"),
]


def page(filename, active, title, subtitle, body):
    nav = "".join(
        f'<a href="{h}" class="{"on" if h == active else ""}"><span class="ic">{ic}</span>{nm}</a>'
        for h, ic, nm in NAV
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · 获客工作台</title><style>{CSS}</style></head>
<body><div class="wrap">
<aside class="side">
  <div class="logo"><b>获客工作台</b><small>INTENT RADAR OPS</small></div>
  <nav class="nav">{nav}</nav>
  <div class="foot"><b>● 数据源正常</b><br>data/ 目录 · CSV 丢进去自动汇总<br>最后构建 {today}</div>
</aside>
<main class="main">
  <div class="hd"><div><h1>{title}</h1><p>{subtitle}</p></div><div class="date">{today}</div></div>
  {body}
</main></div></body></html>"""


def e(s):
    return html.escape(str(s if s is not None else ""))


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


# ============ 页面 1：总台 ============
def build_index():
    warn_html = ""
    if work_cnt - done > 0:
        warn_html = f"""<div class="note">⚠️ 还有 <b>{work_cnt - done}</b> 条作品没扫完（待派 {pending} / 进行中 {doing}）。
        今天是 {today}，如果今天不处理，这些评论里的意向客户就滑过去了。</div>"""
    if lead_cnt and not any("微信" in l.get("stage", "") for l in leads):
        warn_html += """<div class="note">⚠️ 有线索但还没有一个留到微信——私信承接话术需要加引导（见「话术库」承接场景）。</div>"""

    body = f"""
<div class="grid g6">
  <div class="kpi"><div class="lb">今日清单</div><div class="v">{work_cnt}<small>条</small></div><div class="sub">待派 {pending} · 进行中 {doing}</div></div>
  <div class="kpi"><div class="lb">识别意向</div><div class="v">{intent_all}<small>条</small></div><div class="sub">A+B 合计</div></div>
  <div class="kpi"><div class="lb">已回复</div><div class="v">{replied_cnt}<small>条</small></div><div class="sub">回复率 {pct(reply_rate, 0)}</div></div>
  <div class="kpi key"><div class="lb">进私信</div><div class="v">{lead_cnt}<small>人</small></div><div class="sub">回复→私信 {pct(lead_rate)}</div></div>
  <div class="kpi {"alert" if lead_cnt and wx_rate < 0.3 else ""}"><div class="lb">留资/加微</div><div class="v">{lead_wx}<small>人</small></div><div class="sub">私信→留资 {pct(wx_rate, 0)}</div></div>
  <div class="kpi"><div class="lb">需求池</div><div class="v">{len(demands)}<small>个</small></div><div class="sub">该做内容的问题</div></div>
</div>

<div class="card"><h2>链路现状 <span class="tip">每一段各用什么东西在跑</span></h2>
<div class="flow">
  <div class="s"><b>① 数据端</b><span>人工/周清单</span><em>{work_cnt} 条</em></div>
  <div class="s"><b>② 派单</b><span>派给谁·状态</span><em>{pending} 待派</em></div>
  <div class="s"><b>③ 雷达扫评</b><span>识别意向</span><em>{intent_all} 条</em></div>
  <div class="s"><b>④ 人工回复</b><span>只回不回发</span><em>{replied_cnt} 条</em></div>
  <div class="s"><b>⑤ 私信承接</b><span>线索池跟进</span><em>{lead_cnt} 人</em></div>
  <div class="s"><b>⑥ 复盘</b><span>三率看板</span><em>{pct(lead_rate)}</em></div>
</div>
{warn_html}
</div>

<div class="grid g2">
<div class="card"><h2>最近的意向回复 <span class="tip">雷达记录</span></h2>
{_reply_table(replies[:8]) if replies else '<div class="empty">还没有回复记录。员工用雷达回复后点「已回复」，导出 CSV 丢进 data/ 就会出现在这里。</div>'}
</div>
<div class="card"><h2>私信线索（待跟进）</h2>
{_lead_table(leads[:8]) if leads else '<div class="empty">还没有线索进来。有人私信后，在 leads.json 里记一条。</div>'}
</div>
</div>
"""
    return page("index.html", "index.html", "总台", "每天开工第一眼：今天有多少活、昨天的转化怎么样", body)


def _reply_table(rows):
    if not rows:
        return '<div class="empty">无记录</div>'
    trs = ""
    for r in rows:
        g = r.get("等级", "")
        cls = {"A": "tA", "B": "tB", "R": "tR"}.get(g, "tR")
        trs += f"""<tr><td><span class="tag {cls}">{e(g)}</span></td>
<td>{e(r.get('原评论',''))[:34]}</td>
<td>{e(r.get('员工',''))}</td>
<td>{e(r.get('平台',''))}</td></tr>"""
    return f"<table><tr><th>等级</th><th>原评论</th><th>员工</th><th>平台</th></tr>{trs}</table>"


def _lead_table(rows):
    if not rows:
        return '<div class="empty">无线索</div>'
    trs = ""
    for l in rows:
        trs += f"""<tr><td>{e(l.get('name',''))}</td>
<td>{e(l.get('platform',''))}</td>
<td><span class="tag twait">{e(l.get('stage',''))}</span></td>
<td>{e(l.get('owner',''))}</td></tr>"""
    return f"<table><tr><th>客户</th><th>平台</th><th>阶段</th><th>跟进人</th></tr>{trs}</table>"


# ============ 页面 2：今日清单（数据端）============
def build_radar():
    if not works:
        body = '<div class="empty">今天还没有作品清单。<br><br>做法：刷到/搜到值得扫的作品 → 在 data/works.json 里记一条（链接、标题、评论数）。</div>'
    else:
        trs = ""
        for w in works:
            st = w.get("status", "待派")
            stc = {"待派": "twait", "进行中": "tdo", "已完成": "tok"}.get(st, "twait")
            a, b = n(w.get("a_count")), n(w.get("b_count"))
            total = a + b
            trs += f"""<tr>
<td class="num">{n(w.get('views')):,}</td>
<td class="num">{n(w.get('comments')):,}</td>
<td><a href="{e(w.get('url','#'))}" target="_blank">{e(w.get('title',''))[:30]}</a></td>
<td>{e(w.get('platform',''))}</td>
<td class="num"><span class="tag tA">{a}</span> <span class="tag tB">{b}</span></td>
<td>{e(w.get('staff','')) or '—'}</td>
<td><span class="tag {stc}">{e(st)}</span></td></tr>"""
        body = f"""<div class="card"><h2>待扫作品清单 <span class="tip">按播放量排序 · 点标题去扫</span></h2>
<table>
<tr><th>播放</th><th>评论数</th><th>作品</th><th>平台</th><th>A/B 意向</th><th>派给</th><th>状态</th></tr>
{trs}
</table>
<div class="note">扫法：点开作品 → 装了雷达的浏览器自动高亮意向评论 → 逐条回复 → 回到「派单台」更新状态。<br>
清单数据来源：现在靠人工记（刷到就记一条），后面可接蝉妈妈/新榜 API 自动出。</div>
</div>"""
    return page("radar.html", "radar.html", "今日清单", "数据端：今天该扫哪些作品", body)


# ============ 页面 3：派单台 ============
def build_tasks():
    rows = ""
    for s in staff:
        name = s.get("name", "")
        mine = [w for w in works if w.get("staff") == name]
        my_done = sum(1 for w in mine if w.get("status") == "已完成")
        my_replies = sum(1 for r in replies if r.get("员工") == name)
        limit = n(s.get("daily_limit"), 20)
        used_pct = min(100, int(my_replies / limit * 100)) if limit else 0
        bar_cls = "background:#c0392b" if used_pct >= 90 else "background:var(--green)"
        rows += f"""<tr>
<td><b>{e(name)}</b></td>
<td>{e(s.get('platform',''))}</td>
<td>{e(s.get('account',''))}</td>
<td class="num">{len(mine)}</td>
<td class="num">{my_done}</td>
<td class="num">{my_replies}</td>
<td><span class="bar"><i style="width:{used_pct}%;{bar_cls}"></i></span> <span style="font-size:11px">{my_replies}/{limit}</span></td>
</tr>"""
    trs2 = ""
    for w in works:
        st = w.get("status", "待派")
        stc = {"待派": "twait", "进行中": "tdo", "已完成": "tok"}.get(st, "twait")
        trs2 += f"""<tr><td>{e(w.get('title',''))[:28]}</td><td>{e(w.get('platform',''))}</td>
<td>{e(w.get('staff','')) or '<span style="color:#bbb">未派</span>'}</td>
<td><span class="tag {stc}">{e(st)}</span></td>
<td class="num">{n(w.get('a_count')) + n(w.get('b_count'))}</td></tr>"""
    body = f"""<div class="card"><h2>员工与账号 <span class="tip">限额防封号，别让一个人猛发</span></h2>
{'<table><tr><th>员工</th><th>平台</th><th>账号</th><th>派到作品</th><th>已完成</th><th>今日已回</th><th>额度</th></tr>' + rows + '</table>' if staff else '<div class="empty">还没有员工。在 data/staff.json 里加。</div>'}
<div class="note">合规红线：小红书普通号 5 人/天、专业号 20 人/天；抖音 24h 内对同一人只能发 1 条。<br>
超了就会被限流甚至封号——这张表就是为了让你看得见「谁快到线了」。</div>
</div>
<div class="card"><h2>派单明细</h2>
{'<table><tr><th>作品</th><th>平台</th><th>负责人</th><th>状态</th><th>待扫意向</th></tr>' + trs2 + '</table>' if works else '<div class="empty">暂无作品</div>'}
</div>"""
    return page("tasks.html", "tasks.html", "派单台", "中端：谁扫哪条、谁快超限额", body)


# ============ 页面 4：私信承接（后端）============
def build_leads():
    stages = ["待跟进", "已私信", "已加微信", "已报价", "已成单", "已流失"]
    cnt = {s: sum(1 for l in leads if l.get("stage") == s) for s in stages}
    kpi = "".join(
        f'<div class="kpi{" alert" if s in ("已流失", "待跟进") and cnt[s] else ""}"><div class="lb">{s}</div><div class="v">{cnt[s]}<small>人</small></div></div>'
        for s in stages
    )
    trs = ""
    for l in leads:
        trs += f"""<tr><td>{e(l.get('date',''))}</td>
<td><b>{e(l.get('name',''))}</b></td>
<td>{e(l.get('platform',''))}</td>
<td>{e(l.get('comment',''))[:30]}</td>
<td><span class="tag twait">{e(l.get('stage',''))}</span></td>
<td>{e(l.get('next',''))}</td>
<td>{e(l.get('owner',''))}</td></tr>"""
    body = f"""<div class="grid g6">{kpi}</div>
<div class="card"><h2>线索池 <span class="tip">私信进来的人，一个都不能丢</span></h2>
{'<table><tr><th>日期</th><th>客户</th><th>平台</th><th>来源评论</th><th>阶段</th><th>下一步</th><th>跟进人</th></tr>' + trs + '</table>' if leads else '<div class="empty">还没有线索。<br><br>有人私信你 → 在 data/leads.json 记一条（谁、哪个平台、从哪条评论来的、下一步做什么）。</div>'}
<div class="note">这一栏是整个链路最值钱的地方——<b>意向客户从评论走到私信，是最容易掉人的一步</b>。<br>
常见掉法：回了评论但没引导私信、私信里只发广告不回答、问了价格就再没下文。</div>
</div>
{_inbox_card()}
"""
    return page("leads.html", "leads.html", "私信承接", "后端：私信进来的客户，跟进到成交", body)


def _inbox_card():
    """采集器抓来的多平台私信收件箱"""
    if not inbox:
        return """<div class="card"><h2>私信收件箱 <span class="tip">采集器自动抓的（还没数据）</span></h2>
<div class="empty">还没有采集数据。<br><br>
做法：装「获客采集器」脚本 → 打开抖音创作者中心/小红书专业号/视频号后台的私信页面 → 点「采集当前页」→ 导出 CSV 丢进 <code>data/</code> → 重新打开工作台，各平台私信就在这汇总。</div></div>"""
    # 按平台分组
    by_plat = {}
    for r in inbox:
        p = r.get("平台", "未知")
        by_plat.setdefault(p, []).append(r)
    summary = " ".join(
        f'<span class="tag tok">{e(p)} {len(v)}</span>' for p, v in sorted(by_plat.items(), key=lambda x: -len(x[1]))
    )
    trs = ""
    for r in inbox[:20]:
        trs += f"""<tr><td>{e(r.get('平台',''))}</td>
<td><b>{e(r.get('客户昵称',''))}</b></td>
<td>{e(r.get('最后消息',''))[:40]}</td>
<td>{e(r.get('时间',''))}</td>
<td style="color:var(--muted);font-size:11px">{e(r.get('采集时间',''))}</td></tr>"""
    return f"""<div class="card"><h2>私信收件箱 <span class="tip">采集器抓的各平台私信，汇总在一屏</span></h2>
<div style="margin-bottom:10px">{summary}</div>
<table><tr><th>平台</th><th>客户</th><th>最后一条消息</th><th>时间</th><th>采集时间</th></tr>{trs}</table>
<div class="note">这里只<b>汇总展示</b>，实际回复还是去各平台后台回（合规、不会封号）。<br>
看到有意向的，在上面「线索池」里记一条，标好阶段和下一步。</div>
</div>"""


# ============ 页面 5：漏斗复盘 ============
def build_funnel():
    rows = [
        ("① 识别意向", intent_all, "—", "AI 扫出来的 A+B"),
        ("② 已回复", replied_cnt, pct(reply_rate) if intent_all else "—", "回复率，目标 >80%"),
        ("③ 进私信", lead_cnt, pct(lead_rate) if replied_cnt else "—", "★核心：回复→私信，目标 >2%"),
        ("④ 留资/加微", lead_wx, pct(wx_rate) if lead_cnt else "—", "私信→留资，目标 >30%"),
    ]
    trs = ""
    for name, v, rate, note in rows:
        trs += f"""<tr><td><b>{name}</b></td><td class="num" style="font-size:16px;font-weight:800;color:var(--green)">{v}</td>
<td class="num" style="font-weight:700;color:var(--gold)">{rate}</td><td style="color:var(--muted);font-size:11.5px">{note}</td></tr>"""
    # 按平台
    plat = {}
    for r in replies:
        p = r.get("平台", "未知")
        plat[p] = plat.get(p, 0) + 1
    prs = "".join(
        f'<tr><td>{e(k)}</td><td class="num">{v}</td><td><span class="bar"><i style="width:{min(100,int(v/max(plat.values())*100))}%"></i></span></td></tr>'
        for k, v in sorted(plat.items(), key=lambda x: -x[1])
    ) if plat else ""
    body = f"""<div class="card"><h2>核心漏斗 <span class="tip">哪一段漏了，就修哪一段</span></h2>
<table><tr><th>环节</th><th>数量</th><th>转化率</th><th>说明</th></tr>{trs}</table>
<div class="note">
<b>怎么读这张表：</b><br>
· 已回复 远小于 识别意向 → 人手不够或派单漏了<br>
· 回复→私信 &lt; 2% → <b>话术不行</b>（客户没兴趣聊），先改话术别加量<br>
· 私信→留资 &lt; 30% → <b>承接不行</b>（私信没给到价值），改承接话术<br>
· 三个率都正常但成交少 → 那是产品/价格问题，不是获客问题
</div>
</div>
<div class="grid g2">
<div class="card"><h2>各平台回复量</h2>
{('<table><tr><th>平台</th><th>回复数</th><th></th></tr>' + prs + '</table>') if prs else '<div class="empty">暂无数据</div>'}
</div>
<div class="card"><h2>话术效果 TOP</h2>
{_script_rank()}
</div>
</div>"""
    return page("funnel.html", "funnel.html", "漏斗复盘", "数据统计：三个率告诉你该修哪一段", body)


def _script_rank():
    if not scripts_lib:
        return '<div class="empty">暂无话术数据</div>'
    top = sorted(scripts_lib, key=lambda s: -n(s.get("replied")))[:6]
    trs = ""
    for s in top:
        sent, rep = n(s.get("sent")), n(s.get("replied"))
        rate = rep / sent if sent else 0
        trs += f"""<tr><td>{e(s.get('scene',''))[:12]}</td><td class="num">{sent}</td>
<td class="num">{rep}</td><td class="num" style="color:var(--gold);font-weight:700">{pct(rate, 0)}</td></tr>"""
    return f"<table><tr><th>场景</th><th>发了</th><th>回了</th><th>回复率</th></tr>{trs}</table>"


# ============ 页面 6：需求池 ============
def build_demands():
    ds = sorted(demands, key=lambda d: -n(d.get("count")))
    trs = ""
    for d in ds:
        c = n(d.get("count"))
        badge = '<span class="tag tA">该做内容</span>' if c >= 3 else '<span class="tag twait">再观察</span>'
        trs += f"""<tr><td>{e(d.get('question',''))}</td>
<td class="num" style="font-weight:700">{c}</td>
<td>{e(d.get('tag',''))}</td>
<td>{e(d.get('topic',''))[:34]}</td>
<td>{badge}</td></tr>"""
    body = f"""<div class="card"><h2>客户在问什么 <span class="tip">白档：需求反哺内容，这是没有上限的杠杆</span></h2>
{'<table><tr><th>客户原话问题</th><th>次数</th><th>需求标签</th><th>对应内容选题</th><th>状态</th></tr>' + trs + '</table>' if ds else '<div class="empty">还没有记录。扫评时看到同一个问题被问 3 次以上，就记一条。</div>'}
<div class="note"><b>为什么这张表比清单重要：</b>回复评论有额度上限（5-20 人/天），但做内容是<b>没有上限</b>的。<br>
一个问题被问 3 次 → 做成一条内容 → 下一条同类作品里，这种人会主动来找你，不用你去回。</div>
</div>"""
    return page("demands.html", "demands.html", "需求池", "白档：客户的问题 → 内容选题", body)


# ============ 页面 7：话术库 ============
def build_scripts():
    trs = ""
    for s in scripts_lib:
        sent, rep = n(s.get("sent")), n(s.get("replied"))
        rate = rep / sent if sent else 0
        g = s.get("grade", "A")
        cls = {"A": "tA", "B": "tB"}.get(g, "tR")
        trs += f"""<tr><td><span class="tag {cls}">{e(g)}</span></td>
<td><b>{e(s.get('scene',''))}</b></td>
<td style="line-height:1.7">{e(s.get('text',''))}</td>
<td class="num">{sent}</td><td class="num">{rep}</td>
<td class="num" style="font-weight:700;color:var(--gold)">{pct(rate, 0)}</td></tr>"""
    body = f"""<div class="card"><h2>话术库 <span class="tip">按场景分 · 看哪个回复率高</span></h2>
{'<table><tr><th>等级</th><th>场景</th><th>话术</th><th>发</th><th>回</th><th>回复率</th></tr>' + trs + '</table>' if scripts_lib else '<div class="empty">暂无话术</div>'}
<div class="note">话术是底稿，<b>发之前一定要改两句</b>——原封不动复制粘贴，一眼就是机器人。</div>
</div>"""
    return page("scripts.html", "scripts.html", "话术库", "按场景管理话术，用数据淘汰无效话术", body)


# ============ 页面 8：行业包生成器 ============
PACK_BODY = r"""
<div class="card"><h2>① 填行业信息 <span class="tip">关键词是核心，越具体越准</span></h2>
<div style="display:grid;grid-template-columns:220px 1fr;gap:12px;align-items:start">
  <div>
    <div style="font-size:11.5px;color:var(--muted);margin-bottom:5px">行业/产品名称</div>
    <input id="pk-ind" placeholder="电瓶车电池" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:13px;box-sizing:border-box">
    <div style="font-size:11.5px;color:var(--muted);margin:12px 0 5px">客户公司名（可选）</div>
    <input id="pk-co" placeholder="某某电池经营部" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:13px;box-sizing:border-box">
    <div style="font-size:11.5px;color:var(--muted);margin:12px 0 5px">平台</div>
    <label style="display:block;font-size:12px;margin-bottom:4px"><input type="checkbox" class="pk-plat" value="douyin" checked> 抖音</label>
    <label style="display:block;font-size:12px;margin-bottom:4px"><input type="checkbox" class="pk-plat" value="xhs" checked> 小红书</label>
    <label style="display:block;font-size:12px;margin-bottom:4px"><input type="checkbox" class="pk-plat" value="sph"> 视频号</label>
    <label style="display:block;font-size:12px;margin-bottom:4px"><input type="checkbox" class="pk-plat" value="ks"> 快手</label>
  </div>
  <div>
    <div style="font-size:11.5px;color:var(--muted);margin-bottom:5px">行业关键词（一行一个，或用逗号分隔）——填客户真会说的词</div>
    <textarea id="pk-kw" rows="6" placeholder="电动车电池&#10;电瓶车电池&#10;锂电池&#10;铅酸电池&#10;换电池&#10;电池以旧换新" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:13px;box-sizing:border-box;line-height:1.7"></textarea>
    <div style="font-size:10.5px;color:var(--muted);margin-top:6px;line-height:1.7">
      💡 怎么填：想客户在评论区会怎么问。比如「换电池」「电池跑不远」「以旧换新」——<b>不要填"电瓶车"这种大类</b>，太宽会误报。
    </div>
  </div>
</div>
<button id="pk-gen" style="width:100%;margin-top:14px;padding:11px;border:none;border-radius:7px;background:var(--green);color:#fff;font-size:14px;font-weight:700;cursor:pointer">生成行业包</button>
</div>

<div id="pk-result" style="display:none">
<div class="card"><h2>② 检查并修改 <span class="tip">自动生成的是草稿，删掉不像人话的</span></h2>
  <div style="font-size:11.5px;color:var(--muted);margin-bottom:5px">A 级词（强意向 · 当天回）<span id="pk-cnt-a" style="color:var(--gold);font-weight:700"></span></div>
  <textarea id="pk-a" rows="4" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:11.5px;box-sizing:border-box;line-height:1.7;font-family:Consolas,monospace"></textarea>
  <div style="font-size:11.5px;color:var(--muted);margin:10px 0 5px">B 级词（有兴趣 · 48h 内回）<span id="pk-cnt-b" style="color:var(--gold);font-weight:700"></span></div>
  <textarea id="pk-b" rows="3" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:11.5px;box-sizing:border-box;line-height:1.7;font-family:Consolas,monospace"></textarea>
  <div style="font-size:11.5px;color:var(--muted);margin:10px 0 5px">R 级词（高风险 · 不接）</div>
  <textarea id="pk-r" rows="2" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:11.5px;box-sizing:border-box;line-height:1.7;font-family:Consolas,monospace"></textarea>
  <div style="font-size:11.5px;color:var(--muted);margin:10px 0 5px">话术库（键 = 命中词，值 = 话术）</div>
  <textarea id="pk-s" rows="10" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:11.5px;box-sizing:border-box;line-height:1.7;font-family:Consolas,monospace"></textarea>
</div>

<div class="card"><h2>③ 下载两个包，分别发给两个人</h2>
<div class="grid g2" style="margin-bottom:0">
  <div style="border:1px solid var(--line);border-radius:8px;padding:14px">
    <div style="font-size:13px;font-weight:800;color:var(--green);margin-bottom:5px">📡 雷达包 <span style="font-size:10.5px;color:var(--muted);font-weight:400">→ 给客服装</span></div>
    <div style="font-size:11px;color:var(--muted);line-height:1.7;margin-bottom:10px">
      扫评论区、高亮意向、生成话术、记录已回、导出 CSV。<br>
      装在**客服自己**的电脑上（用客服自己的账号）。
    </div>
    <button id="pk-dl-radar" style="width:100%;padding:9px;border:none;border-radius:6px;background:var(--green);color:#fff;font-size:13px;font-weight:700;cursor:pointer">下载雷达包 .user.js</button>
  </div>
  <div style="border:1px solid var(--line);border-radius:8px;padding:14px">
    <div style="font-size:13px;font-weight:800;color:var(--gold);margin-bottom:5px">📋 采集包 <span style="font-size:10.5px;color:var(--muted);font-weight:400">→ 给运营经理装</span></div>
    <div style="font-size:11px;color:var(--muted);line-height:1.7;margin-bottom:10px">
      抓作品清单、抓各平台私信、导出 CSV 喂工作台。<br>
      装在**运营经理**电脑上，负责每天出清单和派单。
    </div>
    <button id="pk-dl-coll" style="width:100%;padding:9px;border:none;border-radius:6px;background:var(--gold);color:#fff;font-size:13px;font-weight:700;cursor:pointer">下载采集包 .user.js</button>
  </div>
</div>
<div class="note">
<b>安装方式（和装普通油猴脚本一样）：</b>两个人都要装 Tampermonkey 扩展 → 打开下载的 .user.js → 浏览器会弹出安装页 → 点「安装」。<br>
<b>装完验收：</b>客服面板标题显示「🎯 <span id="pk-indshow1">行业</span> 意向雷达」，运营面板显示「📡 <span id="pk-indshow2">行业</span> 作品采集」。
</div>
</div>

<div class="card"><h2>④ 同步工作台数据 <span class="tip">不换这些，工作台里还是上一个行业的话术和需求</span></h2>
<div class="grid g3" style="margin-bottom:10px">
  <button id="pk-dl-scripts" style="padding:10px;border:none;border-radius:7px;background:var(--green);color:#fff;font-size:12.5px;font-weight:700;cursor:pointer">话术库<br><span style="font-size:10px;font-weight:400;opacity:.8">scripts.json</span></button>
  <button id="pk-dl-demands" style="padding:10px;border:none;border-radius:7px;background:var(--gold);color:#fff;font-size:12.5px;font-weight:700;cursor:pointer">需求池<br><span style="font-size:10px;font-weight:400;opacity:.8">demands.json</span></button>
  <button id="pk-dl-staff" style="padding:10px;border:none;border-radius:7px;background:#5a6b62;color:#fff;font-size:12.5px;font-weight:700;cursor:pointer">员工表<br><span style="font-size:10px;font-weight:400;opacity:.8">staff.json</span></button>
</div>
<label style="display:block;margin:14px 0 9px;font-size:12.5px;cursor:pointer">
  <input type="checkbox" id="pk-reset" checked> 同时清空作品清单 / 线索池，并删除上个行业的 CSV
</label>
<button id="pk-apply" style="width:100%;padding:13px;border:none;border-radius:7px;background:linear-gradient(90deg,#0F5C45,#14785a);color:#fff;font-size:14px;font-weight:800;cursor:pointer">⚡ 一键应用到工作台</button>
<div id="pk-apply-result" style="margin-top:10px;font-size:12px;line-height:1.85"></div>
<div class="note">
<b>换行业 = 换 data/ 这 4 样东西（代码一行不改）：</b><br>
① <code>scripts.json</code> ← 点上面的按钮下载，覆盖工作台的 <code>data\scripts.json</code><br>
② <code>demands.json</code> ← 同上（给的是通用待验证问题，扫真实评论后填次数）<br>
③ <code>staff.json</code> ← 同上，把员工名和账号填进去<br>
④ <code>works.json</code> / <code>leads.json</code> ← <b>清空</b>（写成 <code>[]</code>），或者直接删掉重新由采集器填<br>
⑤ 把 <code>data\</code> 里旧的 <code>works_*.csv</code> / <code>inbox_*.csv</code> / <code>replies_*.csv</code> 删掉<br><br>
改完双击「启动工作台.vbs」重开 → 「话术库」和「需求池」就变成新行业的内容了。
</div>
</div>
</div>

<script>
const RADAR_TEMPLATE = __RADAR_SRC__;
const COLL_TEMPLATE = __COLL_SRC__;

const A_PURE = ["多少钱","什么价","什么价格","价格","报价","怎么卖","怎么买","哪里买","在哪买","能买吗","哪个好","怎么选","选哪个","求推荐","推荐一下","能上门吗","包安装吗","上门安装","保修多久","能用多久","有售后吗","以旧换新","能置换吗","包邮吗","能发货吗","怎么联系","有货吗","能修吗","想买","要买","想换","要换","准备换","求购"];
const B_PURE = ["怎么保养","能用几年","注意事项","哪个耐用","真假","怎么辨别","有什么区别","怎么样","好用吗","值得买吗","有没有推荐","用多久换"];
const R_PURE = ["加微信","加个微信","私聊","私下交易","内部价","代理","批发","货源","翻新","拆机","高仿","假货","一手货源"];
const A_COMBO = ["坏了","不行了","有问题","不耐用","能修吗","怎么修","多少钱","什么价"];
const B_COMBO = ["怎么保养","能用几年","哪个好"];

const SCRIPT_TPL = {
  "多少钱": "{IND}的价格要看具体型号和规格，你说下用途和预算，我给你报个准价，含不含安装都写清楚～",
  "怎么买": "告诉我你要的型号和数量，我帮你算到位：单价、运费、安装费分开写，不玩套路～",
  "哪个好": "先说清楚你的使用场景，我按耐用性和性价比给你两个方案对比，你自己挑～",
  "求推荐": "你的使用场景是什么？预算大概多少？我按你的情况推一款，不合适我不乱推～",
  "保修": "保修条款我给你写清楚：保多久、保哪些、怎么报修，有不清楚的随时问～",
  "安装": "你这边地址在哪个区？上门安装能安排，我先把费用说清楚再约时间～",
  "真假": "判断真假主要看三点：标识、重量、能不能查。我发你一份对照，你自己核对～",
  "保养": "日常保养就几条，我整理过一份清单，发给你照着做，能多用一两年～",
  "兜底": "你好，我们是做{IND}的。你说下具体需求（用途/型号/数量），我给你一个准确的答复～"
};

function parseKW(s) {
  return s.split(/[\n,，、;；]+/).map(x => x.trim()).filter(x => x.length >= 2);
}
function uniq(arr) {
  const seen = {}, out = [];
  arr.forEach(x => { if (!seen[x]) { seen[x] = 1; out.push(x); } });
  return out;
}
function genWords(kws) {
  // 纯意向词（不拼产品名）—— 真实评论常常是「产品……意向词」中间夹字，拼接词会漏
  const A = A_PURE.slice(), B = B_PURE.slice();
  kws.forEach(k => {
    A_COMBO.forEach(s => A.push(k + s));   // 这些拼起来像人话：「电池坏了」「电池多少钱」
    B_COMBO.forEach(s => B.push(k + s));
  });
  return { A: uniq(A), B: uniq(B), R: R_PURE.slice(), PROD: kws };
}
function genScripts(industry) {
  const out = {};
  Object.keys(SCRIPT_TPL).forEach(k => { out[k] = SCRIPT_TPL[k].replace(/\{IND\}/g, industry); });
  return out;
}
function jsArr(arr) {
  return "[" + arr.map(x => JSON.stringify(x)).join(",") + "]";
}

let PK = null;

document.getElementById("pk-gen").onclick = function () {
  const ind = document.getElementById("pk-ind").value.trim();
  const kws = parseKW(document.getElementById("pk-kw").value);
  if (!ind) { alert("先填行业/产品名称"); return; }
  if (!kws.length) { alert("至少填一个关键词（一行一个）"); return; }
  const w = genWords(kws);
  const s = genScripts(ind);
  PK = { ind: ind, co: document.getElementById("pk-co").value.trim(), kws: kws,
         plats: [...document.querySelectorAll(".pk-plat:checked")].map(e => e.value) };
  document.getElementById("pk-a").value = w.A.join(",");
  document.getElementById("pk-b").value = w.B.join(",");
  document.getElementById("pk-r").value = w.R.join(",");
  document.getElementById("pk-s").value = Object.keys(s).map(k => k + "：" + s[k]).join("\n");
  document.getElementById("pk-cnt-a").textContent = " " + w.A.length + " 个";
  document.getElementById("pk-cnt-b").textContent = " " + w.B.length + " 个";
  document.getElementById("pk-indshow1").textContent = ind;
  document.getElementById("pk-indshow2").textContent = ind;
  document.getElementById("pk-result").style.display = "block";
  document.getElementById("pk-result").scrollIntoView({ behavior: "smooth", block: "start" });
};

function readEdited() {
  const arr = id => document.getElementById(id).value.split(",").map(x => x.trim()).filter(Boolean);
  const sc = {};
  document.getElementById("pk-s").value.split("\n").forEach(line => {
    const i = line.indexOf("：");
    if (i > 0) sc[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  });
  return { A: arr("pk-a"), B: arr("pk-b"), R: arr("pk-r"), scripts: sc };
}

function download(name, text) {
  const blob = new Blob([text], { type: "text/javascript;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
}

document.getElementById("pk-dl-radar").onclick = function () {
  if (!PK) { alert("先点「生成行业包」"); return; }
  const e = readEdited();
  const block =
    '  // ⛔ 本段由「获客工作台 · 行业包生成器」生成，改行业只改这一段\n' +
    '  // 行业：' + PK.ind + (PK.co ? '（' + PK.co + '）' : '') + '\n' +
    '  const INDUSTRY = ' + JSON.stringify(PK.ind) + ';\n' +
    '  const PROD_WORDS = ' + jsArr(PK.kws) + ';   // 产品词闸门：提到这些才算意向\n' +
    '  const STAFF_DEFAULT = "员工";\n' +
    '  const A_WORDS = ' + jsArr(e.A) + ';\n' +
    '  const B_WORDS = ' + jsArr(e.B) + ';\n' +
    '  const RED_WORDS = ' + jsArr(e.R) + ';\n' +
    '  const SCRIPTS = ' + JSON.stringify(e.scripts, null, 2).replace(/\n/g, "\n  ") + ';\n';
  const START = "// ==== INDUSTRY-PACK-START ====";
  const END = "// ==== INDUSTRY-PACK-END ====";
  const si = RADAR_TEMPLATE.indexOf(START);
  const ei = RADAR_TEMPLATE.indexOf(END);
  if (si < 0 || ei < 0) { alert("母本缺少锚点标记，联系罗小黑"); return; }
  const headEnd = RADAR_TEMPLATE.indexOf("\n", si) + 1;
  let out = RADAR_TEMPLATE.slice(0, headEnd) + block + "  " + RADAR_TEMPLATE.slice(ei);
  // 标题 + 描述带上行业名（只改展示，不改逻辑）
  out = out.replace(/🎯 意向雷达/g, "🎯 " + PK.ind + " 意向雷达");
  out = out.replace(/@name\s+.*/, "@name         " + PK.ind + " 意向雷达（客服装）");
  out = out.replace(/@description\s+.*/, "@description  [" + PK.ind + "] 评论区意向识别 + 话术草稿。只读辅助，不代发消息。");
  download("雷达包_" + PK.ind + "_客服装.user.js", out);
};

document.getElementById("pk-dl-coll").onclick = function () {
  if (!PK) { alert("先点「生成行业包」"); return; }
  if (!PK.plats.length) { alert("至少选一个平台"); return; }
  const MAP = {
    douyin: ["https://www.douyin.com/*", "https://douyin.com/*", "https://creator.douyin.com/*", "https://e.douyin.com/*"],
    xhs: ["https://www.xiaohongshu.com/*", "https://xiaohongshu.com/*", "https://pro.xiaohongshu.com/*", "https://creator.xiaohongshu.com/*"],
    sph: ["https://channels.weixin.qq.com/*"],
    ks: ["https://www.kuaishou.com/*", "https://kuaishou.com/*"]
  };
  let lines = [];
  PK.plats.forEach(p => { lines = lines.concat(MAP[p] || []); });
  const matchBlock = lines.map(l => "// @match        " + l).join("\n");
  let out = COLL_TEMPLATE.replace(/(\/\/ @match[^\n]*\n)+/, matchBlock + "\n");
  out = out.replace(/📡 作品清单采集/g, "📡 " + PK.ind + " 作品采集");
  out = out.replace(/💬 私信采集/g, "💬 " + PK.ind + " 私信采集");
  out = out.replace(/@name\s+.*/, "@name         " + PK.ind + " 获客采集器（运营装）");
  out = out.replace(/@description\s+.*/, "@description  [" + PK.ind + "] 抓作品清单 + 抓各平台私信。只读，不发送任何消息。");
  download("采集包_" + PK.ind + "_运营装.user.js", out);
};

// ===== 工作台数据文件（换行业时覆盖 data/ 用）=====
function buildScriptsJSON() {
  const e = readEdited();
  return Object.keys(e.scripts).map(function (k) {
    return { grade: e.A.indexOf(k) >= 0 ? "A" : "B", scene: k, text: e.scripts[k], sent: 0, replied: 0 };
  });
}
function buildDemandsJSON() {
  const k = PK.kws[0] || PK.ind;
  return [
    { question: k + "多少钱 / 什么价", count: 0, tag: "价格", topic: "把价格因素讲清楚（配置差异 + 价格区间）", published: false },
    { question: "怎么选 / 哪个好", count: 0, tag: "选择困难", topic: "按使用场景给一套选择框架", published: false },
    { question: "能用多久 / 质量怎么样", count: 0, tag: "质量信任", topic: "真实寿命 + 怎么判断好坏", published: false },
    { question: "售后怎么保 / 坏了找谁", count: 0, tag: "售后信任", topic: "保修条款原样公开（保多久、保什么）", published: false },
    { question: "能上门吗 / 包安装吗", count: 0, tag: "服务范围", topic: "服务范围、费用、预约方式", published: false },
    { question: "和别家比差在哪", count: 0, tag: "竞争对比", topic: "公开对比维度，不贬低同行", published: false }
  ];
}
function buildStaffJSON() {
  return [
    { name: "", platform: "抖音", account: "", daily_limit: 5, note: "普通号约5人/天；专业号20人/天" },
    { name: "", platform: "小红书", account: "", daily_limit: 5, note: "普通号约5人/天；专业号20人/天" }
  ];
}

document.getElementById("pk-dl-scripts").onclick = function () {
  if (!PK) { alert("先点「生成行业包」"); return; }
  download("scripts.json", JSON.stringify(buildScriptsJSON(), null, 2));
};
document.getElementById("pk-dl-demands").onclick = function () {
  if (!PK) { alert("先点「生成行业包」"); return; }
  download("demands.json", JSON.stringify(buildDemandsJSON(), null, 2));
};
document.getElementById("pk-dl-staff").onclick = function () {
  if (!PK) { alert("先点「生成行业包」"); return; }
  download("staff.json", JSON.stringify(buildStaffJSON(), null, 2));
};

// ===== 一键应用到工作台（写 data/ + 备份 + 重建）=====
document.getElementById("pk-apply").onclick = function () {
  if (!PK) { alert("先点「生成行业包」"); return; }
  const box = document.getElementById("pk-apply-result");
  box.innerHTML = '<span style="color:#666">正在写入…</span>';
  fetch("/api/apply-industry", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      industry: PK.ind,
      scripts: buildScriptsJSON(),
      demands: buildDemandsJSON(),
      staff: buildStaffJSON(),
      reset: document.getElementById("pk-reset").checked
    })
  }).then(function (r) { return r.json(); }).then(function (j) {
    if (!j.ok) {
      box.innerHTML = '<span style="color:#c0392b">写入失败：' + (j.error || "未知错误") + '</span>';
      return;
    }
    box.innerHTML =
      '<div style="background:#e8f5e9;border-left:3px solid #2e7d32;padding:11px 13px;border-radius:0 6px 6px 0">' +
      '<b style="color:#2e7d32">✅ 已应用到工作台</b><br>' +
      '行业：<b>' + j.industry + '</b><br>' +
      '已写入：' + (j.written.join("、") || "无") + '<br>' +
      (j.reset.length ? '已清空：' + j.reset.join("、") + '<br>' : '') +
      (j.removed.length ? '已删旧 CSV：' + j.removed.join("、") + '<br>' : '') +
      '旧数据备份：<code>data\\' + j.backup + '\\</code><br>' +
      '<span style="font-size:11px;color:#555">现在点左边「话术库」「需求池」看看 —— 已经是新行业的了。</span>' +
      '</div>';
  }).catch(function (err) {
    box.innerHTML = '<span style="color:#c0392b">连接失败：' + err.message +
      '<br><span style="font-size:11px">请确认工作台是用「启动工作台.vbs」启动的，不要双击 html 文件打开。</span></span>';
  });
};
</script>
"""


def _find_script(name):
    """在几个可能的位置找母本脚本（兼容发布包结构和开发目录结构）"""
    cands = [
        ROOT.parent / "01_browser-scripts" / name,
        ROOT.parent / "意向雷达V1" / name,
        ROOT / name,
    ]
    for p in cands:
        if p.exists():
            return p
    return None


def build_pack():
    import json as _json
    radar_p = _find_script("意向雷达-评论区助手.user.js")
    coll_p = _find_script("采集器_获客采集.user.js")
    radar_src = radar_p.read_text(encoding="utf-8") if radar_p else ""
    coll_src = coll_p.read_text(encoding="utf-8") if coll_p else ""
    if not radar_src or not coll_src:
        print("warning: 未找到母本脚本，行业包生成器只能手动下载数据文件", file=sys.stderr)
    # 塞进 <script> 前把 </ 转义，防止提前闭合
    def safe(s):
        return _json.dumps(s, ensure_ascii=False).replace("</", "<\\/")
    body = PACK_BODY.replace("__RADAR_SRC__", safe(radar_src)).replace("__COLL_SRC__", safe(coll_src))
    return page("pack.html", "pack.html", "行业包生成器",
                "填行业关键词 → 生成「客服雷达包」+「运营采集包」", body)


# ============ 构建 ============
def main():
    SITE.mkdir(exist_ok=True)
    pages = {
        "index.html": build_index(),
        "radar.html": build_radar(),
        "tasks.html": build_tasks(),
        "leads.html": build_leads(),
        "funnel.html": build_funnel(),
        "demands.html": build_demands(),
        "scripts.html": build_scripts(),
        "pack.html": build_pack(),
    }
    for name, content in pages.items():
        (SITE / name).write_text(content, encoding="utf-8")
    print(f"✓ 生成 {len(pages)} 个页面 -> {SITE}")
    print(f"  作品 {work_cnt} · 回复记录 {replied_cnt} · 线索 {lead_cnt} · 收件箱 {len(inbox)} · 需求 {len(demands)} · 话术 {len(scripts_lib)}")
    if _dup_rows:
        print(f"  （已自动跳过重复作品 {_dup_rows} 条）")
    print(f"  打开方式：python serve.py  然后浏览器访问 http://127.0.0.1:8790")


if __name__ == "__main__":
    main()
