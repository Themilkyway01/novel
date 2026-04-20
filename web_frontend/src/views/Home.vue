<template>
  <div class="home">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo" @click="$router.push('/')">
          <el-icon><Reading /></el-icon>
          <span>网文推荐系统</span>
        </div>

        <div class="search-bar">
          <div class="search-container">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索小说、作者..."
              clearable
              @keyup.enter="handleSearch"
              @input="handleSearchInput"
              @focus="showSuggestions = searchSuggestions.length > 0"
              @blur="handleSearchBlur"
            >
              <template #append>
                <el-button @click="handleSearch">
                  <el-icon><Search /></el-icon>
                </el-button>
              </template>
            </el-input>
            <!-- 搜索建议下拉列表 -->
            <div
              v-show="showSuggestions && searchSuggestions.length > 0"
              class="search-suggestions"
            >
              <div
                v-for="(item, index) in searchSuggestions"
                :key="index"
                class="suggestion-item"
                @click.middle="handleSuggestionClickMiddle(item)"
                @click="handleSuggestionClick(item)"
              >
                <div class="suggestion-content">
                  <span class="suggestion-label">{{ item.label }}</span>
                  <span v-if="item.type === 'novel'" class="suggestion-author">- {{ item.author }}</span>
                </div>
                <el-tag
                  :type="item.type === 'novel' ? 'primary' : 'success'"
                  size="small"
                  class="suggestion-tag"
                >
                  {{ item.type === 'novel' ? '作品' : '作者' }}
                  <span v-if="item.type === 'author' && item.novel_count">({{ item.novel_count }}部)</span>
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <div class="nav-links">
          <el-link type="info" @click="$router.push('/category')">分类</el-link>
          <el-link type="info" @click="$router.push('/rank')">排行榜</el-link>
          <template v-if="userStore.isLoggedIn">
            <el-link type="info" @click="$router.push('/profile')">
              <el-icon><User /></el-icon>
              {{ userStore.user?.username }}
            </el-link>
            <el-link type="info" @click="$router.push('/history')">阅读历史</el-link>
            <el-link type="danger" @click="handleLogout">退出</el-link>
          </template>
          <template v-else>
            <el-link type="primary" @click="$router.push('/login')">登录</el-link>
            <el-link type="success" @click="$router.push('/register')">注册</el-link>
          </template>
        </div>
      </div>
    </el-header>

    <!-- 推荐偏好设置对话框 -->
    <el-dialog
      v-model="showPreferenceDialog"
      title="推荐偏好设置"
      width="600px"
      align-center
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
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
              <el-icon><InfoFilled /></el-icon> 未设置偏好，将显示全部分类的热门推荐
            </p>
            <p v-else>
              <el-icon><Check /></el-icon> 已选择：{{ dialogSelectionSummary }}
            </p>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleCancelDialog">跳过</el-button>
          <el-button type="primary" @click="savePreference">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 主要内容 -->
    <el-main class="main-content">
      <!-- 热门推荐 -->
      <div class="section">
        <div class="section-header">
          <h2><el-icon><HotWater /></el-icon> 热门推荐</h2>
          <el-link type="primary" :loading="hotNovelsLoading" :disabled="hotNovelsLoading" @click="loadHotNovels">换一批</el-link>
        </div>
        <el-row :gutter="20" v-loading="hotNovelsLoading">
          <el-col :xs="12" :sm="8" :md="6" :lg="4" v-for="novel in hotNovels" :key="novel.index">
            <div class="novel-card" @click.middle="goToDetail(novel.index)" @click="goToDetailNewTab(novel.index)">
              <el-image :src="novel.img || '/placeholder.jpg'" fit="cover" />
              <div class="novel-info">
                <div class="novel-name">{{ novel.name }}</div>
                <div class="novel-author">{{ novel.author }}</div>
                <div class="novel-tags">
                  <el-tag size="small">{{ novel.category }}</el-tag>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 最新更新 -->
      <div class="section">
        <div class="section-header">
          <h2><el-icon><Clock /></el-icon> 最新更新</h2>
          <el-link type="primary" :loading="recentNovelsLoading" :disabled="recentNovelsLoading" @click="loadRecent">换一批</el-link>
        </div>
        <el-row :gutter="20" v-loading="recentNovelsLoading">
          <el-col :xs="12" :sm="8" :md="6" :lg="4" v-for="novel in recentNovels" :key="novel.index">
            <div class="novel-card" @click.middle="goToDetail(novel.index)" @click="goToDetailNewTab(novel.index)">
              <el-image :src="novel.img || '/placeholder.jpg'" fit="cover" />
              <div class="novel-info">
                <div class="novel-name">{{ novel.name }}</div>
                <div class="novel-author">{{ novel.author }}</div>
                <div class="novel-update">{{ novel.up_chapter }}</div>
                <div class="novel-time">{{ formatTime(novel.up_time) }}</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

    </el-main>

    <!-- 底部 -->
    <footer class="footer">
      <p>网文小说推荐系统 &copy; 2026</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getHotNovels, getRecentNovels, getSearchSuggestions, getCategories, getNovelList, saveUserPreferences } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const searchKeyword = ref('')
