"""
一次性脚本：为所有 BusStation 补充行政区(district)字段
基于上海地铁站点的真实地理位置映射
"""
import os, sys, django

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transit_system.settings')
django.setup()

from analysis.models import BusStation

# 上海地铁站点 → 行政区 映射 (基于真实地理位置)
DISTRICT_MAP = {
    # 1号线
    "莘庄":       "闵行区",
    "外环路":     "闵行区",
    "莲花路":     "闵行区",
    "锦江乐园":   "徐汇区",
    "上海南站":   "徐汇区",
    "漕宝路":     "徐汇区",
    "上海体育馆": "徐汇区",
    "徐家汇":     "徐汇区",
    "衡山路":     "徐汇区",
    "常熟路":     "静安区",
    "陕西南路":   "黄浦区",
    "黄陂南路":   "黄浦区",
    "人民广场":   "黄浦区",
    "新闸路":     "静安区",
    "汉中路":     "静安区",
    "上海火车站": "静安区",
    "中山北路":   "静安区",
    "延长路":     "静安区",
    "上海马戏城": "静安区",
    "汶水路":     "静安区",
    "彭浦新村":   "静安区",
    # 2号线 (去掉1号线已有的)
    "徐泾东":       "青浦区",
    "虹桥火车站":   "闵行区",
    "虹桥2号航站楼": "闵行区",
    "淞虹路":       "长宁区",
    "北新泾":       "长宁区",
    "威宁路":       "长宁区",
    "娄山关路":     "长宁区",
    "中山公园":     "长宁区",
    "江苏路":       "长宁区",
    "静安寺":       "静安区",
    "南京西路":     "静安区",
    # "人民广场" 已在1号线
    "南京东路":     "黄浦区",
    "陆家嘴":       "浦东新区",
    "东昌路":       "浦东新区",
    "世纪大道":     "浦东新区",
    "上海科技馆":   "浦东新区",
    "世纪公园":     "浦东新区",
    "龙阳路":       "浦东新区",
    "张江高科":     "浦东新区",
    # 10号线 (去掉已有的)
    # "虹桥火车站" 已在2号线
    "虹桥1号航站楼": "闵行区",
    "上海动物园":   "长宁区",
    "龙溪路":       "长宁区",
    "水城路":       "长宁区",
    "伊犁路":       "长宁区",
    "宋园路":       "长宁区",
    "虹桥路":       "长宁区",
    "交通大学":     "徐汇区",
    "上海图书馆":   "徐汇区",
    # "陕西南路" 已在1号线
    "新天地":       "黄浦区",
    "老西门":       "黄浦区",
    "豫园":         "黄浦区",
    # "南京东路" 已在2号线
    "天潼路":       "虹口区",
    "四川北路":     "虹口区",
    "海伦路":       "虹口区",
}


def main():
    updated = 0
    for station_name, district in DISTRICT_MAP.items():
        count = BusStation.objects.filter(station_name=station_name, district__isnull=True).update(district=district)
        if count == 0:
            count = BusStation.objects.filter(station_name=station_name).update(district=district)
        updated += count

    # 兜底：未匹配到的站点
    remaining = BusStation.objects.filter(district__isnull=True).count()
    if remaining > 0:
        BusStation.objects.filter(district__isnull=True).update(district='其他')
        print(f"⚠️  {remaining} 个站点未匹配行政区，已设为'其他'")

    print(f"✅ 已更新 {updated} 个站点的行政区信息")
    # 汇总
    from django.db.models import Count
    summary = BusStation.objects.values('district').annotate(count=Count('station_id')).order_by('-count')
    for row in summary:
        print(f"   {row['district']}: {row['count']} 站")


if __name__ == '__main__':
    main()
