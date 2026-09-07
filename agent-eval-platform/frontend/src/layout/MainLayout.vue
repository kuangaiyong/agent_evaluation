<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div style="height:54px;display:flex;align-items:center;gap:10px;padding:0 20px;border-bottom:1px solid #eef1f6">
        <div class="badge" style="background:#0f172a;color:#fff;font-size:15px;font-weight:800;padding:5px 10px">A</div>
        <div>
          <div style="font-weight:800;font-size:15px;line-height:1.1">TAgentEval</div>
          <div style="font-size:10.5px;color:#94a3b8">智能体评测平台 · 全自研</div>
        </div>
      </div>
      <nav>
        <template v-for="g in navGroups" :key="g.label">
          <div class="side-nav-label">{{ g.label }}</div>
          <router-link v-for="it in g.items" :key="it.path" :to="it.path" class="side-nav-item"
                       :class="{ active: isActive(it.path) }">
            <el-icon><component :is="it.icon" /></el-icon><span>{{ it.name }}</span>
          </router-link>
        </template>
      </nav>
      <div style="padding:12px 18px;border-top:1px solid #eef1f6;font-size:11.5px;color:#94a3b8">
        <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#22c55e;margin-right:6px"></span>
        上报链路正常 · v0.1.0
      </div>
    </aside>
    <div class="main-area">
      <header class="topbar">
        <el-dropdown @command="onSwitchWs">
          <span style="display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:600">
            {{ wsName }}
            <el-tag size="small" :type="wsEnv === '生产' ? 'success' : 'primary'">{{ wsEnv }}</el-tag>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="w in store.workspaces" :key="w.id" :command="w.id">
                {{ w.name }} · {{ w.env }}环境
              </el-dropdown-item>
              <el-dropdown-item divided disabled>创建工作空间（正式版）</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <div style="flex:1"></div>
        <el-badge :value="unread" :hidden="!unread" style="margin-right:14px">
          <el-icon style="cursor:pointer;font-size:18px" @click="$router.push('/notifications')"><Bell /></el-icon>
        </el-badge>
        <el-dropdown @command="onCmd">
          <span style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <el-avatar :size="26" style="background:#1f56e8">{{ (store.user?.name || '?')[0] }}</el-avatar>
            <span style="font-size:12.5px;font-weight:600">{{ store.user?.name }} · {{ roleLabel }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>{{ roleHint }}</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>
      <main class="content"><router-view /></main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { store, setWorkspace, logout } from '../store'
import { api } from '../api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const unread = ref(0)
const ROLE = { admin: '管理员', dev: '开发', ro: '只读' }
const roleLabel = computed(() => ROLE[store.wsRole] || store.user?.role || '')
const roleHint = computed(() => ({ admin: '全部操作权限', dev: '接入/评估/复核', ro: '仅查看，写操作置灰' }[store.wsRole] || ''))
const wsName = computed(() => store.workspaces.find(w => w.id === store.wsId)?.name || '工作空间')
const wsEnv = computed(() => store.workspaces.find(w => w.id === store.wsId)?.env || '生产')
const navGroups = [
  { label: '总览', items: [
    { path: '/dashboard', name: '仪表盘', icon: 'Odometer' },
    { path: '/notifications', name: '通知中心', icon: 'Bell' },
  ]},
  { label: '观测与审计', items: [
    { path: '/access', name: '接入中心', icon: 'Connection' },
    { path: '/traces', name: 'AI Agent 可观测', icon: 'DataLine' },
  ]},
  { label: '评估与实验', items: [
    { path: '/metrics', name: '指标库', icon: 'Grid' },
    { path: '/evaluators', name: '评估器', icon: 'Odometer' },
    { path: '/tasks', name: '评估任务', icon: 'List' },
    { path: '/badcases', name: 'Bad Case 管理', icon: 'Warning' },
  ]},
  { label: '数据中心', items: [
    // 单入口，页内以页签切换轨迹库与数据集（原为两个二级菜单指向同一路由的不同 query）
    { path: '/datacenter', name: '轨迹库 / 数据集', icon: 'Coin' },
  ]},
  { label: '持续优化', items: [
    { path: '/regression', name: '实验与回归', icon: 'Sort' },
  ]},
  { label: '系统管理', items: [
    { path: '/system', name: '成员与权限', icon: 'User' },
    // 原为系统管理页内的第三个页签，提为独立二级菜单
    { path: '/audit', name: '操作审计', icon: 'DocumentChecked' },
  ]},
]
function isActive(p) {
  // 统一按路由前缀匹配：列表页高亮自身，下钻页（如 /traces/:id）继续高亮所属列表。
  // 数据中心合并为单入口后，原先针对 ?tab= 的特判不再需要。
  return route.path === p || route.path.startsWith(p + '/')
}
onMounted(async () => {
  try {
    store.workspaces = await api.workspaces()
    if (!store.wsId && store.workspaces.length) setWorkspace(store.workspaces[0].id, store.workspaces[0].role)
    await loadUnread()
  } catch (e) { /* 忽略 */ }
})
async function onSwitchWs(id) {
  const w = store.workspaces.find(x => x.id === id)
  setWorkspace(id, w?.role)
  await loadUnread()
  ElMessage.success('已切换工作空间：' + (w?.name || '') + '（数据按空间隔离加载）')
  window.location.reload()
}
async function loadUnread() { try { const l = await api.notifications(); unread.value = l.filter(n => n.unread).length } catch (e) {} }
function onCmd(cmd) { if (cmd === 'logout') { logout(); location.href = '/login' } }
</script>
