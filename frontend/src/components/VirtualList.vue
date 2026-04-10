<script setup lang="ts" generic="T">
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  items: T[]
  itemHeight: number
  overscan?: number
  getKey: (item: T, index: number) => string
  class?: string
}>()

const rootRef = ref<HTMLDivElement | null>(null)
const scrollTop = ref(0)
const viewportHeight = ref(0)

const overscan = computed(() => props.overscan ?? 6)

const totalHeight = computed(() => props.items.length * props.itemHeight)

const startIndex = computed(() => {
  const raw = Math.floor(scrollTop.value / props.itemHeight) - overscan.value
  return Math.max(0, raw)
})

const endIndex = computed(() => {
  const visibleCount = Math.ceil(viewportHeight.value / props.itemHeight)
  return Math.min(props.items.length, startIndex.value + visibleCount + overscan.value * 2)
})

const slice = computed(() => props.items.slice(startIndex.value, endIndex.value))

function onScroll() {
  if (!rootRef.value) return
  scrollTop.value = rootRef.value.scrollTop
}

async function measure() {
  await nextTick()
  if (!rootRef.value) return
  viewportHeight.value = rootRef.value.clientHeight
}

function scrollToIndex(index: number) {
  if (!rootRef.value) return
  rootRef.value.scrollTop = Math.max(0, index * props.itemHeight - props.itemHeight)
}

defineExpose({ scrollToIndex })

onMounted(() => {
  measure()
})

watch(
  () => props.items.length,
  () => {
    measure()
  },
)
</script>

<template>
  <div ref="rootRef" class="relative overflow-y-auto" :class="$props.class" @scroll="onScroll">
    <div :style="{ height: totalHeight + 'px' }" />
    <div
      class="absolute left-0 top-0 w-full"
      :style="{ transform: `translateY(${startIndex * itemHeight}px)` }"
    >
      <div
        v-for="(item, i) in slice"
        :key="getKey(item, startIndex + i)"
        :style="{ height: itemHeight + 'px' }"
      >
        <slot :item="item" :index="startIndex + i" />
      </div>
    </div>
  </div>
</template>
