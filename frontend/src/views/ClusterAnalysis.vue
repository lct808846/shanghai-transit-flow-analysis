<template>
  <div class="cluster-analysis">
    <!-- 操作面板 -->
    <div class="control-panel glass-card">
      <div class="panel-title">
        <span class="icon">⚙️</span>
        DBSCAN 聚类参数
      </div>
      <div class="controls-row">
        <div class="control-group">
          <label>邻域半径 (eps)</label>
          <input type="range" v-model.number="eps" min="0.002" max="0.03" step="0.001" />
          <span class="value-badge">{{ eps.toFixed(3) }} (~{{ (eps * 100).toFixed(1) }}km)</span>
        </div>
        <div class="control-group">
          <label>最小样本数</label>
          <input type="range" v-model.number="minSamples" min="1" max="10" step="1" />
          <span class="value-badge">{{ minSamples }}</span>
        </div>
        <div class="control-group">
          <label>分析日期</label>
          <input type="date" v-model="analysisDate" class="date-input" />
        </div>
        <button class="run-btn" @click="runAnalysis" :disabled="running">
          <span v-if="running" class="spinner"></span>
          <span v-else>🚀</span>
          {{ running ? '分析中...' : '执行聚类' }}
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="pageLoading" class="glass-card empty-state">
      <div class="empty-icon"><span class="spinner-lg"></span></div>
      <p>正在加载聚类数据...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="clusterData.length === 0" class="glass-card empty-state">
      <div class="empty-icon">🔬</div>
      <p>暂无聚类结果，请调整参数后点击「执行聚类」</p>
    </div>

    <template v-else>
      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-card glass-card" v-for="stat in statCards" :key="stat.label">
          <div class="stat-icon">{{ stat.icon }}</div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <!-- 聚类散点图 -->
        <div class="chart-container glass-card chart-large">
          <div class="chart-header">
            <h3><span class="dot hot"></span>站点空间聚类分布</h3>
            <div class="legend-row">
              <span class="legend-item" v-for="lbl in clusterLabels" :key="lbl">
                <span class="legend-dot" :style="{ background: getClusterColor(lbl) }"></span>
                {{ lbl === -1 ? '噪声点' : `Cluster ${lbl}` }}
              </span>
            </div>
          </div>
          <div ref="scatterChart" class="chart-body"></div>
        </div>

        <!-- 聚类画像: 站点数 + 总客流 + 均客流 -->
        <div class="chart-container glass-card chart-medium">
          <div class="chart-header">
            <h3><span class="dot info"></span>聚类画像对比</h3>
          </div>
          <div ref="barChart" class="chart-body"></div>
        </div>

        <!-- 各聚类站点分布饼图 -->
        <div class="chart-container glass-card chart-medium">
          <div class="chart-header">
            <h3><span class="dot warn"></span>聚类站点分布</h3>
          </div>
          <div ref="pieChart" class="chart-body"></div>
        </div>
      </div>

      <!-- 聚类详情表 -->
      <div class="detail-section glass-card">
        <div class="chart-header">
          <h3><span class="dot"></span>聚类站点明细</h3>
          <div class="filter-tabs">
            <button
              v-for="tab in filterTabs"
              :key="tab.value"
              :class="['tab-btn', { active: activeFilter === tab.value }]"
              @click="activeFilter = tab.value"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>站点名称</th>
                <th>聚类标签</th>
                <th>经度</th>
                <th>纬度</th>
                <th>总客流</th>
                <th>热点</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredData" :key="item.id" :class="{ 'row-hotspot': item.is_hotspot }">
                <td class="station-name">{{ item.station_name }}</td>
                <td>
                  <span class="cluster-tag" :style="{ background: getClusterColor(item.cluster_label) }">
                    {{ item.cluster_label === -1 ? '噪声' : `C${item.cluster_label}` }}
                  </span>
                </td>
                <td>{{ item.longitude.toFixed(4) }}</td>
                <td>{{ item.latitude.toFixed(4) }}</td>
                <td class="flow-cell">{{ item.total_flow?.toLocaleString() }}</td>
                <td>
                  <span v-if="item.is_hotspot" class="badge badge-hot">🔥 热点</span>
                  <span v-else class="badge badge-normal">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getClusterResults, getClusterSummary, runClusterAnalysis } from '../api'

