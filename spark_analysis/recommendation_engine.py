"""
智能出行推荐引擎
用户输入起点站、终点站、出行时间，系统基于客流数据生成个性化出行建议

推荐算法:
1. 最优时段推荐 — Z-Score 异常检测: 对 OD 各时段客流做标准化，识别异常高峰，推荐低于均值的时段
2. 起点站拥挤分析 — 时序对比: 所选时段 vs 全天均值/标准差，量化拥挤程度并给出前后时段对比
3. 终点站拥挤分析 — 同上，针对到达站
4. 替代路线推荐 — 余弦相似度: 构建站点客流向量，找与目的站最相似但更空闲的替代站点
"""
import os
import sys
import math
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transit_system.settings')

import django
django.setup()

from django.db.models import Sum, Avg, Count, F, Q
from analysis.models import (
    BusStation, OdFlow, StationFlowStats, Recommendation
)


# ==================== 算法工具函数 ====================

def z_score_analysis(values):
    """
    Z-Score 标准化分析
    返回每个值的 z-score，用于识别异常高/低时段
    z = (x - μ) / σ
    """
    arr = np.array(values, dtype=float)
    mean = np.mean(arr)
    std = np.std(arr)
    if std == 0:
        return np.zeros_like(arr), float(mean), float(std)
    z_scores = (arr - mean) / std
    return z_scores, float(mean), float(std)


def cosine_similarity(vec_a, vec_b):
    """
    余弦相似度
    sim(A, B) = (A · B) / (||A|| × ||B||)
    """
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def weighted_score(factors):
    """
    加权评分模型
    factors: list of (value, weight) — value ∈ [0,1], weight ∈ R+
    score = Σ(value_i × weight_i) / Σ(weight_i)
    """
    total_w = sum(w for _, w in factors)
    if total_w == 0:
        return 0.0
    return sum(v * w for v, w in factors) / total_w


def _get_analysis_date():
    """获取最新的有数据日期"""
    return StationFlowStats.objects.order_by('-date').values_list('date', flat=True).first()


# ==================== 推荐策略 ====================

