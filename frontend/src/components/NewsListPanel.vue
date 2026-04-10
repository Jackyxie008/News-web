<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import PanelCard from '@/components/PanelCard.vue'
import SearchPill from '@/components/SearchPill.vue'
import SelectPill from '@/components/SelectPill.vue'
import ResetButton from '@/components/ResetButton.vue'
import VirtualList from '@/components/VirtualList.vue'
import type { FilterState, NewsItem } from '@/lib/news'
import { cn } from '@/lib/utils'

const props = defineProps<{
  allItems: NewsItem[]
  items: NewsItem[]
  selectedId: string | null
  filter: FilterState
}>()

const emit = defineEmits<{
  reset: []
  select: [news: NewsItem | null]
  'update:filter': [next: FilterState]
}>()

const listRef = ref<{ scrollToIndex: (index: number) => void } | null>(null)

const countries = computed(() => {
  const set = new Map<string, string>()
  for (const n of props.allItems) set.set(n.country, n.country)
  return [...set.keys()].sort().map((v) => ({ label: v, value: v }))
})

const medias = computed(() => {
  const set = new Map<string, string>()
  for (const n of props.allItems) set.set(n.media, n.media)
  return [...set.keys()].sort().map((v) => ({ label: v, value: v }))
})

const continents = computed(() => {
  const set = new Map<string, string>()
  for (const n of props.allItems) set.set(n.continent, n.continent)
  return [...set.keys()].sort().map((v) => ({ label: v, value: v }))
})

const types = computed(() => {
  const set = new Map<string, string>()
  for (const n of props.allItems) set.set(n.type, n.type)
  return [...set.keys()].sort().map((v) => ({ label: v, value: v }))
})

const heatOptions = [
  { label: '热度', value: 'hot' },
  { label: '时间', value: 'time' },
]

function patchFilter(partial: Partial<FilterState>) {
  emit('update:filter', { ...props.filter, ...partial })
}

function onSelect(news: NewsItem) {
  emit('select', news)
}

watch(
  () => props.selectedId,
  (id) => {
    if (!id) return
    const index = props.items.findIndex((n) => n.id === id)
    if (index >= 0) listRef.value?.scrollToIndex(index)
  },
)
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="p-4">
      <div class="flex flex-wrap items-center gap-3">
        <SearchPill
          :model-value="props.filter.query"
          placeholder="搜索"
          @update:model-value="(v) => patchFilter({ query: v })"
        />

        <SelectPill
          :model-value="props.filter.country"
          placeholder="国家/地区"
          :options="countries"
          @update:model-value="(v) => patchFilter({ country: v })"
        />

        <SelectPill
          :model-value="props.filter.media"
          placeholder="新闻媒体"
          :options="medias"
          @update:model-value="(v) => patchFilter({ media: v })"
        />

        <SelectPill
          :model-value="props.filter.continent"
          placeholder="大洲"
          :options="continents"
          @update:model-value="(v) => patchFilter({ continent: v })"
        />

        <SelectPill
          :model-value="props.filter.type"
          placeholder="新闻类型"
          :options="types"
          @update:model-value="(v) => patchFilter({ type: v })"
        />

        <div class="ml-auto flex items-center gap-3">
          <SelectPill
            :model-value="props.filter.heat"
            placeholder="热度"
            :options="heatOptions"
            width-class="w-[117px]"
            @update:model-value="(v) => patchFilter({ heat: v as FilterState['heat'] })"
          />
          <ResetButton @click="emit('reset')" />
        </div>
      </div>
    </div>

    <PanelCard class="mx-4 mb-4 flex min-h-0 flex-1 flex-col overflow-hidden">
      <div class="border-b border-zinc-200 px-4 py-3 text-sm font-semibold text-zinc-900">
        新闻列表
        <span class="ml-2 text-xs font-normal text-zinc-500">{{ props.items.length }}</span>
      </div>

      <VirtualList
        ref="listRef"
        class="min-h-0 flex-1"
        :items="props.items"
        :item-height="84"
        :overscan="8"
        :get-key="(item) => item.id"
      >
        <template #default="{ item }">
          <button
            class="flex h-full w-full flex-col justify-center px-4 text-left transition"
            :class="
              cn(
                'border-b border-zinc-100 hover:bg-zinc-50',
                item.id === props.selectedId && 'bg-zinc-100',
              )
            "
            type="button"
            @click="onSelect(item)"
          >
            <div class="line-clamp-1 text-sm font-semibold text-zinc-900">
              {{ item.title }}
            </div>
            <div class="mt-1 flex items-center gap-2 text-xs text-zinc-500">
              <span>{{ item.date }}</span>
              <span>·</span>
              <span>{{ item.media }}</span>
              <span>·</span>
              <span>{{ item.country }}</span>
            </div>
            <div class="mt-1 line-clamp-1 text-xs text-zinc-600">
              {{ item.summary }}
            </div>
          </button>
        </template>
      </VirtualList>
    </PanelCard>
  </div>
</template>
