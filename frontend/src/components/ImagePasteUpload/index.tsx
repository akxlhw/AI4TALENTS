import React, { useEffect, useRef, useState } from 'react'
import { Upload, message, Typography } from 'antd'
import { PlusOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'

const { Text } = Typography

interface ImagePasteUploadProps {
  fileList: UploadFile[]
  onChange: (fileList: UploadFile[]) => void
  maxCount?: number
  maxSizeMB?: number
}

const ACCEPT_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']

const ImagePasteUpload: React.FC<ImagePasteUploadProps> = ({
  fileList,
  onChange,
  maxCount = 5,
  maxSizeMB = 5,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewImage, setPreviewImage] = useState('')

  const handleBeforeUpload = (file: File) => {
    if (!ACCEPT_TYPES.includes(file.type)) {
      message.error('仅支持 PNG、JPEG、GIF、WEBP 格式图片')
      return Upload.LIST_IGNORE
    }
    if (file.size > maxSizeMB * 1024 * 1024) {
      message.error(`单张图片大小不能超过 ${maxSizeMB}MB`)
      return Upload.LIST_IGNORE
    }
    if (fileList.length >= maxCount) {
      message.error(`最多上传 ${maxCount} 张图片`)
      return Upload.LIST_IGNORE
    }
    return false
  }

  const handleChange = (info: { fileList: UploadFile[] }) => {
    onChange(info.fileList.slice(0, maxCount))
  }

  const fileListRef = useRef(fileList)
  fileListRef.current = fileList

  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (!containerRef.current?.contains(document.activeElement)) return
      const items = e.clipboardData?.items
      if (!items) return

      const imageItems: File[] = []
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile()
          if (file) imageItems.push(file)
        }
      }

      if (imageItems.length === 0) return

      e.preventDefault()

      const current = fileListRef.current
      const remaining = maxCount - current.length
      if (remaining <= 0) {
        message.error(`最多上传 ${maxCount} 张图片`)
        return
      }

      const toAdd = imageItems.slice(0, remaining)
      const newFiles: UploadFile[] = toAdd.map((file, idx) => ({
        uid: `paste-${Date.now()}-${idx}`,
        name: file.name || `pasted-image-${idx + 1}.png`,
        status: 'done',
        originFileObj: file as any,
        url: URL.createObjectURL(file),
      }))

      onChange([...current, ...newFiles])
    }

    document.addEventListener('paste', handlePaste)
    return () => document.removeEventListener('paste', handlePaste)
  }, [maxCount, onChange])

  const removeFile = (uid: string) => {
    onChange(fileList.filter((f) => f.uid !== uid))
  }

  const openPreview = (url?: string) => {
    if (url) {
      setPreviewImage(url)
      setPreviewOpen(true)
    }
  }

  return (
    <div ref={containerRef}>
      <Upload
        listType="picture-card"
        fileList={fileList}
        beforeUpload={handleBeforeUpload}
        onChange={handleChange}
        showUploadList={false}
        accept="image/png,image/jpeg,image/gif,image/webp"
        disabled={fileList.length >= maxCount}
        style={{ display: 'inline-block' }}
      >
        {fileList.length < maxCount && (
          <div style={{ width: 100, height: 100, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
            <PlusOutlined />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>点击或粘贴</Text>
            </div>
          </div>
        )}
      </Upload>

      {fileList.map((file) => (
        <div
          key={file.uid}
          style={{
            display: 'inline-block',
            width: 100,
            height: 100,
            marginRight: 8,
            marginBottom: 8,
            position: 'relative',
            borderRadius: 8,
            overflow: 'hidden',
            border: '1px solid #d9d9d9',
          }}
        >
          <img
            src={file.url || (file.originFileObj ? URL.createObjectURL(file.originFileObj as Blob) : '')}
            alt={file.name}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.4)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 12,
              opacity: 0,
              transition: 'opacity 0.2s',
            }}
            className="upload-overlay"
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1' }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = '0' }}
          >
            <EyeOutlined style={{ color: '#fff', fontSize: 16, cursor: 'pointer' }} onClick={() => openPreview(file.url || (file.originFileObj ? URL.createObjectURL(file.originFileObj as Blob) : ''))} />
            <DeleteOutlined style={{ color: '#fff', fontSize: 16, cursor: 'pointer' }} onClick={() => removeFile(file.uid)} />
          </div>
        </div>
      ))}

      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          支持粘贴截图（Ctrl+V），最多 {maxCount} 张，单张不超过 {maxSizeMB}MB
        </Text>
      </div>

      {previewImage && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.8)',
            zIndex: 2000,
            display: previewOpen ? 'flex' : 'none',
            justifyContent: 'center',
            alignItems: 'center',
          }}
          onClick={() => setPreviewOpen(false)}
        >
          <img
            src={previewImage}
            alt="preview"
            style={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}

export default ImagePasteUpload