const clusterColors = [
  '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
]
const noiseColor = 'rgba(107, 114, 128, 0.5)'

const tooltipStyle = {
  backgroundColor: 'rgba(13,18,51,0.95)',
  borderColor: 'rgba(99,102,241,0.4)',
  borderWidth: 1,
  textStyle: { color: '#e2e8f0', fontSize: 13 },
  extraCssText: 'border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);',
}

// 状态
const eps = ref(0.012)
const minSamples = ref(2)
const analysisDate = ref(new Date().toISOString().slice(0, 10))
const running = ref(false)
const pageLoading = ref(false)
const clusterData = ref([])
const summaryData = ref([])
const activeFilter = ref('all')

// 图表 refs
const scatterChart = ref(null)
const barChart = ref(null)
const pieChart = ref(null)
let scatterInstance = null
let barInstance = null
let pieInstance = null

const filterTabs = [
  { label: '全部', value: 'all' },
  { label: '仅热点', value: 'hotspot' },
  { label: '仅噪声', value: 'noise' },
]

// 从实际数据中提取聚类标签(含 -1 噪声)，按标签排序
const clusterLabels = computed(() => {
  const labels = [...new Set(clusterData.value.map(d => d.cluster_label))]
  return labels.sort((a, b) => a - b)
})

const filteredData = computed(() => {
  if (activeFilter.value === 'hotspot') return clusterData.value.filter(d => d.is_hotspot)
  if (activeFilter.value === 'noise') return clusterData.value.filter(d => d.cluster_label === -1)
  return clusterData.value
})

const statCards = computed(() => {
  const total = clusterData.value.length
  const clusters = clusterLabels.value.filter(l => l !== -1).length
  const noise = clusterData.value.filter(d => d.cluster_label === -1).length
  const hotspots = clusterData.value.filter(d => d.is_hotspot).length
  const totalFlow = clusterData.value.reduce((s, d) => s + d.total_flow, 0)
  return [
    { icon: '📍', label: '总站点数', value: total },
    { icon: '🎯', label: '聚类数量', value: clusters },
    { icon: '🔕', label: '噪声点', value: noise },
    { icon: '🔥', label: '热点站点', value: hotspots },
    { icon: '📊', label: '总客流量', value: totalFlow.toLocaleString() },
  ]
})

function getClusterColor(label) {
  if (label === -1) return noiseColor
  return clusterColors[label % clusterColors.length]
}

async function fetchData() {
  const isInitial = clusterData.value.length === 0
  if (isInitial) pageLoading.value = true
  try {
    const [resData, resSummary] = await Promise.all([
      getClusterResults(),
      getClusterSummary(),
    ])
    clusterData.value = resData.data
    summaryData.value = resSummary.data
  } catch (e) {
    console.error('获取聚类数据失败:', e)
  } finally {
    pageLoading.value = false
  }
  if (clusterData.value.length > 0) {
    await nextTick()
    renderScatter()
    renderBar()
    renderPie()
  }
}

async function runAnalysis() {
  running.value = true
  try {
    await runClusterAnalysis({
      eps: eps.value,
      min_samples: minSamples.value,
      date: analysisDate.value || null,
    })
    await fetchData()
  } catch (e) {
    console.error('聚类执行失败:', e)
  } finally {
    running.value = false
  }
}

function ensureChart(ref, instance) {
  if (!ref.value) return null
  if (instance && !instance.isDisposed?.()) {
    try { instance.getDom(); return instance } catch (_) { /* stale */ }
  }
  return echarts.init(ref.value)
}

