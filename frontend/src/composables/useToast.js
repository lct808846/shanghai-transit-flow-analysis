import { reactive } from 'vue'

const state = reactive({
    toasts: [],
    idCounter: 0,
})

/**
 * 全局 Toast 通知管理
 * 使用: const { showToast, showSuccess, showError, showWarning } = useToast()
 */
export function useToast() {
    function showToast(message, type = 'info', duration = 3500) {
        const id = ++state.idCounter
        const toast = { id, message, type, visible: true }
        state.toasts.push(toast)

        // 自动消失
        setTimeout(() => {
            removeToast(id)
        }, duration)

        return id
    }

    function removeToast(id) {
        const idx = state.toasts.findIndex((t) => t.id === id)
        if (idx !== -1) {
            state.toasts[idx].visible = false
            setTimeout(() => {
                state.toasts.splice(idx, 1)
            }, 400) // 等待退出动画
        }
    }

    function showSuccess(message, duration) {
        return showToast(message, 'success', duration)
    }

    function showError(message, duration = 5000) {
        return showToast(message, 'error', duration)
    }

    function showWarning(message, duration = 4000) {
        return showToast(message, 'warning', duration)
    }

    function showInfo(message, duration) {
        return showToast(message, 'info', duration)
    }

    return {
        toasts: state.toasts,
        showToast,
        showSuccess,
        showError,
        showWarning,
        showInfo,
        removeToast,
    }
}
