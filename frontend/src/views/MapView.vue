<template>
  <div class="map-view">
    <!-- 控制面板 -->
    <div class="control-panel glass-card">
      <div class="panel-header">
        <h3>🌐 地图控制</h3>
        <span class="badge badge-info">{{ activeStationList.length }} 个站点</span>
      </div>

      <div class="control-group">
        <label>显示图层</label>
        <div class="layer-toggles">
          <button
            v-for="layer in layers"
            :key="layer.key"
            class="layer-btn"
            :class="{ active: activeLayer === layer.key }"
            @click="activeLayer = layer.key"
          >
            <span class="layer-icon">{{ layer.icon }}</span>
            <span>{{ layer.label }}</span>
          </button>
        </div>
      </div>

      <div class="control-group">
        <label>气泡大小</label>
        <input type="range" v-model.number="bubbleScale" min="1" max="10" step="0.5" class="range-slider" />
        <span class="range-val">×{{ bubbleScale }}</span>
      </div>

      <div class="control-group">
        <label>显示标签</label>
        <div class="toggle-switch" :class="{ on: showLabels }" @click="showLabels = !showLabels">
          <div class="toggle-knob"></div>
        </div>
      </div>

      <!-- 动态统计信息 -->
      <div class="stat-cards">
        <div class="mini-stat" v-for="card in statCards" :key="card.label">
          <div class="mini-val" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="mini-label">{{ card.label }}</div>
        </div>
      </div>

      <!-- 无聚类数据提示 -->
      <div v-if="!loading && clusterData.length === 0 && activeLayer !== 'flow'" class="hint-box">
        💡 暂无聚类数据，请先前往「聚类分析」页面执行
      </div>
    </div>

    <!-- 主地图 -->
    <div class="map-container glass-card">
      <div v-if="loading" class="map-loading">
        <div class="loading-pulse"></div>
        <span>正在加载地图数据...</span>
      </div>

      <div v-if="!loading && !hasData" class="map-empty">
        <div class="empty-icon">🗺️</div>
        <div class="empty-text">暂无可显示的站点数据</div>
        <div class="empty-hint">请确认已完成数据导入和聚类分析</div>
      </div>

      <div ref="mapChart" class="chart-area"></div>

      <div class="coord-bar" v-if="!loading && hasData">
        <span>上海市轨道交通站点分布 · {{ currentLayerLabel }} · 经纬度散点坐标</span>
      </div>

      <!-- 聚类图例 -->
      <div class="map-legend" v-if="activeLayer === 'cluster' && clusterData.length">
        <div class="legend-title">聚类图例</div>
        <div class="legend-items">
          <div v-for="c in clusterColors" :key="c.label" class="legend-item">
            <span class="legend-dot" :style="{ background: c.color }"></span>
            <span>{{ c.label }}</span>
          </div>
        </div>
      </div>

      <!-- 热力图例 -->
      <div class="map-legend" v-else-if="activeLayer === 'heatmap' && clusterData.length">
        <div class="legend-title">客流热力</div>
        <div class="legend-gradient">
          <div class="gradient-bar"></div>
          <div class="gradient-labels">
            <span>低</span><span>中</span><span>高</span>
          </div>
        </div>
      </div>

      <!-- 客流图例 -->
      <div class="map-legend" v-else-if="activeLayer === 'flow' && stations.length">
        <div class="legend-title">客流分布</div>
        <div class="legend-size-items">
          <div class="size-row">
            <span class="size-dot size-sm"></span>
            <span>低客流</span>
          </div>
          <div class="size-row">
            <span class="size-dot size-md"></span>
            <span>中客流</span>
          </div>
          <div class="size-row">
            <span class="size-dot size-lg"></span>
            <span>高客流</span>
          </div>
        </div>
        <div class="legend-gradient" style="margin-top: 8px;">
          <div class="gradient-bar gradient-flow"></div>
          <div class="gradient-labels">
            <span>低</span><span>高</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情卡片 -->
    <Transition name="detail-slide">
      <div class="detail-panel glass-card" v-if="selectedStation">
        <div class="detail-header">
          <h4>📍 {{ selectedStation.name }}</h4>
          <button class="close-btn" @click="selectedStation = null">×</button>
        </div>
        <div class="detail-body">
          <div class="detail-row">
            <span class="detail-label">行政区</span>
            <span class="detail-value">{{ selectedStation.district || '上海市' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">经度</span>
            <span class="detail-value">{{ selectedStation.lng?.toFixed(6) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">纬度</span>
            <span class="detail-value">{{ selectedStation.lat?.toFixed(6) }}</span>
          </div>
          <div class="detail-row" v-if="selectedStation.flow != null">
            <span class="detail-label">总客流</span>
            <span class="detail-value highlight">{{ selectedStation.flow.toLocaleString() }}</span>
          </div>
          <!-- 客流占比条 -->
          <div class="flow-bar-wrap" v-if="selectedStation.flow">
            <div class="flow-bar-bg">
              <div class="flow-bar-fill" :style="{ width: selectedFlowPct + '%' }"></div>
            </div>
            <span class="flow-bar-label">占总客流 {{ selectedFlowPct.toFixed(1) }}%</span>
          </div>
          <!-- 排名 -->
          <div class="detail-row" v-if="selectedStationRank">
            <span class="detail-label">客流排名</span>
            <span class="detail-value rank-badge">
              🏅 第 {{ selectedStationRank }} 名 / {{ activeStationList.length }}
            </span>
          </div>
          <div class="detail-row" v-if="selectedStation.cluster !== undefined">
            <span class="detail-label">聚类</span>
            <span class="detail-value">
              <span class="cluster-tag" :style="{ background: getClusterColor(selectedStation.cluster) }">
                {{ selectedStation.cluster === -1 ? '噪声点' : `簇 ${selectedStation.cluster}` }}
              </span>
            </span>
          </div>
          <div class="detail-row" v-if="selectedStation.hotspot !== undefined">
            <span class="detail-label">状态</span>
            <span class="detail-value">
              <span :class="selectedStation.hotspot ? 'tag-hot' : 'tag-normal'">
                {{ selectedStation.hotspot ? '🔥 热点站' : '常规站点' }}
              </span>
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getStations, getClusterResults, getStationRank } from '@/api'

// ===== 响应式状态 =====
const mapChart = ref(null)
let chartInstance = null
const loading = ref(true)
const stations = ref([])
const clusterData = ref([])
const rankData = ref([])
const selectedStation = ref(null)
const activeLayer = ref('cluster')
const bubbleScale = ref(3)
const showLabels = ref(false)

const layers = [
  { key: 'cluster', icon: '🎯', label: '聚类视图' },
  { key: 'heatmap', icon: '🔥', label: '热力视图' },
  { key: 'flow', icon: '📊', label: '客流视图' },
]

const palette = [
  '#00e6a0', '#64a0ff', '#ff6b6b', '#ffd93d',
  '#a78bfa', '#f97316', '#06b6d4', '#ec4899',
  '#84cc16', '#8b5cf6',
]

// ===== 图表实例安全管理 =====
function ensureChart() {
  if (chartInstance && !chartInstance.isDisposed()) return chartInstance
  if (!mapChart.value) return null
  chartInstance = echarts.init(mapChart.value)
  chartInstance.on('click', (params) => {
    if (params.data?.stationInfo) selectedStation.value = params.data.stationInfo
  })
  return chartInstance
}

// ===== 计算属性 =====
const currentLayerLabel = computed(() =>
  layers.find(l => l.key === activeLayer.value)?.label || ''
)

const clusterColors = computed(() => {
  const labels = [...new Set(clusterData.value.map(d => d.cluster_label))]
    .filter(l => l !== -1).sort((a, b) => a - b)
  const colors = labels.map((l, i) => ({ label: `聚类 ${l}`, color: palette[i % palette.length] }))
  colors.push({ label: '噪声点', color: '#555' })
  return colors
})

const clusterCount = computed(() => {
  const s = new Set(clusterData.value.map(d => d.cluster_label))
  s.delete(-1)
  return s.size
})
const hotspotCount = computed(() => clusterData.value.filter(d => d.is_hotspot).length)
const noiseCount = computed(() => clusterData.value.filter(d => d.cluster_label === -1).length)
const clusterTotalFlow = computed(() => clusterData.value.reduce((s, d) => s + (d.total_flow || 0), 0))
const clusterMaxFlow = computed(() => Math.max(...clusterData.value.map(d => d.total_flow || 0), 0))
const clusterAvgFlow = computed(() => {
  const n = clusterData.value.length
  return n ? Math.round(clusterTotalFlow.value / n) : 0
})

// 客流视图：站点 + 排名预计算
const rankMap = computed(() => {
  const m = new Map()
  rankData.value.forEach(r => m.set(r.station__station_name || '', r.total_flow || 0))
  return m
})
const flowStationData = computed(() =>
  stations.value.map(s => ({
    name: s.station_name,
    flow: rankMap.value.get(s.station_name) || 0,
    lng: s.longitude,
    lat: s.latitude,
    district: s.district,
  })).sort((a, b) => b.flow - a.flow)
)
const flowTotal = computed(() => flowStationData.value.reduce((s, d) => s + d.flow, 0))
const flowMax = computed(() => flowStationData.value.length ? flowStationData.value[0].flow : 0)
const flowAvg = computed(() => {
  const n = flowStationData.value.length
  return n ? Math.round(flowTotal.value / n) : 0
})

// 图层感知的站点列表
const clusterStationList = computed(() =>
  clusterData.value
    .map(d => ({
      name: d.station_name || d.station?.station_name || '',
      flow: d.total_flow || 0,
      color: activeLayer.value === 'cluster'
        ? getClusterColor(d.cluster_label)
        : getFlowColor(d.total_flow || 0, clusterMaxFlow.value),
      cluster: d.cluster_label,
      hotspot: d.is_hotspot,
      lng: d.longitude,
      lat: d.latitude,
      district: d.station?.district,
    }))
    .sort((a, b) => b.flow - a.flow)
)

const flowStationList = computed(() =>
  flowStationData.value.map(s => ({
    ...s,
    color: getFlowColor(s.flow, flowMax.value),
  }))
)

const activeStationList = computed(() =>
  activeLayer.value === 'flow' ? flowStationList.value : clusterStationList.value
)

// 统计卡片 —— 随图层变化
const statCards = computed(() => {
  if (activeLayer.value === 'cluster') return [
    { value: clusterCount.value, label: '聚类簇', color: '#64a0ff' },
    { value: hotspotCount.value, label: '热点站', color: '#ff6b6b' },
    { value: noiseCount.value, label: '噪声点', color: '#888' },
    { value: formatNum(clusterTotalFlow.value), label: '总客流', color: '#00e6a0' },
  ]
  if (activeLayer.value === 'heatmap') return [
    { value: formatNum(clusterMaxFlow.value), label: '最大客流', color: '#ff6b6b' },
    { value: formatNum(clusterAvgFlow.value), label: '平均客流', color: '#64a0ff' },
    { value: hotspotCount.value, label: '热点站', color: '#ff6b6b' },
    { value: formatNum(clusterTotalFlow.value), label: '总客流', color: '#00e6a0' },
  ]
  return [
    { value: flowStationData.value.length, label: '站点数', color: '#64a0ff' },
    { value: formatNum(flowMax.value), label: '最大客流', color: '#ff6b6b' },
    { value: formatNum(flowAvg.value), label: '平均客流', color: '#ffd93d' },
    { value: formatNum(flowTotal.value), label: '总客流', color: '#00e6a0' },
  ]
})

const hasData = computed(() => {
  if (activeLayer.value === 'flow') return stations.value.length > 0
  return clusterData.value.length > 0
})

// 详情面板：排名 & 客流占比
const selectedStationRank = computed(() => {
  if (!selectedStation.value) return null
  const idx = activeStationList.value.findIndex(s => s.name === selectedStation.value.name)
  return idx >= 0 ? idx + 1 : null
})

const selectedFlowPct = computed(() => {
  if (!selectedStation.value?.flow) return 0
  const total = activeLayer.value === 'flow' ? flowTotal.value : clusterTotalFlow.value
  return total ? (selectedStation.value.flow / total) * 100 : 0
})

// ===== 工具函数 =====
function formatNum(n) {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function getClusterColor(label) {
  if (label === -1) return '#555'
  return palette[label % palette.length]
}

function getFlowColor(flow, maxFlow) {
  if (!maxFlow) return '#64a0ff'
  const ratio = flow / maxFlow
  if (ratio > 0.75) return '#ff6b6b'
  if (ratio > 0.5) return '#ffd93d'
  if (ratio > 0.25) return '#00e6a0'
  return '#64a0ff'
}

function selectStationFromList(s) {
  selectedStation.value = {
    name: s.name, lng: s.lng, lat: s.lat,
    flow: s.flow, district: s.district,
    cluster: s.cluster, hotspot: s.hotspot,
  }
}

// ===== 数据加载 =====
async function loadData() {
  loading.value = true
  try {
    const [sRes, cRes, rRes] = await Promise.all([
      getStations(), getClusterResults({}), getStationRank(null, 100),
    ])
    stations.value = sRes.data?.results || sRes.data || []
    clusterData.value = cRes.data || []
    rankData.value = rRes.data || []
  } catch (e) {
    console.error('地图数据加载失败', e)
  } finally {
    loading.value = false
    await nextTick()
    renderChart()
  }
}

// ===== 图表渲染 =====
function renderChart() {
  const inst = ensureChart()
  if (!inst) return
  if (!hasData.value) { inst.clear(); return }
  inst.setOption(buildOption(), true)
}

function getBounds() {
  const all = activeLayer.value === 'flow' ? stations.value : clusterData.value
  if (!all.length) return { xMin: 121.1, xMax: 121.9, yMin: 30.9, yMax: 31.5 }
  const lngs = all.map(d => d.longitude)
  const lats = all.map(d => d.latitude)
  const pad = 0.02
  return {
    xMin: Math.min(...lngs) - pad, xMax: Math.max(...lngs) + pad,
    yMin: Math.min(...lats) - pad, yMax: Math.max(...lats) + pad,
  }
}

function baseAxis() {
  const b = getBounds()
  return {
    xAxis: {
      type: 'value', min: b.xMin, max: b.xMax, name: '经度',
      nameTextStyle: { color: '#556', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(100,160,255,0.15)' } },
      splitLine: { lineStyle: { color: 'rgba(100,160,255,0.06)' } },
      axisLabel: { color: '#556', fontSize: 10, formatter: v => v.toFixed(2) },
    },
    yAxis: {
      type: 'value', min: b.yMin, max: b.yMax, name: '纬度',
      nameTextStyle: { color: '#556', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(100,160,255,0.15)' } },
      splitLine: { lineStyle: { color: 'rgba(100,160,255,0.06)' } },
      axisLabel: { color: '#556', fontSize: 10, formatter: v => v.toFixed(2) },
    },
    grid: { left: 60, right: 40, top: 40, bottom: 50 },
  }
}

function baseTooltip() {
  return {
    trigger: 'item',
    backgroundColor: 'rgba(15, 18, 42, 0.92)',
    borderColor: 'rgba(100, 160, 255, 0.3)',
    padding: [12, 16],
    textStyle: { color: '#e0e0e0', fontSize: 13 },
    formatter: (p) => {
      const info = p.data?.stationInfo
      if (!info) return p.name || ''
      let h = `<strong style="font-size:14px;color:#64a0ff">${info.name}</strong>`
      if (info.district) h += `<span style="color:#888;font-size:11px;margin-left:8px">${info.district}</span>`
      h += '<br/>'
      if (info.flow != null) h += `客流量：<span style="color:#00e6a0;font-weight:bold">${info.flow.toLocaleString()}</span><br/>`
      if (info.cluster !== undefined) h += `聚类：${info.cluster === -1 ? '<span style="color:#888">噪声点</span>' : '<span style="color:' + getClusterColor(info.cluster) + '">簇 ' + info.cluster + '</span>'}<br/>`
      if (info.hotspot) h += `<span style="color:#ff6b6b">🔥 热点站</span><br/>`
      h += `<span style="color:#666;font-size:11px">经度 ${info.lng?.toFixed(4)} · 纬度 ${info.lat?.toFixed(4)}</span>`
      return h
    },
  }
}

function makeInfo(d) {
  return {
    name: d.station_name || d.station?.station_name || '',
    lng: d.longitude, lat: d.latitude,
    flow: d.total_flow, cluster: d.cluster_label,
    hotspot: d.is_hotspot, district: d.station?.district,
  }
}

function buildOption() {
  if (activeLayer.value === 'cluster') return buildCluster()
  if (activeLayer.value === 'heatmap') return buildHeatmap()
  return buildFlow()
}

// ===== 聚类视图 =====
function buildCluster() {
  const groups = {}
  clusterData.value.forEach(d => {
    const l = d.cluster_label
    if (!groups[l]) groups[l] = []
    groups[l].push(d)
  })

  // 动态 symbolSize 范围
  const allFlows = clusterData.value.map(d => d.total_flow || 0)
  const minF = Math.min(...allFlows, 0)
  const maxF = Math.max(...allFlows, 1)
  const sizeScale = (flow) => {
    const ratio = maxF > minF ? (flow - minF) / (maxF - minF) : 0.5
    return 8 + ratio * 30 * (bubbleScale.value / 5)
  }

  const series = Object.keys(groups).sort((a, b) => a - b).map(label => {
    const lbl = parseInt(label)
    const color = getClusterColor(lbl)
    return {
      name: lbl === -1 ? '噪声点' : `聚类 ${lbl}`,
      type: 'scatter',
      data: groups[label].map(d => ({
        name: d.station_name || d.station?.station_name || '',
        value: [d.longitude, d.latitude, d.total_flow || 0],
        stationInfo: makeInfo(d),
      })),
      symbolSize: val => sizeScale(val[2]),
      itemStyle: {
        color, borderColor: 'rgba(255,255,255,0.25)', borderWidth: 1.5,
        shadowBlur: 10, shadowColor: color + '60',
      },
      emphasis: {
        itemStyle: { borderWidth: 3, borderColor: '#fff', shadowBlur: 25 },
        label: { show: true },
      },
      label: {
        show: showLabels.value, formatter: '{b}', position: 'right',
        fontSize: 10, color: '#ccc',
      },
    }
  })

  const hotspots = clusterData.value.filter(d => d.is_hotspot)
  if (hotspots.length) {
    series.push({
      name: '🔥 热点',
      type: 'effectScatter',
      data: hotspots.map(d => ({
        name: d.station_name || d.station?.station_name || '',
        value: [d.longitude, d.latitude, d.total_flow || 0],
        stationInfo: makeInfo(d),
      })),
      symbolSize: val => sizeScale(val[2]) * 1.2,
      showEffectOn: 'render',
      rippleEffect: { brushType: 'stroke', scale: 4, period: 4 },
      itemStyle: { color: '#ff6b6b', shadowBlur: 18, shadowColor: 'rgba(255,107,107,0.5)' },
      label: {
        show: true, formatter: '{b}', position: 'top',
        fontSize: 11, color: '#ffcc00', fontWeight: 'bold',
        textShadowBlur: 4, textShadowColor: '#000',
      },
    })
  }

  return { backgroundColor: 'transparent', tooltip: baseTooltip(), ...baseAxis(), series }
}

// ===== 热力视图 =====
function buildHeatmap() {
  const data = clusterData.value.map(d => ({
    name: d.station_name || d.station?.station_name || '',
    value: [d.longitude, d.latitude, d.total_flow || 0],
    stationInfo: makeInfo(d),
  }))
  const maxFlow = Math.max(...clusterData.value.map(d => d.total_flow || 0), 1)

  return {
    backgroundColor: 'transparent', tooltip: baseTooltip(), ...baseAxis(),
    visualMap: {
      min: 0, max: maxFlow, calculable: true, orient: 'vertical', right: 12, bottom: 60,
      inRange: {
        color: ['#0d47a1', '#1565c0', '#1e88e5', '#42a5f5', '#66bb6a', '#ffee58', '#ffa726', '#ef5350', '#d32f2f'],
      },
      textStyle: { color: '#888' }, text: ['高客流', '低客流'],
    },
    series: [{
      type: 'scatter', data,
      symbolSize: val => {
        const ratio = maxFlow > 0 ? (val[2] || 0) / maxFlow : 0.5
        return 8 + ratio * 30 * (bubbleScale.value / 5)
      },
      itemStyle: { borderColor: 'rgba(255,255,255,0.15)', borderWidth: 1 },
      label: { show: showLabels.value, formatter: '{b}', position: 'right', fontSize: 10, color: '#ccc' },
      emphasis: { itemStyle: { borderWidth: 3, borderColor: '#fff' }, label: { show: true } },
    }],
  }
}

// ===== 客流视图 =====
function buildFlow() {
  const ranked = flowStationData.value
  const data = ranked.map(s => ({
    name: s.name,
    value: [s.lng, s.lat, s.flow],
    stationInfo: { name: s.name, lng: s.lng, lat: s.lat, flow: s.flow, district: s.district },
  }))
  const maxFlow = flowMax.value || 1

  // 前 5 名始终显示标签
  const top5 = new Set(ranked.slice(0, 5).map(s => s.name))

  return {
    backgroundColor: 'transparent', tooltip: baseTooltip(), ...baseAxis(),
    visualMap: {
      min: 0, max: maxFlow, calculable: true, orient: 'vertical', right: 12, bottom: 60,
      inRange: {
        symbolSize: [8, 38],
        color: ['rgba(100,160,255,0.3)', '#64a0ff', '#00e6a0', '#ffd93d', '#ff6b6b'],
      },
      textStyle: { color: '#888' }, text: ['高客流', '低客流'],
    },
    series: [{
      type: 'scatter', data,
      itemStyle: { borderColor: 'rgba(255,255,255,0.15)', borderWidth: 1 },
      label: {
        show: showLabels.value,
        formatter: (p) => {
          if (top5.has(p.name)) return p.name
          return showLabels.value ? p.name : ''
        },
        position: 'right', fontSize: 10, color: '#ccc',
      },
      emphasis: { itemStyle: { borderWidth: 3, borderColor: '#fff' }, label: { show: true } },
    }],
  }
}

// ===== 生命周期 =====
watch([activeLayer, bubbleScale, showLabels], () => renderChart())

let resizeOb = null
onMounted(async () => {
  await loadData()
  resizeOb = new ResizeObserver(() => {
    if (chartInstance && !chartInstance.isDisposed()) chartInstance.resize()
  })
  if (mapChart.value) resizeOb.observe(mapChart.value)
})

onUnmounted(() => {
  resizeOb?.disconnect()
  if (chartInstance && !chartInstance.isDisposed()) chartInstance.dispose()
  chartInstance = null
})
</script>

<style lang="scss" scoped>
.map-view {
  display: grid;
  grid-template-columns: 280px 1fr;
  grid-template-rows: 1fr;
  gap: 20px;
  height: 100%;
  position: relative;
}

.control-panel {
  padding: 22px 18px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 4px; }
}

.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  h3 { font-size: 16px; font-weight: 600; color: #fff; margin: 0; }
}

.badge-info {
  background: rgba(100,160,255,0.15); color: #64a0ff;
  font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500;
}

.control-group {
  display: flex; flex-direction: column; gap: 8px;
  label { font-size: 11px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
}

.layer-toggles { display: flex; flex-direction: column; gap: 6px; }

.layer-btn {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  border-radius: 10px; background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06); color: rgba(255,255,255,0.55);
  cursor: pointer; transition: all 0.3s; font-size: 13px;
  .layer-icon { font-size: 16px; }
  &:hover { background: rgba(100,160,255,0.08); color: #fff; }
  &.active { background: rgba(100,160,255,0.12); border-color: rgba(100,160,255,0.3); color: #64a0ff; box-shadow: 0 0 15px rgba(100,160,255,0.08); }
}

.range-slider {
  -webkit-appearance: none; appearance: none; width: 100%; height: 4px;
  background: rgba(255,255,255,0.1); border-radius: 4px; outline: none;
  &::-webkit-slider-thumb {
    -webkit-appearance: none; width: 16px; height: 16px;
    border-radius: 50%; background: #64a0ff; cursor: pointer;
    box-shadow: 0 0 8px rgba(100,160,255,0.4);
  }
}

.range-val { font-size: 12px; color: rgba(255,255,255,0.35); text-align: right; }

.toggle-switch {
  width: 44px; height: 24px; border-radius: 12px;
  background: rgba(255,255,255,0.08); cursor: pointer;
  position: relative; transition: all 0.3s;
  &.on { background: rgba(100,160,255,0.35); .toggle-knob { transform: translateX(20px); background: #64a0ff; } }
}

.toggle-knob {
  width: 20px; height: 20px; border-radius: 50%;
  background: rgba(255,255,255,0.35); position: absolute;
  top: 2px; left: 2px; transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1);
}

.stat-cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }

.mini-stat {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);
  border-radius: 10px; padding: 10px 6px; text-align: center;
}

.mini-val { font-size: 17px; font-weight: 700; }
.mini-label { font-size: 10px; color: rgba(255,255,255,0.35); margin-top: 3px; }

.hint-box {
  background: rgba(255,165,0,0.06); border: 1px solid rgba(255,165,0,0.15);
  border-radius: 10px; padding: 12px; font-size: 12px;
  color: rgba(255,200,100,0.7); line-height: 1.6;
}

.map-container { position: relative; overflow: hidden; min-height: 500px; }
.chart-area { width: 100%; height: 100%; }

.map-loading {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  display: flex; flex-direction: column; align-items: center; gap: 14px; z-index: 10;
  span { font-size: 13px; color: rgba(255,255,255,0.45); letter-spacing: 1px; }
}

.map-empty {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  display: flex; flex-direction: column; align-items: center; gap: 10px; z-index: 10;
}
.empty-icon { font-size: 48px; opacity: 0.3; }
.empty-text { font-size: 15px; color: rgba(255,255,255,0.4); font-weight: 500; }
.empty-hint { font-size: 12px; color: rgba(255,255,255,0.2); }

.loading-pulse {
  width: 50px; height: 50px; border-radius: 50%;
  background: rgba(100,160,255,0.15); animation: map-pulse 1.5s ease-in-out infinite;
}

@keyframes map-pulse {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.6); opacity: 0.1; }
}

.coord-bar {
  position: absolute; bottom: 8px; right: 12px;
  font-size: 10px; color: rgba(255,255,255,0.2); letter-spacing: 0.5px;
}

.map-legend {
  position: absolute; bottom: 30px; left: 70px;
  background: rgba(15,18,42,0.88); backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;
  padding: 14px 18px; z-index: 5;
}

.legend-title { font-size: 11px; color: rgba(255,255,255,0.4); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }
.legend-items { display: flex; flex-direction: column; gap: 5px; }
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: rgba(255,255,255,0.6); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

.legend-size-items { display: flex; flex-direction: column; gap: 6px; }
.size-row { display: flex; align-items: center; gap: 10px; font-size: 12px; color: rgba(255,255,255,0.5); }
.size-dot { border-radius: 50%; background: #64a0ff; flex-shrink: 0; }
.size-sm { width: 8px; height: 8px; opacity: 0.4; }
.size-md { width: 14px; height: 14px; opacity: 0.65; }
.size-lg { width: 22px; height: 22px; opacity: 1; }

.gradient-bar { width: 120px; height: 8px; border-radius: 4px; background: linear-gradient(90deg, #0d47a1, #42a5f5, #66bb6a, #ffee58, #ef5350); }
.gradient-flow { background: linear-gradient(90deg, rgba(100,160,255,0.3), #64a0ff, #00e6a0, #ffd93d, #ff6b6b); }
.gradient-labels { display: flex; justify-content: space-between; font-size: 10px; color: rgba(255,255,255,0.35); margin-top: 4px; }

.detail-panel { position: absolute; top: 20px; right: 20px; width: 280px; padding: 18px; z-index: 10; }
.detail-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; h4 { font-size: 14px; color: #fff; margin: 0; } }

.close-btn {
  width: 24px; height: 24px; border-radius: 50%;
  background: rgba(255,255,255,0.08); border: none;
  color: rgba(255,255,255,0.5); font-size: 16px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.2s;
  &:hover { background: rgba(255,85,85,0.2); color: #ff5555; }
}

.detail-body { display: flex; flex-direction: column; gap: 10px; }
.detail-row { display: flex; align-items: center; justify-content: space-between; }
.detail-label { font-size: 12px; color: rgba(255,255,255,0.4); }
.detail-value { font-size: 13px; color: rgba(255,255,255,0.85); font-weight: 500; &.highlight { color: #00e6a0; font-weight: 700; } }

/* 客流占比条 */
.flow-bar-wrap { display: flex; flex-direction: column; gap: 4px; }
.flow-bar-bg { height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.flow-bar-fill { height: 100%; background: linear-gradient(90deg, #64a0ff, #00e6a0); border-radius: 2px; transition: width 0.5s ease; }
.flow-bar-label { font-size: 10px; color: rgba(255,255,255,0.3); text-align: right; }

.rank-badge { color: #ffd93d !important; }

.cluster-tag { padding: 2px 10px; border-radius: 12px; font-size: 11px; color: #fff; }
.tag-hot { color: #ff6b6b; font-weight: 600; }
.tag-normal { color: rgba(255,255,255,0.5); }

.detail-slide-enter-active { animation: detail-in 0.35s ease-out; }
.detail-slide-leave-active { animation: detail-out 0.25s ease-in forwards; }

@keyframes detail-in {
  from { opacity: 0; transform: translateY(-15px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes detail-out {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to { opacity: 0; transform: translateY(-15px) scale(0.95); }
}
</style>