function renderScatter() {
  if (!scatterChart.value) return
  scatterInstance = ensureChart(scatterChart, scatterInstance)

  if (clusterData.value.length === 0) { scatterInstance.clear(); return }

  // 按聚类分组
  const groups = {}
  clusterData.value.forEach(d => {
    const key = d.cluster_label
    if (!groups[key]) groups[key] = []
    groups[key].push(d)
  })

  // 动态 symbolSize 基于数据范围
  const flows = clusterData.value.map(d => d.total_flow)
  const minFlow = Math.min(...flows)
  const maxFlow = Math.max(...flows) || 1
  const flowRange = maxFlow - minFlow || 1

  const series = Object.entries(groups)
    .sort(([a], [b]) => parseInt(a) - parseInt(b))
    .map(([label, items]) => {
      const l = parseInt(label)
      return {
        name: l === -1 ? '噪声' : `Cluster ${l}`,
        type: 'scatter',
        data: items.map(d => ({
          value: [d.longitude, d.latitude, d.total_flow],
          name: d.station_name,
          hotspot: d.is_hotspot,
        })),
        symbolSize: (val) => {
          const ratio = (val[2] - minFlow) / flowRange
          return Math.round(8 + ratio * 28)
        },
        itemStyle: {
          color: l === -1 ? noiseColor : clusterColors[l % clusterColors.length],
          borderColor: 'rgba(255,255,255,0.3)',
          borderWidth: 1,
          shadowBlur: l === -1 ? 0 : 8,
          shadowColor: l === -1 ? 'transparent' : clusterColors[l % clusterColors.length] + '66',
        },
        emphasis: {
          itemStyle: { borderColor: '#fff', borderWidth: 2, shadowBlur: 15 }
        },
      }
    })

  scatterInstance.resize()
  scatterInstance.setOption({
    tooltip: {
      trigger: 'item',
      ...tooltipStyle,
      formatter: (p) => {
        const hot = p.data.hotspot ? ' <span style="color:#ef4444">🔥热点</span>' : ''
        return `<b>${p.name}</b>${hot}<br/>
          经度: ${p.value[0].toFixed(4)}<br/>
          纬度: ${p.value[1].toFixed(4)}<br/>
          客流量: <b>${p.value[2].toLocaleString()}</b><br/>
          聚类: ${p.seriesName}`
      }
    },
    grid: { top: 20, right: 30, bottom: 40, left: 65 },
    xAxis: {
      name: '经度',
      nameTextStyle: { color: '#94a3b8' },
      scale: true,
      axisLabel: { color: '#94a3b8', formatter: v => v.toFixed(2) },
      axisLine: { lineStyle: { color: 'rgba(99,102,241,0.2)' } },
      splitLine: { lineStyle: { color: 'rgba(99,102,241,0.05)' } },
    },
    yAxis: {
      name: '纬度',
      nameTextStyle: { color: '#94a3b8' },
      scale: true,
      axisLabel: { color: '#94a3b8', formatter: v => v.toFixed(2) },
      axisLine: { lineStyle: { color: 'rgba(99,102,241,0.2)' } },
      splitLine: { lineStyle: { color: 'rgba(99,102,241,0.05)' } },
    },
    series,
    animationDuration: 1200,
    animationEasing: 'elasticOut',
  }, true)
}

