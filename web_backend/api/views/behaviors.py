"""
用户行为相关视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import F
from django.utils import timezone
import random

from ..models import NovelInfo, UserBehavior
from ..serializers import UserBehaviorSerializer, RatingSerializer
from ..recommender import recommendation_engine


class UserBehaviorViewSet(viewsets.ModelViewSet):
    """用户行为视图集"""
    serializer_class = UserBehaviorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBehavior.objects.filter(user_id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        """记录用户行为（阅读）"""
        novel_id = request.data.get('novel_id')
        read_time = request.data.get('read_time', 30)

        if not novel_id:
            return Response(
                {'error': '缺少小说 ID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            NovelInfo.objects.get(index=novel_id)
        except NovelInfo.DoesNotExist:
            return Response(
                {'error': '小说不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        behavior = UserBehavior.objects.filter(
            user_id=request.user.id,
            novel_id=novel_id
        ).first()

        if behavior:
            additional_time = read_time + random.randint(5, 15)
            behavior.read_time = F('read_time') + additional_time
            behavior.timestamp = timezone.now()
            behavior.save()
        else:
            behavior = UserBehavior.objects.create(
                user_id=request.user.id,
                user_cate=request.user.user_cate,
                novel_id=novel_id,
                read_time=read_time
            )

        behavior.refresh_from_db()
        recommendation_engine.novel_info = None  # 触发重新加载
        recommendation_engine._initialize()

        serializer = self.get_serializer(behavior)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rating_view(request):
    """用户评分"""
    serializer = RatingSerializer(data=request.data)
    if serializer.is_valid():
        novel_id = serializer.validated_data['novel_id']
        rating = serializer.validated_data['rating']

        read_time_map = {1: 20, 2: 60, 3: 180, 4: 600, 5: 1800}
        read_time = read_time_map.get(rating, 180)

        behavior = UserBehavior.objects.filter(
            user_id=request.user.id,
            novel_id=novel_id
        ).first()

        if behavior:
            additional_time = read_time + random.randint(5, 15)
            behavior.read_time = F('read_time') + additional_time
            behavior.timestamp = timezone.now()
            behavior.save()
        else:
            behavior = UserBehavior.objects.create(
                user_id=request.user.id,
                user_cate=request.user.user_cate,
                novel_id=novel_id,
                read_time=read_time
            )

        behavior.refresh_from_db()

        recommendation_engine.novel_info = None
        recommendation_engine._initialize()

        return Response({'message': '评分成功'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_history_view(request):
    """获取用户阅读历史"""
    user_id = request.user.id

    try:
        behaviors = UserBehavior.objects.filter(user_id=user_id).order_by('-timestamp')

        novel_ids = [b.novel_id for b in behaviors]
        novels = NovelInfo.objects.filter(index__in=novel_ids)
        novel_info_cache = {novel.index: {'name': novel.name, 'img': novel.img} for novel in novels}

        from ..serializers import UserBehaviorSerializer
        serializer = UserBehaviorSerializer(
            behaviors, many=True,
            context={'novel_info_cache': novel_info_cache}
        )

        return Response({
            'results': serializer.data,
            'count': behaviors.count()
        })
    except Exception as e:
        import traceback
        print(f"获取阅读历史失败：{e}")
        traceback.print_exc()
        return Response(
            {'error': f'获取阅读历史失败：{str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
