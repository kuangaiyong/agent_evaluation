<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div>
        <h2 class="page-title">数据中心</h2>
        <p class="page-sub">Trajectory 标准化轨迹库 · 三类数据集（评测集 / 回归集 / 经典 Case）版本化管理与 Trace2Dataset 导入</p>
      </div>
      <el-button type="primary" :disabled="!canWrite" @click="openCreateDs">上传 / 创建数据集</el-button>
    </div>
    <el-tabs v-model="tab" @tab-change="onTab">
      <el-tab-pane label="轨迹库" name="traj" />
      <el-tab-pane label="数据集" name="ds" />
    </el-tabs>

    <template v-if="tab === 'traj'">
      <el-table v-loading="trajLoading" :data="trajs" style="width:100%">
        <el-table-column prop="id" label="Trajectory" width="140"><template #default="{ row }"><span class="mono" style="color:#1f56e8" @click="$router.push('/traces/' + row.id)">{{ row.id }}</span></template></el-table-column>
        <el-table-column prop="session_id" label="Session" width="180" />
        <el-table-column prop="app" label="应用" width="150" />
        <el-table-column prop="turn_count" label="Turn" width="80" />
        <el-table-column prop="tokens" label="Token" width="100" />
        <el-table-column prop="time" label="产生时间" width="165" />
        <el-table-column label="评估状态" width="160">
          <template #default="{ row }"><el-tag v-if="row.evaluated" size="small" type="success">已评估 · {{ row.score_avg?.toFixed(2) }}</el-tag><el-tag v-else size="small" type="info">未评估</el-tag></template>
        </el-table-column>
        <el-table-column width="90"><template #default="{ row }"><el-checkbox v-model="row._sel" /></template></el-table-column>
      </el-table>
      <div style="display:flex;justify-content:space-between;margin-top:10px;align-items:center">
        <span style="font-size:12px;color:#94a3b8">已选 {{ selTrajs.length }} 条</span>
        <el-button size="small" :disabled="!selTrajs.length || !canWrite" @click="importSel">批量入库到数据集</el-button>
      </div>
    </template>

    <template v-else>
      <el-row :gutter="12">
        <el-col :md="6" v-for="d in datasets" :key="d.id">
          <el-card style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between">
              <b>{{ d.name }}</b>
              <el-tag size="small" :type="dsTypeMap[d.type]" effect="plain">{{ d.type }}</el-tag>
            </div>
            <div class="mono" style="font-size:10.5px;color:#cbd5e1;margin:2px 0 8px">{{ d.id }} · {{ d.version }}</div>
            <div style="display:flex;gap:16px;margin-bottom:8px">
              <span><b class="mono">{{ d.samples }}</b> 样本</span>
              <span><b class="mono">{{ d.version }}</b> 版本</span>
            </div>
            <div v-if="d.refs?.length" style="font-size:11px;color:#d97706;margin-bottom:8px"><el-icon><Lock /></el-icon> 被引用：{{ d.refs.join('、') }}</div>
            <el-button size="small" @click="openDs(d)">查看样本</el-button>
            <el-button size="small" type="danger" plain :disabled="!canWrite || d.refs?.length" @click="removeDs(d)">删除</el-button>
          </el-card>
        </el-col>
      </el-row>
      <el-card v-if="curDs">
        <div style="font-weight:700;margin-bottom:10px">样本列表 · {{ curDs.name }}</div>
        <el-table :data="curDs.samples" size="small">
          <el-table-column prop="trace_id" label="Trajectory" width="140"><template #default="{ row }"><span class="mono" style="color:#1f56e8">{{ row.trace_id }}</span></template></el-table-column>
          <el-table-column prop="session_id" label="Session" width="180" />
          <el-table-column prop="label" label="样本类型" width="120" />
          <el-table-column label="Score" width="100"><template #default="{ row }">{{ row.score?.toFixed(2) || '—' }}</template></el-table-column>
          <el-table-column prop="time" label="入库时间" />
        </el-table>
      </el-card>
    </template>

    <el-dialog v-model="dsDlg" title="上传 / 创建数据集" width="520px">
      <el-form label-position="top">
        <el-form-item label="数据集名称"><el-input v-model="dsForm.name" placeholder="例如：电商客服评测集 0821" /></el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="dsForm.type"><el-radio-button value="评测集">评测集</el-radio-button><el-radio-button value="回归集">回归集</el-radio-button><el-radio-button value="经典 Case">经典 Case</el-radio-button></el-radio-group>
        </el-form-item>
        <el-form-item label="上传文件（JSON/CSV，含 session_id 字段）">
          <input type="file" accept=".json,.csv" @change="onFile" />
          <div style="font-size:11.5px;color:#94a3b8;margin-top:6px">单文件 ≤ 100MB · Schema 校验失败返回行级错误明细</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dsDlg = false">取消</el-button>
        <el-button type="primary" @click="saveDs">创建并校验导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { store } from '../store'

const route = useRoute()
const tab = ref(route.query.tab === 'ds' ? 'ds' : 'traj')
const trajs = ref([]), trajLoading = ref(false), datasets = ref([]), curDs = ref(null)
const dsDlg = ref(false), dsFile = ref(null)
const dsForm = reactive({ name: '', type: '评测集' })
const canWrite = computed(() => ['admin', 'dev'].includes(store.wsRole))
const selTrajs = computed(() => trajs.value.filter(t => t._sel))
const dsTypeMap = { 评测集: 'primary', 回归集: 'success', '经典 Case': 'warning' }
async function loadTraj() { trajLoading.value = true; try { trajs.value = (await api.trajectories({ size: 100 })).items } catch (e) {} finally { trajLoading.value = false } }
async function loadDs() { try { datasets.value = await api.datasets() } catch (e) {} }
function onTab(n) { n === 'traj' ? loadTraj() : loadDs() }
async function importSel() {
  try {
    const ids = selTrajs.value.map(t => t.id)
    await ElMessageBox.prompt('目标数据集 ID（默认 ds-eval-01）', '批量入库', { inputValue: 'ds-eval-01' })
    const did = await ElMessageBox.prompt('目标数据集 ID', '批量入库', { inputValue: 'ds-eval-01' }).catch(() => null)
    if (!did) return
    const r = await api.fromTraces(did.value, { trace_ids: ids, label: '轨迹导入' })
    ElMessage.success('已入库 ' + r.added + ' 条 · 新版本 ' + r.version)
  } catch (e) { /* cancel */ }
}
async function openDs(d) { curDs.value = { ...d, samples: (await api.dataset(d.id)).samples } }
async function removeDs(d) {
  try { await ElMessageBox.confirm('删除「' + d.name + '」将同步删除全部版本，不可撤销。', '删除数据集', { type: 'warning' })
    await api.deleteDataset(d.id); ElMessage.success('已删除'); loadDs() } catch (e) { if (e.message?.includes('被引用')) ElMessage.error(e.message); }
}
function onFile(e) { dsFile.value = e.target.files?.[0] || null }
async function saveDs() {
  try {
    let d = await api.createDataset(dsForm)
    if (dsFile.value) { const r = await api.uploadDataset(d.id, dsFile.value); ElMessage.success('导入 ' + r.rows + ' 行' + (r.errors?.length ? ' · ' + r.errors.length + ' 行错误（详见明细）' : '')) }
    else ElMessage.success('已创建数据集（空）')
    dsDlg.value = false; loadDs()
  } catch (e) { ElMessage.error(e.message) }
}
async function openCreateDs() { dsForm.name = ''; dsFile.value = null; dsDlg.value = true }
onMounted(() => { tab.value === 'traj' ? loadTraj() : loadDs() })
</script>
