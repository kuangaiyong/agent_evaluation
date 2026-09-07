<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div>
        <h2 class="page-title">评估任务</h2>
        <p class="page-sub">离线批量评估数据集（门禁主路径）· 在线持续评估生产轨迹 · 状态机：创建 → 运行中 ⇄ 已暂停 → 异常 → 已终止</p>
      </div>
      <el-button type="primary" :disabled="!canWrite" @click="openCreate">创建评估任务</el-button>
    </div>
    <el-tabs v-model="tab" @tab-change="load">
      <el-tab-pane label="离线任务" name="offline" />
      <el-tab-pane label="在线任务" name="online" />
    </el-tabs>
    <el-table v-loading="loading" :data="items" style="width:100%" @row-click="row => $router.push('/tasks/' + row.id)">
      <el-table-column label="任务名称" min-width="220">
        <template #default="{ row }"><b>{{ row.name }}</b>
          <div class="mono" style="font-size:11px;color:#cbd5e1">{{ row.id }} · {{ row.created_at }}</div></template>
      </el-table-column>
      <el-table-column prop="app" label="应用" width="140" />
      <el-table-column v-if="tab === 'offline'" prop="dataset" label="数据集" min-width="150">
        <template #default="{ row }">{{ row.dataset || '—' }}</template>
      </el-table-column>
      <el-table-column label="评估器" min-width="200">
        <template #default="{ row }"><el-tag v-for="e in row.evaluators" :key="e.id" size="small" effect="plain" style="margin-right:4px">{{ e.name }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="sample_rate" label="采样率" width="90"><template #default="{ row }">{{ row.sample_rate }}%</template></el-table-column>
      <el-table-column prop="threshold" label="阈值" width="80" />
      <el-table-column label="已评估" width="100" sortable><template #default="{ row }">{{ row.stats?.count ?? 0 }}</template></el-table-column>
      <el-table-column label="平均分" width="90" sortable><template #default="{ row }">{{ (row.stats?.avg ?? 0).toFixed(2) }}</template></el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }"><el-tag size="small" :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.label || row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" v-if="row.status === 'running'" :disabled="!canWrite" @click.stop="act(row, 'pause')">暂停</el-button>
          <el-button size="small" v-if="['paused', 'error', 'created'].includes(row.status)" :disabled="!canWrite" @click.stop="act(row, 'resume')">恢复</el-button>
          <el-button size="small" v-if="row.status === 'created'" :disabled="!canWrite" @click.stop="act(row, 'start')">启动</el-button>
          <el-button size="small" :disabled="!canWrite" @click.stop="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" plain :disabled="!canWrite" @click.stop="act(row, 'terminate')">终止</el-button>
        </template>
      </el-table-column>
    </el-table>


    <el-dialog v-model="editDlg" title="编辑任务配置" width="520px">
      <template v-if="editRow">
        <el-form label-position="top">
          <el-form-item label="绑定评估器（多选）">
            <el-select v-model="editForm.evaluator_ids" multiple style="width:100%">
              <el-option v-for="e in evs.filter(x => x.status === 'published')" :key="e.id" :value="e.id" :label="e.name" /></el-select>
          </el-form-item>
          <el-form-item label="低分阈值">
            <el-slider v-model="editForm.threshold" :min="0.3" :max="0.8" :step="0.05" show-input />
          </el-form-item>
        </el-form>
        <div style="font-size:12px;color:#94a3b8">仅影响此后新轨迹的评估结果；已评分轨迹保持不变（可用「试运行」单独验证历史样本）</div>
      </template>
      <template #footer><el-button @click="editDlg = false">取消</el-button><el-button type="primary" @click="saveEdit">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="dlg" title="创建评估任务" width="560px">
      <el-form label-position="top">
        <el-form-item label="任务名称 *"><el-input v-model="form.name" placeholder="例如：客服助手·在线全量评估" /></el-form-item>
        <el-form-item label="任务类型">
          <el-radio-group v-model="form.mode">
            <el-radio-button value="online">在线评估</el-radio-button>
            <el-radio-button value="offline">离线评估（数据集）</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="form.mode === 'online' ? '关联应用 *' : '目标数据集 *'">
          <el-select v-model="form.app_id" :disabled="form.mode === 'offline'" style="width:100%">
            <el-option v-for="a in apps" :key="a.id" :value="a.id" :label="a.name" /></el-select>
          <el-select v-if="form.mode === 'offline'" v-model="form.dataset_id" style="width:100%;margin-top:6px">
            <el-option v-for="d in datasets" :key="d.id" :value="d.id" :label="d.name + '（' + d.type + '）'" /></el-select>
        </el-form-item>
        <el-form-item label="绑定评估器（多选）">
          <el-select v-model="form.evaluator_ids" multiple style="width:100%">
            <el-option v-for="e in evs.filter(x => x.status === 'published')" :key="e.id" :value="e.id" :label="e.name" /></el-select>
        </el-form-item>
        <el-form-item label="低分阈值">
          <el-slider v-model="form.threshold" :min="0.3" :max="0.8" :step="0.05" show-input />
        </el-form-item>
        <el-form-item v-if="form.mode === 'online'" label="采样率（成本保护）">
          <el-slider v-model="form.sample_rate" :min="1" :max="100" />
        </el-form-item>
        <el-alert type="info" :closable="false">Score < 阈值 的 Case 自动进入 Bad Case 待复核队列</el-alert>
      </el-form>
      <template #footer><el-button @click="dlg = false">取消</el-button><el-button type="primary" @click="create">创建任务</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { store, canWrite } from '../store'

