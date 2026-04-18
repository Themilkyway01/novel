"""
推荐相关视图
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..recommender import recommendation_engine
from ..serializers import NovelListSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def recommend_view(request):
    """
    通用推荐接口
    """
    user_id = request.query_params.get('user_id', None)
    user_cate = request.query_params.get('user_cate', None)
    channel = request.query_params.get('channel', None)
    category = request.query_params.get('category', None)
    n = int(request.query_params.get('n', 12))
    rec_type = request.query_params.get('type', 'hot')
    novel_id = request.query_params.get('novel_id', None)

    preferred_categories = request.query_params.getlist('categories', [])
    if isinstance(preferred_categories, str):
        preferred_categories = preferred_categories.split(',')

    try:
        if rec_type == 'similar':
            if novel_id:
                novels = recommendation_engine.similar_novels(int(novel_id), n)
            elif user_id:
                novels = recommendation_engine.similar_novels_for_user(int(user_id), n)
            else:
                return Response(
                    {'error': '相似推荐需要提供 user_id 或 novel_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif rec_type == 'new':
            novels = recommendation_engine.recommend_new_books(
                user_id=int(user_id) if user_id else None,
                n=n
            )

        elif rec_type == 'recent':
            novels = recommendation_engine.get_recent_updates(
                user_id=int(user_id) if user_id else None,
                channel=int(channel) if channel else None,
                category=category,
                n=n
            )

        elif rec_type == 'hot':
            novels = recommendation_engine.get_hot_recommendations(
                user_id=int(user_id) if user_id else None,
                channel=int(channel) if channel else None,
                category=category,
                n=n
            )

        elif user_id and rec_type in ['hybrid', 'cf']:
            use_hybrid = (rec_type == 'hybrid')
            novels = recommendation_engine.recommend_for_user(
                int(user_id),
                n=n,
                use_hybrid=use_hybrid,
                channel=int(channel) if channel else None,
                category=category
            )

        else:
            novels = recommendation_engine.recommend_cold_start(
                user_cate=int(user_cate) if user_cate else None,
                preferred_categories=preferred_categories,
                n=n
            )

        serializer = NovelListSerializer(novels, many=True)
        return Response(serializer.data)

    except Exception as e:
        import traceback
        print(f"推荐失败：{e}")
        print(traceback.format_exc())
        return Response(
            {'error': f'推荐计算失败：{str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def personal_recommend_view(request):
    """个性化推荐（已登录用户）"""
    n = int(request.query_params.get('n', 12))
    rec_type = request.query_params.get('type', 'hybrid')
    channel = request.query_params.get('channel', None)
    category = request.query_params.get('category', None)

    novels = recommendation_engine.recommend_for_user(
        request.user.id,
        n=n,
        use_hybrid=(rec_type == 'hybrid'),
        channel=int(channel) if channel else None,
        category=category
    )
    serializer = NovelListSerializer(novels, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def hot_novels_view(request):
    """热门小说"""
    n = int(request.query_params.get('n', 12))
    channel = request.query_params.get('channel', None)
    category = request.query_params.get('category', None)
    random_sample = request.query_params.get('random', 'true').lower() == 'true'
    timestamp = request.query_params.get('t', None)

    preferred_categories = request.query_params.get('categories', None)
    if preferred_categories:
        preferred_categories = [cat.strip() for cat in preferred_categories.split(',') if cat.strip()]

    if random_sample:
        user_id = request.query_params.get('user_id', None)
        novels = recommendation_engine.get_hot_recommendations(
            user_id=int(user_id) if user_id else None,
            channel=int(channel) if channel else None,
            category=category,
            preferred_categories=preferred_categories,
            n=n,
            skip_cache=timestamp is not None
        )
    else:
        from ..models import NovelInfo
        sort_by = request.query_params.get('sort', 'all_recommend')
        if sort_by not in ['all_recommend', 'week_recommend', 'wordcount']:
            sort_by = 'all_recommend'

        queryset = NovelInfo.objects.all()
        if channel:
            queryset = queryset.filter(cate=int(channel))
        if category:
            queryset = queryset.filter(category=category)

        novels = queryset.order_by(f'-{sort_by}')[:n]

    serializer = NovelListSerializer(novels, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def recent_update_view(request):
    """最新更新"""
    n = int(request.query_params.get('n', 12))
    channel = request.query_params.get('channel', None)
    category = request.query_params.get('category', None)
    days = int(request.query_params.get('days', 30))
    user_id = request.query_params.get('user_id', None)
    timestamp = request.query_params.get('t', None)

    preferred_categories = request.query_params.get('categories', None)
    if preferred_categories:
        preferred_categories = [cat.strip() for cat in preferred_categories.split(',') if cat.strip()]

    novels = recommendation_engine.get_recent_updates(
        user_id=int(user_id) if user_id else None,
        channel=int(channel) if channel else None,
        category=category,
        preferred_categories=preferred_categories,
        n=n,
        days=days,
        skip_cache=timestamp is not None
    )
    serializer = NovelListSerializer(novels, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def user_preferences_view(request):
    """获取用户偏好"""
    user_id = request.query_params.get('user_id', None)

    if not user_id:
        return Response({'error': '需要提供 user_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = int(user_id)
        prefs = recommendation_engine.get_user_preferences(user_id)
        prefs['inferred_categories'] = recommendation_engine._infer_user_categories(user_id)
        prefs['channels'] = recommendation_engine.categories_by_channel
        prefs['all_categories'] = list(recommendation_engine.novel_info['category'].unique())

        return Response(prefs)

    except Exception as e:
        return Response(
            {'error': f'获取偏好失败：{str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def categories_tree_view(request):
    """获取完整的分类树结构"""
    result = recommendation_engine.categories_by_channel
    return Response(result)
