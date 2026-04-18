"""
API URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, NovelInfoViewSet, UserBehaviorViewSet,
    login_view, register_view, user_profile_view, update_profile_view, save_user_preferences_view, delete_account_view,
    novel_categories_view, novel_sub_categories_view, novel_categories_tree_view,
    novel_detail_view, similar_novels_view,
    rating_view, recommend_view, personal_recommend_view,
    hot_novels_view, recent_update_view, search_suggestions_view,
    user_preferences_view, categories_tree_view, user_history_view
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'novels', NovelInfoViewSet)
router.register(r'behaviors', UserBehaviorViewSet, basename='behavior')

urlpatterns = [
    # 用户认证
    path('auth/login/', login_view, name='login'),
    path('auth/register/', register_view, name='register'),
    path('auth/profile/', user_profile_view, name='profile'),
    path('auth/profile/update/', update_profile_view, name='update_profile'),
    path('auth/preferences/save/', save_user_preferences_view, name='save_user_preferences'),
    path('auth/delete-account/', delete_account_view, name='delete_account'),

    # 小说相关（必须在 router 之前，避免被 router 捕获）
    path('novels/categories/', novel_categories_view, name='categories'),
    path('novels/sub-categories/', novel_sub_categories_view, name='sub_categories'),
    path('novels/categories-tree/', novel_categories_tree_view, name='categories_tree'),
    path('novels/<int:novel_id>/', novel_detail_view, name='novel_detail'),
    path('novels/<int:novel_id>/similar/', similar_novels_view, name='similar_novels'),

    # 用户行为
    path('ratings/', rating_view, name='rating'),

    # 推荐
    path('recommend/', recommend_view, name='recommend'),
    path('recommend/personal/', personal_recommend_view, name='personal_recommend'),

    # 排行榜
    path('hot/', hot_novels_view, name='hot_novels'),
    path('recent/', recent_update_view, name='recent_update'),

    # 搜索建议
    path('search/suggestions/', search_suggestions_view, name='search_suggestions'),

    # 用户偏好
    path('user/preferences/', user_preferences_view, name='user_preferences'),

    # 阅读历史
    path('user/history/', user_history_view, name='user_history'),

    # 分类树
    path('categories/tree/', categories_tree_view, name='categories_tree'),

    # Router URLs（放在最后）
    path('', include(router.urls)),
]
