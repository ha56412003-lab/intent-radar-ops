# -*- coding: utf-8 -*-
"""雷达编排器：ego 扫描 → 判级 → 写回工作台（data/works.json + scan_meta.json）。

一次调用完成「扫关键词 → 挑意向 → 派单表」。
    python run.py --keyword 云南旅游 --videos 3 --rounds 2
    python run.py --pack packs/云南旅游.json --keywords 云南旅游,云南跟团 --videos 2

不需要人工导出任何 CSV：结果直接写进 02_workbench/data/。
"""
import argparse, csv, glob, json, os, pathlib, shutil, subprocess, sys, time
from urllib.parse import quote

HERE = pathlib.Path(__file__).resolve().parent          # .../scripts
PKG = HERE.parent                                        # SKILL 包根
ROOT = PKG.parent                                        # 若在工作台项目里，就是「获客系统/」
OUT_DIR = PKG / "out"
PACKS = PKG / "packs"


def resolve_data(cli=None):
    """数据落点：优先工作台的 data/；独立使用时落到包内 data/。"""
    if cli:
        d = pathlib.Path(cli)
    elif (ROOT / "02_workbench" / "data").exists():
        d = ROOT / "02_workbench" / "data"
    else:
        d = PKG / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


DATA = resolve_data()

DEFAULTS = {
    "platform": "douyin",
    "videos": 3,
    "rounds": 2,
    "space": "意向雷达",
    "preScrolls": 2,
    "scrollWaitMs": 2200,
}

# 各平台的选择器与节奏。douyin 已实测通过；xhs / ks 待登录后校准（标 ⚠ 的就是待校准项）
PLATFORMS = {
    "douyin": {
        "label": "抖音",
        "searchUrl": "https://www.douyin.com/search/{kw}",
        "cardSels": [".search-result-card", 'a[href*="/video/"]'],
        "detailRe": "modal_id=|/video/",
        "commentIconSel": '[data-e2e="feed-comment-icon"]',
        "commentItemSel": '[data-e2e="comment-item"]',
        "commentListSels": ['[data-e2e="comment-list"]'],
        "descSel": '[data-e2e="video-desc"]',
        "authorSel": '[data-e2e="feed-video-nickname"]',
        "detailOpenSel": '[data-e2e="modal-video-container"]',
        "closeSel": None,
        "closeKey": "Escape",
        "firstWaitMs": 3500,
        "detailWaitMs": 4000,
        "verified": True,
    },
    "xhs": {
        "label": "小红书",
        "searchUrl": "https://www.xiaohongshu.com/search_result?keyword={kw}",
        "cardSels": ["section.note-item", ".note-item"],
        "detailRe": "/explore/|noteId=|/discovery/item",
        "commentIconSel": None,
        "commentItemSel": ".parent-comment",
        "commentListSels": [".note-scroller", ".comments-el", ".comments-container"],
        "noCommentSel": ".no-comments",
        "descSel": "#detail-title, .note-content .title, .note-scroller .title",
        "authorSel": ".author-wrapper .username, .author-container .username",
        "detailOpenSel": ".note-detail-mask",
        "closeSel": None,
        "closeKey": "Escape",
        "firstWaitMs": 5000,
        "detailWaitMs": 5000,
        "verified": True,
    },
    "ks": {
        "label": "快手",
        "searchUrl": "https://www.kuaishou.com/search/video?searchKey={kw}",
        "cardSels": [".photo-card", ".card-container"],
        "detailRe": "search/video|/short-video/|photoId",
        "detailDomSel": "video",
        "useRealMouse": True,
        "commentIconSel": None,
        "commentItemSel": '[class*="comment-item"], [class*="commentItem"], .comment-list > div',
        "commentListSels": [".comment-panel", ".comments", ".comment-list", '[class*="comment-list"]'],
        "noCommentSel": None,
        "descSel": ".video-info-title, .work-description, .caption",
        "authorSel": ".user-name, .profile-user-name, .name",
        "detailOpenSel": "video",
        "closeSel": None,
        "closeKey": "Escape",
        "firstWaitMs": 6000,
        "detailWaitMs": 6000,
        "verified": False,
    },
}


def find_ego():
    # 0) 安装脚本记下的路径
    pf = HERE.parent / ".ego-path"
    if pf.exists():
        p = pf.read_text(encoding="utf-8").strip().lstrip("\ufeff")
        if p and pathlib.Path(p).exists():
            return p
    exe = shutil.which("ego-browser")
    if exe:
        return exe
    roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("LOCALAPPDATA", "") + r"\Programs"]
    for r in roots:
        if not r:
            continue
        hits = glob.glob(os.path.join(r, "Citro Labs", "ego lite", "Application", "*", "ego-browser.exe"))
        if hits:
            return sorted(hits)[-1]
    return None


