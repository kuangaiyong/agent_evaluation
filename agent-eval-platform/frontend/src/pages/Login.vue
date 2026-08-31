<template>
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0f172a,#1e3a8a)">
    <el-card style="width:400px;border-radius:16px">
      <div style="text-align:center;margin-bottom:18px">
        <div class="badge" style="background:#0f172a;color:#fff;font-size:22px;font-weight:800;padding:8px 14px;border-radius:10px">A</div>
        <h2 style="margin:12px 0 2px;font-weight:800">AgentEval 智能体评测平台</h2>
        <div style="color:#94a3b8;font-size:12.5px">观测 → 评估 → 沉淀 → 回归 · 全自研 MVP</div>
      </div>
      <el-form :model="form" label-position="top" @keyup.enter="doLogin">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="lin@corp.com" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password size="large" placeholder="admin123" />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="doLogin">登 录</el-button>
      </el-form>
      <div style="margin-top:14px;font-size:12px;color:#94a3b8;line-height:1.8">
        演示账号：lin@corp.com / admin123（管理员）· chen@corp.com / dev123（开发）· sun@corp.com / ro123（只读）
      </div>
    </el-card>
  </div>
</template>
<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { setSession } from '../store'

const router = useRouter()
const form = reactive({ email: '', password: '' })
const loading = ref(false)
async function doLogin() {
  loading.value = true
  try {
    const r = await api.login(form)
    setSession(r)
    ElMessage.success('欢迎回来，' + r.user.name)
    router.push('/')
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}
</script>
