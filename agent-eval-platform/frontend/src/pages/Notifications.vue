<template>
  <div style="max-width:1000px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div>
        <h2 class="page-title">通知中心</h2>
        <p class="page-sub">{{ unreadList.length }} 条未读 · 异常任务告警 / 门禁结果 / 复核到期提醒 / 系统通知</p>
      </div>
      <el-button :disabled="!unreadList.length" @click="readAll">全部标记已读</el-button>
    </div>
    <el-tabs v-model="tab" @tab-change="load">
      <el-tab-pane label="全部" name="" />
      <el-tab-pane label="告警" name="告警" />
      <el-tab-pane label="门禁" name="门禁" />
      <el-tab-pane label="到期" name="到期" />
      <el-tab-pane label="系统" name="系统" />
    </el-tabs>
    <el-card>
      <div v-for="n in items" :key="n.id" style="display:flex;gap:12px;padding:12px 4px;border-bottom:1px solid #f1f5f9;align-items:flex-start;cursor:pointer" @click="open(n)">
        <div :style="{ background: typeMap[n.type]?.bg, color: typeMap[n.type]?.color }" class="badge" style="padding:6px 10px;flex:none">{{ n.type }}</div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:600">{{ n.title }} <span v-if="n.unread" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#2f6bff"></span></div>
          <div style="font-size:12.5px;color:#64748b;margin-top:3px">{{ n.body }}</div>
          <div style="font-size:11px;color:#cbd5e1;margin-top:4px">{{ n.time }}</div>
        </div>
        <el-button size="small" @click.stop="read(n)">{{ n.unread ? '标记已读' : '已读' }}</el-button>
      </div>
      <el-empty v-if="!items.length" description="暂无通知" />
    </el-card>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const items = ref([]), tab = ref('')
const typeMap = { 告警: { bg: '#fee2e2', color: '#dc2626' }, 门禁: { bg: '#d1fae5', color: '#059669' }, 到期: { bg: '#fef3c7', color: '#d97706' }, 系统: { bg: '#f1f5f9', color: '#64748b' } }
const unreadList = computed(() => items.value.filter(n => n.unread))
async function load() { try { items.value = await api.notifications({ type_: tab.value }) } catch (e) {} }
async function read(n) { try { await api.readNotif(n.id); load() } catch (e) {} }
async function readAll() { try { await api.readAllNotifs(); ElMessage.success('已全部标记已读'); load() } catch (e) {} }
function open(n) { read(n); if (n.link) location.hash = '#/' + n.link.replace(/^\//, '') }
onMounted(load)
</script>
