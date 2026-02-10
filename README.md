# 基于 Spark 的上海市公共交通客流时空分布分析系统

基于 **Apache Spark + Django REST Framework + Vue 3 + ECharts** 的全栈大数据分析平台。采用 Spark 作为分布式数据处理引擎，实现上海市公共交通客流数据的 ETL 清洗、时空可视化、DBSCAN 聚类分析与智能出行推荐。

![Spark](https://img.shields.io/badge/Apache%20Spark-3.5+-E25A1C?logo=apachespark&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js&logoColor=white)
![ECharts](https://img.shields.io/badge/ECharts-6.0-AA344D)
![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?logo=vite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 目录

- [系统架构](#系统架构)
- [功能模块](#功能模块)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [Spark 数据处理](#spark-数据处理)
- [数据模型](#数据模型)
- [API 接口](#api-接口)
- [核心算法](#核心算法)
- [数据说明](#数据说明)
- [部署指南](#部署指南)

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Vue 3 SPA (Vite :5173)                   │
│  总览  │ 时间分析 │ 空间分析 │ OD分析 │ 聚类 │ 地图 │ 推荐 │ 管理 │
├──────────────────────────────────────────────────────────────┤
│              Axios + Vite Proxy (/api → :8000)               │
├──────────────────────────────────────────────────────────────┤
│              Django REST Framework (8000)                     │
│     accounts (认证)  │  analysis (15+ API endpoints)         │
├──────────────────────────────────────────────────────────────┤
│            Apache Spark 分布式数据处理层                       │
│  Spark ETL (数据清洗/OD配对/聚合) │ DBSCAN 聚类 │ 推荐引擎    │
├──────────────────────────────────────────────────────────────┤
│                     SQLite (dev) / PostgreSQL (prod)          │
└──────────────────────────────────────────────────────────────┘
```

四层架构设计：

1. **展示层** — Vue 3 SPA，ECharts 多维度可视化
2. **服务层** — Django REST Framework 提供 RESTful API
3. **计算层** — Apache Spark 承担 ETL 数据清洗、OD 配对、客流聚合等大数据处理任务
4. **存储层** — 关系数据库持久化计算结果

---

## 功能模块

### 数据总览 Dashboard

系统核心指标一览：站点数、线路数、当日客流量，数字滚动动画 + 迷你趋势图。

### 时间分析 TimeAnalysis

按小时/日期维度统计全网客流变化趋势。折线图 + 面积图，高峰时段自动标注，支持日期范围筛选。

### 空间分析 SpaceAnalysis

站点客流排名（Top N）、行政区客流分布、拥挤度热力图。奖牌动画 + 柱状图 + 饼图联动。

### OD 分析 OdAnalysis

热门出行路线 Sankey 图、OD 热力矩阵、站点热度双重对比（发送 / 接收），全部自动加载无需筛选。

### 聚类分析 ClusterAnalysis

交互式 DBSCAN 调参面板（eps / min_samples），前端触发后端实时计算。散点图 + 多维柱状图 + 簇内饼图三联动，5 项统计卡片。

### 地图视图 MapView

上海站点地理分布气泡图，支持聚类着色、热力图、客流流向 3 种图层切换，动态气泡缩放，图层感知统计卡片。

### 智能推荐 Recommendations

选择起终点与出行时段后，系统基于 Z-Score 异常检测 + 余弦相似度实时计算 4 类推荐：
- **最优时段推荐** — Z-Score 识别高峰/低谷，推荐错峰时段
- **起点拥挤分析** — 时序对比 + 百分位排名
- **终点拥挤分析** — 同上，角色为到达站
- **替代路线推荐** — 余弦相似度匹配功能相似但更空闲的替代站点

评分含义：分数越高越适合出行。总评圆环可视化，推荐卡片含全时段柱状图（6:00-22:00 补零）、Z-Score 信息、前后时段对比条形图、替代站点节省率进度条。

### 系统管理 Admin

用户管理、角色分配（管理员/分析师/普通用户）、启用/禁用账号、CSV 数据上传。

### 用户认证 Login

Token 鉴权登录/注册，粒子动画背景，路由守卫自动跳转。

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **大数据处理** | Apache Spark 3.5 (PySpark) | 分布式 ETL：数据清洗、窗口函数 OD 配对、客流聚合 |
| **前端框架** | Vue 3.5 (Composition API) | 无 Pinia/Vuex，用 `reactive()` composables 管理状态 |
| **构建工具** | Vite 6 | HMR + `/api` 代理 → Django 8000 |
| **可视化** | ECharts 6 | 柱状/折线/散点/Sankey/饼图/热力图/气泡图 |
| **HTTP** | Axios | 请求拦截器注入 Token，响应拦截器统一错误处理 |
| **路由** | Vue Router 5 | 懒加载 + 导航守卫 |
| **样式** | SCSS | 全局暗黑科技风主题 (`global.scss`) |
| **后端框架** | Django 5.1 + DRF | RESTful API，Token 认证，`PageNumberPagination(50)` |
| **用户模型** | `accounts.UserProfile` | 继承 `AbstractUser`，角色: admin / analyst / viewer |
| **聚类算法** | scikit-learn DBSCAN | 基于站点经纬度 + 客流量进行空间聚类 |
| **推荐引擎** | NumPy | Z-Score 异常检测 + 余弦相似度 + 加权评分 |
| **数据库** | SQLite (dev) | 生产可切换 PostgreSQL / MySQL |
| **跨域** | django-cors-headers | 开发模式 `CORS_ALLOW_ALL_ORIGINS = True` |

---

## 项目结构

```
Demo/
├── backend/                          # Django 后端
│   ├── accounts/                     # 认证模块
│   │   ├── models.py                 # UserProfile (AbstractUser + 角色) / LoginLog
│   │   ├── views.py                  # 登录/注册/用户管理 8 个端点
│   │   └── urls.py
│   ├── analysis/                     # 核心分析模块
│   │   ├── models.py                 # 9 个模型 (站点/OD/统计/聚类/推荐等)
│   │   ├── views.py                  # 5 个 ViewSet + 13 个函数视图
│   │   ├── serializers.py            # DRF 序列化器
│   │   └── urls.py
│   ├── transit_system/               # Django 项目配置
│   │   ├── settings.py               # zh-hans / Asia-Shanghai / Token Auth
│   │   └── urls.py                   # /api/auth/ + /api/ 路由挂载
│   └── db.sqlite3
│
├── frontend/                         # Vue 3 SPA
│   ├── src/
│   │   ├── views/                    # 9 个页面组件
│   │   │   ├── Dashboard.vue         # 数据总览
│   │   │   ├── TimeAnalysis.vue      # 时间分析
│   │   │   ├── SpaceAnalysis.vue     # 空间分析
│   │   │   ├── OdAnalysis.vue        # OD 分析
│   │   │   ├── ClusterAnalysis.vue   # 聚类分析
│   │   │   ├── MapView.vue           # 地图视图
│   │   │   ├── Recommendations.vue   # 智能推荐
│   │   │   ├── Admin.vue             # 系统管理
│   │   │   └── Login.vue             # 登录/注册
│   │   ├── api/index.js              # Axios 封装 (27 个 API 函数)
│   │   ├── composables/              # useAuth.js / useToast.js
│   │   ├── styles/global.scss        # 暗黑科技风全局主题
│   │   ├── router/index.js           # 9 条路由 + 鉴权守卫
│   │   └── App.vue                   # 侧边栏布局
│   ├── vite.config.js                # @ → src/ 别名 + API 代理
│   └── package.json
│
├── spark_analysis/                   # Spark 大数据处理 & 分析引擎
│   ├── spark_etl.py                  # PySpark 分布式 ETL 主流程
│   ├── init_spark.py                 # SparkSession 初始化与配置
│   ├── etl_process.py                # 轻量 ETL (Pandas 版，用于快速调试)
│   ├── dbscan_clustering.py          # DBSCAN 空间聚类分析
│   ├── recommendation_engine.py      # 智能推荐引擎 (4 策略 × 3 算法)
│   ├── update_station_coords.py      # 站点经纬度更新
│   └── update_district.py            # 行政区信息更新
│
├── data/
│   ├── generate_mock_data.py         # 模拟数据生成 (2 年刷卡记录)
│   └── raw/
│       ├── mock_swipe_records.csv    # 原始刷卡数据
│       └── mock_station_flow.csv     # 站点客流数据
│
├── requirements.txt                  # Python 依赖
└── README.md
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Java 8+（Spark 运行依赖）
- Apache Spark 3.5+ / PySpark
- Node.js 18+
- npm 或 yarn

### 1. 克隆 & 安装依赖

```bash
git clone <repo-url>
cd Demo

# Python 依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install && cd ..
```

### 2. 数据库初始化

```bash
cd backend
python manage.py makemigrations accounts analysis
python manage.py migrate

# 创建管理员账号
python manage.py createsuperuser
# 或使用默认测试账号: admin / admin123
```

### 3. 数据生成 & Spark ETL

```bash
# 生成模拟数据 (如需要)
cd data && python generate_mock_data.py && cd ..

# Spark ETL: 分布式数据清洗 → OD 配对 → 客流聚合 → 写入 DB
cd spark_analysis
python spark_etl.py
# 或使用轻量版 (无需 Spark 环境): python etl_process.py

# DBSCAN 聚类 (地图/聚类页面需要)
python dbscan_clustering.py
```

### 4. 启动服务

```bash
# 后端 (终端 1)
cd backend
python manage.py runserver 0.0.0.0:8000

# 前端 (终端 2)
cd frontend
npm run dev
```

### 5. 访问系统

浏览器打开 `http://localhost:5173`，使用 `admin / admin123` 登录。

---

## Spark 数据处理

### ETL 处理流程

系统采用 PySpark 作为核心 ETL 引擎，处理原始刷卡记录数据：

```
原始刷卡 CSV ──▸ Spark 读取 ──▸ 数据清洗(去重/去空) ──▸ 窗口函数 OD 配对 ──▸ 客流聚合 ──▸ 写入 DB
```

**核心处理步骤：**

| 阶段 | Spark 操作 | 说明 |
|------|-----------|------|
| 数据读取 | `spark.read.csv()` | 读取百万级刷卡记录，自动推断 Schema |
| 数据清洗 | `dropna()` + `dropDuplicates()` | 去除空值与重复记录 |
| OD 配对 | `Window.partitionBy('card_id').orderBy('swipe_time')` | 使用 Spark 窗口函数 `lead()` 按乘客 ID 分区，配对进站/出站记录 |
| 时长计算 | `unix_timestamp` 差值 | 计算每次出行耗时（分钟） |
| 客流聚合 | `groupBy().agg()` | 按日期、时段、站点维度聚合客流量与平均时长 |
| 站点统计 | `join` + `fillna` | 分别统计进站/出站客流后 outer join，计算总客流 |
| 持久化 | `collect()` → Django ORM `bulk_create` | Spark 计算结果收集后批量写入关系数据库 |

### Spark 配置

```python
# spark_analysis/init_spark.py
SparkSession.builder
    .appName("Shanghai Transit ETL")
    .master("local[*]")           # 本地模式，利用全部 CPU 核心
    .config("spark.driver.memory", "2g")
    .config("spark.sql.shuffle.partitions", "4")
    .enableHiveSupport()
    .getOrCreate()
```

开发环境使用 `local[*]` 模式，生产环境可切换为 `yarn` 或 `standalone` 集群模式。同时提供 Pandas 轻量版 (`etl_process.py`) 用于快速调试，两者输出结果一致。

---

## 数据模型

```
BusStation (交通站点)
  ├── station_id (PK)
  ├── station_name / district / region_type
  └── longitude / latitude

OdFlow (OD客流)
  ├── origin_station → BusStation
  ├── destination_station → BusStation
  ├── date / hour / flow_count / trip_duration_avg
  └── unique_together: (date, hour, origin, destination)

StationFlowStats (站点客流统计)
  ├── station → BusStation
  ├── date / hour
  ├── in_flow / out_flow / total_flow
  └── congestion_level (low / medium / high)

ClusterResult (聚类结果)
  ├── station → BusStation
  ├── cluster_label / is_hotspot
  └── eps / min_samples / analysis_date

RouteInfo (线路信息) ←→ RouteStation (线路站点关联)

UserTravelHistory (出行历史)
Recommendation (推荐结果, JSONField metadata)
AnalysisReport (分析报告)

UserProfile (用户, extends AbstractUser)
  ├── role: admin / analyst / viewer
  └── phone / department / avatar_url / last_login_ip

LoginLog (登录日志)
```

---

## API 接口

### 认证 `/api/auth/`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `register/` | 用户注册 | 公开 |
| POST | `login/` | 登录，返回 Token | 公开 |
| POST | `logout/` | 退出登录 | 已登录 |
| GET/PUT | `profile/` | 个人信息查看/修改 | 已登录 |
| POST | `change-password/` | 修改密码 | 已登录 |
| GET | `users/` | 用户列表 | 管理员 |
| PUT | `users/<id>/role/` | 修改用户角色 | 管理员 |
| PUT | `users/<id>/toggle/` | 启用/禁用用户 | 管理员 |

### 数据分析 `/api/`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `overview/` | 系统总览指标 | — |
| GET | `hourly-flow/` | 小时客流汇总 | `date`, `month`, `station` |
| GET | `station-rank/` | 站点客流排名 | `date`, `top`, `month` |
| GET | `district-flow/` | 行政区客流 | `date`, `month` |
| GET | `od-top/` | 热门 OD 路线 | `date`, `top`, `month`, `origin`, `dest` |
| GET | `od-station-heat/` | OD 站点热度 | `date`, `month` |
| GET | `stations/` | 站点 CRUD | 分页已关闭，返回全部 |
| GET | `station-stats/` | 站点统计 | 分页 50/页 |
| GET | `od-flow/` | OD 明细 | 分页 50/页 |
| GET | `routes/` | 线路列表 | — |
| GET | `station-list/` | 轻量站点列表 | `search` |

### 聚类 & 推荐 `/api/`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `cluster-results/` | 聚类结果 | `eps`, `min_samples` |
| GET | `cluster-summary/` | 聚类摘要统计 | — |
| POST | `run-cluster/` | 触发 DBSCAN 实时聚类 | `{ eps, min_samples }` |
| GET | `recommendations/` | 智能推荐 (实时计算) | `origin`, `dest`, `hour` |
| GET | `active-users/` | 活跃用户列表 | — |
| POST | `upload-csv/` | CSV 数据上传 | `multipart/form-data` |

---

## 核心算法

### Spark 分布式 ETL

使用 PySpark DataFrame API 处理原始刷卡数据。关键技术点：
- **窗口函数** (`Window.partitionBy().orderBy()`) — 按乘客分区排序，使用 `lead()` 实现相邻记录配对，避免 shuffle join
- **分布式聚合** (`groupBy().agg()`) — 按时间/空间维度并行聚合，支持百万级记录处理
- **自动 Schema 推断** — `inferSchema=True` 自动识别数据类型，减少预处理代码

### DBSCAN 空间聚类

基于站点经纬度，使用 `sklearn.cluster.DBSCAN` 对 55 个站点进行密度聚类。前端可交互调参 `eps`（邻域半径）和 `min_samples`（最小样本数），后端实时计算并返回聚类标签与热点标记。

### Z-Score 异常检测（推荐引擎）

对 OD 对或站点的全天各时段客流序列进行标准化：

$$Z_i = \frac{x_i - \mu}{\sigma}$$

- $Z > 0.8$ → 高峰时段（红色标记）
- $Z < -0.3$ → 推荐时段（绿色标记）
- 用户选择的时段 Z 值越低，出行适宜度评分越高

### 余弦相似度（替代路线）

构建目的站全天客流特征向量，与其他站点计算余弦相似度：

$$\text{sim}(\mathbf{a}, \mathbf{b}) = \frac{\mathbf{a} \cdot \mathbf{b}}{|\mathbf{a}||\mathbf{b}|}$$

筛选相似度 > 0.7 且当前时段更空闲的站点作为替代推荐。

### 加权评分模型

所有推荐结果通过加权评分排序，分数含义：**越高越适合出行**。

$$\text{score} = \frac{\sum v_i \times w_i}{\sum w_i}$$

---

## 数据说明

| 数据 | 说明 |
|------|------|
| `mock_swipe_records.csv` | 模拟刷卡记录（card_id, station_name, swipe_type, swipe_time） |
| `mock_station_flow.csv` | 站点客流统计原始数据 |
| **55 个站点** | 上海真实地铁站名称与经纬度坐标 |
| **Spark ETL** | 刷卡数据 → Spark 清洗 → 窗口函数 OD 配对 → 分布式聚合 → 写入 DB |
| **执行顺序** | `generate_mock_data.py` → `spark_etl.py` → `dbscan_clustering.py` |

---

## 部署指南

### 开发环境

默认 SQLite + Vite 代理，安装依赖后开箱即用。

### 生产环境

```bash
# 前端构建
cd frontend && npm run build   # 输出到 dist/

# 环境变量
export DJANGO_SECRET_KEY="your-production-secret"
export DJANGO_DEBUG=False
```

**建议配置：**

| 组件 | 生产推荐 |
|------|---------|
| 前端托管 | Nginx 托管 `dist/` 静态文件 |
| API 反代 | Nginx → Gunicorn/uWSGI :8000 |
| 数据库 | PostgreSQL / MySQL |
| CORS | 配置 `CORS_ALLOWED_ORIGINS` 白名单 |
| HTTPS | Let's Encrypt + Nginx SSL |
| 静态文件 | `python manage.py collectstatic` |

```nginx
# Nginx 参考配置
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 许可证

MIT License
