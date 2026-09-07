<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div>
        <h2 class="page-title">评估器</h2>
        <p class="page-sub">规则指标 / LLM-as-Judge / Agent-as-Judge / 人工反馈 · 统一输出 Score ∈ [0,1] 并带版本号</p>
      </div>
      <el-button type="primary" :disabled="!canWrite" @click="openCreate">创建评估器</el-button>
    </div>
    <el-table v-loading="loading" :data="items" style="width:100%" @row-click="openDetail">
      <el-table-column label="评估器" min-width="200">
        <template #default="{ row }">
          <b>{{ row.name }}</b>
          <div class="mono" style="font-size:11px;color:#cbd5e1">{{ row.id }} · {{ row.version }}</div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="150">
        <template #default="{ row }"><el-tag size="small" :type="typeMap[row.type]" effect="plain" style="margin-right:4px">{{ row.type_label }}</el-tag>
          <el-tag v-if="row.preset" size="small" effect="plain" type="info">预置</el-tag></template>
      </el-table-column>
      <el-table-column prop="config" label="说明" min-width="260">
        <template #default="{ row }">{{ configDesc(row) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }"><el-tag size="small" :type="row.status === 'published' ? 'success' : 'info'">{{ row.status === 'published' ? '已发布' : '草稿' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="质量" width="150">
        <template #default="{ row }"><el-tag v-if="row.bias_rate > 20" size="small" type="danger">误判率 {{ row.bias_rate }}% · 待优化</el-tag>
          <span v-else style="font-size:12px;color:#94a3b8">误判率 {{ row.bias_rate }}%</span></template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click.stop="openTrial(row)">试运行</el-button>
          <el-button size="small" @click.stop="openDetail(row)">详情</el-button>
          <el-button size="small" :disabled="!canWrite || row.status === 'published'" @click.stop="publish(row)">发布</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dlg" title="创建评估器" width="620px">
      <el-form label-position="top">
        <el-form-item label="评估器名称 *"><el-input v-model="form.name" placeholder="例如：电商问答正确性" /></el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.type">
            <el-radio-button value="rule">规则指标</el-radio-button>
            <el-radio-button value="llm">LLM-as-Judge</el-radio-button>
            <el-radio-button value="agent">Agent-as-Judge</el-radio-button>
            <el-radio-button value="human">人工反馈</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="form.type === 'rule'">
          <el-form-item label="规则配置">
            <el-checkbox v-model="cfg.tool_success">工具调用成功率</el-checkbox>
            <el-checkbox v-model="cfg.no_error" style="margin-left:12px">错误步骤惩罚</el-checkbox>
            <div style="display:flex;gap:8px;margin-top:8px">
              <el-input v-model="cfg.keywords_text" placeholder="关键词，逗号分隔" style="width:48%" />
              <el-input v-model="cfg.regex" placeholder="正则（可选）" style="width:48%" />
            </div>
          </el-form-item>
        </template>
        <template v-else-if="form.type === 'llm' || form.type === 'agent'">
          <el-form-item label="裁判模型"><el-select v-model="cfg.judge_model" style="width:100%"><el-option value="qwen-max" /><el-option value="deepseek-v3" /><el-option value="qwen-plus" /></el-select></el-form-item>
          <el-form-item label="Prompt 模板"><el-input v-model="cfg.prompt" type="textarea" :rows="5"
            placeholder="输出 JSON {&quot;score&quot;: &lt;0-1&gt;, &quot;reason&quot;: &quot;...&quot;}" /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="标注维度"><el-input v-model="cfg.dims_text" placeholder="质量 / 合规 / 满意度" /></el-form-item>
        </template>
        <el-alert type="info" :closable="false">评分协议：输出必须归一化到 [0,1]，越界将被拒绝并记为评估失败；Score 绑定评估器版本号存储</el-alert>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button @click="save('draft')">保存草稿</el-button>
        <el-button type="primary" @click="save('published')">保存并发布</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="drawer" title="评估器试运行" size="760px">
      <div v-if="sel">
        <el-descriptions :column="2" border size="small" style="margin-bottom:14px">
          <el-descriptions-item label="类型">{{ sel.type_label }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ sel.version }}</el-descriptions-item>
          <el-descriptions-item label="裁判模型" :span="2">{{ sel.config?.judge_model || '—' }}</el-descriptions-item>
        </el-descriptions>
        <div style="display:flex;gap:8px;margin-bottom:12px">
          <el-select v-model="trialTrace" style="flex:1">
            <el-option v-for="t in traces" :key="t.id" :value="t.id" :label="t.id + ' · ' + t.app" />
          </el-select>
          <el-button type="primary" :loading="trialing" @click="runTrial">运行试评分</el-button>
        </div>
        <div v-if="trialResult" style="background:#f8fafc;border:1px solid #eef1f6;border-radius:10px;padding:14px">
          <div style="font-size:34px;font-weight:800" :style="{ color: scoreColor(trialResult.score) }">{{ trialResult.score != null ? trialResult.score.toFixed(2) : '—' }}</div>
          <div style="font-size:12.5px;color:#64748b;margin-top:6px">{{ trialResult.reason }}</div>
          <el-tag v-if="trialResult.failed" type="danger" size="small" style="margin-top:8px">评估失败（越界/异常）</el-tag>
        </div>
      </div>
    </el-drawer>
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { store, canWrite } from '../store'

