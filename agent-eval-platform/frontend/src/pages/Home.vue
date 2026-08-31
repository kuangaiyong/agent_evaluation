<template>
  <div>
    <el-card style="margin-bottom:16px;background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;border:none!important">
      <div style="text-align:center;padding:26px 0">
        <el-tag effect="dark" style="margin-bottom:14px">AGENTEVAL · CONTINUOUS TUNING LOOP</el-tag>
        <h1 style="font-size:30px;font-weight:800;margin:0 0 10px">在 AgentEval 洞察你的 <span style="color:#67e8f9">Agent 运行状态</span></h1>
        <p style="color:#cbd5e1;margin:0 0 18px">
          当前工作空间 <b>{{ wsName }}</b>{{ hasTraces ? '：接入应用 ' + kpi.apps + ' 个，累计轨迹 ' + tracesTotal + ' 条' : '尚未检测到 Agent 应用接入，请先前往接入中心完成接入' }}
        </p>
        <el-button type="primary" size="large" @click="$router.push('/access')">前往接入</el-button>
        <el-button size="large" type="primary" plain style="margin-left:12px" @click="$router.push('/traces')">查看可观测</el-button>
      </div>
    </el-card>
    <el-row :gutter="16">
      <el-col :span="8" v-for="c in cards" :key="c.title">
        <el-card style="margin-bottom:16px">
          <div style="font-weight:700">{{ c.title }}</div>
          <div style="font-size:12px;color:#64748b;margin:8px 0;line-height:1.7">{{ c.desc }}</div>
          <el-button size="small" type="primary" plain @click="$router.push(c.path)">进入 →</el-button>
        </el-card>
      </el-col>
    </el-row>
    <el-alert type="success" :closable="false" style="margin-bottom:8px">
      闭环：观测（可观测）→ 评估（评估器/任务）→ 复核（Bad Case）→ 沉淀（数据集）→ 回归与门禁（实验与回归）
    </el-alert>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { store } from '../store'

const kpi = ref({}), tracesTotal = ref(0)
const hasTraces = computed(() => (kpi.value.tasks ?? 0) > 0 || tracesTotal.value > 0)
const wsName = computed(() => store.workspaces.find(w => w.id === store.wsId)?.name || '当前工作空间')
const cards = [
  { title: '接入中心', desc: '管理 Agent 应用接入 · AgentScope / OpenCode / HTTP API 直推，统一 OTLP 网关上报', path: '/access' },
  { title: 'AI Agent 可观测', desc: 'Trace / Session / Tool Call 全链路查询，轨迹树回放 Turn → Step 完整过程', path: '/traces' },
  { title: '评估器与任务', desc: '规则指标 / LLM-as-Judge / Agent-as-Judge，在线持续评估 + 离线批次评估', path: '/evaluators' },
]
onMounted(async () => {
  try {
    const [d, t] = await Promise.all([api.dashboard({ range: '7d' }), api.traces({ size: 1 })])
    kpi.value = d.kpi || {}; tracesTotal.value = t.total || 0
  } catch (e) {}
})
</script>
