/**
 * Search & Recommend Page - v1.4
 *
 * 功能说明：
 * - 人才搜索 Tab: 关键词/语义/混合搜索
 * - 智能推荐 Tab: 包含岗位匹配和相似推荐两种模式
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Typography,
  Space,
  Segmented,
  Tabs,
  message,
} from 'antd'
import {
  SearchOutlined,
  BulbOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { TechDomain } from '../../types'
import '../../i18n/namespaces/academic'
import SearchTab from './components/search-tab'
import JDMatchTab from './components/jd-match-tab'
import RecommendTab from './components/recommend-tab'

const { Title, Text } = Typography

// Helper types
interface School { school_id: number; school_name: string }
interface Country { country_code: string; country_name_cn: string }

const SearchRecommendPage: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation('academic')
  const [urlSearchParams] = useSearchParams()
  const initialTab = urlSearchParams.get('tab') || 'search'
  const [activeTab, setActiveTab] = useState(initialTab)

  // 智能推荐子 Tab 状态
  const initialRecommendMode = urlSearchParams.get('mode') || 'jd-match'
  const [recommendMode, setRecommendMode] = useState(initialRecommendMode)

  // ========== Shared Reference Data ==========
  const [schools, setSchools] = useState<School[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [techDomains, setTechDomains] = useState<TechDomain[]>([])

  // ========== Shared Reference Talent State ==========
  const [referenceTalentIds, setReferenceTalentIds] = useState<number[]>([])
  const [referenceTalentNames, setReferenceTalentNames] = useState<Map<number, string>>(new Map())

  const loadReferenceData = useCallback(async () => {
    try {
      const [schoolsRes, countriesRes, techDomainsRes] = await Promise.all([
        api.schools.list({}),
        api.countries.list(),
        api.techDomains.list(),
      ])
      setSchools(schoolsRes.data.items || [])
      setCountries(countriesRes.data.items || [])
      setTechDomains(techDomainsRes.data.items || [])
    } catch {
      message.error(t('search.loadFiltersError'))
    }
  }, [t])

  useEffect(() => {
    loadReferenceData()
  }, [loadReferenceData])

  const handleAddReferenceTalent = (talentId: number, talentName: string) => {
    if (referenceTalentIds.includes(talentId)) {
      message.warning(t('search.referenceAlreadyAdded'))
      return
    }
    if (referenceTalentIds.length >= 10) {
      message.warning(t('search.referenceLimit'))
      return
    }
    setReferenceTalentIds([...referenceTalentIds, talentId])
    setReferenceTalentNames(new Map(referenceTalentNames).set(talentId, talentName))
  }

  const handleAddToReference = (talentId: number, talentName: string) => {
    handleAddReferenceTalent(talentId, talentName)
    message.success(t('search.referenceAdded', { name: talentName }), 2)
  }

  const handleResetRecommend = () => {
    setReferenceTalentIds([])
    setReferenceTalentNames(new Map())
  }

  const handleRemoveReferenceTalent = (talentId: number) => {
    setReferenceTalentIds(referenceTalentIds.filter(id => id !== talentId))
    const newNames = new Map(referenceTalentNames)
    newNames.delete(talentId)
    setReferenceTalentNames(newNames)
  }

  // ========== Tab Change Handler ==========
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'recommend') {
      navigate(`/search-recommend?tab=${key}&mode=${recommendMode}`)
    } else {
      navigate(`/search-recommend?tab=${key}`)
    }
  }

  const handleRecommendModeChange = (value: string) => {
    setRecommendMode(value)
    navigate(`/search-recommend?tab=recommend&mode=${value}`)
  }

  // ========== Options ==========
  const countryOptions = countries.map(c => ({ value: c.country_code, label: c.country_name_cn }))
  const schoolOptions = schools.map(s => ({ value: s.school_id, label: s.school_name }))
  const techDomainOptions = techDomains.map(d => ({ value: d.tech_domain_id, label: d.domain_name }))

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={3} style={{ marginBottom: 20, fontWeight: 700 }}>
        <SearchOutlined style={{ marginRight: 8, color: 'var(--domain-primary)' }} />
        {t('search.title')}
      </Title>

      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        type="card"
        items={[
          {
            key: 'search',
            label: <span><SearchOutlined /> {t('search.talentSearch')}</span>,
            children: (
              <SearchTab
                schools={schools}
                countries={countries}
                techDomains={techDomains}
                countryOptions={countryOptions}
                schoolOptions={schoolOptions}
                techDomainOptions={techDomainOptions}
                onAddToReference={handleAddToReference}
              />
            ),
          },
          {
            key: 'recommend',
            label: <span><BulbOutlined /> {t('search.smartRecommend')}</span>,
            children: (
              <>
                <div style={{ marginBottom: 16 }}>
                  <Space>
                    <Text type="secondary">{t('search.recommendMode')}</Text>
                    <Segmented
                      value={recommendMode}
                      onChange={(value) => handleRecommendModeChange(value as string)}
                      options={[
                        { value: 'jd-match', label: <span><RobotOutlined /> {t('search.jdMatch')}</span> },
                        { value: 'similar', label: <span><TeamOutlined /> {t('search.similar')}</span> },
                      ]}
                    />
                  </Space>
                </div>
                {recommendMode === 'jd-match' && (
                  <JDMatchTab
                    schools={schools}
                    countries={countries}
                    techDomains={techDomains}
                    countryOptions={countryOptions}
                    schoolOptions={schoolOptions}
                    techDomainOptions={techDomainOptions}
                    onAddToReference={handleAddToReference}
                  />
                )}
                {recommendMode === 'similar' && (
                  <RecommendTab
                    referenceTalentIds={referenceTalentIds}
                    referenceTalentNames={referenceTalentNames}
                    onAddReferenceTalent={handleAddReferenceTalent}
                    onRemoveReferenceTalent={handleRemoveReferenceTalent}
                    onResetReferences={handleResetRecommend}
                  />
                )}
              </>
            ),
          },
        ]}
      />
    </div>
  )
}

export default SearchRecommendPage
