import { Segmented } from 'antd'
import { useTranslation } from 'react-i18next'

/** Top-bar language toggle (中 / EN). Switch takes effect immediately and
 * persists via the i18n languageChanged hook in src/i18n/index.ts. */
const LanguageSwitcher: React.FC = () => {
  const { t, i18n } = useTranslation('nav')
  return (
    <Segmented
      size="small"
      value={i18n.language === 'en' ? 'en' : 'zh'}
      onChange={v => i18n.changeLanguage(v as string)}
      options={[
        { value: 'zh', label: t('langSwitch.zh') },
        { value: 'en', label: t('langSwitch.en') },
      ]}
    />
  )
}

export default LanguageSwitcher
