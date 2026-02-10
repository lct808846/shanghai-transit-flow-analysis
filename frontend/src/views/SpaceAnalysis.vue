<template>
  <div class="space-analysis">
    <!-- 筛选 -->
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
        <label>🔢 排名数量</label>
        <select v-model="topN" class="input-field">
          <option :value="10">Top 10</option>
          <option :value="20">Top 20</option>
          <option :value="50">Top 50</option>
        </select>
      </div>
      <button class="btn-primary" @click="loadData" :disabled="dataLoading">
        <span v-if="dataLoading" class="spinner-sm"></span>
        <span v-else>🔍</span>
        {{ dataLoading ? '查询中...' : '查询' }}
      </button>
    </div>

    <div v-if="dataEmpty" class="glass-card empty-state">
      <div class="empty-icon">📭</div>
      <p>所选日期无客流数据，请调整查询条件</p>
    </div>

    <div v-else class="charts-grid">
      <!-- 站点热力排名 -->
      <div class="glass-card chart-card chart-wide">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot cyan"></span>
            <h3>站点客流热力排名</h3>
            <span class="data-badge" v-if="stationList.length">{{ stationList.length }} 站点</span>
          </div>
        </div>
        <div ref="heatRankRef" class="chart-container" :style="{ minHeight: rankChartHeight }"></div>
      </div>

      <!-- 客流分布饼图 -->
      <div class="glass-card chart-card">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot purple"></span>
            <h3>行政区客流分布</h3>
          </div>
        </div>
        <div ref="pieRef" class="chart-container"></div>
      </div>

      <!-- 站点客流详细列表 -->
      <div class="glass-card chart-card table-card">
        <div class="card-header">
          <div class="header-left">
            <span class="header-dot green"></span>
            <h3>站点客流明细</h3>
          </div>
        </div>
        <div class="station-table-wrap">
          <div class="station-list">
            <div v-for="(item, idx) in stationList" :key="idx"
                 class="station-row table-row-enter"
                 :style="{ animationDelay: idx * 0.03 + 's' }">
              <span class="rank-num" :class="{ top3: idx < 3 }">
                {{ idx < 3 ? ['🥇','🥈','🥉'][idx] : idx + 1 }}
              </span>
              <span class="station-name">{{ item.station__station_name }}</span>
              <span class="flow-detail in">↑{{ item.total_in?.toLocaleString() }}</span>
              <span class="flow-detail out">↓{{ item.total_out?.toLocaleString() }}</span>
              <span class="flow-value">{{ item.total_flow?.toLocaleString() }}</span>
              <span class="badge" :class="getCongestionClass(item.total_flow, stationList)">
                <span class="congestion-dot" :class="getCongestionClass(item.total_flow, stationList)"></span>
                {{ getCongestionLabel(item.total_flow, stationList) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getStationRank, getDistrictFlow } from '../api'

const selectedDate = ref(new Date().toISOString().slice(0, 10))
const selectedMonth = ref(new Date().toISOString().slice(0, 7))
const dateMode = ref('day')
const topN = ref(20)
const heatRankRef = ref(null)
const pieRef = ref(null)
const stationList = ref([])
const dataLoading = ref(false)
const dataEmpty = ref(false)

// 动态图表高度：每个站点分配 32px，最小 280px
const rankChartHeight = computed(() => Math.max(280, stationList.value.length * 32 + 60) + 'px')

let heatRankChart = null
let pieChart = null

const colors = ['#3b82f6', '#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#f43f5e', '#ec4899', '#14b8a6', '#6366f1', '#84cc16']

const tooltipStyle = {
  backgroundColor: 'rgba(13,18,51,0.95)',
  borderColor: 'rgba(59,130,246,0.25)',
  borderWidth: 1,
  textStyle: { color: '#e2e8f0', fontSize: 13 },
  extraCssText: 'border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);',
}

function getCongestionClass(flow, list) {
  if (!list || list.length === 0) return 'low'
  const flows = list.map(d => d.total_flow).filter(v => v > 0).sort((a, b) => a - b)
  const p66 = flows[Math.floor(flows.length * 0.66)] || 0
  const p33 = flows[Math.floor(flows.length * 0.33)] || 0
  if (flow > p66) return 'high'
  if (flow > p33) return 'medium'
  return 'low'
}

function getCongestionLabel(flow, list) {
  const cls = getCongestionClass(flow, list)
  return { low: '低', medium: '中', high: '高' }[cls]
}

async function loadData() {
  dataLoading.value = true
  dataEmpty.value = false
  try {
    const monthParam = dateMode.value === 'month' ? selectedMonth.value : null
    const dateParam = dateMode.value === 'day' ? selectedDate.value : null

    // 并发请求站点排名 + 行政区分布
    const [rankRes, districtRes] = await Promise.all([
      getStationRank(dateParam, topN.value, monthParam),
      getDistrictFlow(dateParam, monthParam),
    ])

    const data = rankRes.data
    const districtData = districtRes.data
    stationList.value = data

    if (!data || data.length === 0) {
      dataEmpty.value = true
      heatRankChart?.clear()
      pieChart?.clear()
      return
    }

    // === Chart 1: 站点排名 — 进出站堆叠横向柱状图 ===
    const names = data.map(d => d.station__station_name).reverse()
    const inValues = data.map(d => d.total_in).reverse()
    const outValues = data.map(d => d.total_out).reverse()
    const totalValues = data.map(d => d.total_flow).reverse()
    const maxVal = Math.max(...totalValues)
    const barW = data.length > 30 ? 10 : data.length > 20 ? 12 : 16

    // 重新调整图表尺寸以适应新高度
    await nextTick()
    heatRankChart?.resize()

    heatRankChart?.setOption({
      tooltip: {
        trigger: 'axis', ...tooltipStyle,
        formatter: (params) => {
          const name = params[0]?.axisValue || ''
          let html = `<div style="font-weight:600;margin-bottom:4px">${name}</div>`
          params.forEach(p => {
            if (p.seriesName !== '背景') html += `<div>${p.marker} ${p.seriesName}: <b>${p.value?.toLocaleString()}</b></div>`
          })
          return html
        }
      },
      legend: { data: ['进站', '出站'], textStyle: { color: '#94a3b8', fontSize: 11 }, top: 0, right: 10, icon: 'roundRect', itemWidth: 14, itemHeight: 3 },
      grid: { left: 110, right: 50, top: 30, bottom: 16 },
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { show: false }, axisTick: { show: false } },
      series: [
        {
          name: '背景', type: 'bar', data: totalValues.map(() => maxVal * 1.05), barWidth: barW, barGap: '-100%',
          itemStyle: { color: 'rgba(59,130,246,0.03)', borderRadius: [0, 8, 8, 0] },
          silent: true, animation: false, z: 0,
        },
        {
          name: '进站', type: 'bar', stack: 'flow', barWidth: barW, z: 1,
          data: inValues.map((v, i) => ({
            value: v,
            itemStyle: {
              borderRadius: [0, 0, 0, 0],
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: colors[i % colors.length] },
                { offset: 1, color: colors[i % colors.length] + 'cc' }
              ])
            }
          })),
        },
        {
          name: '出站', type: 'bar', stack: 'flow', barWidth: barW, z: 1,
          data: outValues.map((v, i) => ({
            value: v,
            itemStyle: {
              borderRadius: [0, 8, 8, 0],
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: colors[i % colors.length] + '88' },
                { offset: 1, color: colors[i % colors.length] + '44' }
              ])
            }
          })),
          label: { show: true, position: 'right', color: '#94a3b8', fontSize: 11,
            formatter: (p) => totalValues[p.dataIndex]?.toLocaleString()
          },
        }
      ],
      animationDuration: 1000,
      animationEasing: 'elasticOut',
      animationDelay: (idx) => idx * 40,
    }, true)

    // === Chart 2: 行政区客流饼图 — 使用真实 district 数据 ===
    const pieData = (districtData || [])
      .filter(d => d.district && d.total_flow > 0)
      .map((d, i) => ({
        name: d.district || '未知',
        value: d.total_flow,
        itemStyle: { color: colors[i % colors.length] }
      }))

    if (pieData.length === 0) {
      pieChart?.clear()
    } else {
      pieChart?.setOption({
        tooltip: {
          trigger: 'item', ...tooltipStyle,
          formatter: (p) => {
            const d = districtData.find(dd => dd.district === p.name)
            let html = `<div style="font-weight:600">${p.marker} ${p.name}</div>`
            html += `<div>总客流: <b>${p.value?.toLocaleString()}</b> (${p.percent}%)</div>`
            if (d) html += `<div>站点数: ${d.station_count}</div>`
            return html
          }
        },
        series: [{
          type: 'pie', radius: ['40%', '72%'], center: ['50%', '50%'],
          label: { color: '#94a3b8', fontSize: 11, formatter: '{b}\n{d}%' },
          labelLine: { lineStyle: { color: 'rgba(59,130,246,0.2)' } },
          itemStyle: { borderColor: '#0a0e27', borderWidth: 2, borderRadius: 4 },
          data: pieData,
          emphasis: { scaleSize: 8, itemStyle: { shadowBlur: 15, shadowColor: 'rgba(99,102,241,0.3)' } },
        }],
        animationDuration: 1200,
      }, true)
    }
  } catch (e) {
    console.error('加载空间分析数据失败', e)
  } finally {
    dataLoading.value = false
  }
}

