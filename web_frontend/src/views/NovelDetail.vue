<template>
  <div class="novel-detail">
    <!-- 顶部导航（复用 Home 的导航） -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo" @click="goBack">
          <el-icon><Reading /></el-icon>
          <span>网文推荐系统</span>
        </div>
        <div class="nav-links">
          <el-link @click="$router.push('/')">首页</el-link>
        </div>
      </div>
    </el-header>

    <el-main class="main-content" v-if="novel">
      <el-row :gutter="30">
        <!-- 左侧：封面 -->
        <el-col :xs="24" :md="8">
          <div class="novel-cover">
            <el-image :src="novel.img || '/placeholder.jpg'" fit="cover" />
          </div>
        </el-col>

        <!-- 右侧：书籍信息 -->
        <el-col :xs="24" :md="16">
          <h1 class="novel-name">{{ novel.name }}</h1>
          
          <div class="novel-meta">
            <el-tag>{{ novel.cate_display }}</el-tag>
            <el-tag type="success">{{ novel.category }}</el-tag>
            <el-tag type="warning">{{ novel.sub_category }}</el-tag>
            <el-tag :type="novel.up_status_display === '完本' ? 'info' : 'success'">
              {{ novel.up_status_display }}
            </el-tag>
            <el-tag :type="novel.signed_display === '签约' ? 'danger' : 'info'">
              {{ novel.signed_display }}
            </el-tag>
          </div>
          
          <div class="info-list">
            <p><strong>作者：</strong><a :href="`/category?keyword=${encodeURIComponent(novel.author)}`" target="_blank" class="author-link">{{ novel.author }}</a></p>
            <p><strong>字数：</strong>{{ formatWordCount(novel.wordcount) }}</p>
            <p><strong>章节数：</strong>{{ novel.chapters }}</p>
            <p><strong>总推荐：</strong>{{ novel.all_recommend }}</p>
            <p><strong>周推荐：</strong>{{ novel.week_recommend }}</p>
            <p><strong>更新时间：</strong>{{ formatTime(novel.up_time) }}</p>
            <p><strong>最新章节：</strong>{{ novel.up_chapter }}</p>
            
            <!-- 操作按钮：开始阅读、推荐、评分 -->
            <el-row class="action-row">
              <el-button type="primary" size="large" @click="handleRead">
                <el-icon><ReadingLamp /></el-icon> 开始阅读
              </el-button>
              <el-button @click="handleRate(5)">
                <el-icon><Star /></el-icon> 推荐
              </el-button>
              <el-button @click="showDialog = true">
                <el-icon><ChatDotRound /></el-icon> 评分
              </el-button>
            </el-row>
          </div>
        </el-col>
      </el-row>

      <!-- 简介模块：占满整行 -->
      <div class="introduction full-width">
        <h3>简介</h3>
        <p>{{ novel.introduction }}</p>
      </div>

      <!-- 相似推荐 -->
      <div class="section" style="margin-top: 40px">
        <h3><el-icon><Star /></el-icon> 相似小说推荐</h3>
        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :xs="12" :sm="8" :md="6" :lg="4" v-for="item in similarNovels.slice(0, 12)" :key="item.novel_id || item.index">
            <div class="novel-card" @click.middle="goToDetail(item.novel_id || item.index)" @click="goToDetailNewTab(item.novel_id || item.index)">
              <el-image :src="item.img || '/placeholder.jpg'" fit="cover" />
              <div class="novel-info">
                <div class="novel-name">{{ item.name }}</div>
                <div class="novel-author">{{ item.author }}</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </el-main>

    <!-- 评分对话框 -->
    <el-dialog v-model="showDialog" title="评分" width="300px">
      <el-rate v-model="ratingValue" :colors="['#99A9BF', '#F7BA2A', '#FF9900']" />
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submitRating">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getNovelDetail, getSimilarNovels, recordBehavior, submitRating as apiSubmitRating } from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const novel = ref(null)
const similarNovels = ref([])
const showDialog = ref(false)
const ratingValue = ref(0)

