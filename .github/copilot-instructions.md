# Copilot Instructions — 上海公共交通客流分析系统

## Architecture Overview

Three-tier monorepo: **Django REST backend** (`backend/`) + **Vue 3 SPA frontend** (`frontend/`) + **standalone data scripts** (`spark_analysis/`). SQLite dev database; Vite proxies `/api` → Django `127.0.0.1:8000`.

- `backend/analysis/` — core domain: transit stations, OD flows, station stats, DBSCAN clustering, recommendations (15+ API endpoints)
- `backend/accounts/` — auth & user management with custom user model `accounts.UserProfile` (extends `AbstractUser`, roles: admin/analyst/viewer)
- `frontend/src/views/` — one Vue SFC per page, all use ECharts for visualization
- `spark_analysis/` — offline scripts that bootstrap `django.setup()` to write directly into the DB via Django ORM

## Key Conventions

### Backend (Django + DRF)
- **Custom user model**: `AUTH_USER_MODEL = 'accounts.UserProfile'` — always reference `UserProfile`, never `django.contrib.auth.User`
- **Auth**: Token-based (`rest_framework.authtoken`). Default permission is `IsAuthenticated`. Use `@permission_classes([AllowAny])` explicitly for public endpoints.
- **API response pattern**: All auth endpoints return `{ status, message, data: { token, user } }`. Analysis endpoints use DRF serializers directly or return custom dicts for aggregation views.
- **ViewSets vs function views**: CRUD resources use `ReadOnlyModelViewSet` with DRF router; aggregation/action endpoints use `@api_view` decorators. See `analysis/urls.py` for the split.
- **Queryset filtering**: Implemented inline via `get_queryset()` with `request.query_params`, not django-filter. Keep this pattern consistent.
- **Bulk operations**: Use `bulk_create()` with batch_size=500 for large data inserts (see `etl_process.py`).
- **Locale**: `LANGUAGE_CODE = 'zh-hans'`, `TIME_ZONE = 'Asia/Shanghai'`. Model verbose_name uses Chinese.

### Frontend (Vue 3 + Vite)
- **Composition API only** — no Options API. State managed via `reactive()` composables (`composables/useAuth.js`, `useToast.js`), no Pinia/Vuex.
- **API layer**: All HTTP calls go through `src/api/index.js` which creates an Axios instance with interceptors for token injection and error handling. Add new API functions here as named exports.
- **Routing**: Lazy-loaded routes in `router/index.js`. Auth guard checks `localStorage.getItem('token')`. Pages needing no auth set `meta: { guest: true }`.
- **Path alias**: `@` → `src/` (configured in `vite.config.js`).
- **Styling**: Global dark theme in `styles/global.scss`. Use SCSS, not plain CSS.
- **Charts**: ECharts 6 — import from `echarts` package. Each view initializes charts in `onMounted` with resize handling.

### Data Pipeline (`spark_analysis/`)
- Scripts bootstrap Django with `sys.path.append(...)` + `django.setup()` to reuse ORM models.
- **ETL flow**: `etl_process.py` reads `data/raw/mock_swipe_records.csv` → computes OD pairs → writes `OdFlow` + `StationFlowStats` to DB.
- **Clustering**: `dbscan_clustering.py` uses scikit-learn DBSCAN on station coords, saves to `ClusterResult`.
- **Recommendations**: `recommendation_engine.py` implements Z-Score anomaly detection + cosine similarity for 3 recommendation types (avoid/time/route).
- Run ETL before clustering; run clustering before map/cluster views show data.

## Dev Workflow

```bash
# Backend
cd backend && python manage.py runserver 0.0.0.0:8000

# Frontend (separate terminal)
cd frontend && npm run dev          # Vite on :5173, proxies /api → :8000

# Data pipeline (run once or after data changes)
cd spark_analysis && python etl_process.py && python dbscan_clustering.py
```

## Critical Patterns

- **Adding a new API endpoint**: Define model in `analysis/models.py` → serializer in `serializers.py` → view in `views.py` → route in `urls.py` → frontend function in `api/index.js` → call from Vue view.
- **Adding a new page**: Create `views/NewPage.vue` → add route in `router/index.js` → add nav entry in `App.vue` sidebar.
- **DBSCAN is triggerable from frontend**: `POST /api/run-cluster/` with `{ eps, min_samples }` calls the clustering logic inline — see `views.run_cluster_analysis`.
- **Recommendation generation**: Triggered via API, results stored in `Recommendation` model with `metadata` JSONField for flexible algorithm-specific data.
