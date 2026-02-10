<template>
  <div class="recommendations-page">
    <!-- 查询面板 -->
    <div class="control-panel glass-card">
      <div class="panel-header">
        <div class="panel-title"><span class="icon">🤖</span>智能出行推荐</div>
        <div class="panel-subtitle">选择起终点与出行时间，获取基于 Z-Score 异常检测 + 余弦相似度的个性化建议</div>
      </div>
      <div class="controls-grid">
        <div class="control-group station-group">
          <label>起点站</label>
          <div class="search-select" ref="originWrap" @click="openDropdown('origin')">
            <div class="select-display" :class="{ active: originDropdown }">
              <span class="display-text" :class="{ placeholder: !selectedOrigin }">
                {{ selectedOrigin ? selectedOrigin.station_name : '请选择起点站' }}
              </span>
              <span class="select-arrow" :class="{ open: originDropdown }">▾</span>
            </div>
          </div>
          <Teleport to="body">
            <div class="dropdown-panel" v-show="originDropdown" ref="originPanel" :style="originPanelStyle">
              <div class="dropdown-search">
                <span class="search-icon">🔍</span>
                <input
                  ref="originInput"
                  type="text"
                  class="dropdown-search-input"
                  placeholder="输入站点名搜索..."
                  v-model="originSearch"
                  @input="searchStations('origin')"
                  @click.stop
                />
              </div>
              <ul class="dropdown-list">
                <li v-for="s in originOptions" :key="s.station_id"
                    @mousedown.prevent="selectStation('origin', s)"
                    :class="{ selected: selectedOrigin?.station_id === s.station_id }">
                  <span class="station-dot"></span>
                  {{ s.station_name }}
                </li>
                <li v-if="!originOptions.length" class="no-data">无匹配站点</li>
              </ul>
            </div>
          </Teleport>
        </div>

        <div class="swap-btn" @click.stop="swapStations" title="交换起终点">⇄</div>

        <div class="control-group station-group">
          <label>终点站</label>
          <div class="search-select" ref="destWrap" @click="openDropdown('dest')">
            <div class="select-display" :class="{ active: destDropdown }">
              <span class="display-text" :class="{ placeholder: !selectedDest }">
                {{ selectedDest ? selectedDest.station_name : '请选择终点站' }}
              </span>
              <span class="select-arrow" :class="{ open: destDropdown }">▾</span>
            </div>
          </div>
          <Teleport to="body">
            <div class="dropdown-panel" v-show="destDropdown" ref="destPanel" :style="destPanelStyle">
              <div class="dropdown-search">
                <span class="search-icon">🔍</span>
                <input
                  ref="destInput"
                  type="text"
                  class="dropdown-search-input"
                  placeholder="输入站点名搜索..."
                  v-model="destSearch"
                  @input="searchStations('dest')"
                  @click.stop
                />
              </div>
              <ul class="dropdown-list">
                <li v-for="s in destOptions" :key="s.station_id"
                    @mousedown.prevent="selectStation('dest', s)"
                    :class="{ selected: selectedDest?.station_id === s.station_id }">
                  <span class="station-dot"></span>
                  {{ s.station_name }}
                </li>
                <li v-if="!destOptions.length" class="no-data">无匹配站点</li>
              </ul>
            </div>
          </Teleport>
        </div>

        <div class="control-group time-group">
          <label>出行时间</label>
          <select v-model="travelHour" class="select-input time-select">
            <option v-for="h in hourOptions" :key="h" :value="h">{{ String(h).padStart(2, '0') }}:00</option>
          </select>
        </div>

        <div class="control-group btn-group">
          <label>&nbsp;</label>
          <button class="run-btn" @click="fetchRecs" :disabled="!canQuery || loading">
            <span v-if="loading" class="spinner"></span>
            <span v-else>🔍</span>
            {{ loading ? '分析中...' : '获取推荐' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 总评概览 -->
    <div class="summary-banner glass-card" v-if="recommendations.length">
      <div class="summary-left">
        <div class="summary-score-ring" :style="ringStyle">
          <svg viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="34" class="ring-bg" />
            <circle cx="40" cy="40" r="34" class="ring-fill" :style="ringStroke" />
          </svg>
          <div class="ring-text">
            <span class="ring-val">{{ overallScore }}</span>
            <span class="ring-unit">分</span>
          </div>
        </div>
        <div class="summary-info">
          <div class="summary-title">{{ overallTitle }}</div>
          <div class="summary-desc">{{ overallDesc }}</div>
        </div>
      </div>
      <div class="summary-tags">
        <span class="stag" v-for="tag in summaryTags" :key="tag.label" :class="tag.cls">
          {{ tag.icon }} {{ tag.label }}
        </span>
      </div>
    </div>

    <!-- 算法说明卡片 (动态) -->
    <div class="algo-row" v-if="usedAlgorithms.length">
      <div class="algo-card glass-card" v-for="algo in usedAlgorithms" :key="algo.name">
        <div class="algo-icon">{{ algo.icon }}</div>
        <div class="algo-info">
          <div class="algo-name">{{ algo.name }}</div>
          <div class="algo-desc">{{ algo.desc }}</div>
        </div>
        <div class="algo-count">{{ algo.count }}条</div>
      </div>
    </div>

    <!-- 推荐卡片列表 -->
    <TransitionGroup name="rec-list-anim" tag="div" class="rec-list" v-if="recommendations.length">
      <div
        v-for="(rec, idx) in recommendations"
        :key="rec.rec_type + (rec.metadata?.role || '')"
        class="rec-card glass-card"
        :class="'rec-' + rec.rec_type"
        :style="{ '--delay': idx * 0.1 + 's' }"
      >
        <div class="rec-header">
          <span class="rec-type-badge" :class="'badge-' + rec.rec_type">
            {{ typeLabel(rec.rec_type, rec.metadata?.role) }}
          </span>
          <span class="rec-score-bar">
            <span class="score-track">
              <span class="score-fill" :style="{ width: (rec.score * 100) + '%', background: scoreColor(rec.score) }"></span>
            </span>
            <span class="score-num" :style="{ color: scoreColor(rec.score) }">{{ (rec.score * 100).toFixed(0) }}</span>
          </span>
          <span class="algo-tag" v-if="rec.metadata?.algorithm">{{ rec.metadata.algorithm }}</span>
        </div>
        <h4 class="rec-title">{{ rec.title }}</h4>
        <p class="rec-desc">{{ rec.description }}</p>
        <div class="rec-meta" v-if="rec.metadata">
          <!-- 时段柱状图 -->
          <div v-if="rec.metadata.hourly_flow" class="mini-chart-wrap">
            <div class="chart-legend">
              <span class="cl-item"><span class="cl-dot" style="background:#f59e0b"></span>当前时段</span>
              <span class="cl-item"><span class="cl-dot" style="background:#ef4444"></span>高峰</span>
              <span class="cl-item"><span class="cl-dot" style="background:#10b981"></span>推荐</span>
            </div>
            <div class="mini-chart" :data-rec-key="rec.rec_type + (rec.metadata?.role || '')"></div>
          </div>
          <!-- Z-Score 信息 -->
          <div v-if="rec.metadata.user_z !== undefined" class="z-info">
            <span class="z-tag" :class="zClass(rec.metadata.user_z)">
              Z = {{ rec.metadata.user_z }}
            </span>
            <span class="z-label">均值 {{ rec.metadata.mean_flow }} · 标准差 {{ rec.metadata.std_flow }}</span>
            <span class="z-level" v-if="rec.metadata.user_level" :class="'level-' + rec.metadata.user_level">
              {{ rec.metadata.user_level }}
            </span>
          </div>
          <!-- 附近时段对比 -->
          <div v-if="rec.metadata.nearby_hours && Object.keys(rec.metadata.nearby_hours).length > 1" class="nearby-compare">
            <div class="nearby-title">⏱ 前后时段对比</div>
            <div class="nearby-bars">
              <div v-for="(info, h) in rec.metadata.nearby_hours" :key="h" class="nearby-bar-row">
                <span class="nb-hour" :class="{ 'nb-current': Number(h) === rec.metadata.user_hour }">
                  {{ h }}:00
                </span>
                <div class="nb-track">
                  <div class="nb-fill" :style="{ width: nearbyPct(info.flow, rec.metadata.nearby_hours) + '%', background: nearbyColor(info.z) }"></div>
                </div>
                <span class="nb-val">{{ info.flow.toLocaleString() }}</span>
                <span class="nb-level" :class="'lv-' + info.level">{{ info.level === 'high' ? '拥挤' : info.level === 'medium' ? '适中' : '舒适' }}</span>
              </div>
            </div>
          </div>
          <!-- 推荐时段 -->
          <div v-if="rec.metadata.recommended_hours?.length" class="meta-hours">
            <span class="meta-hours-label">💡 推荐时段:</span>
            <span v-for="h in rec.metadata.recommended_hours" :key="h" class="hour-tag good">{{ h }}:00</span>
          </div>
          <!-- 高峰时段 -->
          <div v-if="rec.metadata.congested_hours?.length" class="meta-hours">
            <span class="meta-hours-label">⚠️ 高峰时段:</span>
            <span v-for="h in rec.metadata.congested_hours" :key="h" class="hour-tag bad">{{ h }}:00</span>
          </div>
          <!-- 替代站点 -->
          <div v-if="rec.metadata.alternatives?.length" class="alt-list">
            <div class="alt-item" v-for="alt in rec.metadata.alternatives" :key="alt.station_id">
              <div class="alt-main">
                <span class="alt-name">🚏 {{ alt.station_name }}</span>
                <span class="alt-sim">相似度 <strong>{{ (alt.similarity * 100).toFixed(0) }}%</strong></span>
              </div>
              <div class="alt-detail">
                <span class="alt-flow">客流 {{ alt.flow_at_hour.toLocaleString() }}</span>
                <div class="alt-save-bar">
                  <div class="save-track">
                    <div class="save-fill" :style="{ width: Math.min(alt.savings, 100) + '%' }"></div>
                  </div>
                  <span class="save-pct">↓{{ alt.savings }}%</span>
                </div>
              </div>
            </div>
          </div>
          <!-- 百分位 -->
          <div v-if="rec.metadata.percentile" class="percentile-bar">
            <div class="percentile-label">拥挤度百分位</div>
            <div class="percentile-track">
              <div class="percentile-fill" :style="{ width: rec.metadata.percentile + '%' }"></div>
              <div class="percentile-marker" :style="{ left: rec.metadata.percentile + '%' }">
                {{ rec.metadata.percentile }}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </TransitionGroup>

    <!-- 空状态 -->
    <div class="empty-state glass-card" v-if="!recommendations.length && !loading && queried">
      <div class="empty-icon">📭</div>
      <p>暂无推荐数据</p>
      <span>该 OD 对在所选日期可能没有客流数据，请尝试其他站点</span>
    </div>

    <div class="empty-state glass-card" v-if="!recommendations.length && !loading && !queried">
      <div class="empty-icon">🚇</div>
      <p>选择出行信息，获取智能推荐</p>
      <span>请在上方选择起点站、终点站和出行时间，系统将基于客流数据实时分析</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { getRecommendations, getStationList } from '../api'

// ========== 站点搜索 ==========
const originSearch = ref('')
const destSearch = ref('')
const originOptions = ref([])
const destOptions = ref([])
const originDropdown = ref(false)
const destDropdown = ref(false)
const selectedOrigin = ref(null)
const selectedDest = ref(null)
const originWrap = ref(null)
const destWrap = ref(null)
const originInput = ref(null)
const destInput = ref(null)
const originPanel = ref(null)
const destPanel = ref(null)
const originPanelStyle = ref({})
const destPanelStyle = ref({})

// 全量站点缓存
const allStations = ref([])

const travelHour = ref(8)
const hourOptions = Array.from({ length: 18 }, (_, i) => i + 5) // 5:00 ~ 22:00

const recommendations = ref([])
const loading = ref(false)
const queried = ref(false)

// 图表实例跟踪
let miniCharts = []

const canQuery = computed(() => selectedOrigin.value && selectedDest.value && travelHour.value !== null)

// ===== 总评概览 =====
const overallScore = computed(() => {
  if (!recommendations.value.length) return 0
  const avg = recommendations.value.reduce((s, r) => s + r.score, 0) / recommendations.value.length
  return Math.round(avg * 100)
})

const overallTitle = computed(() => {
  const s = overallScore.value
  if (s >= 70) return '出行条件良好'
  if (s >= 45) return '出行条件一般'
  return '出行需注意'
})

const overallDesc = computed(() => {
  const timeRec = recommendations.value.find(r => r.rec_type === 'time')
  const level = timeRec?.metadata?.user_level
  if (level === '高峰') return '当前时段客流较高，建议参考推荐时段错峰出行'
  if (level === '偏高') return '当前时段客流偏高，可适当调整出行时间'
  if (level === '推荐') return '当前时段客流较低，是出行的好时机！'
  return '当前时段客流正常，出行条件可接受'
})

const ringStyle = computed(() => {
  const s = overallScore.value
  const color = s >= 70 ? '#10b981' : s >= 45 ? '#f59e0b' : '#ef4444'
  return { '--ring-color': color }
})

const ringStroke = computed(() => {
  const circumference = 2 * Math.PI * 34
  const pct = overallScore.value / 100
  return {
    strokeDasharray: `${circumference * pct} ${circumference * (1 - pct)}`,
    strokeDashoffset: `${circumference * 0.25}`,
    stroke: ringStyle.value['--ring-color'],
  }
})

const summaryTags = computed(() => {
  const tags = []
  const timeRec = recommendations.value.find(r => r.rec_type === 'time')
  if (timeRec?.metadata?.user_level) {
    const l = timeRec.metadata.user_level
    tags.push({
      label: l === '高峰' ? '高峰时段' : l === '偏高' ? '客流偏高' : l === '推荐' ? '低峰出行' : '客流正常',
      icon: l === '高峰' ? '🔴' : l === '偏高' ? '🟡' : l === '推荐' ? '🟢' : '🔵',
      cls: l === '高峰' ? 'stag-danger' : l === '偏高' ? 'stag-warn' : l === '推荐' ? 'stag-good' : 'stag-info',
    })
  }
  const routeRec = recommendations.value.find(r => r.rec_type === 'route')
  if (routeRec?.metadata?.alternatives?.length) {
    tags.push({ label: `${routeRec.metadata.alternatives.length}个替代站`, icon: '🔄', cls: 'stag-good' })
  }
  const bestHour = timeRec?.metadata?.recommended_hours?.[0]
  if (bestHour != null) tags.push({ label: `推荐 ${bestHour}:00`, icon: '⏰', cls: 'stag-info' })
  return tags
})

// 动态算法卡片
const allAlgos = {
  'Z-Score 异常检测': { icon: '📊', name: 'Z-Score 异常检测', desc: '对客流时序标准化，识别异常高峰与低谷' },
  'Z-Score + 百分位排名': { icon: '📈', name: 'Z-Score + 百分位排名', desc: '结合时序标准化与百分位排名量化拥挤度' },
  '余弦相似度 + 加权评分': { icon: '📐', name: '余弦相似度 + 加权评分', desc: '构建客流特征向量，寻找更空闲的替代站' },
}

const usedAlgorithms = computed(() => {
  const counts = {}
  recommendations.value.forEach(r => {
    const a = r.metadata?.algorithm
    if (a) counts[a] = (counts[a] || 0) + 1
  })
  return Object.keys(counts)
    .filter(k => allAlgos[k])
    .map(k => ({ ...allAlgos[k], count: counts[k] }))
})

// ===== 工具函数 =====
function typeLabel(type, role) {
  if (type === 'time') return '⏰ 时段推荐'
  if (type === 'avoid') return role === '出发站' ? '🚉 起点拥挤分析' : '🏁 终点拥挤分析'
  if (type === 'route') return '🔄 替代路线'
  return '💡 建议'
}

function scoreColor(score) {
  if (score >= 0.6) return '#10b981'
  if (score >= 0.4) return '#f59e0b'
  return '#ef4444'
}

function zClass(z) {
  if (z > 0.8) return 'z-high'
  if (z > 0.3) return 'z-mid'
  if (z < -0.3) return 'z-low'
  return 'z-normal'
}

function nearbyPct(flow, nearbyHours) {
  const maxF = Math.max(...Object.values(nearbyHours).map(v => v.flow), 1)
  return (flow / maxF) * 100
}

function nearbyColor(z) {
  if (z > 0.8) return '#ef4444'
  if (z > 0.3) return '#f59e0b'
  if (z < -0.3) return '#10b981'
  return '#6366f1'
}

// ===== 站点相关 =====
async function loadAllStations() {
  try {
    const res = await getStationList('')
    allStations.value = res.data.data || []
    originOptions.value = allStations.value
    destOptions.value = allStations.value
  } catch (e) { /* ignore */ }
}

function searchStations(role) {
  const keyword = (role === 'origin' ? originSearch.value : destSearch.value).trim().toLowerCase()
  const filtered = keyword
    ? allStations.value.filter(s => s.station_name.toLowerCase().includes(keyword))
    : allStations.value
  if (role === 'origin') originOptions.value = filtered
  else destOptions.value = filtered
}

function selectStation(role, station) {
  if (role === 'origin') {
    selectedOrigin.value = station
    originSearch.value = ''
    originDropdown.value = false
  } else {
    selectedDest.value = station
    destSearch.value = ''
    destDropdown.value = false
  }
}

function calcPanelPos(wrapEl) {
  const rect = wrapEl.getBoundingClientRect()
  return {
    position: 'fixed',
    top: rect.bottom + 4 + 'px',
    left: rect.left + 'px',
    width: rect.width + 'px',
    zIndex: 9999,
  }
}

function openDropdown(role) {
  if (role === 'origin') {
    if (originDropdown.value) { originDropdown.value = false; return }
    destDropdown.value = false
    originOptions.value = allStations.value
    originSearch.value = ''
    originDropdown.value = true
    nextTick(() => {
      if (originWrap.value) originPanelStyle.value = calcPanelPos(originWrap.value)
      originInput.value?.focus()
    })
  } else {
    if (destDropdown.value) { destDropdown.value = false; return }
    originDropdown.value = false
    destOptions.value = allStations.value
    destSearch.value = ''
    destDropdown.value = true
    nextTick(() => {
      if (destWrap.value) destPanelStyle.value = calcPanelPos(destWrap.value)
      destInput.value?.focus()
    })
  }
}

function swapStations() {
  const tmp = selectedOrigin.value
  selectedOrigin.value = selectedDest.value
  selectedDest.value = tmp
}

function handleClickOutside(e) {
  const inOrigin = originWrap.value?.contains(e.target) || originPanel.value?.contains(e.target)
  const inDest = destWrap.value?.contains(e.target) || destPanel.value?.contains(e.target)
  if (!inOrigin) originDropdown.value = false
  if (!inDest) destDropdown.value = false
}

// ========== 推荐查询 ==========
async function fetchRecs() {
  if (!canQuery.value) return
  loading.value = true
  queried.value = true
  disposeMiniCharts()
  try {
    const res = await getRecommendations({
      origin: selectedOrigin.value.station_id,
      dest: selectedDest.value.station_id,
      hour: travelHour.value,
    })
    recommendations.value = res.data.data || []
    await nextTick()
    renderMiniCharts()
  } catch (e) {
    console.error('获取推荐失败', e)
  } finally {
    loading.value = false
  }
}

// ========== 图表管理 ==========
function disposeMiniCharts() {
  miniCharts.forEach(c => { if (c && !c.isDisposed()) c.dispose() })
  miniCharts = []
}

function renderMiniCharts() {
  disposeMiniCharts()
  const containers = document.querySelectorAll('.mini-chart')
  containers.forEach(el => {
    const key = el.dataset.recKey
    const rec = recommendations.value.find(r => (r.rec_type + (r.metadata?.role || '')) === key)
    if (!rec || !rec.metadata?.hourly_flow) return

    const chart = echarts.init(el)
    miniCharts.push(chart)

    const flowMap = rec.metadata.hourly_flow
    const zMap = rec.metadata.z_scores || {}
    const userHour = rec.metadata.user_hour
    const suggestedHours = new Set(rec.metadata.recommended_hours || rec.metadata.suggested_hours || [])

    // 补全 6:00-22:00 全时段，缺失时段补 0
    const fullHours = []
    for (let h = 6; h <= 22; h++) fullHours.push(h)
    // 确保用户选择的时段也在其中
    if (userHour != null && !fullHours.includes(userHour)) fullHours.push(userHour)
    fullHours.sort((a, b) => a - b)

    const flows = fullHours.map(h => flowMap[h] || 0)
    const maxFlow = Math.max(...flows, 1)

    chart.setOption({
      grid: { top: 12, right: 12, bottom: 24, left: 42 },
      xAxis: {
        type: 'category',
        data: fullHours.map(h => h + ':00'),
        axisLabel: { color: '#64748b', fontSize: 10, interval: fullHours.length > 14 ? 1 : 0, rotate: 45 },
        axisLine: { lineStyle: { color: 'rgba(99,102,241,0.15)' } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        min: 0,
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(99,102,241,0.06)' } },
      },
      series: [{
        type: 'bar',
        data: flows.map((v, i) => {
          const h = fullHours[i]
          const z = zMap[h] || 0
          let color = 'rgba(79,70,229,0.45)'
          if (h === userHour) color = '#f59e0b'
          else if (z > 0.8) color = '#ef4444'
          else if (z < -0.3 || suggestedHours.has(h)) color = '#10b981'
          else if (v > 0) color = '#4f46e5'
          return {
            value: v,
            itemStyle: {
              color,
              borderRadius: [3, 3, 0, 0],
              shadowBlur: h === userHour ? 8 : 0,
              shadowColor: h === userHour ? 'rgba(245,158,11,0.4)' : 'transparent',
            },
          }
        }),
        barMaxWidth: 28,
        barMinHeight: 2, // 即使是 0 也显示一个小底线，方便定位用户时段
        animationDuration: 800,
        animationEasing: 'cubicOut',
      }],
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(13,18,51,0.95)',
        borderColor: 'rgba(99,102,241,0.3)',
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        formatter: (params) => {
          const p = params[0]
          const h = fullHours[p.dataIndex]
          const z = zMap[h]
          let tag = ''
          if (h === userHour) tag = ' <span style="color:#f59e0b">◀ 当前选择</span>'
          else if (z !== undefined && z > 0.8) tag = ' <span style="color:#ef4444">● 高峰</span>'
          else if (z !== undefined && z < -0.3) tag = ' <span style="color:#10b981">● 推荐</span>'
          const flowVal = flowMap[h] != null ? flowMap[h] : 0
          return `<strong>${h}:00</strong>${tag}<br/>客流：<b>${flowVal.toLocaleString()}</b>${z !== undefined ? `<br/>Z-Score：${z}` : ''}`
        },
      },
    })
  })
}

function handleResize() {
  miniCharts.forEach(c => { if (c && !c.isDisposed()) c.resize() })
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('resize', handleResize)
  loadAllStations()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('resize', handleResize)
  disposeMiniCharts()
})
</script>

<style lang="scss" scoped>
.recommendations-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// ========== 控制面板 ==========
.control-panel {
  padding: 20px 24px;

  .panel-header { margin-bottom: 18px; }

  .panel-title {
    font-size: 15px; font-weight: 600; color: #e2e8f0;
    display: flex; align-items: center; gap: 8px;
    .icon { font-size: 18px; }
  }

  .panel-subtitle {
    font-size: 12px; color: #64748b; margin-top: 4px; padding-left: 26px;
  }

  .controls-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr 140px 140px;
    align-items: end;
    gap: 12px;
  }

  .control-group {
    display: flex; flex-direction: column; gap: 6px;
    label {
      font-size: 12px; color: #94a3b8;
      text-transform: uppercase; letter-spacing: 0.5px;
    }
  }

  .swap-btn {
    width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
    background: rgba(99,102,241,0.1); border-radius: 8px; cursor: pointer;
    color: #6366f1; font-size: 18px; transition: all 0.2s;
    align-self: end;
    &:hover { background: rgba(99,102,241,0.2); transform: scale(1.1); }
  }
}

