<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          :class="[`toast-${toast.type}`, { 'toast-exit': !toast.visible }]"
          @click="removeToast(toast.id)"
        >
          <div class="toast-icon">
            <span v-if="toast.type === 'success'">✓</span>
            <span v-else-if="toast.type === 'error'">✕</span>
            <span v-else-if="toast.type === 'warning'">!</span>
            <span v-else>i</span>
          </div>
          <div class="toast-content">{{ toast.message }}</div>
          <div class="toast-close" @click.stop="removeToast(toast.id)">×</div>
          <div class="toast-progress" :style="{ animationDuration: getDuration(toast.type) }"></div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '@/composables/useToast'

const { toasts, removeToast } = useToast()

function getDuration(type) {
  if (type === 'error') return '5s'
  if (type === 'warning') return '4s'
  return '3.5s'
}
</script>

<style lang="scss" scoped>
.toast-container {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: center;
  min-width: 320px;
  max-width: 480px;
  padding: 14px 18px;
  border-radius: 12px;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  cursor: pointer;
  pointer-events: all;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(30, 30, 50, 0.95), rgba(20, 20, 40, 0.9));
    z-index: -1;
  }
}

.toast-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
  margin-right: 12px;
}

.toast-content {
  flex: 1;
  font-size: 13.5px;
  color: rgba(255, 255, 255, 0.92);
  line-height: 1.5;
  letter-spacing: 0.3px;
}

.toast-close {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.35);
  margin-left: 12px;
  flex-shrink: 0;
  transition: color 0.2s;
  &:hover {
    color: rgba(255, 255, 255, 0.8);
  }
}

.toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  border-radius: 0 0 12px 12px;
  animation: toast-progress-shrink linear forwards;
}

@keyframes toast-progress-shrink {
  from { width: 100%; }
  to { width: 0%; }
}

// === Type Variants ===
.toast-success {
  border-color: rgba(0, 230, 160, 0.2);
  .toast-icon {
    background: rgba(0, 230, 160, 0.18);
    color: #00e6a0;
    box-shadow: 0 0 12px rgba(0, 230, 160, 0.2);
  }
  .toast-progress {
    background: linear-gradient(90deg, #00e6a0, #00c896);
  }
}

.toast-error {
  border-color: rgba(255, 85, 85, 0.2);
  .toast-icon {
    background: rgba(255, 85, 85, 0.18);
    color: #ff5555;
    box-shadow: 0 0 12px rgba(255, 85, 85, 0.2);
  }
  .toast-progress {
    background: linear-gradient(90deg, #ff5555, #e04040);
  }
}

.toast-warning {
  border-color: rgba(255, 180, 50, 0.2);
  .toast-icon {
    background: rgba(255, 180, 50, 0.18);
    color: #ffb432;
    box-shadow: 0 0 12px rgba(255, 180, 50, 0.2);
  }
  .toast-progress {
    background: linear-gradient(90deg, #ffb432, #e0a028);
  }
}

.toast-info {
  border-color: rgba(100, 160, 255, 0.2);
  .toast-icon {
    background: rgba(100, 160, 255, 0.18);
    color: #64a0ff;
    box-shadow: 0 0 12px rgba(100, 160, 255, 0.2);
  }
  .toast-progress {
    background: linear-gradient(90deg, #64a0ff, #5090ee);
  }
}

// === Transitions ===
.toast-enter-active {
  animation: toast-slide-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toast-leave-active {
  animation: toast-slide-out 0.35s ease-in forwards;
}

@keyframes toast-slide-in {
  from {
    opacity: 0;
    transform: translateX(80px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes toast-slide-out {
  from {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateX(80px) scale(0.85);
  }
}
</style>
