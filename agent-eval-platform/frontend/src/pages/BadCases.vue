<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div>
        <h2 class="page-title">Bad Case 管理</h2>
        <p class="page-sub">低分 Case 人工复核（确认 Bad / 误判 / 待定）→ 标注 Root Cause → 自动写入 Bad Case Dataset</p>
      </div>
      <div style="display:flex;gap:8px">
        <el-select v-model="filters.status" clearable placeholder="全部状态" style="width:130px" @change="load">
          <el-option label="待复核" value="pending" /><el-option label="已入库" value="confirmed" /><el-option label="已标记误判" value="misjudged" /><el-option label="待定" value="pending2" />
        </el-select>
        <el-button :disabled="!canWrite" @click="openBatch">批量复核</el-button>
      </div>
    </div>
    <el-row :gutter="12" style="margin-bottom:12px">
      <el-col :span="6" v-for="s in stats" :key="s[0]"><el-card><div style="font-size:11.5px;color:#94a3b8">{{ s[0] }}</div><b style="font-size:20px">{{ s[1] }}</b></el-card></el-col>
    </el-row>
    <el-table v-loading="loading" :data="items" style="width:100%" @row-click="openReview">
      <el-table-column prop="id" label="Case ID" width="110" />
      <el-table-column prop="trace_id" label="Trace" width="130"><template #default="{ row }"><span class="mono" style="color:#94a3b8">{{ row.trace_id }}</span></template></el-table-column>
      <el-table-column prop="app" label="应用" width="140" />
      <el-table-column prop="evaluator" label="评估器" width="150" />
      <el-table-column label="Score" width="110"><template #default="{ row }"><b :style="{ color: scoreColor(row.score) }">{{ row.score.toFixed(2) }}</b> <span style="color:#94a3b8;font-size:11px">/ {{ row.threshold }}</span></template></el-table-column>
      <el-table-column prop="time" label="触发时间" width="165" />
      <el-table-column label="复核状态" width="150">
        <template #default="{ row }">
          <el-tag size="small" :type="stMap[row.status]?.type">{{ stMap[row.status]?.label }}</el-tag>
          <div v-if="row.root_cause" style="font-size:11px;color:#94a3b8">{{ row.root_cause }}</div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button size="small" :type="row.status === 'pending' ? 'primary' : 'default'" plain @click.stop="openReview(row)">{{ row.status === 'pending' ? '复核' : '查看' }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawer" title="复核 Bad Case" size="900px">
      <template v-if="cur">
        <div style="font-size:12px;color:#94a3b8;margin-bottom:10px">{{ cur.trace_id }} · {{ cur.app }} · 阈值 {{ cur.threshold }} · 来自任务「{{ cur.task }}」</div>
        <el-row :gutter="12">
          <el-col :span="14">
            <div style="font-weight:700;margin-bottom:8px">轨迹回放（精简）</div>
            <div v-for="(turn, ti) in (cur.trace?.turns || [])" :key="ti" style="margin-bottom:10px">
              <div style="background:#eef4ff;border-radius:10px;padding:7px 11px;font-size:12.5px;color:#1e3a8a">{{ turn.message }}</div>
              <div v-for="st in turn.steps" :key="st.name" style="font-size:11.5px;color:#64748b;padding-left:12px;border-left:2px solid #e2e8f0;margin:4px 0 4px 12px">
                {{ st.name }} · <span class="mono">{{ (st.duration_ms / 1000).toFixed(1) }}s</span>
                <span v-if="st.error" style="color:#dc2626"> · {{ st.error }}</span>
              </div>
              <div style="background:#fff;border:1px solid #eef1f6;border-radius:10px;padding:7px 11px;font-size:12.5px;margin-top:4px">{{ outputOf(turn) }}</div>
            </div>
            <div style="background:#f8fafc;border-radius:8px;padding:10px;font-size:12px;color:#64748b;margin-top:8px">
              <b>评分明细：</b>{{ cur.evaluator }} → <b :style="{ color: scoreColor(cur.score) }">{{ cur.score.toFixed(2) }}</b>（归一化 [0,1]，版本 {{ cur.score_meta?.version }}）
              <div style="margin-top:4px;color:#475569">{{ cur.score_meta?.meta?.reason }}</div>
            </div>
          </el-col>
          <el-col :span="10">
            <div style="font-weight:700;margin-bottom:8px">复核结论（三选一）</div>
            <el-radio-group v-model="conclusion" style="display:flex;flex-direction:column;gap:8px;margin-bottom:12px">
              <el-radio value="confirm" border style="width:100%">确认 Bad（标注 Root Cause 后写入数据集）</el-radio>
              <el-radio value="misjudge" border style="width:100%">误判（答案正确，不计入回归集）</el-radio>
              <el-radio value="pending" border style="width:100%">待定（保留队列，可二次复核）</el-radio>
            </el-radio-group>
            <template v-if="conclusion === 'confirm'">
              <div style="font-weight:600;font-size:12.5px;margin-bottom:6px">Root Cause 标签（可多选）</div>
              <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px">
                <el-check-tag v-for="rc in rcGroups" :key="rc" :checked="rcSel.includes(rc)" style="margin:0" @change="toggleRc(rc)">{{ rc }}</el-check-tag>
              </div>
            </template>
            <el-alert v-if="conclusion === 'misjudge'" type="info" :closable="false"
                      :title="'将计入评估器误判率（' + cur.evaluator + '），反馈用于评估器优化'" style="margin-bottom:10px" />
            <el-input v-model="note" type="textarea" :rows="3" placeholder="补充说明（可选）" />
            <el-button type="primary" :disabled="!canWrite || conclusion === 'pending'" style="margin-top:14px;width:100%" @click="submit">提交复核</el-button>
          </el-col>
        </el-row>
      </template>
    </el-drawer>

    <el-dialog v-model="batchDlg" title="批量复核向导" width="560px">
      <el-table :data="batchList" size="small" max-height="260" @selection-change="s => batchSel = s">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="id" label="Case" width="90" />
        <el-table-column prop="evaluator" label="评估器" width="130" />
        <el-table-column label="Score" width="80"><template #default="{ row }"><b :style="{ color: scoreColor(row.score) }">{{ row.score.toFixed(2) }}</b></template></el-table-column>
      </el-table>
      <el-form label-position="top" style="margin-top:12px">
        <el-form-item label="统一结论">
          <el-select v-model="batchConcl" style="width:100%"><el-option label="确认 Bad（入库）" value="confirm" /><el-option label="误判" value="misjudge" /><el-option label="待定" value="pending" /></el-select>
        </el-form-item>
        <el-form-item v-if="batchConcl === 'confirm'" label="Root Cause（确认 Bad 时生效）">
          <el-select v-model="batchRc" style="width:100%"><el-option v-for="rc in rcGroups" :key="rc" :value="rc" :label="rc" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="batchDlg = false">取消</el-button><el-button type="primary" @click="submitBatch">批量提交</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { store } from '../store'

const items = ref([]), loading = ref(false), drawer = ref(false), batchDlg = ref(false)
const cur = ref(null), conclusion = ref('confirm'), note = ref(''), rcSel = ref([]), batchSel = ref([])
const batchList = ref([]), batchConcl = ref('confirm'), batchRc = ref('检索失败')
const filters = reactive({ status: '' })
const canWrite = computed(() => ['admin', 'dev'].includes(store.wsRole))
const stMap = { pending: { label: '待复核', type: 'danger' }, confirmed: { label: '已入库', type: 'success' }, misjudged: { label: '已标记误判', type: 'info' }, pending2: { label: '待定', type: 'warning' } }
const rcGroups = ['幻觉', '检索失败', '指令理解偏差', '逻辑错误', '工具参数错误', '格式不符', '安全合规', '成本超限']
const stats = computed(() => {
  const s = statsData.value || {}
  return [['待复核队列', s.pending ?? 0, '阈值自动筛入队'], ['今日已复核', (s.confirmed_7d ?? 0) + (s.misjudged_7d ?? 0), '确认 + 误判'], ['已入库', s.confirmed_7d ?? 0, '自动写入数据集'], ['已标记误判', s.misjudged_7d ?? 0, '计入评估器误判率']]
})
const statsData = ref(null)
function scoreColor(s) { if (s == null) return '#94a3b8'; return s >= 0.7 ? '#059669' : s >= 0.55 ? '#d97706' : '#dc2626' }
function outputOf(turn) { const st = turn.steps?.[turn.steps.length - 1]; return st ? (typeof st.output === 'string' ? st.output : JSON.stringify(st.output)) : '' }
function toggleRc(rc) { rcSel.value = rcSel.value.includes(rc) ? rcSel.value.filter(x => x !== rc) : [...rcSel.value, rc] }
async function load() {
  loading.value = true
  try { const r = await api.badcases(filters); items.value = r.items || []; statsData.value = r.stats }
  catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}
async function openReview(row) {
  try {
    cur.value = await api.badcase(row.id)
    conclusion.value = 'confirm'; note.value = ''; rcSel.value = []
    drawer.value = true
  } catch (e) { ElMessage.error(e.message) }
}
async function submit() {
  try {
    await api.review(cur.value.id, { conclusion, root_cause: rcSel.value.join(' · '), note: note.value })
    ElMessage.success(conclusion === 'confirm' ? '已确认 Bad 并写入数据集' : conclusion === 'misjudge' ? '已标记误判（计入误判率）' : '已标记待定')
    drawer.value = false; load()
  } catch (e) { ElMessage.error(e.message) }
}
async function openBatch() {
  try { const r = await api.badcases({ status: 'pending' }); batchList.value = r.items || []; batchDlg.value = true } catch (e) {}
}
async function submitBatch() {
  try {
    const r = await api.batchReview({ ids: batchSel.value.map(x => x.id), conclusion: batchConcl.value, root_cause: batchRc.value })
    ElMessage.success('已完成 ' + r.count + ' 条批量复核'); batchDlg.value = false; load()
  } catch (e) { ElMessage.error(e.message) }
}
onMounted(load)
</script>
