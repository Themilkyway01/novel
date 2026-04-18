<template>
  <div class="recommend-page">
    <h1>个性化推荐</h1>

    <div class="user-input-section">
      <div class="input-group">
        <label>用户 ID</label>
        <input
          v-model.number="userId"
          type="number"
          placeholder="请输入用户ID"
          min="1"
        />
      </div>
      <div class="input-group">
        <label>推荐数量</label>
        <select v-model.number="recommendCount">
          <option :value="5">5 本</option>
          <option :value="10">10 本</option>
          <option :value="20">20 本</option>
          <option :value="30">30 本</option>
        </select>
      </div>
      <div class="input-group">
        <label>推荐方式</label>
        <select v-model="useHybrid">
          <option :value="true">混合推荐</option>
          <option :value="false">协同过滤</option>
        </select>
      </div>
      <button @click="fetchRecommendations" :disabled="loading || !userId">
        {{ loading ? '加载中...' : '获取推荐' }}
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="recommendations.length > 0" class="recommendations-section">
      <h2>为您推荐</h2>
      <div class="recommendations-grid">
        <NovelCard
          v-for="novel in recommendations"
          :key="novel.novel_id || novel.id"
          :novel="novel"
        />
      </div>
    </div>

    <div v-else-if="!loading && searched" class="empty-state">
      <p>暂无推荐结果，请尝试其他用户ID</p>
    </div>

    <div class="new-books-section">
      <h2>新书推荐</h2>
      <button @click="fetchNewBooks" :disabled="loading || !userId" class="btn-secondary">
        查看最新上架
      </button>
      <div v-if="newBooks.length > 0" class="recommendations-grid">
        <NovelCard
          v-for="novel in newBooks"
          :key="novel.novel_id || novel.id"
          :novel="novel"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getRecommendations, getNewBookRecommendations } from '@/api'
import NovelCard from '../components/NovelCard.vue'

const userId = ref(null)
const recommendCount = ref(10)
const useHybrid = ref(true)
const loading = ref(false)
const error = ref('')
const recommendations = ref([])
const newBooks = ref([])
const searched = ref(false)

const fetchRecommendations = async () => {
  if (!userId.value) return

  loading.value = true
  error.value = ''
  searched.value = true

  try {
    const response = await getRecommendations(
      userId.value,
      recommendCount.value,
      useHybrid.value
    )
    recommendations.value = response.data.recommendations || []
  } catch (err) {
    error.value = err.response?.data?.error || '获取推荐失败，请检查用户ID是否正确'
    recommendations.value = []
  } finally {
    loading.value = false
  }
}

const fetchNewBooks = async () => {
  if (!userId.value) return

  loading.value = true
  error.value = ''

  try {
    const response = await getNewBookRecommendations(userId.value, 6)
    newBooks.value = response.data.recommendations || []
  } catch (err) {
    error.value = err.response?.data?.error || '获取新书推荐失败'
    newBooks.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.recommend-page {
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 32px;
}

.user-input-section {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  margin-bottom: 32px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-weight: 500;
  color: #666;
}

.input-group input,
.input-group select {
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  min-width: 150px;
}

button {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: opacity 0.2s;
}

button:hover:not(:disabled) {
  opacity: 0.9;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #666;
  margin: 16px 0;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.recommendations-section,
.new-books-section {
  margin-top: 48px;
}

.recommendations-section h2,
.new-books-section h2 {
  margin-bottom: 24px;
}

.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #999;
  background: #f5f5f5;
  border-radius: 12px;
}

@media (max-width: 768px) {
  .user-input-section {
    flex-direction: column;
    align-items: stretch;
  }

  .input-group input,
  .input-group select {
    width: 100%;
  }
}
</style>
