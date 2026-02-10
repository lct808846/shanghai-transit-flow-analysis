<template>
  <div class="time-analysis">
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
      <div class="filter-group">
        <label>🚉 选择站点</label>
        <select v-model="selectedStation" class="input-field station-select">
          <option value="">-- 请选择站点 --</option>
          <option v-for="s in stationOptions" :key="s.station_id" :value="s.station_name">
            {{ s.station_name }}
          </option>
        </select>
      </div>
      <button class="btn-primary" @click="loadData" :disabled="dataLoading || !selectedStation">
        <span v-if="dataLoading" class="spinner-sm"></span>
        <span v-else>🔍</span>
        {{ dataLoading ? '查询中...' : '查询' }}
      </button>
    </div>

    <div v-if="!selectedStation" class="glass-card empty-state">
      <div class="empty-icon">👆</div>
      <p>请先选择一个站点，再点击查询按钮</p>
    </div>

    <div v-else-if="!hasLoaded && !dataLoading" class="glass-card empty-state">
      <div class="empty-icon">🔍</div>
      <p>已选择「{{ selectedStation }}」，点击查询开始分析</p>
    </div>

    <div v-else-if="dataEmpty" class="glass-card empty-state">
      <div class="empty-icon">📭</div>
      <p>所选日期无客流数据，请调整查询条件</p>
    </div>

    <div v-else class="charts-grid">
      <!-- 24小时客流曲线 -->
      <div class="glass-card chart-card chart-wide">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot amber"></span>
            <h3>24小时客流变化曲线</h3>
          </div>
          <div class="peak-badges">
            <span class="badge high"><span class="badge-pulse"></span>🌅 早高峰 07-09</span>
            <span class="badge medium"><span class="badge-pulse"></span>🌆 晚高峰 17-19</span>
          </div>
        </div>
        <div ref="hourlyDetailRef" class="chart-container"></div>
      </div>

      <!-- 分时段进出站对比 -->
      <div class="glass-card chart-card">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot blue"></span>
            <h3>分时段进出站对比</h3>
          </div>
        </div>
        <div ref="inOutCompareRef" class="chart-container"></div>
      </div>

      <!-- 拥挤度时间分布 -->
      <div class="glass-card chart-card">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot rose"></span>
            <h3>分时段拥挤度分布</h3>
          </div>
        </div>
        <div ref="congestionRef" class="chart-container"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getHourlyFlow, getStationList } from '../api'

const selectedDate = ref(new Date().toISOString().slice(0, 10))
const selectedMonth = ref(new Date().toISOString().slice(0, 7))
const dateMode = ref('day')
const selectedStation = ref('')
const stationOptions = ref([])
const hourlyDetailRef = ref(null)
const inOutCompareRef = ref(null)
const congestionRef = ref(null)
const dataLoading = ref(false)
const dataEmpty = ref(false)
const hasLoaded = ref(false)

let hourlyDetailChart = null
let inOutCompareChart = null
let congestionChart = null

const tooltipStyle = {
  backgroundColor: 'rgba(13,18,51,0.95)',
  borderColor: 'rgba(59,130,246,0.25)',
  borderWidth: 1,
  textStyle: { color: '#e2e8f0', fontSize: 13 },
  extraCssText: 'border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);',
}

// 时段划分:  0-5 凌晨  6-9 早高峰  10-15 平峰  16-19 晚高峰  20-23 夜间
const periodMap = [
  { name: '🌙 凌晨 (0-5)', start: 0, end: 5, color: '#475569' },
  { name: '🌅 早高峰 (6-9)', start: 6, end: 9, color: '#f43f5e' },
  { name: '☀️ 平峰 (10-15)', start: 10, end: 15, color: '#3b82f6' },
  { name: '🌆 晚高峰 (16-19)', start: 16, end: 19, color: '#f59e0b' },
  { name: '🌃 夜间 (20-23)', start: 20, end: 23, color: '#8b5cf6' },
]

function sumRange(arr, start, end) {
  return arr.slice(start, end + 1).reduce((a, b) => a + b, 0)
}

