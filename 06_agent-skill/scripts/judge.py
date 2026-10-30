# -*- coding: utf-8 -*-
"""判级器：把 radar 扫描出的原始评论，按行业包判成 A/B/R，并生成派单行。

用法（被 run.py 调用，也可单独跑）：
    python judge.py --raw raw.json --pack packs/云南旅游.json --out judged.json
"""
import argparse, hashlib, json, re, pathlib
from collections import Counter

NOISE = {"...", "…", "话", "分享", "回复", "作者", "展开", "收起", "赞", "", "置顶评论", "展开更多", "更多回复"}
TIME_RE = re.compile(r"^(\d+[分小时天月年]前|昨天|前天|刚刚|今天|\d{1,2}-\d{1,2}|\d{4}-\d{1,2}-\d{1,2}|\d{2}-\d{2})")
ID_RE = re.compile(r"/video/(\d+)|modal_id=(\d+)|/explore/([0-9a-zA-Z]+)|/short-video/([0-9a-zA-Z]+)|noteId=([0-9a-zA-Z]+)")


def parse_comment(raw: str):
    """通用解析：去噪 → 首行当昵称 → 剩下的取最长一段当评论。

    不按「作者」截断：抖音的 comment-item 会内嵌作者回复，小红书的 parent-comment 里
    「作者」只是一个徽章。两种情况的正确处理都是「去掉徽章、取最长内容」。
    """
    lines = [l.strip() for l in (raw or "").splitlines()]
    user, content, meta = None, "", ""
    cand = []
    for l in lines:
        if l in NOISE or re.fullmatch(r"\d+", l or ""):
            continue
        if TIME_RE.match(l):
            meta = l
            continue
        if user is None:
            user = l
            continue
        cand.append(l)
    if cand:
        content = max(cand, key=len)
    return user or "", content or "", meta or ""


def judge_one(content: str, pack: dict):
    low = content
    a_hits = [w for w in pack.get("a_words", []) if w in low]
    b_hits = [w for w in pack.get("b_words", []) if w in low]
    red_hits = [w for w in pack.get("red_words", []) if w.lower() in low.lower()]
    neg_hits = [w for w in pack.get("neg_patterns", []) if w in low]
    prod = pack.get("prod_words") or []
    has_prod = (not prod) or any(w in low for w in prod)

    if red_hits or neg_hits:
        return "R", 0, red_hits + neg_hits, False
    if not has_prod:
        return "", 0, a_hits + b_hits, False
    if a_hits:
        return "A", 100 + len(a_hits) * 10, a_hits, True
    if b_hits:
        return "B", 50 + len(b_hits) * 5, b_hits, True
    return "", 0, [], False


def pick_script(hits, pack: dict):
    scripts = pack.get("scripts", {}) or {}
    for w in hits:
        for k, v in scripts.items():
            if k in w or w in k:
                return v
    if hits:
        for k in ("多少钱", "钱", "报名", "定制"):
            if k in scripts:
                return scripts[k]
    return ""


def judge(raw_path, pack_path, out_path):
    raw = json.loads(pathlib.Path(raw_path).read_text(encoding="utf-8"))
    pack = json.loads(pathlib.Path(pack_path).read_text(encoding="utf-8"))

    works, dispatched = [], []
    for v in raw.get("videos", []):
        if not v.get("ok"):
            continue
        rows = []
        for raw_text in v.get("comments", []):
            user, content, meta = parse_comment(raw_text)
            if not content or len(content) < 2:
                continue
            level, score, hits, _ = judge_one(content, pack)
            rows.append({
                "等级": level, "分数": score, "用户": user, "评论": content,
                "时间地区": meta, "命中词": "/".join(hits),
                "建议话术": pick_script(hits, pack) if level in ("A", "B") else "",
            })
        rows.sort(key=lambda r: -r["分数"])
        a = sum(1 for r in rows if r["等级"] == "A")
        b = sum(1 for r in rows if r["等级"] == "B")
        m = ID_RE.search(v.get("url", "") or "")
        vid = next((g for g in m.groups() if g), str(v.get("idx"))) if m else str(v.get("idx"))
        works.append({
            "id": "ag-" + vid,
            "date": raw.get("scannedAt", "")[:10],
            "platform": raw.get("platformName") or "抖音",
            "title": (v.get("videoDesc") or v.get("cardText") or "")[:60],
            "url": v.get("url", ""),
            "views": 0,
            "comments": len(rows),
            "a_count": a,
            "b_count": b,
            "staff": "",
            "status": "待派",
            "_from": "agent",
            "_author": v.get("author", ""),
            "scanned_at": raw.get("scannedAt", ""),
        })
        for r in rows:
            if r["等级"] in ("A", "B"):
                did = hashlib.md5(
                    f"{works[-1]['url']}|{r['用户']}|{r['评论']}".encode("utf-8")
                ).hexdigest()[:12]
                dispatched.append({
                    "id": did,
                    "作品": works[-1]["title"],
                    "链接": works[-1]["url"],
                    "平台": works[-1]["platform"],
                    "扫描时间": works[-1]["scanned_at"],
                    **r,
                })

    result = {
        "keyword": raw.get("keyword"),
        "pack": pack.get("name"),
        "scannedAt": raw.get("scannedAt"),
        "works": works,
        "dispatched": dispatched,
        "stats": {
            "videos": len(works),
            "comments": sum(w["comments"] for w in works),
            "A": sum(w["a_count"] for w in works),
            "B": sum(w["b_count"] for w in works),
        },
    }
    pathlib.Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = judge(a.raw, a.pack, a.out)
    s = r["stats"]
    print(f"判级完成：视频 {s['videos']} 个 · 评论 {s['comments']} 条 · A {s['A']} · B {s['B']}")
