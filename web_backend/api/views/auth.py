"""
认证相关视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.cache import cache

from ..models import User, UserBehavior
from ..serializers import UserSerializer, UserRegisterSerializer


class UserViewSet(viewsets.ModelViewSet):
    """用户视图集"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """用户注册"""
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            UserBehavior.objects.filter(user_id=user.id).delete()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """用户登录"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': '请输入用户名和密码'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 首先检查用户是否存在
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'username': '用户名不存在'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # 验证密码
    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
    else:
        return Response(
            {'password': '密码错误'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """用户注册"""
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        UserBehavior.objects.filter(user_id=user.id).delete()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_view(request):
    """获取当前用户信息"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """更新用户信息"""
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_user_preferences_view(request):
    """
    保存用户偏好设置
    """
    user = request.user

    data = {
        'selected_channel': request.data.get('selected_channel', ''),
        'selected_categories': request.data.get('selected_categories', []),
        'selected_sub_categories': request.data.get('selected_sub_categories', {}),
        'has_set_preference': request.data.get('has_set_preference', True)
    }

    serializer = UserSerializer(user, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        cache.clear()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_account_view(request):
    """
    删除用户账户
    需要验证密码，删除用户及其所有相关数据
    """
    import traceback
    
    user = request.user
    password = request.data.get('password', '')

    if not password:
        return Response(
            {'error': '请输入密码'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 验证密码
    if not user.check_password(password):
        return Response(
            {'error': '密码错误'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 保存用户信息用于日志记录（删除后对象无效）
    user_id = user.id
    username = user.username
    
    print(f"开始删除用户 {user_id}({username})...")
    
    try:
        # Step 1: 删除用户行为记录
        behavior_count = UserBehavior.objects.filter(user_id=user_id).count()
        UserBehavior.objects.filter(user_id=user_id).delete()
        print(f"已删除用户 {user_id}({username}) 的行为记录 ({behavior_count} 条)")
        
        # Step 2: 尝试删除用户档案（如果表存在）
        profile_deleted = False
        try:
            from ..models import UserProfile
            profile_count = UserProfile.objects.filter(user=user).count()
            if profile_count > 0:
                UserProfile.objects.filter(user=user).delete()
                print(f"已删除用户 {user_id}({username}) 的扩展档案 ({profile_count} 条)")
                profile_deleted = True
            else:
                print(f"用户 {user_id}({username}) 没有扩展档案记录")
        except Exception as profile_error:
            # 如果用户档案不存在、表不存在或其它错误，忽略错误
            print(f"处理用户档案时出现非关键错误（继续执行）：{profile_error}")
        
        # Step 3: 清除多对多关系（如果表存在）
        try:
            # 清除 groups 关系
            user.groups.clear()
            print(f"已清除用户 {user_id}({username}) 的组关系")
        except Exception as groups_error:
            print(f"清除组关系时出现非关键错误（继续执行）：{groups_error}")
        
        try:
            # 清除 user_permissions 关系
            user.user_permissions.clear()
            print(f"已清除用户 {user_id}({username}) 的权限关系")
        except Exception as perms_error:
            print(f"清除权限关系时出现非关键错误（继续执行）：{perms_error}")
        
        # Step 4: 删除用户
        try:
            user.delete()
            print(f"已成功删除用户 {user_id}({username})")
        except Exception as delete_error:
            # 检查是否是表不存在的错误
            error_msg = str(delete_error)
            if "doesn't exist" in error_msg and "user_profile_groups" in error_msg:
                print(f"检测到中间表不存在错误，尝试使用原始SQL删除用户记录")
                try:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM user_profile WHERE id = %s", [user_id])
                        deleted_rows = cursor.rowcount
                        print(f"原始SQL删除成功，影响行数: {deleted_rows}")
                        if deleted_rows > 0:
                            print(f"已通过原始SQL删除用户 {user_id}({username})")
                        else:
                            print(f"警告：原始SQL删除未影响任何行，用户ID可能不存在")
                except Exception as raw_sql_error:
                    print(f"原始SQL删除也失败: {raw_sql_error}")
                    # 重新抛出原始错误
                    raise delete_error
            else:
                # 其他错误，直接抛出
                raise delete_error
        
        return Response(
            {'message': '账户已成功注销'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"=== 删除用户 {user_id}({username}) 失败 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误消息: {str(e)}")
        print(f"详细堆栈：")
        print(error_trace)
        print("================================")
        
        # 返回详细的错误信息用于调试（开发环境）
        import os
        if os.environ.get('DJANGO_DEBUG', '').lower() == 'true':
            return Response(
                {
                    'error': '账户注销失败',
                    'detail': str(e),
                    'type': type(e).__name__,
                    'traceback': error_trace.split('\n')[:10]  # 只返回前10行堆栈
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        else:
            return Response(
                {'error': '账户注销失败，请稍后重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