function renderBar() {
  if (!barChart.value) return
  barInstance = ensureChart(barChart, barInstance)

  const sorted = [...summaryData.value]
    .filter(s => s.cluster_label !== -1)
    .sort((a, b) => b.total_flow - a.total_flow)

  if (sorted.length === 0) { barInstance.clear(); return }

  barInstance.resize()
  barInstance.setOption({
    tooltip: {
      trigger: 'axis',
      ...tooltipStyle,
      formatter(params) {
        const c = params[0]?.axisValue
        let html = `<b>${c}</b>`
        params.forEach(p => {
          html += `<br/>${p.marker} ${p.seriesName}: <b>${p.value?.toLocaleString()}</b>`
        })
        return html
      }
    },
    legend: {
      data: ['总客流', '站点数', '平均客流'],
      top: 0,
      textStyle: { color: '#94a3b8', fontSize: 11 },
      itemWidth: 12, itemHeight: 8,
    },
    grid: { top: 40, right: 60, bottom: 30, left: 55 },
    xAxis: {
      type: 'category',
      data: sorted.map(s => `C${s.cluster_label}`),
      axisLabel: { color: '#94a3b8' },
      axisLine: { lineStyle: { color: 'rgba(99,102,241,0.2)' } },
    },
    yAxis: [
      {
        type: 'value', name: '客流',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: 'rgba(99,102,241,0.2)' } },
        splitLine: { lineStyle: { color: 'rgba(99,102,241,0.05)' } },
      },
      {
        type: 'value', name: '站点数',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: 'rgba(99,102,241,0.2)' } },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '总客流', type: 'bar', yAxisIndex: 0,
        data: sorted.map(s => ({
          value: s.total_flow,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: s.is_hotspot ? '#ef4444' : '#6366f1' },
              { offset: 1, color: s.is_hotspot ? '#ef444433' : '#6366f133' },
            ]),
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barWidth: '35%',
      },
      {
        name: '站点数', type: 'bar', yAxisIndex: 1,
        data: sorted.map(s => ({
          value: s.station_count,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#06b6d4' },
              { offset: 1, color: '#06b6d433' },
            ]),
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barWidth: '25%',
      },
      {
        name: '平均客流', type: 'line', yAxisIndex: 0,
        data: sorted.map(s => s.station_count > 0 ? Math.round(s.total_flow / s.station_count) : 0),
        smooth: true,
        symbol: 'circle', symbolSize: 8,
        lineStyle: { color: '#f59e0b', width: 2 },
        itemStyle: { color: '#f59e0b' },
      },
    ],
    animationDuration: 1000,
  }, true)
}

function renderPie() {
  if (!pieChart.value) return
  pieInstance = ensureChart(pieChart, pieInstance)

  // 每个聚类(含噪声)的站点数
  const groups = {}
  clusterData.value.forEach(d => {
    const label = d.cluster_label === -1 ? '噪声点' : `Cluster ${d.cluster_label}`
    groups[label] = (groups[label] || 0) + 1
  })

  const pieData = Object.entries(groups).map(([name, count]) => {
    const isNoise = name === '噪声点'
    const idx = isNoise ? -1 : parseInt(name.replace('Cluster ', ''))
    return {
      value: count,
      name: isNoise ? '噪声点' : `C${idx} (${count}站)`,
      itemStyle: { color: getClusterColor(idx) },
    }
  })

  if (pieData.length === 0) { pieInstance.clear(); return }

  pieInstance.resize()
  pieInstance.setOption({
    tooltip: {
      trigger: 'item',
      ...tooltipStyle,
      formatter: p => `<b>${p.name}</b><br/>站点数: <b>${p.value}</b> (${p.percent}%)`,
    },
    series: [{
      type: 'pie',
      radius: ['42%', '70%'],
      center: ['50%', '52%'],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#0a0e27',
        borderWidth: 3,
      },
      label: {
        color: '#cbd5e1',
        fontSize: 12,
        formatter: '{b}\n{d}%',
      },
      labelLine: {
        lineStyle: { color: 'rgba(99,102,241,0.3)' },
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 20,
          shadowColor: 'rgba(99,102,241,0.5)',
        },
      },
      data: pieData,
    }],
    animationDuration: 1200,
  }, true)
}

function handleResize() {
  scatterInstance?.resize()
  barInstance?.resize()
  pieInstance?.resize()
}

onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  scatterInstance?.dispose()
  barInstance?.dispose()
  pieInstance?.dispose()
})
</script>