def load_pack(path):
    p = pathlib.Path(path)
    if not p.suffix:
        p = p.with_suffix(".json")
    if not p.is_absolute() and not p.exists():
        p = PACKS / p.name
    if not p.exists():
        cands = list(PACKS.glob("*.json"))
        raise SystemExit(f"找不到行业包 {path}。现有：{[c.name for c in cands]}")
    return json.loads(p.read_text(encoding="utf-8")), p


def run_scan(ego, cfg, ts):
    plat = cfg.get("platform", "douyin")
    preset = PLATFORMS.get(plat)
    if not preset:
        raise SystemExit(f"不支持的平台 {plat}，可选：{list(PLATFORMS)}")
    tpl = (HERE / "scan_template.mjs").read_text(encoding="utf-8")
    script = HERE.parent / "out" / f"scan_{ts}.mjs"
    script.parent.mkdir(parents=True, exist_ok=True)
    raw_path = HERE.parent / "out" / f"raw_{ts}.json"
    cfg = dict(
        cfg,
        preset=preset,
        searchUrl=preset["searchUrl"].format(kw=quote(cfg["keyword"])),
        out=str(raw_path).replace("\\", "/"),
        outDir=str(raw_path.parent).replace("\\", "/"),
    )
    script.write_text(tpl.replace("__CFG__", json.dumps(cfg, ensure_ascii=False)), encoding="utf-8")

    flag = "" if preset.get("verified") else "（选择器未校准）"
    print(f"→ 扫描中：{preset['label']}{flag}｜关键词「{cfg['keyword']}」｜最多 {cfg['videos']} 个内容 × {cfg['rounds']} 屏评论…")
    with open(script, "rb") as fh:
        r = subprocess.run([ego, "nodejs"], stdin=fh, capture_output=True, timeout=1800)
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    for line in out.splitlines():
        if line.startswith("[scan]") or "Error" in line:
            print("  " + line.strip())
    if not raw_path.exists():
        raise SystemExit("扫描没有产出结果文件。\n" + out[-2000:])
    return raw_path


def run_judge(raw_path, pack_path, ts):
    judged_path = HERE.parent / "out" / f"judged_{ts}.json"
    r = subprocess.run([sys.executable, str(HERE / "judge.py"), "--raw", str(raw_path),
                        "--pack", str(pack_path), "--out", str(judged_path)],
                       capture_output=True)
    print("  " + (r.stdout or b"").decode("utf-8", "replace").strip())
    if r.returncode != 0:
        raise SystemExit("判级失败：\n" + (r.stderr or b"").decode("utf-8", "replace"))
    return json.loads(judged_path.read_text(encoding="utf-8"))


def merge_works(new_works):
    """按 url 合并：意向数刷新，人工维护的 staff/status 保留。"""
    p = DATA / "works.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    # 清掉自带的示例数据（url 里带 demo 的），别混进真实清单
    old = [w for w in old if "demo" not in (w.get("url") or "")]
    idx = {w.get("url", ""): w for w in old if w.get("url")}
    merged, added, updated = [], 0, 0
    for w in new_works:
        prev = idx.pop(w["url"], None)
        if prev:
            prev.update({k: w[k] for k in ("a_count", "b_count", "comments", "title", "scanned_at")})
            prev["_from"] = "agent"
            merged.append(prev)
            updated += 1
        else:
            merged.append(w)
            added += 1
    merged.extend(idx.values())  # 旧的、这次没扫到的保留
    p.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    return added, updated, len(merged)


def write_dispatched(result):
    """把 A/B 级评论明细写进工作台，供「待回复清单」用；按 id 去重累积。"""
    p = DATA / "dispatched.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    seen = {d.get("id") for d in old}
    added = 0
    for d in result.get("dispatched", []):
        if not d.get("id") or d["id"] in seen:
            continue
        seen.add(d["id"])
        old.append(d)
        added += 1
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    return added, len(old)


