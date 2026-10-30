# -*- coding: utf-8 -*-
"""行业包向导：填几个问题，生成一个能直接跑的行业包。

交互式（推荐给运营经理）：
    python scripts/new_pack.py

一行是非交互（给 Agent / 脚本用）：
    python scripts/new_pack.py --name 电瓶车电池 --keywords 换电池,锂电池,以旧换新 --prod 电池,电瓶
"""
import argparse, json, pathlib, shutil, sys, time

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
PACKS = PKG / "packs"
ROOT = PKG.parent
DATA = ROOT / "02_workbench" / "data"

# ---------- 通用词表（跨行业都成立的说法，来自真实评论区归纳） ----------
A_PURE = [
    "多少钱", "什么价", "什么价格", "价格", "报价", "怎么卖", "怎么买", "哪里买", "在哪买",
    "能买吗", "哪个好", "怎么选", "选哪个", "求推荐", "推荐一下", "能上门吗", "包安装吗",
    "上门安装", "保修多久", "能用多久", "有售后吗", "以旧换新", "能置换吗", "包邮吗",
    "能发货吗", "怎么联系", "有货吗", "能修吗", "想买", "要买", "想换", "要换", "准备换", "求购",
    "怎么报名", "如何报名", "在哪报名", "怎么参加", "求带", "人均", "预算", "团费", "几号出发",
    "什么时候有", "最近有吗", "带老人", "带爸妈", "带小孩", "亲子", "一家几口",
]
B_PURE = [
    "求攻略", "有攻略吗", "求推荐", "怎么玩", "怎么去", "路线", "行程", "几天合适", "玩几天",
    "门票", "住宿", "住哪里", "交通", "求组队", "有人一起吗", "避坑", "防坑", "被坑", "踩雷",
    "淡季", "旺季", "几月去", "最佳时间", "靠谱吗", "值得吗", "体验怎么样",
]
RED_PURE = ["微信", "vx", "V信", "wechat", "手机号", "电话", "二维码", "加我好友"]
NEG_PURE = ["不要打广告", "别打广告", "打广告", "广告", "骗子", "举报", "同行", "别at", "不要at", "拉客", "托"]

# ---------- 话术骨架（{ind} 换成行业名；跑真实评论后必须改成自己的话） ----------
SCRIPT_TPL = {
    "多少钱": "{ind}的价格看具体需求和数量，你说下大概情况，我给你报个准价，费用一项项写清楚～",
    "怎么买": "告诉我你要什么规格、多少量，我把费用和流程写清楚，不玩套路～",
    "怎么报名": "报名很简单，告诉我人数和时间，我把安排和细节发你，你看了再决定～",
    "哪个好": "看你怎么用：{ind}不同档位差别在配置上，你说下主要用途，我帮你挑一个不踩坑的～",
    "能上门吗": "你这边位置在哪？上门能安排，我先把费用说清楚再约时间～",
    "保修": "正常使用都有保修，具体年限看型号，我发一份保修说明给你～",
    "以旧换新": "以旧换新可以做，旧的能抵多少要看状态，你拍张照我帮你估个价～",
    "求推荐": "你说一下预算和主要用途，我给你推荐两个档位对比着看，不推荐最贵的～",
    "靠谱吗": "我们自己做了几年了，可以先给你看真实反馈和老客户评价，你自己判断～",
    "几天": "{ind}这类看你想怎么安排：紧凑型 X 天够用，宽松型建议 Y 天，你假期几天？我帮你选～",
}


def ask(prompt, default=""):
    hint = f"（{default}）" if default else ""
    v = input(f"{prompt}{hint}：").strip()
    return v or default


def gen_pack(name, keywords, prod_words, platforms, extra_a="", extra_b=""):
    kw = [k.strip() for k in keywords if k.strip()]
    prod = [p.strip() for p in prod_words if p.strip()]
    a = list(dict.fromkeys(A_PURE + [x.strip() for x in extra_a.split(",") if x.strip()]))
    b = list(dict.fromkeys(B_PURE + [x.strip() for x in extra_b.split(",") if x.strip()]))
    scripts = {}
    for k, tpl in SCRIPT_TPL.items():
        scripts[k] = tpl.replace("{ind}", name)
        scripts[k] = scripts[k].replace("X 天", "3-5 天").replace("Y 天", "7-10 天")
    return {
        "name": name,
        "platform": (platforms[0] if platforms else "douyin"),
        "platforms": platforms or ["douyin"],
        "version": "1.0.0",
        "note": "向导生成于 " + time.strftime("%Y-%m-%d") + "，词库和话术是骨架，跑真实评论后必须校准",
        "keywords": kw,
        "prod_words": prod,
        "a_words": a,
        "b_words": b,
        "red_words": list(RED_PURE),
        "neg_patterns": list(NEG_PURE),
        "scripts": scripts,
    }


