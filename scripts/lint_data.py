#!/usr/bin/env python3
"""
Lint and validate ad offense records in data/records/*.yaml
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("❌ 错误: 未安装 PyYAML，请运行 pip install pyyaml 安装。")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECORDS_DIR = PROJECT_ROOT / "data" / "records"

ALLOWED_PLATFORMS = {"iOS", "Android", "HarmonyOS", "Windows", "macOS", "Web", "Cross-Platform"}

ALLOWED_OFFENSE_TYPES = {
    "摇一摇跳转",
    "扭一扭/倾斜跳转",
    "开屏广告/全屏遮罩",
    "假关闭按钮/像素级诱导",
    "伪装系统通知/红包/短信",
    "自动下载/静默安装",
    "无法关闭/强制倒计时",
    "应用内悬浮窗/流氓弹窗",
    "恐吓欺诈/假冒杀毒清理",
    "诱导付费/隐蔽扣费",
    "其他不体面的交互行为",
    "其他恶劣行为"
}

ALLOWED_CATEGORIES = {
    "电商购物",
    "金融借贷",
    "网络游戏",
    "二手车/房产",
    "生活服务",
    "社交娱乐",
    "工具清理",
    "在线教育/培训",
    "医疗健康/保健",
    "其他"
}

def validate_record(file_path: Path) -> list[str]:
    errors = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [f"YAML 解析失败: {e}"]

    if not isinstance(data, dict):
        return ["根节点必须是 YAML 对象 (Dictionary)"]

    # 1. Check ID and filename match
    record_id = data.get("id")
    if not record_id or not isinstance(record_id, str):
        errors.append("缺少必须的字符串字段: 'id'")
    else:
        if not re.match(r"^[\w-]+$", record_id):
            errors.append(f"字段 'id' ({record_id}) 仅支持字母、汉字、数字、下划线和连字符")
        if file_path.stem != record_id:
            errors.append(f"文件名 ({file_path.name}) 与 record id ({record_id}.yaml) 不匹配")

    # 2. Check Date
    date_val = data.get("date")
    if not date_val:
        errors.append("缺少必须字段: 'date' (格式 YYYY-MM-DD)")
    else:
        # If pyyaml parsed it as datetime.date, convert to str
        date_str = str(date_val).strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            errors.append(f"日期格式错误: '{date_val}'，应为 YYYY-MM-DD")

    # 3. Check Advertiser
    adv = data.get("advertiser")
    if not adv or not isinstance(adv, dict):
        errors.append("缺少或非法字段: 'advertiser'")
    else:
        name = adv.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            errors.append("缺少必须字段: 'advertiser.name'")
        
        category = adv.get("category")
        if not category:
            errors.append("缺少必须字段: 'advertiser.category'")
        elif category not in ALLOWED_CATEGORIES:
            errors.append(f"未知的广告品类: '{category}'，可选值: {', '.join(sorted(ALLOWED_CATEGORIES))}")

        boycott_level = adv.get("boycott_level")
        if boycott_level is not None and (not isinstance(boycott_level, int) or not (1 <= boycott_level <= 5)):
            errors.append(f"'advertiser.boycott_level' 若存在必须是 1 到 5 之间的整数，当前为: {boycott_level}")

    # 4. Check Host App
    host = data.get("host_app")
    if not host or not isinstance(host, dict):
        errors.append("缺少或非法字段: 'host_app'")
    else:
        if not host.get("name"):
            errors.append("缺少必须字段: 'host_app.name'")
        platform = host.get("platform")
        if not platform:
            errors.append("缺少必须字段: 'host_app.platform'")
        elif platform not in ALLOWED_PLATFORMS:
            errors.append(f"未知的平台: '{platform}'，可选值: {', '.join(sorted(ALLOWED_PLATFORMS))}")

    # 5. Check Offense Types
    offenses = data.get("offense_type")
    if not offenses or not isinstance(offenses, list):
        errors.append("缺少必须列表字段: 'offense_type' (至少包含一项)")
    else:
        for item in offenses:
            if item not in ALLOWED_OFFENSE_TYPES:
                errors.append(f"未知的交互手段类型: '{item}'，可选值: {', '.join(sorted(ALLOWED_OFFENSE_TYPES))}")

    # 6. Check Description
    desc = data.get("description")
    if not desc or not isinstance(desc, str) or len(desc.strip()) < 10:
        errors.append("字段 'description' 必须至少包含 10 个字的详细客观描述")
    elif re.search(r"<[^>]+>", desc):
        errors.append(f"字段 'description' 不能包含原生 HTML 标签代码，请使用纯文本客观记录: '{desc[:30]}...'")

    # 7. Check Alternatives (Optional)
    for alt_field in ["host_alternatives", "advertiser_alternatives", "suggested_alternatives"]:
        if alt_field in data and not isinstance(data[alt_field], list):
            errors.append(f"字段 '{alt_field}' 若存在必须为列表")

    # Optional outrage_count (怒斥计数)
    if "outrage_count" in data:
        cnt = data["outrage_count"]
        if not isinstance(cnt, int) or cnt < 0:
            errors.append(f"字段 'outrage_count' 必须为非负整数，当前为: {cnt}")

    # 8. Check Evidence (Mandatory Evidence)
    evidence = data.get("evidence")
    if not evidence or not isinstance(evidence, dict):
        errors.append("缺少必须字段: 'evidence' (留存凭据)")
    else:
        images = evidence.get("images", [])
        if not images or not isinstance(images, list) or len(images) == 0:
            errors.append("缺少必要截图: 'evidence.images' 必须至少包含 1 张现场截图作为客观留存凭据！")
        else:
            for img in images:
                if isinstance(img, str) and not (img.startswith("http://") or img.startswith("https://")):
                    local_path = PROJECT_ROOT / img
                    if not local_path.exists():
                        errors.append(f"证据截图文件不存在: '{img}'")

    return errors

def main():
    if not RECORDS_DIR.exists():
        print(f"❌ 目录不存在: {RECORDS_DIR}")
        sys.exit(1)

    record_files = sorted(list(RECORDS_DIR.glob("*.yaml")) + list(RECORDS_DIR.glob("*.yml")))
    if not record_files:
        print(f"ℹ️ 在 {RECORDS_DIR} 中暂无案例记录文件（等待社区提报入库）。")
        sys.exit(0)

    total_errors = 0
    print(f"🔍 开始校验 {len(record_files)} 条案例记录...\n")

    for file_path in record_files:
        rel_path = file_path.relative_to(PROJECT_ROOT)
        errors = validate_record(file_path)
        if errors:
            print(f"❌ [{rel_path}] 存在校验错误:")
            for err in errors:
                print(f"   - {err}")
            total_errors += len(errors)
        else:
            print(f"✅ [{rel_path}] 格式正确")

    print("\n" + "="*50)
    if total_errors > 0:
        print(f"❌ 校验失败: 发现 {total_errors} 处错误，请修改后重试。")
        sys.exit(1)
    else:
        print("🎉 全部记录格式校验通过！")
        sys.exit(0)

if __name__ == "__main__":
    main()
