<template>
  <div class="admin-page">
    <!-- 权限检查 -->
    <div v-if="!isAdmin()" class="no-access glass-card">
      <span class="no-icon">🔒</span>
      <h3>权限不足</h3>
      <p>仅管理员可访问此页面</p>
    </div>

    <template v-else>
      <!-- 系统概览卡片 -->
      <div class="overview-row">
        <div class="overview-card glass-card" v-for="card in overviewCards" :key="card.label">
          <div class="ov-icon" :style="{ background: card.bg }">{{ card.icon }}</div>
          <div class="ov-info">
            <div class="ov-value">{{ formatNum(card.value) }}</div>
            <div class="ov-label">{{ card.label }}</div>
          </div>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="tab-bar glass-card">
        <button
          v-for="tab in tabs" :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          {{ tab.label }}
        </button>
      </div>

      <!-- ====== Tab: 用户管理 ====== -->
      <div v-show="activeTab === 'users'" class="tab-content">
        <div class="user-management glass-card">
          <div class="section-header">
            <h3><span class="dot"></span>用户管理</h3>
            <span class="user-count">共 {{ users.length }} 个用户</span>
          </div>
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>用户名</th>
                  <th>邮箱</th>
                  <th>手机号</th>
                  <th>部门</th>
                  <th>角色</th>
                  <th>状态</th>
                  <th>注册时间</th>
                  <th>最后登录</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in users" :key="u.id" :class="{ 'row-disabled': !u.is_active }">
                  <td class="id-cell">{{ u.id }}</td>
                  <td class="name-cell">
                    <span class="avatar-mini">{{ u.username[0].toUpperCase() }}</span>
                    {{ u.username }}
                  </td>
                  <td>{{ u.email || '—' }}</td>
                  <td>{{ u.phone || '—' }}</td>
                  <td>{{ u.department || '—' }}</td>
                  <td>
                    <select class="role-select" :value="u.role" @change="handleRoleChange(u, $event)" :disabled="u.id === currentUser?.id">
                      <option value="admin">管理员</option>
                      <option value="analyst">分析师</option>
                      <option value="viewer">普通用户</option>
                    </select>
                  </td>
                  <td>
                    <span :class="['status-tag', u.is_active ? 'active' : 'disabled']">
                      {{ u.is_active ? '✅ 正常' : '🚫 禁用' }}
                    </span>
                  </td>
                  <td class="time-cell">{{ formatDate(u.date_joined) }}</td>
                  <td class="time-cell">{{ u.last_login ? formatDate(u.last_login) : '从未' }}</td>
                  <td>
                    <button class="action-btn" :class="u.is_active ? 'btn-danger' : 'btn-success'" @click="handleToggle(u)" :disabled="u.id === currentUser?.id">
                      {{ u.is_active ? '禁用' : '启用' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- ====== Tab: 数据上传 ====== -->
      <div v-show="activeTab === 'upload'" class="tab-content">
        <div class="upload-section">
          <!-- 上传类型选择 -->
          <div class="upload-types">
            <div
              v-for="ut in uploadTypes" :key="ut.key"
              class="upload-type-card glass-card"
              :class="{ selected: uploadType === ut.key }"
              @click="uploadType = ut.key"
            >
              <div class="ut-icon">{{ ut.icon }}</div>
              <div class="ut-info">
                <div class="ut-name">{{ ut.name }}</div>
                <div class="ut-desc">{{ ut.desc }}</div>
              </div>
              <div class="ut-check" v-if="uploadType === ut.key">✓</div>
            </div>
          </div>

          <!-- 文件选择 + 上传 -->
          <div class="upload-area glass-card">
            <div
              class="drop-zone"
              :class="{ dragging: isDragging, 'has-file': selectedFile }"
              @dragenter.prevent="isDragging = true"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="handleDrop"
              @click="triggerFileInput"
            >
              <input type="file" ref="fileInput" accept=".csv" style="display:none" @change="handleFileSelect" />
              <template v-if="!selectedFile">
                <div class="drop-icon">📂</div>
                <div class="drop-text">拖拽 CSV 文件到此处，或 <span class="link">点击选择文件</span></div>
                <div class="drop-hint">支持 .csv 格式，最大 200MB</div>
              </template>
              <template v-else>
                <div class="file-preview">
                  <div class="file-icon">📄</div>
                  <div class="file-info">
                    <div class="file-name">{{ selectedFile.name }}</div>
                    <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
                  </div>
                  <button class="file-remove" @click.stop="clearFile">✕</button>
                </div>
              </template>
            </div>

            <!-- 列格式说明 -->
            <div class="format-hint">
              <div class="format-title">📋 {{ currentFormatHint.title }}</div>
              <div class="format-cols">
                <span class="col-tag" v-for="col in currentFormatHint.columns" :key="col">{{ col }}</span>
              </div>
              <div class="format-example">示例: {{ currentFormatHint.example }}</div>
            </div>

            <!-- 上传按钮 + 进度 -->
            <div class="upload-actions">
              <button class="upload-btn" :disabled="!canUpload || uploading" @click="handleUpload">
                <span v-if="uploading" class="spinner"></span>
                <span v-else>🚀</span>
                {{ uploading ? `上传中 ${uploadProgress}%` : '开始上传' }}
              </button>
            </div>

            <!-- 上传进度条 -->
            <div class="progress-bar-wrap" v-if="uploading">
              <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
            </div>

            <!-- 上传结果 -->
            <div class="upload-result glass-card" v-if="uploadResult" :class="uploadResult.status">
              <div class="result-header">
                <span class="result-icon">{{ uploadResult.status === 'success' ? '✅' : '❌' }}</span>
                <span class="result-title">{{ uploadResult.message }}</span>
              </div>
              <div class="result-detail-text" v-if="uploadResult.detail">
                <p>{{ uploadResult.detail }}</p>
              </div>
              <div class="result-details" v-if="uploadResult.result">
                <div class="result-item" v-for="(val, key) in uploadResult.result" :key="key">
                  <span class="result-key">{{ resultLabel(key) }}</span>
                  <span class="result-val">{{ Array.isArray(val) ? val.join(', ') : val }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 上传历史 -->
          <div class="upload-history glass-card" v-if="uploadHistory.length">
            <div class="section-header">
              <h3><span class="dot info"></span>本次会话上传记录</h3>
            </div>
            <div class="history-list">
              <div class="history-item" v-for="(h, idx) in uploadHistory" :key="idx" :class="h.status">
                <span class="h-time">{{ h.time }}</span>
                <span class="h-type">{{ h.typeName }}</span>
                <span class="h-file">{{ h.fileName }}</span>
                <span class="h-result">{{ h.summary }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== Tab: 系统信息 ====== -->
      <div v-show="activeTab === 'system'" class="tab-content">
        <div class="sys-info-grid">
          <div class="sys-card glass-card">
            <div class="section-header">
              <h3><span class="dot info"></span>数据库概况</h3>
            </div>
            <div class="info-list">
              <div class="info-row" v-for="item in dbInfo" :key="item.label">
                <span class="info-label">{{ item.label }}</span>
                <span class="info-value">{{ item.value }}</span>
              </div>
            </div>
          </div>

          <div class="sys-card glass-card">
            <div class="section-header">
              <h3><span class="dot warn"></span>快捷操作</h3>
            </div>
            <div class="quick-actions">
              <button class="qa-btn" @click="handleRunETL" :disabled="actionLoading.etl">
                <span>📥</span> {{ actionLoading.etl ? '运行中...' : '重新运行 ETL' }}
              </button>
              <button class="qa-btn" @click="handleRunCluster" :disabled="actionLoading.cluster">
                <span>🎯</span> {{ actionLoading.cluster ? '运行中...' : '执行聚类分析' }}
              </button>
              <button class="qa-btn" @click="handleRefreshData" :disabled="actionLoading.refresh">
                <span>🔄</span> {{ actionLoading.refresh ? '刷新中...' : '刷新数据' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'
import {
  getUserList, updateUserRole, toggleUserActive,
  getOverview, runClusterAnalysis, uploadCsv
} from '../api'

const { isAdmin, getUser } = useAuth()
const currentUser = computed(() => getUser())

// ========== Tab 管理 ==========
const activeTab = ref('users')
const tabs = [
  { key: 'users', label: '用户管理', icon: '👥' },
  { key: 'upload', label: '数据上传', icon: '📤' },
  { key: 'system', label: '系统信息', icon: '⚙️' },
]

// ========== 概览数据 ==========
const users = ref([])
const overview = ref({})
const actionLoading = reactive({ etl: false, cluster: false, refresh: false })

const overviewCards = computed(() => [
  { icon: '👥', label: '注册用户', value: users.value.length, bg: 'rgba(99,102,241,0.12)' },
  { icon: '📍', label: '站点总数', value: overview.value.total_stations || 0, bg: 'rgba(6,182,212,0.12)' },
  { icon: '🔀', label: 'OD记录', value: overview.value.total_od_records || 0, bg: 'rgba(16,185,129,0.12)' },
  { icon: '📊', label: '统计记录', value: overview.value.total_stat_records || 0, bg: 'rgba(245,158,11,0.12)' },
])

const dbInfo = computed(() => [
  { label: '站点数', value: overview.value.total_stations || 0 },
  { label: '线路数', value: overview.value.total_routes || 0 },
  { label: 'OD 记录', value: formatNum(overview.value.total_od_records || 0) },
  { label: '客流统计', value: formatNum(overview.value.total_stat_records || 0) },
  { label: '最新数据日期', value: overview.value.latest_date || '—' },
  { label: '当日总客流', value: formatNum(overview.value.latest_daily_flow || 0) },
])

// ========== 上传相关 ==========
const uploadType = ref('station_flow')
const selectedFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref(null)
const uploadHistory = ref([])
const isDragging = ref(false)
const fileInput = ref(null)

const uploadTypes = [
  {
    key: 'station_flow',
    icon: '🚉',
    name: '站点客流数据',
    desc: '按小时聚合的站点进出站客流量 → 站点/线路/客流统计',
  },
  {
    key: 'swipe_record',
    icon: '💳',
    name: '刷卡记录数据',
    desc: '原始刷卡记录 → OD配对/出行历史/客流统计',
  },
]

const formatHints = {
  station_flow: {
    title: '站点客流格式要求',
    columns: ['transactiondate', 'incount', 'staname', 'linename', 'outcount'],
    example: '2025-05-01 08, 45, 人民广场, 轨道交通1号线, 38',
  },
  swipe_record: {
    title: '刷卡记录格式要求',
    columns: ['card_id', 'swipe_time', 'station_name', 'line_name', 'swipe_type'],
    example: 'CARD_000001, 2025-05-01 08:15:00, 人民广场, 轨道交通1号线, in',
  },
}

const currentFormatHint = computed(() => formatHints[uploadType.value])
const canUpload = computed(() => selectedFile.value && uploadType.value)

const resultLabels = {
  total_rows: '总行数',
  columns: '识别列名',
  stations_created: '新建站点',
  routes_created: '新建线路',
  stats_created: '客流记录',
  od_records_created: 'OD 记录',
  travel_records_created: '出行历史',
  skipped_rows: '跳过行数',
}
function resultLabel(key) { return resultLabels[key] || key }

function formatNum(n) {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toLocaleString()
}

function formatDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function triggerFileInput() { fileInput.value?.click() }

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (file) { selectedFile.value = file; uploadResult.value = null }
}

function handleDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.name.endsWith('.csv')) {
    selectedFile.value = file
    uploadResult.value = null
  }
}

function clearFile() {
  selectedFile.value = null
  uploadResult.value = null
  if (fileInput.value) fileInput.value.value = ''
}

async function handleUpload() {
  if (!canUpload.value) return
  uploading.value = true
  uploadProgress.value = 0
  uploadResult.value = null

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('type', uploadType.value)

  try {
    const res = await uploadCsv(formData, (e) => {
      if (e.lengthComputable) uploadProgress.value = Math.round((e.loaded / e.total) * 100)
    })
    uploadResult.value = res.data
    uploadHistory.value.unshift({
      time: new Date().toLocaleTimeString('zh-CN'),
      typeName: uploadTypes.find(t => t.key === uploadType.value)?.name,
      fileName: selectedFile.value.name,
      summary: `✅ ${res.data.result?.total_rows || 0} 行数据处理完成`,
      status: 'success',
    })
    // 刷新概览数据
    fetchData()
  } catch (e) {
    let msg = '上传失败'
    let detail = ''
    if (!e.response) {
      // 网络错误 / 超时
      if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
        msg = '上传超时：服务器处理时间过长'
        detail = '建议：文件过大时请使用 ETL 脚本导入，或拆分文件后上传'
      } else {
        msg = '网络连接失败'
        detail = '请检查后端服务是否正常运行 (http://localhost:8000)'
      }
    } else {
      const { status: code, data } = e.response
      msg = data?.message || `服务器错误 (HTTP ${code})`
      if (code === 413) {
        msg = '文件过大，超出服务器限制'
        detail = '请在 Django settings.py 中增大 DATA_UPLOAD_MAX_MEMORY_SIZE'
      } else if (code === 403) {
        msg = '权限不足：仅管理员可上传数据'
        detail = '请确认当前账号角色为 admin'
      } else if (code === 401) {
        msg = '登录已过期，请重新登录'
      } else if (code === 500) {
        detail = data?.detail || '后端处理异常，请查看服务器终端日志'
      } else if (code === 400) {
        detail = data?.detail || ''
      }
    }
    uploadResult.value = { status: 'error', message: msg, detail: detail }
    uploadHistory.value.unshift({
      time: new Date().toLocaleTimeString('zh-CN'),
      typeName: uploadTypes.find(t => t.key === uploadType.value)?.name,
      fileName: selectedFile.value.name,
      summary: `❌ ${msg}`,
      status: 'error',
    })
  } finally {
    uploading.value = false
  }
}

// ========== 数据加载 ==========
async function fetchData() {
  try {
    const [usersRes, overviewRes] = await Promise.all([
      getUserList(),
      getOverview(),
    ])
    users.value = usersRes.data.data || usersRes.data
    overview.value = overviewRes.data
  } catch (e) {
    console.error('获取管理数据失败:', e)
  }
}

async function handleRoleChange(user, event) {
  const newRole = event.target.value
  try {
    await updateUserRole(user.id, newRole)
    user.role = newRole
  } catch (e) {
    event.target.value = user.role
  }
}

async function handleToggle(user) {
  try {
    await toggleUserActive(user.id)
    user.is_active = !user.is_active
  } catch (e) { console.error('操作失败:', e) }
}

async function handleRunETL() {
  actionLoading.etl = true
  setTimeout(() => { actionLoading.etl = false; alert('ETL 任务请通过命令行执行') }, 1500)
}

async function handleRunCluster() {
  actionLoading.cluster = true
  try {
    await runClusterAnalysis({ eps: 0.012, min_samples: 2, date: '2025-05-01' })
    alert('聚类分析完成！')
    fetchData()
  } catch (e) {
    alert('聚类失败')
  } finally { actionLoading.cluster = false }
}

async function handleRefreshData() {
  actionLoading.refresh = true
  try {
    await fetchData()
  } finally { actionLoading.refresh = false }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.no-access {
  padding: 60px; text-align: center;
  .no-icon { font-size: 48px; display: block; margin-bottom: 16px; }
  h3 { color: #e2e8f0; font-size: 20px; margin-bottom: 8px; }
  p { color: #64748b; font-size: 14px; }
}

// ========== 概览 ==========
.overview-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
}

.overview-card {
  padding: 20px; display: flex; align-items: center; gap: 16px;
  transition: transform 0.3s ease;
  &:hover { transform: translateY(-3px); }

  .ov-icon {
    width: 48px; height: 48px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
  }
  .ov-value {
    font-size: 24px; font-weight: 700;
    background: linear-gradient(135deg, #6366f1, #06b6d4);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .ov-label { font-size: 12px; color: #94a3b8; margin-top: 2px; }
}

// ========== Tab 栏 ==========
.tab-bar {
  display: flex; gap: 4px; padding: 6px;
}

.tab-btn {
  flex: 1; padding: 10px 16px;
  background: transparent; border: none; border-radius: 10px;
  color: #64748b; font-size: 13px; font-weight: 500;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: all 0.25s ease;

  .tab-icon { font-size: 16px; }

  &:hover { color: #94a3b8; background: rgba(99,102,241,0.05); }

  &.active {
    background: rgba(99,102,241,0.12);
    color: #818cf8; font-weight: 600;
    box-shadow: 0 2px 8px rgba(99,102,241,0.15);
  }
}

// ========== 用户管理 ==========
.user-management { padding: 20px; }

.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
  h3 {
    font-size: 15px; color: #e2e8f0;
    display: flex; align-items: center; gap: 8px;
  }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    display: inline-block; background: #6366f1;
    &.info { background: #06b6d4; }
    &.warn { background: #f59e0b; }
  }
  .user-count { font-size: 12px; color: #64748b; }
}

.table-wrapper {
  overflow-x: auto; border-radius: 8px;
  &::-webkit-scrollbar { height: 4px; }
  &::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 2px; }

  table {
    width: 100%; border-collapse: collapse; white-space: nowrap;

    thead th {
      padding: 10px 14px; text-align: left;
      font-size: 11px; color: #94a3b8;
      text-transform: uppercase; letter-spacing: 0.5px;
      background: rgba(13,18,51,0.95);
      border-bottom: 1px solid rgba(99,102,241,0.1);
      position: sticky; top: 0; z-index: 1;
    }

    tbody tr {
      border-bottom: 1px solid rgba(99,102,241,0.05);
      transition: background 0.2s;
      &:hover { background: rgba(99,102,241,0.04); }
      &.row-disabled { opacity: 0.5; }
    }

    td { padding: 10px 14px; font-size: 13px; color: #cbd5e1; }
    .id-cell { font-family: monospace; color: #64748b; }
    .time-cell { font-size: 12px; color: #64748b; }
    .name-cell {
      display: flex; align-items: center; gap: 8px;
      font-weight: 500; color: #e2e8f0;
    }
  }
}

.avatar-mini {
  width: 26px; height: 26px; border-radius: 6px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: white;
}

.role-select {
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.15);
  border-radius: 6px; padding: 4px 8px;
  color: #e2e8f0; font-size: 12px;
  cursor: pointer; outline: none;
  &:focus { border-color: rgba(99,102,241,0.5); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
  option { background: #0d1233; color: #e2e8f0; }
}

.status-tag {
  font-size: 11px; padding: 3px 10px; border-radius: 12px;
  &.active { background: rgba(16,185,129,0.1); color: #10b981; }
  &.disabled { background: rgba(239,68,68,0.1); color: #ef4444; }
}

.action-btn {
  padding: 4px 14px; border: none; border-radius: 6px;
  font-size: 11px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
  &.btn-danger { background: rgba(239,68,68,0.1); color: #ef4444; &:hover { background: rgba(239,68,68,0.2); } }
  &.btn-success { background: rgba(16,185,129,0.1); color: #10b981; &:hover { background: rgba(16,185,129,0.2); } }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

// ========== 数据上传 ==========
.upload-section {
  display: flex; flex-direction: column; gap: 16px;
}

.upload-types {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
}

.upload-type-card {
  padding: 18px 20px; display: flex; align-items: center; gap: 14px;
  cursor: pointer; transition: all 0.25s; position: relative;
  border: 1px solid transparent;

  &:hover { border-color: rgba(99,102,241,0.2); }

  &.selected {
    border-color: rgba(99,102,241,0.4);
    background: rgba(99,102,241,0.06);
    box-shadow: 0 0 0 1px rgba(99,102,241,0.15);
  }

  .ut-icon { font-size: 28px; flex-shrink: 0; }
  .ut-name { font-size: 14px; font-weight: 600; color: #e2e8f0; }
  .ut-desc { font-size: 12px; color: #64748b; margin-top: 3px; line-height: 1.5; }
  .ut-check {
    position: absolute; top: 10px; right: 12px;
    width: 22px; height: 22px; border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white; font-size: 12px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }
}

.upload-area {
  padding: 24px;
}

.drop-zone {
  border: 2px dashed rgba(99,102,241,0.2);
  border-radius: 12px; padding: 40px 20px;
  text-align: center; cursor: pointer;
  transition: all 0.3s ease;

  &:hover, &.dragging {
    border-color: rgba(99,102,241,0.5);
    background: rgba(99,102,241,0.04);
  }

  &.has-file {
    border-style: solid;
    border-color: rgba(99,102,241,0.3);
    padding: 16px 20px;
  }

  .drop-icon { font-size: 36px; margin-bottom: 10px; }
  .drop-text { font-size: 14px; color: #94a3b8; .link { color: #818cf8; text-decoration: underline; cursor: pointer; } }
  .drop-hint { font-size: 12px; color: #4a5568; margin-top: 6px; }

  .file-preview {
    display: flex; align-items: center; gap: 12px; text-align: left;
    .file-icon { font-size: 28px; }
    .file-info { flex: 1; }
    .file-name { font-size: 14px; color: #e2e8f0; font-weight: 500; }
    .file-size { font-size: 12px; color: #64748b; margin-top: 2px; }
    .file-remove {
      width: 28px; height: 28px; border-radius: 6px;
      background: rgba(239,68,68,0.1); border: none;
      color: #ef4444; font-size: 14px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.2s;
      &:hover { background: rgba(239,68,68,0.2); }
    }
  }
}

.format-hint {
  margin-top: 16px; padding: 14px 18px;
  background: rgba(99,102,241,0.04);
  border: 1px solid rgba(99,102,241,0.08);
  border-radius: 10px;

  .format-title { font-size: 13px; color: #94a3b8; margin-bottom: 8px; }
  .format-cols {
    display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px;
    .col-tag {
      padding: 3px 10px; border-radius: 6px;
      background: rgba(99,102,241,0.1); color: #818cf8;
      font-size: 12px; font-family: monospace;
    }
  }
  .format-example { font-size: 11px; color: #4a5568; font-family: monospace; }
}

.upload-actions {
  margin-top: 16px; display: flex; justify-content: flex-end;
}

.upload-btn {
  padding: 10px 28px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none; border-radius: 10px; color: white;
  font-size: 14px; font-weight: 600; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(99,102,241,0.3);

  &:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.4); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
  .spinner {
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white; border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.progress-bar-wrap {
  margin-top: 12px; height: 4px; border-radius: 2px;
  background: rgba(99,102,241,0.1); overflow: hidden;

  .progress-bar {
    height: 100%; border-radius: 2px;
    background: linear-gradient(90deg, #6366f1, #06b6d4);
    transition: width 0.3s ease;
  }
}

.upload-result {
  margin-top: 16px; padding: 16px 20px;

  &.success { border-left: 3px solid #10b981; }
  &.error { border-left: 3px solid #ef4444; }

  .result-header {
    display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
    .result-icon { font-size: 18px; }
    .result-title { font-size: 14px; font-weight: 600; color: #e2e8f0; }
  }

  .result-detail-text {
    margin-bottom: 10px;
    p {
      font-size: 12px; color: #f59e0b;
      line-height: 1.6; margin: 0;
      padding: 8px 12px; border-radius: 6px;
      background: rgba(245,158,11,0.06);
      border-left: 2px solid rgba(245,158,11,0.3);
    }
  }

  .result-details {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px;
    .result-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 8px 12px; border-radius: 6px;
      background: rgba(99,102,241,0.04);
      .result-key { font-size: 12px; color: #94a3b8; }
      .result-val { font-size: 13px; font-weight: 600; color: #e2e8f0; font-family: monospace; }
    }
  }
}

.upload-history {
  padding: 20px;
}

.history-list {
  display: flex; flex-direction: column; gap: 6px;
}

.history-item {
  display: flex; align-items: center; gap: 16px;
  padding: 10px 14px; border-radius: 8px;
  background: rgba(99,102,241,0.03);
  font-size: 12px; color: #94a3b8;

  &.error { border-left: 2px solid #ef4444; }
  &.success { border-left: 2px solid #10b981; }

  .h-time { color: #4a5568; min-width: 70px; }
  .h-type { color: #818cf8; min-width: 100px; }
  .h-file { color: #e2e8f0; flex: 1; font-family: monospace; }
  .h-result { color: #94a3b8; }
}

// ========== 系统信息 ==========
.sys-info-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
}

.sys-card { padding: 20px; }

.info-list { display: flex; flex-direction: column; gap: 2px; }

.info-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(99,102,241,0.05);
  .info-label { font-size: 13px; color: #94a3b8; }
  .info-value { font-size: 14px; font-weight: 600; color: #e2e8f0; font-family: monospace; }
}

.quick-actions { display: flex; flex-direction: column; gap: 10px; }

.qa-btn {
  width: 100%; padding: 12px 16px;
  background: rgba(99,102,241,0.06);
  border: 1px solid rgba(99,102,241,0.12);
  border-radius: 10px;
  color: #cbd5e1; font-size: 13px; font-weight: 500;
  cursor: pointer; display: flex; align-items: center; gap: 10px;
  transition: all 0.25s ease;
  &:hover:not(:disabled) { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.3); transform: translateX(4px); }
  &:disabled { opacity: 0.5; cursor: wait; }
  span { font-size: 18px; }
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .overview-row { grid-template-columns: repeat(2, 1fr); }
  .upload-types { grid-template-columns: 1fr; }
  .sys-info-grid { grid-template-columns: 1fr; }
}
</style>
