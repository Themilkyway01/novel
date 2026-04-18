"""
小说相关视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Count

from ..models import NovelInfo
from ..serializers import NovelInfoSerializer, NovelListSerializer


class NovelInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """小说信息视图集"""
    queryset = NovelInfo.objects.all().order_by('-all_recommend')
    serializer_class = NovelInfoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """支持搜索和过滤"""
        from django.db.models import Q
        queryset = super().get_queryset()

        keyword = self.request.query_params.get('keyword', None)
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) |
                Q(author__icontains=keyword)
            )

        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        sub_category = self.request.query_params.get('sub_category', None)
        if sub_category:
            queryset = queryset.filter(sub_category=sub_category)

        cate = self.request.query_params.get('cate', None)
        if cate:
            queryset = queryset.filter(cate=int(cate))

        up_status = self.request.query_params.get('up_status', None)
        if up_status is not None:
            queryset = queryset.filter(up_status=int(up_status))

        sort_by = self.request.query_params.get('sort', 'all_recommend')
        if sort_by in ['all_recommend', 'week_recommend', 'wordcount', 'up_time']:
            queryset = queryset.order_by(f'-{sort_by}')

        return queryset


@api_view(['GET'])
@permission_classes([AllowAny])
def novel_categories_view(request):
    """获取分类列表"""
    cate = request.query_params.get('cate', None)

    queryset = NovelInfo.objects.all()
    if cate is not None:
        queryset = queryset.filter(cate=int(cate))

    categories = queryset.values('category').annotate(
        count=Count('index')
    ).order_by('-count')
    return Response(list(categories))


@api_view(['GET'])
@permission_classes([AllowAny])
def novel_sub_categories_view(request):
    """获取子分类列表"""
    category = request.query_params.get('category', None)

    if not category:
        return Response([])

    queryset = NovelInfo.objects.filter(category=category)
    sub_categories = queryset.values('sub_category').annotate(
        count=Count('index')
    ).order_by('-count')
    return Response(list(sub_categories))


@api_view(['GET'])
@permission_classes([AllowAny])
def novel_categories_tree_view(request):
    """获取分类树（频道 - 分类 - 子分类）"""
    cate = request.query_params.get('cate', None)

    result = []
    queryset = NovelInfo.objects.all()
    if cate is not None:
        queryset = queryset.filter(cate=int(cate))

    channels = queryset.values('cate').distinct()
    for channel in channels:
        channel_id = channel['cate']
        channel_name = {0: '女频', 1: '男频', 2: '出版'}.get(channel_id, '未知')

        categories = NovelInfo.objects.filter(cate=channel_id).values('category').distinct()
        category_list = []

        for cat in categories:
            cat_name = cat['category']
            sub_cats = NovelInfo.objects.filter(
                cate=channel_id,
                category=cat_name
            ).values('sub_category').distinct()
            sub_category_list = [sub['sub_category'] for sub in sub_cats]

            category_list.append({
                'name': cat_name,
                'sub_categories': sub_category_list
            })

        result.append({
            'id': channel_id,
            'name': channel_name,
            'categories': category_list
        })

    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def novel_detail_view(request, novel_id):
    """小说详情"""
    try:
        novel = NovelInfo.objects.get(index=novel_id)
        serializer = NovelInfoSerializer(novel)
        return Response(serializer.data)
    except NovelInfo.DoesNotExist:
        return Response(
            {'error': '小说不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def similar_novels_view(request, novel_id):
    """相似小说推荐"""
    try:
        novel_id = int(novel_id)
    except (ValueError, TypeError):
        return Response(
            {'error': '无效的小说 ID'},
            status=status.HTTP_400_BAD_REQUEST
        )

    n = int(request.query_params.get('n', 20))
    same_category_priority = request.query_params.get('same_category_priority', 'true').lower() == 'true'

    try:
        from ..recommender import recommendation_engine
        novels = recommendation_engine.similar_novels(novel_id, n, same_category_priority)
        serializer = NovelListSerializer(novels, many=True)
        return Response(serializer.data)
    except Exception as e:
        import traceback
        print(f"相似推荐失败：{e}")
        print(traceback.format_exc())
        return Response(
            {'error': f'推荐计算失败：{str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def search_suggestions_view(request):
    """搜索建议"""
    keyword = request.query_params.get('keyword', '').strip()
    limit = int(request.query_params.get('limit', 10))

    if not keyword or len(keyword) < 1:
        return Response([])

    results = []

    def get_match_position(text, keyword):
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        pos = text_lower.find(keyword_lower)
        return pos if pos >= 0 else 999

    novel_matches = NovelInfo.objects.filter(
        name__icontains=keyword
    ).values('index', 'name', 'author')

    novel_list = list(novel_matches)
    novel_list.sort(key=lambda x: get_match_position(x['name'], keyword))
    novel_list = novel_list[:limit]

    for novel in novel_list:
        results.append({
            'type': 'novel',
            'id': novel['index'],
            'name': novel['name'],
            'author': novel['author'],
            'label': novel['name'],
            'match_position': get_match_position(novel['name'], keyword),
        })

    author_matches = NovelInfo.objects.filter(
        author__icontains=keyword
    ).values('author').distinct()

    author_list = list(author_matches)
    author_list.sort(key=lambda x: get_match_position(x['author'], keyword))
    author_list = author_list[:limit]

    added_authors = set()
    for item in author_list:
        author = item['author']
        if author not in added_authors:
            added_authors.add(author)
            novel_count = NovelInfo.objects.filter(author=author).count()
            results.append({
                'type': 'author',
                'id': None,
                'name': author,
                'author': author,
                'label': author,
                'novel_count': novel_count,
                'match_position': get_match_position(author, keyword),
            })

    results.sort(key=lambda x: (x.get('match_position', 999), x['type'] != 'novel'))

    for item in results:
        item.pop('match_position', None)

    return Response(results[:limit * 2])
