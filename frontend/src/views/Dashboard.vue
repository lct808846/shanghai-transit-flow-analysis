<template>
  <div class="dashboard">
    <!-- 顶部指标卡片 -->
    <div class="metrics-row">
      <div
        class="metric-card glass-card"
        v-for="(item, idx) in metrics"
        :key="idx"
        :class="{ 'is-loaded': !loading }"
        :style="{ '--delay': idx * 0.12 + 's', '--accent': item.color }"
      >
        <!-- 骨架屏 -->
        <template v-if="loading">
          <div class="metric-icon skeleton-icon"></div>
          <div class="metric-info">
            <span class="skeleton-line w60"></span>
            <span class="skeleton-line w40"></span>
          </div>
        </template>
        <template v-else>
          <div class="metric-icon" :style="{ background: item.gradient }">
            <span class="icon-emoji">{{ item.icon }}</span>
          </div>
          <div class="metric-info">
            <span class="metric-value">
              <span class="animated-number" ref="numberRefs">{{ item.displayValue }}</span>
            </span>
            <span class="metric-label">{{ item.label }}</span>
            <span class="metric-trend" v-if="item.trend">
              <span :class="item.trend > 0 ? 'trend-up' : 'trend-down'">
                {{ item.trend > 0 ? '↑' : '↓' }} {{ Math.abs(item.trend) }}%
              </span>
              <span class="trend-period">较昨日</span>
            </span>
          </div>
          <div class="metric-spark">
            <svg viewBox="0 0 60 24" class="spark-line">
              <polyline :points="item.spark" fill="none" :stroke="item.color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
        </template>
        <div class="card-glow" :style="{ background: `radial-gradient(circle at 80% 20%, ${item.color}15, transparent 70%)` }"></div>
      </div>
    </div>

    <!-- 实时状态条 -->
    <div class="status-ticker glass-card">
      <div class="ticker-dot pulse"></div>
      <span class="ticker-label">实时数据</span>
      <div class="ticker-divider"></div>
      <span class="ticker-text">{{ statusText }}</span>
      <div class="ticker-right">
        <span class="ticker-time">🕐 {{ currentTime }}</span>
        <button class="refresh-btn" @click="refreshAll" :class="{ spinning: refreshing }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 小时客流趋势 -->
      <div class="glass-card chart-card chart-wide">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot blue"></span>
            <h3>全网小时客流趋势</h3>
            <span class="data-badge" v-if="hourlyDataCount">{{ hourlyDataCount }} 条</span>
          </div>
          <div class="header-right">
            <div class="date-combo">
              <div class="date-mode-toggle">
                <button class="mode-btn" :class="{ active: dateMode === 'day' }" @click="dateMode = 'day'; handleDateChange()">日</button>
                <button class="mode-btn" :class="{ active: dateMode === 'month' }" @click="dateMode = 'month'; handleDateChange()">月</button>
              </div>
              <input v-if="dateMode === 'day'" type="date" v-model="selectedDate" class="input-field" @change="handleDateChange" />
              <input v-else type="month" v-model="selectedMonth" class="input-field" @change="handleDateChange" />
            </div>
          </div>
        </div>
        <div class="chart-body">
          <div v-if="chartLoading.hourly" class="chart-skeleton">
            <div class="skeleton-wave"></div>
          </div>
          <div ref="hourlyChartRef" class="chart-container" :class="{ 'chart-ready': !chartLoading.hourly }"></div>
        </div>
      </div>

      <!-- 站点排名 -->
      <div class="glass-card chart-card">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot green"></span>
            <h3>站点客流 TOP 10</h3>
          </div>
        </div>
        <div class="chart-body">
          <div v-if="chartLoading.rank" class="chart-skeleton">
            <div class="skeleton-bars"></div>
          </div>
          <div ref="rankChartRef" class="chart-container" :class="{ 'chart-ready': !chartLoading.rank }"></div>
        </div>
      </div>

      <!-- OD 热门路线 -->
      <div class="glass-card chart-card">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot purple"></span>
            <h3>热门 OD 路线</h3>
          </div>
        </div>
        <div class="chart-body">
          <div v-if="chartLoading.od" class="chart-skeleton">
            <div class="skeleton-bars"></div>
          </div>
          <div ref="odChartRef" class="chart-container" :class="{ 'chart-ready': !chartLoading.od }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { getOverview, getHourlyFlow, getStationRank, getOdTop } from '../api'

const selectedDate = ref(new Date().toISOString().slice(0, 10))
const selectedMonth = ref(new Date().toISOString().slice(0, 7))
const dateMode = ref('day')
const hourlyChartRef = ref(null)
const rankChartRef = ref(null)
const odChartRef = ref(null)

