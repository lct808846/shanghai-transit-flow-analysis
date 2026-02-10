from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.utils import timezone

from .models import UserProfile, LoginLog
from .serializers import (
    RegisterSerializer, LoginSerializer, UserProfileSerializer,
    ChangePasswordSerializer, UserListSerializer
)


def get_client_ip(request):
    """获取客户端IP"""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """用户注册"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'status': 'success',
            'message': '注册成功',
            'data': {
                'token': token.key,
                'user': UserProfileSerializer(user).data,
            }
        }, status=status.HTTP_201_CREATED)
    return Response({
        'status': 'error',
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """用户登录"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)

        # 更新登录信息
        ip = get_client_ip(request)
        user.last_login = timezone.now()
        user.last_login_ip = ip
        user.save(update_fields=['last_login', 'last_login_ip'])

        # 记录登录日志
        LoginLog.objects.create(
            user=user,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
        )

        return Response({
            'status': 'success',
            'message': '登录成功',
            'data': {
                'token': token.key,
                'user': UserProfileSerializer(user).data,
            }
        })

    # 登录失败日志
    username = request.data.get('username', '')
    try:
        user = UserProfile.objects.get(username=username)
        LoginLog.objects.create(user=user, ip_address=get_client_ip(request), success=False)
    except UserProfile.DoesNotExist:
        pass

    return Response({
        'status': 'error',
        'message': '用户名或密码错误',
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """退出登录 (删除Token)"""
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({'status': 'success', 'message': '已退出登录'})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile(request):
    """获取/更新个人信息"""
    if request.method == 'GET':
        serializer = UserProfileSerializer(request.user)
        return Response({'status': 'success', 'data': serializer.data})

    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({'status': 'success', 'data': serializer.data})
    return Response({'status': 'error', 'errors': serializer.errors}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """修改密码"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        # 重新生成 Token
        request.user.auth_token.delete()
        token = Token.objects.create(user=request.user)
        return Response({
            'status': 'success',
            'message': '密码修改成功',
            'data': {'token': token.key},
        })
    return Response({'status': 'error', 'errors': serializer.errors}, status=400)


# ================ 管理员接口 ================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    """用户列表（管理员/分析师可用）"""
    if not request.user.is_analyst:
        return Response({'status': 'error', 'message': '权限不足'}, status=403)

    users = UserProfile.objects.all().order_by('-date_joined')
    serializer = UserListSerializer(users, many=True)
    return Response({'status': 'success', 'data': serializer.data})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_role(request, user_id):
    """修改用户角色（仅管理员）"""
    if not request.user.is_admin:
        return Response({'status': 'error', 'message': '权限不足'}, status=403)

    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return Response({'status': 'error', 'message': '用户不存在'}, status=404)

    new_role = request.data.get('role')
    if new_role not in dict(UserProfile.ROLE_CHOICES):
        return Response({'status': 'error', 'message': '无效的角色'}, status=400)

    user.role = new_role
    user.save(update_fields=['role'])
    return Response({
        'status': 'success',
        'message': f'已将 {user.username} 的角色修改为 {user.get_role_display()}',
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def toggle_user_active(request, user_id):
    """启用/禁用用户（仅管理员）"""
    if not request.user.is_admin:
        return Response({'status': 'error', 'message': '权限不足'}, status=403)

    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return Response({'status': 'error', 'message': '用户不存在'}, status=404)

    if user == request.user:
        return Response({'status': 'error', 'message': '不能禁用自己'}, status=400)

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    action = '启用' if user.is_active else '禁用'
    return Response({'status': 'success', 'message': f'已{action}用户 {user.username}'})
