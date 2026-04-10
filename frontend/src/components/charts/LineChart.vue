<script setup lang="ts">
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { ECharts } from 'echarts'
import EChart from '@/components/charts/EChart.vue'
import type { LineDatum } from '@/lib/news'

const props = defineProps<{ data: LineDatum[] }>()
const emit = defineEmits<{ range: [range: { start: string; end: string } | null] }>()

const option = computed<EChartsOption>(() => {
  const x = props.data.map((d) => d.date)
  const y = props.data.map((d) => d.value)

  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 18, bottom: 40 },
    xAxis: {
      type: 'category',
      data: x,
      axisLabel: { color: '#52525b', fontSize: 10 },
      axisLine: { lineStyle: { color: '#e4e4e7' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#52525b', fontSize: 10 },
      splitLine: { lineStyle: { color: '#f4f4f5' } },
    },
    dataZoom: [
      {
        type: 'inside',
        throttle: 50,
      },
    ],
    series: [
      {
        type: 'line',
        data: y,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#111827', width: 2 },
        itemStyle: { color: '#111827' },
        areaStyle: { color: 'rgba(17,24,39,0.08)' },
      },
    ],
  }
})

function onReady(chart: ECharts) {
  chart.off('datazoom')
  chart.on('datazoom', () => {
    const opt = chart.getOption() as unknown
    const dz0 =
      typeof opt === 'object' && opt && 'dataZoom' in opt
        ? (opt as { dataZoom?: unknown }).dataZoom
        : undefined
    const dz = Array.isArray(dz0)
      ? (dz0[0] as { startValue?: unknown; endValue?: unknown } | undefined)
      : undefined
    const startValue = dz?.startValue
    const endValue = dz?.endValue

    if (typeof startValue === 'number' && typeof endValue === 'number') {
      const start = props.data[startValue]?.date
      const end = props.data[endValue]?.date
      if (start && end) {
        emit('range', { start, end })
        return
      }
    }
    emit('range', null)
  })
}
</script>

<template>
  <EChart class="h-[240px] w-full" :option="option" :on-ready="onReady" />
</template>
