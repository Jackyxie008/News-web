<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import TopNav from '@/components/TopNav.vue'
import NewsDetailCardWithMap from '@/components/NewsDetailCardWithMap.vue'
import { fetchNewsById, fetchNewsList, filterNews, getNewsTypeLabel, NEWS_TYPE_MAP, type Lang, type NewsDetail, type NewsItem } from '@/lib/news'
import { CONTINENTS_EN, CONTINENTS_ZH, getAllCountryOptions } from '@/lib/geo'

const lang = ref<Lang>((localStorage.getItem('lang') as Lang) === 'en' ? 'en' : 'zh')
const mode = ref<'hot' | 'all'>('hot')

const allItems = ref<NewsItem[]>([])
const query = ref('')
const typeFilter = ref<string | null>(null)
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
  return filterNews(allItems.value, filter.value).slice().sort((a, b) => b.ts - a.ts)
})

// 默认选择最近24小时
onMounted(async () => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  timeRange.value = {
    start: new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    end: today.toISOString().slice(0, 10),
  }
  try {
    allItems.value = await fetchNewsList(lang.value)
  } catch (error) {
    console.error(error)
  }
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
  fetchNewsList(lang.value).then((items) => {
    allItems.value = items
  })
  // 重新获取选中的新闻详情
  if (selectedId.value) {
    fetchNewsById(selectedId.value, lang.value).then((detail) => {
      selectedDetail.value = detail
    })
  }
}

function onReset() {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  timeRange.value = {
    start: new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    end: today.toISOString().slice(0, 10),
  }
  query.value = ''
  typeFilter.value = null
}

const t = computed(() => ({
  title: lang.value === 'en' ? 'News Reader' : '新闻阅读器',
  noResults: lang.value === 'en' ? 'No news found' : '暂无新闻',
}))
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
      @update:mode="(v) => {}"
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

        <div v-if="filteredItems.length === 0" class="py-12 text-center text-zinc-500">
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