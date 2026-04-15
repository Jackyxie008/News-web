<script setup lang="ts">
import { Search, X } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}

function clearInput() {
  emit('update:modelValue', '')
}
</script>

<template>
  <div
    class="flex h-[40px] w-full max-w-[281px] items-center gap-2 overflow-hidden rounded-full border border-[#e5e7eb] bg-white px-4 py-3"
  >
    <input
      :value="props.modelValue"
      :placeholder="props.placeholder ?? '搜索'"
      class="w-full bg-transparent text-[16px] leading-4 text-zinc-900 outline-none placeholder:text-[#9ca3af]"
      type="text"
      @input="onInput"
    />
    <button
      class="flex items-center justify-center p-0.5"
      :class="props.modelValue ? 'opacity-100' : 'opacity-40'"
      type="button"
      aria-label="清除"
      @click="clearInput"
    >
      <X class="h-3 w-3 text-zinc-900" />
    </button>
    <div class="flex items-center justify-center p-0.5">
      <Search class="h-3 w-3 text-zinc-900" />
    </div>
  </div>
</template>