def gen_demands(name, kw):
    k = kw[0] if kw else name
    return [
        {"question": f"{k}多少钱 / 什么价", "count": 0, "tag": "价格", "topic": "把价格差异讲清楚（配置 + 区间），别只说'便宜'", "published": False},
        {"question": "怎么选 / 哪个好", "count": 0, "tag": "选择困难", "topic": "按使用场景给一套选择框架（3 个问题定档位）", "published": False},
        {"question": "靠谱吗 / 会不会被坑", "count": 0, "tag": "信任", "topic": "真实反馈 + 售后承诺，正面回应最常被问的顾虑", "published": False},
        {"question": "能便宜点吗", "count": 0, "tag": "价格", "topic": "把'为什么值这个价'讲清楚，而不是直接降价", "published": False},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="", help="行业名，如 电瓶车电池")
    ap.add_argument("--keywords", default="", help="关键词，逗号分隔（客户真会说的词）")
    ap.add_argument("--prod", default="", help="产品词（闸门，评论必须提到才算意向）")
    ap.add_argument("--platform", default="", help="douyin / xhs / ks，逗号分隔可多个")
    ap.add_argument("--extra-a", default="", help="额外的强意向词，逗号分隔")
    ap.add_argument("--extra-b", default="", help="额外的兴趣词，逗号分隔")
    ap.add_argument("--apply", action="store_true", help="同时写进工作台（scripts.json / demands.json）")
    ap.add_argument("--force", action="store_true", help="同名行业包已存在时直接覆盖")
    a = ap.parse_args()

    interactive = not (a.name and a.keywords)
    print("=" * 52)
    print("  行业包向导 · 4 个问题，生成一个能直接跑的包")
    print("=" * 52)

    if interactive:
        name = a.name or ask("① 行业名（例：电瓶车电池）")
        if not name:
            sys.exit("行业名不能为空")
        print("\n  关键词 = 客户在评论区真的会说的词，越具体越准")
        print("  ✅ 好：换电池、锂电池、以旧换新    ❌ 差：电瓶车、电池（太宽，全是噪音）")
        keywords = a.keywords or ask("② 关键词（逗号分隔）")
        print("\n  产品词 = 评论里必须提到它，才算意向（防止'多少钱'这种泛词误报）")
        prod = a.prod or ask("③ 产品词（逗号分隔；留空=不限制）", "")
        plats = a.platform or ask("④ 平台 douyin/xhs/ks（逗号分隔）", "douyin")
        extra_a = ask("⑤ 额外强意向词（可留空，跑完真实评论再补）", "")
        extra_b = ""
    else:
        name, keywords, prod = a.name, a.keywords, a.prod
        plats, extra_a, extra_b = a.platform or "douyin", a.extra_a, a.extra_b

    platforms = [p.strip() for p in plats.split(",") if p.strip()]
    kw = [k.strip() for k in keywords.split(",") if k.strip()]
    if not kw:
        sys.exit("至少要给一个关键词")

    pack = gen_pack(name, kw, prod.split(","), platforms, extra_a, extra_b)

    PACKS.mkdir(parents=True, exist_ok=True)
    out = PACKS / f"{name}.json"
    if out.exists() and not a.force:
        if interactive:
            yn = ask(f"  ⚠ {out.name} 已存在，覆盖吗？(y/N)", "N")
            if yn.lower() != "y":
                sys.exit("已取消")
        else:
            sys.exit(f"{out.name} 已存在（加 --force 覆盖）")
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 52)
    print(f"✓ 行业包已生成：{out}")
    print(f"  行业 {pack['name']}｜平台 {', '.join(platforms)}")
    print(f"  关键词 {len(kw)} 个｜产品词 {len(pack['prod_words'])} 个")
    print(f"  A 级词 {len(pack['a_words'])}｜B 级词 {len(pack['b_words'])}｜话术 {len(pack['scripts'])} 条")

    # 可选：同步到工作台
    do_apply = a.apply
    if interactive and not do_apply:
        print("\n  ⚠ 写进工作台会覆盖现有的话术库/需求池（旧文件会自动备份）")
        do_apply = ask("  要写进工作台吗？(y/N)", "N").lower() == "y"

    if do_apply and DATA.exists():
        ts = time.strftime("%Y%m%d_%H%M%S")
        body = [{"grade": "A" if k in pack["a_words"] else "B", "scene": k, "text": v, "sent": 0, "replied": 0}
                for k, v in pack["scripts"].items()]
        for fn, content in (("scripts.json", body), ("demands.json", gen_demands(name, kw))):
            p = DATA / fn
            if p.exists():
                shutil.copy2(p, DATA / f"{fn}.bak_{ts}")
            p.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ 已写进工作台（旧文件备份为 *.bak_{ts}），重开工作台就能看到新话术和需求池")

    print("\n下一步（先试扫一次，看命中率再说）：")
    print(f"  python scripts/run.py --pack \"{name}\" --keyword {kw[0]} --videos 2 --rounds 2")
    print("\n⚠ 词库是草稿。扫完 200-300 条真实评论，把客户真会说的说法补进 a_words，命中率才上得来。")
    print("=" * 52)


if __name__ == "__main__":
    main()
