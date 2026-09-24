#!/usr/bin/env python3
"""
Compile data/records/*.yaml into a rich, structured, and beautifully formatted README.md
"""

import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    print("❌ 错误: 未安装 PyYAML，请运行 pip install pyyaml 安装。")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECORDS_DIR = PROJECT_ROOT / "data" / "records"
README_FILE = PROJECT_ROOT / "README.md"

def load_records():
    records = []
    if not RECORDS_DIR.exists():
        return records

    for file_path in sorted(RECORDS_DIR.glob("*.yaml")) + sorted(RECORDS_DIR.glob("*.yml")):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and data.get("id"):
                    data["_file"] = file_path.name
                    records.append(data)
            except Exception as e:
                print(f"⚠️ 跳过解析失败文件 {file_path.name}: {e}")
    return records

def generate_markdown(records):
    total_records = len(records)
    
    # Aggregations
    advertisers_map = defaultdict(lambda: {
        "count": 0,
        "parent_company": set(),
        "categories": set(),
        "hosts": set(),
        "offenses": Counter()
    })
    
    hosts_map = defaultdict(lambda: {
        "count": 0,
        "platforms": set(),
        "advertisers": set(),
        "offenses": Counter()
    })

    offense_counter = Counter()
    host_alternatives_map = defaultdict(set)
    advertiser_alternatives_map = defaultdict(set)

    for r in records:
        adv = r.get("advertiser", {})
        adv_name = adv.get("name", "未知品牌")
        category = adv.get("category", "其他")
        parent = adv.get("parent_company")
        
        host = r.get("host_app", {})
        host_name = host.get("name", "未知APP")
        platform = host.get("platform", "未知")

        offenses = r.get("offense_type", [])
        for off in offenses:
            offense_counter[off] += 1
            advertisers_map[adv_name]["offenses"][off] += 1
            hosts_map[host_name]["offenses"][off] += 1

        advertisers_map[adv_name]["count"] += 1
        advertisers_map[adv_name]["categories"].add(category)
        if parent:
            advertisers_map[adv_name]["parent_company"].add(parent)
        advertisers_map[adv_name]["hosts"].add(host_name)

        hosts_map[host_name]["count"] += 1
        hosts_map[host_name]["platforms"].add(platform)
        hosts_map[host_name]["advertisers"].add(adv_name)

        # Host alternatives
        h_alts = r.get("host_alternatives", [])
        if not h_alts and "suggested_alternatives" in r:
            h_alts = r.get("suggested_alternatives", [])
        for h_alt in h_alts:
            if h_alt.strip():
                host_alternatives_map[host_name].add(h_alt.strip())

        # Advertiser alternatives
        a_alts = r.get("advertiser_alternatives", [])
        for a_alt in a_alts:
            if a_alt.strip():
                advertiser_alternatives_map[category].add(a_alt.strip())

    unique_advertisers = len(advertisers_map)
    unique_hosts = len(hosts_map)

    # Sort records chronologically (descending), tie-break with id
    sorted_records = sorted(records, key=lambda x: (str(x.get("date", "")), str(x.get("id", ""))), reverse=True)

    lines = []
    lines.append("# fucking-ad")
    lines.append("### 移动端不良广告与诱导跳转留存实录")
    lines.append("")
    lines.append("> 🌐 **在线曝光检索站（即时检索 · 移动端适配）**：**[https://hp-z3.github.io/fucking-ad/](https://hp-z3.github.io/fucking-ad/)**  ")
    lines.append("> 💬 **「商业营销不应建立在对用户的戏弄之上。天下苦流氓广告久矣，以图为证，客观留存移动端各类恶意诱导与流氓跳转。」**  ")
    lines.append("> ⚡ **「互联网也许健忘，但开源社区有据可循。让每一次粗暴打扰留下公开透明的存证档案。」**")
    lines.append("")
    lines.append("[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)")
    lines.append("[![Online Portal](https://img.shields.io/badge/Online%20Web-在线检索站-cyan.svg)](https://hp-z3.github.io/fucking-ad/)")
    lines.append(f"![Total Records](https://img.shields.io/badge/收录案例-{total_records}起-slate.svg)")
    lines.append(f"![Advertiser Brands](https://img.shields.io/badge/涉及广告主-{unique_advertisers}家-slate.svg)")
    lines.append(f"![Host Apps](https://img.shields.io/badge/涉及宿主APP-{unique_hosts}款-slate.svg)")
    lines.append("[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🎯 项目初衷 (Manifesto)")
    lines.append("")
    lines.append("你是否也经历过这些令人啼笑皆非的日常时刻？")
    lines.append("- 走在路上刚掏出手机，手腕稍微一偏，手机陀螺仪便以迅雷不及掩耳之势判定为“扭动手机”，猝不及防为你推开电商百亿补贴的大门；")
    lines.append("- 弹窗右上角的叉号仿佛是在视力表最后一行选拔出来的，尺寸微小且难以辨认，稍有不慎点偏半个像素，立即启动后台下载流水线；")
    lines.append("- 红色横幅赫然写着“200,000元备用金即将失效”或仿冒微信未读红包，专挑防备心较低的长辈或注意力分散的用户下手；")
    lines.append("- 明明充值了年度会员，打开 APP 依然要面对体贴的 5 秒开屏全屏推荐——关闭按钮甚至延迟 3 秒才慢条斯理地浮现。")
    lines.append("")
    lines.append("不少人在被惊扰时暗下决心：*“这家公司的产品我坚决不用！”*  ")
    lines.append("然而，劣质营销恰恰利用了人类的**遗忘效应**：一段时间后，用户往往只记住了该品牌的“知名度与曝光量”，却遗忘了它曾粗暴打扰过自己的日常——**诱导投放由此达成了商业转化。**")
    lines.append("")
    lines.append("**本项目旨在建立一份客观、公开、可查证的「移动端不良广告与诱导跳转留存名录」**：")
    lines.append("1. **客观存证**：把每一次违规打扰记录成结构化数据，附带真实截图留存，让非体面的交互留下公开档案。")
    lines.append("2. **理性避雷**：消费即投票。在日常消费与服务选购前搜一搜，把预算留给真正尊重用户的体面品牌。")
    lines.append("3. **正向替代**：整理体面、清爽的开源与干净替代软件，协助大家逐步卸载肆意骚扰的宿主应用。")
    lines.append("4. **社区共建**：汇聚广泛用户的真实日常样本，促使商业广告重新回归体面与克制。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 案例总览与统计")
    lines.append("")
    lines.append(f"- 📝 **已收录案例样本**：`{total_records}` 起")
    lines.append(f"- 🏢 **涉及广告主品牌**：`{unique_advertisers}` 家")
    lines.append(f"- 📱 **载体宿主应用数**：`{unique_hosts}` 款")
    lines.append("")

    if total_records == 0:
        lines.append("> 💡 **名录初始化就绪**：当前暂无收录案例。天下手机用户苦不良弹窗久矣，欢迎[通过 Issue 提交案例](../../issues/new?template=report_ad.yml)成为第一个贡献者！")
        lines.append("")
    else:
        lines.append("### 🔥 典型诱导与打扰手段分布")
        lines.append("")
        lines.append("| 手段类型 | 出现频次 | 占比 | 典型表现 |")
        lines.append("| :--- | :---: | :---: | :--- |")
        sorted_offenses = sorted(offense_counter.items(), key=lambda x: (-x[1], x[0]))
        for off_name, off_count in sorted_offenses:
            pct = f"{(off_count / total_records * 100):.1f}%"
            lines.append(f"| **{off_name}** | `{off_count}` | {pct} | 滥用传感器、微小假关闭按钮、视觉欺诈 |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🏢 涉事品牌关注名录 (消费避雷参考)")
    lines.append("")
    lines.append("> 提示：消费即投票。日常消费与服务选购时，可参考以下频繁使用诱导式弹窗投放的品牌名录。")
    lines.append("")

    if advertisers_map:
        lines.append("| 品牌名称 | 所属主体企业 | 涉及品类 | 留存案例数 | 常见载体宿主 |")
        lines.append("| :--- | :--- | :--- | :---: | :--- |")
        sorted_advs = sorted(advertisers_map.items(), key=lambda x: (x[1]["count"], x[0]), reverse=True)
        for adv_name, info in sorted_advs:
            parent_str = "、".join(sorted(info["parent_company"])) if info["parent_company"] else "未知"
            cat_str = "、".join(sorted(info["categories"]))
            hosts_list = sorted(list(info["hosts"]))
            hosts_str = "、".join(hosts_list[:3]) + (" 等" if len(hosts_list) > 3 else "")
            lines.append(f"| **{adv_name}** | {parent_str} | {cat_str} | `{info['count']}` | {hosts_str} |")
    else:
        lines.append("> *当前暂无涉事品牌记录，等待社区提报。*")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📱 载体宿主应用观察榜 (高频弹窗发生地)")
    lines.append("")

    if hosts_map:
        lines.append("| 宿主 APP | 平台 | 留存案例数 | 典型手段 | 常见推广品牌 | 推荐替代方案 |")
        lines.append("| :--- | :---: | :---: | :--- | :--- | :--- |")
        sorted_hosts = sorted(hosts_map.items(), key=lambda x: (x[1]["count"], x[0]), reverse=True)
        for host_name, info in sorted_hosts:
            plat_str = " / ".join(sorted(info["platforms"]))
            sorted_host_offenses = sorted(info["offenses"].items(), key=lambda x: (-x[1], x[0]))
            top_offenses = "、".join([k for k, _ in sorted_host_offenses[:2]])
            advs_list = sorted(list(info["advertisers"]))
            top_advs = "、".join(advs_list[:3])
            alts = host_alternatives_map.get(host_name, set())
            sorted_alts = sorted(list(alts))
            alt_str = "、".join(sorted_alts[:2]) if sorted_alts else "寻找纯净替代"
            lines.append(f"| **{host_name}** | {plat_str} | `{info['count']}` | {top_offenses} | {top_advs} | {alt_str} |")
    else:
        lines.append("> *当前暂无宿主应用记录，等待社区提报。*")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📋 最新案例档案库")
    lines.append("")

    if sorted_records:
        lines.append("<details>")
        lines.append("<summary><b>👉 点击展开查看所有留存的历史案例细节（按日期倒序）</b></summary>")
        lines.append("")

        for r in sorted_records:
            rid = r.get("id")
            date = r.get("date")
            adv = r.get("advertiser", {})
            host = r.get("host_app", {})
            offenses = "、".join([f"`{o}`" for o in r.get("offense_type", [])])
            import re
            desc = re.sub(r"<[^>]+>", "", r.get("description", "")).strip()
            evidence = r.get("evidence", {})
            images = evidence.get("images", [])

            lines.append(f"### 📍 [{date}] {adv.get('name')} 弹窗留存 (`{rid}`)")
            lines.append(f"- **涉事广告主**：{adv.get('name')}（{adv.get('category')} / 主体企业：{adv.get('parent_company', '未知')}）")
            lines.append(f"- **载体宿主 APP**：{host.get('name')} ({host.get('platform', '未知')} {host.get('version', '')})")
            lines.append(f"- **主要表现手法**：{offenses}")
            lines.append(f"- **事发经过记录**：{desc}")
            
            if images:
                img_links = []
                for img in images:
                    if img.startswith("http"):
                        img_links.append(f"[查看网络截图]({img})")
                    else:
                        img_links.append(f"[查看截图凭证]({img})")
                lines.append(f"- **截图凭据**：{' ｜ '.join(img_links)}")
            
            h_alts = r.get("host_alternatives", [])
            if h_alts:
                lines.append(f"- **📲 推荐体面替代软件**：{'、'.join(h_alts)}")

            a_alts = r.get("advertiser_alternatives", [])
            if a_alts:
                lines.append(f"- **🛒 消费替代渠道参考**：{'、'.join(a_alts)}")

            lines.append(f"- **原始数据源**：[`data/records/{r['_file']}`](data/records/{r['_file']})")
            lines.append("")
            lines.append("---")

        lines.append("</details>")
    else:
        lines.append("> *当前暂无案例归档。*")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 💡 纯净替代品推荐库 (支持体面商业与良心软件)")
    lines.append("")
    lines.append("让互联网环境更体面的最有效方式，就是积极支持那些**干净、克制、尊重用户**的产品与渠道：")
    lines.append("")

    lines.append("### 1. 纯净宿主软件替代品（远离高频弹窗困扰）")
    lines.append("")
    if host_alternatives_map:
        for h_name, alts in sorted(host_alternatives_map.items()):
            lines.append(f"- **替代【{h_name}】**：{'、'.join(sorted(alts))}")
    else:
        lines.append("> *暂无推荐替代方案，欢迎提交推荐。*")
    lines.append("")

    lines.append("### 2. 替代消费途径推荐（把预算留给尊重用户的品牌）")
    lines.append("")
    if advertiser_alternatives_map:
        for cat, alts in sorted(advertiser_alternatives_map.items()):
            lines.append(f"- **{cat}品类**：{'、'.join(sorted(alts))}")
    else:
        lines.append("> *暂无消费替代推荐，欢迎提交推荐。*")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🤖 自动化收录流程 (如何提交 Issue 自动生成 PR)")
    lines.append("")
    lines.append("本项目已配置 GitHub Actions 自动化建档机器人：")
    lines.append("")
    lines.append("1. **进入提交页面**：点击访问 [New Issue](../../issues/new?template=report_ad.yml)，选择 **「提交流氓广告/诱导跳转案例」**。")
    lines.append("2. **按模板填写信息**：")
    lines.append("   - **品牌名称**（必填，如拼多多、快手极速版、360借条等）；")
    lines.append("   - **载体宿主 APP**（必填，如酷狗音乐、万年历等）；")
    lines.append("   - **APP 版本号**（推荐填写，如 `12.0.1`，方便精准定责）；")
    lines.append("   - **事发捕获日期**（选填，留空默认为提交当天）；")
    lines.append("   - **勾选典型手法**（多选，如摇一摇、假关闭按钮等）；")
    lines.append("   - **现场截图凭据（核心必须项）**：**在说明框中直接 Ctrl+V / Command+V 粘贴截图**，或拖拽图片上传生成 GitHub 图片链接。**无截图的提交将无法自动生成 PR**。")
    lines.append("3. **机器人自动转换**：")
    lines.append("   - 提交 Issue 后，GitHub Actions 机器人将在 30 秒内自动触发。")
    lines.append("   - 机器人自动解析表单、下载或转录截图、校验数据格式并自动创建对应的 Pull Request。")
    lines.append("4. **合并发布**：")
    lines.append("   - 维护团队核实证据真实性后点击 Merge，系统自动同步更新 README 与在线检索站！")
    lines.append("")
    lines.append("> ⚠️ **仓库管理员配置须知 (如自动 PR 未触发请检查此项)**：  ")
    lines.append("> 新创建的 GitHub 仓库默认限制了机器人创建 PR。请仓库所有者确认开启以下配置：  ")
    lines.append("> 1. 进入仓库 **Settings** -> **Actions** -> **General**；  ")
    lines.append("> 2. 滑到页面下方 **Workflow permissions**；  ")
    lines.append("> 3. 勾选 **「Read and write permissions」**；  ")
    lines.append("> 4. 必须勾选 **「Allow GitHub Actions to create and approve pull requests」** 并保存。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## ⚖️ 客观性与免责声明")
    lines.append("")
    lines.append("1. **事实优先**：所有入库记录必须有真实截屏、录屏或网络公开报道等客观证据支撑，拒绝毫无根据的捏造与恶意中伤。")
    lines.append("2. **就事论事**：记录针对的是「具体的流氓广告投放与诱导行为」，旨在维护消费者的知情权与选择权。")
    lines.append("3. **改过即更新**：若某产品/品牌已全面下架整改此类流氓广告，可提交 Issue 并附上整改证据，项目将在记录中标记「已整改」。")
    lines.append("")
    lines.append("---")
    lines.append("### License")
    lines.append("本项目代码遵循 [MIT License](LICENSE)，数据与文档采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh) 协议共享。")
    lines.append("")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Build or check README.md from YAML records.")
    parser.add_argument("--check", action="store_true", help="Check if README.md is up-to-date without writing.")
    args = parser.parse_args()

    records = load_records()
    print(f"📖 读取到 {len(records)} 条案例记录...")

    new_content = generate_markdown(records)

    if args.check:
        if not README_FILE.exists():
            print("❌ README.md 不存在！")
            sys.exit(1)
        current_content = README_FILE.read_text(encoding="utf-8")
        if current_content != new_content:
            print("❌ README.md 与 data/records/ 数据不同步！请运行 `python scripts/build_readme.py` 更新。")
            sys.exit(1)
        else:
            print("✅ README.md 已经与数据保持最新！")
            sys.exit(0)

    README_FILE.write_text(new_content, encoding="utf-8")
    print(f"🎉 成功更新 {README_FILE}！")

if __name__ == "__main__":
    main()