let hourlyChart = null
let rankChart = null
let odChart = null

const loading = ref(true)
const refreshing = ref(false)
const hourlyDataCount = ref(0)
const chartLoading = reactive({ hourly: true, rank: true, od: true })

const currentTime = ref('')
let timeTimer = null

// 迷你火花线数据
const sparkData = [
  '0,20 10,15 20,18 30,8 40,12 50,6 60,10',
  '0,18 10,12 20,20 30,14 40,10 50,16 60,8',
  '0,10 10,6 20,14 30,20 40,16 50,12 60,4',
  '0,16 10,20 20,10 30,6 40,14 50,18 60,12',
]

const metrics = ref([
  { icon: '🚉', label: '监测站点', value: 0, displayValue: '-', gradient: 'linear-gradient(135deg, #3b82f6, #06b6d4)', color: '#3b82f6', trend: 0, spark: sparkData[0] },
  { icon: '🚌', label: '运营线路', value: 0, displayValue: '-', gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)', color: '#8b5cf6', trend: 0, spark: sparkData[1] },
  { icon: '👥', label: '今日总客流', value: 0, displayValue: '-', gradient: 'linear-gradient(135deg, #10b981, #34d399)', color: '#10b981', trend: 5.2, spark: sparkData[2] },
  { icon: '📊', label: 'OD记录数', value: 0, displayValue: '-', gradient: 'linear-gradient(135deg, #f59e0b, #fbbf24)', color: '#f59e0b', trend: -1.8, spark: sparkData[3] },
])

const statusText = computed(() => {
  if (loading.value) return '正在加载系统数据...'
  const total = metrics.value[2].value
  if (total > 100000) return `全网客流高峰运行中，当日总客流 ${total.toLocaleString()} 人次`
  return `系统正常运行，已接入 ${metrics.value[0].value} 个监测站点`
})

function updateTime() {
  currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// 数字动画
function animateNumber(target, metric) {
  const start = 0
  const end = target
  const duration = 1200
  const startTime = performance.now()

  function update(currentTime) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
    const current = Math.round(start + (end - start) * eased)
    metric.displayValue = current.toLocaleString()
    if (progress < 1) requestAnimationFrame(update)
  }
  requestAnimationFrame(update)
}

// 通用 tooltip 样式
const tooltipStyle = {
  backgroundColor: 'rgba(13,18,51,0.95)',
  borderColor: 'rgba(59,130,246,0.25)',
  borderWidth: 1,
  textStyle: { color: '#e2e8f0', fontSize: 13 },
  extraCssText: 'border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); backdrop-filter: blur(10px);',
}

async function loadOverview() {
  loading.value = true
  try {
    const { data } = await getOverview()
    metrics.value[0].value = data.total_stations || 0
    metrics.value[1].value = data.total_routes || 0
    metrics.value[2].value = data.latest_daily_flow || 0
    metrics.value[3].value = data.total_od_records || 0

    await nextTick()
    metrics.value.forEach(m => animateNumber(m.value, m))
  } catch (e) {
    console.error('加载总览失败', e)
    metrics.value.forEach(m => { m.displayValue = '-' })
  } finally {
    loading.value = false
  }
}

