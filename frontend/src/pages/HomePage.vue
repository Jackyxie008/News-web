<script setup lang="ts">
import { computed, ref } from 'vue'
import TopNav from '@/components/TopNav.vue'
import NewsListPanel from '@/components/NewsListPanel.vue'
import MapPanel from '@/components/MapPanel.vue'
import StatsPanel from '@/components/StatsPanel.vue'
import { buildChartData, filterNews, mockNews, type FilterState, type NewsItem } from '@/lib/news'

const filter = ref<FilterState>({
  query: '',
  country: null,
  media: null,
  continent: null,
  type: null,
  heat: null,
  timeRange: null,
})

const selectedId = ref<string | null>(null)

const filtered = computed(() => filterNews(mockNews, filter.value))

const charts = computed(() => buildChartData(filtered.value))

function onSelectNews(news: NewsItem | null) {
  selectedId.value = news?.id ?? null
}

function onReset() {
  filter.value = {
    query: '',
    country: null,
    media: null,
    continent: null,
    type: null,
    heat: null,
    timeRange: null,
  }
  selectedId.value = null
}

function onUpdateFilter(next: FilterState) {
  filter.value = next
}
</script>

<template>
  <div class="h-screen w-full bg-black">
    <div class="grid h-full grid-rows-[61px_minmax(0,1fr)]">
      <TopNav />
      <div class="grid h-full grid-cols-[360px_minmax(0,1fr)_360px] bg-black">
        <div class="h-full bg-[#d9d9d9]">
          <NewsListPanel
            :all-items="mockNews"
            :filter="filter"
            :items="filtered"
            :selected-id="selectedId"
            @reset="onReset"
            @update:filter="onUpdateFilter"
            @select="onSelectNews"
          />
        </div>
        <div class="h-full bg-black">
          <MapPanel :items="filtered" :selected-id="selectedId" @select="onSelectNews" />
        </div>
        <div class="h-full bg-[#d9d9d9]">
          <StatsPanel :charts="charts" :filter="filter" @update:filter="onUpdateFilter" />
        </div>
      </div>
    </div>
  </div>
</template>