def recommend_best_time(origin_id, dest_id, travel_hour, analysis_date):
    """
    策略1: 最优时段推荐 (Z-Score 异常检测)

    算法流程:
    1. 查询该 OD 对全天各时段客流量
    2. 对客流序列做 Z-Score 标准化
    3. Z > 1.0 的时段标记为「高峰」(红色)
    4. Z < -0.5 的时段标记为「推荐」(绿色)
    5. 用户所选时段如果 Z > 0.5，建议调整
    """
    hourly_qs = (
        OdFlow.objects.filter(
            origin_station_id=origin_id,
            destination_station_id=dest_id,
            date=analysis_date,
        )
        .values('hour')
        .annotate(flow=Sum('flow_count'))
        .order_by('hour')
    )
    hourly = list(hourly_qs)
    if not hourly:
        return None

    hours = [h['hour'] for h in hourly]
    flows = [h['flow'] for h in hourly]
    z_scores, mean_flow, std_flow = z_score_analysis(flows)

    # 找用户所选时段
    user_idx = None
    user_flow = 0
    user_z = 0.0
    for i, h in enumerate(hours):
        if h == travel_hour:
            user_idx = i
            user_flow = flows[i]
            user_z = float(z_scores[i])
            break

    # 找最优时段 (z最低) 和最差时段 (z最高)
    best_idx = int(np.argmin(z_scores))
    worst_idx = int(np.argmax(z_scores))

    # 推荐时段: z < -0.3 的
    recommended_hours = [hours[i] for i in range(len(hours)) if z_scores[i] < -0.3]
    peak_hours = [hours[i] for i in range(len(hours)) if z_scores[i] > 0.8]

    # 判断用户选的时段好不好
    if user_z > 0.8:
        level = '高峰'
        advice = f'您选择的 {travel_hour}:00 客流量 {user_flow} 人次，处于高峰时段（Z={user_z:.1f}）。'
    elif user_z > 0.3:
        level = '偏高'
        advice = f'您选择的 {travel_hour}:00 客流量 {user_flow} 人次，略高于平均水平（Z={user_z:.1f}）。'
    elif user_z < -0.3:
        level = '推荐'
        advice = f'您选择的 {travel_hour}:00 客流量 {user_flow} 人次，低于平均水平（Z={user_z:.1f}），是不错的选择！'
    else:
        level = '正常'
        advice = f'您选择的 {travel_hour}:00 客流量 {user_flow} 人次，处于正常水平（Z={user_z:.1f}）。'

    if recommended_hours and level in ('高峰', '偏高'):
        rec_str = ', '.join(f'{h}:00' for h in sorted(recommended_hours)[:3])
        advice += f' 建议改为 {rec_str} 出行，客流更少。'

    origin_name = BusStation.objects.filter(pk=origin_id).values_list('station_name', flat=True).first() or origin_id
    dest_name = BusStation.objects.filter(pk=dest_id).values_list('station_name', flat=True).first() or dest_id

    # 出行适宜度评分: 越适合出行分数越高
    score = weighted_score([
        (max(0, min(1.0, 0.5 - user_z * 0.25)), 0.6),  # Z越低(越空闲)→分越高
        (1 - min(1.0, std_flow / max(mean_flow, 1)), 0.2),  # 波动小→更稳定→分越高
        (0.8 if level in ('推荐', '正常') else 0.3, 0.2),  # 当前时段已是低峰→分更高
    ])

    return {
        'rec_type': 'time',
        'title': f'⏰ {origin_name} → {dest_name} 时段分析',
        'description': advice,
        'score': round(max(0.05, min(0.98, score)), 2),
        'metadata': {
            'origin': origin_name,
            'destination': dest_name,
            'hourly_flow': {h: f for h, f in zip(hours, flows)},
            'z_scores': {h: round(float(z), 2) for h, z in zip(hours, z_scores)},
            'mean_flow': round(mean_flow, 1),
            'std_flow': round(std_flow, 1),
            'user_hour': travel_hour,
            'user_flow': user_flow,
            'user_z': round(user_z, 2),
            'user_level': level,
            'best_hour': hours[best_idx],
            'worst_hour': hours[worst_idx],
            'recommended_hours': sorted(recommended_hours)[:4],
            'peak_hours': sorted(peak_hours),
            'algorithm': 'Z-Score 异常检测',
        },
    }