<style lang="scss" scoped>
.cluster-analysis {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 20px; text-align: center;
  .empty-icon { font-size: 42px; margin-bottom: 14px; opacity: 0.7; }
  p { color: #64748b; font-size: 14px; }
}

.spinner-lg {
  display: inline-block; width: 32px; height: 32px;
  border: 3px solid rgba(99,102,241,0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

// 操作面板
.control-panel {
  padding: 20px 24px;

  .panel-title {
    font-size: 15px;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;

    .icon { font-size: 18px; }
  }

  .controls-row {
    display: flex;
    align-items: flex-end;
    gap: 24px;
    flex-wrap: wrap;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 180px;

    label {
      font-size: 12px;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    input[type="range"] {
      -webkit-appearance: none;
      appearance: none;
      height: 4px;
      background: rgba(99, 102, 241, 0.2);
      border-radius: 2px;
      outline: none;

      &::-webkit-slider-thumb {
        -webkit-appearance: none;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #6366f1;
        cursor: pointer;
        box-shadow: 0 0 8px rgba(99, 102, 241, 0.5);
      }
    }

    .date-input {
      background: rgba(99, 102, 241, 0.1);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 8px;
      padding: 6px 12px;
      color: #e2e8f0;
      font-size: 13px;
      outline: none;

      &:focus {
        border-color: rgba(99, 102, 241, 0.5);
      }
    }

    .value-badge {
      font-size: 12px;
      color: #6366f1;
      font-weight: 600;
      font-family: 'Courier New', monospace;
    }
  }

  .run-btn {
    padding: 10px 28px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border: none;
    border-radius: 10px;
    color: white;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);

    &:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
    }

    &:disabled {
      opacity: 0.6;
      cursor: wait;
    }

    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
  }
}

// 统计卡片
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.stat-card {
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: transform 0.3s ease;

  &:hover {
    transform: translateY(-3px);
  }

  .stat-icon {
    font-size: 28px;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(99, 102, 241, 0.1);
    border-radius: 12px;
  }

  .stat-info {
    .stat-value {
      font-size: 24px;
      font-weight: 700;
      background: linear-gradient(135deg, #6366f1, #06b6d4);
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .stat-label {
      font-size: 12px;
      color: #94a3b8;
      margin-top: 2px;
    }
  }
}

// 图表区
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 20px;
}

.chart-container {
  padding: 20px;

  &.chart-large {
    grid-column: 1 / -1;
  }

  .chart-header {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;

    h3 {
      font-size: 15px;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
      background: #6366f1;

      &.hot { background: #ef4444; }
      &.info { background: #06b6d4; }
      &.warn { background: #f59e0b; }
    }

    .legend-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;

      .legend-item {
        font-size: 11px;
        color: #94a3b8;
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .legend-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
      }
    }
  }

  .chart-body {
    width: 100%;
    height: 340px;
  }
}

// 表格区
.detail-section {
  padding: 20px;

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      font-size: 15px;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 8px;

      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        background: #6366f1;
      }
    }
  }

  .filter-tabs {
    display: flex;
    gap: 8px;

    .tab-btn {
      padding: 6px 16px;
      border: 1px solid rgba(99, 102, 241, 0.2);
      background: transparent;
      color: #94a3b8;
      border-radius: 20px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.25s ease;

      &.active, &:hover {
        background: rgba(99, 102, 241, 0.15);
        border-color: rgba(99, 102, 241, 0.5);
        color: #6366f1;
      }
    }
  }
}

.table-wrapper {
  max-height: 400px;
  overflow-y: auto;
  border-radius: 8px;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.3);
    border-radius: 2px;
  }

  table {
    width: 100%;
    border-collapse: collapse;

    thead {
      position: sticky;
      top: 0;
      z-index: 1;

      th {
        padding: 10px 16px;
        text-align: left;
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        background: rgba(13, 18, 51, 0.95);
        border-bottom: 1px solid rgba(99, 102, 241, 0.1);
      }
    }

    tbody {
      tr {
        transition: background 0.2s;
        border-bottom: 1px solid rgba(99, 102, 241, 0.05);

        &:hover {
          background: rgba(99, 102, 241, 0.05);
        }

        &.row-hotspot {
          background: rgba(239, 68, 68, 0.04);
        }
      }

      td {
        padding: 10px 16px;
        font-size: 13px;
        color: #cbd5e1;
      }

      .station-name {
        font-weight: 500;
        color: #e2e8f0;
      }

      .flow-cell {
        font-family: 'Courier New', monospace;
        font-weight: 600;
        color: #6366f1;
      }
    }
  }
}

.cluster-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: white;
}

.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;

  &.badge-hot {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  &.badge-normal {
    color: #475569;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-grid {
    grid-template-columns: 1fr;
  }
  .controls-row {
    flex-direction: column;
  }
}
</style>