// 加载小说详情
const loadNovelDetail = async () => {
  try {
    const res = await getNovelDetail(route.params.id)
    novel.value = res
    // 设置页面标题为小说标题
    document.title = res.name || '网文推荐系统'
  } catch (error) {
    console.error('加载小说详情失败:', error)
    ElMessage.error('小说不存在')
  }
}

// 加载相似推荐
const loadSimilarNovels = async () => {
  try {
    const res = await getSimilarNovels(route.params.id)
    similarNovels.value = res
    console.log('相似小说数据:', res)
    if (res && res.length > 0) {
      console.log('第一个相似小说的 ID 字段:', res[0].novel_id, res[0].index)
    }
  } catch (error) {
    console.error('加载相似推荐失败:', error)
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      ElMessage.warning('相似推荐加载超时，请稍后重试')
    } else {
      ElMessage.warning('暂时无法加载相似推荐')
    }
  }
}

// 开始阅读
const handleRead = () => {
  if (userStore.isLoggedIn) {
    // 记录阅读行为（随机阅读时长 25-35 分钟）
    const randomTime = 30 + Math.floor(Math.random() * 11) - 5
    recordBehavior({ novel_id: route.params.id, read_time: randomTime })
    ElMessage.success('已添加到阅读历史')
  } else {
    ElMessage.warning('请先登录后阅读')
    router.push('/login')
  }
}

// 评分
const handleRate = (rating) => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }
  apiSubmitRating({ novel_id: route.params.id, rating })
    .then(() => {
      ElMessage.success('评分成功，已添加到阅读历史')
    })
    .catch(err => {
      console.error('评分失败:', err)
    })
}

// 提交评分
const submitRating = () => {
  if (ratingValue.value === 0) {
    ElMessage.warning('请选择评分')
    return
  }
  handleRate(ratingValue.value)
  showDialog.value = false
}

// 返回上一页
const goBack = () => {
  router.go(-1)
}

// 跳转详情
const goToDetail = (novelId) => {
  console.log('点击相似小说，ID:', novelId)
  if (!novelId) {
    console.error('Invalid novel ID:', novelId)
    ElMessage.error('小说 ID 无效')
    return
  }
  router.push(`/novel/${novelId}`)
}

// 新标签页打开详情
const goToDetailNewTab = (novelId) => {
  console.log('新标签页打开相似小说，ID:', novelId)
  if (!novelId) {
    console.error('Invalid novel ID:', novelId)
    ElMessage.error('小说 ID 无效')
    return
  }
  const routeUrl = router.resolve({
    path: `/novel/${novelId}`
  })
  window.open(routeUrl.href, '_blank')
}

// 格式化字数
const formatWordCount = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadNovelDetail()
  loadSimilarNovels()
})
</script>

<style scoped>
.novel-detail {
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

.novel-cover {
  margin-bottom: 15px;
}

.novel-cover :deep(.el-image) {
  width: 100%;
  max-width: 300px;
  height: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 20px;
}

.action-row .el-button {
  min-width: 100px;
  height: 40px;
  font-size: 14px;
}

.novel-name {
  font-size: 24px;
  color: #303133;
  margin-bottom: 15px;
}

.novel-meta {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.info-list p {
  margin: 10px 0;
  color: #606266;
}

.author-link {
  color: #303133;
  text-decoration: none;
  cursor: pointer;
}

.author-link:hover {
  text-decoration: none;
}

.introduction {
  margin-top: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.introduction.full-width {
  width: 100%;
}

.introduction h3 {
  margin-bottom: 10px;
  color: #303133;
}

.introduction p {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.section {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.section h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #303133;
}

.novel-card {
  cursor: pointer;
  transition: transform 0.3s;
  margin-bottom: 20px;
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

.novel-info .novel-name {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.novel-author {
  font-size: 12px;
  color: #909399;
}
</style>
