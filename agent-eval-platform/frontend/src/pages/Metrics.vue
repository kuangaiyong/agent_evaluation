<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;gap:16px;flex-wrap:wrap">
      <div>
        <h2 class="page-title">指标库</h2>
        <p class="page-sub">
          {{ total }} 项指标的<b>只读</b>字典 · 按「层 × 柱」定位 · 评估器挂靠到指标编号后才计入覆盖度
        </p>
      </div>
      <el-tag type="info" effect="plain" size="small">
        权威源是 01 分册，改指标改文档后跑 scripts/sync_metrics.py
      </el-tag>
    </div>

    <el-row :gutter="10" style="margin-bottom:12px">
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">指标总数</div>
        <div class="kpi-num">{{ total }}</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">{{ facets.groups?.length || 0 }} 组</div></el-card></el-col>
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">已挂靠评估器</div>
        <div class="kpi-num" :style="{ color: cov.done ? '#047857' : '#b45309' }">{{ cov.done ?? 0 }}</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">本工作空间口径</div></el-card></el-col>
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">覆盖率</div>
        <div class="kpi-num">{{ covPct }}<span style="font-size:15px">%</span></div>
        <el-progress :percentage="covPct" :show-text="false" :stroke-width="6" style="margin-top:7px" /></el-card></el-col>
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">未覆盖</div>
        <div class="kpi-num">{{ (cov.total ?? 0) - (cov.done ?? 0) }}</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">还没有任何评估器</div></el-card></el-col>
    </el-row>

    <el-card v-loading="loadingCov" style="margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">
        <b style="font-size:14px">「层 × 柱」覆盖度</b>
        <span style="font-size:11.5px;color:#94a3b8">每格「已挂靠 / 该格总数」· 点格子筛选 · 层与柱的取值由字典决定，不是写死的 5×4</span>
      </div>
      <div style="overflow-x:auto">
        <table class="mx">
          <thead>
            <tr><th></th><th v-for="p in cov.pillars" :key="p">{{ p }}</th><th>合计</th></tr>
          </thead>
          <tbody>
            <tr v-for="l in cov.layers" :key="l">
              <th class="rw">{{ l }}</th>
              <td v-for="p in cov.pillars" :key="p" :class="cellClass(l, p)"
                  :style="{ cursor: cell(l, p) ? 'pointer' : 'default' }"
                  @click="cell(l, p) && pickCell(l, p)">
                <template v-if="cell(l, p)"><b>{{ cell(l, p).done }}/{{ cell(l, p).total }}</b></template>
                <template v-else><span style="color:#cbd5e1">·</span></template>
              </td>
              <td class="tot"><b>{{ rowTotal(l) }}</b></td>
            </tr>
            <tr><th class="rw">合计</th>
              <td v-for="p in cov.pillars" :key="p" class="tot"><b>{{ colTotal(p) }}</b></td>
              <td class="tot"><b>{{ cov.total ?? 0 }}</b></td></tr>
          </tbody>
        </table>
      </div>
    </el-card>

    <el-card style="margin-bottom:12px">
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        <el-select v-model="f.layer" clearable placeholder="层" style="width:130px" @change="load">
          <el-option v-for="l in facets.layers" :key="l" :value="l" :label="l" /></el-select>
        <el-select v-model="f.pillar" clearable placeholder="柱" style="width:180px" @change="load">
          <el-option v-for="p in facets.pillars" :key="p" :value="p" :label="p" /></el-select>
        <el-select v-model="f.group" clearable placeholder="分组" style="width:210px" @change="load">
          <el-option v-for="g in facets.groups" :key="g.code" :value="g.code" :label="g.code + ' 组 · ' + g.name" /></el-select>
        <el-input v-model="f.q" clearable placeholder="搜编号或名称" style="width:200px" @keyup.enter="load" @clear="load" />
        <el-button @click="load">查询</el-button>
        <el-button text @click="reset">重置</el-button>
        <span style="margin-left:auto;font-size:12.5px;color:#64748b">命中 {{ items.length }} / {{ total }}</span>
      </div>
    </el-card>

    <el-table v-loading="loading" :data="items" style="width:100%" @row-click="open">
      <el-table-column label="编号" width="92">
        <template #default="{ row }"><b class="mono">{{ row.code }}</b></template>
      </el-table-column>
      <el-table-column prop="name" label="指标名称" min-width="220" />
      <el-table-column label="层 × 柱" width="180">
        <template #default="{ row }">{{ row.layer }} · {{ row.pillar }}</template>
      </el-table-column>
      <el-table-column label="分组" width="150">
        <template #default="{ row }"><span style="color:#64748b">{{ row.group_code }} · {{ row.group_name }}</span></template>
      </el-table-column>
      <el-table-column label="阈值" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.threshold || '—' }}</template>
      </el-table-column>
      <el-table-column label="已挂评估器" width="180">
        <template #default="{ row }">
          <el-tag v-for="e in row.evaluators" :key="e.id" size="small" type="success" effect="plain"
                  style="margin-right:4px">{{ e.name }} {{ e.version }}</el-tag>
          <span v-if="!row.evaluators.length" style="color:#b45309;font-size:12.5px">未挂靠</span>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="dlg" :title="cur ? cur.code + ' · ' + cur.name : ''" size="560px">
      <div v-if="cur" style="display:flex;flex-direction:column;gap:14px;font-size:13.5px;line-height:1.8">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-tag size="small">{{ cur.layer }} · {{ cur.pillar }}</el-tag>
          <el-tag size="small" type="info">{{ cur.group_code }} 组 · {{ cur.group_name }}</el-tag>
        </div>
        <div v-for="s in sections" :key="s.k" v-show="cur[s.k]">
          <div style="font-size:12px;color:#64748b;font-weight:600;margin-bottom:3px">{{ s.t }}</div>
          <div style="white-space:pre-line;color:#3f4954">{{ cur[s.k] }}</div>
        </div>
        <div>
          <div style="font-size:12px;color:#64748b;font-weight:600;margin-bottom:5px">已挂靠评估器</div>
          <template v-if="cur.evaluators.length">
            <el-tag v-for="e in cur.evaluators" :key="e.id" size="small" type="success" effect="plain"
                    style="margin-right:6px">{{ e.name }} · {{ e.type }} · {{ e.version }}</el-tag>
          </template>
          <el-alert v-else type="warning" :closable="false" show-icon
                    title="这项指标还没有任何评估器实现，覆盖度里算作未覆盖。" />
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const items = ref([]), total = ref(0), cov = ref({}), facets = ref({})
const loading = ref(false), loadingCov = ref(false), dlg = ref(false), cur = ref(null)
const f = reactive({ layer: '', pillar: '', group: '', q: '' })

