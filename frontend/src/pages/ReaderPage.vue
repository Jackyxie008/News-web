<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import TopNav from '@/components/TopNav.vue'
import NewsDetailCardWithMap from '@/components/NewsDetailCardWithMap.vue'
import { fetchNewsById, fetchNewsList, filterNews, getNewsTypeLabel, NEWS_TYPE_MAP, type Lang, type NewsDetail, type NewsItem } from '@/lib/news'
import { CONTINENTS_EN, CONTINENTS_ZH, getAllCountryOptions } from '@/lib/geo'

const lang = ref<Lang>((localStorage.getItem('lang') as Lang) === 'en' ? 'en' : 'zh')
const mode = ref<'hot' | 'all'>('hot')
const modeKey = ref(0) // 用于追踪模式变化，重新加载数据

const allItems = ref<NewsItem[]>([])
const hasMore = ref(false)
const isLoading = ref(false)
const query = ref('')
const typeFilter = ref<string | string[] | null>(null)
const timeRange = ref<{ start: string; end: string } | null>(null)

// 选中的新闻
const selectedId = ref<string | null>(null)
const selectedDetail = ref<NewsDetail | null>(null)

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

const countryOptions = computed(() => getAllCountryOptions(lang.value))

const filter = computed(() => ({
  query: query.value,
  country: null,
  media: null,
  continent: null,
  type: typeFilter.value,
  heat: null,
  timeRange: timeRange.value,
}))

const filteredItems = computed(() => {
  const items = filterNews(allItems.value, filter.value)
  // 根据模式排序：热点模式按热度排序，全部模式按时间排序
  if (mode.value === 'hot') {
    return items.slice().sort((a, b) => b.heat - a.heat)
  }
  return items.slice().sort((a, b) => b.ts - a.ts)
})

// 加载新闻数据
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

// 默认选择最近24小时
onMounted(async () => {
  const now = new Date()
  const formatDate = (d: Date) => {
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  timeRange.value = {
    start: formatDate(new Date(now.getTime() - 24 * 60 * 60 * 1000)),
    end: formatDate(now),
  }
  await loadNews(true)
})

// 监听选中的新闻 ID，获取详情
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

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return dateStr
}

function onSelectItem(item: NewsItem) {
  selectedId.value = item.id
}

function onCloseDetail() {
  selectedId.value = null
  selectedDetail.value = null
}

function onChangeLang(value: Lang) {
  lang.value = value
  localStorage.setItem('lang', value)
  // 切换语言后重新获取新闻列表
  loadNews(true)
  // 重新获取选中的新闻详情
  if (selectedId.value) {
    fetchNewsById(selectedId.value, lang.value).then((detail) => {
      selectedDetail.value = detail
    })
  }
}

function onChangeMode(value: 'hot' | 'all') {
  mode.value = value
}

function onReset() {
  const now = new Date()
  const formatDate = (d: Date) => {
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  timeRange.value = {
    start: formatDate(new Date(now.getTime() - 24 * 60 * 60 * 1000)),
    end: formatDate(now),
  }
  query.value = ''
  typeFilter.value = null
}

// 监听筛选变化，重新加载数据
watch([query, typeFilter, timeRange], async () => {
  // 筛选变化时重新加载
}, { deep: true })

const t = computed(() => ({
  title: lang.value === 'en' ? 'News Reader' : '新闻阅读器',
  noResults: lang.value === 'en' ? 'No news found' : '暂无新闻',
  loading: lang.value === 'en' ? 'Loading...' : '加载中...',
  loadMore: lang.value === 'en' ? 'Load More' : '加载更多',
}))

// 暴露加载更多方法
defineExpose({ loadMore })
</script>

<template>
  <div class="flex h-screen flex-col bg-white">
    <TopNav
      :lang="lang"
      :mode="mode"
      :query="query"
      :type="typeFilter"
      :continent="null"
      :country="null"
      :time-range="timeRange"
      :type-options="typeOptions"
      :continent-options="continentOptions"
      :country-options="countryOptions"
      @update:lang="onChangeLang"
      @update:mode="onChangeMode"
      @update:query="(v) => (query = v)"
      @update:type="(v) => (typeFilter = v)"
      @update:continent="(v) => {}"
      @update:country="(v) => {}"
      @update:time-range="(v) => (timeRange = v)"
      @reset="onReset"
    />

    <!-- 主内容区域：左边列表 + 右边卡片 -->
    <div class="flex flex-1 overflow-hidden">
      <!-- 左边：新闻列表 -->
      <main class="flex-1 overflow-y-auto px-6 py-6">
        <h1 class="mb-6 text-2xl font-bold">{{ t.title }}</h1>

        <div v-if="isLoading && filteredItems.length === 0" class="py-12 text-center text-zinc-500">
          {{ t.loading }}
        </div>
        <div v-else-if="filteredItems.length === 0" class="py-12 text-center text-zinc-500">
          {{ t.noResults }}
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="item in filteredItems"
            :key="item.id"
            class="cursor-pointer rounded-xl border p-4 transition-colors"
            :class="selectedId === item.id ? 'border-zinc-400 bg-zinc-100' : 'border-zinc-200 bg-zinc-50 hover:bg-zinc-100'"
            @click="onSelectItem(item)"
          >
            <div class="flex gap-4">
              <img
                v-if="item.imageUrl"
                :src="item.imageUrl"
                :alt="item.title"
                class="h-20 w-28 flex-none rounded-lg object-cover ring-1 ring-zinc-200"
              />
              <div class="min-w-0 flex-1">
                <h3 class="mb-2 text-base font-medium leading-tight line-clamp-2">{{ item.title }}</h3>
                <div class="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                  <span>{{ formatDate(item.date) }}</span>
                  <span>·</span>
                  <span>{{ item.media }}</span>
                  <span>·</span>
                  <span>{{ getNewsTypeLabel(item.type, lang) }}</span>
                  <span>·</span>
                  <span>{{ item.country }}</span>
                </div>
                <p class="mt-2 text-sm text-zinc-600 line-clamp-2">{{ item.summary || '' }}</p>
              </div>
            </div>
          </div>
          
          <!-- 加载更多按钮 -->
          <div v-if="hasMore" class="py-4 text-center">
            <button
              class="rounded-lg bg-zinc-100 px-6 py-2 text-sm text-zinc-600 hover:bg-zinc-200"
              :disabled="isLoading"
              @click="loadMore"
            >
              {{ isLoading ? t.loading : t.loadMore }}
            </button>
          </div>
        </div>
      </main>

      <!-- 右边：新闻详情卡片 -->
      <aside class="w-[480px] border-l border-zinc-200 p-4">
        <NewsDetailCardWithMap
          :visible="Boolean(selectedId)"
          :lang="lang"
          :detail="selectedDetail"
          @close="onCloseDetail"
        />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
