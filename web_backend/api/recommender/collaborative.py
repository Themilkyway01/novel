"""
协同过滤推荐模块
处理基于用户行为的协同过滤推荐
"""
import numpy as np
from django.core.cache import cache

from .base import recommendation_engine


class CollaborativeFiltering:
    """协同过滤推荐器"""

    def __init__(self, engine):
        self.engine = engine

    def get_user_profile(self, user_id):
        """获取用户画像向量"""
        try:
            from api.models import UserBehavior
            user_behaviors = UserBehavior.objects.filter(user_id=user_id).values_list(
                'novel_id', flat=True
            )
            user_read = list(user_behaviors)

            if not user_read:
                return None

            idx_list = self.engine.novel_info[
                self.engine.novel_info['index'].isin(user_read)
            ].index

            if len(idx_list) == 0:
                return None

            user_profile = self.engine.tfidf_matrix[idx_list].mean(axis=0)
            return np.asarray(user_profile).reshape(1, -1)
        except Exception as e:
            print(f"获取用户画像失败: {e}")
            return None

    def recommend_for_user(self, user_id, n=10, channel=None, category=None):
        """
        为已登录用户推荐
        使用协同过滤模型预测用户对未读书籍的评分
        """
        if self.engine.model is None or self.engine.novel_info.empty:
            return []

        cache_key = f'recommend_user_{user_id}_{n}_{channel}_{category}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        read_items = self.engine.get_user_reading_history(user_id)
        all_items = self.engine.novel_info['index'].tolist()
        candidates = [item for item in all_items if item not in read_items]

        if not candidates:
            return []

        candidates_df = self.engine.novel_info[
            self.engine.novel_info['index'].isin(candidates)
        ]
        if channel is not None:
            candidates_df = candidates_df[candidates_df['cate'] == channel]
        if category is not None:
            candidates_df = candidates_df[candidates_df['category'] == category]

        candidates = candidates_df['index'].tolist()

        if not candidates:
            return []

        predictions = []
        for item_id in candidates[:500]:
            try:
                pred = self.engine.model.predict(
                    uid=user_id, iid=int(item_id)
                ).est
                predictions.append((int(item_id), pred))
            except Exception:
                continue

        if not predictions:
            return self.engine.get_hot_recommendations(user_id, channel, category, n)

        predictions.sort(key=lambda x: x[1], reverse=True)
        top_ids = [item[0] for item in predictions[:n * 2]]

        rec_novels = self.engine.novel_info[
            self.engine.novel_info['index'].isin(top_ids)
        ]

        user_gender = self.engine.user_gender_map.get(user_id)
        if user_gender is not None and user_gender in [0, 1, 2]:
            rec_novels = rec_novels[rec_novels['cate'] == user_gender]

        result = self.engine._apply_diversity_factor(
            rec_novels.to_dict('records'), user_id, n, channel, category
        )

        cache.set(cache_key, result, 60 * 30)
        return result


# 全局协同过滤实例
cf_recommender = CollaborativeFiltering(recommendation_engine)
