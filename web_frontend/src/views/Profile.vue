<template>
  <div class="profile-page">
    <!-- 导航栏 -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo" @click="$router.push('/')">
          <el-icon><Reading /></el-icon>
          <span>网文推荐系统</span>
        </div>
        <div class="nav-links">
          <el-link @click="$router.push('/')">首页</el-link>
          <el-link @click="$router.push('/history')">阅读历史</el-link>
        </div>
      </div>
    </el-header>

    <el-main class="main-content">
      <h2><el-icon><User /></el-icon> 个人中心</h2>

      <el-row :gutter="20">
        <!-- 用户信息卡片 -->
        <el-col :xs="24" :md="12">
          <el-card>
            <template #header>
              <span><el-icon><User /></el-icon> 基本信息</span>
            </template>
            <el-form label-width="100px">
              <el-form-item label="用户名">
                <span>{{ userStore.user?.username }}</span>
              </el-form-item>

              <el-form-item label="邮箱">
                <span>{{ userStore.user?.email || '未设置' }}</span>
              </el-form-item>

              <el-form-item label="注册时间">
                <span>{{ formatTime(userStore.user?.created_at) }}</span>
              </el-form-item>

              <el-form-item label="当前偏好" class="preference-form-item">
                <div class="preference-tags">
                  <span v-if="!hasSelection" class="no-preference">未设置偏好，将显示全部分类的热门推荐</span>
                  <template v-else>
                    <el-tag
                      v-if="selectedChannel !== ''"
                      :type="getChannelTagType(selectedChannel)"
                      size="large"
                      effect="light"
                      style="margin-right: 10px; margin-bottom: 10px"
                    >
                      {{ channelName }}
                    </el-tag>
                    <el-tag
                      v-for="(cat, index) in selectedCategories"
                      :key="cat"
                      :type="getCategoryTagType(index)"
                      effect="light"
                      size="large"
                      style="margin-right: 10px; margin-bottom: 10px"
                    >
                      {{ cat }}
                      <template v-if="subCategoryMap[cat] && subCategoryMap[cat].length > 0">
                        <span class="sub-category">（{{ subCategoryMap[cat].join('，') }}）</span>
                      </template>
                    </el-tag>
                  </template>
                </div>
              </el-form-item>

              <el-form-item label="">
                <el-button type="primary" @click="openPreferenceDialog">
                  <el-icon><Setting /></el-icon> 点击修改
                </el-button>
                <el-button type="danger" @click="showDeleteDialog = true" style="margin-left: 10px;">
                  <el-icon><Delete /></el-icon> 注销账户
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <!-- 阅读偏好分析 -->
        <el-col :xs="24" :md="12">
          <el-card>
            <template #header>
              <span><el-icon><Data-Analysis /></el-icon> 阅读偏好分析</span>
            </template>
            <div v-if="hasReadingHistory && userPreferences.inferred_categories.length > 0">
              <p style="margin-bottom: 12px;">根据您的阅读记录，您可能喜欢以下分类：</p>
              <div class="preference-details">
                <div
                  v-for="(category, index) in userPreferences.inferred_categories"
                  :key="category.category"
                  class="preference-category-item"
                >
                  <div class="category-header">
                    <el-tag
                      :type="getCategoryTagType(index)"
                      effect="light"
                      size="large"
                      class="category-tag"
                    >
                      {{ category.category }}
                    </el-tag>
                    <span class="category-score">
                      兴趣指数: {{ category.score }}
                    </span>
                  </div>
                  <div class="category-info">
                    <span>阅读 {{ category.count }} 本，平均时长 {{ category.avg_read_time }} 分钟</span>
                  </div>
                  <div v-if="category.sub_categories && category.sub_categories.length > 0" class="sub-categories">
                    <div
                      v-for="subCat in category.sub_categories"
                      :key="subCat.name"
                      class="sub-category-item"
                    >
                      <span class="sub-category-name">{{ subCat.name }}</span>
                      <span class="sub-category-info">
                        {{ subCat.count }} 本 / {{ subCat.avg_read_time }} 分钟
                      </span>
                      <span class="sub-category-score">{{ subCat.score }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else>
              <p><el-icon><Info-Filled /></el-icon> 暂无阅读记录，开始阅读以生成您的专属偏好分析</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-dialog
        v-model="showPreferenceDialog"
        title="推荐偏好设置"
        width="600px"
        align-center
      >
        <el-form label-width="80px">
          <el-form-item label="频道">
            <el-radio-group v-model="dialogChannel" @change="handleDialogChannelChange">
              <el-radio-button value="">全部</el-radio-button>
              <el-radio-button :value="1">男频</el-radio-button>
              <el-radio-button :value="0">女频</el-radio-button>
              <el-radio-button :value="2">出版</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="分类" v-if="dialogChannel !== ''">
            <el-select
              v-model="dialogCategories"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :max-collapse-tags="3"
              placeholder="请选择分类（最多3个）"
              clearable
              @change="handleDialogCategoriesChange"
              style="width: 100%"
              :multiple-limit="3"
            >
              <el-option
                v-for="cat in dialogAvailableCategories"
                :key="cat"
                :label="cat"
                :value="cat"
              />
            </el-select>
          </el-form-item>

          <!-- 每个分类的子分类选择 -->
          <el-form-item
            v-for="category in dialogCategories"
            :key="category"
            :label="category"
            v-if="Number(dialogChannel) !== 2"
          >
            <el-select
              v-model="dialogSubCategoryMap[category]"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :max-collapse-tags="3"
              placeholder="请选择子分类（最多 3 个）"
              clearable
              @change="handleDialogSubCategoriesChange"
              style="width: 100%"
              :multiple-limit="3"
            >
              <el-option
                v-for="subCat in dialogSubCategoryOptions[category] || []"
                :key="subCat"
                :label="subCat"
                :value="subCat"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="当前状态">
            <div class="status-info">
              <p v-if="!dialogHasSelection">
                <el-icon><Info-Filled /></el-icon> 未设置偏好，将显示全部分类的热门推荐
              </p>
              <p v-else>
                <el-icon><Check /></el-icon> 已选择：{{ dialogSelectionSummary }}
              </p>
            </div>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showPreferenceDialog = false">取消</el-button>
            <el-button type="primary" @click="savePreference">保存</el-button>
          </span>
        </template>
      </el-dialog>
      
      <!-- 注销账户对话框 -->
      <el-dialog
        v-model="showDeleteDialog"
        title="注销账户"
        width="400px"
        align-center
        :before-close="handleDeleteDialogClose"
      >
        <el-alert
          title="警告"
          type="warning"
          :closable="false"
          style="margin-bottom: 15px;"
        >
          <p>此操作将永久删除您的账户以及所有相关数据（阅读历史、偏好设置等），且无法恢复。请谨慎操作。</p>
        </el-alert>
        <el-form :model="deleteForm" :rules="deleteRules" ref="deleteFormRef" label-width="80px">
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="deleteForm.password"
              type="password"
              placeholder="请输入密码进行验证"
              show-password
              @keyup.enter="confirmDelete"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="cancelDelete">取消</el-button>
            <el-button type="danger" @click="confirmDelete" :loading="deleteLoading">
              {{ deleteLoading ? '处理中...' : '确认注销' }}
            </el-button>
          </span>
        </template>
      </el-dialog>
    </el-main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getCategories, getUserPreferences, getNovelList, getReadingHistory, saveUserPreferences, deleteAccount } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const selectedChannel = ref('')
