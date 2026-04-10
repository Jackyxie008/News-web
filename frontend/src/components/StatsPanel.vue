<script setup lang="ts">
import PanelCard from '@/components/PanelCard.vue'
import PieChart from '@/components/charts/PieChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import type { ChartData, FilterState } from '@/lib/news'

const props = defineProps<{
  charts: ChartData
  filter: FilterState
}>()

const emit = defineEmits<{ 'update:filter': [next: FilterState] }>()

function patchFilter(partial: Partial<FilterState>) {
  emit('update:filter', { ...props.filter, ...partial })
}
</script>

<template>
  <div class="flex h-full flex-col p-4">
    <PanelCard class="flex flex-col p-4">
      <div class="flex items-center justify-between">
        <div class="text-sm font-semibold text-zinc-900">分类占比</div>
        <div class="text-xs text-zinc-500">当前筛选</div>
      </div>
      <PieChart
        class="mt-3"
        :data="props.charts.pie"
        @select="(name) => patchFilter({ type: name })"
      />
    </PanelCard>

    <PanelCard class="mt-4 flex min-h-0 flex-1 flex-col p-4">
      <div class="flex items-center justify-between">
        <div class="text-sm font-semibold text-zinc-900">趋势</div>
        <div class="text-xs text-zinc-500">拖拽缩放</div>
      </div>
      <div class="mt-3 min-h-0 flex-1">
        <LineChart :data="props.charts.line" @range="(r) => patchFilter({ timeRange: r })" />
      </div>
      <div class="mt-2 text-xs text-zinc-500">
        <span v-if="props.filter.timeRange"
          >{{ props.filter.timeRange.start }} - {{ props.filter.timeRange.end }}</span
        >
        <span v-else>全部时间</span>
      </div>
    </PanelCard>
  </div>
</template>
