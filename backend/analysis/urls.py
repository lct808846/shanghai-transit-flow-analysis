from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'stations', views.BusStationViewSet)
router.register(r'od-flow', views.OdFlowViewSet)
router.register(r'station-stats', views.StationFlowStatsViewSet)
router.register(r'routes', views.RouteInfoViewSet)
router.register(r'reports', views.AnalysisReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # 聚合统计接口
    path('hourly-flow/', views.hourly_flow_summary, name='hourly-flow'),
    path('station-rank/', views.station_flow_rank, name='station-rank'),
    path('district-flow/', views.district_flow, name='district-flow'),
    path('od-top/', views.od_top_routes, name='od-top'),
    path('od-station-heat/', views.od_station_heat, name='od-station-heat'),
    path('overview/', views.system_overview, name='overview'),
    # 聚类分析接口
    path('cluster-results/', views.cluster_results, name='cluster-results'),
    path('cluster-summary/', views.cluster_summary, name='cluster-summary'),
    path('run-cluster/', views.run_cluster_analysis, name='run-cluster'),
    # 数据上传
    path('upload-csv/', views.upload_csv, name='upload-csv'),
    # 推荐接口
    path('recommendations/', views.get_recommendations, name='recommendations'),
    path('station-list/', views.get_station_list, name='station-list'),
    path('active-users/', views.get_active_users, name='active-users'),
]