const selectedCategories = ref([])
const subCategoryMap = reactive({})
const subCategoryOptions = reactive({})
const availableCategories = ref([])
const userPreferences = reactive({
  inferred_categories: []
})

const hasReadingHistory = ref(false)

// 对话框相关
const showPreferenceDialog = ref(false)

// 注销账户相关
const showDeleteDialog = ref(false)
const deleteLoading = ref(false)
const deleteFormRef = ref(null)
const deleteForm = reactive({
  password: ''
})

const deleteRules = {
  password: [
    { required: true, message: '请输入密码进行验证', trigger: 'blur' },
    { min: 1, message: '密码不能为空', trigger: 'blur' }
  ]
}
const dialogChannel = ref('')
const dialogCategories = ref([])
const dialogSubCategoryMap = reactive({})
const dialogSubCategoryOptions = reactive({})
const dialogAvailableCategories = ref([])

// 打开偏好设置对话框
const openPreferenceDialog = () => {
  console.log('打开对话框前的 selectedChannel:', selectedChannel.value, '类型:', typeof selectedChannel.value)
  // 初始化对话框数据为当前选择
  dialogChannel.value = selectedChannel.value !== '' ? Number(selectedChannel.value) : ''
  console.log('初始化后的 dialogChannel:', dialogChannel.value, '类型:', typeof dialogChannel.value)
  dialogCategories.value = [...selectedCategories.value]
  
  // 复制子分类映射
  Object.keys(dialogSubCategoryMap).forEach(key => delete dialogSubCategoryMap[key])
  Object.keys(subCategoryMap).forEach(key => {
    dialogSubCategoryMap[key] = [...subCategoryMap[key]]
  })
  
  // 复制分类选项
  dialogAvailableCategories.value = [...availableCategories.value]
  Object.keys(dialogSubCategoryOptions).forEach(key => delete dialogSubCategoryOptions[key])
  Object.keys(subCategoryOptions).forEach(key => {
    dialogSubCategoryOptions[key] = [...subCategoryOptions[key]]
  })
  
  showPreferenceDialog.value = true
}

