import { reactive } from 'vue'

// 简单的全局状态管理（不引入 Pinia 保持轻量）
const state = reactive({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
})

export function useAuth() {
    const isLoggedIn = () => !!state.token

    const getUser = () => state.user

    const getToken = () => state.token

    const setAuth = (token, user) => {
        state.token = token
        state.user = user
        localStorage.setItem('token', token)
        localStorage.setItem('user', JSON.stringify(user))
    }

    const clearAuth = () => {
        state.token = ''
        state.user = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
    }

    const isAdmin = () => state.user?.role === 'admin' || false
    const isAnalyst = () => ['admin', 'analyst'].includes(state.user?.role) || false

    return { state, isLoggedIn, getUser, getToken, setAuth, clearAuth, isAdmin, isAnalyst }
}
