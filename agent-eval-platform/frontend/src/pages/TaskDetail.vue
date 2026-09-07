<template>
  <div v-loading="loading">
    <template v-if="t">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
        <div>
          <h2 class="page-title">{{ t.name }}</h2>
          <p class="page-sub">{{ t.id }} · {{ t.app || t.dataset }} · 阈值 {{ t.threshold }} · 采样率 {{ t.sample_rate }}%</p>
        </div>
        <div style="display:flex;gap:8px">
          <el-tag :type="stMap[t.status]?.type">{{ stMap[t.status]?.label }}</el-tag>
          <el-button v-if="t.status === 'running'" :disabled="!canWrite" @click="act('pause')">暂停</el-button>
          <el-button v-if="['paused', 'error', 'created'].includes(t.status)" :disabled="!canWrite" type="primary" @click="act('resume')">恢复</el-button>
          <el-button v-if="t.status === 'created'" :disabled="!canWrite" type="primary" @click="act('start')">启动</el-button>
          <el-button :disabled="!canWrite" type="danger" plain @click="act('terminate')">终止</el-button>
        </div>
      </div>
      <el-alert v-if="t.err_msg" type="error" show-icon :title="t.err_msg" style="margin-bottom:12px" />
      <el-row :gutter="10" style="margin-bottom:12px">
        <el-col :span="4" v-for="m in statItems" :key="m[0]"><el-card><div style="font-size:11px;color:#94a3b8">{{ m[0] }}</div><b style="font-size:18px">{{ m[1] }}</b></el-card></el-col>
      </el-row>
      <el-card>
        <div style="font-weight:700;margin-bottom:10px">最近评估结果</div>
        <el-table :data="results" size="small">
          <el-table-column prop="trace_id" label="Trace" width="140"><template #default="{ row }"><span class="mono" style="color:#1f56e8" @click="$router.push('/traces/' + row.trace_id)">{{ row.trace_id }}</span></template></el-table-column>
          <el-table-column prop="evaluator" label="评估器" width="150" />
          <el-table-column label="Score" width="120"><template #default="{ row }"><b :style="{ color: scoreColor(row.score) }">{{ row.score?.toFixed(2) || '—' }}</b></template></el-table-column>
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column prop="time" label="时间" width="100" />
          <el-table-column label="依据"><template #default="{ row }">{{ row.meta?.reason }}</template></el-table-column>
          <el-table-column label="失败" width="80"><template #default="{ row }"><el-tag v-if="row.failed" size="small" type="danger">失败</el-tag></template></el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { store, canWrite } from '../store'

const route = useRoute()
const t = ref(null), results = ref([]), loading = ref(false)
const stMap = { running: { label: '运行中', type: 'success' }, paused: { label: '已暂停', type: 'warning' }, error: { label: '异常', type: 'danger' }, terminated: { label: '已终止', type: 'info' }, completed: { label: '已完成', type: 'primary' }, created: { label: '待启动', type: 'info' } }
const statItems = computed(() => {
  const s = t.value?.stats || {}
  return [['累计评估', s.count ?? 0], ['平均 Score', (s.avg ?? 0).toFixed(2)], ['低分 Case', s.low ?? 0], ['评估失败', s.fail ?? 0], ['Judge 额度', s.avg ? '¥0.086/日' : '—']]
})
function scoreColor(s) { if (s == null) return '#94a3b8'; return s >= 0.7 ? '#059669' : s >= 0.55 ? '#d97706' : '#dc2626' }
async function load() {
  loading.value = true
  try {
    t.value = await api.task(route.params.id)
    results.value = await api.taskResults(route.params.id)
  } catch (e) {} finally { loading.value = false }
}
async function act(action) {
  if (action === 'terminate') { try { await ElMessageBox.confirm('终止后不可恢复，确认？', '提示', { type: 'warning' }) } catch (e) { return } }
  try { await api.taskAction(t.value.id, action); ElMessage.success('已执行：' + action); load() } catch (e) { ElMessage.error(e.message) }
}
onMounted(load)
</script>
