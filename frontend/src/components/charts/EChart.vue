<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import * as echarts from 'echarts'

const props = defineProps<{
  option: EChartsOption
  onReady?: (chart: echarts.ECharts) => void
}>()

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value, undefined, { renderer: 'canvas' })
  chart.setOption(props.option, true)
  props.onReady?.(chart)
  ro = new ResizeObserver(() => chart?.resize())
  ro.observe(el.value)
})

onUnmounted(() => {
  ro?.disconnect()
  ro = null
  chart?.dispose()
  chart = null
})

watch(
  () => props.option,
  (opt) => {
    chart?.setOption(opt, true)
  },
  { deep: true },
)
</script>

<template>
  <div ref="el" class="h-full w-full" />
</template>
