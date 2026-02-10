from django.db import models
from django.contrib.auth.models import AbstractUser


class UserProfile(AbstractUser):
    """
    自定义用户模型 - 扩展 Django 内置 User
    """
    ROLE_CHOICES = [
        ('admin', '管理员'),
        ('analyst', '分析师'),
        ('viewer', '普通用户'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer', verbose_name="角色")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="手机号")
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="部门")
    avatar_url = models.URLField(blank=True, null=True, verbose_name="头像URL")
    last_login_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="最后登录IP")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_analyst(self):
        return self.role in ('admin', 'analyst')


class LoginLog(models.Model):
    """登录日志"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="用户")
    login_time = models.DateTimeField(auto_now_add=True, verbose_name="登录时间")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP地址")
    user_agent = models.TextField(blank=True, null=True, verbose_name="User-Agent")
    success = models.BooleanField(default=True, verbose_name="是否成功")

    class Meta:
        verbose_name = "登录日志"
        verbose_name_plural = "登录日志"
        ordering = ['-login_time']
