<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{ class?: string }>()
</script>

<template>
  <div :class="cn('rounded-2xl bg-white', $props.class)">
    <slot />
  </div>
</template>
