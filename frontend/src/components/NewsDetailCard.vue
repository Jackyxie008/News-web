<script setup lang="ts">
import type { NewsDetail } from '@/lib/news'
import closeIcon from '@/assets/icon_x.svg'
import locationOnIcon from '@/assets/location_on.svg'

const props = defineProps<{
  visible: boolean
  lang: 'zh' | 'en'
  detail: NewsDetail | null
}>()

const emit = defineEmits<{
  close: []
  locate: []
}>()
</script>

<template>
  <aside
    v-if="props.visible"
    class="absolute bottom-6 right-6 top-[88px] z-[1200] w-[min(547px,calc(100vw-24px))] overflow-hidden rounded-[20px] border border-zinc-200 bg-white shadow-[0_20px_60px_rgba(0,0,0,0.28)]"
  >
    <div class="flex h-full flex-col p-6">
      <div class="mb-4 flex items-start justify-between gap-4">
        <h2 class="break-words text-[34px] font-semibold leading-[1.2] text-black">
          {{ props.detail?.title || (props.lang === 'en' ? 'News Title' : '新闻标题') }}
        </h2>
        <div class="flex flex-none flex-col items-center gap-1">
          <button
            class="inline-flex h-8 w-8 items-center justify-center rounded-md bg-transparent hover:bg-zinc-100"
            type="button"
            aria-label="关闭"
            @click="emit('close')"
          >
            <img :src="closeIcon" alt="X" class="h-5 w-5" />
          </button>
          <button
            class="inline-flex h-8 w-8 items-center justify-center rounded-md bg-transparent hover:bg-zinc-100"
            type="button"
            aria-label="定位到地图"
            @click="emit('locate')"
          >
            <img :src="locationOnIcon" alt="location_on" class="h-6 w-6" />
          </button>
        </div>
      </div>

      <div class="flex-1 space-y-4 overflow-y-auto pr-1 text-black">
        <section>
          <p class="mb-1 text-base font-medium">{{ props.lang === 'en' ? 'Location' : '地点' }}</p>
          <p class="text-sm text-zinc-700">{{ props.detail?.location || props.detail?.country || '-' }}</p>
        </section>

        <section>
          <p class="mb-1 text-base font-medium">
            {{ props.lang === 'en' ? 'Published At' : '发布时间' }}
          </p>
          <p class="text-sm text-zinc-700">
            {{ props.detail?.published || props.detail?.date || '-' }}
          </p>
        </section>

        <section>
          <p class="mb-2 text-base font-medium">{{ props.lang === 'en' ? 'Keywords' : '关键字' }}</p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="keyword in props.detail?.keywords || []"
              :key="keyword"
              class="rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-700"
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
          <p class="mb-1 text-base font-medium">{{ props.lang === 'en' ? 'Category' : '新闻类型' }}</p>
          <p class="text-sm text-zinc-700">{{ props.detail?.newsType || props.detail?.type || '-' }}</p>
        </section>

        <section v-if="props.detail?.imageUrl">
          <img
            :src="props.detail.imageUrl"
            :alt="props.detail?.title || 'news-image'"
            class="max-h-[220px] w-full rounded-lg object-cover ring-1 ring-zinc-200"
          />
          <p class="mt-2 text-xs text-zinc-600">
            {{
              props.lang === 'en'
                ? `Image Source: ${props.detail?.imageSource || '-'}`
                : `图片来源：${props.detail?.imageSource || '-'}`
            }}
          </p>
        </section>

        <section>
          <p class="mb-1 text-base font-medium">{{ props.lang === 'en' ? 'Content' : '正文' }}</p>
          <p class="whitespace-pre-wrap text-sm leading-6 text-zinc-700">
            {{ props.detail?.fullText?.trim() || props.detail?.summary || '-' }}
          </p>
        </section>

        <section>
          <p class="mb-1 text-base font-medium">{{ props.lang === 'en' ? 'Links' : '链接' }}</p>
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
    </div>
  </aside>
</template>