async function loadHourlyFlow() {
  chartLoading.hourly = true
  try {
    const monthParam = dateMode.value === 'month' ? selectedMonth.value : null
    const dateParam = dateMode.value === 'day' ? selectedDate.value : null
    const { data } = await getHourlyFlow(dateParam, monthParam)
    hourlyDataCount.value = data.length
    const hours = data.map(d => d.hour + ':00')
    const inFlow = data.map(d => d.total_in)
    const outFlow = data.map(d => d.total_out)

    hourlyChart?.setOption({
      tooltip: {
        trigger: 'axis',
        ...tooltipStyle,
        axisPointer: { type: 'cross', lineStyle: { color: 'rgba(59,130,246,0.2)' }, crossStyle: { color: 'rgba(59,130,246,0.2)' } },
      },
      legend: {
        data: ['进站客流', '出站客流'],
        textStyle: { color: '#94a3b8', fontSize: 12 },
        top: 8, right: 20,
        icon: 'roundRect', itemWidth: 16, itemHeight: 3,
      },
      grid: { left: 60, right: 30, top: 55, bottom: 40 },
      xAxis: {
        type: 'category', data: hours, boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(59,130,246,0.12)' } },
        axisLabel: { color: '#64748b', fontSize: 11 },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: 'rgba(59,130,246,0.05)', type: 'dashed' } },
        axisLabel: { color: '#64748b', fontSize: 11 },
        axisLine: { show: false }, axisTick: { show: false },
      },
      series: [
        {
          name: '进站客流', type: 'line', data: inFlow, smooth: 0.4, showSymbol: false, symbol: 'circle', symbolSize: 8,
          lineStyle: { width: 2.5, color: '#3b82f6', shadowBlur: 8, shadowColor: 'rgba(59,130,246,0.3)' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59,130,246,0.2)' },
            { offset: 0.7, color: 'rgba(59,130,246,0.05)' },
            { offset: 1, color: 'rgba(59,130,246,0)' }
          ])},
          itemStyle: { color: '#3b82f6', borderColor: '#fff', borderWidth: 2 },
          emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(59,130,246,0.5)' } },
        },
        {
          name: '出站客流', type: 'line', data: outFlow, smooth: 0.4, showSymbol: false, symbol: 'circle', symbolSize: 8,
          lineStyle: { width: 2.5, color: '#06b6d4', shadowBlur: 8, shadowColor: 'rgba(6,182,212,0.3)' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(6,182,212,0.2)' },
            { offset: 0.7, color: 'rgba(6,182,212,0.05)' },
            { offset: 1, color: 'rgba(6,182,212,0)' }
          ])},
          itemStyle: { color: '#06b6d4', borderColor: '#fff', borderWidth: 2 },
          emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(6,182,212,0.5)' } },
        },
      ],
      animationDuration: 1200,
      animationEasing: 'cubicOut',
    })
  } catch (e) {
    console.error('加载小时客流失败', e)
  } finally {
    chartLoading.hourly = false
  }
}

async function loadStationRank() {
  chartLoading.rank = true
  try {
    const monthParam = dateMode.value === 'month' ? selectedMonth.value : null
    const dateParam = dateMode.value === 'day' ? selectedDate.value : null
    const { data } = await getStationRank(dateParam, 10, monthParam)
    const names = data.map(d => d.station__station_name).reverse()
    const values = data.map(d => d.total_flow).reverse()
    const maxVal = Math.max(...values)

    rankChart?.setOption({
      tooltip: { trigger: 'axis', ...tooltipStyle },
      grid: { left: 100, right: 50, top: 16, bottom: 16 },
      xAxis: {
        type: 'value', show: false,
      },
      yAxis: {
        type: 'category', data: names,
        axisLabel: { color: '#94a3b8', fontSize: 12, margin: 12 },
        axisLine: { show: false }, axisTick: { show: false },
      },
      series: [
        // 背景条
        {
          type: 'bar', data: values.map(() => maxVal * 1.05), barWidth: 18, barGap: '-100%',
          itemStyle: { color: 'rgba(59,130,246,0.04)', borderRadius: [0, 10, 10, 0] },
          silent: true, animation: false,
        },
        {
          type: 'bar', data: values.map((v, i) => ({
            value: v,
            itemStyle: {
              borderRadius: [0, 10, 10, 0],
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: i >= values.length - 3 ? '#f59e0b' : '#3b82f6' },
                { offset: 1, color: i >= values.length - 3 ? '#fbbf24' : '#06b6d4' }
              ]),
              shadowBlur: i >= values.length - 3 ? 8 : 0,
              shadowColor: i >= values.length - 3 ? 'rgba(245,158,11,0.3)' : 'transparent',
            }
          })),
          barWidth: 18,
          label: {
            show: true, position: 'right', color: '#94a3b8', fontSize: 11, fontWeight: 600,
            formatter: '{c}',
          },
        }
      ],
      animationDuration: 1000,
      animationEasing: 'elasticOut',
      animationDelay: (idx) => idx * 60,
    })
  } catch (e) {
    console.error('加载站点排名失败', e)
  } finally {
    chartLoading.rank = false
  }
}