async function loadData() {
  dataLoading.value = true
  dataEmpty.value = false
  try {
    const monthParam = dateMode.value === 'month' ? selectedMonth.value : null
    const dateParam = dateMode.value === 'day' ? selectedDate.value : null
    const stationParam = selectedStation.value || null
    if (!stationParam) {
      dataEmpty.value = false
      return
    }
    const { data: hourly } = await getHourlyFlow(dateParam, monthParam, stationParam)

    if (!hourly || hourly.length === 0) {
      dataEmpty.value = true
      hasLoaded.value = true
      hourlyDetailChart?.clear()
      inOutCompareChart?.clear()
      congestionChart?.clear()
      return
    }

    hasLoaded.value = true
    // 延迟初始化图表（v-else 条件渲染后 DOM 才存在）
    await nextTick()
    if (!hourlyDetailChart && hourlyDetailRef.value) hourlyDetailChart = echarts.init(hourlyDetailRef.value)
    if (!inOutCompareChart && inOutCompareRef.value) inOutCompareChart = echarts.init(inOutCompareRef.value)
    if (!congestionChart && congestionRef.value) congestionChart = echarts.init(congestionRef.value)

    const hours = hourly.map(d => d.hour + ':00')
    const totalFlow = hourly.map(d => d.total_flow)
    const inFlow = hourly.map(d => d.total_in)
    const outFlow = hourly.map(d => d.total_out)

    const isMonth = dateMode.value === 'month'
    const titleSuffix = stationParam ? ` — ${stationParam}` : ' — 全网'
    const dateLabel = isMonth ? selectedMonth.value : selectedDate.value

    // === Chart 1: 24小时客流曲线 ===
    hourlyDetailChart?.setOption({
      tooltip: { trigger: 'axis', ...tooltipStyle, axisPointer: { type: 'cross', lineStyle: { color: 'rgba(59,130,246,0.15)' } } },
      legend: { data: ['总客流', '进站', '出站'], textStyle: { color: '#94a3b8', fontSize: 12 }, top: 5, right: 20, icon: 'roundRect', itemWidth: 16, itemHeight: 3 },
      grid: { left: 60, right: 30, top: 45, bottom: 40 },
      xAxis: { type: 'category', data: hours, boundaryGap: false, axisLine: { lineStyle: { color: 'rgba(59,130,246,0.12)' } }, axisLabel: { color: '#64748b' }, axisTick: { show: false } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(59,130,246,0.05)', type: 'dashed' } }, axisLabel: { color: '#64748b' }, axisLine: { show: false } },
      series: [
        { name: '总客流', type: 'line', data: totalFlow, smooth: 0.4, showSymbol: false, symbol: 'circle', symbolSize: 8,
          lineStyle: { width: 3, color: '#f59e0b', shadowBlur: 10, shadowColor: 'rgba(245,158,11,0.3)' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(245,158,11,0.18)' }, { offset: 1, color: 'rgba(245,158,11,0)' }]) },
          itemStyle: { color: '#f59e0b', borderColor: '#fff', borderWidth: 2 },
          markArea: {
            silent: true,
            data: [
              [{ xAxis: '6:00', itemStyle: { color: 'rgba(244,63,94,0.06)' } }, { xAxis: '9:00' }],
              [{ xAxis: '16:00', itemStyle: { color: 'rgba(244,63,94,0.06)' } }, { xAxis: '19:00' }],
            ]
          }
        },
        { name: '进站', type: 'line', data: inFlow, smooth: 0.4, showSymbol: false,
          lineStyle: { width: 2, color: '#3b82f6', type: 'dashed' }, itemStyle: { color: '#3b82f6' } },
        { name: '出站', type: 'line', data: outFlow, smooth: 0.4, showSymbol: false,
          lineStyle: { width: 2, color: '#06b6d4', type: 'dashed' }, itemStyle: { color: '#06b6d4' } },
      ],
      animationDuration: 1200,
      animationEasing: 'cubicOut',
    }, true)

    // === Chart 2: 分时段客流对比(进站vs出站) — 替换原来无意义的总量饼图 ===
    const periodData = periodMap.map(p => {
      const pIn = sumRange(inFlow, p.start, p.end)
      const pOut = sumRange(outFlow, p.start, p.end)
      return { name: p.name, inVal: pIn, outVal: pOut, color: p.color }
    })

    inOutCompareChart?.setOption({
      tooltip: {
        trigger: 'axis', ...tooltipStyle,
        formatter: (params) => {
          const name = params[0]?.axisValue || ''
          let html = `<div style="font-weight:600;margin-bottom:4px">${name}</div>`
          params.forEach(p => { html += `<div>${p.marker} ${p.seriesName}: <b>${p.value?.toLocaleString()}</b></div>` })
          const total = (params[0]?.value || 0) + (params[1]?.value || 0)
          html += `<div style="margin-top:4px;border-top:1px solid rgba(255,255,255,0.1);padding-top:4px">合计: <b>${total.toLocaleString()}</b></div>`
          return html
        }
      },
      legend: { data: ['进站', '出站'], textStyle: { color: '#94a3b8', fontSize: 12 }, top: 5, right: 10, icon: 'roundRect', itemWidth: 14, itemHeight: 3 },
      grid: { left: 50, right: 20, top: 40, bottom: 40 },
      xAxis: { type: 'category', data: periodData.map(p => p.name), axisLabel: { color: '#94a3b8', fontSize: 10, interval: 0, rotate: 0 }, axisLine: { lineStyle: { color: 'rgba(59,130,246,0.12)' } }, axisTick: { show: false } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(59,130,246,0.05)', type: 'dashed' } }, axisLabel: { color: '#64748b' }, axisLine: { show: false } },
      series: [
        { name: '进站', type: 'bar', stack: 'total', barWidth: 28,
          data: periodData.map(p => ({ value: p.inVal, itemStyle: { color: p.color, borderRadius: [0, 0, 0, 0] } })),
          itemStyle: { borderRadius: [0, 0, 4, 4] },
        },
        { name: '出站', type: 'bar', stack: 'total', barWidth: 28,
          data: periodData.map(p => ({ value: p.outVal, itemStyle: { color: p.color + '88' } })),
          itemStyle: { borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', color: '#94a3b8', fontSize: 10,
            formatter: (p) => { const total = periodData[p.dataIndex].inVal + periodData[p.dataIndex].outVal; return total > 0 ? total.toLocaleString() : '' }
          },
        },
      ],
      animationDuration: 1000,
    }, true)

    // === Chart 3: 拥挤度热力图 — 动态百分位阈值 ===
    const sortedFlow = [...totalFlow].filter(v => v > 0).sort((a, b) => a - b)
    const p33 = sortedFlow[Math.floor(sortedFlow.length * 0.33)] || 0
    const p66 = sortedFlow[Math.floor(sortedFlow.length * 0.66)] || 0

    const congestionData = hours.map((h, i) => {
      const t = totalFlow[i]
      let level = 0
      if (t > p66) level = 2
      else if (t > p33) level = 1
      return [i, 0, level]
    })

    congestionChart?.setOption({
      tooltip: {
        formatter: (p) => {
          const h = hours[p.data[0]]
          const flow = totalFlow[p.data[0]]
          const tag = ['🟢 低', '🟡 中', '🔴 高'][p.data[2]]
          return `<div style="font-weight:600">${h}</div>${tag}拥挤 · 客流 ${flow?.toLocaleString()}`
        },
        ...tooltipStyle
      },
      grid: { left: 60, right: 30, top: 20, bottom: 50 },
      xAxis: { type: 'category', data: hours, axisLine: { lineStyle: { color: 'rgba(59,130,246,0.12)' } }, axisLabel: { color: '#64748b', interval: 1 }, axisTick: { show: false } },
      yAxis: { type: 'category', data: ['拥挤度'], axisLine: { show: false }, axisLabel: { color: '#64748b' } },
      visualMap: { show: true, min: 0, max: 2, orient: 'horizontal', left: 'center', bottom: 5,
        pieces: [
          { value: 0, label: '低', color: '#10b981' },
          { value: 1, label: '中', color: '#f59e0b' },
          { value: 2, label: '高', color: '#f43f5e' },
        ],
        textStyle: { color: '#94a3b8' }
      },
      series: [{
        type: 'heatmap', data: congestionData,
        label: { show: false },
        itemStyle: { borderRadius: 8, borderColor: '#0a0e27', borderWidth: 2 },
        emphasis: { itemStyle: { shadowBlur: 10 } },
      }],
      animationDuration: 1000,
    }, true)
  } catch (e) {
    console.error('加载时间分析数据失败', e)
  } finally {
    dataLoading.value = false
  }
}

function handleResize() {
  hourlyDetailChart?.resize()
  inOutCompareChart?.resize()
  congestionChart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  // 加载站点下拉列表
  try {
    const { data } = await getStationList('')
    stationOptions.value = data.data || data
  } catch (e) {
    console.error('加载站点列表失败', e)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  hourlyDetailChart?.dispose()
  inOutCompareChart?.dispose()
  congestionChart?.dispose()
})
</script>

<style lang="scss" scoped>
.time-analysis { display: flex; flex-direction: column; gap: 20px; }

.filter-panel {
  display: flex; align-items: flex-end; gap: 16px; padding: 20px 24px; flex-wrap: wrap;
  .filter-group {
    display: flex; flex-direction: column; gap: 6px;
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
    &:disabled { opacity: 0.6; cursor: not-allowed; }
  }
  .station-select {
    appearance: none; cursor: pointer; min-width: 180px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2364748b' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 12px center;
    padding-right: 32px;
  }
  .spinner-sm {
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card { min-height: 340px; display: flex; flex-direction: column; }
.chart-wide { grid-column: 1 / -1; }

.card-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
  .header-left { display: flex; align-items: center; gap: 10px; }
  .header-dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    &.amber { background: #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,0.4); }
    &.blue { background: #3b82f6; box-shadow: 0 0 8px rgba(59,130,246,0.4); }
    &.rose { background: #f43f5e; box-shadow: 0 0 8px rgba(244,63,94,0.4); }
  }
  h3 { font-size: 14px; font-weight: 600; color: #e2e8f0; }
}

.peak-badges {
  display: flex; gap: 8px;
  .badge {
    position: relative; padding-left: 18px;
    .badge-pulse {
      position: absolute; left: 6px; top: 50%; transform: translateY(-50%);
      width: 6px; height: 6px; border-radius: 50%;
      animation: pulse-dot 2s infinite;
    }
    &.high .badge-pulse { background: #f43f5e; box-shadow: 0 0 6px rgba(244,63,94,0.5); }
    &.medium .badge-pulse { background: #f59e0b; box-shadow: 0 0 6px rgba(245,158,11,0.5); }
  }
}

.chart-container { flex: 1; min-height: 260px; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 20px; text-align: center;
  .empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.6; }
  p { color: #64748b; font-size: 14px; }
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse-dot {
  0%, 100% { opacity: 0.5; transform: translateY(-50%) scale(1); }
  50% { opacity: 1; transform: translateY(-50%) scale(1.4); }
}
</style>