.select-input {
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px; padding: 9px 12px;
  color: #e2e8f0; font-size: 13px; outline: none; width: 100%;
  box-sizing: border-box; height: 38px;
  -webkit-appearance: none; appearance: none;
  option { background: #0d1233; color: #e2e8f0; }
  &:focus { border-color: rgba(99, 102, 241, 0.5); }
}

.time-select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236366f1' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 28px;
}

.search-select {
  position: relative;
  cursor: pointer;

  .select-display {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(99, 102, 241, 0.08);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 8px; padding: 0 12px;
    height: 38px; transition: all 0.2s;
    &:hover { border-color: rgba(99,102,241,0.4); }

    .display-text {
      font-size: 13px; color: #e2e8f0;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      &.placeholder { color: #4a5568; }
    }

    .select-arrow {
      font-size: 12px; color: #6366f1;
      transition: transform 0.25s ease;
      margin-left: 8px; flex-shrink: 0;
      &.open { transform: rotate(180deg); }
    }
  }

  .select-display.active {
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 0 0 2px rgba(99,102,241,0.1);
  }
}

.run-btn {
  padding: 0 20px; height: 38px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none; border-radius: 10px; color: white;
  font-size: 13px; font-weight: 600; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
  white-space: nowrap;
  &:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.4); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
  .spinner {
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white; border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

// ========== 总评概览 ==========
.summary-banner {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 24px; gap: 20px;
}

.summary-left {
  display: flex; align-items: center; gap: 18px;
}

.summary-score-ring {
  position: relative; width: 74px; height: 74px; flex-shrink: 0;
  svg { width: 100%; height: 100%; transform: rotate(-90deg); }
  .ring-bg { fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 6; }
  .ring-fill { fill: none; stroke-width: 6; stroke-linecap: round; transition: all 0.8s ease; }
  .ring-text {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    flex-direction: column; gap: 0;
  }
  .ring-val { font-size: 22px; font-weight: 700; color: var(--ring-color); line-height: 1; }
  .ring-unit { font-size: 10px; color: #64748b; }
}

.summary-info {
  .summary-title { font-size: 16px; font-weight: 600; color: #e2e8f0; }
  .summary-desc { font-size: 13px; color: #94a3b8; margin-top: 4px; line-height: 1.6; }
}

.summary-tags {
  display: flex; gap: 8px; flex-shrink: 0; flex-wrap: wrap;
  .stag {
    padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;
    white-space: nowrap;
    &.stag-danger { background: rgba(239,68,68,0.1); color: #ef4444; }
    &.stag-warn { background: rgba(245,158,11,0.1); color: #f59e0b; }
    &.stag-good { background: rgba(16,185,129,0.1); color: #10b981; }
    &.stag-info { background: rgba(99,102,241,0.1); color: #818cf8; }
  }
}

// ========== 算法说明 ==========
.algo-row {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px;
}

.algo-card {
  padding: 14px 18px; display: flex; align-items: center; gap: 12px;
  .algo-icon { font-size: 24px; }
  .algo-info { flex: 1; }
  .algo-name { font-size: 13px; font-weight: 600; color: #e2e8f0; }
  .algo-desc { font-size: 11px; color: #64748b; margin-top: 2px; line-height: 1.5; }
  .algo-count {
    font-size: 12px; color: #818cf8; font-weight: 600;
    background: rgba(99,102,241,0.1); padding: 3px 10px; border-radius: 12px;
    flex-shrink: 0;
  }
}

// ========== 推荐卡片 ==========
.rec-list {
  display: flex; flex-direction: column; gap: 16px;
}

.rec-list-anim-enter-active { animation: recIn 0.5s ease-out both; animation-delay: var(--delay, 0s); }
.rec-list-anim-leave-active { animation: recOut 0.3s ease-in both; }

@keyframes recIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes recOut {
  from { opacity: 1; }
  to { opacity: 0; transform: translateY(-10px); }
}

.rec-card {
  padding: 20px 24px; border-left: 3px solid transparent;
  transition: all 0.3s ease;
  &:hover { transform: translateX(4px); }
  &.rec-avoid { border-left-color: #f59e0b; }
  &.rec-time { border-left-color: #6366f1; }
  &.rec-route { border-left-color: #10b981; }
}

.rec-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap;
}

.rec-type-badge {
  font-size: 11px; padding: 3px 10px; border-radius: 12px; font-weight: 500;
  &.badge-avoid { background: rgba(245,158,11,0.12); color: #f59e0b; }
  &.badge-time { background: rgba(99,102,241,0.12); color: #6366f1; }
  &.badge-route { background: rgba(16,185,129,0.12); color: #10b981; }
}

.rec-score-bar {
  display: flex; align-items: center; gap: 8px;
  .score-track {
    width: 60px; height: 5px; border-radius: 3px;
    background: rgba(255,255,255,0.06); overflow: hidden;
  }
  .score-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
  .score-num { font-size: 13px; font-weight: 700; min-width: 24px; }
}

.algo-tag {
  margin-left: auto;
  font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: rgba(99,102,241,0.08); color: #818cf8;
}

.rec-title { font-size: 15px; font-weight: 600; color: #e2e8f0; margin-bottom: 8px; }
.rec-desc { font-size: 13px; color: #94a3b8; line-height: 1.7; margin-bottom: 12px; white-space: pre-line; }

// ========== 卡片内元素 ==========
.rec-meta {
  .mini-chart-wrap { margin-top: 8px; }

  .chart-legend {
    display: flex; gap: 14px; margin-bottom: 6px;
    .cl-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: #64748b; }
    .cl-dot { width: 8px; height: 8px; border-radius: 2px; }
  }

  .mini-chart { width: 100%; height: 170px; }

  .z-info {
    display: flex; align-items: center; gap: 10px; margin-top: 10px; flex-wrap: wrap;
    .z-tag {
      padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;
      &.z-high { background: rgba(239,68,68,0.12); color: #ef4444; }
      &.z-mid { background: rgba(245,158,11,0.12); color: #f59e0b; }
      &.z-low { background: rgba(16,185,129,0.12); color: #10b981; }
      &.z-normal { background: rgba(99,102,241,0.1); color: #818cf8; }
    }
    .z-label { font-size: 11px; color: #64748b; }
    .z-level {
      font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px;
      &.level-高峰 { background: rgba(239,68,68,0.1); color: #ef4444; }
      &.level-偏高 { background: rgba(245,158,11,0.1); color: #f59e0b; }
      &.level-推荐 { background: rgba(16,185,129,0.1); color: #10b981; }
      &.level-正常 { background: rgba(99,102,241,0.08); color: #818cf8; }
    }
  }

  // 附近时段对比
  .nearby-compare {
    margin-top: 12px; padding: 14px; border-radius: 10px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    .nearby-title { font-size: 12px; color: #94a3b8; margin-bottom: 10px; font-weight: 500; }
  }
  .nearby-bars { display: flex; flex-direction: column; gap: 6px; }
  .nearby-bar-row {
    display: grid; grid-template-columns: 52px 1fr 70px 44px; gap: 8px; align-items: center;
  }
  .nb-hour {
    font-size: 12px; color: #64748b; text-align: right;
    &.nb-current { color: #f59e0b; font-weight: 700; }
  }
  .nb-track {
    height: 8px; background: rgba(255,255,255,0.04); border-radius: 4px; overflow: hidden;
  }
  .nb-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
  .nb-val { font-size: 11px; color: #94a3b8; text-align: right; }
  .nb-level {
    font-size: 10px; font-weight: 500; text-align: center;
    &.lv-high { color: #ef4444; }
    &.lv-medium { color: #f59e0b; }
    &.lv-low { color: #10b981; }
  }

  .meta-hours {
    display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 10px;
    .meta-hours-label { font-size: 12px; color: #94a3b8; }
    .hour-tag {
      padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;
      &.good { background: rgba(16,185,129,0.1); color: #10b981; }
      &.bad { background: rgba(239,68,68,0.1); color: #ef4444; }
    }
  }

  .alt-list {
    margin-top: 12px; display: flex; flex-direction: column; gap: 8px;
    .alt-item {
      padding: 12px 16px; border-radius: 10px;
      background: rgba(16,185,129,0.04);
      border: 1px solid rgba(16,185,129,0.1);
      display: flex; flex-direction: column; gap: 8px;
    }
    .alt-main {
      display: flex; align-items: center; justify-content: space-between;
      .alt-name { font-size: 14px; color: #e2e8f0; font-weight: 600; }
      .alt-sim {
        font-size: 12px; color: #06b6d4;
        strong { color: #22d3ee; }
      }
    }
    .alt-detail {
      display: flex; align-items: center; gap: 16px;
      .alt-flow { font-size: 12px; color: #94a3b8; flex-shrink: 0; }
    }
    .alt-save-bar {
      flex: 1; display: flex; align-items: center; gap: 8px;
      .save-track {
        flex: 1; height: 6px; background: rgba(16,185,129,0.08);
        border-radius: 3px; overflow: hidden;
      }
      .save-fill {
        height: 100%; border-radius: 3px;
        background: linear-gradient(90deg, #10b981, #34d399);
        transition: width 0.5s ease;
      }
      .save-pct {
        font-size: 13px; font-weight: 700; color: #10b981;
        min-width: 50px; text-align: right;
      }
    }
  }

  .percentile-bar {
    margin-top: 12px;
    .percentile-label { font-size: 11px; color: #64748b; margin-bottom: 6px; }
    .percentile-track {
      position: relative; height: 6px; border-radius: 3px;
      background: linear-gradient(90deg, #10b981 0%, #f59e0b 50%, #ef4444 100%);
      opacity: 0.3;
    }
    .percentile-fill {
      position: absolute; top: 0; left: 0; height: 100%; border-radius: 3px;
      background: linear-gradient(90deg, #10b981, #f59e0b, #ef4444);
      opacity: 1; transition: width 0.6s ease;
    }
    .percentile-marker {
      position: absolute; top: -20px; transform: translateX(-50%);
      font-size: 11px; font-weight: 600; color: #e2e8f0;
      background: rgba(13,18,51,0.8); padding: 1px 6px; border-radius: 4px;
    }
  }
}

// ========== 空状态 ==========
.empty-state {
  padding: 60px; text-align: center;
  .empty-icon { font-size: 48px; margin-bottom: 16px; }
  p { font-size: 16px; color: #e2e8f0; font-weight: 500; margin-bottom: 6px; }
  span { font-size: 13px; color: #64748b; }
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>

<style lang="scss">
/* Teleport 到 body 的下拉面板 — 非 scoped */
.dropdown-panel {
  background: rgba(13, 18, 51, 0.98);
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.1);
  overflow: hidden;
  animation: dropPanelIn 0.2s ease-out;

  .dropdown-search {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 14px;
    border-bottom: 1px solid rgba(99,102,241,0.1);

    .search-icon { font-size: 13px; opacity: 0.5; }

    .dropdown-search-input {
      flex: 1; background: none; border: none; outline: none;
      color: #e2e8f0; font-size: 13px;
      &::placeholder { color: #4a5568; }
    }
  }

  .dropdown-list {
    max-height: 260px; overflow-y: auto; list-style: none;
    padding: 4px 0; margin: 0;

    &::-webkit-scrollbar { width: 4px; }
    &::-webkit-scrollbar-track { background: transparent; }
    &::-webkit-scrollbar-thumb {
      background: rgba(99,102,241,0.25); border-radius: 2px;
    }

    li {
      padding: 9px 14px; color: #94a3b8; font-size: 13px;
      cursor: pointer; display: flex; align-items: center; gap: 8px;
      transition: all 0.15s;

      .station-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: rgba(99,102,241,0.3); flex-shrink: 0;
        transition: background 0.15s;
      }

      &:hover {
        background: rgba(99,102,241,0.08); color: #e2e8f0;
        .station-dot { background: #6366f1; }
      }

      &.selected {
        background: rgba(99,102,241,0.15); color: #818cf8; font-weight: 500;
        .station-dot { background: #818cf8; box-shadow: 0 0 6px rgba(129,140,248,0.4); }
      }

      &.no-data {
        color: #4a5568; cursor: default; justify-content: center;
        padding: 20px; font-size: 12px;
        &:hover { background: none; }
      }
    }
  }
}

@keyframes dropPanelIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>