<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div>
        <h2 class="page-title">系统管理</h2>
        <p class="page-sub">工作空间数据隔离 · 三级角色 RBAC（管理员 / 开发 / 只读）· 关键操作审计留痕</p>
      </div>
      <el-button type="primary" :disabled="!canWrite" @click="inviteDlg = true">邀请成员</el-button>
    </div>
    <el-tabs v-model="tab">
      <el-tab-pane label="成员与权限" name="member">
        <el-row :gutter="12">
          <el-col :span="16">
            <el-table :data="members" size="small">
              <el-table-column label="成员" min-width="180">
                <template #default="{ row }"><b>{{ row.name }}</b><div style="font-size:11px;color:#cbd5e1">{{ row.email }}</div></template>
              </el-table-column>
              <el-table-column label="角色" width="120"><template #default="{ row }"><el-tag size="small" :type="roleMap[row.role]?.type">{{ roleMap[row.role]?.label }}</el-tag></template></el-table-column>
              <el-table-column label="说明"><template #default="{ row }">{{ roleMap[row.role]?.hint }}</template></el-table-column>
            </el-table>
          </el-col>
          <el-col :span="8">
            <el-card>
              <div style="font-weight:700;margin-bottom:8px">角色说明</div>
              <div v-for="(r, k) in roleMap" :key="k" style="font-size:12px;margin-bottom:8px">
                <el-tag size="small" :type="r.type" style="margin-right:6px">{{ r.label }}</el-tag>{{ r.hint }}
              </div>
              <el-alert type="info" :closable="false" title="成员按工作空间授权，跨空间数据不可见" />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
      <el-tab-pane label="工作空间" name="ws">
        <el-card>
          <div style="font-weight:700;margin-bottom:10px">工作空间（{{ store.wsId }}）</div>
          <el-table :data="store.workspaces" size="small">
            <el-table-column prop="name" label="空间名" width="160" />
            <el-table-column prop="env" label="环境" width="90"><template #default="{ row }"><el-tag size="small" :type="row.env === '生产' ? 'success' : 'primary'">{{ row.env }}</el-tag></template></el-table-column>
            <el-table-column prop="description" label="描述" />
            <el-table-column label="成员角色" width="120"><template #default="{ row }">{{ roleMap[row.role]?.label }}</template></el-table-column>
          </el-table>
          <div style="font-size:12px;color:#94a3b8;margin-top:8px">数据隔离：成员按工作空间授权；URL 直链他空间资源返回 403；热数据 30 天 / 冷数据归档 1 年</div>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="审计日志" name="audit">
        <el-table :data="audits" size="small" v-loading="auditLoading">
          <el-table-column prop="actor" label="操作人" width="100" />
          <el-table-column prop="action" label="操作" width="150" />
          <el-table-column prop="obj" label="对象" min-width="220" />
          <el-table-column label="结果" width="110"><template #default="{ row }"><el-tag size="small" :type="row.result.includes('成功') ? 'success' : 'danger'">{{ row.result }}</el-tag></template></el-table-column>
          <el-table-column prop="time" label="时间" width="170" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="inviteDlg" title="邀请成员" width="460px">
      <el-form label-position="top">
        <el-form-item label="邮箱"><el-input v-model="invite.email" placeholder="zhang@corp.com" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="invite.name" placeholder="张三" /></el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="invite.role"><el-radio value="dev">开发（推荐）</el-radio><el-radio value="ro">只读</el-radio><el-radio value="admin">管理员</el-radio></el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="inviteDlg = false">取消</el-button><el-button type="primary" @click="doInvite">发送邀请</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { store } from '../store'

const tab = ref('member'), members = ref([]), audits = ref([]), auditLoading = ref(false), inviteDlg = ref(false)
const invite = reactive({ email: '', name: '', role: 'dev' })
const canWrite = computed(() => ['admin', 'dev'].includes(store.wsRole))
const roleMap = { admin: { label: '管理员', type: 'danger', hint: '全部操作' }, dev: { label: '开发', type: 'primary', hint: '接入 / 评估 / 复核' }, ro: { label: '只读', type: 'info', hint: '仅查看' } }
async function load() {
  try { members.value = await api.members() } catch (e) {}
  auditLoading.value = true
  try { audits.value = await api.audits() } catch (e) {} finally { auditLoading.value = false }
}
async function doInvite() {
  try { await api.invite(invite); ElMessage.success('邀请已发送'); inviteDlg.value = false; load() } catch (e) { ElMessage.error(e.message) }
}
onMounted(load)
</script>