function handleResize() { heatRankChart?.resize(); pieChart?.resize() }

onMounted(async () => {
  await nextTick()
  heatRankChart = echarts.init(heatRankRef.value)
  pieChart = echarts.init(pieRef.value)
  window.addEventListener('resize', handleResize)
  await loadData()
})

onUnmounted(() => { window.removeEventListener('resize', handleResize); heatRankChart?.dispose(); pieChart?.dispose() })
</script>

<style lang="scss" scoped>
.space-analysis { display: flex; flex-direction: column; gap: 20px; }

.filter-panel {
  display: flex; align-items: flex-end; gap: 16px; padding: 20px 24px; flex-wrap: wrap;
  .filter-group { display: flex; flex-direction: column; gap: 6px;
    label { font-size: 12px; color: #64748b; font-weight: 500; }
    select { appearance: none; cursor: pointer; }
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

.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card { min-height: 360px; display: flex; flex-direction: column; }
.chart-wide { grid-column: 1 / -1; }

.card-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
  .header-left { display: flex; align-items: center; gap: 10px; }
  .header-dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    &.cyan { background: #06b6d4; box-shadow: 0 0 8px rgba(6,182,212,0.4); }
    &.green { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.4); }
    &.purple { background: #8b5cf6; box-shadow: 0 0 8px rgba(139,92,246,0.4); }
  }
  h3 { font-size: 14px; font-weight: 600; color: #e2e8f0; }
  .data-badge {
    font-size: 10px; padding: 2px 8px; border-radius: 8px;
    background: rgba(6,182,212,0.1); color: #22d3ee; font-weight: 500;
  }
}

.chart-container { flex: 1; min-height: 280px; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 20px; text-align: center;
  .empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.6; }
  p { color: #64748b; font-size: 14px; }
}

.table-card { padding: 16px; }

.station-table-wrap { flex: 1; overflow-y: auto; max-height: 380px; }

.table-row-enter {
  animation: rowSlide 0.4s ease forwards;
  opacity: 0;
}

.station-list {
  display: flex; flex-direction: column; gap: 2px;
}

.station-row {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 8px; border-radius: 8px;
  transition: background 0.2s;
  &:hover { background: rgba(59,130,246,0.06); }
}

.rank-num {
  flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 6px; font-size: 11px; font-weight: 700;
  background: rgba(59,130,246,0.08); color: #64748b;
  &.top3 { background: transparent; font-size: 16px; width: 26px; }
}

.station-name {
  flex: 1; min-width: 0;
  font-weight: 500; color: #e2e8f0; font-size: 13px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.flow-detail {
  flex-shrink: 0; font-size: 11px; font-variant-numeric: tabular-nums; min-width: 50px; text-align: right;
  &.in { color: #3b82f6; }
  &.out { color: #06b6d4; }
}

.flow-value {
  flex-shrink: 0;
  font-weight: 600; color: #e2e8f0; font-size: 13px;
  font-variant-numeric: tabular-nums; text-align: right;
  min-width: 36px;
}

.congestion-dot {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 3px;
  &.low { background: #10b981; }
  &.medium { background: #f59e0b; }
  &.high { background: #f43f5e; }
}
.badge { flex-shrink: 0; white-space: nowrap; font-size: 11px; color: #94a3b8; }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes rowSlide {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}
</style>
