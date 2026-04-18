/**
 * API 封装模块
 * 统一管理所有后端 API 调用
 */
import request from '@/utils/request'

// ==================== 认证相关 ====================

/**
 * 用户登录
 */
export function login(username, password) {
  return request.post('/api/auth/login/', { username, password })
}

/**
 * 用户注册
 */
export function register(data) {
  return request.post('/api/auth/register/', data)
}

/**
 * 获取用户信息
 */
export function getUserProfile() {
  return request.get('/api/auth/profile/')
}

/**
 * 更新用户资料
 */
export function updateProfile(data) {
  return request.put('/api/auth/profile/update/', data)
}

/**
 * 保存用户偏好设置
 */
export function saveUserPreferences(data) {
  return request.post('/api/auth/preferences/save/', data)
}

/**
 * 删除账户
 */
export function deleteAccount(password) {
  return request.post('/api/auth/delete-account/', { password })
}

// ==================== 小说相关 ====================

/**
 * 获取小说列表
 */
export function getNovelList(params = {}) {
  return request.get('/api/novels/', { params })
}

/**
 * 获取小说详情
 */
export function getNovelDetail(novelId) {
  return request.get(`/api/novels/${novelId}/`)
}

/**
 * 获取分类列表
 */
export function getCategories(params = {}) {
  return request.get('/api/novels/categories/', { params })
}

/**
 * 获取子分类列表
 */
export function getSubCategories(params = {}) {
  return request.get('/api/novels/sub-categories/', { params })
}

/**
 * 获取分类树
 */
export function getCategoriesTree(params = {}) {
  return request.get('/api/categories/tree/', { params })
}

/**
 * 获取相似小说
 */
export function getSimilarNovels(novelId, params = {}) {
  return request.get(`/api/novels/${novelId}/similar/`, { params })
}

/**
 * 搜索建议
 */
export function getSearchSuggestions(keyword, limit = 10) {
  return request.get('/api/search/suggestions/', { params: { keyword, limit } })
}

// ==================== 推荐相关 ====================

/**
 * 获取热门推荐
 */
export function getHotNovels(params = {}) {
  return request.get('/api/hot/', { params })
}

/**
 * 获取最新更新
 */
export function getRecentNovels(params = {}) {
  return request.get('/api/recent/', { params })
}

/**
 * 获取个性化推荐（已登录用户）
 */
export function getPersonalRecommend(params = {}) {
  return request.get('/api/recommend/personal/', { params })
}

/**
 * 获取通用推荐
 */
export function getRecommendations(params = {}) {
  return request.get('/api/recommend/', { params })
}

/**
 * 冷启动推荐（新用户）
 */
export function getColdStartRecommendations(params = {}) {
  return request.get('/api/recommend/', {
    params: { ...params, type: 'cold_start' }
  })
}

/**
 * 新书推荐
 */
export function getNewBookRecommendations(params = {}) {
  return request.get('/api/recommend/', {
    params: { ...params, type: 'new' }
  })
}

/**
 * 获取用户偏好
 */
export function getUserPreferences(userId) {
  return request.get('/api/user/preferences/', { params: { user_id: userId } })
}

// ==================== 用户行为相关 ====================

/**
 * 获取阅读历史
 */
export function getReadingHistory() {
  return request.get('/api/user/history/')
}

/**
 * 记录用户行为（阅读）
 */
export function recordBehavior(data) {
  return request.post('/api/behaviors/', data)
}

/**
 * 用户评分
 */
export function submitRating(data) {
  return request.post('/api/ratings/', data)
}