def analyze_station_congestion(station_id, travel_hour, analysis_date, role='origin'):
    """
    策略2/3: 站点拥挤度分析 (时序对比 + Z-Score)

    算法流程:
    1. 查询该站全天各时段客流
    2. Z-Score 识别异常拥挤时段
    3. 计算所选时段的拥挤百分位 (在全天中排第几)
    4. 与前后 ±2 小时对比，给出最优窗口
    """
    hourly_qs = (
        StationFlowStats.objects.filter(station_id=station_id, date=analysis_date)
        .values('hour', 'total_flow', 'in_flow', 'out_flow', 'congestion_level')
        .order_by('hour')
    )
    records = list(hourly_qs)
    if not records:
        return None

    station_name = BusStation.objects.filter(pk=station_id).values_list('station_name', flat=True).first() or station_id
    role_label = '出发站' if role == 'origin' else '到达站'

    hours = [r['hour'] for r in records]
    flows = [r['total_flow'] for r in records]
    z_scores, mean_flow, std_flow = z_score_analysis(flows)

    # 找到用户所选时段数据
    user_record = None
    user_z = 0.0
    user_flow = 0
    for i, r in enumerate(records):
        if r['hour'] == travel_hour:
            user_record = r
            user_z = float(z_scores[i])
            user_flow = r['total_flow']
            break

    if not user_record:
        # 该时段无数据，取最近的
        user_flow = 0
        congestion = 'unknown'
    else:
        congestion = user_record['congestion_level']

    # 百分位排名: 该时段在全天中排第几
    sorted_flows = sorted(flows)
    percentile = (sorted_flows.index(user_flow) + 1) / len(sorted_flows) * 100 if user_flow in sorted_flows else 50

    # 前后 ±2 小时窗口对比
    nearby = {}
    for i, r in enumerate(records):
        if abs(r['hour'] - travel_hour) <= 2:
            nearby[r['hour']] = {
                'flow': r['total_flow'],
                'z': round(float(z_scores[i]), 2),
                'level': r['congestion_level'],
            }

    # 推荐最佳窗口
    best_nearby_hour = min(nearby.keys(), key=lambda h: nearby[h]['flow']) if nearby else travel_hour

    # 拥挤度文字
    if congestion == 'high':
        desc = f'{station_name}（{role_label}）在 {travel_hour}:00 客流 {user_flow} 人次，拥挤度【高】（Z={user_z:.1f}，超过全天 {percentile:.0f}% 的时段）。'
    elif congestion == 'medium':
        desc = f'{station_name}（{role_label}）在 {travel_hour}:00 客流 {user_flow} 人次，拥挤度【中等】（Z={user_z:.1f}，超过全天 {percentile:.0f}% 的时段）。'
    else:
        desc = f'{station_name}（{role_label}）在 {travel_hour}:00 客流 {user_flow} 人次，拥挤度【低】（Z={user_z:.1f}），出行较为舒适。'

    if best_nearby_hour != travel_hour and nearby.get(best_nearby_hour, {}).get('flow', 999999) < user_flow:
        desc += f' 附近时段 {best_nearby_hour}:00 客流仅 {nearby[best_nearby_hour]["flow"]} 人次，可考虑调整。'

    icon = '🚉' if role == 'origin' else '🏁'
    # 出行适宜度评分: 越不拥挤分数越高
    score = weighted_score([
        (max(0, min(1.0, 0.5 - user_z * 0.25)), 0.5),  # Z越低→越空闲→分越高
        (1 - percentile / 100.0, 0.3),  # 百分位越低(越不挤)→分越高
        (1.0 if congestion == 'low' else 0.5 if congestion == 'medium' else 0.15, 0.2),
    ])

    return {
        'rec_type': 'avoid',
        'title': f'{icon} {role_label} {station_name} 拥挤分析',
        'description': desc,
        'score': round(max(0.05, min(0.98, score)), 2),
        'metadata': {
            'station': station_name,
            'station_id': station_id,
            'role': role_label,
            'hourly_flow': {h: f for h, f in zip(hours, flows)},
            'z_scores': {h: round(float(z), 2) for h, z in zip(hours, z_scores)},
            'user_hour': travel_hour,
            'user_flow': user_flow,
            'user_z': round(user_z, 2),
            'congestion_level': congestion,
            'percentile': round(percentile, 1),
            'nearby_hours': nearby,
            'best_nearby_hour': best_nearby_hour,
            'mean_flow': round(mean_flow, 1),
            'suggested_hours': [h for h in hours if z_scores[hours.index(h)] < -0.3][:4],
            'congested_hours': [h for h in hours if z_scores[hours.index(h)] > 0.8],
            'algorithm': 'Z-Score + 百分位排名',
        },
    }


