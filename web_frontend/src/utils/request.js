import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '',
  timeout: 60000  // 增加到 60 秒，防止相似推荐等耗时操作超时
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const { status, data } = error.response

      // 400 错误不自动显示提示，由调用方处理错误显示
      if (status === 400) {
        return Promise.reject(error)
      }

      if (status === 401) {
        // 跳过登录接口的 401 错误，由登录页面自行处理
        if (error.response.config.url.includes('/api/auth/login/')) {
          return Promise.reject(error)
        }
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      } else if (status === 403) {
        ElMessage.error('无权访问')
      } else if (status === 404) {
        ElMessage.error('请求的资源不存在')
      } else if (status === 500) {
        ElMessage.error('服务器错误')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default request
