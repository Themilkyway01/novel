<template>
  <div class="cold-start-page">
    <h1>新用户推荐</h1>
    <p class="subtitle">告诉我们您的偏好，我们为您推荐喜欢的小说</p>

    <div class="preference-form">
      <div class="form-group">
        <label>用户类型</label>
        <div class="radio-group">
          <label class="radio-label">
            <input type="radio" v-model.number="userCate" :value="1" />
            <span>男频</span>
          </label>
          <label class="radio-label">
            <input type="radio" v-model.number="userCate" :value="0" />
            <span>女频</span>
          </label>
          <label class="radio-label">
            <input type="radio" v-model.number="userCate" :value="2" />
            <span>出版</span>
          </label>
        </div>
      </div>

      <div class="form-group">
        <label>喜欢的分类（可多选）</label>
        <div class="category-checkboxes">
          <label
            v-for="cat in availableCategories"
            :key="cat"
            class="checkbox-label"
          >
            <input type="checkbox" :value="cat" v-model="selectedCategories" />
            <span>{{ cat }}</span>
          </label>
        </div>
      </div>

      <div class="form-group">
        <label>推荐数量</label>
        <select v-model.number="recommendCount">
          <option :value="5">5 本</option>
          <option :value="10">10 本</option>
          <option :value="20">20 本</option>
        </select>
      </div>

      <button @click="fetchRecommendations" :disabled="loading">
        {{ loading ? '加载中...' : '获取推荐' }}
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="recommendations.length > 0" class="results-section">
      <h2>为您推荐的好书</h2>
      <div class="recommendations-grid">
        <NovelCard
          v-for="novel in recommendations"
          :key="novel.novel_id || novel.id"
          :novel="novel"
        />
      </div>
    </div>

    <div v-else-if="!loading && searched" class="empty-state">
      <p>暂无符合条件的推荐，请尝试其他选择</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getColdStartRecommendations } from '@/api'
import NovelCard from '../components/NovelCard.vue'

const userCate = ref(1)
const selectedCategories = ref([])
const recommendCount = ref(10)
const loading = ref(false)
const error = ref('')
const recommendations = ref([])
const searched = ref(false)

const availableCategories = [
  '玄幻', '奇幻', '武侠', '仙侠', '都市', '职场',
  '军事', '历史', '游戏', '竞技', '科幻', '灵异',
  '悬疑', '轻小说', '短篇', '言情', '穿越', '耽美'
]

const fetchRecommendations = async () => {
  loading.value = true
  error.value = ''
  searched.value = true

  try {
    const response = await getColdStartRecommendations(
      userCate.value,
      selectedCategories.value,
      recommendCount.value
    )
    recommendations.value = response.data.recommendations || []
  } catch (err) {
    error.value = err.response?.data?.error || '获取推荐失败'
    recommendations.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.cold-start-page {
  max-width: 900px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 8px;
}

.subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 40px;
}

.preference-form {
  background: white;
  padding: 32px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  margin-bottom: 32px;
}

.form-group {
  margin-bottom: 24px;
}

.form-group > label {
  display: block;
  font-weight: 500;
  margin-bottom: 12px;
  color: #333;
}

.radio-group {
  display: flex;
  gap: 24px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.radio-label input {
  width: 18px;
  height: 18px;
}

.category-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #f5f5f5;
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.checkbox-label:hover {
  background: #eee;
}

.checkbox-label input {
  width: 16px;
  height: 16px;
}

.form-group select {
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  min-width: 150px;
}

button {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
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

.error-message {
  background: #fee;
  color: #c33;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.results-section {
  margin-top: 40px;
}

.results-section h2 {
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
</style>