def recommend_alternative_routes(origin_id, dest_id, travel_hour, analysis_date):
    """
    策略4: 替代路线推荐 (余弦相似度)

    算法流程:
    1. 构建目的站的客流特征向量 V_dest = [hour_6_flow, hour_7_flow, ..., hour_22_flow]
    2. 构建所有其他站的客流特征向量
    3. 用余弦相似度 sim(V_dest, V_other) 找功能相似的站
    4. 在相似站中筛选出当前时段更空闲的站点作为替代
    5. 同时检查替代 OD 是否存在客流数据
    """
    # 目的站全天客流向量
    dest_hourly = dict(
        StationFlowStats.objects.filter(station_id=dest_id, date=analysis_date)
        .values_list('hour', 'total_flow')
    )
    if not dest_hourly:
        return None

    all_hours = sorted(dest_hourly.keys())
    dest_vector = [dest_hourly.get(h, 0) for h in all_hours]
    dest_flow_at_hour = dest_hourly.get(travel_hour, 0)

    dest_name = BusStation.objects.filter(pk=dest_id).values_list('station_name', flat=True).first() or dest_id
    origin_name = BusStation.objects.filter(pk=origin_id).values_list('station_name', flat=True).first() or origin_id

    # 获取所有站点在同一天的客流 (排除起点和终点)
    all_station_flows = (
        StationFlowStats.objects.filter(date=analysis_date)
        .exclude(station_id__in=[origin_id, dest_id])
        .values('station_id', 'station__station_name', 'hour', 'total_flow')
    )

    # 按站点分组构建向量
    station_vectors = defaultdict(lambda: {'name': '', 'flows': {}})
    for sf in all_station_flows:
        sid = sf['station_id']
        station_vectors[sid]['name'] = sf['station__station_name']
        station_vectors[sid]['flows'][sf['hour']] = sf['total_flow']

    # 计算余弦相似度并筛选
    candidates = []
    for sid, info in station_vectors.items():
        vec = [info['flows'].get(h, 0) for h in all_hours]
        sim = cosine_similarity(dest_vector, vec)

        alt_flow_at_hour = info['flows'].get(travel_hour, 0)

        # 只要相似度 > 0.7 且当前时段更空闲的
        if sim > 0.7 and alt_flow_at_hour < dest_flow_at_hour:
            # 检查从 origin 到这个替代站是否有 OD 数据
            od_flow = OdFlow.objects.filter(
                origin_station_id=origin_id,
                destination_station_id=sid,
                date=analysis_date,
                hour=travel_hour,
            ).aggregate(total=Sum('flow_count'))['total'] or 0

            savings = round((1 - alt_flow_at_hour / max(dest_flow_at_hour, 1)) * 100, 1)

            candidates.append({
                'station_id': sid,
                'station_name': info['name'],
                'similarity': round(sim, 3),
                'flow_at_hour': alt_flow_at_hour,
                'od_flow': od_flow,
                'savings': savings,
            })

    # 按相似度×节省率综合排序
    candidates.sort(key=lambda x: x['similarity'] * (x['savings'] / 100), reverse=True)
    top_alts = candidates[:3]

    if not top_alts:
        return None

    alt_desc_parts = []
    for alt in top_alts:
        alt_desc_parts.append(
            f'{alt["station_name"]}（相似度 {alt["similarity"]:.0%}，'
            f'{travel_hour}:00 客流 {alt["flow_at_hour"]} 人次，减少 {alt["savings"]}%）'
        )

    desc = (
        f'{dest_name} 在 {travel_hour}:00 客流 {dest_flow_at_hour} 人次。'
        f'基于余弦相似度算法，为您找到以下功能相似但更空闲的替代站点：\n'
        + '；'.join(alt_desc_parts) + '。'
    )

    # 替代方案质量评分: 替代越优质分数越高
    score = weighted_score([
        (min(1.0, top_alts[0]['savings'] / 50), 0.4),  # 节省比例越高→方案越好
        (top_alts[0]['similarity'], 0.4),  # 相似度越高→替代越可行
        (min(1.0, len(top_alts) / 3), 0.2),  # 可选方案越多越好
    ])

    return {
        'rec_type': 'route',
        'title': f'🔄 替代目的站推荐',
        'description': desc,
        'score': round(max(0.05, min(0.95, 0.2 + score * 0.6)), 2),
        'metadata': {
            'origin': origin_name,
            'destination': dest_name,
            'dest_flow_at_hour': dest_flow_at_hour,
            'travel_hour': travel_hour,
            'alternatives': top_alts,
            'algorithm': '余弦相似度 + 加权评分',
        },
    }


