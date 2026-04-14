<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
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

const label = computed(() => {
  const current = props.options.find((o) => o.value === props.modelValue)
  return current?.label ?? props.placeholder
})

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

function onSelect(value: string | null) {
  emit('update:modelValue', value)
  close()
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
</script>

<template>
  <div ref="rootRef" class="relative">
    <button
      :class="
        cn(
          'flex h-[28px] items-center gap-2 rounded-lg bg-white px-[6px] py-[6px] text-left',
          props.widthClass ?? 'w-[117px]',
        )
      "
      type="button"
      @click="toggle"
    >
      <p
        class="flex-1 truncate text-[16px] leading-4 tracking-normal"
        :class="props.modelValue ? 'text-zinc-900' : 'text-[#b3b3b3]'"
      >
        {{ label }}
      </p>
      <ChevronDown class="h-4 w-4 text-zinc-900" />
    </button>

    <div
      v-if="open"
      class="absolute left-0 top-[34px] z-20 w-[220px] overflow-hidden rounded-xl bg-white shadow-[0_10px_30px_rgba(0,0,0,0.18)] ring-1 ring-black/10"
    >
      <button
        class="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-zinc-50"
        type="button"
        @click="onSelect(null)"
      >
        全部
      </button>
      <button
        v-for="o in props.options"
        :key="o.value"
        class="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-zinc-50"
        type="button"
        @click="onSelect(o.value)"
      >
        {{ o.label }}
      </button>
    </div>
  </div>
</template>