def write_meta(result, pack_name, keyword):
    meta = {
        "last_scan": result.get("scannedAt"),
        "keyword": keyword,
        "pack": pack_name,
        "videos": result["stats"]["videos"],
        "comments": result["stats"]["comments"],
        "a": result["stats"]["A"],
        "b": result["stats"]["B"],
        "agent": "ego-browser",
        "host": os.environ.get("COMPUTERNAME", ""),
    }
    (DATA / "scan_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def write_dispatch(result, ts):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = result["dispatched"]
    md = OUT_DIR / f"派单表_{ts}.md"
    cs = OUT_DIR / f"派单表_{ts}.csv"
    with open(cs, "w", encoding="utf-8-sig", newline="") as f:
        fields = ["等级", "分数", "作品", "用户", "评论", "时间地区", "命中词", "建议话术", "链接"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    lines = [f"# 意向派单表 · {result['pack']} · {ts}", ""]
    s = result["stats"]
    lines += [f"- 关键词：{result['keyword']}", f"- 视频 {s['videos']} 个｜评论 {s['comments']} 条｜**A {s['A']} / B {s['B']}**", "",
              "| 等级 | 用户 | 评论 | 命中词 | 建议话术 |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['等级']} | {r['用户']} | {r['评论'][:60]} | {r['命中词']} | {str(r['建议话术'])[:50]} |")
    md.write_text("\n".join(lines), encoding="utf-8")
    return md, cs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="云南旅游", help="行业包名或路径")
    ap.add_argument("--keyword", default="", help="单个关键词")
    ap.add_argument("--keywords", default="", help="多个关键词，逗号分隔")
    ap.add_argument("--videos", type=int, default=DEFAULTS["videos"])
    ap.add_argument("--rounds", type=int, default=DEFAULTS["rounds"])
    ap.add_argument("--space", default=DEFAULTS["space"])
    ap.add_argument("--platform", default="", help="douyin / xhs / ks（默认取行业包里的 platform）")
    ap.add_argument("--ego", default="", help="ego-browser 可执行文件路径（默认自动找）")
    ap.add_argument("--data", default="", help="工作台 data 目录（默认自动找；独立使用时写到包内 data/）")
    ap.add_argument("--no-write", action="store_true", help="只出派单表，不写进工作台（试跑用）")
    a = ap.parse_args()

    if a.data:
        global DATA
        DATA = resolve_data(a.data)
        print(f"数据落点 = {DATA}")

    pack, pack_path = load_pack(a.pack)
    kws = [k.strip() for k in (a.keywords or a.keyword or ",".join(pack.get("keywords", [])[:1])).split(",") if k.strip()]
    if not kws:
        raise SystemExit("没有关键词：用 --keyword 指定，或写进行业包的 keywords")

    ego = a.ego or find_ego()
    if not ego:
        raise SystemExit("找不到 ego-browser。先装 ego(lite)（见 install/ 目录），或加 --ego 指定路径。")
    print(f"ego-browser = {ego}")
    print(f"行业包 = {pack['name']}（{pack_path.name}）｜关键词 {kws}")

    all_works, last = [], None
    for kw in kws:
        ts = time.strftime("%Y%m%d-%H%M%S")
        cfg = dict(DEFAULTS, keyword=kw, platform=(a.platform or pack.get("platform", "douyin")),
                   videos=a.videos, rounds=a.rounds, space=a.space)
        raw = run_scan(ego, cfg, ts)
        rj = json.loads(raw.read_text(encoding="utf-8"))
        if rj.get("loginRequired"):
            raise SystemExit(
                f"\n「{kw}」需要先登录 {rj.get('platformName')}：\n"
                f"  ① 在 ego 窗口里切到对应标签，用手机扫码登录\n"
                f"  ② 登录后重跑同一条命令\n"
            )
        res = run_judge(raw, pack_path, ts)
        last = res
        all_works.extend(res["works"])
        print(f"  「{kw}」：视频 {res['stats']['videos']}｜评论 {res['stats']['comments']}｜A {res['stats']['A']} B {res['stats']['B']}")

    if last is None:
        raise SystemExit("扫描没有产出结果，检查一下 ego 是否登录、窗口是否最小化")
    if a.no_write:
        added = updated = total = 0
        d_added = d_total = 0
        meta = {"a": last["stats"]["A"], "b": last["stats"]["B"]}
        print("\n（--no-write：只出派单表，没有写进工作台）")
    else:
        added, updated, total = merge_works(all_works)
        d_added, d_total = write_dispatched(last)
        meta = write_meta(last, pack["name"], ",".join(kws))
    md, cs = write_dispatch(last, time.strftime("%Y%m%d-%H%M%S"))

    print("\n" + "=" * 46)
    print(f"写回工作台：新增 {added} 条作品 / 更新 {updated} 条 / 清单共 {total} 条")
    print(f"扫了两遍？看这个：{DATA / 'works.json'}")
    print(f"派单表：{md.name} / {cs.name}（在 {OUT_DIR}）")
    print(f"本次共判出 A {meta['a']} 条、B {meta['b']} 条")
    print("=" * 46)
    print("下一步：双击「启动工作台.vbs」→ 看「今日清单」和「派单台」")


if __name__ == "__main__":
    main()
