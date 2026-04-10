<script setup lang="ts">
import { List } from 'lucide-vue-next'

function onMenu() {}
</script>

<template>
  <header class="h-[61px] bg-[#d9d9d9]">
    <div class="mx-auto flex h-full max-w-[1440px] items-center justify-between px-6">
      <div class="flex items-center gap-3">
        <div class="h-7 w-7 rounded-lg bg-black" />
        <div class="text-sm font-semibold text-black">News Globe</div>
      </div>

      <button
        class="inline-flex h-[27px] w-[27px] items-center justify-center text-black hover:opacity-80"
        type="button"
        aria-label="菜单"
        @click="onMenu"
      >
        <List class="h-[27px] w-[27px]" />
      </button>
    </div>
  </header>
</template>