const searchSuggestions = ref([])
const showSuggestions = ref(false)
let searchTimeout = null

const hotNovels = ref([])
const recentNovels = ref([])
// 跟踪已显示的热门书籍ID，避免重复推荐（最多保留最近50个）
const displayedHotNovelIds = ref([])

// 加载状态
const hotNovelsLoading = ref(false)
const recentNovelsLoading = ref(false)

// 推荐偏好设置对话框相关
const showPreferenceDialog = ref(false)
const dialogChannel = ref('')
const dialogCategories = ref([])
const dialogSubCategoryMap = reactive({})
const dialogSubCategoryOptions = reactive({})
const dialogAvailableCategories = ref([])

// 计算对话框选择状态
const dialogHasSelection = computed(() => {
  return dialogChannel.value !== '' || dialogCategories.value.length > 0
})

const dialogSelectionSummary = computed(() => {
  const parts = []
  if (dialogChannel.value !== '') {
    const channelMap = { '0': '女频', '1': '男频', '2': '出版' }
    parts.push(channelMap[dialogChannel.value])
  }
  if (dialogCategories.value.length > 0) {
    parts.push(dialogCategories.value.join('、'))
  }
  return parts.join(' - ')
})

// 初始化
onMounted(async () => {
  await loadAll()

  // 检查是否需要弹出推荐偏好设置对话框
  // 只在注册后弹出一次（通过sessionStorage标记）
  await nextTick()
  console.log('检查对话框条件:', {
    isLoggedIn: userStore.isLoggedIn,
    justRegistered: sessionStorage.getItem('justRegistered')
  })
  if (userStore.isLoggedIn && sessionStorage.getItem('justRegistered') === 'true') {
    console.log('弹出推荐偏好设置对话框（注册后）')
    await openPreferenceDialog()
    // 清除标记，确保只弹出一次
    sessionStorage.removeItem('justRegistered')
    // 同时更新userStore状态，确保其他页面知道已看过弹窗
    userStore.setHasSeenRegistrationDialog(true)
  }
})

// 随机打乱数组
const shuffleArray = (array) => {
  const newArray = [...array]
  for (let i = newArray.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[newArray[i], newArray[j]] = [newArray[j], newArray[i]]
  }
  return newArray
}

// 加载所有推荐
const loadAll = async () => {
  console.log('加载推荐数据，用户偏好:', {
    isLoggedIn: userStore.isLoggedIn,
    selectedChannel: userStore.selectedChannel,
    selectedCategories: userStore.selectedCategories,
    userId: userStore.user?.id
  })
  await loadHotNovels()
  await loadRecent()
}

// 打开推荐偏好设置对话框
const openPreferenceDialog = async () => {
  // 初始化对话框数据
  dialogChannel.value = userStore.selectedChannel !== '' ? Number(userStore.selectedChannel) : ''
  dialogCategories.value = [...userStore.selectedCategories]

  // 复制子分类映射
  Object.keys(dialogSubCategoryMap).forEach(key => delete dialogSubCategoryMap[key])
  Object.keys(userStore.selectedSubCategories).forEach(key => {
    dialogSubCategoryMap[key] = [...userStore.selectedSubCategories[key]]
  })

  // 加载当前频道的分类
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

  // 为已选择的分类加载子分类
  for (const cat of dialogCategories.value) {
    await loadDialogSubCategoriesForCategory(cat)
  }

  showPreferenceDialog.value = true
}

