<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import TopNav from '@/components/TopNav.vue'
import MapPanel from '@/components/MapPanel.vue'
import { filterNews, mockNews, type FilterState, type NewsItem } from '@/lib/news'

const selectedId = ref<string | null>(null)
const filter = ref<FilterState>({
  query: '',
  country: null,
  media: null,
  continent: null,
  type: null,
  heat: null,
  timeRange: null,
})

const filteredItems = computed(() => filterNews(mockNews, filter.value))

const typeOptions = computed(() => {
  const list = new Set(mockNews.map((n) => n.type))
  return [...list].map((value) => ({ label: value, value }))
})
const mediaOptions = computed(() => {
  const list = new Set(mockNews.map((n) => n.media))
  return [...list].map((value) => ({ label: value, value }))
})
const continentOptions = computed(() => {
  const list = new Set(mockNews.map((n) => n.continent))
  return [...list].map((value) => ({ label: value, value }))
})
const countryOptions = computed(() => {
  const list = new Set(mockNews.map((n) => n.country))
  return [...list].map((value) => ({ label: value, value }))
})

watch(filteredItems, (items) => {
  if (!selectedId.value) return
  const exists = items.some((n) => n.id === selectedId.value)
  if (!exists) selectedId.value = null
})

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
}
</script>

<template>
  <main class="relative h-screen w-screen overflow-hidden bg-black">
    <MapPanel :items="filteredItems" :selected-id="selectedId" @select="onSelectNews" />
    <div class="absolute inset-x-0 top-0 z-[1000]">
      <TopNav
        :query="filter.query"
        :type="filter.type"
        :media="filter.media"
        :continent="filter.continent"
        :country="filter.country"
        :heat="filter.heat"
        :type-options="typeOptions"
        :media-options="mediaOptions"
        :continent-options="continentOptions"
        :country-options="countryOptions"
        @update:query="(value) => (filter.query = value)"
        @update:type="(value) => (filter.type = value)"
        @update:media="(value) => (filter.media = value)"
        @update:continent="(value) => (filter.continent = value)"
        @update:country="(value) => (filter.country = value)"
        @update:heat="(value) => (filter.heat = value)"
        @reset="onReset"
      />
    </div>
  </main>
</template>
