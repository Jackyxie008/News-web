<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Calendar, ChevronDown, X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = defineProps<{
  modelValue: { start: string; end: string } | null
  lang: 'zh' | 'en'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: { start: string; end: string } | null]
}>()

const open = ref(false)
const customMode = ref(false)
const now = new Date()
const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
const startDate = ref(new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10))
const endDate = ref(today.toISOString().slice(0, 10))

// 预设选项配置
const presets = computed(() => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

  return [
    {
      label: props.lang === 'en' ? 'Last 24h' : '最近24小时',
      value: '24h',
      start: new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      end: today.toISOString().slice(0, 10),
    },
    {
      label: props.lang === 'en' ? 'Last 3 days' : '最近3天',
      value: '3d',
      start: new Date(today.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      end: today.toISOString().slice(0, 10),
    },
    {
      label: props.lang === 'en' ? 'Last 7 days' : '最近7天',
      value: '7d',
      start: new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      end: today.toISOString().slice(0, 10),
    },
  ]
})

// 当前选中的预设
const selectedPreset = computed(() => {
  if (!props.modelValue || customMode.value) return null
  const start = props.modelValue.start
  const end = props.modelValue.end
  return presets.value.find((p) => p.start === start && p.end === end)?.value ?? null
})

// 显示文本
const displayText = computed(() => {
  if (customMode.value && startDate.value && endDate.value) {
    return `${startDate.value} ~ ${endDate.value}`
  }
  if (selectedPreset.value) {
    return presets.value.find((p) => p.value === selectedPreset.value)?.label
  }
  return props.lang === 'en' ? 'Time Range' : '时间范围'
})

function selectPreset(preset: (typeof presets.value)[0]) {
  emit('update:modelValue', { start: preset.start, end: preset.end })
  customMode.value = false
  open.value = false
}

function enableCustomMode() {
  customMode.value = true
  // 初始化日期值
  if (props.modelValue) {
    startDate.value = props.modelValue.start
    endDate.value = props.modelValue.end
  } else {
    const now = new Date()
    endDate.value = now.toISOString().slice(0, 10)
    startDate.value = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
  }
}

function applyCustomRange() {
  if (startDate.value && endDate.value && startDate.value <= endDate.value) {
    emit('update:modelValue', { start: startDate.value, end: endDate.value })
    open.value = false
  }
}

function clearSelection() {
  emit('update:modelValue', null)
  customMode.value = false
  open.value = false
}

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

function onClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.time-range-picker')) {
    open.value = false
  }
}

// 默认选择最近24小时
onMounted(() => {
  if (!props.modelValue) {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    emit('update:modelValue', {
      start: new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      end: today.toISOString().slice(0, 10),
    })
  }
})
</script>

<template>
  <div class="relative time-range-picker" @click="onClickOutside">
    <div @click.stop>
      <div
        :class="
          cn(
            'flex h-[28px] items-center gap-1.5 rounded-lg bg-white px-[6px] py-[6px] text-left text-[14px]',
            open ? 'ring-1 ring-black/20' : '',
          )
        "
        @click="toggle"
      >
        <Calendar class="h-4 w-4 text-zinc-500" />
        <span :class="displayText === (props.lang === 'en' ? 'Time Range' : '时间范围') ? 'text-[#b3b3b3]' : 'text-zinc-900'">
          {{ displayText }}
        </span>
        <button
          v-if="props.modelValue"
          class="ml-1 inline-flex items-center justify-center rounded-sm p-0.5 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
          type="button"
          aria-label="清除"
          @click.stop="clearSelection"
        >
          <X class="h-3.5 w-3.5" />
        </button>
        <ChevronDown class="h-4 w-4 text-zinc-500" :class="open ? 'rotate-180' : ''" />
      </div>

      <!-- 下拉面板 -->
      <div
        v-if="open"
        class="absolute right-0 top-[36px] z-50 w-[320px] max-h-[400px] overflow-hidden rounded-xl bg-white shadow-[0_10px_30px_rgba(0,0,0,0.18)] ring-1 ring-black/10"
      >
        <!-- 预设选项 -->
        <div class="border-b border-zinc-100 p-2">
          <div class="mb-1 px-2 text-xs text-zinc-500">
            {{ props.lang === 'en' ? 'Quick Select' : '快速选择' }}
          </div>
          <button
            v-for="preset in presets"
            :key="preset.value"
            class="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-zinc-50"
            :class="selectedPreset === preset.value ? 'bg-zinc-100 text-zinc-900' : 'text-zinc-700'"
            type="button"
            @click="selectPreset(preset)"
          >
            {{ preset.label }}
          </button>
        </div>

        <!-- 自定义范围 -->
        <div class="p-3">
          <div class="mb-2 text-xs text-zinc-500">
            {{ props.lang === 'en' ? 'Custom Range' : '自定义范围' }}
          </div>
          <div class="flex items-center gap-2">
            <input
              v-model="startDate"
              type="date"
              class="flex-1 rounded-md border border-zinc-200 px-2 py-1.5 text-sm focus:border-zinc-400 focus:outline-none"
              @focus="enableCustomMode"
            />
            <span class="text-zinc-400">~</span>
            <input
              v-model="endDate"
              type="date"
              class="flex-1 rounded-md border border-zinc-200 px-2 py-1.5 text-sm focus:border-zinc-400 focus:outline-none"
              @focus="enableCustomMode"
            />
          </div>
          <button
            v-if="customMode && startDate && endDate && startDate <= endDate"
            class="mt-2 w-full rounded-md bg-zinc-900 py-1.5 text-sm text-white hover:bg-zinc-800"
            type="button"
            @click="applyCustomRange"
          >
            {{ props.lang === 'en' ? 'Apply' : '应用' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
