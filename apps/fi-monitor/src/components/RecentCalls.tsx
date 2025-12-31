import { useRef } from 'react'
import DataTable from 'datatables.net-react'
import DT from 'datatables.net-dt'

import 'datatables.net-dt/css/dataTables.dataTables.min.css'

DataTable.use(DT)

interface Call {
  id: string
  timestamp: string
  model: string
  total_tokens: number
  latency_ms: number
  status: string
  prompt_preview: string
  response_preview: string
}

interface RecentCallsProps {
  calls: Call[]
}

export function RecentCalls({ calls }: RecentCallsProps) {
  const tableRef = useRef<HTMLTableElement>(null)

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString()
  }

  const getLatencyClass = (ms: number) => {
    if (ms < 500) return 'fast'
    if (ms < 2000) return 'medium'
    return 'slow'
  }

  const columns = [
    {
      title: 'Time',
      data: 'timestamp',
      render: (data: string) => `<span class="time">${formatTime(data)}</span>`
    },
    {
      title: 'Model',
      data: 'model',
      render: (data: string) => `<code class="model-badge">${data}</code>`
    },
    {
      title: 'Prompt',
      data: 'prompt_preview',
      render: (data: string) => `<span class="preview-text" title="${data?.replace(/"/g, '&quot;') || ''}">${data || ''}</span>`
    },
    {
      title: 'Response',
      data: 'response_preview',
      render: (data: string) => `<span class="preview-text" title="${data?.replace(/"/g, '&quot;') || ''}">${data || ''}</span>`
    },
    {
      title: 'Tokens',
      data: 'total_tokens',
      className: 'text-center'
    },
    {
      title: 'Latency',
      data: 'latency_ms',
      render: (data: number) => `<span class="latency ${getLatencyClass(data)}">${data}ms</span>`
    },
    {
      title: 'Status',
      data: 'status',
      render: (data: string) => `<span class="status-badge ${data === 'success' ? 'success' : 'error'}">${data}</span>`
    }
  ]

  const options = {
    pageLength: 10,
    lengthMenu: [5, 10, 25, 50],
    order: [[0, 'desc']],
    searching: true,
    info: true,
    autoWidth: false,
    responsive: true,
    dom: '<"top"lf>rt<"bottom"ip>',
    language: {
      search: 'Filter:',
      lengthMenu: 'Show _MENU_ calls',
      info: 'Showing _START_ to _END_ of _TOTAL_ calls',
      infoEmpty: 'No calls recorded',
      emptyTable: 'No calls recorded yet'
    }
  }

  return (
    <div className="card datatable-card">
      <DataTable
        ref={tableRef}
        data={calls}
        columns={columns}
        options={options}
        className="display compact stripe hover"
      />
    </div>
  )
}