const items = ref([]), traces = ref([]), loading = ref(false), dlg = ref(false), drawer = ref(false)
const sel = ref(null), trialTrace = ref(''), trialResult = ref(null), trialing = ref(false)
const form = reactive({ name: '', type: 'rule' })
const cfg = reactive({ tool_success: true, no_error: false, keywords_text: '', regex: '', judge_model: 'qwen-max', prompt: '', dims_text: '' })
const typeMap = { rule: 'info', llm: 'primary', agent: 'warning', human: 'success' }
function scoreColor(s) { if (s == null) return '#94a3b8'; return s >= 0.7 ? '#059669' : s >= 0.55 ? '#d97706' : '#dc2626' }
function configDesc(row) {
  const c = row.config || {}
  if (row.type === 'rule') return (c.tool_success ? '工具成功率 + ' : '') + (c.no_error ? '错误惩罚 + ' : '') + (c.keywords?.length ? '关键词 ' + c.keywords.join('/') : '')
  return (c.dims || []).join(' / ') || '确定性计算与模型判断'
}
async function load() { loading.value = true; try { items.value = await api.evaluators() } catch (e) { ElMessage.error(e.message) } finally { loading.value = false } }
async function openCreate() { form.name = ''; Object.keys(cfg).forEach(k => cfg[k] = k === 'tool_success' ? true : ''); dlg.value = true }
async function save(status) {
  if (!form.name) return ElMessage.warning('请输入名称')
  const config = { ...cfg }
  delete config.keywords_text
  if (cfg.keywords_text) config.keywords = cfg.keywords_text.split(/[,，]/).map(s => s.trim()).filter(Boolean)
  if (cfg.dims_text) config.dims = cfg.dims_text.split(/[,，/]/).map(s => s.trim()).filter(Boolean)
  try { await api.createEvaluator({ name: form.name, type: form.type, config, status }); ElMessage.success('已保存'); dlg.value = false; load() }
  catch (e) { ElMessage.error(e.message) }
}
async function openDetail(row) {
  sel.value = row
  if (!traces.value.length) { try { traces.value = (await api.traces({ size: 20 })).items } catch (e) {} }
  trialTrace.value = traces.value[0]?.id || ''
  trialResult.value = null
  drawer.value = true
}
async function openTrial(row) { openDetail(row) }
async function runTrial() {
  trialing.value = true
  try { const r = await api.trial(sel.value.id, { trace_ids: [trialTrace.value] }); trialResult.value = r.results[0] } catch (e) { ElMessage.error(e.message) }
  finally { trialing.value = false }
}
async function publish(row) { try { await api.publishEvaluator(row.id); ElMessage.success('已发布 ' + row.name + '（版本自增）'); load() } catch (e) { ElMessage.error(e.message) } }
onMounted(load)
</script>
