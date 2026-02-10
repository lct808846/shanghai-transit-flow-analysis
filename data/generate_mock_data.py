"""
上海地铁客流模拟数据生成器 — 近两年全量数据
覆盖范围: 2024-03-01 ~ 2026-02-10 (约 712 天)
包含: 季节趋势 / 工作日-周末差异 / 节假日效应 / 天气波动 / 站点热度分级
"""
import csv
import random
import math
import datetime
import os

# ======================= 全局配置 =======================
START_DATE = datetime.date(2024, 3, 1)
END_DATE   = datetime.date(2026, 2, 10)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

# 用户池大小 (刷卡数据)
NUM_USERS = 800

# ======================= 线路与站点 =======================
METRO_NETWORK = {
    "轨道交通1号线": [
        "莘庄", "外环路", "莲花路", "锦江乐园", "上海南站", "漕宝路",
        "上海体育馆", "徐家汇", "衡山路", "常熟路", "陕西南路", "黄陂南路",
        "人民广场", "新闸路", "汉中路", "上海火车站", "中山北路", "延长路",
        "上海马戏城", "汶水路", "彭浦新村",
    ],
    "轨道交通2号线": [
        "徐泾东", "虹桥火车站", "虹桥2号航站楼", "淞虹路", "北新泾",
        "威宁路", "娄山关路", "中山公园", "江苏路", "静安寺", "南京西路",
        "人民广场", "南京东路", "陆家嘴", "东昌路", "世纪大道",
        "上海科技馆", "世纪公园", "龙阳路", "张江高科",
    ],
    "轨道交通10号线": [
        "虹桥火车站", "虹桥1号航站楼", "上海动物园", "龙溪路", "水城路",
        "伊犁路", "宋园路", "虹桥路", "交通大学", "上海图书馆", "陕西南路",
        "新天地", "老西门", "豫园", "南京东路", "天潼路", "四川北路", "海伦路",
    ],
}

# 去重后构建站点表 (保留首次出现的线路归属)
_seen = set()
ALL_STATIONS = []
for line, stations in METRO_NETWORK.items():
    for sta in stations:
        if sta not in _seen:
            _seen.add(sta)
            ALL_STATIONS.append({"name": sta, "line": line})

# 站点热度分级 — 枢纽 / 商圈 / 普通
HUB_STATIONS = {"人民广场", "上海火车站", "虹桥火车站", "徐家汇", "陆家嘴",
                "世纪大道", "南京东路", "南京西路", "静安寺", "中山公园"}
BUSY_STATIONS = {"上海南站", "龙阳路", "张江高科", "莘庄", "陕西南路",
                 "江苏路", "新天地", "豫园", "交通大学", "漕宝路"}

def station_heat(name):
    """返回站点热度系数 (枢纽 1.8, 商圈 1.3, 普通 1.0)"""
    if name in HUB_STATIONS: return 1.8
    if name in BUSY_STATIONS: return 1.3
    return 1.0

# ======================= 节假日 / 特殊日期 =======================
# 主要法定节假日与大型活动 (近似日期, 只标注休假/客流高峰段)
HOLIDAYS = set()
HOLIDAY_BOOST_DAYS = set()   # 假期出行高峰 (客流 × 1.4)

def _add_holiday_range(y, ranges):
    for m, d_start, d_end in ranges:
        for d in range(d_start, d_end + 1):
            try:
                dt = datetime.date(y, m, d)
                HOLIDAYS.add(dt)
                HOLIDAY_BOOST_DAYS.add(dt)
            except ValueError:
                pass

for _y in (2024, 2025, 2026):
    _add_holiday_range(_y, [
        (1, 1, 3),    # 元旦
        (1, 28, 31),  # 春节 (大致)
        (2, 1, 6),    # 春节
        (4, 4, 6),    # 清明
        (5, 1, 5),    # 五一
        (6, 7, 9),    # 端午
        (9, 15, 17),  # 中秋
        (10, 1, 7),   # 国庆
    ])

# ======================= 辅助函数 =======================

def ensure_dir(d):
    os.makedirs(d, exist_ok=True)

def seasonal_factor(dt):
    """
    季节性波动: 夏季 7-8 月客流略降 (0.88), 冬季 12-1 月略降 (0.92),
    春秋季正常 (1.0), 用 sin 做平滑过渡
    """
    doy = dt.timetuple().tm_yday
    # 简单正弦模型: 峰值在 4 月和 10 月
    return 1.0 + 0.08 * math.sin(2 * math.pi * (doy - 100) / 365)

