from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, F, Count, Avg
from .models import BusStation, OdFlow, StationFlowStats, RouteInfo, AnalysisReport, ClusterResult, Recommendation
from .serializers import (
    BusStationSerializer, OdFlowSerializer, StationFlowStatsSerializer,
    RouteInfoSerializer, AnalysisReportSerializer,
    HourlyFlowSerializer, StationRankSerializer, OdTopSerializer,
    ClusterResultSerializer, ClusterSummarySerializer,
    RecommendationSerializer
)


# ====================== ViewSets (CRUD) ======================

class BusStationViewSet(viewsets.ReadOnlyModelViewSet):
    """站点信息接口（站点数量较少，不分页）"""
    queryset = BusStation.objects.all()
    serializer_class = BusStationSerializer
    pagination_class = None


class OdFlowViewSet(viewsets.ReadOnlyModelViewSet):
    """OD客流接口，支持按日期和小时筛选"""
    queryset = OdFlow.objects.select_related('origin_station', 'destination_station').all()
    serializer_class = OdFlowSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get('date')
        hour = self.request.query_params.get('hour')
        origin = self.request.query_params.get('origin')
        destination = self.request.query_params.get('destination')
        if date:
            qs = qs.filter(date=date)
        if hour:
            qs = qs.filter(hour=hour)
        if origin:
            qs = qs.filter(origin_station__station_name__icontains=origin)
        if destination:
            qs = qs.filter(destination_station__station_name__icontains=destination)
        return qs


class StationFlowStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """站点客流统计接口，支持按日期、小时、站点筛选"""
    queryset = StationFlowStats.objects.select_related('station').all()
    serializer_class = StationFlowStatsSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get('date')
        hour = self.request.query_params.get('hour')
        station = self.request.query_params.get('station')
        congestion = self.request.query_params.get('congestion')
        if date:
            qs = qs.filter(date=date)
        if hour:
            qs = qs.filter(hour=hour)
        if station:
            qs = qs.filter(station__station_name__icontains=station)
        if congestion:
            qs = qs.filter(congestion_level=congestion)
        return qs


class RouteInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """线路信息接口"""
    queryset = RouteInfo.objects.all()
    serializer_class = RouteInfoSerializer


class AnalysisReportViewSet(viewsets.ReadOnlyModelViewSet):
    """分析报告接口"""
    queryset = AnalysisReport.objects.all().order_by('-report_date')
    serializer_class = AnalysisReportSerializer


# ====================== 聚合统计 API ======================

@api_view(['GET'])
def hourly_flow_summary(request):
    """
    按小时统计全网客流量
    可选参数: ?date=2025-05-01 或 ?month=2025-05 (按月聚合)
              ?station=站点名 (按站点名模糊筛选)
    """
    date = request.query_params.get('date')
    month = request.query_params.get('month')  # YYYY-MM
    station = request.query_params.get('station')
    qs = StationFlowStats.objects.all()
    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=int(year), date__month=int(mon))
        except (ValueError, TypeError):
            pass
    elif date:
        qs = qs.filter(date=date)
    if station:
        qs = qs.filter(station__station_name__icontains=station)

    result = qs.values('hour').annotate(
        total_in=Sum('in_flow'),
        total_out=Sum('out_flow'),
        total_flow=Sum('total_flow')
    ).order_by('hour')

    serializer = HourlyFlowSerializer(result, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def station_flow_rank(request):
    """
    站点客流量排名 (Top N)
    可选参数: ?date=2025-05-01&top=20 或 ?month=2025-05&top=20
    """
    date = request.query_params.get('date')
    month = request.query_params.get('month')
    top_n = int(request.query_params.get('top', 20))
    qs = StationFlowStats.objects.all()
    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=int(year), date__month=int(mon))
        except (ValueError, TypeError):
            pass
    elif date:
        qs = qs.filter(date=date)

    result = qs.values('station', 'station__station_name').annotate(
        total_flow=Sum('total_flow'),
        total_in=Sum('in_flow'),
        total_out=Sum('out_flow'),
    ).order_by('-total_flow')[:top_n]

    serializer = StationRankSerializer(result, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def district_flow(request):
    """
    按行政区聚合站点客流
    可选参数: ?date=2025-05-01 或 ?month=2025-05
    """
    date = request.query_params.get('date')
    month = request.query_params.get('month')
    qs = StationFlowStats.objects.all()
    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=int(year), date__month=int(mon))
        except (ValueError, TypeError):
            pass
    elif date:
        qs = qs.filter(date=date)

    result = qs.values(district=F('station__district')).annotate(
        total_flow=Sum('total_flow'),
        total_in=Sum('in_flow'),
        total_out=Sum('out_flow'),
        station_count=Count('station', distinct=True),
    ).order_by('-total_flow')

    return Response(list(result))


