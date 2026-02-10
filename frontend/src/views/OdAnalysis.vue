<template>
  <div class="od-analysis">
    <!-- 筛选面板 -->
    <div class="glass-card filter-panel">
      <div class="filter-group">
        <label>📅 日期范围</label>
        <div class="date-combo">
          <div class="date-mode-toggle">
            <button class="mode-btn" :class="{ active: dateMode === 'day' }" @click="dateMode = 'day'">日</button>
            <button class="mode-btn" :class="{ active: dateMode === 'month' }" @click="dateMode = 'month'">月</button>
          </div>
          <input v-if="dateMode === 'day'" type="date" v-model="selectedDate" class="input-field" />
          <input v-else type="month" v-model="selectedMonth" class="input-field" />
        </div>
      </div>
      <button class="btn-primary" @click="loadData" :disabled="dataLoading">
        <span v-if="dataLoading" class="spinner-sm"></span>
        <span v-else>🔍</span>
        {{ dataLoading ? '查询中...' : '查询' }}
      </button>
    </div>

    <!-- 空状态: 无数据 -->
    <div v-if="hasLoaded && odList.length === 0 && !dataLoading" class="glass-card empty-state">
      <div class="empty-icon">📭</div>
      <p>当前筛选条件下暂无 OD 数据</p>
    </div>

    <!-- 有数据时展示图表 -->
    <template v-if="odList.length > 0">
      <!-- 第一行: 桑基图 + 站点热度 -->
      <div class="charts-row">
        <!-- 桑基图 -->
        <div class="glass-card chart-card chart-main">
          <div class="card-header">
            <div class="header-left">
              <span class="header-dot purple"></span>
              <h3>OD 客流流向图（Top 15 路线）</h3>
            </div>
            <div class="flow-summary">
              <span class="summary-item">
                <span class="summary-dot blue"></span>
                {{ uniqueOrigins }} 出发站
              </span>
              <span class="summary-item">
                <span class="summary-dot cyan"></span>
                {{ uniqueDests }} 到达站
              </span>
            </div>
          </div>
          <div ref="sankeyRef" class="chart-container"></div>
        </div>

        <!-- 站点热度图 -->
        <div class="glass-card chart-card chart-side">
          <div class="card-header">
            <div class="header-left">
              <span class="header-dot orange"></span>
              <h3>站点 OD 热度 Top10</h3>
            </div>
          </div>
          <div ref="heatRef" class="chart-container heat-chart-container"></div>
        </div>
      </div>

      <!-- 第二行: OD 明细表 -->
      <div class="glass-card chart-card chart-wide">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot green"></span>
            <h3>OD 客流明细</h3>
          </div>
          <span class="record-count">共 {{ odList.length }} 条记录</span>
        </div>
        <div class="od-table-wrap">
          <table class="od-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>出发站</th>
                <th></th>
                <th>到达站</th>
                <th>客流量</th>
                <th>流量占比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in odList" :key="idx" class="table-row-enter"
                  :style="{ animationDelay: idx * 0.02 + 's' }">
                <td>
                  <span class="rank-num" :class="{ top3: idx < 3 }">
                    {{ idx < 3 ? ['🥇','🥈','🥉'][idx] : idx + 1 }}
                  </span>
                </td>
                <td class="station-name origin">{{ item.origin_station__station_name }}</td>
                <td class="arrow">
                  <svg width="20" height="12" viewBox="0 0 20 12">
                    <line x1="0" y1="6" x2="14" y2="6" stroke="#8b5cf6" stroke-width="2" stroke-linecap="round"/>
                    <polygon points="14,2 20,6 14,10" fill="#8b5cf6"/>
                  </svg>
                </td>
                <td class="station-name dest">{{ item.destination_station__station_name }}</td>
                <td class="flow-value">{{ item.total_flow?.toLocaleString() }}</td>
                <td class="percent-cell">
                  <div class="percent-bar" :style="{ width: getBarWidth(item.total_flow) + '%' }"></div>
                  <span>{{ getSharePercent(item.total_flow) }}%</span>
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getOdTop, getOdStationHeat } from '../api'

const selectedDate = ref(new Date().toISOString().slice(0, 10))
const selectedMonth = ref(new Date().toISOString().slice(0, 7))
const dateMode = ref('day')
const sankeyRef = ref(null)
const heatRef = ref(null)
const odList = ref([])
const heatData = ref({ origins: [], destinations: [] })
const dataLoading = ref(false)
const hasLoaded = ref(false)

let sankeyChart = null
let heatChart = null

const colors = ['#3b82f6', '#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#f43f5e', '#ec4899', '#14b8a6', '#6366f1', '#84cc16']

const tooltipStyle = {
  backgroundColor: 'rgba(13,18,51,0.95)',
  borderColor: 'rgba(139,92,246,0.25)',
  borderWidth: 1,
  textStyle: { color: '#e2e8f0', fontSize: 13 },
  extraCssText: 'border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);',
}

