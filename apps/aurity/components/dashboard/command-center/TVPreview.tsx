
import React from 'react';
import { Activity, Pause, Bell } from "lucide-react"
import { FIAvatar } from "@/components/dashboard/FIAvatar"
import { Button } from '@/components/ui/button';

export const TVPreview = ({
  isLoadingSlides,
  doctorMessage,
  slides,
  carouselIndex,
  handleIndexChange,
  handleContentLoad,
  totalCarouselItems,
  carouselContent,
  isAutoPlaying,
  calledPatient,
  handleMarkComplete,
}: any) => (
  <div className="flex-1 relative rounded-2xl overflow-hidden border border-slate-700/50 bg-slate-900/50">
    <div className="absolute inset-0">
      {isLoadingSlides ? (
        <div className="flex items-center justify-center h-full">
          <Activity className="w-8 h-8 fi-text-purple animate-spin" />
        </div>
      ) : (
        <FIAvatar
          mode="broadcast"
          clinicName="Clínica AURITY"
          doctorMessage={doctorMessage}
          clinicSlides={slides}
          externalCurrentIndex={carouselIndex}
          onIndexChange={handleIndexChange}
          onContentLoad={handleContentLoad}
        />
      )}
    </div>
    <div className="absolute top-4 left-4 flex items-center gap-2">
      <div className="px-3 py-1.5 bg-slate-900/80 backdrop-blur-sm border border-slate-700 rounded-lg">
        <span className="fi-text-xs">Slide </span>
        <span className="text-sm font-bold text-white">{carouselIndex + 1}</span>
        <span className="fi-text-xs">/{totalCarouselItems}</span>
        {carouselContent[carouselIndex]?.type && (
          <span className="ml-2 text-xs fi-text-purple">
            ({carouselContent[carouselIndex].widgetType || carouselContent[carouselIndex].type})
          </span>
        )}
      </div>
      {!isAutoPlaying && (
        <div className="px-2 py-1 bg-amber-500/20 border border-amber-500/30 rounded-lg flex items-center gap-1">
          <Pause className="w-3 h-3 fi-text-warning" />
          <span className="text-xs fi-text-warning">Pausado</span>
        </div>
      )}
    </div>
    {calledPatient && (
      <div className="absolute top-4 right-4 px-4 py-2 bg-emerald-500/20 backdrop-blur-sm border border-emerald-500/50 rounded-xl animate-pulse">
        <div className="fi-flex-gap-md">
          <Bell className="w-5 h-5 fi-text-success" />
          <div>
            <p className="text-xs fi-text-success/80">Turno llamado</p>
            <p className="text-xl font-bold text-emerald-300 font-mono">{calledPatient.ticketNumber}</p>
          </div>
          <Button
            onClick={() => handleMarkComplete(calledPatient.ticketNumber)}
            className="fi-btn-success-sm"
            variant="success"
            size="sm"
            type="button"
          >
            Iniciar
          </Button>
        </div>
      </div>
    )}
  </div>
);
