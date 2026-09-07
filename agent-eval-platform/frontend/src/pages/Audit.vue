<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;gap:16px;flex-wrap:wrap">
      <div>
        <h2 class="page-title">操作审计</h2>
        <p class="page-sub">
          append-only 关键操作留痕 · 改评分器 rubric / 改金标准 / 重跑任务 三类标记为高风险 · 判定依据长期保留
        </p>
      </div>
      <el-button @click="exportCsv">导出审计记录</el-button>
    </div>

    <el-row :gutter="10" style="margin-bottom:12px">
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">当前范围记录</div>
        <div class="kpi-num">{{ rows.length }}</div></el-card></el-col>
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">高风险操作</div>
        <div class="kpi-num" :style="{ color: highRiskCount ? '#b45309' : undefined }">{{ highRiskCount }}</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">改 rubric / 改金标准 / 重跑</div></el-card></el-col>
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">失败操作</div>
        <div class="kpi-num">{{ failedCount }}</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">多为权限不足</div></el-card></el-col>
      <el-col :xs="12" :sm="6"><el-card><div style="font-size:12px;color:#64748b">留存策略</div>
        <div class="kpi-num" style="font-size:19px;padding-top:5px">永久</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">判定依据不随轨迹归档</div></el-card></el-col>
    </el-row>

    <el-card style="margin-bottom:12px">
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        <el-select v-model="filters.actor" clearable placeholder="全部操作人" style="width:170px" @change="load">
          <el-option v-for="a in actors" :key="a" :value="a" :label="a" />
        </el-select>
        <el-button :type="filters.highRisk ? 'primary' : 'default'" @click="toggleHighRisk">仅高风险</el-button>
        <el-select v-model="filters.limit" style="width:140px" @change="load">
          <el-option :value="30" label="最近 30 条" />
          <el-option :value="100" label="最近 100 条" />
          <el-option :value="500" label="最近 500 条" />
        </el-select>
        <el-button text @click="reset">重置</el-button>
        <span style="margin-left:auto;font-size:12.5px;color:#64748b">命中 {{ rows.length }} 条</span>
      </div>
    </el-card>

    <el-table v-loading="loading" :data="rows" style="width:100%" @row-click="open">
      <el-table-column prop="actor" label="操作人" width="130">
        <template #default="{ row }"><b>{{ row.actor }}</b></template>
      </el-table-column>
      <el-table-column label="操作" min-width="200">
        <template #default="{ row }">
          <el-tag v-if="row.high_risk" size="small" type="warning" effect="plain" style="margin-right:6px">高风险</el-tag>
          {{ row.action }}
        </template>
      </el-table-column>
      <el-table-column prop="obj" label="对象" min-width="240" show-overflow-tooltip />
      <el-table-column label="结果" width="130">
        <template #default="{ row }">
          <el-tag size="small" :type="row.result.includes('成功') ? 'success' : 'danger'">{{ row.result }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="time" label="时间" width="180" sortable />
      <template #empty>
        <div style="padding:28px 0;color:#94a3b8;font-size:13px">没有符合条件的操作记录</div>
      </template>
    </el-table>

    <el-drawer v-model="drawer" :title="cur ? cur.action : ''" size="480px">
      <div v-if="cur" style="display:flex;flex-direction:column;gap:14px;font-size:13.5px;line-height:1.8">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-tag size="small">{{ cur.actor }}</el-tag>
          <el-tag v-if="cur.high_risk" size="small" type="warning">高风险操作</el-tag>
          <el-tag size="small" :type="cur.result.includes('成功') ? 'success' : 'danger'">{{ cur.result }}</el-tag>
        </div>
        <div v-for="f in detailFields" :key="f.k" v-show="cur[f.k]">
          <div style="font-size:12px;color:#64748b;font-weight:600;margin-bottom:3px">{{ f.t }}</div>
          <div style="color:#3f4954;white-space:pre-line">{{ cur[f.k] }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const rows = ref([]), actors = ref([]), loading = ref(false)
const drawer = ref(false), cur = ref(null)
const filters = reactive({ actor: '', highRisk: false, limit: 30 })

const detailFields = [
  { k: 'obj', t: '操作对象' }, { k: 'time', t: '时间' }, { k: 'ip', t: '来源 IP' },
]
const highRiskCount = computed(() => rows.value.filter(r => r.high_risk).length)
const failedCount = computed(() => rows.value.filter(r => !r.result.includes('成功')).length)

async function load() {
  loading.value = true
  try {
    rows.value = await api.audits({
      actor: filters.actor || undefined,
      high_risk: filters.highRisk || undefined,
      limit: filters.limit,
    })
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}
function toggleHighRisk() { filters.highRisk = !filters.highRisk; load() }
function reset() { filters.actor = ''; filters.highRisk = false; filters.limit = 30; load() }
function open(row) { cur.value = row; drawer.value = true }

function exportCsv() {
  const head = ['操作人', '操作', '对象', '结果', '时间', '高风险']
  const body = rows.value.map(r => [r.actor, r.action, r.obj, r.result, r.time, r.high_risk ? '是' : '否'])
  const csv = [head, ...body].map(cols => cols.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url; a.download = `审计记录-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a); a.click(); a.remove()
  // 紧跟 click 就 revoke 会让 Firefox/Safari 的下载中断，挪到下一轮事件循环
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  ElMessage.success(`已导出 ${rows.value.length} 条审计记录`)
}

onMounted(() => { load(); api.auditActors().then(r => actors.value = r).catch(() => {}) })
</script>
