<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import TopNav from '@/components/TopNav.vue'
import MapPanel from '@/components/MapPanel.vue'
import NewsDetailCard from '@/components/NewsDetailCard.vue'
import {
  fetchNewsById,
  fetchNewsList,
  filterNews,
  getNewsTypeLabel,
  NEWS_TYPE_MAP,
  type FilterState,
  type Lang,
  type NewsDetail,
  type NewsItem,
} from '@/lib/news'
import { CONTINENTS_EN, CONTINENTS_ZH, getAllCountryOptions } from '@/lib/geo'

const selectedId = ref<string | null>(null)
const lang = ref<Lang>((localStorage.getItem('lang') as Lang) === 'en' ? 'en' : 'zh')
const mode = ref<'hot' | 'all'>('hot')
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
const hasMore = ref(false)
const isLoading = ref(false)
const filterKey = ref(0) // 用于追踪筛选变化

const filteredBaseItems = computed(() => filterNews(allItems.value, filter.value))
const filteredItems = computed(() => {
  if (mode.value === 'hot') {
    return filteredBaseItems.value.slice().sort((a, b) => b.heat - a.heat).slice(0, 20)
  }
  return filteredBaseItems.value
})
const selectedDetail = ref<NewsDetail | null>(null)
const focusRequestId = ref(0)
const flyToLocation = ref<string | null>(null)

const typeOptions = computed(() => {
  return Object.keys(NEWS_TYPE_MAP).map((value) => ({
    label: getNewsTypeLabel(value, lang.value),
    value,
  }))
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
  flyToLocation.value = null
}

function onCloseDetail() {
  selectedId.value = null
  selectedDetail.value = null
  flyToLocation.value = null
}

function onLocateDetail() {
  if (!selectedId.value) return
  focusRequestId.value += 1
}

function onLocateCountry(country: string) {
  // 飞转到指定地点
  flyToLocation.value = country
  focusRequestId.value += 1
}

function onChangeLang(value: Lang) {
  lang.value = value
}

function onChangeMode(value: 'hot' | 'all') {
  mode.value = value
}

function onReset() {
  const now = new Date()
  // 计算24小时前
  const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  // 使用本地日期格式 (YYYY-MM-DD)
  const formatDate = (d: Date) => {
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  const defaultTimeRange = {
    start: formatDate(oneDayAgo),
    end: formatDate(now),
  }
  filter.value = {
    query: '',
    country: null,
    media: null,
    continent: null,
    type: null,
    heat: null,
    timeRange: defaultTimeRange,
  }
}

// 初始加载和筛选变化时重新加载
async function loadNews(reset = false) {
  if (isLoading.value) return
  isLoading.value = true
  try {
    if (reset) {
      allItems.value = []
    }
    const offset = allItems.value.length
    const result = await fetchNewsList(lang.value, 200, offset)
    
    if (reset) {
      allItems.value = result.items
    } else {
      allItems.value = [...allItems.value, ...result.items]
    }
    hasMore.value = result.hasMore
  } catch (error) {
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// 滚动加载更多
async function loadMore() {
  if (!hasMore.value || isLoading.value) return
  await loadNews(false)
}

onMounted(async () => {
  await loadNews(true)
})

// 监听筛选变化，重新加载数据
watch(filter, async () => {
  filterKey.value++
  await loadNews(true)
}, { deep: true })

// 监听语言变化
watch(lang, async (nextLang) => {
  localStorage.setItem('lang', nextLang)
  await loadNews(true)
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

// 暴露加载更多方法给父组件
defineExpose({ loadMore })
</script>

<template>
  <main class="relative h-screen w-screen overflow-hidden bg-black">
    <MapPanel
      :items="filteredItems"
      :selected-id="selectedId"
      :lang="lang"
      :focus-request-id="focusRequestId"
      :fly-to-location="flyToLocation"
      :has-more="hasMore"
      :is-loading="isLoading"
      @select="onSelectNews"
      @load-more="loadMore"
    />
    <NewsDetailCard
      :visible="Boolean(selectedId)"
      :lang="lang"
      :detail="selectedDetail"
      @close="onCloseDetail"
      @locate="onLocateDetail"
      @locate-country="onLocateCountry"
    />
    <div class="absolute inset-x-0 top-0 z-[1000]">
      <TopNav
        :lang="lang"
        :mode="mode"
        :query="filter.query"
        :type="filter.type"
        :continent="filter.continent"
        :country="filter.country"
        :time-range="filter.timeRange"
        :type-options="typeOptions"
        :continent-options="continentOptions"
        :country-options="countryOptions"
        @update:lang="onChangeLang"
        @update:mode="onChangeMode"
        @update:query="(value) => (filter.query = value)"
        @update:type="(value) => (filter.type = value)"
        @update:continent="(value) => (filter.continent = value)"
        @update:country="(value) => (filter.country = value)"
        @update:time-range="(value) => (filter.timeRange = value)"
        @reset="onReset"
      />
    </div>
  </main>
</template>
