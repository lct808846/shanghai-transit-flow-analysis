from django.db import models

class BusStation(models.Model):
    """
    公交站点/地铁站点元数据
    """
    station_id = models.CharField(max_length=50, primary_key=True, verbose_name="站点ID")
    station_name = models.CharField(max_length=100, verbose_name="站点名称")
    longitude = models.FloatField(verbose_name="经度")
    latitude = models.FloatField(verbose_name="纬度")
    district = models.CharField(max_length=50, blank=True, null=True, verbose_name="行政区")
    region_type = models.CharField(max_length=20, default='bus', choices=[('bus', '公交'), ('subway', '地铁')], verbose_name="类型")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "交通站点"
        verbose_name_plural = "交通站点"

    def __str__(self):
        return self.station_name

class OdFlow(models.Model):
    """
    OD出行客流 (Origin-Destination)
    用于存储从 Spark 计算出的 OD 矩阵结果
    """
    date = models.DateField(verbose_name="日期")
    hour = models.IntegerField(verbose_name="小时")
    origin_station = models.ForeignKey(BusStation, related_name='outbound_flows', on_delete=models.CASCADE, verbose_name="出发站点")
    destination_station = models.ForeignKey(BusStation, related_name='inbound_flows', on_delete=models.CASCADE, verbose_name="到达站点")
    flow_count = models.IntegerField(verbose_name="客流量")
    trip_duration_avg = models.FloatField(blank=True, null=True, verbose_name="平均出行耗时(分)")

    class Meta:
        verbose_name = "OD客流"
        verbose_name_plural = "OD客流"
        indexes = [
            models.Index(fields=['date', 'hour']),
            models.Index(fields=['origin_station']),
            models.Index(fields=['destination_station']),
        ]

class StationFlowStats(models.Model):
    """
    站点粒度的客流统计结果 (进站/出站/总流量/拥挤度)
    """
    station = models.ForeignKey(BusStation, on_delete=models.CASCADE, verbose_name="站点")
    date = models.DateField(verbose_name="日期")
    hour = models.IntegerField(verbose_name="小时")
    in_flow = models.IntegerField(default=0, verbose_name="进站流量")
    out_flow = models.IntegerField(default=0, verbose_name="出站流量")
    total_flow = models.IntegerField(default=0, verbose_name="总流量")
    congestion_level = models.CharField(max_length=20, default='low', choices=[('low', '低'), ('medium', '中'), ('high', '高')], verbose_name="拥挤度等级")

    class Meta:
        verbose_name = "站点客流统计"
        verbose_name_plural = "站点客流统计"
        indexes = [
            models.Index(fields=['station', 'date', 'hour']),
        ]

class RouteInfo(models.Model):
    """
    线路信息
    """
    route_id = models.CharField(max_length=50, primary_key=True, verbose_name="线路ID")
    route_name = models.CharField(max_length=100, verbose_name="线路名称")
    direction = models.CharField(max_length=20, blank=True, null=True, verbose_name="方向") # 上行/下行
    
    class Meta:
        verbose_name = "线路信息"
        verbose_name_plural = "线路信息"

class RouteStation(models.Model):
    """
    线路-站点关联表 (描述线路经过哪些站点及其顺序)
    """
    route = models.ForeignKey(RouteInfo, on_delete=models.CASCADE, verbose_name="线路")
    station = models.ForeignKey(BusStation, on_delete=models.CASCADE, verbose_name="站点")
    sequence = models.IntegerField(verbose_name="站点序号")

    class Meta:
        verbose_name = "线路站点关联"
        verbose_name_plural = "线路站点关联"
        ordering = ['route', 'sequence']

class ClusterResult(models.Model):
    """
    DBSCAN 空间聚类结果
    """
    station = models.ForeignKey(BusStation, on_delete=models.CASCADE, verbose_name="站点")
    cluster_label = models.IntegerField(verbose_name="聚类标签")  # -1 表示噪声点
    longitude = models.FloatField(verbose_name="经度")
    latitude = models.FloatField(verbose_name="纬度")
    total_flow = models.IntegerField(default=0, verbose_name="站点总客流")
    is_hotspot = models.BooleanField(default=False, verbose_name="是否热点")
    eps = models.FloatField(default=0.0, verbose_name="聚类半径参数")
    min_samples = models.IntegerField(default=0, verbose_name="最小样本参数")
    analysis_date = models.DateField(null=True, blank=True, verbose_name="分析日期")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "聚类结果"
        verbose_name_plural = "聚类结果"
        indexes = [
            models.Index(fields=['cluster_label']),
            models.Index(fields=['analysis_date']),
        ]

    def __str__(self):
        return f"{self.station} -> Cluster {self.cluster_label}"


class AnalysisReport(models.Model):
    """
    存储生成的分析报告摘要 (如早晚高峰时段判定结果、全天总客流等)
    """
    report_date = models.DateField(verbose_name="报告日期")
    total_passenger_count = models.IntegerField(verbose_name="全天总客流量")
    peak_morning_start = models.TimeField(null=True, blank=True, verbose_name="早高峰开始")
    peak_morning_end = models.TimeField(null=True, blank=True, verbose_name="早高峰结束")
    peak_evening_start = models.TimeField(null=True, blank=True, verbose_name="晚高峰开始")
    peak_evening_end = models.TimeField(null=True, blank=True, verbose_name="晚高峰结束")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "分析报告"
        verbose_name_plural = "分析报告"


class UserTravelHistory(models.Model):
    """用户出行历史记录（从刷卡数据提取）"""
    user_id = models.CharField(max_length=50, db_index=True, verbose_name="用户ID/卡号")
    origin_station = models.ForeignKey(BusStation, related_name='travel_origins', on_delete=models.CASCADE, verbose_name="出发站")
    destination_station = models.ForeignKey(BusStation, related_name='travel_destinations', on_delete=models.CASCADE, verbose_name="到达站")
    travel_date = models.DateField(verbose_name="出行日期")
    travel_hour = models.IntegerField(verbose_name="出行时段")
    duration_min = models.FloatField(default=0, verbose_name="耗时(分)")

    class Meta:
        verbose_name = "出行历史"
        verbose_name_plural = "出行历史"
        indexes = [
            models.Index(fields=['user_id', 'travel_date']),
        ]


class Recommendation(models.Model):
    """智能推荐结果"""
    REC_TYPE_CHOICES = [
        ('avoid', '拥挤分析'),
        ('time', '时段推荐'),
        ('route', '替代路线'),
    ]

    user_id = models.CharField(max_length=50, db_index=True, verbose_name="用户ID")
    rec_type = models.CharField(max_length=20, choices=REC_TYPE_CHOICES, verbose_name="推荐类型")
    title = models.CharField(max_length=200, verbose_name="推荐标题")
    description = models.TextField(verbose_name="推荐描述")
    score = models.FloatField(default=0, verbose_name="推荐评分")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="附加数据")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "推荐结果"
        verbose_name_plural = "推荐结果"
        ordering = ['-score']
