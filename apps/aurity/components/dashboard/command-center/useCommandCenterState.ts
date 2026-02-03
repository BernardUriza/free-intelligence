
import { useState, useCallback, useEffect } from "react"
import { useToast } from "@/hooks/useToast"
import { useDashboardShortcuts } from "@/hooks/useDashboardShortcuts"
import {
  MOCK_QUEUE_PATIENTS,
  ESTIMATED_MINUTES_PER_PATIENT,
  type QueuePatient,
} from "@/lib/dashboard/constants"

export const useCommandCenterState = () => {
  const [doctorMessage, setDoctorMessage] = useState<string | null>(null)
  const [slides, setSlides] = useState<any[]>([])
  const [isLoadingSlides, setIsLoadingSlides] = useState(false)
  const [carouselIndex, setCarouselIndex] = useState(0)
  const [totalCarouselItems, setTotalCarouselItems] = useState(0)
  const [carouselContent, setCarouselContent] = useState<any[]>([])
  const [isAutoPlaying, setIsAutoPlaying] = useState(true)
  const [showSidePanel, setShowSidePanel] = useState(false)
  const [sidePanelTab, setSidePanelTab] = useState<'queue' | 'content' | 'message'>('queue')
  const [showShortcuts, setShowShortcuts] = useState(false)
  const { toasts, removeToast, success, info } = useToast()
  const [queuePatients, setQueuePatients] = useState<QueuePatient[]>(
    MOCK_QUEUE_PATIENTS.filter(p => p.status !== 'called')
  )

  const waitingCount = queuePatients.filter(p => p.status === 'waiting').length
  const avgWaitTime = Math.round(waitingCount * ESTIMATED_MINUTES_PER_PATIENT)
  const inProgressCount = queuePatients.filter(p => p.status === 'in_progress').length

  const handleCallNext = useCallback((ticketNumber: string) => {
    try {
      const audio = new Audio('/sounds/ding.mp3')
      audio.volume = 0.5
      audio.play().catch(() => {})
    } catch {}
    setQueuePatients(prev => prev.map(p =>
      p.ticketNumber === ticketNumber ? { ...p, status: 'called' as const } : p
    ))
    success(`Llamando turno ${ticketNumber}`)
  }, [success])

  const handleMarkComplete = useCallback((ticketNumber: string) => {
    setQueuePatients(prev => prev.map(p =>
      p.ticketNumber === ticketNumber ? { ...p, status: 'in_progress' as const } : p
    ))
    info(`Turno ${ticketNumber} en consulta`)
  }, [info])

  const firstWaitingPatient = queuePatients.find(p => p.status === 'waiting')
  const calledPatient = queuePatients.find(p => p.status === 'called')

  useDashboardShortcuts({
    onCallNext: useCallback(() => {
      if (firstWaitingPatient && !calledPatient) {
        handleCallNext(firstWaitingPatient.ticketNumber)
      }
    }, [firstWaitingPatient, calledPatient, handleCallNext]),
    onOpenTV: useCallback(() => {
      window.open('/dashboard?mode=tv', '_blank')
    }, []),
    onPrevSlide: useCallback(() => {
      if (totalCarouselItems > 1) {
        setCarouselIndex(prev => (prev - 1 + totalCarouselItems) % totalCarouselItems)
      }
    }, [totalCarouselItems]),
    onNextSlide: useCallback(() => {
      if (totalCarouselItems > 1) {
        setCarouselIndex(prev => (prev + 1) % totalCarouselItems)
      }
    }, [totalCarouselItems]),
    onTogglePlay: useCallback(() => {
      setIsAutoPlaying(prev => !prev)
      info(isAutoPlaying ? 'Auto-play pausado' : 'Auto-play activado')
    }, [isAutoPlaying, info]),
  })

  useEffect(() => {
    async function fetchSlides() {
      setIsLoadingSlides(true)
      try {
        const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7001"
        const response = await fetch(`${backendURL}/api/aurity/clinic/clinic-media/list?active_only=true`)
        if (response.ok) {
          const data = await response.json()
          setSlides(data.media || [])
        }
      } catch (error) {
        console.error("Failed to fetch slides:", error)
      } finally {
        setIsLoadingSlides(false)
      }
    }
    fetchSlides()
  }, [])

  const handleIndexChange = useCallback((index: number) => setCarouselIndex(index), [])
  const handleContentLoad = useCallback((total: number, contentArray?: any[]) => {
    setTotalCarouselItems(total)
    if (contentArray) setCarouselContent(contentArray)
  }, [])

  return {
    doctorMessage, setDoctorMessage,
    slides,
    isLoadingSlides,
    carouselIndex, setCarouselIndex,
    totalCarouselItems,
    carouselContent,
    isAutoPlaying, setIsAutoPlaying,
    showSidePanel, setShowSidePanel,
    sidePanelTab, setSidePanelTab,
    showShortcuts, setShowShortcuts,
    toasts, removeToast, success, info,
    queuePatients,
    waitingCount,
    avgWaitTime,
    inProgressCount,
    handleCallNext,
    handleMarkComplete,
    firstWaitingPatient,
    calledPatient,
    handleIndexChange,
    handleContentLoad,
  }
}
