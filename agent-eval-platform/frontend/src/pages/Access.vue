<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div>
        <h2 class="page-title">接入中心</h2>
        <p class="page-sub">统一走 LoongSuite 接入 · 按智能体形态选三条通道之一 · 全部以 OTLP 上报到网关</p>
      </div>
      <el-button type="primary" :disabled="!canWrite" @click="openCreate">创建 Agent 应用</el-button>
    </div>
    <el-table v-loading="loading" :data="apps" style="width:100%">
      <el-table-column label="应用" min-width="200">
        <template #default="{ row }">
          <b>{{ row.name }}</b>
          <div class="mono" style="font-size:11px;color:#cbd5e1">{{ row.id }}</div>
        </template>
      </el-table-column>
      <el-table-column label="智能体类型" width="120"><template #default="{ row }"><el-tag size="small" effect="plain">{{ row.type }}</el-tag></template></el-table-column>
      <el-table-column label="接入通道" width="150">
        <template #default="{ row }">
          <el-tag size="small" :type="pilotSupported(row.type) ? 'primary' : 'warning'" effect="plain">{{ row.channel }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="API Key" width="150"><template #default="{ row }"><span class="mono" style="font-size:12px">{{ row.api_key_masked || '—' }}</span></template></el-table-column>
      <el-table-column label="接入状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="stMap[row.status]?.type || 'info'">{{ stMap[row.status]?.label || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="model" label="模型" width="120" />
      <el-table-column prop="traces24h" label="累计 Trace" width="110"  sortable/>
      <el-table-column label="平均 Score" width="110" sortable>
        <template #default="{ row }"><b :style="{ color: scoreColor(row.avg_score) }">{{ row.avg_score?.toFixed(2) || '—' }}</b></template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openGuide(row)">接入引导</el-button>
          <el-button size="small" :disabled="!canWrite" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" :disabled="!canWrite" @click="verifyApp(row)">自检</el-button>
          <el-button size="small" :disabled="!canWrite" @click="rotateKey(row)">轮换 Key</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-row :gutter="12" style="margin-top:14px">
      <el-col :md="8" v-for="c in tips" :key="c.t"><el-card><b>{{ c.t }}</b><div style="font-size:12px;color:#64748b;margin-top:6px;line-height:1.7">{{ c.d }}</div></el-card></el-col>
    </el-row>


    <el-dialog v-model="editDlg" title="编辑 Agent 应用" width="520px">
      <el-form v-if="editRow" label-position="top">
        <el-form-item label="应用名称 *"><el-input v-model="editForm.name" /></el-form-item>
        <el-form-item label="智能体类型">
          <el-select v-model="editForm.type" style="width:100%">
            <el-option value="AgentScope" label="AgentScope" />
            <el-option value="OpenCode" label="OpenCode" />
            <el-option value="Hermes Agent" label="Hermes Agent" />
            <el-option value="CodeBuddy" label="CodeBuddy" />
            <el-option value="其他" label="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="接入通道">
          <el-select v-model="editForm.channel" clearable placeholder="留空则按智能体类型推导" style="width:100%">
            <el-option value="① Python Agent" label="① Python Agent（应用内插桩）" />
            <el-option value="② Pilot" label="② Pilot（本地 Coding CLI）" />
            <el-option value="③ OTLP 直推" label="③ OTLP 直推（兜底）" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认被测模型">
          <el-select v-model="editForm.model" style="width:100%">
            <el-option value="qwen-plus" label="qwen-plus" />
            <el-option value="qwen-max" label="qwen-max" />
            <el-option value="deepseek-v3" label="deepseek-v3" />
            <el-option value="deepseek-v4-flash" label="deepseek-v4-flash" />
            <el-option value="自定义（OpenAI 兼容）" label="自定义（OpenAI 兼容）" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号（用于回归分组）">
          <el-input v-model="editForm.version" placeholder="如 v1.0.0" />
        </el-form-item>
        <el-alert type="info" :closable="false" title="模型为标识字段：智能体上报自带 model 时以上报为准；版本号建议与 AGENTEVAL_VERSION 保持一致" />
      </el-form>
      <template #footer><el-button @click="editDlg = false">取消</el-button><el-button type="primary" :loading="editSaving" @click="saveEdit">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="dlg" title="创建 Agent 应用" width="520px">
      <el-form label-position="top">
        <el-form-item label="应用名称 *"><el-input v-model="form.name" placeholder="例如：电商客服助手" /></el-form-item>
        <el-form-item label="智能体类型 *">
          <el-select v-model="form.type" style="width:100%">
            <el-option value="AgentScope" label="AgentScope（走通道 ① Python Agent）" />
            <el-option value="OpenCode" label="OpenCode（走通道 ② Pilot）" />
            <el-option value="Hermes Agent" label="Hermes Agent（走通道 ② Pilot）" />
            <el-option value="CodeBuddy" label="CodeBuddy（走通道 ③ OTLP 直推）" />
            <el-option value="其他" label="其他（走通道 ③ OTLP 直推）" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认被测模型">
          <el-select v-model="form.model" style="width:100%"><el-option value="qwen-plus" label="qwen-plus" /><el-option value="qwen-max" label="qwen-max" /><el-option value="deepseek-v3" label="deepseek-v3" /></el-select>
        </el-form-item>
        <el-alert type="info" :closable="false">API Key 仅创建时完整展示一次，后续仅展示掩码</el-alert>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="create">创建并生成 API Key</el-button>
      </template>
    </el-dialog>


    <el-dialog v-model="guideDlg" title="接入引导" width="760px">
      <template v-if="guideApp">
        <el-alert type="info" :closable="false" style="margin-bottom:12px"
                  :title="guideApp.type + ' · 建议走「' + guideApp.channel + '」 · API Key 已就绪，业务代码零改动'" />
        <el-alert v-if="!pilotSupported(guideApp.type)" type="warning" :closable="false" style="margin-bottom:12px"
                  title="该工具不在 LoongSuite Pilot 的官方支持清单内，请走通道 ③">
          <template #default>
            <div style="font-size:12.5px;line-height:1.8">
              Pilot 清单里的是 <b>WorkBuddy</b>（腾讯 AI 办公工作站），<b>不是 CodeBuddy</b>（AI 代码编辑器）——
              两者同源但不是一个产品，不能当成已支持。CodeBuddy Code 自身支持按 OTel 规范推 trace 到自有
              Collector，走通道 ③ 是干净的，但要按它自己的环境变量文档配，不是按 Pilot 的。
            </div>
          </template>
        </el-alert>
        <el-tabs v-model="guideTab">
          <el-tab-pane label="通道 ① Python Agent" name="py">
            <div style="font-size:12.5px;color:#64748b;margin-bottom:8px">适用：AgentScope 等 Python 智能体应用 · 包裹原启动命令，业务代码零改动</div>
            <div class="mono" style="background:#0f172a;color:#e2e8f0;border-radius:8px;padding:14px;font-size:12px;line-height:1.9;overflow-x:auto">
<pre style="margin:0;white-space:pre"># 1) 安装发行版与插桩插件
pip install "loongsuite-distro[otlp]"
loongsuite-bootstrap -a install --latest --auto-detect

# 2) 指向本平台的 OTLP 网关
export OTEL_SERVICE_NAME={{ guideApp.name }}
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8088
export OTEL_EXPORTER_OTLP_HEADERS="x-api-key:{{ guideApp.api_key_masked }}"

# 3) 包裹原启动命令，业务代码一行不改
loongsuite-instrument python main.py</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="通道 ② Pilot" name="pilot">
            <div style="font-size:12.5px;color:#64748b;margin-bottom:8px">适用：OpenCode、Hermes Agent 等本地 Coding CLI · 装在开发机上，自动注入插件</div>
            <div class="mono" style="background:#0f172a;color:#e2e8f0;border-radius:8px;padding:14px;font-size:12px;line-height:1.9;overflow-x:auto">
<pre style="margin:0;white-space:pre"># 1) 每台开发机装一次
curl -fsSL https://loongcollector-community-edition.oss-cn-shanghai.aliyuncs.com/loongsuite-pilot/installer.sh \
  -o /tmp/loongsuite-pilot-installer.sh &amp;&amp; bash /tmp/loongsuite-pilot-installer.sh install

# 2) 配 OTLP Trace 导出（~/.loongsuite-pilot/config.json 或环境变量）
#    Pilot 自动发现本机已装的 agent 并注入对应插件：
#      OpenCode      → plugin injection
#      Hermes Agent  → native directory plugin

# 3) 校验接入与用量
loongsuite-pilot status
loongsuite-pilot token-usage</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="通道 ③ OTLP 直推" name="otlp">
            <div style="font-size:12.5px;color:#64748b;margin-bottom:8px">适用：CodeBuddy 及未被 Pilot 覆盖的工具 · 兜底通道，任何支持 OTel 的工具都能走</div>
            <div class="mono" style="background:#0f172a;color:#e2e8f0;border-radius:8px;padding:14px;font-size:12px;line-height:1.9;overflow-x:auto">
<pre style="margin:0;white-space:pre"># A) 工具自身支持 OTLP：按它自己的环境变量文档指向本平台
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8088
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_HEADERS="x-api-key:{{ guideApp.api_key_masked }}"

# B) 直接打自研网关，带 App Key，不必部署 Collector
curl -X POST http://localhost:8088/api/otlp/v1/traces \
  -H "x-api-key: {{ guideApp.api_key_masked }}" \
  -H "content-type: application/json" \
  --data-binary @spans.json</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
        <div style="display:flex;justify-content:space-between;margin-top:14px">
          <el-button :loading="verifying" @click="doVerify(guideApp)">验证上报</el-button>
          <span style="font-size:12px;color:#94a3b8">验证通过后，接入状态将从「未接入 → 上报中 → 已接入」</span>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="keyDlg" title="API Key（仅展示一次）" width="480px">
      <el-input v-model="fullKey" readonly class="mono" />
      <div style="font-size:12px;color:#94a3b8;margin-top:8px">上报端点：http://<平台>/api/ingest/trace · 鉴权头 x-api-key</div>
    </el-dialog>
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { store, canWrite } from '../store'

const apps = ref([]), loading = ref(false), dlg = ref(false), keyDlg = ref(false), fullKey = ref('')
const form = reactive({ name: '', type: 'AgentScope', model: 'qwen-plus' })
const guideDlg = ref(false), guideTab = ref('py'), guideApp = ref(null), verifying = ref(false)
const editDlg = ref(false), editRow = ref(null), editSaving = ref(false), editForm = ref({ name: '', type: 'AgentScope', channel: '', model: 'qwen-plus', version: '' })
const stMap = { none: { label: '未接入', type: 'info' }, reporting: { label: '上报中', type: 'primary' }, connected: { label: '已接入', type: 'success' }, interrupted: { label: '数据中断', type: 'danger' } }
const tips = [
  { t: '零侵入接入', d: 'AgentScope 只需 3–5 行启动配置；OpenCode 仅改配置文件，不修改被测智能体业务代码' },
  { t: '自动脱敏', d: '上报链路 TLS 加密，Trace 中 PII 服务端自动脱敏，API Key 仅创建时完整展示一次' },
  { t: '接入三态检测', d: '未接入 → 上报中 → 已接入；数据延迟时展示中间态而非假未接入，24h 无数据给中断告警' },
]
function scoreColor(s) { if (s == null) return '#94a3b8'; return s >= 0.7 ? '#059669' : s >= 0.55 ? '#d97706' : '#dc2626' }
async function load() { loading.value = true; try { apps.value = await api.apps() } catch (e) { ElMessage.error(e.message) } finally { loading.value = false } }
async function create() {
  if (!form.name) return ElMessage.warning('请输入应用名称')
  try {
    const r = await api.createApp(form)
    fullKey.value = r.api_key_full; dlg.value = false; keyDlg.value = true
    await load(); onKeyStored(r)
  } catch (e) { ElMessage.error(e.message) }
}
async function onKeyStored() { await load() }
async function verifyApp(row) { try { await api.verifyApp(row.id); ElMessage.success(row.name + ' 自检通过：上报链路与数据清洗正常'); load() } catch (e) { ElMessage.error(e.message) } }
async function rotateKey(row) {
  try { await ElMessageBox.confirm('轮换后旧 Key 立即失效，确认轮换？', '轮换 ' + row.name, { type: 'warning' })
    const r = await api.rotateKey(row.id); fullKey.value = r.api_key_full; keyDlg.value = true
  } catch (e) { /* 用户取消 */ }
}
function openCreate() { form.name = ''; dlg.value = true }
function openEdit(row) {
  editRow.value = row
  editForm.value = { name: row.name, type: row.type, channel: row.channel || '', model: row.model, version: row.version || '' }
  editDlg.value = true
}
async function saveEdit() {
  editSaving.value = true
  try {
    await api.updateApp(editRow.value.id, editForm.value)
    ElMessage.success('应用配置已更新'); editDlg.value = false; load()
  } catch (e) { ElMessage.error(e.message) } finally { editSaving.value = false }
}
// Pilot 官方支持清单里的是 WorkBuddy（腾讯 AI 办公工作站），不是 CodeBuddy（AI 代码编辑器）——
// 同源但不是一个产品，不能当成已支持。未在清单内的一律指引走通道 ③。
const PILOT_SUPPORTED = ['OpenCode', 'Hermes Agent']
function pilotSupported(type) { return type === 'AgentScope' || PILOT_SUPPORTED.includes(type) }
// 以 channel 为准：它允许被显式覆盖，按 type 推会和弹窗顶部给的建议自相矛盾
function tabOfChannel(ch) {
  if (!ch) return 'otlp'
  if (ch.includes('Python Agent')) return 'py'
  if (ch.includes('Pilot')) return 'pilot'
  return 'otlp'
}
function openGuide(row) { guideApp.value = row; guideTab.value = tabOfChannel(row.channel); guideDlg.value = true }
async function doVerify(row) {
  verifying.value = true
  try { await api.verifyApp(row.id); ElMessage.success(row.name + ' 自检通过：上报链路与数据清洗正常，状态已更新'); load() } catch (e) { ElMessage.error(e.message) } finally { verifying.value = false }
}
onMounted(load)
</script>