def trend_factor(dt):
    """长期增长趋势: 从 2024-03 到 2026-02 客流平均增长 ~12%"""
    days_since_start = (dt - START_DATE).days
    total_days = (END_DATE - START_DATE).days
    return 1.0 + 0.12 * (days_since_start / total_days)

def day_type_factor(dt):
    """工作日 vs 周末 vs 节假日"""
    if dt in HOLIDAYS:
        return 1.35  # 节假日景区/商圈客流上升
    wd = dt.weekday()
    if wd >= 5:
        return 0.72  # 周末整体略低
    return 1.0

def weather_jitter():
    """随机天气扰动 (极端天气降低 10-20%)"""
    r = random.random()
    if r < 0.03:   # ~3% 暴雨/台风天
        return random.uniform(0.65, 0.80)
    if r < 0.08:   # ~5% 小雨
        return random.uniform(0.88, 0.95)
    return 1.0

def hour_profile(hour, is_workday):
    """
    返回 (进站系数, 出站系数) — 工作日双峰, 周末/假日单峰
    """
    if is_workday:
        profiles = {
            5:  (0.08, 0.03), 6:  (0.25, 0.08), 7:  (0.80, 0.15),
            8:  (1.00, 0.20), 9:  (0.65, 0.30), 10: (0.30, 0.35),
            11: (0.25, 0.38), 12: (0.30, 0.35), 13: (0.28, 0.30),
            14: (0.25, 0.28), 15: (0.28, 0.32), 16: (0.35, 0.55),
            17: (0.50, 0.85), 18: (0.30, 1.00), 19: (0.18, 0.65),
            20: (0.12, 0.35), 21: (0.08, 0.20), 22: (0.05, 0.12),
            23: (0.02, 0.06),
        }
    else:
        profiles = {
            5:  (0.02, 0.01), 6:  (0.05, 0.02), 7:  (0.12, 0.05),
            8:  (0.22, 0.10), 9:  (0.40, 0.20), 10: (0.60, 0.35),
            11: (0.65, 0.45), 12: (0.55, 0.50), 13: (0.50, 0.48),
            14: (0.55, 0.50), 15: (0.58, 0.55), 16: (0.50, 0.55),
            17: (0.42, 0.60), 18: (0.30, 0.65), 19: (0.20, 0.55),
            20: (0.15, 0.40), 21: (0.10, 0.28), 22: (0.06, 0.15),
            23: (0.03, 0.08),
        }
    return profiles.get(hour, (0.05, 0.05))


# ======================= 站点客流数据生成 =======================

def generate_station_flow_data():
    """
    生成按 (日期, 小时, 站点) 聚合的客流数据
    列: transactiondate, incount, staname, linename, outcount
    兼容上传 API 的 station_flow 类型
    """
    filename = os.path.join(OUTPUT_DIR, "mock_station_flow.csv")
    print(f"[station_flow] 正在生成 → {filename}")

    total_days = (END_DATE - START_DATE).days + 1
    row_count = 0

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["transactiondate", "incount", "staname", "linename", "outcount"])

        for day_offset in range(total_days):
            dt = START_DATE + datetime.timedelta(days=day_offset)
            is_workday = dt.weekday() < 5 and dt not in HOLIDAYS

            s_factor = seasonal_factor(dt)
            t_factor = trend_factor(dt)
            d_factor = day_type_factor(dt)
            w_jitter = weather_jitter()

            day_multiplier = s_factor * t_factor * d_factor * w_jitter

            for hour in range(5, 24):
                in_coeff, out_coeff = hour_profile(hour, is_workday)

                for info in ALL_STATIONS:
                    heat = station_heat(info["name"])
                    # 基准客流: 枢纽站高峰可达 400+, 普通站平峰 <30
                    base_in  = 220 * in_coeff  * heat * day_multiplier
                    base_out = 220 * out_coeff * heat * day_multiplier

                    # 加随机噪声 ±25%
                    incount  = max(0, int(base_in  * random.uniform(0.75, 1.25)))
                    outcount = max(0, int(base_out * random.uniform(0.75, 1.25)))

                    time_str = f"{dt} {hour:02d}"
                    writer.writerow([time_str, incount, info["name"], info["line"], outcount])
                    row_count += 1

            if (day_offset + 1) % 60 == 0:
                print(f"  ... {day_offset + 1}/{total_days} 天完成 ({row_count:,} 行)")

    print(f"[station_flow] 完成! 共 {row_count:,} 行")


# ======================= 刷卡记录数据生成 =======================

