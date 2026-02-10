"""
DBSCAN 空间聚类分析
对站点进行空间聚类，结合客流量识别交通热点区域
"""
import os
import sys
import numpy as np
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transit_system.settings')
django.setup()

from django.db.models import Sum
from analysis.models import BusStation, StationFlowStats, ClusterResult


def run_dbscan(eps=0.008, min_samples=2, date=None):
    """
    执行 DBSCAN 空间聚类分析

    参数:
        eps: float - DBSCAN 邻域半径 (经纬度距离，约 0.01 ≈ 1km)
        min_samples: int - 最小样本数
        date: str|None - 可选日期筛选 (如 '2025-05-01')

    返回:
        dict - 聚类统计信息
    """
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler

    print("=" * 60)
    print("  DBSCAN 空间聚类分析")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. 获取站点数据及其客流量
    # ------------------------------------------------------------------
    stations = BusStation.objects.all()
    if stations.count() == 0:
        print("错误: 数据库中没有站点数据，请先运行 ETL 流程")
        return None

    station_data = []
    for station in stations:
        flow_qs = StationFlowStats.objects.filter(station=station)
        if date:
            flow_qs = flow_qs.filter(date=date)
        total_flow = flow_qs.aggregate(total=Sum('total_flow'))['total'] or 0

        station_data.append({
            'station': station,
            'lon': station.longitude,
            'lat': station.latitude,
            'total_flow': total_flow,
        })

    print(f"共获取 {len(station_data)} 个站点")

    # ------------------------------------------------------------------
    # 2. 构建特征矩阵 (经度, 纬度)
    # ------------------------------------------------------------------
    coords = np.array([[s['lon'], s['lat']] for s in station_data])

    # 检查坐标是否全部相同（说明未更新坐标）
    if np.std(coords[:, 0]) < 0.001 and np.std(coords[:, 1]) < 0.001:
        print("警告: 所有站点坐标几乎相同！请先运行 update_station_coords.py 更新坐标")
        return None

    # ------------------------------------------------------------------
    # 3. 执行 DBSCAN 聚类
    #    使用 haversine 度量需要弧度，这里简化用欧氏距离 (经纬度小范围近似可用)
    # ------------------------------------------------------------------
    print(f"DBSCAN 参数: eps={eps}, min_samples={min_samples}")

    db = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
    labels = db.fit_predict(coords)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    print(f"聚类数量: {n_clusters}")
    print(f"噪声点数: {n_noise}")

    # ------------------------------------------------------------------
    # 4. 计算每个聚类的总客流，识别热点
    # ------------------------------------------------------------------
    cluster_flows = {}
    for i, sd in enumerate(station_data):
        label = int(labels[i])
        if label == -1:
            continue
        if label not in cluster_flows:
            cluster_flows[label] = 0
        cluster_flows[label] += sd['total_flow']

    # 使用客流量中位数判断热点
    if cluster_flows:
        flow_values = list(cluster_flows.values())
        flow_median = np.median(flow_values)
        flow_threshold = flow_median * 1.2  # 高于中位数 20% 为热点
        print(f"客流中位数: {flow_median:.0f}, 热点阈值: {flow_threshold:.0f}")
    else:
        flow_threshold = 0

    # ------------------------------------------------------------------
    # 5. 存入数据库
    # ------------------------------------------------------------------
    ClusterResult.objects.all().delete()
    objects_to_create = []

    for i, sd in enumerate(station_data):
        label = int(labels[i])
        is_hot = (label != -1 and cluster_flows.get(label, 0) > flow_threshold)

        objects_to_create.append(ClusterResult(
            station=sd['station'],
            cluster_label=label,
            longitude=sd['lon'],
            latitude=sd['lat'],
            total_flow=sd['total_flow'],
            is_hotspot=is_hot,
            eps=eps,
            min_samples=min_samples,
            analysis_date=date,
        ))

    ClusterResult.objects.bulk_create(objects_to_create)
    print(f"已写入 {len(objects_to_create)} 条聚类结果到数据库")

    # ------------------------------------------------------------------
    # 6. 输出统计报告
    # ------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("聚类统计报告")
    print("-" * 50)

    for cl in sorted(set(labels)):
        members = [station_data[i] for i in range(len(labels)) if labels[i] == cl]
        total = sum(m['total_flow'] for m in members)
        tag = "🔥热点" if cl != -1 and cluster_flows.get(cl, 0) > flow_threshold else ""
        if cl == -1:
            tag = "🔵噪声"
        station_names = [m['station'].station_name for m in members]
        print(f"\n  Cluster {cl} ({len(members)} 站点, 总客流 {total}) {tag}")
        print(f"    站点: {', '.join(station_names)}")

    result_summary = {
        'n_clusters': n_clusters,
        'n_noise': n_noise,
        'total_stations': len(station_data),
        'cluster_details': {
            int(cl): {
                'count': len([1 for l in labels if l == cl]),
                'total_flow': cluster_flows.get(int(cl), 0) if cl != -1 else sum(
                    station_data[i]['total_flow'] for i in range(len(labels)) if labels[i] == -1
                ),
                'is_hotspot': cl != -1 and cluster_flows.get(int(cl), 0) > flow_threshold,
            }
            for cl in sorted(set(labels))
        }
    }

    print("\n✅ DBSCAN 聚类分析完成！")
    return result_summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='DBSCAN 空间聚类分析')
    parser.add_argument('--eps', type=float, default=0.008, help='DBSCAN 邻域半径 (默认 0.008 ≈ 800m)')
    parser.add_argument('--min-samples', type=int, default=2, help='最小样本数 (默认 2)')
    parser.add_argument('--date', type=str, default=None, help='分析日期 (如 2025-05-01)')
    args = parser.parse_args()

    result = run_dbscan(eps=args.eps, min_samples=args.min_samples, date=args.date)
    if result:
        print(f"\n最终结果: {result['n_clusters']} 个聚类, {result['n_noise']} 个噪声点")
