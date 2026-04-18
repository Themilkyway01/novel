<template>
  <div class="novel-card" @click.middle="handleMiddleClick" @click="handleClick">
    <el-image :src="novel.img || '/placeholder.jpg'" fit="cover" />
    <div class="novel-info">
      <div class="novel-name">{{ novel.name }}</div>
      <div class="novel-author">{{ novel.author }}</div>
      <div v-if="novel.category" class="novel-tags">
        <el-tag size="small">{{ novel.category }}</el-tag>
      </div>
      <div v-if="novel.up_chapter" class="novel-update">{{ novel.up_chapter }}</div>
      <div v-if="novel.up_time" class="novel-time">{{ formatTime(novel.up_time) }}</div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  novel: {
    type: Object,
    required: true
  }
})

const router = useRouter()

const handleClick = () => {
  const novelId = props.novel.novel_id || props.novel.index || props.novel.id
  const routeUrl = router.resolve({
    path: `/novel/${novelId}`
  })
  window.open(routeUrl.href, '_blank')
}

const handleMiddleClick = () => {
  const novelId = props.novel.novel_id || props.novel.index || props.novel.id
  router.push(`/novel/${novelId}`)
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.novel-card {
  cursor: pointer;
  transition: transform 0.3s;
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

.novel-tags {
  margin-top: 5px;
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
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
</style>
