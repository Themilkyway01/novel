"""
Django REST Framework Serializers
"""
from rest_framework import serializers
from .models import User, NovelInfo, UserBehavior


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'user_cate', 'avatar', 'phone',
                  'selected_channel', 'selected_categories', 'selected_sub_categories', 'has_set_preference',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'user_cate']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': '两次输入的密码不一致'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            user_cate=validated_data.get('user_cate', 1)
        )
        return user


class NovelInfoSerializer(serializers.ModelSerializer):
    """小说信息序列化器"""
    up_status_display = serializers.SerializerMethodField()
    signed_display = serializers.SerializerMethodField()
    vip_display = serializers.SerializerMethodField()
    cate_display = serializers.SerializerMethodField()
    
    class Meta:
        model = NovelInfo
        fields = [
            'index', 'cate', 'cate_display', 'img', 'name', 'author', 
            'up_time', 'up_chapter', 'up_status', 'up_status_display',
            'signed', 'signed_display', 'vip', 'vip_display',
            'category', 'sub_category', 'wordcount', 'all_recommend', 
            'week_recommend', 'introduction', 'chapters'
        ]
    
    def get_up_status_display(self, obj):
        return '完本' if obj.up_status == 1 else '连载'
    
    def get_signed_display(self, obj):
        return '签约' if obj.signed == 1 else '未签约'
    
    def get_vip_display(self, obj):
        return 'VIP' if obj.vip == 1 else '免费'
    
    def get_cate_display(self, obj):
        cate_map = {0: '女频', 1: '男频', 2: '出版'}
        return cate_map.get(obj.cate, '未知')


class NovelListSerializer(serializers.ModelSerializer):
    """小说列表简化序列化器"""
    novel_id = serializers.IntegerField(source='index')
    
    class Meta:
        model = NovelInfo
        fields = ['index', 'novel_id', 'img', 'name', 'author', 'category', 'sub_category', 'wordcount', 'all_recommend', 'week_recommend', 'introduction', 'up_chapter', 'up_time', 'up_status']


class UserBehaviorSerializer(serializers.ModelSerializer):
    """用户行为序列化器"""
    novel_name = serializers.SerializerMethodField()
    novel_img = serializers.SerializerMethodField()

    class Meta:
        model = UserBehavior
        fields = ['id', 'user_id', 'novel_id', 'novel_name', 'novel_img', 'read_time', 'timestamp']
        read_only_fields = ['id', 'timestamp']

    def get_novel_name(self, obj):
        novel_cache = self.context.get('novel_info_cache', {})
        if isinstance(novel_cache, dict):
            novel_info = novel_cache.get(obj.novel_id)
            if novel_info:
                return novel_info.get('name', '未知小说')
        return '未知小说'

    def get_novel_img(self, obj):
        novel_cache = self.context.get('novel_info_cache', {})
        if isinstance(novel_cache, dict):
            novel_info = novel_cache.get(obj.novel_id)
            if novel_info:
                return novel_info.get('img', '/placeholder.jpg')
        return '/placeholder.jpg'


class RatingSerializer(serializers.Serializer):
    """评分序列化器"""
    novel_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
