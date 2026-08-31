<template>
  <div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div>
        <h2 class="page-title">仪表盘与洞察</h2>
        <p class="page-sub">核心质量指标、趋势与排行 · 数据范围：当前工作空间（实时 API）</p>
      </div>
      <div style="display:flex;gap:8px">
        <el-select v-model="appId" style="width:200px" placeholder="全部应用" @change="load">
          <el-option label="全部应用" value="" />
          <el-option v-for="a in apps" :key="a.id" :value="a.id" :label="a.name" />
        </el-select>
        <el-radio-group v-model="range" @change="load">
          <el-radio-button value="7d">近 7 天</el-radio-button>
          <el-radio-button value="30d">近 30 天</el-radio-button>
          <el-radio-button value="90d">近 90 天</el-radio-button>
        </el-radio-group>
      </div>
    </div>
    <el-row :gutter="12">
      <el-col v-for="k in kpiItems" :key="k.label" :xs="12" :md="8" :xl="4">
        <el-card style="margin-bottom:12px">
          <div style="font-size:12px;color:#94a3b8">{{ k.label }}</div>
          <div class="kpi-num">{{ k.value }}<span style="font-size:13px;color:#94a3b8;margin-left:2px">{{ k.unit }}</span></div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px">{{ k.note }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="12">
      <el-col :md="16">
        <el-card style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:6px">Score 趋势（全应用加权 · 阈值 0.6）</div><div ref="trendEl" style="height:250px"></div></el-card>
      </el-col>
      <el-col :md="8">
        <el-card style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:6px">应用质量排行</div><div ref="rankEl" style="height:250px"></div></el-card>
      </el-col>
    </el-row>
    <el-row :gutter="12">
      <el-col :span="24">
        <el-card>
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
            <span style="font-weight:700">最近 Bad Case（待复核）</span>
            <el-button size="small" @click="$router.push('/badcases')">查看全部 →</el-button>
          </div>
          <el-table v-loading="loading" :data="recentBad" size="small">
            <el-table-column prop="id" label="Case" width="110" />
            <el-table-column label="Score" width="110">
              <template #default="{ row }"><b :style="{ color: scoreColor(row.score) }">{{ row.score?.toFixed(2) }}</b></template>
            </el-table-column>
            <el-table-column prop="threshold" label="阈值" width="80" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }"><el-button size="small" type="primary" plain @click="$router.push('/badcases')">复核</el-button></template>
            </el-table-column>
            <el-table-column prop="time" label="触发时间" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    <el-alert v-if="alerts.error_tasks?.length" type="error" style="margin-top:12px" :closable="false" show-icon
              :title="'评估任务异常：' + alerts.error_tasks[0].name + ' — ' + alerts.error_tasks[0].err_msg" />
    <el-alert v-if="alerts.interrupted_apps?.length" type="warning" style="margin-top:8px" :closable="false" show-icon
              :title="'应用数据中断：' + alerts.interrupted_apps.map(a => a.name).join('、')" />
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api'

const range = ref('7d'), appId = ref(''), loading = ref(false)
const data = ref({ kpi: {}, trend: [], ranking: [], recent_bad: [], alerts: {} })
const apps = ref([]), trendEl = ref(null), rankEl = ref(null)
const charts = []
const kpiItems = computed(() => [
  { label: '接入 Agent 应用', value: data.value.kpi.apps ?? 0, unit: '个', note: (data.value.kpi.online_apps ?? 0) + ' 个在线' },
  { label: '区间评估任务', value: data.value.kpi.tasks ?? 0, unit: '个', note: '含在线/离线' },
  { label: '平均 Score', value: (data.value.kpi.score ?? 0).toFixed(2), unit: '', note: '阈值 0.6' },
  { label: '低分率', value: (data.value.kpi.low_rate ?? 0).toFixed(1), unit: '%', note: 'Score < 0.6' },
  { label: '待复核 Bad Case', value: data.value.kpi.pending_bad ?? 0, unit: '条', note: 'P95 入库时效 6.2min' },
  { label: '评估器平均误判率', value: (data.value.kpi.bias ?? 0).toFixed(1), unit: '%', note: '>20% 标记待优化' },
])
const recentBad = computed(() => data.value.recent_bad || [])
const alerts = computed(() => data.value.alerts || {})
function scoreColor(s) { if (s == null) return '#94a3b8'; if (s >= 0.7) return '#059669'; if (s >= 0.55) return '#d97706'; return '#dc2626' }
async function load() {
  loading.value = true
  try {
    const [d, a] = await Promise.all([api.dashboard({ range: range.value, app_id: appId.value }), api.apps()])
    data.value = d; apps.value = a
    renderCharts()
  } catch (e) {} finally { loading.value = false }
}
function renderCharts() {
  charts.forEach(c => c.dispose()); charts.length = 0
  if (trendEl.value) {
    const c = echarts.init(trendEl.value)
    charts.push(c)
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 36, right: 14, top: 18, bottom: 26 },
      xAxis: { type: 'category', data: data.value.trend.map((_, i) => 'D' + (i + 1)), axisLabel: { color: '#94a3b8' } },
      yAxis: { type: 'value', min: 0.5, max: 1, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [{
        type: 'line', smooth: true, data: data.value.trend, lineStyle: { width: 2.5, color: '#1f56e8' },
        itemStyle: { color: '#1f56e8' }, areaStyle: { color: 'rgba(47,107,255,.16)' },
        markLine: { silent: true, symbol: 'none', data: [{ yAxis: 0.6, label: { formatter: '阈值 0.6', color: '#ef4444' }, lineStyle: { color: '#ef4444', type: 'dashed' } }] },
      }],
    })
  }
  if (rankEl.value) {
    const c = echarts.init(rankEl.value)
    charts.push(c)
    const ranks = (data.value.ranking || []).slice(0, 6)
    c.setOption({
      grid: { left: 10, right: 46, top: 8, bottom: 24 },
      xAxis: { type: 'value', min: 0.6, max: 1, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      yAxis: { type: 'category', data: ranks.map(r => r.app), axisLabel: { color: '#475569', fontSize: 11 }, axisLine: { show: false }, axisTick: { show: false } },
      series: [{ type: 'bar', barWidth: 12, data: ranks.map(r => ({ value: r.score, itemStyle: { color: '#2f6bff' } })), itemStyle: { borderRadius: [4, 4, 0, 0] }, label: { show: true, position: 'right', fontWeight: 'bold', color: '#334155' } }],
    })
  }
}
onMounted(load)
</script>
