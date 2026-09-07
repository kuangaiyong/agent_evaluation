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
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-checkbox v-model="row._sel" style="margin-right:8px" />
            <el-button size="small" :disabled="!canWrite" @click.stop="toDataset(row)">转为评测任务</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex;justify-content:space-between;margin-top:10px;align-items:center">
        <span style="font-size:12px;color:#94a3b8">已选 {{ selTrajs.length }} 条</span>
        <el-button size="small" :disabled="!selTrajs.length || !canWrite" @click="importSel">批量入库到数据集</el-button>
      </div>
    </template>

    <template v-else>
      <el-table :data="datasets" style="width:100%" @row-click="openDs">
        <el-table-column label="数据集" min-width="200">
          <template #default="{ row }">
            <b>{{ row.name }}</b>
            <div class="mono" style="font-size:11px;color:#cbd5e1">{{ row.id }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }"><el-tag size="small" :type="dsTypeMap[row.type]" effect="plain">{{ row.type }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="90" />
        <el-table-column prop="samples" label="条目数" width="90" sortable />
        <el-table-column label="已配金标准" width="150">
          <template #default="{ row }">
            <b :style="{ color: row.gold >= row.samples ? '#059669' : '#b45309' }">{{ row.gold ?? 0 }} / {{ row.samples }}</b>
            <div v-if="row.samples && (row.gold ?? 0) < row.samples" style="font-size:11px;color:#b45309">
              {{ row.samples - (row.gold ?? 0) }} 条待补录金标准
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最近使用" min-width="150">
          <template #default="{ row }">{{ row.refs?.length ? row.refs.join('、') : '—' }}</template>
        </el-table-column>
        <el-table-column prop="updated" label="更新时间" width="120" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="openDs(row)">查看样本</el-button>
            <el-button size="small" type="danger" plain :disabled="!canWrite || row.refs?.length" @click.stop="removeDs(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
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
import { store, canWrite } from '../store'

const route = useRoute()
const tab = ref(route.query.tab === 'ds' ? 'ds' : 'traj')
const trajs = ref([]), trajLoading = ref(false), datasets = ref([]), curDs = ref(null)
const dsDlg = ref(false), dsFile = ref(null)
const dsForm = reactive({ name: '', type: '评测集' })
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
// 单条轨迹转评测任务。入库条目的金标准为空，进入待补录队列。
// 注意：specs/data-center 还要求「未补录的条目不参与门禁判定」，该行为尚未实现
//（无补录入口，评估与回归也未按 gold 过滤），故界面只陈述补录状态，不作门禁承诺。
async function toDataset(row) {
  if (!datasets.value.length) await loadDs()   // traj 页签下 datasets 可能还没加载
  let picked
  try {
    picked = await ElMessageBox.prompt(
      '目标数据集 ID。入库后该条目的金标准为空，需人工补录。',
      '转为评测任务', { inputValue: datasets.value[0]?.id || '' })
  } catch (e) { return }        // 只有这一段是「用户取消」
  if (!picked?.value) return
  try {
    const r = await api.fromTraces(picked.value, { trace_ids: [row.id], label: '轨迹导入' })
    ElMessage.success(`已加入 ${r.added} 条到待补录队列 · 新版本 ${r.version}`)
    loadDs()
  } catch (e) { ElMessage.error(e.message) }   // 接口失败必须让用户看见
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
