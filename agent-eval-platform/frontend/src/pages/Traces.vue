<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div>
        <h2 class="page-title">AI Agent 可观测</h2>
        <p class="page-sub">Trace / Session / Tool Call 全链路查询 · 点击行进入轨迹详情回放 Turn → Step</p>
      </div>
      <div style="display:flex;gap:8px">
        <el-select v-model="filters.app_id" clearable placeholder="全部应用" style="width:170px" @change="load">
          <el-option v-for="a in apps" :key="a.id" :value="a.id" :label="a.name" />
        </el-select>
        <el-select v-model="filters.status" clearable placeholder="全部状态" style="width:120px" @change="load">
          <el-option label="成功" value="ok" /><el-option label="失败" value="error" />
        </el-select>
        <el-input v-model="filters.session_id" placeholder="Session ID 搜索…" clearable style="width:220px" @change="load" />
      </div>
    </div>
    <el-table v-loading="loading" :data="items" style="width:100%" @row-click="row => $router.push('/traces/' + row.id)">
      <el-table-column prop="id" label="Trace ID" width="130"><template #default="{ row }"><span class="mono" style="color:#1f56e8">{{ row.id }}</span></template></el-table-column>
      <el-table-column prop="session_id" label="Session ID" width="180"><template #default="{ row }"><span class="mono" style="font-size:12px;color:#94a3b8">{{ row.session_id }}</span></template></el-table-column>
      <el-table-column prop="app" label="应用" width="150" />
      <el-table-column prop="model" label="模型" width="110" />
      <el-table-column prop="created_at" label="开始时间" width="165"  sortable/>
      <el-table-column label="耗时" width="100" sortable><template #default="{ row }">{{ (row.duration_ms / 1000).toFixed(1) }}s</template></el-table-column>
      <el-table-column prop="tokens" label="Token" width="90"  sortable/>
      <el-table-column label="状态" width="90">
        <template #default="{ row }"><el-tag size="small" :type="row.status === 'ok' ? 'success' : 'danger'">{{ row.status === 'ok' ? '成功' : '失败' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="Score" width="120" sortable>
        <template #default="{ row }"><el-tag v-if="row.score_avg != null" size="small" :type="scoreType(row.score_avg)">{{ row.score_avg.toFixed(2) }}</el-tag><span v-else style="color:#cbd5e1">未评估</span></template>
      </el-table-column>
    </el-table>
    <el-pagination style="margin-top:14px;justify-content:flex-end" layout="total, prev, pager, next" :total="total"
                   :page-size="filters.size" v-model:current-page="filters.page" @current-change="load" />
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const items = ref([]), apps = ref([]), total = ref(0), loading = ref(false)
const filters = reactive({ page: 1, size: 20, app_id: '', status: '', session_id: '' })
function scoreType(s) { return s >= 0.7 ? 'success' : s >= 0.55 ? 'warning' : 'danger' }
async function load() {
  loading.value = true
  try {
    const [t, a] = await Promise.all([api.traces(filters), api.apps()])
    items.value = t.items || []; total.value = t.total; apps.value = a
  } catch (e) {} finally { loading.value = false }
}
onMounted(load)
</script>