async function loadOdTop() {
  chartLoading.od = true
  try {
    const monthParam = dateMode.value === 'month' ? selectedMonth.value : null
    const dateParam = dateMode.value === 'day' ? selectedDate.value : null
    const { data } = await getOdTop(dateParam, 10, monthParam)
    const items = data.map(d => ({
      name: `${d.origin_station__station_name} → ${d.destination_station__station_name}`,
      value: d.total_flow
    })).reverse()
    const maxVal = Math.max(...items.map(i => i.value))

    odChart?.setOption({
      tooltip: { trigger: 'axis', ...tooltipStyle },
      grid: { left: 180, right: 50, top: 16, bottom: 16 },
      xAxis: { type: 'value', show: false },
      yAxis: {
        type: 'category', data: items.map(i => i.name),
        axisLabel: { color: '#94a3b8', fontSize: 11, width: 165, overflow: 'truncate' },
        axisLine: { show: false }, axisTick: { show: false },
      },
      series: [
        {
          type: 'bar', data: items.map(() => maxVal * 1.05), barWidth: 18, barGap: '-100%',
          itemStyle: { color: 'rgba(139,92,246,0.04)', borderRadius: [0, 10, 10, 0] },
          silent: true, animation: false,
        },
        {
          type: 'bar', data: items.map(i => ({
            value: i.value,
            itemStyle: {
              borderRadius: [0, 10, 10, 0],
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#8b5cf6' },
                { offset: 1, color: '#c084fc' }
              ]),
            }
          })),
          barWidth: 18,
          label: {
            show: true, position: 'right', color: '#94a3b8', fontSize: 11, fontWeight: 600,
            formatter: '{c}',
          },
        }
      ],
      animationDuration: 1000,
      animationEasing: 'elasticOut',
      animationDelay: (idx) => idx * 60,
    })
  } catch (e) {
    console.error('加载OD排名失败', e)
  } finally {
    chartLoading.od = false
  }
}

function handleDateChange() {
  Promise.all([loadHourlyFlow(), loadStationRank(), loadOdTop()])
}

async function refreshAll() {
  refreshing.value = true
  await loadOverview()
  await Promise.all([loadHourlyFlow(), loadStationRank(), loadOdTop()])
  setTimeout(() => { refreshing.value = false }, 600)
}

function handleResize() {
  hourlyChart?.resize()
  rankChart?.resize()
  odChart?.resize()
}

onMounted(async () => {
  updateTime()
  timeTimer = setInterval(updateTime, 1000)

  await nextTick()
  hourlyChart = echarts.init(hourlyChartRef.value)
  rankChart = echarts.init(rankChartRef.value)
  odChart = echarts.init(odChartRef.value)

  window.addEventListener('resize', handleResize)

  await loadOverview()
  await Promise.all([loadHourlyFlow(), loadStationRank(), loadOdTop()])
})

onUnmounted(() => {
  clearInterval(timeTimer)
  window.removeEventListener('resize', handleResize)
  hourlyChart?.dispose()
  rankChart?.dispose()
  odChart?.dispose()
})
</script>

<style lang="scss" scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// ===== 指标卡片 =====
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 22px;
  position: relative;
  overflow: hidden;
  opacity: 0;
  transform: translateY(16px);
  animation: metricEnter 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--delay);

  .card-glow {
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.4s ease;
  }

  &:hover .card-glow { opacity: 1; }

  .metric-icon {
    width: 50px;
    height: 50px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    position: relative;

    .icon-emoji { font-size: 22px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }
  }

  .metric-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-width: 0;
  }

  .metric-value {
    font-size: 24px;
    font-weight: 800;
    color: #e2e8f0;
    line-height: 1.1;
    letter-spacing: -0.5px;
    font-variant-numeric: tabular-nums;
  }

  .metric-label {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
  }

  .metric-trend {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;

    .trend-up {
      font-size: 11px;
      font-weight: 700;
      color: #10b981;
      background: rgba(16, 185, 129, 0.1);
      padding: 1px 6px;
      border-radius: 6px;
    }
    .trend-down {
      font-size: 11px;
      font-weight: 700;
      color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
      padding: 1px 6px;
      border-radius: 6px;
    }
    .trend-period { font-size: 10px; color: #475569; }
  }

  .metric-spark {
    width: 60px;
    height: 24px;
    flex-shrink: 0;
    opacity: 0.5;

    .spark-line { width: 100%; height: 100%; }
  }
}

