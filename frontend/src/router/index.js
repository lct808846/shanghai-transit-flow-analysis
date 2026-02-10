import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '数据总览', icon: '📊' }
  },
  {
    path: '/time-analysis',
    name: 'TimeAnalysis',
    component: () => import('../views/TimeAnalysis.vue'),
    meta: { title: '时间分析', icon: '⏱️' }
  },
  {
    path: '/space-analysis',
    name: 'SpaceAnalysis',
    component: () => import('../views/SpaceAnalysis.vue'),
    meta: { title: '空间分析', icon: '🗺️' }
  },
  {
    path: '/od-analysis',
    name: 'OdAnalysis',
    component: () => import('../views/OdAnalysis.vue'),
    meta: { title: 'OD分析', icon: '🔀' }
  },
  {
    path: '/cluster-analysis',
    name: 'ClusterAnalysis',
    component: () => import('../views/ClusterAnalysis.vue'),
    meta: { title: '聚类分析', icon: '🎯' }
  },
  {
    path: '/map-view',
    name: 'MapView',
    component: () => import('../views/MapView.vue'),
    meta: { title: '地图视图', icon: '🌐' }
  },
  {
    path: '/recommendations',
    name: 'Recommendations',
    component: () => import('../views/Recommendations.vue'),
    meta: { title: '智能推荐', icon: '🤖' }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/Admin.vue'),
    meta: { title: '系统管理', icon: '⚙️' }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 导航守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  // 需要登录的页面
  if (!to.meta.guest && !token) {
    next('/login')
    return
  }

  // 已登录时访问登录页 -> 跳转首页
  if (to.meta.guest && token) {
    next('/')
    return
  }

  next()
})

export default router
