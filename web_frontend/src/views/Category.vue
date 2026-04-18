<template>
  <div class="category-page">
    <!-- 导航栏（同 Home） -->
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
          <el-link @click="$router.push('/')">首页</el-link>
        </div>
      </div>
    </el-header>

    <el-main class="main-content">
      <!-- 筛选条件（搜索模式下隐藏） -->
      <el-card class="filter-card" v-if="!isSearchMode">
        <el-form :inline="true">
          <el-form-item label="频道">
            <el-select v-model="filters.cate" placeholder="全部" clearable @change="handleCateChange">
              <el-option label="全部" :value="undefined" />
              <el-option label="男频" :value="1" />
              <el-option label="女频" :value="0" />
              <el-option label="出版" :value="2" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="分类">
            <el-select v-model="filters.category" placeholder="全部" clearable @change="handleCategoryChange">
              <el-option label="全部" :value="undefined" />
              <el-option
                v-for="cat in categories"
                :key="cat.category"
                :label="cat.category"
                :value="cat.category"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="子分类">
            <el-select 
              v-model="filters.sub_category" 
              placeholder="全部" 
              clearable 
              :disabled="isPublishMode"
              @change="loadNovels"
            >
              <el-option label="全部" :value="undefined" />
              <el-option
                v-for="subCat in subCategories"
                :key="subCat"
                :label="subCat"
                :value="subCat"
                v-if="!isPublishMode"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="连载状态">
            <el-select 
              v-model="filters.up_status" 
              placeholder="全部" 
              clearable 
              :disabled="isPublishMode"
              @change="loadNovels"
            >
              <el-option label="全部" :value="undefined" />
              <el-option label="连载" :value="0" v-if="!isPublishMode" />
              <el-option label="完本" :value="1" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="排序">
            <el-select v-model="filters.sort" placeholder="全部" clearable @change="loadNovels">
              <el-option label="全部" :value="undefined" />
              <el-option label="总推荐" value="all_recommend" />
              <el-option label="周推荐" value="week_recommend" />
              <el-option label="字数" value="wordcount" />
              <el-option label="更新时间" value="up_time" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 小说列表 -->
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :xs="12" :sm="8" :md="6" :lg="4" v-for="novel in novels" :key="novel.index">
          <div class="novel-card" @click.middle="goToDetail(novel.index)" @click="goToDetailNewTab(novel.index)">
            <el-image :src="novel.img || '/placeholder.jpg'" fit="cover" />
            <div class="novel-info">
              <div class="novel-name">{{ novel.name }}</div>
              <div class="novel-author">{{ novel.author }}</div>
              <div class="novel-desc">{{ novel.introduction?.substring(0, 60) }}...</div>
              <div class="novel-tags">
                <el-tag size="small">{{ novel.category }}</el-tag>
                <el-tag size="small" type="success">{{ novel.sub_category }}</el-tag>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="handlePageChange"
        style="margin-top: 30px; justify-content: center; display: flex"
      />
    </el-main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getNovelList, getCategories, getSearchSuggestions } from '@/api'

const router = useRouter()
const route = useRoute()

const searchKeyword = ref('')
const searchSuggestions = ref([])
const showSuggestions = ref(false)
let searchTimeout = null
const categories = ref([])
const novels = ref([])
const currentPage = ref(1)
const pageSize = ref(24)
const total = ref(0)

const filters = reactive({
  cate: undefined,
  category: undefined,
  sub_category: undefined,
  up_status: undefined,
  sort: undefined
})

const subCategories = ref([])

// 判断是否为出版模式（禁用连载状态选择）
const isPublishMode = computed(() => filters.cate === 2)

// 判断是否为搜索模式（有关键词时隐藏筛选栏）
const isSearchMode = computed(() => !!route.query.keyword)

// 加载分类（仅在选择了频道时加载）
const loadCategories = async () => {
  // 未选择频道时，分类只显示"全部"
  if (filters.cate === undefined) {
    categories.value = []
    filters.category = undefined
    filters.sub_category = undefined
    subCategories.value = []
    return
  }
  
  try {
    const params = { cate: filters.cate }
    const res = await getCategories(params)
    categories.value = res || []
    
    // 如果当前已选择分类，但不在新的分类列表中，则清空分类选择
    if (filters.category && !categories.value.some(cat => cat.category === filters.category)) {
      console.log(`分类 "${filters.category}" 不属于当前选择的频道，已清空`)
      filters.category = undefined
      filters.sub_category = undefined
      subCategories.value = []
    }
  } catch (error) {
    console.error('加载分类失败:', error)
    categories.value = []
  }
}

// 处理频道变化，重置分类和子分类
const handleCateChange = async () => {
  // 重置分类和子分类
  filters.category = undefined
  filters.sub_category = undefined
  subCategories.value = []
  
  // 如果选择了出版，连载状态固定为完结
  if (filters.cate === 2) {
    filters.up_status = 1
  } else {
    // 如果不是出版，清空连载状态（除非用户手动设置）
    filters.up_status = undefined
  }
  
  // 重新加载分类（根据频道过滤）
  await loadCategories()
  loadNovels()
}

// 加载小说列表
const loadNovels = async () => {
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      ...filters
    }
    
    if (route.query.keyword) {
      params.keyword = route.query.keyword
    }
    
    const res = await getNovelList(params)
    novels.value = res.results || res
    total.value = res.count || novels.value.length
  } catch (error) {
    console.error('加载小说列表失败:', error)
  }
}

