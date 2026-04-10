<script setup lang="ts">
defineEmits<{ click: [] }>()
</script>

<template>
  <button
    class="flex h-[28px] w-[56px] items-center justify-center gap-2 overflow-hidden rounded-lg bg-[#2c2c2c] px-[11px] text-[16px] leading-4 text-white"
    type="button"
    @click="$emit('click')"
  >
    重设
  </button>
</template>