// 对话框中频道变化
const handleDialogChannelChange = async () => {
  dialogCategories.value = []
  Object.keys(dialogSubCategoryMap).forEach(key => delete dialogSubCategoryMap[key])
  Object.keys(dialogSubCategoryOptions).forEach(key => delete dialogSubCategoryOptions[key])

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
  const newVals = dialogCategories.value

  for (const cat of newVals) {
    if (!dialogSubCategoryOptions[cat]) {
      await loadDialogSubCategoriesForCategory(cat)
    }
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

    const uniqueSubCats = [...new Set(novelsList.map(novel => novel.sub_category).filter(Boolean))]
    dialogSubCategoryOptions[category] = uniqueSubCats

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
  // 更新 userStore
  userStore.setChannel(dialogChannel.value)
  userStore.setCategories([...dialogCategories.value])
  userStore.setSubCategories({ ...dialogSubCategoryMap })
  userStore.setHasSetPreference(true)
  userStore.setHasSeenRegistrationDialog(true)

  // 同步保存到服务器
  try {
    await saveUserPreferences({
      selected_channel: userStore.selectedChannel,
      selected_categories: userStore.selectedCategories,
      selected_sub_categories: userStore.selectedSubCategories,
      has_set_preference: true
    })
    console.log('偏好设置已同步到服务器')
  } catch (error) {
    console.error('保存偏好到服务器失败:', error)
  }

  // 关闭对话框
  showPreferenceDialog.value = false

  ElMessage.success('偏好设置已保存')

  // 重置已显示书籍ID列表，因为偏好已改变
  displayedHotNovelIds.value = []

  // 重新加载推荐内容
  loadAll()
}

// 跳过设置
const handleCancelDialog = () => {
  userStore.setHasSeenRegistrationDialog(true)
  showPreferenceDialog.value = false
}

// 加载热门推荐
const loadHotNovels = async () => {
  try {
    hotNovelsLoading.value = true
    const params = { n: 12, random: true, t: Date.now() }
    // 优先使用用户选择的频道偏好，如果没有则使用注册时的性别偏好
    if (userStore.selectedChannel !== '' && userStore.selectedChannel !== null && userStore.selectedChannel !== undefined) {
      params.channel = parseInt(userStore.selectedChannel)
    } else if (userStore.isLoggedIn && userStore.user && userStore.user.user_cate !== undefined && userStore.user.user_cate !== null) {
      // 使用用户注册时的性别偏好（男频/女频）
      params.channel = userStore.user.user_cate
    }
    // 传递所有选中的分类（支持多类别偏好）
    if (userStore.selectedCategories && userStore.selectedCategories.length > 0) {
      // 确保分类按字母顺序排序，保证缓存键一致
      params.categories = [...userStore.selectedCategories].sort().join(',')
    }
    if (userStore.isLoggedIn && userStore.user) {
      params.user_id = userStore.user.id
    }
    // 添加排除已显示书籍的逻辑
    if (displayedHotNovelIds.value.length > 0) {
      params.exclude = displayedHotNovelIds.value.join(',')
    }
    console.log('加载热门推荐，参数:', params)
    const res = await getHotNovels(params)
    console.log('热门推荐结果:', res)
    // 随机打乱推荐结果
    hotNovels.value = shuffleArray(res)
    // 将新显示的书籍ID添加到已显示列表中，避免重复，最多保留最近50个
    res.forEach(novel => {
      if (novel.id && !displayedHotNovelIds.value.includes(novel.id)) {
        displayedHotNovelIds.value.push(novel.id)
      }
    })
    // 限制数组大小，最多保留最近50个ID
    if (displayedHotNovelIds.value.length > 50) {
      displayedHotNovelIds.value = displayedHotNovelIds.value.slice(-50)
    }
  } catch (error) {
    console.error('加载热门推荐失败:', error)
  } finally {
    hotNovelsLoading.value = false
  }
}

// 加载最新更新
const loadRecent = async () => {
  try {
    recentNovelsLoading.value = true
    const params = { n: 12, t: Date.now() }  // 始终传递时间戳以跳过缓存
    // 优先使用用户选择的频道偏好，如果没有则使用注册时的性别偏好
    if (userStore.selectedChannel !== '' && userStore.selectedChannel !== null && userStore.selectedChannel !== undefined) {
      params.channel = parseInt(userStore.selectedChannel)
    } else if (userStore.isLoggedIn && userStore.user && userStore.user.user_cate !== undefined && userStore.user.user_cate !== null) {
      // 使用用户注册时的性别偏好（男频/女频）
      params.channel = userStore.user.user_cate
    }
    // 传递所有选中的分类（支持多类别偏好）
    if (userStore.selectedCategories && userStore.selectedCategories.length > 0) {
      // 确保分类按字母顺序排序，保证缓存键一致
      params.categories = [...userStore.selectedCategories].sort().join(',')
    }
    if (userStore.isLoggedIn && userStore.user) {
      params.user_id = userStore.user.id
    }
    console.log('加载最新更新，参数:', params)
    const res = await getRecentNovels(params)
    console.log('最新更新结果:', res)
    // 随机打乱推荐结果
    recentNovels.value = shuffleArray(res)
  } catch (error) {
    console.error('加载最新更新失败:', error)
  } finally {
    recentNovelsLoading.value = false
  }
}

// 搜索
const handleSearch = () => {
  showSuggestions.value = false
  if (searchKeyword.value.trim()) {
    router.push({ path: '/category', query: { keyword: searchKeyword.value } })
  }
}

// 搜索输入处理（防抖）
const handleSearchInput = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }

  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    searchSuggestions.value = []
    showSuggestions.value = false
    return
  }

  searchTimeout = setTimeout(async () => {
    try {
      const res = await getSearchSuggestions(keyword, 10)
      searchSuggestions.value = res
      showSuggestions.value = res.length > 0
    } catch (error) {
      console.error('搜索建议失败:', error)
    }
  }, 300)
}

