<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import { fetchNewsById, type Lang, type NewsItem } from '@/lib/news'

const route = useRoute()
const router = useRouter()
const lang = ref<Lang>((localStorage.getItem('lang') as Lang) === 'en' ? 'en' : 'zh')

const id = computed(() => String(route.params.id || ''))
const item = ref<NewsItem | null>(null)

const mapRef = ref<HTMLDivElement | null>(null)
const map = ref<L.Map | null>(null)

function googleTileUrl() {
  const hl = lang.value === 'en' ? 'en' : 'zh-CN'
  return `https://mt1.google.com/vt/lyrs=m&hl=${hl}&gl=CN&x={x}&y={y}&z={z}`
}

function onBack() {
  router.push('/')
}

const t = {
  back: lang.value === 'en' ? 'Back' : '返回',
  detail: lang.value === 'en' ? 'News Detail' : '新闻详情',
  notFound: lang.value === 'en' ? 'News not found. Please go back to the home page.' : '未找到该新闻。你可以返回主页继续浏览。',
  meta: lang.value === 'en' ? 'Metadata' : '元信息',
  source: lang.value === 'en' ? 'Source' : '来源',
  time: lang.value === 'en' ? 'Time' : '时间',
  location: lang.value === 'en' ? 'Location' : '地点',
  map: lang.value === 'en' ? 'Map' : '地图',
}

function renderMap() {
  if (!mapRef.value) return
  map.value?.remove()

  const center: [number, number] = item.value ? [item.value.lat, item.value.lng] : [20, 0]
  const zoom = item.value ? 4 : 2
  const m = L.map(mapRef.value, { center, zoom, zoomControl: true })
  L.tileLayer(googleTileUrl(), { maxZoom: 18, minZoom: 2, attribution: '' }).addTo(m)
  if (item.value) {
    L.circleMarker([item.value.lat, item.value.lng], {
      radius: 7,
      weight: 3,
      color: '#ffffff',
      fillColor: '#ef4444',
      fillOpacity: 0.95,
    })
      .addTo(m)
      .bindPopup(item.value.title, { autoPan: true })
      .openPopup()
  }
  map.value = m
}

async function loadItem() {
  try {
    item.value = await fetchNewsById(id.value, lang.value)
  } catch (error) {
    console.error(error)
    item.value = null
  }
  renderMap()
}

onMounted(async () => {
  await loadItem()
})

onUnmounted(() => {
  map.value?.remove()
  map.value = null
})

watch(id, async () => {
  await loadItem()
})
</script>

<template>
  <div class="min-h-screen bg-black text-white">
    <div class="mx-auto max-w-6xl px-6 py-6">
      <button
        class="inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-3 py-2 text-sm font-medium text-white ring-1 ring-zinc-800 hover:bg-zinc-800"
        type="button"
        @click="onBack"
      >
        {{ t.back }}
      </button>

      <div class="mt-6 grid grid-cols-12 gap-6">
        <div class="col-span-12 rounded-2xl bg-zinc-950/70 p-6 ring-1 ring-zinc-800 lg:col-span-8">
          <h1 class="text-lg font-semibold tracking-tight">{{ item?.title ?? t.detail }}</h1>
          <p class="mt-2 text-sm text-zinc-300">ID：{{ id }}</p>
          <div class="mt-6 space-y-3 text-sm text-zinc-200">
            <p>
              {{ item?.summary ?? t.notFound }}
            </p>
          </div>
        </div>

        <div class="col-span-12 space-y-6 lg:col-span-4">
          <div class="rounded-2xl bg-zinc-950/70 p-6 ring-1 ring-zinc-800">
            <div class="text-sm font-semibold">{{ t.meta }}</div>
            <div class="mt-4 space-y-2 text-sm text-zinc-300">
              <div class="flex items-center justify-between">
                <span>{{ t.source }}</span>
                <span class="text-zinc-200">{{ item?.media ?? '-' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span>{{ t.time }}</span>
                <span class="text-zinc-200">{{ item?.date ?? '-' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span>{{ t.location }}</span>
                <span class="text-zinc-200">{{ item?.country ?? '-' }}</span>
              </div>
            </div>
          </div>

          <div class="rounded-2xl bg-zinc-950/70 p-6 ring-1 ring-zinc-800">
            <div class="text-sm font-semibold">{{ t.map }}</div>
            <div ref="mapRef" class="mt-4 h-64 rounded-xl ring-1 ring-zinc-800" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
