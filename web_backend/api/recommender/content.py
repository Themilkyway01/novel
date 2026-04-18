"""
内容相似度推荐模块
基于TF-IDF和余弦相似度计算小说相似度
"""
import random
import numpy as np
from django.core.cache import cache
from sklearn.metrics.pairwise import cosine_similarity

from .base import recommendation_engine


class ContentBasedRecommender:
    """基于内容的推荐器"""

    def __init__(self, engine):
        self.engine = engine

    def similar_novels(self, novel_id, n=10, same_category_priority=True):
        """
        相似小说推荐
        :param novel_id: 小说 ID
        :param n: 返回数量
        :param same_category_priority: 是否同类别优先
        """
        if self.engine.novel_info.empty:
            return []

        cache_key = f'similar_{novel_id}_{n}_{same_category_priority}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            novel_idx_rows = self.engine.novel_info[
                self.engine.novel_info['index'] == novel_id
            ]
            if len(novel_idx_rows) == 0:
                return []

            novel_idx = novel_idx_rows.index[0]
            target_novel = novel_idx_rows.iloc[0]
            target_category = target_novel.get('category', '')

            if not hasattr(self.engine, 'tfidf_matrix') or self.engine.tfidf_matrix is None:
                return []

            novel_vector = self.engine.tfidf_matrix[novel_idx]
            all_similarities = cosine_similarity(novel_vector, self.engine.tfidf_matrix).flatten()

            similarities = []
            for i, sim in enumerate(all_similarities):
                if i != novel_idx and sim > 0:
                    similarities.append((i, sim))

            if not similarities:
                return []

            if same_category_priority:
                same_cat_sims = []
                other_cat_sims = []

                for idx, sim in similarities:
                    novel_cat = self.engine.novel_info.iloc[idx].get('category', '')
                    if novel_cat == target_category:
                        same_cat_sims.append((idx, sim, 0))
                    else:
                        other_cat_sims.append((idx, sim, 1))

                same_cat_sims.sort(key=lambda x: x[1], reverse=True)
                other_cat_sims.sort(key=lambda x: x[1], reverse=True)

                same_cat_count = max(1, int(n * 0.8))
                top_indices = [idx for idx, _, _ in same_cat_sims[:same_cat_count]]
                top_indices += [idx for idx, _, _ in other_cat_sims[:n - len(top_indices)]]

                if len(top_indices) < n:
                    remaining = n - len(top_indices)
                    used_indices = set(top_indices)
                    all_sorted = sorted(
                        [(idx, sim) for idx, sim, _ in same_cat_sims + other_cat_sims
                         if idx not in used_indices],
                        key=lambda x: x[1], reverse=True
                    )
                    top_indices += [idx for idx, _ in all_sorted[:remaining]]
            else:
                similarities.sort(key=lambda x: x[1], reverse=True)
                top_indices = [idx for idx, _ in similarities[:n]]

            result = self.engine.novel_info.iloc[top_indices].to_dict('records')
            cache.set(cache_key, result, 60 * 60)
            return result

        except Exception as e:
            print(f"相似小说计算失败：{e}")
            return []

    def similar_novels_for_user(self, user_id, n=10, same_category_priority=True):
        """基于用户阅读历史的相似小说推荐"""
        user_reads = self.engine.get_user_reading_history(user_id)
        if not user_reads:
            return self.engine.get_hot_recommendations(user_id=user_id, n=n)

        recent_reads = user_reads[:5]
        all_similar = []

        for novel_id in recent_reads:
            similar = self.similar_novels(novel_id, n=5, same_category_priority=same_category_priority)
            all_similar.extend(similar)

        if not all_similar:
            return self.engine.get_hot_recommendations(user_id=user_id, n=n)

        novel_counts = {}
        for novel in all_similar:
            idx = novel['index']
            if idx not in user_reads:
                if idx not in novel_counts:
                    novel_counts[idx] = {'novel': novel, 'count': 0}
                novel_counts[idx]['count'] += 1

        sorted_novels = sorted(novel_counts.values(), key=lambda x: x['count'], reverse=True)
        return [item['novel'] for item in sorted_novels[:n]]


# 全局内容推荐实例
content_recommender = ContentBasedRecommender(recommendation_engine)