def generate_raw_swipe_data():
    """
    生成模拟刷卡记录 (用于 OD 分析)
    列: card_id, swipe_time, station_name, line_name, swipe_type
    """
    filename = os.path.join(OUTPUT_DIR, "mock_swipe_records.csv")
    print(f"[swipe_records] 正在生成 → {filename}")

    total_days = (END_DATE - START_DATE).days + 1
    card_pool = [f"CARD_{i:06d}" for i in range(NUM_USERS)]

    # 为每位用户分配固定的"通勤 OD" — 模拟真实通勤习惯
    user_profiles = {}
    for card in card_pool:
        home_station = random.choice(ALL_STATIONS)
        work_station = random.choice(ALL_STATIONS)
        while work_station["name"] == home_station["name"]:
            work_station = random.choice(ALL_STATIONS)
        user_profiles[card] = {
            "home": home_station,
            "work": work_station,
            "commute_prob": random.uniform(0.70, 0.95),   # 工作日通勤概率
            "leisure_prob": random.uniform(0.20, 0.55),    # 周末出行概率
            "morning_hour": random.choices(range(7, 10), weights=[30, 50, 20])[0],
            "evening_hour": random.choices(range(17, 20), weights=[20, 50, 30])[0],
        }

    row_count = 0

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["card_id", "swipe_time", "station_name", "line_name", "swipe_type"])

        for day_offset in range(total_days):
            dt = START_DATE + datetime.timedelta(days=day_offset)
            is_workday = dt.weekday() < 5 and dt not in HOLIDAYS
            day_rows = []

            for card in card_pool:
                prof = user_profiles[card]
                trips = []

                if is_workday:
                    # 通勤
                    if random.random() < prof["commute_prob"]:
                        # 早高峰: 家 → 单位
                        h = prof["morning_hour"]
                        m = random.randint(0, 59)
                        dur = random.randint(20, 75)
                        trips.append((h, m, dur, prof["home"], prof["work"]))

                        # 晚高峰: 单位 → 家
                        h2 = prof["evening_hour"]
                        m2 = random.randint(0, 59)
                        dur2 = random.randint(20, 75)
                        trips.append((h2, m2, dur2, prof["work"], prof["home"]))

                    # 额外随机出行 (~8% 概率)
                    if random.random() < 0.08:
                        h = random.randint(10, 16)
                        m = random.randint(0, 59)
                        dur = random.randint(15, 60)
                        s1 = random.choice(ALL_STATIONS)
                        s2 = random.choice(ALL_STATIONS)
                        while s2["name"] == s1["name"]:
                            s2 = random.choice(ALL_STATIONS)
                        trips.append((h, m, dur, s1, s2))
                else:
                    # 周末/假期: 随机出行
                    if random.random() < prof["leisure_prob"]:
                        num_trips = random.choices([1, 2, 3], weights=[50, 40, 10])[0]
                        used_hours = set()
                        for _ in range(num_trips):
                            h = random.randint(8, 20)
                            while h in used_hours:
                                h = random.randint(8, 20)
                            used_hours.add(h)
                            m = random.randint(0, 59)
                            dur = random.randint(15, 90)
                            s1 = random.choice(ALL_STATIONS)
                            s2 = random.choice(ALL_STATIONS)
                            while s2["name"] == s1["name"]:
                                s2 = random.choice(ALL_STATIONS)
                            trips.append((h, m, dur, s1, s2))

                for (h, m, dur, origin, dest) in trips:
                    enter_time = datetime.datetime.combine(dt, datetime.time(h, m, random.randint(0, 59)))
                    exit_time = enter_time + datetime.timedelta(minutes=dur)

                    day_rows.append([
                        card, enter_time.strftime("%Y-%m-%d %H:%M:%S"),
                        origin["name"], origin["line"], "in"
                    ])
                    day_rows.append([
                        card, exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                        dest["name"], dest["line"], "out"
                    ])

            # 按 card_id + swipe_time 排序后写入 (保证 OD 配对正确)
            day_rows.sort(key=lambda r: (r[0], r[1]))
            writer.writerows(day_rows)
            row_count += len(day_rows)

            if (day_offset + 1) % 60 == 0:
                print(f"  ... {day_offset + 1}/{total_days} 天完成 ({row_count:,} 行)")

    print(f"[swipe_records] 完成! 共 {row_count:,} 行")


# ======================= 主入口 =======================
if __name__ == "__main__":
    ensure_dir(OUTPUT_DIR)
    print(f"=== 上海地铁模拟数据生成器 ===")
    print(f"时间范围: {START_DATE} ~ {END_DATE}")
    print(f"站点数: {len(ALL_STATIONS)}, 用户数: {NUM_USERS}")
    print()
    generate_station_flow_data()
    print()
    generate_raw_swipe_data()
    print()
    print("=== 全部完成 ===")
