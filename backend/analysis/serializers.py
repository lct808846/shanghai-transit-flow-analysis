from rest_framework import serializers
from .models import BusStation, OdFlow, StationFlowStats, RouteInfo, RouteStation, AnalysisReport, ClusterResult, Recommendation


class BusStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusStation
        fields = '__all__'


class OdFlowSerializer(serializers.ModelSerializer):
    origin_station_name = serializers.CharField(source='origin_station.station_name', read_only=True)
    destination_station_name = serializers.CharField(source='destination_station.station_name', read_only=True)

    class Meta:
        model = OdFlow
        fields = ['id', 'date', 'hour', 'origin_station', 'origin_station_name',
                  'destination_station', 'destination_station_name',
                  'flow_count', 'trip_duration_avg']


class StationFlowStatsSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.station_name', read_only=True)

    class Meta:
        model = StationFlowStats
        fields = ['id', 'station', 'station_name', 'date', 'hour',
                  'in_flow', 'out_flow', 'total_flow', 'congestion_level']


class RouteInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteInfo
        fields = '__all__'


class RouteStationSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.station_name', read_only=True)

    class Meta:
        model = RouteStation
        fields = ['id', 'route', 'station', 'station_name', 'sequence']


class AnalysisReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisReport
        fields = '__all__'


# ---------- 聚合统计用的自定义序列化器 ----------

class HourlyFlowSerializer(serializers.Serializer):
    """按小时聚合的客流量"""
    hour = serializers.IntegerField()
    total_in = serializers.IntegerField()
    total_out = serializers.IntegerField()
    total_flow = serializers.IntegerField()


class StationRankSerializer(serializers.Serializer):
    """站点客流排名"""
    station = serializers.CharField()
    station__station_name = serializers.CharField()
    total_flow = serializers.IntegerField()
    total_in = serializers.IntegerField()
    total_out = serializers.IntegerField()


class OdTopSerializer(serializers.Serializer):
    """OD 热门路线排名"""
    origin_station = serializers.CharField()
    origin_station__station_name = serializers.CharField()
    destination_station = serializers.CharField()
    destination_station__station_name = serializers.CharField()
    total_flow = serializers.IntegerField()


class ClusterResultSerializer(serializers.ModelSerializer):
    """聚类结果"""
    station_name = serializers.CharField(source='station.station_name', read_only=True)

    class Meta:
        model = ClusterResult
        fields = ['id', 'station', 'station_name', 'cluster_label', 'longitude', 'latitude',
                  'total_flow', 'is_hotspot', 'eps', 'min_samples', 'analysis_date', 'created_at']


class ClusterSummarySerializer(serializers.Serializer):
    """聚类统计摘要"""
    cluster_label = serializers.IntegerField()
    station_count = serializers.IntegerField()
    total_flow = serializers.IntegerField()
    is_hotspot = serializers.BooleanField()
    center_lon = serializers.FloatField()
    center_lat = serializers.FloatField()


class RecommendationSerializer(serializers.ModelSerializer):
    """推荐结果"""
    rec_type_display = serializers.CharField(source='get_rec_type_display', read_only=True)

    class Meta:
        model = Recommendation
        fields = ['id', 'user_id', 'rec_type', 'rec_type_display', 'title',
                  'description', 'score', 'metadata', 'created_at']
