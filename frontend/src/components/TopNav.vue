<script setup lang="ts">
import { List } from 'lucide-vue-next'
import gTranslateIcon from '@/assets/g_translate.svg'
import ResetButton from '@/components/ResetButton.vue'
import SelectPill from '@/components/SelectPill.vue'
import SearchPill from '@/components/SearchPill.vue'

const props = defineProps<{
  lang: 'zh' | 'en'
  mode: 'hot' | 'all'
  query: string
  type: string | null
  continent: string | null
  country: string | null
  typeOptions: { label: string; value: string }[]
  continentOptions: { label: string; value: string }[]
  countryOptions: { label: string; value: string }[]
}>()

const emit = defineEmits<{
  'update:lang': [value: 'zh' | 'en']
  'update:mode': [value: 'hot' | 'all']
  'update:query': [value: string]
  'update:type': [value: string | null]
  'update:continent': [value: string | null]
  'update:country': [value: string | null]
  reset: []
}>()

function onMenu() {}

function toggleLang() {
  emit('update:lang', props.lang === 'zh' ? 'en' : 'zh')
}
</script>

<template>
  <header class="h-[61px] bg-[#d9d9d9]">
    <div class="mx-auto flex h-full max-w-[1440px] items-center gap-2 px-2">
      <button
        class="inline-flex h-[27px] w-[27px] items-center justify-center text-black hover:opacity-80"
        type="button"
        aria-label="菜单"
        @click="onMenu"
      >
        <List class="h-[27px] w-[27px]" />
      </button>

      <div class="ml-1 inline-flex h-[30px] overflow-hidden">
        <button
          class="inline-flex items-center justify-center border-b px-3 text-[16px] leading-[22px]"
          :class="
            props.mode === 'hot'
              ? 'rounded-t-[4px] border-zinc-700 text-zinc-900'
              : 'rounded-t-[4px] border-zinc-300 text-zinc-500'
          "
          type="button"
          @click="emit('update:mode', 'hot')"
        >
          {{ props.lang === 'en' ? 'Hot' : '热点' }}
        </button>
        <button
          class="inline-flex items-center justify-center border-b px-3 text-[16px] leading-[22px]"
          :class="
            props.mode === 'all'
              ? 'rounded-t-[4px] border-zinc-700 text-zinc-900'
              : 'rounded-t-[4px] border-zinc-300 text-zinc-500'
          "
          type="button"
          @click="emit('update:mode', 'all')"
        >
          {{ props.lang === 'en' ? 'All' : '全部' }}
        </button>
      </div>

      <div class="ml-auto flex items-center gap-2">
        <ResetButton :lang="props.lang" @click="emit('reset')" />
        <SelectPill
          :model-value="props.type"
          :placeholder="props.lang === 'en' ? 'Category' : '新闻类型'"
          :options="props.typeOptions"
          @update:model-value="(value) => emit('update:type', value)"
        />
        <SelectPill
          :model-value="props.continent"
          :placeholder="props.lang === 'en' ? 'Continent' : '大洲'"
          :options="props.continentOptions"
          @update:model-value="(value) => emit('update:continent', value)"
        />
        <SelectPill
          :model-value="props.country"
          :placeholder="props.lang === 'en' ? 'Country/Region' : '国家/地区'"
          :options="props.countryOptions"
          @update:model-value="(value) => emit('update:country', value)"
        />
        <div class="w-[360px]">
          <SearchPill
            :model-value="props.query"
            :placeholder="props.lang === 'en' ? 'Search' : '搜索'"
            @update:model-value="(value) => emit('update:query', value)"
          />
        </div>
      </div>

      <button
        class="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white/90 ring-1 ring-black/10 hover:bg-white"
        type="button"
        :aria-label="props.lang === 'en' ? 'Switch Language' : '切换语言'"
        @click="toggleLang"
      >
        <img :src="gTranslateIcon" alt="g_translate" class="h-6 w-6" />
      </button>
    </div>
  </header>
</template>
