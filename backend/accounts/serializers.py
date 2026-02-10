from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    """注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = UserProfile
        fields = ['username', 'password', 'password_confirm', 'email', 'phone', 'department']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "两次密码不一致"})
        if UserProfile.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "用户名已存在"})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = UserProfile(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("用户名或密码错误")
        if not user.is_active:
            raise serializers.ValidationError("账户已被禁用")
        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'phone', 'department', 'role',
                  'role_display', 'avatar_url', 'date_joined', 'last_login', 'is_active']
        read_only_fields = ['id', 'username', 'role', 'date_joined', 'last_login', 'is_active']


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("原密码错误")
        return value


class UserListSerializer(serializers.ModelSerializer):
    """用户列表（管理员用）"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'phone', 'department', 'role',
                  'role_display', 'is_active', 'date_joined', 'last_login']
