// QR Code Viewer for Tunnel URL (mobile testing)
import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'

interface QRCodeViewerProps {
  url: string
}

export function QRCodeViewer({ url }: QRCodeViewerProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="qr-code-viewer">
      {/* Collapsed view - small QR for quick reference */}
      <div className="qr-mini" onClick={() => setExpanded(true)} title="Click to enlarge QR code">
        <QRCodeSVG
          value={url}
          size={64}
          level="M"
          bgColor="transparent"
          fgColor="currentColor"
        />
        <span className="qr-label">📱 Scan QR</span>
      </div>

      {/* Expanded modal - large QR for easy scanning */}
      {expanded && (
        <div
          className="qr-modal-overlay"
          onClick={() => setExpanded(false)}
        >
          <div
            className="qr-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="qr-modal-header">
              <h3>Scan with Mobile Device</h3>
              <button
                className="qr-close"
                onClick={() => setExpanded(false)}
                title="Close (Esc)"
              >
                ✕
              </button>
            </div>

            <div className="qr-modal-body">
              <QRCodeSVG
                value={url}
                size={280}
                level="H"
                bgColor="#ffffff"
                fgColor="#000000"
                includeMargin
              />
              <div className="qr-url">{url.replace('https://', '')}</div>
              <div className="qr-instructions">
                <p>📱 Open camera app on your iPhone/Android</p>
                <p>📸 Point camera at QR code</p>
                <p>🔗 Tap notification to open tunnel URL</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