// 骨架屏
.skeleton-icon {
  width: 50px; height: 50px; border-radius: 14px;
  background: linear-gradient(110deg, rgba(59,130,246,0.06) 30%, rgba(59,130,246,0.12) 50%, rgba(59,130,246,0.06) 70%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-line {
  display: block;
  height: 14px; border-radius: 6px;
  background: linear-gradient(110deg, rgba(59,130,246,0.06) 30%, rgba(59,130,246,0.12) 50%, rgba(59,130,246,0.06) 70%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;

  &.w60 { width: 60%; height: 20px; margin-bottom: 6px; }
  &.w40 { width: 40%; height: 12px; }
}

// ===== 状态条 =====
.status-ticker {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  animation: metricEnter 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: 0.5s;
  opacity: 0;
  transform: translateY(16px);

  .ticker-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #10b981; flex-shrink: 0;
    &.pulse {
      animation: pulse-glow 2s infinite;
      box-shadow: 0 0 8px rgba(16,185,129,0.5);
    }
  }

  .ticker-label {
    font-size: 11px; font-weight: 700; color: #10b981;
    text-transform: uppercase; letter-spacing: 1px;
  }

  .ticker-divider {
    width: 1px; height: 16px; background: rgba(59,130,246,0.15);
  }

  .ticker-text {
    font-size: 13px; color: #94a3b8; flex: 1;
  }

  .ticker-right {
    display: flex; align-items: center; gap: 12px;
  }

  .ticker-time {
    font-size: 12px; color: #64748b; font-variant-numeric: tabular-nums;
  }

  .refresh-btn {
    width: 28px; height: 28px; border-radius: 8px; border: none;
    background: rgba(59,130,246,0.08); color: #64748b;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; transition: all 0.3s ease;

    &:hover { background: rgba(59,130,246,0.15); color: #3b82f6; }
    &.spinning svg { animation: spin 0.8s linear infinite; }
  }
}

// ===== 图表区域 =====
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  min-height: 370px;
  display: flex;
  flex-direction: column;
  animation: metricEnter 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: 0.6s;
  opacity: 0;
  transform: translateY(16px);
}

.chart-wide {
  grid-column: 1 / -1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .header-dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    &.blue { background: #3b82f6; box-shadow: 0 0 8px rgba(59,130,246,0.4); }
    &.green { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.4); }
    &.purple { background: #8b5cf6; box-shadow: 0 0 8px rgba(139,92,246,0.4); }
  }

  h3 {
    font-size: 14px;
    font-weight: 600;
    color: #e2e8f0;
  }

  .data-badge {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 8px;
    background: rgba(59,130,246,0.1);
    color: #60a5fa;
    font-weight: 500;
  }

  .header-right { display: flex; align-items: center; gap: 8px; }

  .date-combo {
    display: flex; align-items: stretch;
    border: 1px solid rgba(59,130,246,0.15);
    border-radius: 8px; overflow: hidden;
    background: rgba(15,23,42,0.6);
    .date-mode-toggle {
      display: flex; flex-shrink: 0;
      border-right: 1px solid rgba(59,130,246,0.12);
      .mode-btn {
        padding: 0 10px; font-size: 11px; font-weight: 600;
        background: transparent; color: #4a5568;
        border: none; cursor: pointer; transition: all 0.2s;
        &.active { background: rgba(99,102,241,0.12); color: #818cf8; }
        &:hover:not(.active) { color: #94a3b8; }
      }
    }
    .input-field {
      padding: 6px 10px; font-size: 12px; border: none;
      border-radius: 0; background: transparent; color: #94a3b8;
      min-width: 130px;
      &:focus { box-shadow: none; }
    }
  }
}

.chart-body {
  flex: 1;
  position: relative;
  min-height: 280px;
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 280px;
  opacity: 0;
  transition: opacity 0.6s ease;

  &.chart-ready { opacity: 1; }
}

// 图表骨架
.chart-skeleton {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.skeleton-wave {
  width: 80%;
  height: 60%;
  background:
    repeating-linear-gradient(90deg,
      rgba(59,130,246,0.03) 0px, rgba(59,130,246,0.06) 4px,
      rgba(59,130,246,0.03) 8px
    );
  border-radius: 8px;
  animation: shimmer 2s infinite;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 80'%3E%3Cpath d='M0,60 Q25,20 50,40 T100,30 T150,50 T200,20 V80 H0Z' fill='black'/%3E%3C/svg%3E");
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 80'%3E%3Cpath d='M0,60 Q25,20 50,40 T100,30 T150,50 T200,20 V80 H0Z' fill='black'/%3E%3C/svg%3E");
  mask-size: 100% 100%;
  -webkit-mask-size: 100% 100%;
}

.skeleton-bars {
  width: 80%;
  height: 60%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 8px 0;

  &::before, &::after {
    content: '';
    display: block;
    height: 12px;
    border-radius: 6px;
    background: linear-gradient(110deg, rgba(59,130,246,0.04) 30%, rgba(59,130,246,0.08) 50%, rgba(59,130,246,0.04) 70%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }
  &::before { width: 85%; }
  &::after { width: 60%; }
}

// ===== 动画 =====
@keyframes metricEnter {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 5px rgba(16,185,129,0.2); }
  50% { box-shadow: 0 0 12px rgba(16,185,129,0.5); }
}

// ===== 响应式 =====
@media (max-width: 1100px) {
  .metrics-row { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .chart-wide { grid-column: auto; }
}
</style>
