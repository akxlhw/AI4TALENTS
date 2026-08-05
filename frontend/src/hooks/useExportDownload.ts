import { useState } from 'react'
import { message, type MenuProps } from 'antd'

export type ExportFormat = 'csv' | 'xlsx'

interface UseExportDownloadOptions {
  /** Returns the currently selected ids at request/confirm time. */
  getIds: () => number[]
  /** Warning shown when export is requested with an empty selection. */
  emptyWarning: string
  /** Calls the backend export API; resolves with the binary payload. */
  exportApi: (ids: number[], format: ExportFormat) => Promise<{ data: BlobPart }>
  /** Downloaded file name without extension. */
  fileName: string
  /** Success message; receives the exported count. */
  successMessage: (count: number) => string
  /** Maps an export error to a user-facing message. */
  formatError: (err: unknown) => string
}

/**
 * Shared selection-export flow used by the favorites page and the open-source
 * search page: format dropdown -> confirm modal -> blob download.
 */
export function useExportDownload({
  getIds,
  emptyWarning,
  exportApi,
  fileName,
  successMessage,
  formatError,
}: UseExportDownloadOptions) {
  const [exporting, setExporting] = useState(false)
  const [exportConfirmVisible, setExportConfirmVisible] = useState(false)
  const [pendingExportFormat, setPendingExportFormat] = useState<ExportFormat | null>(null)

  const requestExport = (format: ExportFormat) => {
    if (getIds().length === 0) {
      message.warning(emptyWarning)
      return
    }
    setPendingExportFormat(format)
    setExportConfirmVisible(true)
  }

  const exportMenu: MenuProps = {
    items: [
      { key: 'csv', label: '导出 CSV' },
      { key: 'xlsx', label: '导出 Excel' },
    ],
    onClick: e => requestExport(e.key as ExportFormat),
  }

  const confirmExport = async () => {
    if (!pendingExportFormat) return
    setExporting(true)
    try {
      const ids = getIds()
      const response = await exportApi(ids, pendingExportFormat)
      const blob = new Blob([response.data], {
        type:
          pendingExportFormat === 'xlsx'
            ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            : 'text/csv',
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${fileName}.${pendingExportFormat}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success(successMessage(ids.length))
    } catch (err) {
      message.error(formatError(err))
    } finally {
      setExporting(false)
      setExportConfirmVisible(false)
      setPendingExportFormat(null)
    }
  }

  const cancelExport = () => {
    setExportConfirmVisible(false)
    setPendingExportFormat(null)
  }

  return { exporting, exportMenu, exportConfirmVisible, confirmExport, cancelExport }
}
