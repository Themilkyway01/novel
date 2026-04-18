"""
推荐系统 API 接口
提供统一的推荐服务接口，供 Web 后端调用
"""
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict

from recommender import Recommender, UserProfileManager


class RecommendationAPI:
    """推荐系统 API - 封装所有推荐场景"""
    
    def __init__(self, recommender: Recommender, user_profile_manager: UserProfileManager):
        self.recommender = recommender
        self.user_profile_manager = user_profile_manager
        self._user_channel_preference = {}
        self._user_category_preference = {}
    
    def set_user_preference(self, user_id: int, channel: Optional[int] = None,
                            category: Optional[str] = None):
        """设置用户频道/分类偏好"""
        if channel is not None:
            self._user_channel_preference[user_id] = channel
        if category is not None:
            self._user_category_preference[user_id] = category
    
    def clear_user_preference(self, user_id: int, clear_channel: bool = True,
                              clear_category: bool = True):
        """清除用户偏好"""
        if clear_channel:
            self._user_channel_preference.pop(user_id, None)
        if clear_category:
            self._user_category_preference.pop(user_id, None)
    
    def get_user_preference(self, user_id: int) -> Dict:
        """获取用户偏好"""
        return {
            'channel': self._user_channel_preference.get(user_id),
            'category': self._user_category_preference.get(user_id)
        }
    
    def _get_user_filters(self, user_id: Optional[int], channel: Optional[int] = None,
                          category: Optional[str] = None) -> tuple:
        """获取用户过滤条件（偏好或画像）"""
        if user_id is not None:
            if channel is None:
                channel = self._user_channel_preference.get(user_id)
            if category is None:
                category = self._user_category_preference.get(user_id)
        return channel, category
    
    def get_hot_recommendations(self, user_id: Optional[int] = None,
                                channel: Optional[int] = None,
                                category: Optional[str] = None,
                                n: int = 12) -> List[Dict]:
        """热门推荐"""
        channel, category = self._get_user_filters(user_id, channel, category)
        recs = self.recommender.recommend(
            user_id=user_id, channel=channel, category=category, n=n, recommendation_type='hot'
        )
        return self._format_recommendations(recs)
    
    def get_latest_recommendations(self, user_id: Optional[int] = None,
                                   channel: Optional[int] = None,
                                   category: Optional[str] = None,
                                   n: int = 12, days: int = 30) -> List[Dict]:
        """最新更新推荐"""
        channel, category = self._get_user_filters(user_id, channel, category)
        recs = self.recommender.get_latest_updates(
            channel=channel, category=category, n=n, days=days
        )
        return self._format_recommendations(recs)
    
    def get_personalized_recommendations(self, user_id: int,
                                         channel: Optional[int] = None,
                                         category: Optional[str] = None,
                                         n: int = 12,
                                         use_diversity: bool = True) -> List[Dict]:
        """个性化推荐"""
        channel, category = self._get_user_filters(user_id, channel, category)
        recs = self.recommender.recommend(
            user_id=user_id, channel=channel, category=category,
            n=n, use_diversity=use_diversity
        )
        return self._format_recommendations(recs)
    
    def get_similar_recommendations(self, user_id: int, n: int = 10) -> List[Dict]:
        """相似小说推荐（基于用户历史）"""
        recs = self.recommender.recommend(user_id=user_id, n=n, recommendation_type='similar')
        return self._format_recommendations(recs)
    
    def get_similar_novels_by_id(self, novel_id: int, n: int = 5) -> List[Dict]:
        """根据小说 ID 获取相似小说"""
        recs = self.recommender.get_similar_novels(novel_id, n)
        return self._format_recommendations(recs)
    
    def refresh_hot_recommendations(self, user_id: Optional[int] = None,
                                    channel: Optional[int] = None,
                                    category: Optional[str] = None,
                                    n: int = 12) -> List[Dict]:
        """刷新热门推荐（换一批）"""
        return self.get_hot_recommendations(user_id, channel, category, n)
    
    def refresh_latest_recommendations(self, user_id: Optional[int] = None,
                                       channel: Optional[int] = None,
                                       category: Optional[str] = None,
                                       n: int = 12, days: int = 30) -> List[Dict]:
        """刷新最新更新（换一批）"""
        return self.get_latest_recommendations(user_id, channel, category, n, days)
    
    def update_user_behavior(self, user_id: int, novel_id: int, rating: float,
                             read_time: int = 0, created_at: Optional[datetime] = None):
        """更新用户行为（增量更新画像）"""
        new_behavior = pd.DataFrame([{
            'user_id': user_id, 'novel_id': novel_id, 'rating': rating,
            'read_time': read_time, 'created_at': created_at or datetime.now()
        }])
        self.user_profile_manager.update_user_behavior(user_id, new_behavior)
    
    def get_user_profile(self, user_id: int) -> Dict:
        """获取用户画像摘要"""
        profile = self.user_profile_manager.get_user_profile(user_id)
        return profile.get_profile_summary()
    
    def _format_recommendations(self, recs_df: pd.DataFrame) -> List[Dict]:
        """格式化推荐结果"""
        if recs_df.empty:
            return []
        
        result = []
        for _, row in recs_df.iterrows():
            result.append({
                'novel_id': row.get('novel_id'),
                'name': row.get('name', ''),
                'category': row.get('category', ''),
                'sub_category': row.get('sub_category', ''),
                'channel': row.get('cate', row.get('channel', 2)),
                'author': row.get('author', ''),
                'cover_url': row.get('cover_url', ''),
                'description': row.get('description', ''),
                'score': row.get('hybrid_score', row.get('similarity_score', 0))
            })
        return result


def load_recommendation_api(model_path: str, tfidf_path: str,
                            novel_info: pd.DataFrame, filtered_data: pd.DataFrame,
                            user_gender_map: Dict) -> RecommendationAPI:
    """加载推荐系统 API"""
    user_profile_manager = UserProfileManager(novel_info, filtered_data)
    recommender = Recommender.load(
        model_path, tfidf_path, novel_info, filtered_data,
        user_gender_map, user_profile_manager=user_profile_manager
    )
    return RecommendationAPI(recommender, user_profile_manager)
