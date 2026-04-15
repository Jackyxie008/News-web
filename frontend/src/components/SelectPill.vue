<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ChevronDown, X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = defineProps<{
  modelValue: string | null
  placeholder: string
  options: { label: string; value: string }[]
  widthClass?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const query = ref('')

const label = computed(() => {
  const current = props.options.find((o) => o.value === props.modelValue)
  return current?.label ?? props.placeholder
})

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.options
  return props.options.filter((o) => `${o.label} ${o.value}`.toLowerCase().includes(q))
})

function toggle() {
  // 点击筛选框时只执行“打开”，避免 input focus 与 button toggle 冲突造成闪烁
  open.value = true
  nextTick(() => inputRef.value?.focus())
}

function close() {
  open.value = false
}

function onSelect(value: string | null) {
  emit('update:modelValue', value)
  const current = props.options.find((o) => o.value === value)
  query.value = current?.label ?? ''
  close()
}

function onInput() {
  if (props.modelValue !== null) {
    emit('update:modelValue', null)
  }
}

function clearInput() {
  query.value = ''
  emit('update:modelValue', null)
  nextTick(() => inputRef.value?.focus())
}

function onPointerDown(e: MouseEvent) {
  if (!open.value) return
  const root = rootRef.value
  if (!root) return
  if (root.contains(e.target as Node)) return
  close()
}

onMounted(() => {
  document.addEventListener('mousedown', onPointerDown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onPointerDown)
})

watch(
  () => props.modelValue,
  (value) => {
    const current = props.options.find((o) => o.value === value)
    query.value = current?.label ?? ''
  },
  { immediate: true },
)
</script>

<template>
  <div ref="rootRef" class="relative">
    <div
      :class="
        cn(
          'relative flex h-[28px] items-center overflow-hidden rounded-lg bg-white px-[6px] py-[6px] text-left',
          props.widthClass ?? 'w-[170px]',
        )
      "
      @click="toggle"
    >
      <input
        ref="inputRef"
        v-model="query"
        class="w-full bg-transparent pr-8 text-[16px] leading-4 tracking-normal outline-none"
        :class="query ? 'text-zinc-900' : 'text-[#b3b3b3]'"
        :placeholder="label"
        type="text"
        @focus="open = true"
        @input="onInput"
        @click.stop
      />
      <div class="pointer-events-none absolute right-1 top-1/2 flex -translate-y-1/2 items-center gap-0.5">
        <button
          class="pointer-events-auto inline-flex items-center justify-center rounded-sm p-0.5 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
          :class="query || props.modelValue ? 'opacity-100' : 'opacity-40'"
          type="button"
          aria-label="清除"
          @mousedown.prevent.stop
          @click.prevent.stop="clearInput"
        >
          <X class="h-3.5 w-3.5" />
        </button>
        <ChevronDown class="h-4 w-4 text-zinc-900" />
      </div>
    </div>

    <div
      v-if="open"
      class="absolute left-0 top-[34px] z-20 w-full min-w-[220px] overflow-hidden rounded-xl bg-white shadow-[0_10px_30px_rgba(0,0,0,0.18)] ring-1 ring-black/10"
    >
      <button
        class="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-zinc-50"
        type="button"
        @click="onSelect(null)"
      >
        全部
      </button>
      <div class="max-h-64 overflow-y-auto">
        <button
          v-for="o in filteredOptions"
          :key="o.value"
          class="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-zinc-50"
          type="button"
          @click="onSelect(o.value)"
        >
          {{ o.label }}
        </button>
      </div>
    </div>
  </div>
</template>
