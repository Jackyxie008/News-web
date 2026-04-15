<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import TopNav from '@/components/TopNav.vue'
import MapPanel from '@/components/MapPanel.vue'
import NewsDetailCard from '@/components/NewsDetailCard.vue'
import {
  fetchNewsById,
  fetchNewsList,
  filterNews,
  type FilterState,
  type Lang,
  type NewsDetail,
  type NewsItem,
} from '@/lib/news'
import { CONTINENTS_EN, CONTINENTS_ZH, getAllCountryOptions } from '@/lib/geo'

const selectedId = ref<string | null>(null)
const lang = ref<Lang>((localStorage.getItem('lang') as Lang) === 'en' ? 'en' : 'zh')
const filter = ref<FilterState>({
  query: '',
  country: null,
  media: null,
  continent: null,
  type: null,
  heat: null,
  timeRange: null,
})

const allItems = ref<NewsItem[]>([])
const filteredItems = computed(() => filterNews(allItems.value, filter.value))
const selectedDetail = ref<NewsDetail | null>(null)

const typeOptions = computed(() => {
  const list = new Set(allItems.value.map((n) => n.type))
  return [...list].map((value) => ({ label: value, value }))
})
const continentOptions = computed(() => {
  const values = lang.value === 'en' ? CONTINENTS_EN : CONTINENTS_ZH
  return values.map((value) => ({ label: value, value }))
})
const countryOptions = computed(() => {
  return getAllCountryOptions(lang.value)
})

function onSelectNews(news: NewsItem | null) {
  selectedId.value = news?.id ?? null
}

function onCloseDetail() {
  selectedId.value = null
  selectedDetail.value = null
}

function onChangeLang(value: Lang) {
  lang.value = value
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

onMounted(async () => {
  try {
    allItems.value = await fetchNewsList(lang.value)
  } catch (error) {
    console.error(error)
    allItems.value = []
  }
})

watch(selectedId, async (id) => {
  if (!id) {
    selectedDetail.value = null
    return
  }
  try {
    selectedDetail.value = await fetchNewsById(id, lang.value)
  } catch (error) {
    console.error(error)
    selectedDetail.value = null
  }
})

watch(lang, async (nextLang) => {
  localStorage.setItem('lang', nextLang)
  // 防止中英文切换后旧语言筛选值导致结果为空
  filter.value = {
    ...filter.value,
    type: null,
    continent: null,
    country: null,
    media: null,
    heat: null,
  }
  try {
    allItems.value = await fetchNewsList(nextLang)
  } catch (error) {
    console.error(error)
    allItems.value = []
  }
  if (!selectedId.value) {
    selectedDetail.value = null
    return
  }
  try {
    selectedDetail.value = await fetchNewsById(selectedId.value, nextLang)
  } catch (error) {
    console.error(error)
    selectedDetail.value = null
  }
})
</script>

<template>
  <main class="relative h-screen w-screen overflow-hidden bg-black">
    <MapPanel :items="filteredItems" :selected-id="selectedId" :lang="lang" @select="onSelectNews" />
    <NewsDetailCard
      :visible="Boolean(selectedId)"
      :lang="lang"
      :detail="selectedDetail"
      @close="onCloseDetail"
    />
    <div class="absolute inset-x-0 top-0 z-[1000]">
      <TopNav
        :lang="lang"
        :query="filter.query"
        :type="filter.type"
        :continent="filter.continent"
        :country="filter.country"
        :type-options="typeOptions"
        :continent-options="continentOptions"
        :country-options="countryOptions"
        @update:lang="onChangeLang"
        @update:query="(value) => (filter.query = value)"
        @update:type="(value) => (filter.type = value)"
        @update:continent="(value) => (filter.continent = value)"
        @update:country="(value) => (filter.country = value)"
        @reset="onReset"
      />
    </div>
  </main>
</template>