# ==================== 主入口 ====================

def generate_od_recommendations(origin_id, dest_id, travel_hour, analysis_date=None):
    """
    根据用户选择的 起点、终点、出行时段 生成出行推荐（实时计算，不写库）

    使用的算法:
    - Z-Score 异常检测 (时段推荐、拥挤分析)
    - 余弦相似度 (替代路线)
    - 加权评分模型 (推荐优先级排序)
    """
    if not analysis_date:
        analysis_date = _get_analysis_date()
    if not analysis_date:
        return []

    results = []

    # 策略1: 最优时段推荐
    rec = recommend_best_time(origin_id, dest_id, travel_hour, analysis_date)
    if rec:
        results.append(rec)

    # 策略2: 起点站拥挤分析
    rec = analyze_station_congestion(origin_id, travel_hour, analysis_date, role='origin')
    if rec:
        results.append(rec)

    # 策略3: 终点站拥挤分析
    rec = analyze_station_congestion(dest_id, travel_hour, analysis_date, role='destination')
    if rec:
        results.append(rec)

    # 策略4: 替代路线推荐
    rec = recommend_alternative_routes(origin_id, dest_id, travel_hour, analysis_date)
    if rec:
        results.append(rec)

    # 按 score 排序
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def import_travel_history_from_od():
    """从 OD 数据中提取出行历史（模拟）"""
    import pandas as pd
    from analysis.models import UserTravelHistory

    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'mock_swipe_records.csv')
    if not os.path.exists(csv_path):
        print("未找到刷卡数据文件")
        return

    df = pd.read_csv(csv_path)
    df['swipe_time'] = pd.to_datetime(df['swipe_time'])
    df.sort_values(by=['card_id', 'swipe_time'], inplace=True)

    df['next_card'] = df['card_id'].shift(-1)
    df['next_swipe_type'] = df['swipe_type'].shift(-1)
    df['next_station'] = df['station_name'].shift(-1)
    df['next_time'] = df['swipe_time'].shift(-1)

    trips = df[(df['card_id'] == df['next_card']) &
               (df['swipe_type'] == 'in') &
               (df['next_swipe_type'] == 'out')].copy()

    trips['duration_min'] = (trips['next_time'] - trips['swipe_time']).dt.total_seconds() / 60

    UserTravelHistory.objects.all().delete()
    objects = []
    for _, row in trips.iterrows():
        objects.append(UserTravelHistory(
            user_id=row['card_id'],
            origin_station_id=row['station_name'],
            destination_station_id=row['next_station'],
            travel_date=row['swipe_time'].date(),
            travel_hour=row['swipe_time'].hour,
            duration_min=row['duration_min'],
        ))

    batch_size = 500
    for i in range(0, len(objects), batch_size):
        UserTravelHistory.objects.bulk_create(objects[i:i + batch_size])

    print(f"已导入 {len(objects)} 条出行历史记录")
    return len(objects)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='智能出行推荐引擎')
    parser.add_argument('--import-history', action='store_true', help='从刷卡数据导入出行历史')
    parser.add_argument('--origin', type=str, help='起点站ID')
    parser.add_argument('--dest', type=str, help='终点站ID')
    parser.add_argument('--hour', type=int, help='出行时段 (0-23)')
    parser.add_argument('--date', type=str, default=None, help='分析日期')
    args = parser.parse_args()

    if args.import_history:
        import_travel_history_from_od()

    if args.origin and args.dest and args.hour is not None:
        recs = generate_od_recommendations(args.origin, args.dest, args.hour, args.date)
        print(f"\n共生成 {len(recs)} 条推荐:")
        for r in recs:
            print(f"  [{r['rec_type']}] {r['title']} (score={r['score']:.2f})")
            print(f"    {r['description'][:100]}...")
            print(f"    算法: {r['metadata'].get('algorithm', 'N/A')}")
