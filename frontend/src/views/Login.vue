<template>
  <div class="login-page">
    <!-- 动态背景粒子 -->
    <div class="bg-particles">
      <span v-for="i in 20" :key="i" class="particle" :style="particleStyle(i)"></span>
    </div>

    <div class="login-container">
      <!-- 左侧品牌区 -->
      <div class="brand-side">
        <div class="brand-content">
          <div class="brand-icon">🚇</div>
          <h1>上海公共交通</h1>
          <h2>客流时空分析系统</h2>
          <p class="brand-desc">
            基于大数据分析的城市公共交通客流时空分布智能分析平台
          </p>
          <div class="brand-features">
            <div class="feature" v-for="f in features" :key="f.icon">
              <span class="f-icon">{{ f.icon }}</span>
              <span>{{ f.text }}</span>
            </div>
          </div>
        </div>
        <div class="brand-glow"></div>
      </div>

      <!-- 右侧表单区 -->
      <div class="form-side">
        <div class="form-wrapper">
          <div class="form-header">
            <h3>{{ isLogin ? '欢迎回来' : '创建账户' }}</h3>
            <p>{{ isLogin ? '登录以访问分析平台' : '注册新账户开始使用' }}</p>
          </div>

          <form @submit.prevent="handleSubmit" class="auth-form">
            <div class="input-group">
              <label>用户名</label>
              <div class="input-wrap">
                <span class="input-icon">👤</span>
                <input
                  v-model="form.username"
                  type="text"
                  placeholder="请输入用户名"
                  required
                  autocomplete="username"
                />
              </div>
            </div>

            <template v-if="!isLogin">
              <div class="input-group">
                <label>邮箱</label>
                <div class="input-wrap">
                  <span class="input-icon">📧</span>
                  <input v-model="form.email" type="email" placeholder="请输入邮箱" />
                </div>
              </div>
              <div class="input-group">
                <label>手机号</label>
                <div class="input-wrap">
                  <span class="input-icon">📱</span>
                  <input v-model="form.phone" type="text" placeholder="请输入手机号" />
                </div>
              </div>
            </template>

            <div class="input-group">
              <label>密码</label>
              <div class="input-wrap">
                <span class="input-icon">🔒</span>
                <input
                  v-model="form.password"
                  :type="showPwd ? 'text' : 'password'"
                  placeholder="请输入密码"
                  required
                  autocomplete="current-password"
                />
                <span class="toggle-pwd" @click="showPwd = !showPwd">
                  {{ showPwd ? '🙈' : '👁️' }}
                </span>
              </div>
            </div>

            <div class="input-group" v-if="!isLogin">
              <label>确认密码</label>
              <div class="input-wrap">
                <span class="input-icon">🔒</span>
                <input
                  v-model="form.password_confirm"
                  type="password"
                  placeholder="再次输入密码"
                  required
                />
              </div>
            </div>

            <div v-if="errorMsg" class="error-msg">
              <span>⚠️</span> {{ errorMsg }}
            </div>

            <button type="submit" class="submit-btn" :disabled="loading">
              <span v-if="loading" class="spinner"></span>
              {{ loading ? '处理中...' : (isLogin ? '登 录' : '注 册') }}
            </button>
          </form>

          <div class="form-footer">
            <span>{{ isLogin ? '还没有账户？' : '已有账户？' }}</span>
            <a href="#" @click.prevent="toggleMode">
              {{ isLogin ? '立即注册' : '返回登录' }}
            </a>
          </div>

          <div class="demo-hint" v-if="isLogin">
            <span>演示账户: admin / admin123</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authLogin, authRegister } from '../api'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { setAuth } = useAuth()

const isLogin = ref(true)
const loading = ref(false)
const showPwd = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  password: '',
  password_confirm: '',
  email: '',
  phone: '',
})

const features = [
  { icon: '📊', text: '时空分布分析' },
  { icon: '🎯', text: 'DBSCAN 聚类' },
  { icon: '🔀', text: 'OD 矩阵分析' },
  { icon: '🤖', text: '智能推荐' },
]

function toggleMode() {
  isLogin.value = !isLogin.value
  errorMsg.value = ''
}

