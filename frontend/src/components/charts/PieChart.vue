<script setup lang="ts">
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { ECharts } from 'echarts'
import EChart from '@/components/charts/EChart.vue'
import type { PieDatum } from '@/lib/news'

const props = defineProps<{ data: PieDatum[] }>()
const emit = defineEmits<{ select: [name: string] }>()

const option = computed<EChartsOption>(() => {
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 2,
        },
        label: { show: false },
        emphasis: { scale: true, scaleSize: 6 },
        data: props.data.map((d) => ({ name: d.name, value: d.value })),
      },
    ],
  }
})

function onReady(chart: ECharts) {
  chart.off('click')
  chart.on('click', (params: { name?: unknown } | undefined) => {
    const name = params?.name
    if (typeof name === 'string' && name) emit('select', name)
  })
}
</script>

<template>
  <EChart class="h-[220px] w-full" :option="option" :on-ready="onReady" />
</template>
