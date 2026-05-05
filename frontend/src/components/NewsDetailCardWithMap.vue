<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import type { NewsDetail } from '@/lib/news'
import L from 'leaflet'
import closeIcon from '@/assets/icon_x.svg'
import locationOnIcon from '@/assets/location_on.svg'

const props = defineProps<{
  visible: boolean
  lang: 'zh' | 'en'
  detail: NewsDetail | null
}>()

const emit = defineEmits<{
  close: []
  'locate-country': [country: string]
}>()

const mapRef = ref<HTMLDivElement | null>(null)
const map = ref<L.Map | null>(null)

// 获取所有地点（用分号分隔，每个分号分隔的内容就是一个地点）
const locations = computed(() => {
  // 只使用 location 字段
  if (!props.detail?.location) return []
  return props.detail.location.split(/[;；]/).map((s) => s.trim()).filter(Boolean)
})

function googleTileUrl() {
  const hl = props.lang === 'en' ? 'en' : 'zh-CN'
  return `https://mt1.google.com/vt/lyrs=m&hl=${hl}&gl=CN&x={x}&y={y}&z={z}`
}

function initMap() {
  if (!mapRef.value || !props.detail) return
  
  // 移除旧地图
  map.value?.remove()
  
  const lat = props.detail.lat ?? 20
  const lng = props.detail.lng ?? 0
  const zoom = props.detail.lat ? 6 : 2
  
  const m = L.map(mapRef.value, { center: [lat, lng], zoom, zoomControl: true })
  L.tileLayer(googleTileUrl(), { maxZoom: 18, minZoom: 2, attribution: '' }).addTo(m)
  
  // 添加标记
  L.circleMarker([lat, lng], {
    radius: 8,
    weight: 3,
    color: '#ffffff',
    fillColor: '#ef4444',
    fillOpacity: 0.95,
  }).addTo(m)
  
  map.value = m
}

watch(
  () => props.detail,
  () => {
    if (props.visible && mapRef.value) {
      setTimeout(initMap, 100)
    }
  },
)

onMounted(() => {
  if (props.visible && props.detail) {
    setTimeout(initMap, 100)
  }
})

onUnmounted(() => {
  map.value?.remove()
  map.value = null
})
</script>

<template>
  <aside
    v-if="props.visible"
    class="relative flex h-full flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white"
  >
    <div class="flex items-center justify-between border-b border-zinc-100 px-4 py-3">
      <h2 class="break-words text-lg font-semibold text-black">
        {{ props.detail?.title || (props.lang === 'en' ? 'News Title' : '新闻标题') }}
      </h2>
      <button
        class="inline-flex h-8 w-8 items-center justify-center rounded-md bg-transparent hover:bg-zinc-100"
        type="button"
        aria-label="关闭"
        @click="emit('close')"
      >
        <img :src="closeIcon" alt="X" class="h-5 w-5" />
      </button>
    </div>

    <div class="flex-1 space-y-3 overflow-y-auto p-4 text-black">
      <!-- 小地图 -->
      <section class="rounded-xl overflow-hidden border border-zinc-200">
        <div ref="mapRef" class="h-40 w-full"></div>
      </section>

      <section>
        <p class="mb-2 text-sm font-medium">{{ props.lang === 'en' ? 'Location' : '地点' }}</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="loc in locations"
            :key="loc"
            class="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-3 py-1 text-sm text-zinc-700 hover:bg-zinc-200"
            type="button"
            @click="emit('locate-country', loc)"
          >
            <img :src="locationOnIcon" alt="location" class="h-4 w-4" />
            {{ loc }}
          </button>
          <span
            v-if="locations.length === 0"
            class="text-sm text-zinc-700"
          >
            -
          </span>
        </div>
      </section>

      <section>
        <p class="mb-1 text-sm font-medium">
          {{ props.lang === 'en' ? 'Published At' : '发布时间' }}
        </p>
        <p class="text-sm text-zinc-700">
          {{ props.detail?.published || props.detail?.date || '-' }}
        </p>
      </section>

      <section>
        <p class="mb-2 text-sm font-medium">{{ props.lang === 'en' ? 'Keywords' : '关键字' }}</p>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="keyword in props.detail?.keywords || []"
            :key="keyword"
            class="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs text-zinc-700"
          >
            {{ keyword }}
          </span>
          <span
            v-if="!(props.detail?.keywords && props.detail.keywords.length > 0)"
            class="text-sm text-zinc-700"
          >
            -
          </span>
        </div>
      </section>

      <section>
        <p class="mb-1 text-sm font-medium">{{ props.lang === 'en' ? 'Category' : '新闻类型' }}</p>
        <p class="text-sm text-zinc-700">{{ props.detail?.newsType || props.detail?.type || '-' }}</p>
      </section>

      <section v-if="props.detail?.imageUrl?.trim()">
        <img
          :src="props.detail.imageUrl.trim()"
          :alt="props.detail?.title || 'news-image'"
          class="max-h-48 w-full rounded-lg object-cover ring-1 ring-zinc-200"
        />
      </section>

      <section>
        <p class="mb-1 text-sm font-medium">{{ props.lang === 'en' ? 'Content' : '正文' }}</p>
        <p class="whitespace-pre-wrap text-sm leading-6 text-zinc-700">
          {{ props.detail?.fullText?.trim() || props.detail?.summary || '-' }}
        </p>
      </section>

      <div class="text-center text-sm text-zinc-400">{{ props.lang === 'en' ? '✦ AI summary ✦' : '✦ AI总结 ✦' }}</div>

      <section>
        <p class="mb-1 text-sm font-medium">{{ props.lang === 'en' ? 'Links' : '链接' }}</p>
        <div class="space-y-2">
          <div
            v-for="(item, idx) in (props.detail?.linkItems && props.detail.linkItems.length > 0
              ? props.detail.linkItems
              : (props.detail?.links || []).map((url) => ({ url, source: props.detail?.media || '-' })))"
            :key="`${item.url}-${idx}`"
          >
            <p class="mb-0.5 text-xs text-zinc-600">
              {{ props.lang === 'en' ? `Source: ${item.source || '-'}` : `来源：${item.source || '-'}` }}
            </p>
            <a
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              class="block truncate text-sm text-blue-700 underline"
            >
              {{ item.url }}
            </a>
          </div>
          <p
            v-if="
              !(
                (props.detail?.linkItems && props.detail.linkItems.length > 0) ||
                (props.detail?.links && props.detail.links.length > 0)
              )
            "
            class="text-sm text-zinc-700"
          >
            -
          </p>
        </div>
      </section>
    </div>
  </aside>
</template>