// 搜索框失焦处理
const handleSearchBlur = () => {
  setTimeout(() => {
    showSuggestions.value = false
  }, 200)
}

// 点击搜索建议（左键新标签页）
const handleSuggestionClick = (item) => {
  showSuggestions.value = false
  if (item.type === 'novel') {
    const routeUrl = router.resolve({
      path: `/novel/${item.id}`
    })
    window.open(routeUrl.href, '_blank')
  } else if (item.type === 'author') {
    const routeUrl = router.resolve({
      path: '/category',
      query: { keyword: item.author }
    })
    window.open(routeUrl.href, '_blank')
  }
}

// 点击搜索建议（中键同标签页）
const handleSuggestionClickMiddle = (item) => {
  showSuggestions.value = false
  if (item.type === 'novel') {
    router.push(`/novel/${item.id}`)
  } else if (item.type === 'author') {
    router.push({ path: '/category', query: { keyword: item.author } })
  }
}

// 退出登录
const handleLogout = () => {
  userStore.logout()
  ElMessage.success('已退出登录')
  // 使用 window.location.reload() 强制刷新页面，确保首页数据更新
  window.location.reload()
}

// 跳转详情
const goToDetail = (novelId) => {
  router.push(`/novel/${novelId}`)
}

// 新标签页打开详情
const goToDetailNewTab = (novelId) => {
  const routeUrl = router.resolve({
    path: `/novel/${novelId}`
  })
  window.open(routeUrl.href, '_blank')
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  height: 60px;
  gap: 40px;
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

.search-bar {
  flex: 1;
  max-width: 500px;
}

.search-container {
  position: relative;
  width: 100%;
}

.search-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-height: 400px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.suggestion-item:hover {
  background-color: #f5f7fa;
}

.suggestion-content {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 10px;
}

.suggestion-label {
  font-size: 14px;
  color: #303133;
}

.suggestion-author {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.suggestion-tag {
  flex-shrink: 0;
}

.nav-links {
  display: flex;
  gap: 20px;
  align-items: center;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  flex: 1;
  padding: 0;
}

.section {
  margin: 20px 0;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  color: #303133;
}

.novel-card {
  cursor: pointer;
  transition: transform 0.3s;
  margin-bottom: 20px;
  position: relative;
}

.novel-card:hover {
  transform: translateY(-5px);
}

.novel-card :deep(.el-image) {
  width: 100%;
  height: 200px;
  border-radius: 8px;
}

.novel-info {
  padding: 10px 0;
}

.novel-name {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.novel-author {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.novel-desc {
  font-size: 12px;
  color: #C0C4CC;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.novel-update {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.novel-time {
  font-size: 11px;
  color: #C0C4CC;
  margin-top: 3px;
}

.novel-tags {
  margin-top: 5px;
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.status-info p {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0;
  color: #606266;
}

.status-info .el-icon {
  font-size: 16px;
}
</style>