// 对话框中频道变化
const handleDialogChannelChange = async () => {
  dialogCategories.value = []
  Object.keys(dialogSubCategoryMap).forEach(key => delete dialogSubCategoryMap[key])
  Object.keys(dialogSubCategoryOptions).forEach(key => delete dialogSubCategoryOptions[key])
  
  // 加载新频道对应的分类
  try {
    const params = {}
    if (dialogChannel.value && dialogChannel.value !== '') {
      params.cate = parseInt(dialogChannel.value)
    }
    const res = await getCategories(params)
    dialogAvailableCategories.value = res.map(item => item.category)
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

// 对话框中分类变化
const handleDialogCategoriesChange = async () => {
  // 移除不在新选择中的分类的子分类
  const oldVals = [...dialogCategories.value]
  const newVals = dialogCategories.value
  
  // 为新选择的分类加载子分类
  for (const cat of newVals) {
    if (!dialogSubCategoryOptions[cat]) {
      await loadDialogSubCategoriesForCategory(cat)
    }
    // 初始化子分类选择
    if (!dialogSubCategoryMap[cat]) {
      dialogSubCategoryMap[cat] = []
    }
  }
}

// 对话框中子分类变化
const handleDialogSubCategoriesChange = () => {
  // 可以在这里添加额外的处理逻辑
}

// 为指定分类加载子分类（对话框版本）
const loadDialogSubCategoriesForCategory = async (category) => {
  if (!category || dialogChannel.value === 2) {
    // 出版模式不加载子分类
    dialogSubCategoryOptions[category] = []
    return
  }

  try {
    const params = {
      page: 1,
      page_size: 100,
      category: category
    }

    if (dialogChannel.value) {
      params.cate = parseInt(dialogChannel.value)
    }

    const res = await getNovelList(params)
    const novelsList = res.results || res

    // 提取唯一的子分类
    const uniqueSubCats = [...new Set(novelsList.map(novel => novel.sub_category).filter(Boolean))]
    dialogSubCategoryOptions[category] = uniqueSubCats

    // 初始化子分类选择（如果还没有的话）
    if (!dialogSubCategoryMap[category]) {
      dialogSubCategoryMap[category] = []
    }
  } catch (error) {
    console.error(`加载分类"${category}"的子分类失败:`, error)
    dialogSubCategoryOptions[category] = []
  }
}

// 保存偏好设置
const savePreference = async () => {
  // 更新主数据（确保类型一致）
  selectedChannel.value = dialogChannel.value !== '' ? String(dialogChannel.value) : ''
  selectedCategories.value = [...dialogCategories.value]

  // 更新子分类映射
  Object.keys(subCategoryMap).forEach(key => delete subCategoryMap[key])
  Object.keys(dialogSubCategoryMap).forEach(key => {
    subCategoryMap[key] = [...dialogSubCategoryMap[key]]
  })

  // 保存到 userStore 和 localStorage
  saveSelectionToStore()

  // 同步保存到服务器
  try {
    await saveUserPreferences({
      selected_channel: selectedChannel.value,
      selected_categories: selectedCategories.value,
      selected_sub_categories: subCategoryMap,
      has_set_preference: true
    })
    console.log('偏好设置已同步到服务器')
  } catch (error) {
    console.error('保存偏好到服务器失败:', error)
  }

  // 关闭对话框
  showPreferenceDialog.value = false

  ElMessage.success('偏好设置已保存')
}

// 频道名称映射
const channelNameMap = {
  1: '男频',
  0: '女频',
  2: '出版'
}

// 频道标签类型映射
const channelTagTypeMap = {
  1: 'danger',    // 男频 - 红色
  0: 'success',   // 女频 - 绿色
  2: 'warning'    // 出版 - 橙色
}

// 获取频道标签类型
const getChannelTagType = (channel) => {
  return channelTagTypeMap[channel] || 'primary'
}

// 分类标签类型循环数组
const categoryTagTypes = ['primary', 'success', 'warning', 'danger', 'info']

// 获取分类标签类型
const getCategoryTagType = (index) => {
  return categoryTagTypes[index % categoryTagTypes.length]
}

const channelName = computed(() => channelNameMap[selectedChannel.value] || '')

// 是否有选择
const hasSelection = computed(() => {
  return selectedChannel.value !== '' || selectedCategories.value.length > 0
})

// 对话框中的选择状态
const dialogHasSelection = computed(() => {
  return dialogChannel.value !== '' || dialogCategories.value.length > 0
})

// 对话框中的选择摘要
const dialogSelectionSummary = computed(() => {
  if (dialogChannel.value === '' && dialogCategories.value.length === 0) {
    return ''
  }

  let parts = []
  if (dialogChannel.value !== '') {
    parts.push(`频道：${channelNameMap[dialogChannel.value] || ''}`)
  }
  if (dialogCategories.value.length > 0) {
    const catsWithSub = dialogCategories.value.map(cat => {
      const subCats = dialogSubCategoryMap[cat] || []
      return subCats.length > 0 ? `${cat}(${subCats.join(',')})` : cat
    })
    parts.push(`分类：${catsWithSub.join('、')}`)
  }
  return parts.join('，')
})

// 选择摘要
const selectionSummary = computed(() => {
  if (selectedChannel.value === '' && selectedCategories.value.length === 0) {
    return ''
  }
  
  let parts = []
  if (selectedChannel.value !== '') {
    parts.push(`频道：${channelName.value}`)
  }
  if (selectedCategories.value.length > 0) {
    const catsWithSub = selectedCategories.value.map(cat => {
      const subCats = subCategoryMap[cat] || []
      return subCats.length > 0 ? `${cat}(${subCats.join(',')})` : cat
    })
    parts.push(`分类：${catsWithSub.join('、')}`)
  }
  return parts.join('，')
})

// 初始化
onMounted(() => {
  // 确保类型一致：userStore.selectedChannel 可能是字符串
  selectedChannel.value = userStore.selectedChannel !== '' ? String(userStore.selectedChannel) : ''
  // 从userStore加载已选择的分类
  if (userStore.selectedCategories && userStore.selectedCategories.length > 0) {
    selectedCategories.value = [...userStore.selectedCategories]
  }
  // 从userStore加载已选择的子分类
  if (userStore.selectedSubCategories) {
    Object.keys(userStore.selectedSubCategories).forEach(cat => {
      subCategoryMap[cat] = [...userStore.selectedSubCategories[cat]]
    })
  }
  loadCategories()
  loadUserPreferences()
})

// 监听对话框打开，初始化数据
watch(showPreferenceDialog, (newVal) => {
  if (newVal) {
    // 初始化对话框数据
    dialogChannel.value = selectedChannel.value !== '' ? Number(selectedChannel.value) : ''
    dialogCategories.value = [...selectedCategories.value]
    // 复制子分类
    Object.keys(dialogSubCategoryMap).forEach(key => delete dialogSubCategoryMap[key])
    Object.keys(subCategoryMap).forEach(key => {
      dialogSubCategoryMap[key] = [...subCategoryMap[key]]
    })
    // 复制分类选项
    dialogAvailableCategories.value = [...availableCategories.value]
    Object.keys(dialogSubCategoryOptions).forEach(key => delete dialogSubCategoryOptions[key])
    Object.keys(subCategoryOptions).forEach(key => {
      dialogSubCategoryOptions[key] = [...subCategoryOptions[key]]
    })
  }
})

// 监听对话框中分类选择变化，加载对应的子分类
watch(() => [...dialogCategories.value], async (newVals, oldVals) => {
  if (!showPreferenceDialog.value) return
  
  // 移除不在新选择中的分类的子分类
  const removedCats = oldVals.filter(cat => !newVals.includes(cat))
  removedCats.forEach(cat => {
    delete dialogSubCategoryMap[cat]
    delete dialogSubCategoryOptions[cat]
  })

  // 为新选择的分类加载子分类
  for (const cat of newVals) {
    if (!dialogSubCategoryOptions[cat]) {
      await loadDialogSubCategoriesForCategory(cat)
    }
  }
})

// 监听分类选择变化，加载对应的子分类
watch(() => [...selectedCategories.value], async (newVals, oldVals) => {
  // 移除不在新选择中的分类的子分类
  const removedCats = oldVals.filter(cat => !newVals.includes(cat))
  removedCats.forEach(cat => {
    delete subCategoryMap[cat]
    delete subCategoryOptions[cat]
  })
  
  // 为新选择的分类加载子分类
  for (const cat of newVals) {
    if (!subCategoryOptions[cat]) {
      await loadSubCategoriesForCategory(cat)
    }
  }
  
  // 保存到userStore
  saveSelectionToStore()
})

// 加载分类列表
const loadCategories = async () => {
  try {
    const params = {}
    if (selectedChannel.value) {
      params.cate = parseInt(selectedChannel.value)
    }
    const res = await getCategories(params)
    availableCategories.value = res.map(item => item.category)
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

// 加载用户偏好和阅读历史
const loadUserPreferences = async () => {
  if (!userStore.user?.id) return

  try {
    // 同时获取用户偏好和阅读历史
    const [preferencesRes, historyRes] = await Promise.allSettled([
      getUserPreferences(userStore.user.id),
      getReadingHistory()
    ])
    
    // 处理偏好数据
    if (preferencesRes.status === 'fulfilled') {
      userPreferences.inferred_categories = preferencesRes.value.inferred_categories || []
    } else {
      console.error('加载用户偏好失败:', preferencesRes.reason)
      userPreferences.inferred_categories = []
    }
    
    // 检查是否有阅读历史
    if (historyRes.status === 'fulfilled') {
      const historyData = historyRes.value
      hasReadingHistory.value = historyData && Array.isArray(historyData.results) && historyData.results.length > 0
    } else {
      console.error('加载阅读历史失败:', historyRes.reason)
      hasReadingHistory.value = false
    }
  } catch (error) {
    console.error('加载用户数据失败:', error)
    userPreferences.inferred_categories = []
    hasReadingHistory.value = false
  }
}

// 处理频道变化
const handleChannelChange = () => {
  userStore.setChannel(selectedChannel.value)
  selectedCategories.value = []
  Object.keys(subCategoryMap).forEach(key => delete subCategoryMap[key])
  Object.keys(subCategoryOptions).forEach(key => delete subCategoryOptions[key])
  loadCategories()
  saveSelectionToStore()
}

// 处理分类变化
const handleCategoriesChange = () => {
  saveSelectionToStore()
}

// 处理子分类变化
const handleSubCategoriesChange = () => {
  saveSelectionToStore()
}

// 为指定分类加载子分类
const loadSubCategoriesForCategory = async (category) => {
  if (!category || selectedChannel.value === 2) {
    // 出版模式不加载子分类
    subCategoryOptions[category] = []
    return
  }

  try {
    const params = {
      page: 1,
      page_size: 100,
      category: category
    }

    if (selectedChannel.value) {
      params.cate = parseInt(selectedChannel.value)
    }

    const res = await getNovelList(params)
    const novelsList = res.results || res

    // 提取唯一的子分类
    const uniqueSubCats = [...new Set(novelsList.map(novel => novel.sub_category).filter(Boolean))]
    subCategoryOptions[category] = uniqueSubCats
    
    // 初始化子分类选择（如果还没有的话）
    if (!subCategoryMap[category]) {
      subCategoryMap[category] = []
    }
  } catch (error) {
    console.error(`加载分类"${category}"的子分类失败:`, error)
    subCategoryOptions[category] = []
  }
}

// 保存选择到userStore
const saveSelectionToStore = () => {
  // 确保保存的是字符串类型
  userStore.setChannel(String(selectedChannel.value))
  userStore.setCategories([...selectedCategories.value])
  userStore.setSubCategories({ ...subCategoryMap })
  userStore.setHasSetPreference(true)
  userStore.setHasSeenRegistrationDialog(true)

  console.log('保存偏好设置到store:', {
    channel: selectedChannel.value,
    type: typeof selectedChannel.value,
    categories: selectedCategories.value,
    subCategories: subCategoryMap
  })
}

// 清除选择
const clearSelection = () => {
  userStore.clearSelection()
  selectedChannel.value = ''
  selectedCategories.value = []
  Object.keys(subCategoryMap).forEach(key => delete subCategoryMap[key])
  Object.keys(subCategoryOptions).forEach(key => delete subCategoryOptions[key])
  loadCategories()
  ElMessage.success('已清除偏好选择')
}

// 注销账户相关函数
const handleDeleteDialogClose = (done) => {
  if (deleteLoading.value) return
  cancelDelete()
  done()
}

const cancelDelete = () => {
  showDeleteDialog.value = false
  deleteForm.password = ''
  if (deleteFormRef.value) {
    deleteFormRef.value.resetFields()
  }
}

const confirmDelete = () => {
  if (!deleteFormRef.value) return
  
  deleteFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    deleteLoading.value = true
    try {
      await deleteAccount(deleteForm.password)
      ElMessage.success('账户已成功注销')
      userStore.logout()
      showDeleteDialog.value = false
      router.push('/')
    } catch (error) {
      console.error('注销失败:', error)
      if (error.response && error.response.data && error.response.data.error) {
        ElMessage.error(error.response.data.error)
      } else {
        ElMessage.error('注销失败，请检查密码或稍后重试')
      }
    } finally {
      deleteLoading.value = false
    }
  })
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: bold;
  color: #409EFF;
  cursor: pointer;
}

.nav-links {
  display: flex;
  gap: 20px;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 30px;
}

.main-content h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  color: #303133;
}

.preference-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-info {
  color: #606266;
  font-size: 14px;
}

.status-info p {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 5px;
}

.preference-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

/* 阅读偏好详细分析样式 */
.preference-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preference-category-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s;
}

.preference-category-item:hover {
  background: #f0f1f2;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.category-tag {
  font-size: 16px;
  font-weight: 500;
}

.category-score {
  font-size: 14px;
  color: #67c23a;
  font-weight: 500;
}

.category-info {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
  padding-left: 4px;
}

.sub-categories {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-left: 12px;
  border-left: 2px solid #e4e7ed;
  margin-left: 4px;
}

.sub-category-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #fff;
  border-radius: 4px;
  font-size: 13px;
}

.sub-category-name {
  font-weight: 500;
  color: #303133;
  flex: 1;
}

.sub-category-info {
  color: #606266;
  margin: 0 12px;
}

.sub-category-score {
  color: #67c23a;
  font-weight: 500;
  min-width: 40px;
  text-align: right;
}

.preference-form-item :deep(.el-form-item__content) {
  display: flex;
  align-items: center;
}

.preference-form-item :deep(.el-form-item__label) {
  display: flex;
  align-items: center;
}
</style>
