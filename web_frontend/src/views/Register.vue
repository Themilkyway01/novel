<template>
  <div class="register-page">
    <div class="register-card">
      <h2>用户注册</h2>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input 
            v-model="form.email" 
            placeholder="请输入邮箱（可选）" 
            autocomplete="off"
            spellcheck="false"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="password_confirm">
          <el-input v-model="form.password_confirm" type="password" placeholder="请再次输入密码" show-password />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleRegister" :loading="loading" style="width: 100%">
            注册
          </el-button>
        </el-form-item>
        
        <div class="links">
          <span>已有账号？</span>
          <el-link type="primary" @click="$router.push('/login')">立即登录</el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { register } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const fieldErrorsToShow = reactive({})

const form = reactive({
  username: '',
  email: '',
  password: '',
  password_confirm: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (fieldErrorsToShow.username) {
          callback(new Error(fieldErrorsToShow.username))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  email: [
    {
      validator: (rule, value, callback) => {
        if (value && value.trim() !== '') {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(value)) {
            callback(new Error('请输入有效的邮箱地址'))
          } else {
            callback()
          }
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleRegister = async () => {
  // 清除之前的字段错误
  Object.keys(fieldErrorsToShow).forEach(key => delete fieldErrorsToShow[key])
  formRef.value.clearValidate()

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const res = await register(form)
      userStore.setAuth(res.access, res.user)
      userStore.setHasSetPreference(false)
      userStore.setHasSeenRegistrationDialog(false)
      // 设置注册标记，用于首页弹窗
      sessionStorage.setItem('justRegistered', 'true')
      ElMessage.success('注册成功')
      router.push('/')
    } catch (error) {
      // 清除之前的字段错误
      Object.keys(fieldErrorsToShow).forEach(key => delete fieldErrorsToShow[key])
      formRef.value.clearValidate()

      // 处理后端验证错误，只在表单字段下方显示错误
      if (error.response && error.response.status === 400) {
        const errorData = error.response.data
        console.log('注册错误数据:', errorData)

        if (typeof errorData === 'object') {
          // 遍历所有错误键，提取字段错误
          const errorFields = []
          for (const [key, value] of Object.entries(errorData)) {
            const nonFieldKeys = ['detail', 'non_field_errors']
            if (nonFieldKeys.includes(key)) continue

            // 处理字段错误，用户名已存在时显示简洁提示
            let errorMessage = Array.isArray(value) ? value[0] : value
            if (key === 'username' && (errorMessage.includes('user') || errorMessage.includes('exists') || errorMessage.includes('存在'))) {
              errorMessage = '用户名已存在'
            }
            fieldErrorsToShow[key] = errorMessage
            errorFields.push(key)
          }
          console.log('处理的错误字段:', errorFields, fieldErrorsToShow)

          // 触发验证以显示字段错误
          if (errorFields.length > 0) {
            // 使用 nextTick 确保 fieldErrorsToShow 已经更新
            await nextTick()
            formRef.value.validateField(errorFields)
          }
        }
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  background: #fff;
  padding: 40px;
  border-radius: 10px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  width: 400px;
}

.register-card h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}

.links {
  text-align: center;
  margin-top: 10px;
}
</style>
