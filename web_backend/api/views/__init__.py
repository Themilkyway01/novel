"""
视图模块

包含以下子模块：
- auth.py         : 认证相关（登录、注册、用户信息）
- novels.py       : 小说相关（列表、详情、搜索）
- recommendations.py : 推荐相关（热门、最新、个性化）
- behaviors.py    : 用户行为（阅读记录、评分）
"""
from .auth import (
    UserViewSet, login_view, register_view,
    user_profile_view, update_profile_view, save_user_preferences_view, delete_account_view
)
from .novels import (
    NovelInfoViewSet, novel_categories_view, novel_sub_categories_view,
    novel_categories_tree_view, novel_detail_view, similar_novels_view,
    search_suggestions_view
)
from .recommendations import (
    recommend_view, personal_recommend_view, hot_novels_view,
    recent_update_view, user_preferences_view, categories_tree_view
)
from .behaviors import (
    UserBehaviorViewSet, rating_view, user_history_view
)

__all__ = [
    # auth
    'UserViewSet', 'login_view', 'register_view',
    'user_profile_view', 'update_profile_view', 'save_user_preferences_view', 'delete_account_view',
    # novels
    'NovelInfoViewSet', 'novel_categories_view', 'novel_sub_categories_view',
    'novel_categories_tree_view', 'novel_detail_view', 'similar_novels_view',
    'search_suggestions_view',
    # recommendations
    'recommend_view', 'personal_recommend_view', 'hot_novels_view',
    'recent_update_view', 'user_preferences_view', 'categories_tree_view',
    # behaviors
    'UserBehaviorViewSet', 'rating_view', 'user_history_view',
]