@api_view(['GET'])
def od_top_routes(request):
    """
    热门 OD 路线排名 (Top N)
    可选参数: ?date=2025-05-01&top=20&origin=站名&destination=站名
    """
    date = request.query_params.get('date')
    month = request.query_params.get('month')
    top_n = int(request.query_params.get('top', 20))
    origin = request.query_params.get('origin')
    destination = request.query_params.get('destination')
    qs = OdFlow.objects.all()
    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=int(year), date__month=int(mon))
        except (ValueError, TypeError):
            pass
    elif date:
        qs = qs.filter(date=date)
    if origin:
        qs = qs.filter(origin_station__station_name=origin)
    if destination:
        qs = qs.filter(destination_station__station_name=destination)

    result = qs.values(
        'origin_station', 'origin_station__station_name',
        'destination_station', 'destination_station__station_name'
    ).annotate(
        total_flow=Sum('flow_count')
    ).order_by('-total_flow')[:top_n]

    serializer = OdTopSerializer(result, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def od_station_heat(request):
    """
    OD 站点热度统计：分别统计出发/到达维度 Top10
    返回 { origins: [{station_name, total_flow}], destinations: [...] }
    """
    date = request.query_params.get('date')
    month = request.query_params.get('month')
    qs = OdFlow.objects.all()
    if month:
        try:
            year, mon = month.split('-')
            qs = qs.filter(date__year=int(year), date__month=int(mon))
        except (ValueError, TypeError):
            pass
    elif date:
        qs = qs.filter(date=date)

    origins = list(
        qs.values(station_name=F('origin_station__station_name'))
        .annotate(total_flow=Sum('flow_count'))
        .order_by('-total_flow')[:10]
    )
    destinations = list(
        qs.values(station_name=F('destination_station__station_name'))
        .annotate(total_flow=Sum('flow_count'))
        .order_by('-total_flow')[:10]
    )
    return Response({'origins': origins, 'destinations': destinations})


@api_view(['GET'])
def cluster_results(request):
    """
    获取聚类结果列表
    可选参数: ?label=0 (按聚类标签筛选)  ?hotspot=true (仅热点)
    """
    qs = ClusterResult.objects.select_related('station').all()
    label = request.query_params.get('label')
    hotspot = request.query_params.get('hotspot')
    if label is not None:
        qs = qs.filter(cluster_label=int(label))
    if hotspot == 'true':
        qs = qs.filter(is_hotspot=True)

    serializer = ClusterResultSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def cluster_summary(request):
    """
    聚类统计摘要 (每个聚类的站点数、总客流、中心坐标)
    """
    clusters = ClusterResult.objects.values('cluster_label').annotate(
        station_count=Count('id'),
        total_flow=Sum('total_flow'),
        center_lon=Avg('longitude'),
        center_lat=Avg('latitude'),
    ).order_by('cluster_label')

    # 判断热点
    results = []
    flows = [c['total_flow'] for c in clusters if c['cluster_label'] != -1]
    threshold = sorted(flows)[len(flows) // 2] * 1.2 if flows else 0

    for c in clusters:
        c['is_hotspot'] = c['cluster_label'] != -1 and c['total_flow'] > threshold
        results.append(c)

    serializer = ClusterSummarySerializer(results, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def run_cluster_analysis(request):
    """
    触发 DBSCAN 聚类分析 (POST 请求)
    参数: eps (float), min_samples (int), date (str, optional)
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'spark_analysis'))
    from dbscan_clustering import run_dbscan

    eps = float(request.data.get('eps', 0.012))
    min_samples = int(request.data.get('min_samples', 2))
    date = request.data.get('date', None)

    result = run_dbscan(eps=eps, min_samples=min_samples, date=date)
    if result:
        return Response({'status': 'success', 'summary': result})
    return Response({'status': 'error', 'message': '聚类失败，请检查数据'}, status=400)


@api_view(['GET'])
def get_recommendations(request):
    """
    实时出行推荐
    参数: ?origin=站点ID &dest=站点ID &hour=8 &date=2025-05-01(可选)
    基于 Z-Score 异常检测 + 余弦相似度 + 加权评分 实时计算
    """
    origin = request.query_params.get('origin')
    dest = request.query_params.get('dest')
    hour = request.query_params.get('hour')
    date = request.query_params.get('date', None)

    if not origin or not dest or hour is None:
        return Response({'status': 'error', 'message': '请提供 origin, dest, hour 参数'}, status=400)

    try:
        hour = int(hour)
    except (ValueError, TypeError):
        return Response({'status': 'error', 'message': 'hour 必须为整数'}, status=400)

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'spark_analysis'))
    from recommendation_engine import generate_od_recommendations

    recs = generate_od_recommendations(origin, dest, hour, date)
    return Response({'status': 'success', 'count': len(recs), 'data': recs})


@api_view(['GET'])
def get_station_list(request):
    """
    获取站点列表 (用于推荐页面下拉框)
    支持 ?search=关键词 模糊搜索
    """
    search = request.query_params.get('search', '')
    qs = BusStation.objects.all().order_by('station_name')
    if search:
        qs = qs.filter(station_name__icontains=search)
    data = list(qs.values('station_id', 'station_name'))
    return Response({'status': 'success', 'data': data})


@api_view(['GET'])
def get_active_users(request):
    """
    获取活跃用户列表（有出行记录的用户）
    """
    from analysis.models import UserTravelHistory
    top_n = int(request.query_params.get('top', 20))
    users = (
        UserTravelHistory.objects.values('user_id')
        .annotate(trip_count=Count('id'))
        .order_by('-trip_count')[:top_n]
    )
    return Response({'status': 'success', 'data': list(users)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_csv(request):
    """
    CSV 数据上传接口 (仅管理员)
    支持上传类型: station_flow (站点客流), swipe_record (刷卡记录)
    """
    import csv, io
    from datetime import datetime, date as date_type
    from django.db import transaction
    from .models import (
        BusStation, OdFlow, StationFlowStats, RouteInfo,
        UserTravelHistory
    )

    # 权限检查
    if not (request.user.is_staff or getattr(request.user, 'role', '') == 'admin'):
        return Response({'status': 'error', 'message': '仅管理员可上传数据'}, status=403)

    upload_type = request.data.get('type', '')
    csv_file = request.FILES.get('file')

    if not csv_file:
        return Response({'status': 'error', 'message': '请上传 CSV 文件'}, status=400)
    if not csv_file.name.endswith('.csv'):
        return Response({'status': 'error', 'message': '仅支持 .csv 格式文件'}, status=400)
    if csv_file.size > 200 * 1024 * 1024:  # 200MB
        return Response({'status': 'error', 'message': '文件大小不能超过 200MB'}, status=400)

    try:
        content = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    except Exception as e:
        return Response({'status': 'error', 'message': f'CSV 解析失败: {str(e)}'}, status=400)

    if not rows:
        return Response({'status': 'error', 'message': 'CSV 文件为空'}, status=400)

    columns = list(rows[0].keys())
    result = {'total_rows': len(rows), 'columns': columns}

    try:
        if upload_type == 'station_flow':
            # ===== 站点客流数据 =====
            required = {'transactiondate', 'incount', 'staname', 'linename', 'outcount'}
            if not required.issubset(set(columns)):
                missing = required - set(columns)
                return Response({'status': 'error', 'message': f'缺少必要列: {missing}'}, status=400)

            stations_created = 0
            routes_created = 0
            stats_created = 0

            station_cache = {s.station_name: s for s in BusStation.objects.all()}
            route_cache = set(RouteInfo.objects.values_list('route_name', flat=True))

            stats_batch = []

            with transaction.atomic():
                for row in rows:
                    sta_name = row['staname'].strip()
                    line_name = row['linename'].strip()
                    date_hour = row['transactiondate'].strip()
                    in_count = int(row['incount'])
                    out_count = int(row['outcount'])

                    # 解析日期时间
                    parts = date_hour.split()
                    dt = parts[0]
                    hr = int(parts[1]) if len(parts) > 1 else 0

                    # 确保站点存在
                    if sta_name not in station_cache:
                        station_obj, created = BusStation.objects.get_or_create(
                            station_id=f'S_{sta_name}',
                            defaults={
                                'station_name': sta_name,
                                'longitude': 121.47,
                                'latitude': 31.23,
                                'region_type': 'subway',
                            }
                        )
                        station_cache[sta_name] = station_obj
                        if created:
                            stations_created += 1

                    # 确保线路存在
                    if line_name not in route_cache:
                        RouteInfo.objects.get_or_create(
                            route_id=f'R_{line_name}',
                            defaults={'route_name': line_name, 'direction': '上行'}
                        )
                        route_cache.add(line_name)
                        routes_created += 1

                    total = in_count + out_count
                    cong = 'high' if total > 100 else ('medium' if total > 50 else 'low')

                    stats_batch.append(StationFlowStats(
                        station=station_cache[sta_name],
                        date=dt,
                        hour=hr,
                        in_flow=in_count,
                        out_flow=out_count,
                        total_flow=total,
                        congestion_level=cong,
                    ))

                if stats_batch:
                    StationFlowStats.objects.bulk_create(stats_batch, batch_size=500)
                    stats_created = len(stats_batch)

            result.update({
                'stations_created': stations_created,
                'routes_created': routes_created,
                'stats_created': stats_created,
            })

        elif upload_type == 'swipe_record':
            # ===== 刷卡记录 → OD配对 + 出行历史 =====
            required = {'card_id', 'swipe_time', 'station_name', 'line_name', 'swipe_type'}
            if not required.issubset(set(columns)):
                missing = required - set(columns)
                return Response({'status': 'error', 'message': f'缺少必要列: {missing}'}, status=400)

            station_cache = {s.station_name: s for s in BusStation.objects.all()}

            # 按 card_id 和 swipe_time 排序进行 OD 配对
            rows.sort(key=lambda r: (r['card_id'], r['swipe_time']))

            od_agg = {}  # (date, hour, origin, dest) -> {flow, durations}
            travel_batch = []
            od_created = 0
            travel_created = 0
            skipped = 0

            with transaction.atomic():
                # 确保站点存在
                for row in rows:
                    sta = row['station_name'].strip()
                    if sta not in station_cache:
                        obj, created = BusStation.objects.get_or_create(
                            station_id=f'S_{sta}',
                            defaults={
                                'station_name': sta,
                                'longitude': 121.47,
                                'latitude': 31.23,
                                'region_type': 'subway',
                            }
                        )
                        station_cache[sta] = obj

                # OD 配对
                i = 0
                while i < len(rows) - 1:
                    curr = rows[i]
                    nxt = rows[i + 1]

                    if (curr['card_id'] == nxt['card_id']
                        and curr['swipe_type'].strip().lower() == 'in'
                        and nxt['swipe_type'].strip().lower() == 'out'):

                        origin_name = curr['station_name'].strip()
                        dest_name = nxt['station_name'].strip()

                        if origin_name in station_cache and dest_name in station_cache:
                            try:
                                t1 = datetime.strptime(curr['swipe_time'].strip(), '%Y-%m-%d %H:%M:%S')
                                t2 = datetime.strptime(nxt['swipe_time'].strip(), '%Y-%m-%d %H:%M:%S')
                                duration = (t2 - t1).total_seconds() / 60
                                dt = t1.date()
                                hr = t1.hour

                                key = (str(dt), hr, origin_name, dest_name)
                                if key not in od_agg:
                                    od_agg[key] = {'flow': 0, 'durations': []}
                                od_agg[key]['flow'] += 1
                                od_agg[key]['durations'].append(duration)

                                travel_batch.append(UserTravelHistory(
                                    user_id=curr['card_id'].strip(),
                                    origin_station=station_cache[origin_name],
                                    destination_station=station_cache[dest_name],
                                    travel_date=dt,
                                    travel_hour=hr,
                                    duration_min=round(duration, 1),
                                ))
                            except Exception:
                                skipped += 1
                        else:
                            skipped += 1
                        i += 2
                    else:
                        skipped += 1
                        i += 1

                # 写入 OdFlow
                od_batch = []
                for (dt, hr, orig, dest), data in od_agg.items():
                    avg_dur = round(sum(data['durations']) / len(data['durations']), 1) if data['durations'] else 0
                    od_batch.append(OdFlow(
                        date=dt,
                        hour=hr,
                        origin_station=station_cache[orig],
                        destination_station=station_cache[dest],
                        flow_count=data['flow'],
                        trip_duration_avg=avg_dur,
                    ))

                if od_batch:
                    OdFlow.objects.bulk_create(od_batch, batch_size=500)
                    od_created = len(od_batch)

                if travel_batch:
                    UserTravelHistory.objects.bulk_create(travel_batch, batch_size=500)
                    travel_created = len(travel_batch)

            result.update({
                'od_records_created': od_created,
                'travel_records_created': travel_created,
                'skipped_rows': skipped,
            })

        else:
            return Response({'status': 'error', 'message': f'不支持的上传类型: {upload_type}，可选: station_flow, swipe_record'}, status=400)

    except Exception as e:
        import traceback
        return Response({'status': 'error', 'message': f'数据处理失败: {str(e)}', 'detail': traceback.format_exc()}, status=500)

    return Response({'status': 'success', 'message': '数据导入成功', 'result': result})


@api_view(['GET'])
@permission_classes([AllowAny])
def system_overview(request):
    """
    系统总览数据 (首页看板用)
    """
    from django.db.models import Count, Avg
    total_stations = BusStation.objects.count()
    total_routes = RouteInfo.objects.count()
    total_od_records = OdFlow.objects.count()
    total_stat_records = StationFlowStats.objects.count()

    # 获取最新一天的数据概况
    latest_date = StationFlowStats.objects.order_by('-date').values_list('date', flat=True).first()
    daily_flow = 0
    if latest_date:
        daily_flow = StationFlowStats.objects.filter(date=latest_date).aggregate(
            total=Sum('total_flow')
        )['total'] or 0

    return Response({
        'total_stations': total_stations,
        'total_routes': total_routes,
        'total_od_records': total_od_records,
        'total_stat_records': total_stat_records,
        'latest_date': latest_date,
        'latest_daily_flow': daily_flow,
    })
