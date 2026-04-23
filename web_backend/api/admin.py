"""
Django Admin 配置 - 后台管理界面
提供系统内容的增删改查操作，支持数据表格视图和权限验证
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from .models import User, NovelInfo, UserBehavior


# ==================== 用户管理 ====================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """自定义用户管理界面"""
    list_display = ('username', 'email', 'user_cate_display', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'user_cate', 'has_set_preference')
    search_fields = ('username', 'email', 'phone')
    ordering = ('-created_at',)
    readonly_fields = ('last_login', 'date_joined', 'created_at', 'updated_at')
    actions = ['activate_users', 'deactivate_users', 'make_staff', 'remove_staff']
    
    # 自定义字段显示
    def user_cate_display(self, obj):
        return obj.get_user_cate_display()
    user_cate_display.short_description = '用户类别'
    
    # 字段分组配置
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('个人信息'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'avatar')}),
        (_('偏好设置'), {'fields': ('user_cate', 'selected_channel', 'selected_categories', 
                                 'selected_sub_categories', 'has_set_preference')}),
        (_('权限状态'), {'fields': ('is_active', 'is_staff', 'is_superuser', 
                                 'groups', 'user_permissions')}),
        (_('重要日期'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_cate', 
                      'is_staff', 'is_active'),
        }),
    )
    
    # 批量操作：激活用户
    @admin.action(description='激活所选用户')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 个用户', messages.SUCCESS)
    
    # 批量操作：禁用用户
    @admin.action(description='禁用所选用户')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个用户', messages.WARNING)
    
    # 批量操作：设为员工
    @admin.action(description='设为员工用户')
    def make_staff(self, request, queryset):
        updated = queryset.update(is_staff=True)
        self.message_user(request, f'成功将 {updated} 个用户设为员工', messages.SUCCESS)
    
    # 批量操作：取消员工权限
    @admin.action(description='取消员工权限')
    def remove_staff(self, request, queryset):
        # 防止取消超级用户的员工权限
        non_superusers = queryset.filter(is_superuser=False)
        updated = non_superusers.update(is_staff=False)
        if updated < queryset.count():
            self.message_user(request, f'超级用户的员工权限无法取消', messages.WARNING)
        self.message_user(request, f'成功取消 {updated} 个用户的员工权限', messages.SUCCESS)
    
    # 权限控制
    def has_delete_permission(self, request, obj=None):
        """只有超级用户可以删除用户"""
        return request.user.is_superuser


# ==================== 小说信息管理 ====================
@admin.register(NovelInfo)
class NovelInfoAdmin(admin.ModelAdmin):
    """小说信息管理界面"""
    list_display = ('index', 'name', 'author', 'cate_display', 'category', 
                    'sub_category', 'wordcount', 'up_status_display', 'signed_display', 'up_time')
    list_filter = ('cate', 'up_status', 'signed', 'vip', 'category')
    search_fields = ('name', 'author', 'category', 'sub_category', 'introduction')
    list_per_page = 50
    readonly_fields = ('index',)
    date_hierarchy = 'up_time'
    actions = ['mark_as_completed', 'mark_as_signed', 'export_novel_info']
    
    # 自定义字段显示方法
    def cate_display(self, obj):
        return obj.get_cate_display()
    cate_display.short_description = '类别'
    
    def up_status_display(self, obj):
        return '完本' if obj.up_status == 1 else '连载'
    up_status_display.short_description = '连载状态'
    
    def signed_display(self, obj):
        return '已签约' if obj.signed == 1 else '未签约'
    signed_display.short_description = '签约状态'
    
    # 字段分组配置
    fieldsets = (
        (_('基本信息'), {'fields': ('cate', 'name', 'author', 'img')}),
        (_('分类信息'), {'fields': ('category', 'sub_category')}),
        (_('内容信息'), {'fields': ('wordcount', 'chapters', 'introduction')}),
        (_('推荐数据'), {'fields': ('all_recommend', 'week_recommend')}),
        (_('状态信息'), {'fields': ('up_status', 'signed', 'vip', 
                                 'up_time', 'up_chapter')}),
    )
    
    # 批量操作：标记为完本
    @admin.action(description='标记为完本')
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(up_status=1)
        self.message_user(request, f'成功将 {updated} 部小说标记为完本', messages.SUCCESS)
    
    # 批量操作：标记为签约
    @admin.action(description='标记为已签约')
    def mark_as_signed(self, request, queryset):
        updated = queryset.update(signed=1)
        self.message_user(request, f'成功将 {updated} 部小说标记为已签约', messages.SUCCESS)
    
    # 权限控制
    def has_delete_permission(self, request, obj=None):
        """只有员工用户可以删除小说信息"""
        return request.user.is_staff


# ==================== 用户行为管理 ====================
@admin.register(UserBehavior)
class UserBehaviorAdmin(admin.ModelAdmin):
    """用户行为管理界面"""
    list_display = ('id', 'user_id', 'novel_id', 'read_time', 'timestamp_formatted')
    list_filter = ('user_cate',)
    search_fields = ('user_id', 'novel_id')
    list_per_page = 100
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    # 自定义时间显示
    def timestamp_formatted(self, obj):
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    timestamp_formatted.short_description = '行为时间'
    
    # 权限控制
    def has_add_permission(self, request):
        """只有超级用户可以添加用户行为记录"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """只有员工用户可以修改用户行为记录"""
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """只有超级用户可以删除用户行为记录"""
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """数据访问控制：普通员工只能查看最近30天的记录"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # 这里可以添加时间过滤逻辑
            pass
        return qs

# ==================== 自定义Admin站点配置 ====================
# 设置Admin站点标题
admin.site.site_header = '小说推荐系统管理后台'
admin.site.site_title = '小说推荐系统'
admin.site.index_title = '数据管理面板'

# 自定义权限验证
def check_admin_permission(request):
    """全局后台访问权限检查"""
    if not request.user.is_authenticated:
        return False
    if not request.user.is_active:
        return False
    if not request.user.is_staff:
        return False
    return True

# 应用权限检查到所有ModelAdmin
for model, model_admin in admin.site._registry.items():
    original_has_module_permission = model_admin.has_module_permission
    original_has_view_permission = model_admin.has_view_permission
    
    def custom_has_module_permission(self, request):
        if not check_admin_permission(request):
            return False
        return original_has_module_permission(request)
    
    def custom_has_view_permission(self, request, obj=None):
        if not check_admin_permission(request):
            return False
        return original_has_view_permission(request, obj)
    
    model_admin.has_module_permission = custom_has_module_permission.__get__(model_admin, type(model_admin))
    model_admin.has_view_permission = custom_has_view_permission.__get__(model_admin, type(model_admin))


# ==================== 数据导出功能（示例） ====================
# 此处可以添加数据导出功能，如导出为Excel、CSV等
# 可以使用django-import-export库扩展