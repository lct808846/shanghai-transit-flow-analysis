"""
PySpark ETL 脚本
=================
使用 PySpark 对原始刷卡记录进行分布式 ETL 处理。

注意：
  - 需要安装 Java 8+ 和 PySpark 3.5+
  - 对于小规模数据，推荐使用 etl_process.py（Pandas 版本）
  - 本脚本适用于大规模数据（百万级以上记录）

用法：
  python spark_etl.py
  或：
  spark-submit spark_etl.py
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transit_system.settings')
django.setup()

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from analysis.models import BusStation, OdFlow, StationFlowStats


def create_spark_session():
    """创建 SparkSession"""
    return (
        SparkSession.builder
        .appName("Shanghai Transit ETL")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def run_spark_etl():
    """PySpark ETL 主流程"""

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_data_path = os.path.join(project_root, 'data', 'raw', 'mock_swipe_records.csv')

    if not os.path.exists(raw_data_path):
        print(f"[ERROR] 数据文件不存在: {raw_data_path}")
        print("请先运行 etl_process.py 生成模拟数据。")
        return

    print(f"[Spark ETL] 读取数据文件: {raw_data_path}")

    # 1. 创建 SparkSession
    spark = create_spark_session()

    try:
        # 2. 读取 CSV 数据
        df = spark.read.csv(raw_data_path, header=True, inferSchema=True)
        df = df.withColumn('swipe_time', F.to_timestamp('swipe_time'))

        record_count = df.count()
        print(f"[Spark ETL] 共读取 {record_count} 条刷卡记录")
        print(f"[Spark ETL] Schema:")
        df.printSchema()

        # 3. 数据清洗 - 去重、去空值
        df_clean = df.dropna(subset=['card_id', 'station_name', 'swipe_time', 'swipe_type'])
        df_clean = df_clean.dropDuplicates()
        clean_count = df_clean.count()
        print(f"[Spark ETL] 清洗后 {clean_count} 条记录 (去除 {record_count - clean_count} 条)")

        # 4. OD 配对 - 使用窗口函数
        window_spec = Window.partitionBy('card_id').orderBy('swipe_time')

        df_with_next = df_clean.withColumn('next_card', F.lead('card_id').over(window_spec)) \
            .withColumn('next_swipe_type', F.lead('swipe_type').over(window_spec)) \
            .withColumn('next_station', F.lead('station_name').over(window_spec)) \
            .withColumn('next_time', F.lead('swipe_time').over(window_spec))

        # 筛选有效 OD 对（同一人、这次进站、下次出站）
        trips = df_with_next.filter(
            (F.col('card_id') == F.col('next_card')) &
            (F.col('swipe_type') == 'in') &
            (F.col('next_swipe_type') == 'out')
        )

        # 计算出行时长
        trips = trips.withColumn(
            'duration_min',
            (F.unix_timestamp('next_time') - F.unix_timestamp('swipe_time')) / 60
        )
        trips = trips.withColumn('date', F.to_date('swipe_time'))
        trips = trips.withColumn('hour', F.hour('swipe_time'))

        trip_count = trips.count()
        print(f"[Spark ETL] 配对出 {trip_count} 条 OD 出行记录")

        # 5. 聚合 OD 统计
        od_stats = trips.groupBy('date', 'hour', 'station_name', 'next_station').agg(
            F.count('card_id').alias('flow_count'),
            F.avg('duration_min').alias('avg_duration')
        )

        print(f"[Spark ETL] 生成 {od_stats.count()} 条 OD 聚合记录")

        # 6. 站点客流统计
        in_stats = df_clean.filter(F.col('swipe_type') == 'in') \
            .groupBy(F.to_date('swipe_time').alias('date'),
                     F.hour('swipe_time').alias('hour'),
                     'station_name') \
            .agg(F.count('*').alias('in_flow'))

        out_stats = df_clean.filter(F.col('swipe_type') == 'out') \
            .groupBy(F.to_date('swipe_time').alias('date'),
                     F.hour('swipe_time').alias('hour'),
                     'station_name') \
            .agg(F.count('*').alias('out_flow'))

        station_stats = in_stats.join(
            out_stats,
            on=['date', 'hour', 'station_name'],
            how='outer'
        ).fillna(0)

        station_stats = station_stats.withColumn(
            'total_flow', F.col('in_flow') + F.col('out_flow')
        )

        print(f"[Spark ETL] 生成 {station_stats.count()} 条站点统计记录")

        # 7. 写入数据库
        print("[Spark ETL] 开始写入数据库...")

        # 收集到 Driver 端写入 Django ORM
        od_rows = od_stats.collect()
        OdFlow.objects.all().delete()

        od_objects = []
        for row in od_rows:
            try:
                origin = BusStation.objects.get(pk=row['station_name'])
                dest = BusStation.objects.get(pk=row['next_station'])
                od_objects.append(OdFlow(
                    date=row['date'],
                    hour=row['hour'],
                    origin_station=origin,
                    destination_station=dest,
                    flow_count=row['flow_count'],
                    trip_duration_avg=float(row['avg_duration'])
                ))
            except BusStation.DoesNotExist:
                continue

        batch_size = 500
        for i in range(0, len(od_objects), batch_size):
            OdFlow.objects.bulk_create(od_objects[i:i + batch_size])
        print(f"[Spark ETL] 写入 {len(od_objects)} 条 OD 记录")

        stat_rows = station_stats.collect()
        StationFlowStats.objects.all().delete()

        stat_objects = []
        for row in stat_rows:
            try:
                station = BusStation.objects.get(pk=row['station_name'])
                tf = int(row['total_flow'])
                congestion = 'low'
                if tf > 100:
                    congestion = 'high'
                elif tf > 50:
                    congestion = 'medium'

                stat_objects.append(StationFlowStats(
                    station=station,
                    date=row['date'],
                    hour=row['hour'],
                    in_flow=int(row['in_flow']),
                    out_flow=int(row['out_flow']),
                    total_flow=tf,
                    congestion_level=congestion
                ))
            except BusStation.DoesNotExist:
                continue

        for i in range(0, len(stat_objects), batch_size):
            StationFlowStats.objects.bulk_create(stat_objects[i:i + batch_size])
        print(f"[Spark ETL] 写入 {len(stat_objects)} 条站点统计记录")

        print("[Spark ETL] ✅ 全部处理完成！")

    finally:
        spark.stop()
        print("[Spark ETL] SparkSession 已关闭")


if __name__ == "__main__":
    run_spark_etl()