const uniqueOrigins = computed(() => new Set(odList.value.map(d => d.origin_station__station_name)).size)
const uniqueDests = computed(() => new Set(odList.value.map(d => d.destination_station__station_name)).size)

const totalFlow = computed(() => odList.value.reduce((s, d) => s + d.total_flow, 0) || 1)
const maxFlow = computed(() => Math.max(...odList.value.map(d => d.total_flow), 1))

function getSharePercent(flow) {
  return ((flow / totalFlow.value) * 100).toFixed(1)
}
function getBarWidth(flow) {
  return ((flow / maxFlow.value) * 100).toFixed(1)
}

async function loadData() {
  dataLoading.value = true
  try {
    const monthParam = dateMode.value === 'month' ? selectedMonth.value : null
    const dateParam = dateMode.value === 'day' ? selectedDate.value : null

    // 并行请求 OD Top 和 站点热度
    const [odRes, heatRes] = await Promise.all([
      getOdTop(dateParam, 30, monthParam),
      getOdStationHeat(dateParam, monthParam)
    ])

    odList.value = odRes.data
    heatData.value = heatRes.data
    hasLoaded.value = true

    await nextTick()
    renderSankey()
    renderHeatChart()
  } catch (e) {
    console.error('加载OD分析数据失败', e)
  } finally {
    dataLoading.value = false
  }
}

function renderSankey() {
  if (!sankeyRef.value) return
  if (!sankeyChart) sankeyChart = echarts.init(sankeyRef.value)

  const top15 = odList.value.slice(0, 15)
  if (top15.length === 0) {
    sankeyChart.clear()
    return
  }

  const nodesSet = new Set()
  top15.forEach(d => {
    nodesSet.add('出发: ' + d.origin_station__station_name)
    nodesSet.add('到达: ' + d.destination_station__station_name)
  })
  const nodes = Array.from(nodesSet).map((name, i) => ({
    name,
    itemStyle: { color: colors[i % colors.length] + 'cc', borderColor: colors[i % colors.length], borderWidth: 1 }
  }))
  const links = top15.map(d => ({
    source: '出发: ' + d.origin_station__station_name,
    target: '到达: ' + d.destination_station__station_name,
    value: d.total_flow
  }))

  sankeyChart.resize()
  sankeyChart.setOption({
    tooltip: { trigger: 'item', ...tooltipStyle },
    series: [{
      type: 'sankey',
      layout: 'none',
      emphasis: { focus: 'adjacency' },
      nodeAlign: 'left',
      lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.3 },
      label: { color: '#94a3b8', fontSize: 11, fontWeight: 500 },
      data: nodes,
      links: links,
      nodeWidth: 22,
      nodeGap: 14,
      left: 40,
      right: 120,
      top: 20,
      bottom: 20,
    }],
    animationDuration: 1500,
    animationEasing: 'cubicOut',
  }, true)
}

function renderHeatChart() {
  if (!heatRef.value) return
  if (!heatChart) heatChart = echarts.init(heatRef.value)

  const origins = (heatData.value.origins || []).slice().reverse()
  const dests = (heatData.value.destinations || []).slice().reverse()

  if (origins.length === 0 && dests.length === 0) {
    heatChart.clear()
    return
  }

  heatChart.resize()
  heatChart.setOption({
    tooltip: {
      ...tooltipStyle,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params) {
        const p = params[0]
        return `<b>${p.name}</b><br/>${p.seriesName}: <b style="color:${p.color}">${p.value?.toLocaleString()}</b>`
      }
    },
    legend: {
      data: ['出发客流', '到达客流'],
      top: 0,
      textStyle: { color: '#94a3b8', fontSize: 11 },
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 16,
    },
    grid: [
      { left: 120, right: 60, top: 40, bottom: '53%' },
      { left: 120, right: 60, top: '53%', bottom: 20 },
    ],
    xAxis: [
      { type: 'value', gridIndex: 0, axisLabel: { color: '#475569', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(59,130,246,0.06)' } }, name: '出发客流', nameTextStyle: { color: '#64748b', fontSize: 10 }, nameLocation: 'end' },
      { type: 'value', gridIndex: 1, axisLabel: { color: '#475569', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(59,130,246,0.06)' } }, name: '到达客流', nameTextStyle: { color: '#64748b', fontSize: 10 }, nameLocation: 'end' },
    ],
    yAxis: [
      {
        type: 'category', gridIndex: 0, data: origins.map(d => d.station_name),
        axisLabel: { color: '#94a3b8', fontSize: 11, fontWeight: 500, width: 100, overflow: 'truncate' },
        axisTick: { show: false }, axisLine: { show: false },
      },
      {
        type: 'category', gridIndex: 1, data: dests.map(d => d.station_name),
        axisLabel: { color: '#94a3b8', fontSize: 11, fontWeight: 500, width: 100, overflow: 'truncate' },
        axisTick: { show: false }, axisLine: { show: false },
      },
    ],
    series: [
      {
        name: '出发客流', type: 'bar', xAxisIndex: 0, yAxisIndex: 0,
        data: origins.map(d => d.total_flow),
        barWidth: 14,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#3b82f6' }, { offset: 1, color: '#6366f1' }
        ]), borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10,
          formatter: p => p.value?.toLocaleString() },
      },
      {
        name: '到达客流', type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
        data: dests.map(d => d.total_flow),
        barWidth: 14,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#06b6d4' }, { offset: 1, color: '#14b8a6' }
        ]), borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10,
          formatter: p => p.value?.toLocaleString() },
      },
    ],
    animationDuration: 1200,
    animationEasing: 'cubicOut',
  }, true)
}

