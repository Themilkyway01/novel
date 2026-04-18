"""
Django Models - 映射现有数据库表
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    用户模型 - 对应 user_profile 表
    """
    GENDER_CHOICES = [
        (0, '女频'),
        (1, '男频'),
        (2, '出版'),
    ]

    user_cate = models.SmallIntegerField('用户类别', default=1, choices=GENDER_CHOICES)
    avatar = models.CharField('头像', max_length=255, blank=True, null=True)
    phone = models.CharField('手机号', max_length=20, blank=True, null=True)

    # 用户偏好设置（存储在JSON字段中）
    selected_channel = models.CharField('选择的频道', max_length=10, blank=True, null=True, default='')
    selected_categories = models.JSONField('选择的分类', blank=True, null=True, default=list)
    selected_sub_categories = models.JSONField('选择的子分类', blank=True, null=True, default=dict)
    has_set_preference = models.BooleanField('是否已设置偏好', default=False)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'user_profile'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


class NovelInfo(models.Model):
    """
    小说信息模型 - 对应 novel_info 表
    """
    cate_choices = [
        (0, '女频'),
        (1, '男频'),
        (2, '出版'),
    ]
    
    index = models.AutoField('ID', primary_key=True)
    cate = models.SmallIntegerField('类别', choices=cate_choices)
    img = models.CharField('封面 URL', max_length=255, blank=True, null=True)
    name = models.CharField('书名', max_length=255)
    author = models.CharField('作者', max_length=100)
    up_time = models.DateTimeField('更新时间', blank=True, null=True)
    up_chapter = models.CharField('更新章节', max_length=255, blank=True, null=True)
    up_status = models.SmallIntegerField('连载状态', default=0)  # 0 连载，1 完本
    signed = models.SmallIntegerField('签约状态', default=0)  # 0 未签约，1 签约
    vip = models.SmallIntegerField('VIP 状态', default=0)  # 0 免费，1 VIP
    category = models.CharField('分类', max_length=100)
    sub_category = models.CharField('子分类', max_length=100)
    wordcount = models.IntegerField('字数', default=0)
    all_recommend = models.IntegerField('总推荐数', default=0)
    week_recommend = models.IntegerField('周推荐数', default=0)
    introduction = models.TextField('简介', blank=True, null=True)
    chapters = models.IntegerField('章节数', default=0)
    
    class Meta:
        db_table = 'novel_info'
        verbose_name = '小说信息'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.name


class UserBehavior(models.Model):
    """
    用户行为模型 - 对应 user_behavior 表
    数据库表结构：id(主键), user_id, user_cate, novel_id, read_time, timestamp
    """
    # 不显式声明主键，让 Django 自动使用 id 作为主键
    # 如果数据库表中主键名不是 id，Django 会自动处理
    user_id = models.BigIntegerField('用户 ID', null=True, blank=True)
    user_cate = models.BigIntegerField('用户类别', null=True, blank=True)
    novel_id = models.BigIntegerField('小说 ID', null=True, blank=True)
    read_time = models.SmallIntegerField('阅读时长 (分钟)')
    timestamp = models.DateTimeField('时间戳', auto_now_add=True)
    
    class Meta:
        db_table = 'user_behavior'
        verbose_name = '用户行为'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['novel_id']),
        ]
    
    def __str__(self):
        return f"User {self.user_id} - Novel {self.novel_id}"


class UserProfile(models.Model):
    """
    用户档案模型（可选，用于扩展 Django User）
    """
    GENDER_CHOICES = [
        (0, '女'),
        (1, '男'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    gender = models.SmallIntegerField('性别', choices=GENDER_CHOICES, default=1)
    birth_date = models.DateField('出生日期', blank=True, null=True)
    bio = models.TextField('个人简介', blank=True, null=True)
    avatar = models.CharField('头像 URL', max_length=255, blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'user_extend_profile'
        verbose_name = '用户档案'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.user.username
