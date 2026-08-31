<template>
  <div v-loading="loading">
    <template v-if="t">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
        <div>
          <div style="display:flex;gap:8px;align-items:center">
            <h2 class="page-title mono">{{ t.id }}</h2>
            <el-tag :type="t.status === 'ok' ? 'success' : 'danger'">{{ t.status === 'ok' ? '成功' : '失败' }}</el-tag>
            <el-tag v-if="t.score_avg != null && t.score_avg < 0.6" type="danger">低分 · 已入 Bad Case 队列</el-tag>
          </div>
          <p class="page-sub">{{ t.app }} · {{ t.model }} · {{ t.version }} · 开始于 {{ t.created_at }}</p>
        </div>
        <el-button @click="$router.back()">返回列表</el-button>
      </div>
      <el-row :gutter="10" style="margin-bottom:14px">
        <el-col :span="4" v-for="m in metas" :key="m[0]"><el-card><div style="font-size:11px;color:#94a3b8">{{ m[0] }}</div><b style="font-size:16px">{{ m[1] }}</b></el-card></el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :md="16">
          <el-card>
            <el-tabs v-model="tab">
              <el-tab-pane label="轨迹树" name="tree">
                <div v-for="(turn, ti) in t.payload.turns" :key="ti" style="margin-bottom:14px">
                  <div style="font-size:12px;color:#64748b;margin-bottom:6px">
                    <b>T{{ ti + 1 }}</b> · 用户消息
                  </div>
                  <div style="background:#eef4ff;border-radius:10px 10px 3px 10px;padding:8px 12px;font-size:13px;color:#1e3a8a;display:inline-block;margin-bottom:8px">{{ turn.message }}</div>
                  <el-timeline style="padding-left:10px">
                    <el-timeline-item v-for="st in turn.steps" :key="st.name" :type="st.status === 'ok' ? 'success' : 'danger'"
                                      :timestamp="(st.duration_ms / 1000).toFixed(1) + 's'" style="cursor:pointer" @click="selStep = st">
                      <div style="font-weight:600;font-size:13px">{{ st.name }} <el-tag size="small" effect="plain" style="margin-left:6px">{{ st.kind }}</el-tag>
                        <span v-if="st.tokens" style="color:#94a3b8;font-size:11px;margin-left:6px">{{ st.tokens }} tok</span></div>
                      <div v-if="st.error" style="color:#dc2626;font-size:11.5px;margin-top:2px" class="mono">{{ st.error }}</div>
                    </el-timeline-item>
                  </el-timeline>
                </div>
              </el-tab-pane>
              <el-tab-pane label="Session 回放" name="replay">
                <div v-for="(turn, ti) in t.payload.turns" :key="ti" style="margin-bottom:14px">
                  <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">Turn {{ ti + 1 }}</div>
                  <div style="background:#eef4ff;border-radius:10px 10px 3px 10px;padding:8px 12px;color:#1e3a8a;display:inline-block;max-width:85%">{{ turn.message }}</div>
                  <div style="margin-top:6px;background:#fff;border:1px solid #eef1f6;border-radius:10px 10px 10px 3px;padding:8px 12px;display:inline-block;max-width:88%">
                    {{ lastOutput(turn) }}
                  </div>
                </div>
              </el-tab-pane>
              <el-tab-pane label="评估结果" name="eval">
                <el-table :data="t.scores || []" size="small">
                  <el-table-column prop="evaluator_id" label="评估器" width="140" />
                  <el-table-column label="Score" width="120">
                    <template #default="{ row }"><b :style="{ color: scoreColor(row.score) }">{{ row.score?.toFixed(2) || '—' }}</b></template>
                  </el-table-column>
                  <el-table-column prop="version" label="版本" width="90" />
                  <el-table-column label="判定依据"><template #default="{ row }" class="mono">{{ row.meta?.reason }}</template></el-table-column>
                  <el-table-column label="失败" width="70"><template #default="{ row }"><el-tag v-if="row.failed" size="small" type="danger">失败</el-tag></template></el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </el-col>
        <el-col :md="8">
          <el-card>
            <div style="font-weight:700;margin-bottom:10px">Span 详情</div>
            <template v-if="selStep">
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="类型">{{ selStep.kind }}<el-tag size="small" v-if="selStep.tool" style="margin-left:6px">{{ selStep.tool }}</el-tag></el-descriptions-item>
                <el-descriptions-item label="状态"><el-tag size="small" :type="selStep.status === 'ok' ? 'success' : 'danger'">{{ selStep.status }}</el-tag></el-descriptions-item>
                <el-descriptions-item label="耗时">{{ selStep.duration_ms }}ms</el-descriptions-item>
                <el-descriptions-item label="Token">{{ selStep.tokens || 0 }}</el-descriptions-item>
              </el-descriptions>
              <div style="font-size:12px;font-weight:600;color:#64748b;margin:12px 0 4px">入参</div>
              <pre class="mono" style="background:#0f172a;color:#e2e8f0;border-radius:8px;padding:10px;font-size:11.5px;overflow-x:auto">{{ pretty(selStep.input) }}</pre>
              <div style="font-size:12px;font-weight:600;color:#64748b;margin:12px 0 4px">出参</div>
              <pre class="mono" style="background:#0f172a;color:#e2e8f0;border-radius:8px;padding:10px;font-size:11.5px;overflow-x:auto">{{ pretty(selStep.output) }}</pre>
            </template>
            <el-empty v-else description="点击左侧轨迹树节点查看入参/出参" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const t = ref(null), loading = ref(false), tab = ref('tree'), selStep = ref(null)
const metas = computed(() => [
  ['端到端耗时', (t.value.duration_ms / 1000).toFixed(1) + 's'],
  ['总 Token', t.value.tokens || 0],
  ['评估 Cost', '¥' + (t.value.cost || 0).toFixed(4)],
  ['整体 Score', t.value.score_avg?.toFixed(2) || '—'],
  ['Turns / Steps', t.value.turns + ' / ' + t.value.steps],
  ['模型', t.value.model],
])
function pretty(v) { return typeof v === 'string' ? v : JSON.stringify(v ?? {}, null, 2) }
function scoreColor(s) { if (s == null) return '#94a3b8'; return s >= 0.7 ? '#059669' : s >= 0.55 ? '#d97706' : '#dc2626' }
function lastOutput(turn) {
  const steps = turn.steps || []
  return steps.length ? (typeof steps[steps.length - 1].output === 'string' ? steps[steps.length - 1].output : JSON.stringify(steps[steps.length - 1].output)) : ''
}
onMounted(async () => {
  loading.value = true
  try {
    const d = await api.trace(route.params.id)
    t.value = d
    selStep.value = d.payload.turns?.[0]?.steps?.[0] || null
  } catch (e) {} finally { loading.value = false }
})
</script>
