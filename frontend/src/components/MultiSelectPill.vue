<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Check, X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = defineProps<{
  modelValue: string[]
  placeholder: string
  options: { label: string; value: string }[]
  widthClass?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const query = ref('')

const selectedCount = computed(() => props.modelValue.length)

const displayText = computed(() => {
  if (selectedCount.value === 0) return props.placeholder
  if (selectedCount.value === 1) {
    const option = props.options.find((o) => o.value === props.modelValue[0])
    return option?.label ?? props.modelValue[0]
  }
  return `${props.placeholder} (${selectedCount.value})`
})

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.options
  return props.options.filter((o) => `${o.label} ${o.value}`.toLowerCase().includes(q))
})

function toggle() {
  open.value = true
  nextTick(() => inputRef.value?.focus())
}

function close() {
  open.value = false
  query.value = ''
}

function isSelected(value: string) {
  return props.modelValue.includes(value)
}

function onSelect(value: string) {
  const newValue = isSelected(value)
    ? props.modelValue.filter((v) => v !== value)
    : [...props.modelValue, value]
  emit('update:modelValue', newValue)
}

function clearAll() {
  emit('update:modelValue', [])
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
    if (value.length === 0) {
      query.value = ''
    }
  },
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
      <span
        class="w-full truncate pr-8 text-[16px] leading-4 tracking-normal"
        :class="selectedCount > 0 ? 'text-zinc-900' : 'text-[#b3b3b3]'"
      >
        {{ displayText }}
      </span>
      <div class="pointer-events-none absolute right-1 top-1/2 flex -translate-y-1/2 items-center gap-0.5">
        <button
          class="pointer-events-auto inline-flex items-center justify-center rounded-sm p-0.5 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
          :class="selectedCount > 0 ? 'opacity-100' : 'opacity-40'"
          type="button"
          aria-label="清除"
          @mousedown.prevent.stop
          @click.prevent.stop="clearAll"
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <div
      v-if="open"
      class="absolute right-0 top-[34px] z-20 w-full min-w-[220px] overflow-hidden rounded-xl bg-white shadow-[0_10px_30px_rgba(0,0,0,0.18)] ring-1 ring-black/10"
    >
      <div class="border-b border-zinc-100 p-2">
        <input
          ref="inputRef"
          v-model="query"
          class="w-full bg-transparent px-3 py-2 text-sm outline-none placeholder:text-zinc-400"
          type="text"
          placeholder="搜索..."
          @input.stop
        />
      </div>
      <div class="max-h-64 overflow-y-auto">
        <button
          v-for="o in filteredOptions"
          :key="o.value"
          class="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-zinc-50"
          type="button"
          @click="onSelect(o.value)"
        >
          <span
            class="mr-2 flex h-4 w-4 items-center justify-center rounded border"
            :class="isSelected(o.value) ? 'border-zinc-900 bg-zinc-900' : 'border-zinc-300'"
          >
            <Check v-if="isSelected(o.value)" class="h-3 w-3 text-white" />
          </span>
          {{ o.label }}
        </button>
      </div>
    </div>
  </div>
</template>
