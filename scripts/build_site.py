#!/usr/bin/env python3
"""
Compile data/records/*.yaml and copy screenshots into docs/ for GitHub Pages
"""

import os
import sys
import json
import shutil
from pathlib import Path
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    print("❌ 错误: 未安装 PyYAML，请运行 pip install pyyaml 安装。")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECORDS_DIR = PROJECT_ROOT / "data" / "records"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_SCREENSHOTS_DIR = DOCS_DIR / "screenshots"
DOCS_DATA_FILE = DOCS_DIR / "data.json"

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

def compile_data(records):
    # Sort descending by date, tie-break with id
    sorted_records = sorted(records, key=lambda x: (str(x.get("date", "")), str(x.get("id", ""))), reverse=True)

    advertisers_map = defaultdict(lambda: {
        "name": "",
        "alias": [],
        "parent_company": "",
        "category": "",
        "count": 0,
        "outrage_count": 0,
        "hosts": set(),
        "offenses": Counter(),
        "alternatives": set(),
        "record_ids": []
    })

    hosts_map = defaultdict(lambda: {
        "name": "",
        "platforms": set(),
        "count": 0,
        "outrage_count": 0,
        "advertisers": set(),
        "offenses": Counter(),
        "alternatives": set(),
        "record_ids": []
    })

    offense_counter = Counter()
    category_counter = Counter()

    for r in sorted_records:
        rid = r.get("id", "")
        adv = r.get("advertiser", {})
        adv_name = adv.get("name", "未知品牌")
        category = adv.get("category", "其他")
        parent = adv.get("parent_company", "")
        alias = adv.get("alias", [])
        outrage = r.get("outrage_count", 0)
        r["outrage_count"] = outrage
        
        host = r.get("host_app", {})
        host_name = host.get("name", "未知APP")
        platform = host.get("platform", "未知")

        offenses = r.get("offense_type", [])
        for off in offenses:
            offense_counter[off] += 1
            advertisers_map[adv_name]["offenses"][off] += 1
            hosts_map[host_name]["offenses"][off] += 1

        category_counter[category] += 1

        # Update advertiser info
        ad_entry = advertisers_map[adv_name]
        ad_entry["name"] = adv_name
        if alias and not ad_entry["alias"]:
            ad_entry["alias"] = alias
        if parent and not ad_entry["parent_company"]:
            ad_entry["parent_company"] = parent
        if not ad_entry["category"]:
            ad_entry["category"] = category
        ad_entry["count"] += 1
        ad_entry["outrage_count"] += outrage
        ad_entry["hosts"].add(host_name)
        ad_entry["record_ids"].append(rid)
        for alt in r.get("advertiser_alternatives", []):
            if alt.strip():
                ad_entry["alternatives"].add(alt.strip())

        # Update host info
        host_entry = hosts_map[host_name]
        host_entry["name"] = host_name
        if platform and platform != "未知":
            host_entry["platforms"].add(platform)
        host_entry["count"] += 1
        host_entry["outrage_count"] += outrage
        host_entry["advertisers"].add(adv_name)
        host_entry["record_ids"].append(rid)
        for alt in r.get("host_alternatives", []):
            if alt.strip():
                host_entry["alternatives"].add(alt.strip())

    # Format advertisers list (rank by outrage_count desc, count desc)
    advertisers_list = []
    for adv_name, info in sorted(advertisers_map.items(), key=lambda x: (-x[1]["outrage_count"], -x[1]["count"], x[0])):
        advertisers_list.append({
            "name": adv_name,
            "alias": info["alias"],
            "parent_company": info["parent_company"],
            "category": info["category"],
            "count": info["count"],
            "outrage_count": info["outrage_count"],
            "hosts": sorted(list(info["hosts"])),
            "offenses": sorted([{"name": k, "count": v} for k, v in info["offenses"].items()], key=lambda x: -x["count"]),
            "alternatives": sorted(list(info["alternatives"])),
            "record_ids": info["record_ids"]
        })

    # Format hosts list
    hosts_list = []
    for host_name, info in sorted(hosts_map.items(), key=lambda x: (-x[1]["count"], x[0])):
        hosts_list.append({
            "name": host_name,
            "platforms": sorted(list(info["platforms"])),
            "count": info["count"],
            "advertisers": sorted(list(info["advertisers"])),
            "offenses": sorted([{"name": k, "count": v} for k, v in info["offenses"].items()], key=lambda x: -x["count"]),
            "alternatives": sorted(list(info["alternatives"])),
            "record_ids": info["record_ids"]
        })

    top_offenses = [{"name": k, "count": v} for k, v in sorted(offense_counter.items(), key=lambda x: (-x[1], x[0]))]
    categories = [{"name": k, "count": v} for k, v in sorted(category_counter.items(), key=lambda x: (-x[1], x[0]))]

    return {
        "stats": {
            "total_records": len(sorted_records),
            "total_advertisers": len(advertisers_list),
            "total_hosts": len(hosts_list),
            "top_offenses": top_offenses,
            "categories": categories
        },
        "records": sorted_records,
        "advertisers": advertisers_list,
        "hosts": hosts_list
    }

def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    records = load_records()
    print(f"📦 读取到 {len(records)} 条案例记录，准备构建静态站...")

    data = compile_data(records)

    # Write data.json
    with open(DOCS_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 生成 {DOCS_DATA_FILE.relative_to(PROJECT_ROOT)}")

    # Copy screenshots to docs/screenshots
    if SCREENSHOTS_DIR.exists():
        if DOCS_SCREENSHOTS_DIR.exists():
            shutil.rmtree(DOCS_SCREENSHOTS_DIR)
        shutil.copytree(SCREENSHOTS_DIR, DOCS_SCREENSHOTS_DIR)
        print(f"✅ 同步截图资源到 {DOCS_SCREENSHOTS_DIR.relative_to(PROJECT_ROOT)}")

    # Inject JSON directly into index.html template placeholder if exists
    template_file = PROJECT_ROOT / "scripts" / "template_index.html"
    if template_file.exists():
        html_content = template_file.read_text(encoding="utf-8")
        compact_json = json.dumps(data, ensure_ascii=False)
        html_content = html_content.replace("__EMBEDDED_DATA_PLACEHOLDER__", compact_json)
        (DOCS_DIR / "index.html").write_text(html_content, encoding="utf-8")
        print(f"✅ 成功编译并内嵌数据至 {DOCS_DIR / 'index.html'}")

    print("🎉 静态站点数据构建完成！")

if __name__ == "__main__":
    main()
