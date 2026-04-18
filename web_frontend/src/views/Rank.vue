<template>
  <div class="rank-page">
    <!-- 导航栏 -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo" @click="goBack">
          <el-icon><Reading /></el-icon>
          <span>网文推荐系统</span>
        </div>
        <div class="nav-links">
          <el-link @click="goBack">返回</el-link>
          <el-link @click="$router.push('/')">首页</el-link>
        </div>
      </div>
    </el-header>

    <el-main class="main-content">
      <h2><el-icon><Trophy /></el-icon> 排行榜</h2>

      <el-tabs v-model="activeTab" @tab-change="loadRanking">
        <el-tab-pane label="总榜" name="all" />
        <el-tab-pane label="周榜" name="week" />
        <el-tab-pane label="男频榜" name="male" />
        <el-tab-pane label="女频榜" name="female" />
        <el-tab-pane label="出版榜" name="publish" />
      </el-tabs>

      <el-table :data="rankingList" style="width: 100%" class="ranking-table" @row-click="handleRowClick">
        <el-table-column type="index" label="排名" width="80">
          <template #default="{ $index }">
            <span :class="['rank-num', $index < 3 ? 'top-3' : '']">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="书名" min-width="200">
          <template #default="{ row }">
            <span class="novel-name-link">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="author" label="作者" min-width="100" />
        <el-table-column prop="category" label="分类" min-width="80" />
        <el-table-column prop="up_status" label="状态" min-width="80">
          <template #default="{ row }">
            {{ row.up_status === 1 ? '完本' : '连载' }}
          </template>
        </el-table-column>
        <el-table-column prop="all_recommend" label="总推荐" min-width="100" sortable>
          <template #default="{ row }">
            {{ formatNumber(row.all_recommend) }}
          </template>
        </el-table-column>
        <el-table-column prop="week_recommend" label="周推荐" min-width="100" sortable>
          <template #default="{ row }">
            {{ formatNumber(row.week_recommend) }}
          </template>
        </el-table-column>
        <el-table-column prop="wordcount" label="字数" min-width="100" sortable>
          <template #default="{ row }">
            {{ formatWordCount(row.wordcount) }}
          </template>
        </el-table-column>
      </el-table>
    </el-main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getHotNovels } from '@/api'

const router = useRouter()
const activeTab = ref('all')
const rankingList = ref([])

// 返回上一页
const goBack = () => {
  router.go(-1)
}

const loadRanking = async (tab) => {
  try {
    let params = { n: 100, random: false }

    if (tab === 'all') {
      // 总榜：按总推荐排序，不限制频道
      params.sort = 'all_recommend'
    } else if (tab === 'week') {
      // 周榜：按周推荐排序
      params.sort = 'week_recommend'
    } else if (tab === 'male') {
      // 男频榜：限制男频频道，按总推荐排序
      params.channel = 1
      params.sort = 'all_recommend'
    } else if (tab === 'female') {
      // 女频榜：限制女频频道，按总推荐排序
      params.channel = 0
      params.sort = 'all_recommend'
    } else if (tab === 'publish') {
      // 出版榜：限制出版频道，按总推荐排序
      params.channel = 2
      params.sort = 'all_recommend'
    }

    const res = await getHotNovels(params)
    rankingList.value = res
  } catch (error) {
    console.error('加载排行榜失败:', error)
  }
}

const formatWordCount = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + '千'
  }
  return num
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

// 处理表格行点击（左键同标签页，中键新标签页）
const handleRowClick = (row, column, event) => {
  if (event.button === 1) {
    // 中键点击，同标签页打开
    goToDetail(row.index)
  } else if (event.button === 0) {
    // 左键点击，新标签页打开
    goToDetailNewTab(row.index)
  }
}

onMounted(() => {
  loadRanking(activeTab.value)
})
</script>

<style scoped>
.rank-page {
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
  margin-bottom: 20px;
  color: #303133;
}

.rank-num {
  font-weight: bold;
  font-size: 16px;
}

.rank-num.top-3 {
  color: #FF9900;
  font-size: 18px;
}

.ranking-table {
  cursor: pointer;
}

.ranking-table :deep(.el-table__row) {
  transition: background-color 0.2s;
}

.ranking-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.novel-name-link {
  color: #000;
  text-decoration: none;
  font-weight: 500;
}

.novel-name-link:hover {
  text-decoration: none;
}

.ranking-table :deep(.el-table__row) {
  transition: background-color 0.2s;
}

.ranking-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

/* 让表格行铺满整个宽度 */
</style>
