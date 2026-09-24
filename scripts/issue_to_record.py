#!/usr/bin/env python3
"""
Convert GitHub Issue Form markdown body into a structured YAML record in data/records/
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("❌ 未安装 PyYAML")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECORDS_DIR = PROJECT_ROOT / "data" / "records"

ALLOWED_OFFENSES = [
    ("摇一摇", "摇一摇跳转"),
    ("扭一扭", "扭一扭/倾斜跳转"),
    ("倾斜", "扭一扭/倾斜跳转"),
    ("开屏", "开屏广告/全屏遮罩"),
    ("全屏遮罩", "开屏广告/全屏遮罩"),
    ("假关闭", "假关闭按钮/像素级诱导"),
    ("诱导", "假关闭按钮/像素级诱导"),
    ("系统通知", "伪装系统通知/红包/短信"),
    ("红包", "伪装系统通知/红包/短信"),
    ("短信", "伪装系统通知/红包/短信"),
    ("自动下载", "自动下载/静默安装"),
    ("静默安装", "自动下载/静默安装"),
    ("无法关闭", "无法关闭/强制倒计时"),
    ("倒计时", "无法关闭/强制倒计时"),
    ("悬浮窗", "应用内悬浮窗/流氓弹窗"),
    ("恐吓", "恐吓欺诈/假冒杀毒清理"),
    ("杀毒", "恐吓欺诈/假冒杀毒清理"),
    ("扣费", "诱导付费/隐蔽扣费")
]

ALLOWED_CATEGORIES = [
    "电商购物", "金融借贷", "网络游戏", "二手车/房产",
    "生活服务", "社交娱乐", "工具清理", "在线教育/培训",
    "医疗健康/保健", "其他"
]

KNOWN_BRANDS = {
    "拼多多": {"parent": "上海寻梦信息技术有限公司", "category": "电商购物", "level": 5},
    "pdd": {"parent": "上海寻梦信息技术有限公司", "category": "电商购物", "level": 5},
    "快手": {"parent": "北京快手科技有限公司", "category": "社交娱乐", "level": 4},
    "快手极速版": {"parent": "北京快手科技有限公司", "category": "社交娱乐", "level": 4},
    "360借条": {"parent": "奇富科技股份有限公司 (原360数科)", "category": "金融借贷", "level": 5},
    "奇富科技": {"parent": "奇富科技股份有限公司", "category": "金融借贷", "level": 5},
    "抖音": {"parent": "北京字节跳动科技有限公司", "category": "社交娱乐", "level": 4},
    "抖音极速版": {"parent": "北京字节跳动科技有限公司", "category": "社交娱乐", "level": 4},
    "今日头条": {"parent": "北京字节跳动科技有限公司", "category": "社交娱乐", "level": 4},
    "得物": {"parent": "上海识装信息科技有限公司", "category": "电商购物", "level": 4},
    "瓜子二手车": {"parent": "车好多旧机动车经纪（北京）有限公司", "category": "二手车/房产", "level": 4},
    "转转": {"parent": "北京转转精神科技有限责任公司", "category": "二手车/房产", "level": 4},
    "淘宝": {"parent": "阿里巴巴（中国）网络技术有限公司", "category": "电商购物", "level": 4},
    "淘特": {"parent": "阿里巴巴（中国）网络技术有限公司", "category": "电商购物", "level": 4},
    "京东": {"parent": "北京京东世纪贸易有限公司", "category": "电商购物", "level": 4},
    "京东金条": {"parent": "京东科技控股股份有限公司", "category": "金融借贷", "level": 5},
    "京东白条": {"parent": "京东科技控股股份有限公司", "category": "金融借贷", "level": 5},
    "度小满": {"parent": "度小满科技（北京）有限公司", "category": "金融借贷", "level": 5},
    "有钱花": {"parent": "度小满科技（北京）有限公司", "category": "金融借贷", "level": 5},
    "美团": {"parent": "北京三快科技有限公司", "category": "生活服务", "level": 3}
}

def parse_issue_markdown(body: str) -> dict:
    """Parse sections delimited by ### Title"""
    sections = {}
    current_key = None
    current_lines = []

    for line in body.splitlines():
        if line.startswith("### "):
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line[4:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections

def clean_val(val: str, default="") -> str:
    if not val:
        return default
    val = val.strip()
    if val in ["_No response_", "无", "暂无", "未知", "none", "None"]:
        return default
    return val

def extract_field(sections: dict, keywords: list, default="") -> str:
    for sec_name, content in sections.items():
        for kw in keywords:
            if kw in sec_name:
                return clean_val(content, default)
    return default

def extract_images(text: str) -> list:
    """Extract all valid screenshot/image URLs from markdown, HTML or raw links"""
    imgs = []
    # Markdown ![alt](url)
    imgs.extend(re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', text))
    # HTML <img ... src="url"
    imgs.extend(re.findall(r'<img[^>]+src=[\"\'](https?://[^\"\']+)[\"\']', text, re.IGNORECASE))
    # Direct image extensions
    imgs.extend(re.findall(r'https?://[^\s\)\"\'>]+?\.(?:png|jpe?g|gif|webp)(?:\?[^\s\)\"\'>]*)?', text, re.IGNORECASE))
    # Direct github user attachments
    imgs.extend(re.findall(r'https?://(?:github\.com/[^\s\)\"\'>]+/assets/|user-images\.githubusercontent\.com/|github-production-user-asset-[^\s\)\"\'>]+)[^\s\)\"\'>]+', text))

    cleaned = []
    for u in imgs:
        u = u.strip().rstrip(').,\"\'>')
        if u and u not in cleaned:
            cleaned.append(u)
    return cleaned

def process_issue(issue_data: dict, issue_number: int):
    body = issue_data.get("body", "") or ""
    sections = parse_issue_markdown(body)

    # 1. Advertiser name
    adv_name = extract_field(sections, ["涉事广告主", "作恶广告主", "品牌名称", "广告主", "品牌"], "")
    if not adv_name:
        match_brand = re.search(r"(?:涉事广告主|品牌名称|广告主|品牌)[：:\s]+([^\n\r]+)", body)
        if match_brand:
            adv_name = match_brand.group(1).strip()
    if not adv_name:
        adv_name = "未知品牌"
    # Clean markdown bold/links
    adv_name = re.sub(r"[*_`]", "", adv_name).strip()

    # 2. Parent company
    parent_company = extract_field(sections, ["母公司", "公司全称", "主体企业"], "")
    parent_company = re.sub(r"[*_`]", "", parent_company).strip()

    # 3. Category
    raw_cat = extract_field(sections, ["品类", "业务品类"], "其他")
    category = "其他"
    for cat in ALLOWED_CATEGORIES:
        if cat in raw_cat:
            category = cat
            break

    # Auto-fill from KNOWN_BRANDS if missing
    for brand_key, brand_info in KNOWN_BRANDS.items():
        if brand_key.lower() in adv_name.lower() or adv_name.lower() in brand_key.lower():
            if not parent_company:
                parent_company = brand_info.get("parent", "")
            if category == "其他":
                category = brand_info.get("category", "其他")
            break

    # 5. Host app, platform & version
    raw_host = extract_field(sections, ["载体宿主", "宿主 APP", "受害宿主"], "")
    if not raw_host:
        match_host = re.search(r"(?:载体宿主|宿主\s*APP|宿主应用|载体应用|宿主)[：:\s]+([^\n\r]+)", body)
        if match_host:
            raw_host = match_host.group(1).strip()
    if not raw_host:
        raw_host = "未知应用"

    host_name = raw_host
    platform = "Android"  # default
    if "ios" in raw_host.lower() or "iphone" in raw_host.lower() or "ipad" in raw_host.lower():
        platform = "iOS"
    elif "harmony" in raw_host.lower() or "鸿蒙" in raw_host:
        platform = "HarmonyOS"
    elif "windows" in raw_host.lower():
        platform = "Windows"
    elif "mac" in raw_host.lower():
        platform = "macOS"

    # Extract version
    raw_version = extract_field(sections, ["版本号", "宿主 APP 版本", "版本", "定责"], "")
    if not raw_version:
        match_ver = re.search(r"[vV]?(\d+\.\d+(?:\.\d+)?)", raw_host)
        if match_ver:
            raw_version = match_ver.group(1)
    if raw_version:
        raw_version = raw_version.lstrip("vV").strip()

    # Clean host name (e.g. "酷狗音乐 (iOS 17.5)" -> "酷狗音乐")
    host_name = re.split(r"[\(（\s]", host_name)[0].strip()
    if not host_name:
        host_name = "未知应用"

    # 6. Offense types
    raw_offenses = extract_field(sections, ["骚扰与流氓手法", "诱导手法", "典型手法", "作恶类型", "流氓手法", "恶劣行为"], "")
    detected_offenses = set()
    for line in raw_offenses.splitlines():
        if "[x]" in line.lower() or "✓" in line:
            for kw, std_name in ALLOWED_OFFENSES:
                if kw in line:
                    detected_offenses.add(std_name)

    # If none detected from checkboxes, scan raw text
    if not detected_offenses:
        for kw, std_name in ALLOWED_OFFENSES:
            if kw in raw_offenses or kw in body:
                detected_offenses.add(std_name)
    if not detected_offenses:
        detected_offenses.add("其他不体面的交互行为")

    # 7. Description
    raw_desc = extract_field(sections, ["现场截图", "事发说明", "事发经过", "恶行简述", "详细恶行描述", "详细描述", "恶行描述", "经历", "简述"], "")
    cleaned_desc = re.sub(r"!\[.*?\]\(.*?\)", "", raw_desc)
    cleaned_desc = re.sub(r"<img[^>]*>", "", cleaned_desc, flags=re.IGNORECASE)
    cleaned_desc = re.sub(r"<[^>]+>", "", cleaned_desc)
    cleaned_desc = re.sub(r"https?://\S+", "", cleaned_desc)
    cleaned_desc = re.sub(r"[\(（]?[请在此处]*直接\s*(?:Ctrl\+V|Command\+V)?\s*粘贴(?:屏幕)?截图[\)）]?", "", cleaned_desc, flags=re.IGNORECASE)
    cleaned_desc = re.sub(r"无图不予收录", "", cleaned_desc)
    cleaned_desc = re.sub(r"\s+", " ", cleaned_desc).strip()

    if len(cleaned_desc) >= 6:
        description = cleaned_desc
    else:
        top_offenses = "、".join(list(detected_offenses)[:2])
        description = f"在 {host_name} 遇到来自 {adv_name} 的流氓广告与诱导跳转，涉及【{top_offenses}】，严重打扰正常使用。"

    # 8. Date extraction
    raw_date = extract_field(sections, ["事发日期", "捕获日期", "事发捕获日期", "日期"], "")
    match_date = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", raw_date)
    if match_date:
        date_str = match_date.group(1)
        date_compact = date_str.replace("-", "")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_compact = datetime.now().strftime("%Y%m%d")

    # 10. Alternatives
    raw_host_alts = extract_field(sections, ["体面替代", "良心替代", "替换该宿主", "替换宿主", "干净软件", "良心替代品", "替代品"], "")
    host_alternatives = [a.strip() for a in re.split(r"[,，、\n]+", raw_host_alts) if a.strip() and a.strip() not in ["_No response_", "无"]]

    raw_adv_alts = extract_field(sections, ["替代品牌", "体面品牌", "替换广告主"], "")
    adv_alternatives = [a.strip() for a in re.split(r"[,，、\n]+", raw_adv_alts) if a.strip() and a.strip() not in ["_No response_", "无"]]

    # Generate strictly ASCII-safe record ID
    COMMON_SLUGS = {
        "拼多多": "pdd", "抖音": "douyin", "快手": "kuaishou", "淘宝": "taobao",
        "淘特": "taote", "京东": "jd", "360": "360", "美团": "meituan",
        "百度": "baidu", "腾讯": "tencent", "酷狗": "kugou", "酷安": "coolapk",
        "瓜子": "guazi", "转转": "zhuanzhuan", "得物": "dewu", "小红书": "xhs",
        "爱奇艺": "iqiyi", "优酷": "youku", "腾讯视频": "vqq", "知乎": "zhihu",
        "微博": "weibo", "贴吧": "tieba", "头条": "toutiao", "度小满": "duxiaoman"
    }
    clean_slug = ""
    brand_lower = adv_name.lower().strip()
    for k, v in COMMON_SLUGS.items():
        if k in brand_lower:
            clean_slug = v
            break
    if not clean_slug:
        ascii_chars = re.sub(r"[^a-zA-Z0-9]+", "", brand_lower)
        if ascii_chars:
            clean_slug = ascii_chars[:12]
        else:
            clean_slug = hashlib.md5(adv_name.encode("utf-8")).hexdigest()[:6]
    record_id = f"{date_compact}-issue{issue_number}-{clean_slug}"

    # 9. Evidence Images (Download and locally archive into screenshots/YYYY/)
    raw_images = extract_images(body)
    all_images = []
    year_str = date_str[:4]
    screenshots_year_dir = PROJECT_ROOT / "screenshots" / year_str
    screenshots_year_dir.mkdir(parents=True, exist_ok=True)

    for idx, img_url in enumerate(raw_images, start=1):
        if img_url.startswith("http://") or img_url.startswith("https://"):
            ext = ".png"
            if ".jpg" in img_url.lower() or ".jpeg" in img_url.lower():
                ext = ".jpg"
            elif ".webp" in img_url.lower():
                ext = ".webp"
            elif ".gif" in img_url.lower():
                ext = ".gif"

            local_filename = f"{record_id}_{idx:02d}{ext}"
            local_rel_path = f"screenshots/{year_str}/{local_filename}"
            local_abs_path = screenshots_year_dir / local_filename

            download_success = False
            try:
                import subprocess
                cmd = [
                    "curl", "-s", "-L", "--max-time", "15",
                    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "-H", "Referer: https://github.com/",
                    img_url, "-o", str(local_abs_path)
                ]
                res = subprocess.run(cmd, capture_output=True, timeout=20)
                if res.returncode == 0 and local_abs_path.exists() and local_abs_path.stat().st_size > 1000:
                    download_success = True
                    print(f"✅ 成功下载截图并本地归档: {local_rel_path} ({local_abs_path.stat().st_size} bytes)")
            except Exception as e:
                print(f"⚠️ 下载截图异常 {img_url}: {e}")

            if download_success:
                all_images.append(local_rel_path)
            else:
                all_images.append(img_url)
        else:
            all_images.append(img_url)

    host_dict = {
        "name": host_name,
        "platform": platform
    }
    if raw_version:
        host_dict["version"] = raw_version

    record = {
        "id": record_id,
        "date": date_str,
        "advertiser": {
            "name": adv_name,
            "category": category
        },
        "host_app": host_dict,
        "offense_type": sorted(list(detected_offenses)),
        "description": description,
        "evidence": {
            "images": all_images,
            "video_url": ""
        }
    }

    if parent_company:
        record["advertiser"]["parent_company"] = parent_company
    if host_alternatives:
        record["host_alternatives"] = host_alternatives
    if adv_alternatives:
        record["advertiser_alternatives"] = adv_alternatives
    record["tags"] = [category] + [o.split("/")[0] for o in record["offense_type"][:2]]

    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RECORDS_DIR / f"{record_id}.yaml"
    with open(out_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, allow_unicode=True, sort_keys=False)

    return out_file, len(all_images) > 0, adv_name, host_name

def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/issue_to_record.py <path_to_github_event.json> 或从 GITHUB_EVENT_PATH 读取")
        sys.exit(1)

    event_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    if not event_path.exists():
        print(f"❌ 找不到事件文件: {event_path}")
        sys.exit(1)

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    issue = event.get("issue")
    if not issue:
        print("❌ 事件中不包含 issue 对象")
        sys.exit(1)

    issue_number = issue.get("number", 0)
    out_path, has_images, brand_name, host_name = process_issue(issue, issue_number)
    print(f"🎉 成功由 Issue #{issue_number} 转化并生成记录文件: {out_path.name} (含截图: {has_images}, 品牌: {brand_name}, 宿主: {host_name})")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"record_file={out_path.name}\n")
            f.write(f"record_id={out_path.stem}\n")
            f.write(f"has_images={'true' if has_images else 'false'}\n")
            f.write(f"brand_name={brand_name}\n")
            f.write(f"host_name={host_name}\n")

if __name__ == "__main__":
    main()
