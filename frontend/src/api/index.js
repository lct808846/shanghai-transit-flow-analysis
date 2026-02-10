import axios from 'axios'
import { useToast } from '@/composables/useToast'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 请求拦截器 - 自动附加 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

// 响应拦截器 - 统一错误处理 + Toast 通知
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const { showError } = useToast()

    if (!error.response) {
      showError('网络连接失败，请检查网络设置')
      return Promise.reject(error)
    }

    const { status: code, data } = error.response
    const message = data?.message || data?.detail || ''

    if (code === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        showError('登录已过期，请重新登录')
        setTimeout(() => { window.location.href = '/login' }, 800)
      }
    } else if (code === 403) {
      showError(message || '权限不足，无法执行此操作')
    } else if (code === 500) {
      showError('服务器内部错误，请稍后重试')
    } else if (code === 400) {
      showError(message || '请求参数有误')
    }

    return Promise.reject(error)
  }
)

// ============ 认证 API ============
export const authLogin = (data) => api.post('/auth/login/', data)
export const authRegister = (data) => api.post('/auth/register/', data)
export const authLogout = () => api.post('/auth/logout/')
export const getProfile = () => api.get('/auth/profile/')
export const updateProfile = (data) => api.put('/auth/profile/', data)
export const changePassword = (data) => api.post('/auth/change-password/', data)
export const getUserList = () => api.get('/auth/users/')
export const updateUserRole = (userId, role) => api.put(`/auth/users/${userId}/role/`, { role })
export const toggleUserActive = (userId) => api.put(`/auth/users/${userId}/toggle/`)

// 系统总览
export const getOverview = () => api.get('/overview/')

// 按小时客流 (支持 date / month / station)
export const getHourlyFlow = (date, month, station) => {
  const params = {}
  if (month) params.month = month
  else if (date) params.date = date
  if (station) params.station = station
  return api.get('/hourly-flow/', { params })
}

// 站点排名 (支持 date 或 month, 返回 total_flow/total_in/total_out)
export const getStationRank = (date, top = 20, month) => {
  const params = { top }
  if (month) params.month = month
  else if (date) params.date = date
  return api.get('/station-rank/', { params })
}

// OD 热门路线 (支持 date 或 month, 可选 origin/destination 筛选)
export const getOdTop = (date, top = 20, month, origin, destination) => {
  const params = { top }
  if (month) params.month = month
  else if (date) params.date = date
  if (origin) params.origin = origin
  if (destination) params.destination = destination
  return api.get('/od-top/', { params })
}

// OD 站点热度统计 (出发/到达维度)
export const getOdStationHeat = (date, month) => {
  const params = {}
  if (month) params.month = month
  else if (date) params.date = date
  return api.get('/od-station-heat/', { params })
}

// 站点客流统计
export const getStationStats = (params) => api.get('/station-stats/', { params })

// 行政区客流聚合
export const getDistrictFlow = (date, month) => {
  const params = {}
  if (month) params.month = month
  else if (date) params.date = date
  return api.get('/district-flow/', { params })
}

// OD 客流
export const getOdFlow = (params) => api.get('/od-flow/', { params })

// 站点列表
export const getStations = () => api.get('/stations/')

// 线路列表
export const getRoutes = () => api.get('/routes/')

// 聚类分析
export const getClusterResults = (params) => api.get('/cluster-results/', { params })
export const getClusterSummary = () => api.get('/cluster-summary/')
export const runClusterAnalysis = (data) => api.post('/run-cluster/', data)

// 地图视图
export const getMapStations = () => api.get('/stations/')
export const getMapCluster = (params) => api.get('/cluster-results/', { params })

// 数据上传 (超时 10 分钟, 大文件后端处理耗时较长)
export const uploadCsv = (formData, onProgress) => api.post('/upload-csv/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 600000,
  onUploadProgress: onProgress,
})

// 智能推荐
export const getRecommendations = (params) => api.get('/recommendations/', { params })
export const getStationList = (search) => api.get('/station-list/', { params: { search } })

export default api