const sections = [
  { k: 'definition', t: '定义' }, { k: 'formula', t: '公式' }, { k: 'collection', t: '采集' },
  { k: 'pitfall', t: '陷阱' }, { k: 'notes', t: '实测与补充' }, { k: 'threshold', t: '阈值' },
]

const covPct = computed(() => cov.value.total ? Math.round(cov.value.done / cov.value.total * 100) : 0)
const cellMap = computed(() => Object.fromEntries((cov.value.cells || []).map(c => [c.layer + '|' + c.pillar, c])))
function cell(l, p) { return cellMap.value[l + '|' + p] }
function rowTotal(l) { return (cov.value.cells || []).filter(c => c.layer === l).reduce((a, c) => a + c.total, 0) }
function colTotal(p) { return (cov.value.cells || []).filter(c => c.pillar === p).reduce((a, c) => a + c.total, 0) }
function cellClass(l, p) {
  const c = cell(l, p)
  if (!c) return 'cov-none'
  const r = c.done / c.total
  return r === 0 ? 'cov0' : r < 0.34 ? 'cov1' : r < 0.67 ? 'cov2' : 'cov3'
}
function pickCell(l, p) { f.layer = l; f.pillar = p; load() }

async function load() {
  loading.value = true
  try {
    const d = await api.metrics({ layer: f.layer, pillar: f.pillar, group: f.group, q: f.q })
    items.value = d.items; total.value = d.total
  } finally { loading.value = false }
}
async function loadCov() {
  loadingCov.value = true
  try { cov.value = await api.metricCoverage() } catch (e) { /* 忽略 */ } finally { loadingCov.value = false }
}
function reset() { f.layer = ''; f.pillar = ''; f.group = ''; f.q = ''; load() }
async function open(row) { try { cur.value = await api.metric(row.code); dlg.value = true } catch (e) { /* 忽略 */ } }

onMounted(async () => {
  await Promise.all([load(), loadCov(), api.metricFacets().then(r => facets.value = r).catch(() => {})])
})
</script>

<style scoped>
.mx { border-collapse: separate; border-spacing: 3px; min-width: 620px; font-size: 12.5px; }
.mx th { padding: 5px 8px; font-size: 11.5px; color: #3f4954; white-space: nowrap; text-align: center; font-weight: 600; }
.mx th.rw { text-align: right; }
.mx td { text-align: center; padding: 9px 6px; border-radius: 6px; font-variant-numeric: tabular-nums; }
.cov-none { background: #fafbfc; }
.cov0 { background: #f1f5f9; color: #5c6a7d; }
.cov1 { background: #dbe7fd; color: #11181f; }
.cov2 { background: #a9c4f8; color: #11181f; }
.cov3 { background: #3565e0; color: #fff; }
.mx td.tot { background: #f8fafc; color: #11181f; font-weight: 600; }
</style>