function handleResize() {
  sankeyChart?.resize()
  heatChart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await loadData()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  sankeyChart?.dispose()
  heatChart?.dispose()
})
</script>

<style lang="scss" scoped>
.od-analysis { display: flex; flex-direction: column; gap: 20px; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 20px; text-align: center;
  .empty-icon { font-size: 42px; margin-bottom: 14px; opacity: 0.7; }
  p { color: #64748b; font-size: 14px; }
}

.filter-panel {
  display: flex; align-items: flex-end; gap: 16px; padding: 20px 24px; flex-wrap: wrap;
  .filter-group { display: flex; flex-direction: column; gap: 6px;
    label { font-size: 12px; color: #64748b; font-weight: 500; }
  }
  .date-combo {
    display: flex; align-items: stretch;
    border: 1px solid rgba(59,130,246,0.15);
    border-radius: 10px; overflow: hidden;
    background: rgba(15,23,42,0.8);
    .date-mode-toggle {
      display: flex; flex-shrink: 0;
      border-right: 1px solid rgba(59,130,246,0.12);
      .mode-btn {
        padding: 0 14px; font-size: 12px; font-weight: 600;
        background: transparent; color: #4a5568;
        border: none; cursor: pointer; transition: all 0.2s;
        &.active { background: rgba(99,102,241,0.12); color: #818cf8; }
        &:hover:not(.active) { color: #94a3b8; }
      }
    }
    .input-field {
      border: none; border-radius: 0; background: transparent;
      padding: 10px 14px; min-width: 150px;
      &:focus { box-shadow: none; }
    }
  }
  .btn-primary {
    display: flex; align-items: center; gap: 8px;
    &:disabled { opacity: 0.6; cursor: wait; }
  }
  .spinner-sm {
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.charts-row {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
}

.chart-card { min-height: 380px; display: flex; flex-direction: column; }
.chart-wide { width: 100%; }

.card-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
  .header-left { display: flex; align-items: center; gap: 10px; }
  .header-dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    &.purple { background: #8b5cf6; box-shadow: 0 0 8px rgba(139,92,246,0.4); }
    &.green { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.4); }
    &.orange { background: #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,0.4); }
  }
  h3 { font-size: 14px; font-weight: 600; color: #e2e8f0; }
  .record-count { font-size: 12px; color: #64748b; }
}

.flow-summary {
  display: flex; gap: 12px;
  .summary-item {
    font-size: 11px; color: #94a3b8; display: flex; align-items: center; gap: 4px;
  }
  .summary-dot {
    width: 6px; height: 6px; border-radius: 50%;
    &.blue { background: #3b82f6; }
    &.cyan { background: #06b6d4; }
  }
}

.chart-container { flex: 1; min-height: 320px; }
.heat-chart-container { min-height: 480px; }

.od-table-wrap { flex: 1; overflow-y: auto; max-height: 400px; }

.table-row-enter {
  animation: rowSlide 0.4s ease forwards;
  opacity: 0;
}

.od-table {
  width: 100%; border-collapse: collapse;
  th, td { padding: 10px 12px; text-align: left; font-size: 13px; white-space: nowrap; }
  th { color: #64748b; font-weight: 600; position: sticky; top: 0; z-index: 10; background: rgba(22, 30, 65, 1); border-bottom: 1px solid rgba(59,130,246,0.1); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; backdrop-filter: none; }
  td { color: #94a3b8; border-bottom: 1px solid rgba(59,130,246,0.05); }
  tr:hover td { background: rgba(59,130,246,0.05); }

  .rank-num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 8px; font-size: 12px; font-weight: 700;
    background: rgba(59,130,246,0.08); color: #64748b;
    &.top3 { background: transparent; font-size: 16px; }
  }
  .station-name { font-weight: 500; }
  .origin { color: #3b82f6; }
  .dest { color: #06b6d4; }
  .arrow { padding: 0 4px; vertical-align: middle; }
  .flow-value { font-weight: 700; color: #e2e8f0; font-variant-numeric: tabular-nums; }

  .percent-cell {
    position: relative;
    min-width: 80px;
    span { position: relative; z-index: 1; font-size: 11px; font-weight: 600; color: #94a3b8; }
    .percent-bar {
      position: absolute; left: 0; top: 50%; transform: translateY(-50%);
      height: 4px; border-radius: 2px;
      background: linear-gradient(90deg, #8b5cf6, #c084fc);
      transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
    }
  }
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes rowSlide {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

@media (max-width: 900px) {
  .charts-row { grid-template-columns: 1fr; }
}
</style>
