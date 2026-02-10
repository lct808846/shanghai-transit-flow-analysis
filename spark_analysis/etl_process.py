import os
import sys
import django
import pandas as pd
import numpy as np

# 设置 Django 环境
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transit_system.settings')
django.setup()

from analysis.models import BusStation, OdFlow, StationFlowStats, RouteInfo

def process_data():
    # 自动定位项目根目录下的数据文件
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_data_path = os.path.join(project_root, 'data', 'raw', 'mock_swipe_records.csv')
    
    if not os.path.exists(raw_data_path):
        print(f"Data file not found: {raw_data_path}")
        return

    print(f"Reading data from {raw_data_path} using Pandas...")
    df = pd.read_csv(raw_data_path)
    df['swipe_time'] = pd.to_datetime(df['swipe_time'])
    
    # ------------------------------------------------------------------
    # 2. 元数据同步
    # ------------------------------------------------------------------
    print("Syncing metadata to DB...")
    stations = df[['station_name', 'line_name']].drop_duplicates()
    
    for _, row in stations.iterrows():
        BusStation.objects.get_or_create(
            station_id=row['station_name'], 
            defaults={
                'station_name': row['station_name'],
                'longitude': 121.47, 
                'latitude': 31.23,
                'region_type': 'subway' 
            }
        )
        RouteInfo.objects.get_or_create(
            route_id=row['line_name'],
            defaults={'route_name': row['line_name']}
        )

    # ------------------------------------------------------------------
    # 3. OD 客流计算 (Trip Identification)
    # ------------------------------------------------------------------
    print("Calculating OD Matrix...")
    
    # 按卡号和时间排序
    df.sort_values(by=['card_id', 'swipe_time'], inplace=True)
    
    # 偏移一行获取下次刷卡信息
    df['next_card'] = df['card_id'].shift(-1)
    df['next_swipe_type'] = df['swipe_type'].shift(-1)
    df['next_station'] = df['station_name'].shift(-1)
    df['next_time'] = df['swipe_time'].shift(-1)
    
    # 筛选有效的 OD 对（同一人，这次进，下次出）
    trips = df[(df['card_id'] == df['next_card']) & 
               (df['swipe_type'] == 'in') & 
               (df['next_swipe_type'] == 'out')].copy()

    trips['duration_min'] = (trips['next_time'] - trips['swipe_time']).dt.total_seconds() / 60
    trips['date'] = trips['swipe_time'].dt.date
    trips['hour'] = trips['swipe_time'].dt.hour
    
    # 聚合
    od_stats = trips.groupby(['date', 'hour', 'station_name', 'next_station']).agg(
        flow_count=('card_id', 'count'),
        avg_duration=('duration_min', 'mean')
    ).reset_index()
    
    print(f"Saving {len(od_stats)} OD records to DB...")
    od_objects = []
    
    for _, row in od_stats.iterrows():
        # 获取关联对象
        origin = BusStation.objects.get(pk=row['station_name'])
        dest = BusStation.objects.get(pk=row['next_station'])
        
        od_objects.append(OdFlow(
            date=row['date'],
            hour=row['hour'],
            origin_station=origin,
            destination_station=dest,
            flow_count=row['flow_count'],
            trip_duration_avg=row['avg_duration']
        ))
    
    # 批量插入 (分批处理以防内存溢出)
    batch_size = 500
    OdFlow.objects.all().delete() # 清理旧数据
    for i in range(0, len(od_objects), batch_size):
        OdFlow.objects.bulk_create(od_objects[i:i+batch_size])

    # ------------------------------------------------------------------
    # 4. 站点客流统计
    # ------------------------------------------------------------------
    print("Calculating Station Statistics...")
    
    # 进站统计
    in_stats = df[df['swipe_type'] == 'in'].groupby(
        [df['swipe_time'].dt.date.rename('date'), df['swipe_time'].dt.hour.rename('hour'), 'station_name']
    ).size().reset_index(name='in_flow')
    
    # 出站统计
    out_stats = df[df['swipe_type'] == 'out'].groupby(
        [df['swipe_time'].dt.date.rename('date'), df['swipe_time'].dt.hour.rename('hour'), 'station_name']
    ).size().reset_index(name='out_flow')
    
    # 合并
    station_stats = pd.merge(in_stats, out_stats, on=['date', 'hour', 'station_name'], how='outer').fillna(0)
    station_stats['total_flow'] = station_stats['in_flow'] + station_stats['out_flow']
    
    stat_objects = []
    StationFlowStats.objects.all().delete() # 清理旧数据
    
    for _, row in station_stats.iterrows():
        tf = row['total_flow']
        congestion = 'low'
        if tf > 100: congestion = 'high'
        elif tf > 50: congestion = 'medium'
        
        station = BusStation.objects.get(pk=row['station_name'])
        
        stat_objects.append(StationFlowStats(
            station=station,
            date=row['date'],
            hour=row['hour'],
            in_flow=row['in_flow'],
            out_flow=row['out_flow'],
            total_flow=tf,
            congestion_level=congestion
        ))
        
    for i in range(0, len(stat_objects), batch_size):
        StationFlowStats.objects.bulk_create(stat_objects[i:i+batch_size])
        
    print(f"Saved {len(stat_objects)} Station Stat records.")
    print("ETL Process (Pandas) Completed Successfully.")

if __name__ == "__main__":
    process_data()