const tab = ref('offline'), items = ref([]), apps = ref([]), evs = ref([]), datasets = ref([]), loading = ref(false), dlg = ref(false), editDlg = ref(false)
const editRow = ref(null), editForm = ref({ evaluator_ids: [], threshold: 0.6 })
const form = reactive({ name: '', mode: 'offline', app_id: '', dataset_id: '', evaluator_ids: [], threshold: 0.6, sample_rate: 100 })
const statusMap = { running: { label: '运行中', type: 'success' }, paused: { label: '已暂停', type: 'warning' }, error: { label: '异常', type: 'danger' }, terminated: { label: '已终止', type: 'info' }, completed: { label: '已完成', type: 'primary' }, created: { label: '待启动', type: 'info' } }
async function load() {
  loading.value = true
  try { items.value = await api.tasks({ mode: tab.value }) } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}
async function openCreate() {
  try {
    const [a, e, d] = await Promise.all([api.apps(), api.evaluators(), api.datasets()])
    apps.value = a; evs.value = e; datasets.value = d
    form.name = ''; form.evaluator_ids = []; form.app_id = a[0]?.id || ''
  } catch (e) {}
  dlg.value = true
}
async function openEdit(row) {
  editRow.value = row
  try { if (!evs.value.length) evs.value = await api.evaluators() } catch (e) {}
  editForm.value = { evaluator_ids: [...(row.evaluators?.map(x => x.id) || [])], threshold: row.threshold }
  editDlg.value = true
}
async function saveEdit() {
  try {
    await api.updateTask(editRow.value.id, { evaluator_ids: editForm.value.evaluator_ids, threshold: editForm.value.threshold })
    ElMessage.success('任务配置已更新'); editDlg.value = false; load()
  } catch (e) { ElMessage.error(e.message) }
}
async function create() {
  if (!form.name) return ElMessage.warning('请输入任务名称')
  try { await api.createTask(form); ElMessage.success('任务已创建（待启动）'); dlg.value = false; load() } catch (e) { ElMessage.error(e.message) }
}
async function act(row, action) {
  const label = { pause: '暂停', resume: '恢复', start: '启动', terminate: '终止' }[action]
  if (['terminate'].includes(action)) {
    try { await ElMessageBox.confirm('终止后任务不可恢复，已产生的数据保留。确认终止？', '终止 ' + row.name, { type: 'warning' }) }
    catch (e) { return }
  }
  try { await api.taskAction(row.id, action); ElMessage.success('已' + label); load() } catch (e) { ElMessage.error(e.message) }
}
onMounted(load)
</script>
