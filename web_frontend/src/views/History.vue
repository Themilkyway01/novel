<template>
  <div class="history-page">
    <!-- 导航栏 -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo" @click="$router.push('/')">
          <el-icon><Reading /></el-icon>
          <span>网文推荐系统</span>
        </div>
        <div class="nav-links">
          <el-link @click="$router.push('/')">首页</el-link>
          <el-link @click="$router.push('/profile')">个人中心</el-link>
        </div>
      </div>
    </el-header>

    <el-main class="main-content">
      <div class="header-with-summary">
        <h2><el-icon><Document /></el-icon> 阅读历史</h2>
        <div class="reading-summary" v-if="historyList.length > 0">
          <el-tag type="info" effect="plain">
            共 {{ historyList.length }} 本书，共 {{ totalReadHours }} 小时 {{ totalReadMinutes }} 分钟
          </el-tag>
        </div>
      </div>
      
      <el-table :data="historyList" style="width: 100%" class="history-table">
        <el-table-column prop="novel_img" label="封面" width="100">
          <template #default="{ row }">
            <el-image 
              :src="row.novel_img || '/placeholder.jpg'" 
              fit="cover" 
              style="width: 60px; height: 80px; border-radius: 4px; cursor: pointer;"
              @click.middle="goToDetail(row.novel_id)" @click="goToDetailNewTab(row.novel_id)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="novel_name" label="书名" min-width="200">
          <template #default="{ row }">
            <span class="novel-name-link" @click.middle="goToDetail(row.novel_id)" @click="goToDetailNewTab(row.novel_id)">{{ row.novel_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="read_time" label="阅读时长" sortable min-width="120">
          <template #default="{ row }">
            {{ formatReadTime(row.read_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="阅读时间" sortable min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
      </el-table>
      
      <el-empty v-if="historyList.length === 0" description="暂无阅读记录" />
    </el-main>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getReadingHistory } from '@/api'

const router = useRouter()
const userStore = useUserStore()
const historyList = ref([])

const loadHistory = async () => {
  if (!userStore.user?.id) {
    historyList.value = []
    return
  }
  try {
    const res = await getReadingHistory()
    let rawData = res.results || res || []
    // 按小说ID分组，累加阅读时长，保留最新的阅读时间
    const novelMap = new Map()
    rawData.forEach(item => {
      const novelId = item.novel_id
      if (novelMap.has(novelId)) {
        const existing = novelMap.get(novelId)
        // 累加阅读时长
        existing.read_time += item.read_time
        // 更新为最新的阅读时间
        existing.timestamp = item.timestamp
      } else {
        novelMap.set(novelId, { ...item })
      }
    })
    historyList.value = Array.from(novelMap.values())
  } catch (error) {
    console.error('加载历史失败:', error)
  }
}

const formatReadTime = (minutes) => {
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}小时${mins}分钟`
  }
  return `${minutes}分钟`
}

// 计算总阅读时长
const totalReadTime = computed(() => {
  return historyList.value.reduce((total, item) => total + (item.read_time || 0), 0)
})

const totalReadHours = computed(() => {
  const totalMinutes = totalReadTime.value
  return Math.floor(totalMinutes / 60)
})

const totalReadMinutes = computed(() => {
  const totalMinutes = totalReadTime.value
  return totalMinutes % 60
})

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
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

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.history-page {
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
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  margin-top: 20px;
}

.main-content h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 0;
  color: #303133;
}

.header-with-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.reading-summary {
  display: flex;
  align-items: center;
  gap: 12px;
}

.reading-summary .el-tag {
  font-size: 14px;
  padding: 6px 16px;
}

.novel-name-link {
  color: #303133;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s;
}

.novel-name-link:hover {
  color: #409EFF;
}

.history-table :deep(.el-table__header th) {
  text-align: center !important;
}

.history-table :deep(.el-table__body td) {
  text-align: center !important;
}

.history-table :deep(.el-table__cell) {
  text-align: center !important;
}

.history-table :deep(.el-table__row) {
  height: 100px;
}
</style>
