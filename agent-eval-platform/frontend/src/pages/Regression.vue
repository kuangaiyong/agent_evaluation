<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div>
        <h2 class="page-title">实验与回归</h2>
        <p class="page-sub">新旧版本同一回归集对比评估 · 产出退化清单与发布建议 · V1.1 预览</p>
      </div>
      <el-button type="primary" :disabled="!canWrite" @click="openCreate">创建回归实验</el-button>
    </div>
    <el-table v-loading="loading" :data="runs" style="width:100%" @row-click="openReport">
      <el-table-column label="回归实验" min-width="220">
        <template #default="{ row }"><b>{{ row.name }}</b><div class="mono" style="font-size:11px;color:#cbd5e1">{{ row.id }} · {{ row.time }}</div></template>
      </el-table-column>
      <el-table-column prop="dataset" label="数据集" width="170" />
      <el-table-column label="版本对比" width="140"><template #default="{ row }"><span class="mono">{{ row.base_ver }}</span> → <span class="mono">{{ row.comp_ver }}</span></template></el-table-column>
      <el-table-column label="整体 Score 变化" width="180">
        <template #default="{ row }"><span class="mono">{{ row.base_score?.toFixed(3) }}</span> → <b class="mono" :style="{ color: (row.comp_score ?? 0) >= (row.base_score ?? 0) ? '#059669' : '#dc2626' }">{{ row.comp_score?.toFixed(3) }}</b></template>
      </el-table-column>
      <el-table-column label="退化 / 改进" width="110"><template #default="{ row }"><span style="color:#dc2626">{{ row.degraded }}</span> / <span style="color:#059669">{{ row.improved }}</span></template></el-table-column>
      <el-table-column label="结论" width="120">
        <template #default="{ row }"><el-tag size="small" :type="row.verdict === 'publish' ? 'success' : 'danger'">{{ row.verdict === 'publish' ? '可发布' : '不建议发布' }}</el-tag></template>
      </el-table-column>
    </el-table>

    <el-card v-if="report" style="margin-top:14px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <b>{{ report.name || '对比报告' }}</b>
        <el-button size="small" @click="report = null">关闭</el-button>
      </div>
      <el-row :gutter="10">
        <el-col :span="6" v-for="m in reportCards" :key="m[0]"><el-card><div style="font-size:11px;color:#94a3b8">{{ m[0] }}</div><b style="font-size:16px">{{ m[1] }}</b></el-card></el-col>
      </el-row>
      <el-table :data="reportRows" size="small" style="margin-top:12px">
        <el-table-column prop="trace_id" label="Trajectory" width="150" />
        <el-table-column label="base" width="90"><template #default="{ row }">{{ row.base?.toFixed(2) }}</template></el-table-column>
        <el-table-column label="comp" width="90"><template #default="{ row }">{{ row.comp?.toFixed(2) }}</template></el-table-column>
        <el-table-column label="Δ" width="90"><template #default="{ row }"><b :style="{ color: row.delta > 0.005 ? '#059669' : row.delta < -0.005 ? '#dc2626' : '#94a3b8' }">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta.toFixed(2) }}</b></template></el-table-column>
      </el-table>
    </el-card>

    
    <el-card style="margin-top:14px" v-if="gateInfo">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
        <div style="display:flex;gap:10px;align-items:center">
          <el-icon size="20" color="#059669"><Link /></el-icon>
          <div>
            <b>CI/CD 质量门禁</b>
            <div style="font-size:12px;color:#94a3b8;margin-top:2px">
              判定规则：{{ gateInfo.rule }}
              <span v-if="gateInfo.url"> · 回调地址：<span class="mono">{{ gateInfo.url }}</span></span>
              <span v-else> · 未配置回调地址（回归结论暂不推送）</span>
            </div>
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <el-tag :type="gateInfo.configured ? 'success' : 'info'" size="small">{{ gateInfo.configured ? '已启用' : '未启用' }}</el-tag>
          <el-tag v-if="gateInfo.last?.status" :type="gateInfo.last.status === 'sent' ? 'success' : 'danger'" size="small">
            最近送达：{{ gateInfo.last.status }} · {{ gateInfo.last.at }}
          </el-tag>
        </div>
      </div>
    </el-card>
    <el-dialog v-model="dlg" title="创建回归实验" width="520px">
      <el-form label-position="top">
        <el-form-item label="实验名称"><el-input v-model="form.name" placeholder="客服助手 v1.2 → v1.3 回归" /></el-form-item>
        <el-form-item label="回归集"><el-select v-model="form.dataset_id" style="width:100%"><el-option v-for="d in datasets" :key="d.id" :value="d.id" :label="d.name" /></el-select></el-form-item>
        <el-form-item label="关联应用"><el-select v-model="form.app_id" clearable style="width:100%"><el-option v-for="a in apps" :key="a.id" :value="a.id" :label="a.name" /></el-select></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="基准版本"><el-input v-model="form.base_ver" placeholder="v1.2" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="对比版本"><el-input v-model="form.comp_ver" placeholder="v1.3" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="dlg = false">取消</el-button><el-button type="primary" @click="create">创建并运行</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { store } from '../store'

const runs = ref([]), datasets = ref([]), apps = ref([]), loading = ref(false), dlg = ref(false), report = ref(null)
const gateInfo = ref(null)
const form = reactive({ name: '', dataset_id: '', app_id: '', base_ver: 'v1.2', comp_ver: 'v1.3' })
const canWrite = computed(() => ['admin', 'dev'].includes(store.wsRole))
const reportCards = computed(() => {
  const r = report.value?.report || {}
  return [['基准版本', r.base_score?.toFixed(3) ?? '—'], ['对比版本', r.comp_score?.toFixed(3) ?? '—'],
          ['退化样本', r.degraded ?? 0], ['改进样本', r.improved ?? 0]]
})
const reportRows = computed(() => (report.value?.report?.rows || []).slice(0, 100))
async function load() { loading.value = true; try { runs.value = await api.regRuns() } catch (e) {} finally { loading.value = false } }
async function openCreate() { try { [datasets.value, apps.value] = await Promise.all([api.datasets(), api.apps()]) } catch (e) {}; dlg.value = true }
async function create() { try { await api.createRegRun(form); ElMessage.success('回归实验已创建并运行'); dlg.value = false; load() } catch (e) { ElMessage.error(e.message) } }
async function openReport(row) { try { report.value = await api.regRun(row.id) } catch (e) {} }
onMounted(() => { load(); api.regGateInfo().then(r => gateInfo.value = r).catch(() => {}) })
</script>
