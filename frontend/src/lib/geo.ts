import type { Lang } from '@/lib/news'

export const CONTINENTS_ZH = ['亚洲', '欧洲', '非洲', '北美洲', '南美洲', '大洋洲', '南极洲']
export const CONTINENTS_EN = [
  'Asia',
  'Europe',
  'Africa',
  'North America',
  'South America',
  'Oceania',
  'Antarctica',
]

// ISO 3166-1 alpha-2
const REGION_CODES = [
  'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AO', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AW', 'AX', 'AZ',
  'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BL', 'BM', 'BN', 'BO', 'BQ', 'BR', 'BS',
  'BT', 'BV', 'BW', 'BY', 'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL', 'CM', 'CN',
  'CO', 'CR', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC', 'EE',
  'EG', 'EH', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 'FO', 'FR', 'GA', 'GB', 'GD', 'GE', 'GF',
  'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GP', 'GQ', 'GR', 'GS', 'GT', 'GU', 'GW', 'GY', 'HK', 'HM',
  'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IM', 'IN', 'IO', 'IQ', 'IR', 'IS', 'IT', 'JE', 'JM',
  'JO', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN', 'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC',
  'LI', 'LK', 'LR', 'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MF', 'MG', 'MH', 'MK',
  'ML', 'MM', 'MN', 'MO', 'MP', 'MQ', 'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA',
  'NC', 'NE', 'NF', 'NG', 'NI', 'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG',
  'PH', 'PK', 'PL', 'PM', 'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 'RE', 'RO', 'RS', 'RU', 'RW',
  'SA', 'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO', 'SR', 'SS',
  'ST', 'SV', 'SX', 'SY', 'SZ', 'TC', 'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO',
  'TR', 'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA', 'VC', 'VE', 'VG', 'VI',
  'VN', 'VU', 'WF', 'WS', 'YE', 'YT', 'ZA', 'ZM', 'ZW',
] as const

// 国家名称映射（中英文）
const COUNTRY_NAME_MAP: Record<string, string[]> = {
  '中国': ['CN', 'China'],
  '美国': ['US', 'United States', 'USA'],
  '英国': ['GB', 'United Kingdom', 'UK'],
  '日本': ['JP', 'Japan'],
  '德国': ['DE', 'Germany'],
  '法国': ['FR', 'France'],
  '俄罗斯': ['RU', 'Russia'],
  '韩国': ['KR', 'South Korea', 'Korea'],
  '加拿大': ['CA', 'Canada'],
  '澳大利亚': ['AU', 'Australia'],
  '巴西': ['BR', 'Brazil'],
  '印度': ['IN', 'India'],
  '意大利': ['IT', 'Italy'],
  '西班牙': ['ES', 'Spain'],
  '墨西哥': ['MX', 'Mexico'],
  '印度尼西亚': ['ID', 'Indonesia'],
  '荷兰': ['NL', 'Netherlands'],
  '沙特阿拉伯': ['SA', 'Saudi Arabia', '沙特'],
  '土耳其': ['TR', 'Turkey'],
  '瑞士': ['CH', 'Switzerland'],
  '新加坡': ['SG', 'Singapore'],
  '香港': ['HK', 'Hong Kong'],
  '台湾': ['TW', 'Taiwan'],
  '新西兰': ['NZ', 'New Zealand'],
  '埃及': ['EG', 'Egypt'],
  '阿根廷': ['AR', 'Argentina'],
  '越南': ['VN', 'Vietnam'],
  '泰国': ['TH', 'Thailand'],
  '南非': ['ZA', 'South Africa'],
  '菲律宾': ['PH', 'Philippines'],
  '巴基斯坦': ['PK', 'Pakistan'],
  '马来西亚': ['MY', 'Malaysia'],
  '哥伦比亚': ['CO', 'Colombia'],
  '智利': ['CL', 'Chile'],
  '秘鲁': ['PE', 'Peru'],
  '尼日利亚': ['NG', 'Nigeria'],
  '肯尼亚': ['KE', 'Kenya'],
  '阿联酋': ['AE', 'United Arab Emirates', '迪拜'],
  '瑞典': ['SE', 'Sweden'],
  '挪威': ['NO', 'Norway'],
  '波兰': ['PL', 'Poland'],
  '比利时': ['BE', 'Belgium'],
  '奥地利': ['AT', 'Austria'],
  '希腊': ['GR', 'Greece'],
  '捷克': ['CZ', 'Czech Republic'],
  '以色列': ['IL', 'Israel'],
  '伊朗': ['IR', 'Iran'],
  '伊拉克': ['IQ', 'Iraq'],
  '乌克兰': ['UA', 'Ukraine'],
  '哈萨克斯坦': ['KZ', 'Kazakhstan'],
  '欧盟': ['EU', 'European Union'],
}

export function getAllCountryOptions(lang: Lang) {
  const locale = lang === 'en' ? 'en' : 'zh-Hans'
  const dn = new Intl.DisplayNames([locale], { type: 'region' })
  const mapped = REGION_CODES.map((code) => {
    const name = dn.of(code)
    return name ? { code, name } : null
  })
    .filter((item) => item !== null)
    .sort((a, b) => a.name.localeCompare(b.name, locale))
  return mapped.map((item) => ({ label: item.name, value: item.code }))
}

// 根据国家名称查找 ISO 代码
export function findCountryCode(countryName: string): string | null {
  // 先检查预定义映射
  const upperName = countryName.toUpperCase()
  for (const [cn, codes] of Object.entries(COUNTRY_NAME_MAP)) {
    if (cn === countryName || codes.includes(upperName) || codes.includes(countryName)) {
      return codes[0]
    }
  }
  
  // 尝试使用 Intl.DisplayNames 反向查找
  const locale = 'en'
  const dn = new Intl.DisplayNames([locale], { type: 'region' })
  const searchLower = countryName.toLowerCase()
  
  for (const code of REGION_CODES) {
    const name = dn.of(code)
    if (name && name.toLowerCase() === searchLower) {
      return code
    }
  }
  
  return null
}