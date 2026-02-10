<template>
  <div class="app-layout" v-if="route.name !== 'Login'">
    <!-- 侧边导航 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo-icon">🚇</div>
        <div class="logo-text">
          <h1>客流分析</h1>
          <span>Shanghai Transit</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="r in navRoutes"
          :key="r.path"
          :to="r.path"
          class="nav-item"
          :class="{ active: route.path === r.path }"
        >
          <span class="nav-icon">{{ r.meta.icon }}</span>
          <span class="nav-label">{{ r.meta.title }}</span>
          <span class="nav-indicator"></span>
          <span class="nav-hover-bg"></span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="system-status">
          <span class="status-dot"></span>
          <span>系统运行中</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <header class="top-bar">
        <div class="page-title">
          <h2>{{ currentTitle }}</h2>
          <p class="subtitle">上海市公共交通客流时空分布分析系统</p>
        </div>
        <div class="top-actions">
          <div class="date-display">
            <span class="date-icon">📅</span>
            <span>{{ currentDate }}</span>
          </div>
          <div class="user-info" v-if="isLoggedIn()">
            <span class="user-avatar">{{ userInitial }}</span>
            <span class="user-name">{{ state.user?.username }}</span>
            <span class="user-role badge-role">{{ state.user?.role_display }}</span>
            <button class="logout-btn" @click="handleLogout" title="退出登录">🚪</button>
          </div>
        </div>
      </header>

      <div class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>

  <!-- 登录页面独立渲染 -->
  <router-view v-else />

  <!-- 全局 Toast 通知 -->
  <ToastContainer />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'
import { authLogout } from './api'
import ToastContainer from './components/ToastContainer.vue'

const route = useRoute()
const router = useRouter()
const { state, isLoggedIn, clearAuth } = useAuth()

const navRoutes = router.getRoutes().filter(r => r.meta && r.meta.icon)

const currentTitle = computed(() => {
  const matched = navRoutes.find(r => r.path === route.path)
  return matched ? matched.meta.title : '数据总览'
})

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  })
})

const userInitial = computed(() => {
  return (state.user?.username || '?')[0].toUpperCase()
})

async function handleLogout() {
  try { await authLogout() } catch (e) { /* ignore */ }
  clearAuth()
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

// ===== 侧边栏 =====
.sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  background: linear-gradient(180deg, #0d1233 0%, #0a0e27 100%);
  border-right: 1px solid rgba(59, 130, 246, 0.1);
  display: flex;
  flex-direction: column;
  padding: 0;
  position: relative;
  overflow: hidden;

  // 装饰背景光效
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 50%);
    pointer-events: none;
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 28px 24px 24px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);

  .logo-icon {
    font-size: 32px;
    animation: float 3s ease-in-out infinite;
  }

  .logo-text {
    h1 {
      font-size: 18px;
      font-weight: 700;
      background: linear-gradient(135deg, #3b82f6, #06b6d4);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    span {
      font-size: 11px;
      color: #64748b;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
  }
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  text-decoration: none;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;

  .nav-icon {
    font-size: 18px;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .nav-label {
    position: relative;
    z-index: 1;
  }
  .nav-indicator {
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 0;
    background: linear-gradient(180deg, #3b82f6, #06b6d4);
    border-radius: 3px;
    transition: height 0.3s ease;
  }
  .nav-hover-bg {
    position: absolute;
    inset: 0;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(139, 92, 246, 0.04));
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }

  &:hover {
    color: #e2e8f0;
    .nav-hover-bg { opacity: 1; }
    .nav-icon { transform: scale(1.15) translateX(2px); }
  }

  &.active {
    color: #ffffff;
    .nav-hover-bg { opacity: 1; background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(139, 92, 246, 0.06)); }
    .nav-indicator { height: 24px; }
    .nav-icon { transform: scale(1.1); }
  }
}

.sidebar-footer {
  padding: 20px 24px;
  border-top: 1px solid rgba(59, 130, 246, 0.08);
}

.system-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #64748b;

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    animation: pulse-glow 2s infinite;
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
  }
}

// ===== 主内容 =====
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 80% 10%, rgba(59, 130, 246, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 20% 80%, rgba(139, 92, 246, 0.03) 0%, transparent 50%),
    #0a0e27;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 32px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
  backdrop-filter: blur(10px);

  .page-title {
    h2 {
      font-size: 22px;
      font-weight: 700;
      color: #e2e8f0;
    }
    .subtitle {
      font-size: 12px;
      color: #64748b;
      margin-top: 2px;
    }
  }
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.date-display {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(22, 30, 65, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 10px;
  font-size: 13px;
  color: #94a3b8;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  background: rgba(22, 30, 65, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 10px;

  .user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    color: white;
  }

  .user-name {
    font-size: 13px;
    font-weight: 500;
    color: #e2e8f0;
  }

  .badge-role {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    background: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    font-weight: 500;
  }

  .logout-btn {
    background: none;
    border: none;
    font-size: 16px;
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
    transition: all 0.2s;
    opacity: 0.6;

    &:hover {
      opacity: 1;
      background: rgba(239, 68, 68, 0.1);
    }
  }
}

.content-area {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
}

// ===== 页面过渡动画 =====
.page-fade-enter-active { transition: all 0.45s cubic-bezier(0.4, 0, 0.2, 1); }
.page-fade-leave-active { transition: all 0.2s cubic-bezier(0.4, 0, 1, 1); }
.page-fade-enter-from { opacity: 0; transform: translateY(16px) scale(0.99); }
.page-fade-leave-to { opacity: 0; transform: translateY(-8px) scale(0.995); }
</style>
