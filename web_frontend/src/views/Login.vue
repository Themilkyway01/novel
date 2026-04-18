<template>
  <div class="login-page">
    <div class="login-card">
      <h2>用户登录</h2>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
        
        <div class="links">
          <span>还没有账号？</span>
          <el-link type="primary" @click="$router.push('/register')">立即注册</el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { login } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const fieldErrors = reactive({})

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (fieldErrors.username) {
          callback(new Error(fieldErrors.username))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (fieldErrors.password) {
          callback(new Error(fieldErrors.password))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleLogin = async () => {
  // 清除之前的字段错误
  Object.keys(fieldErrors).forEach(key => delete fieldErrors[key])
  formRef.value.clearValidate()
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const res = await login(form.username, form.password)
      userStore.setAuth(res.access, res.user)
      // 从服务器加载用户偏好
      await userStore.loadUserPreferences()
      ElMessage.success('登录成功')
      router.push('/')
    } catch (error) {
      console.error('登录失败:', error)
      // 处理字段错误
      if (error.response && error.response.data) {
        const data = error.response.data
        // 后端可能返回 {username: '用户名不存在'} 或 {password: '密码错误'}
        Object.keys(fieldErrors).forEach(key => delete fieldErrors[key])
        formRef.value.clearValidate()
        
        if (data.username) {
          fieldErrors.username = data.username
          await nextTick()
          formRef.value.validateField(['username'])
        } else if (data.password) {
          fieldErrors.password = data.password
          await nextTick()
          formRef.value.validateField(['password'])
        } else if (data.error) {
          // 兼容旧的错误格式
          ElMessage.error(data.error)
        } else {
          ElMessage.error('登录失败，请稍后重试')
        }
      } else {
        ElMessage.error('网络错误，请检查网络连接')
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: #fff;
  padding: 40px;
  border-radius: 10px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  width: 400px;
}

.login-card h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}

.links {
  text-align: center;
  margin-top: 10px;
}
</style>
