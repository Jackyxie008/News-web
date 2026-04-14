<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import { mockNews } from '@/lib/news'

const route = useRoute()
const router = useRouter()

const id = computed(() => String(route.params.id || ''))

const item = computed(() => mockNews.find((n) => n.id === id.value) ?? null)

const mapRef = ref<HTMLDivElement | null>(null)
const map = ref<L.Map | null>(null)

function googleTileUrl() {
  return 'https://mt1.google.com/vt/lyrs=m&hl=zh-CN&gl=CN&x={x}&y={y}&z={z}'
}

function onBack() {
  router.push('/')
}

onMounted(() => {
  if (!mapRef.value) return
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
})

onUnmounted(() => {
  map.value?.remove()
  map.value = null
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
        返回
      </button>

      <div class="mt-6 grid grid-cols-12 gap-6">
        <div class="col-span-12 rounded-2xl bg-zinc-950/70 p-6 ring-1 ring-zinc-800 lg:col-span-8">
          <h1 class="text-lg font-semibold tracking-tight">{{ item?.title ?? '新闻详情' }}</h1>
          <p class="mt-2 text-sm text-zinc-300">ID：{{ id }}</p>
          <div class="mt-6 space-y-3 text-sm text-zinc-200">
            <p>
              {{ item?.summary ?? '未找到该新闻。你可以返回主页继续浏览。' }}
            </p>
          </div>
        </div>

        <div class="col-span-12 space-y-6 lg:col-span-4">
          <div class="rounded-2xl bg-zinc-950/70 p-6 ring-1 ring-zinc-800">
            <div class="text-sm font-semibold">元信息</div>
            <div class="mt-4 space-y-2 text-sm text-zinc-300">
              <div class="flex items-center justify-between">
                <span>来源</span>
                <span class="text-zinc-200">{{ item?.media ?? '-' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span>时间</span>
                <span class="text-zinc-200">{{ item?.date ?? '-' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span>地点</span>
                <span class="text-zinc-200">{{ item?.country ?? '-' }}</span>
              </div>
            </div>
          </div>

          <div class="rounded-2xl bg-zinc-950/70 p-6 ring-1 ring-zinc-800">
            <div class="text-sm font-semibold">地图</div>
            <div ref="mapRef" class="mt-4 h-64 rounded-xl ring-1 ring-zinc-800" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