function particleStyle(i) {
  const x = Math.random() * 100
  const y = Math.random() * 100
  const size = 2 + Math.random() * 4
  const dur = 15 + Math.random() * 25
  const delay = Math.random() * 10
  return {
    left: `${x}%`,
    top: `${y}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDuration: `${dur}s`,
    animationDelay: `${delay}s`,
  }
}

async function handleSubmit() {
  errorMsg.value = ''
  loading.value = true

  try {
    let res
    if (isLogin.value) {
      res = await authLogin({ username: form.username, password: form.password })
    } else {
      if (form.password !== form.password_confirm) {
        errorMsg.value = '两次密码不一致'
        loading.value = false
        return
      }
      res = await authRegister(form)
    }

    const { token, user } = res.data.data
    setAuth(token, user)
    router.push('/')
  } catch (e) {
    const data = e.response?.data
    if (data?.message) {
      errorMsg.value = data.message
    } else if (data?.errors) {
      const first = Object.values(data.errors)[0]
      errorMsg.value = Array.isArray(first) ? first[0] : first
    } else {
      errorMsg.value = '网络错误，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #060a20;
  position: relative;
  overflow: hidden;
}

// 背景粒子
.bg-particles {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}

.particle {
  position: absolute;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.3);
  animation: floatParticle linear infinite;
  pointer-events: none;
}

@keyframes floatParticle {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.3; }
  25% { transform: translate(30px, -40px) scale(1.2); opacity: 0.6; }
  50% { transform: translate(-20px, -80px) scale(0.8); opacity: 0.4; }
  75% { transform: translate(40px, -30px) scale(1.1); opacity: 0.5; }
}

// 容器
.login-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: 880px;
  min-height: 540px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.5), 0 0 60px rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.12);
}

// 左侧品牌
.brand-side {
  width: 380px;
  background: linear-gradient(135deg, #0d1233 0%, #1a1145 50%, #0d1233 100%);
  padding: 48px 36px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  overflow: hidden;

  .brand-glow {
    position: absolute;
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.15), transparent);
    top: -40px;
    right: -60px;
    pointer-events: none;
  }
}

.brand-content {
  position: relative;
  z-index: 1;

  .brand-icon {
    font-size: 48px;
    margin-bottom: 16px;
    filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.4));
  }

  h1 {
    font-size: 24px;
    font-weight: 700;
    background: linear-gradient(135deg, #e2e8f0, #6366f1);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
  }

  h2 {
    font-size: 16px;
    color: #94a3b8;
    font-weight: 400;
    margin-bottom: 20px;
  }

  .brand-desc {
    font-size: 13px;
    color: #64748b;
    line-height: 1.6;
    margin-bottom: 28px;
  }
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .feature {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    color: #94a3b8;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(99, 102, 241, 0.06);
    border: 1px solid rgba(99, 102, 241, 0.08);
    transition: all 0.3s ease;

    &:hover {
      background: rgba(99, 102, 241, 0.1);
      border-color: rgba(99, 102, 241, 0.2);
    }

    .f-icon { font-size: 16px; }
  }
}

// 右侧表单
.form-side {
  flex: 1;
  background: #0a0e27;
  padding: 48px 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-wrapper {
  width: 100%;
  max-width: 340px;
}

.form-header {
  margin-bottom: 28px;

  h3 {
    font-size: 24px;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 6px;
  }

  p {
    font-size: 13px;
    color: #64748b;
  }
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-group {
  label {
    display: block;
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.input-wrap {
  display: flex;
  align-items: center;
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 10px;
  padding: 0 14px;
  transition: all 0.3s ease;

  &:focus-within {
    border-color: rgba(99, 102, 241, 0.5);
    box-shadow: 0 0 12px rgba(99, 102, 241, 0.1);
  }

  .input-icon {
    font-size: 14px;
    margin-right: 10px;
    opacity: 0.6;
  }

  input {
    flex: 1;
    background: none;
    border: none;
    padding: 12px 0;
    color: #e2e8f0;
    font-size: 14px;
    outline: none;

    &::placeholder { color: #475569; }
  }

  .toggle-pwd {
    cursor: pointer;
    font-size: 14px;
    opacity: 0.6;
    transition: opacity 0.2s;
    &:hover { opacity: 1; }
  }
}

.error-msg {
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
  color: #ef4444;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.submit-btn {
  width: 100%;
  padding: 13px;
  margin-top: 4px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.4);
  }

  &:disabled {
    opacity: 0.6;
    cursor: wait;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.form-footer {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: #64748b;

  a {
    color: #6366f1;
    text-decoration: none;
    font-weight: 500;
    margin-left: 4px;
    transition: color 0.2s;
    &:hover { color: #818cf8; }
  }
}

.demo-hint {
  margin-top: 14px;
  text-align: center;
  font-size: 11px;
  color: #475569;
  padding: 8px;
  background: rgba(99, 102, 241, 0.04);
  border-radius: 6px;
  border: 1px dashed rgba(99, 102, 241, 0.1);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .login-container { flex-direction: column; width: 95%; }
  .brand-side { width: 100%; padding: 30px; min-height: auto; }
  .brand-features { flex-direction: row; flex-wrap: wrap; }
}
</style>