// 处理分页变化，翻页后自动滚动到顶部
const handlePageChange = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
  loadNovels()
}

// 处理分类变化，加载对应的子分类
const handleCategoryChange = async () => {
  filters.sub_category = undefined // 重置子分类选择
  await loadSubCategories()
  loadNovels()
}

// 加载子分类
const loadSubCategories = async () => {
  // 出版模式下不加载子分类，固定为全部
  if (!filters.category || isPublishMode.value) {
    subCategories.value = []
    return
  }
  
  try {
    // 通过 API 获取子分类，这里使用 getNovelList 获取所有该分类的小说并提取子分类
    const params = {
      page: 1,
      page_size: 100,
      category: filters.category
    }
    
    // 必须有频道筛选，确保子分类属于正确的频道
    if (filters.cate !== undefined) {
      params.cate = filters.cate
    } else {
      // 如果没有选择频道，先查询该分类所属的频道
      const probeRes = await getNovelList({ page: 1, page_size: 1, category: filters.category })
      const probeNovels = probeRes.results || probeRes
      if (probeNovels.length > 0) {
        params.cate = probeNovels[0].cate
      }
    }
    
    const res = await getNovelList(params)
    const novelsList = res.results || res
    
    // 提取唯一的子分类
    const uniqueSubCats = [...new Set(novelsList.map(novel => novel.sub_category).filter(Boolean))]
    subCategories.value = uniqueSubCats
  } catch (error) {
    console.error('加载子分类失败:', error)
    subCategories.value = []
  }
}

// 当分类被选择时，如果频道未选择，自动推断可能的频道
watch(() => filters.category, async (newVal) => {
  if (newVal && filters.cate === undefined) {
    // 查询该分类所属的频道
    try {
      const params = {
        page: 1,
        page_size: 1,
        category: newVal
      }
      const res = await getNovelList(params)
      const novelsList = res.results || res
      if (novelsList.length > 0) {
        // 自动设置频道为该分类所属的频道
        filters.cate = novelsList[0].cate
        // 如果频道是出版，连载状态固定为完结，子分类固定为全部
        if (filters.cate === 2) {
          filters.up_status = 1
          filters.sub_category = undefined
          subCategories.value = []
        }
        // 重新加载分类列表以高亮显示正确的频道
        await loadCategories()
      }
    } catch (error) {
      console.error('获取分类所属频道失败:', error)
    }
  }
})

// 当子分类被选择时，如果频道未选择，自动推断可能的频道
watch(() => filters.sub_category, async (newVal) => {
  if (newVal && filters.cate === undefined) {
    // 查询该子分类所属的频道
    try {
      const params = {
        page: 1,
        page_size: 1,
        sub_category: newVal
      }
      const res = await getNovelList(params)
      const novelsList = res.results || res
      if (novelsList.length > 0) {
        // 自动设置频道为该子分类所属的频道
        filters.cate = novelsList[0].cate
        // 如果频道是出版，连载状态固定为完结，子分类固定为全部
        if (filters.cate === 2) {
          filters.up_status = 1
          filters.sub_category = undefined
          subCategories.value = []
        }
        // 重新加载分类列表以高亮显示正确的频道
        await loadCategories()
      }
    } catch (error) {
      console.error('获取子分类所属频道失败:', error)
    }
  }
})

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
    // 点击作品，跳转到详情页（新标签页）
    const routeUrl = router.resolve({
      path: `/novel/${item.id}`
    })
    window.open(routeUrl.href, '_blank')
  } else if (item.type === 'author') {
    // 点击作者，跳转到分类页并按作者搜索（新标签页）
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
    // 点击作品，跳转到详情页
    router.push(`/novel/${item.id}`)
  } else if (item.type === 'author') {
    // 点击作者，跳转到分类页并按作者搜索
    router.push({ path: '/category', query: { keyword: item.author } })
  }
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
  // 从 URL 参数初始化搜索关键词
  if (route.query.keyword) {
    searchKeyword.value = route.query.keyword
  }
  loadCategories()
  loadNovels()
})

// 监听路由 keyword 变化，重新加载小说列表
watch(() => route.query.keyword, (newKeyword) => {
  if (newKeyword) {
    searchKeyword.value = newKeyword
  } else {
    searchKeyword.value = ''
  }
  currentPage.value = 1
  loadNovels()
})
</script>

<style scoped>
.category-page {
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
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
}

.filter-card {
  margin-top: 20px;
}

.filter-card :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
  flex: 1;
}

.filter-card :deep(.el-select) {
  width: 100%;
}

/* 让所有筛选条件在一行显示并铺满整行 */
.filter-card :deep(.el-form) {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 24px;
  justify-content: flex-start;
}

.filter-card :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-card :deep(.el-form-label) {
  min-width: 70px;
  text-align: right;
  padding-right: 12px;
  color: #606266;
  font-weight: 500;
}

.filter-card :deep(.el-select) {
  width: 140px;
}

.novel-card {
  cursor: pointer;
  transition: transform 0.3s;
  margin-bottom: 20px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.novel-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.novel-card :deep(.el-image) {
  width: 100%;
  height: 200px;
}

.novel-info {
  padding: 12px;
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
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.novel-tags {
  display: flex;
  gap: 5px;
}
</style>
