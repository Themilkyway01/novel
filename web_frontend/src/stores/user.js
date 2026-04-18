import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // 用户选择的频道和分类
  const selectedChannel = ref(localStorage.getItem('selectedChannel') || '')
  const selectedCategories = ref(JSON.parse(localStorage.getItem('selectedCategories') || '[]'))
  const selectedSubCategories = ref(JSON.parse(localStorage.getItem('selectedSubCategories') || '{}'))

  // 是否已设置推荐偏好
  const hasSetPreference = ref(JSON.parse(localStorage.getItem('hasSetPreference') || 'false'))
  
  // 是否已看过注册后对话框（控制注册后只弹出一次）
  // 如果用户已登录且没有记录，默认设为 true（老用户）并保存
  const getInitialHasSeenRegistrationDialog = () => {
    const stored = localStorage.getItem('hasSeenRegistrationDialog')
    if (stored !== null) {
      return JSON.parse(stored)
    }
    // 如果没有存储记录但用户已登录，认为是老用户，默认设为 true
    const isLoggedIn = token.value !== ''
    if (isLoggedIn) {
      // 自动保存，避免下次再检查
      localStorage.setItem('hasSeenRegistrationDialog', JSON.stringify(true))
    }
    return isLoggedIn
  }
  const hasSeenRegistrationDialog = ref(getInitialHasSeenRegistrationDialog())

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(newToken, newUser) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(newUser))

    // 设置 axios 默认请求头
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  // 从服务器加载用户偏好
  async function loadUserPreferences() {
    if (!user.value || !user.value.id) return

    try {
      const res = await axios.get('/api/auth/profile/')
      const userData = res.data

      // 从服务器加载偏好设置
      if (userData.selected_channel !== undefined) {
        selectedChannel.value = userData.selected_channel || ''
        localStorage.setItem('selectedChannel', userData.selected_channel || '')
      }
      if (userData.selected_categories) {
        selectedCategories.value = userData.selected_categories || []
        localStorage.setItem('selectedCategories', JSON.stringify(userData.selected_categories || []))
      }
      if (userData.selected_sub_categories) {
        selectedSubCategories.value = userData.selected_sub_categories || {}
        localStorage.setItem('selectedSubCategories', JSON.stringify(userData.selected_sub_categories || {}))
      }
      if (userData.has_set_preference !== undefined) {
        hasSetPreference.value = userData.has_set_preference
        localStorage.setItem('hasSetPreference', JSON.stringify(userData.has_set_preference))
      }

      console.log('从服务器加载用户偏好:', {
        channel: selectedChannel.value,
        categories: selectedCategories.value,
        subCategories: selectedSubCategories.value,
        hasSetPreference: hasSetPreference.value
      })
    } catch (error) {
      console.error('加载用户偏好失败:', error)
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    hasSetPreference.value = false
    hasSeenRegistrationDialog.value = false
    // 清除认证信息
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    // 清除偏好设置，确保新用户看到的是全部选项
    localStorage.removeItem('selectedChannel')
    localStorage.removeItem('selectedCategories')
    localStorage.removeItem('selectedSubCategories')
    localStorage.removeItem('hasSetPreference')
    localStorage.removeItem('hasSeenRegistrationDialog')
    // 重置内存中的偏好数据
    selectedChannel.value = ''
    selectedCategories.value = []
    selectedSubCategories.value = {}
    delete axios.defaults.headers.common['Authorization']
  }

  // 设置用户选择的频道和分类
  function setChannel(channel) {
    selectedChannel.value = channel
    localStorage.setItem('selectedChannel', channel)
  }

  function setCategories(categories) {
    selectedCategories.value = categories
    localStorage.setItem('selectedCategories', JSON.stringify(categories))
  }

  function setSubCategories(subCategories) {
    selectedSubCategories.value = subCategories
    localStorage.setItem('selectedSubCategories', JSON.stringify(subCategories))
  }

  function clearSelection() {
    selectedChannel.value = ''
    selectedCategories.value = []
    selectedSubCategories.value = {}
    localStorage.removeItem('selectedChannel')
    localStorage.removeItem('selectedCategories')
    localStorage.removeItem('selectedSubCategories')
  }

  function setHasSetPreference(value) {
    hasSetPreference.value = value
    localStorage.setItem('hasSetPreference', JSON.stringify(value))
  }

  function setHasSeenRegistrationDialog(value) {
    hasSeenRegistrationDialog.value = value
    localStorage.setItem('hasSeenRegistrationDialog', JSON.stringify(value))
  }

  // 初始化时设置 token 和选择状态
  if (token.value) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  return {
    token,
    user,
    isLoggedIn,
    selectedChannel,
    selectedCategories,
    selectedSubCategories,
    hasSetPreference,
    hasSeenRegistrationDialog,
    setAuth,
    logout,
    setChannel,
    setCategories,
    setSubCategories,
    clearSelection,
    setHasSetPreference,
    setHasSeenRegistrationDialog,
    loadUserPreferences
  }
})
