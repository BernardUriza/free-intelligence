"use client";

/**
 * NAS Installer Page
 * Card: FI-INFRA-STR-014
 *
 * Interactive installation guide for NAS deployment and PC simulation
 * Philosophy: Visible instruction = reliable action
 */

import { useState } from "react";
import { Server, Laptop, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RealNASTab } from "@/components/infra/RealNASTab";
import { PCSimulationTab } from "@/components/infra/PCSimulationTab";
import { VerificationTab } from "@/components/infra/VerificationTab";
import { AppTemplate } from "@/components/layout/AppTemplate";
import { SERVICES } from "@/lib/nas-config";

export default function NASInstallerPage() {
  const [activeTab, setActiveTab] = useState("real-nas");

  return (
    <AppTemplate
      headerConfig={{
        title: 'FI-Core Installer',
        subtitle: 'Self-Hosted · Guía de instalación',
        icon: 'database',
        iconColor: 'fi-text-success',
        showBackButton: true,
      }}
      backgroundGradient="none"
      padding="0"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Cloud vs Self-Hosted Comparison */}
        <Card className="mb-8 bg-gradient-to-br from-purple-900/30 to-blue-900/30 border-purple-700/50">
          <CardHeader>
            <CardTitle className="text-slate-50">FI-Cloud vs FI-Core: Elige tu Despliegue</CardTitle>
            <CardDescription className="fi-text">
              Free Intelligence está disponible como servicio en la nube (FI-Cloud) o auto-hospedado (FI-Core).
              Elige según tus necesidades de control y escalabilidad.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* FI-Cloud */}
              <div className="p-6 rounded-lg bg-slate-900/50 border border-slate-700">
                <div className="flex items-center gap-3 mb-4">
                  <div className="fi-icon-box-blue">
                    <svg className="w-5 h-5 fi-text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold fi-text-primary">FI-Cloud</h3>
                    <p className="fi-text-xs">Servicio gestionado · Listo en 30 segundos</p>
                  </div>
                </div>

                <ul className="space-y-2 mb-4">
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Cero configuración</strong> – Funciona inmediatamente</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Datos encriptados</strong> – AES-256 en reposo</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Actualizaciones automáticas</strong> – Nuevas features cada semana</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Cumple HIPAA</strong> – Infraestructura certificada</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Soporte incluido</strong> – Chat en vivo + email</span>
                  </li>
                </ul>

                <div className="pt-4 fi-border-top">
                  <p className="fi-text-xs mb-2">Ideal para:</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="px-2 py-1 text-xs bg-blue-500/10 text-blue-300 rounded">Médicos individuales</span>
                    <span className="px-2 py-1 text-xs bg-blue-500/10 text-blue-300 rounded">Clínicas pequeñas</span>
                    <span className="px-2 py-1 text-xs bg-blue-500/10 text-blue-300 rounded">Startups</span>
                  </div>
                </div>

                <Button
                  onClick={() => window.location.href = '/chat'}
                  variant="primary"
                  fullWidth
                  size="sm"
                  className="mt-4"
                >
                  Probar FI-Cloud ahora →
                </Button>
              </div>

              {/* FI-Core */}
              <div className="p-6 rounded-lg bg-slate-900/50 border border-emerald-700/50">
                <div className="flex items-center gap-3 mb-4">
                  <div className="fi-icon-box-emerald">
                    <Server className="w-5 h-5 fi-text-success" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold fi-text-success">FI-Core</h3>
                    <p className="fi-text-xs">Self-hosted · Control total</p>
                  </div>
                </div>

                <ul className="space-y-2 mb-4">
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">100% on-premise</strong> – Datos nunca salen de tu red</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Air-gapped compatible</strong> – Funciona sin internet</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">White-label</strong> – Personaliza marca y dominio</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Cumplimiento regulatorio</strong> – Datos bajo tu jurisdicción</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm fi-text">
                    <span className="fi-text-success mt-0.5">✓</span>
                    <span><strong className="text-slate-200">Sin límites</strong> – Usuarios/pacientes ilimitados</span>
                  </li>
                </ul>

                <div className="pt-4 fi-border-top">
                  <p className="fi-text-xs mb-2">Ideal para:</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="px-2 py-1 text-xs bg-emerald-500/10 text-emerald-300 rounded">Hospitales</span>
                    <span className="px-2 py-1 text-xs bg-emerald-500/10 text-emerald-300 rounded">Redes de clínicas</span>
                    <span className="px-2 py-1 text-xs bg-emerald-500/10 text-emerald-300 rounded">Gobiernos</span>
                  </div>
                </div>

                <Button
                  onClick={() => setActiveTab("real-nas")}
                  variant="success"
                  fullWidth
                  size="sm"
                  className="mt-4"
                >
                  Instalar FI-Core →
                </Button>
              </div>
            </div>

            {/* Quick Comparison Table */}
            <div className="mt-6 overflow-hidden rounded-lg border border-slate-700">
              <table className="w-full text-sm">
                <thead className="bg-slate-800">
                  <tr>
                    <th className="px-4 py-3 text-left fi-text font-medium">Feature</th>
                    <th className="px-4 py-3 text-center text-blue-300 font-medium">FI-Cloud</th>
                    <th className="px-4 py-3 text-center text-emerald-300 font-medium">FI-Core</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  <tr className="bg-slate-900/50">
                    <td className="px-4 py-3 fi-text">Tiempo de setup</td>
                    <td className="px-4 py-3 text-center text-slate-400">30 segundos</td>
                    <td className="px-4 py-3 text-center text-slate-400">1-2 horas</td>
                  </tr>
                  <tr className="bg-slate-900/30">
                    <td className="px-4 py-3 fi-text">Hardware requerido</td>
                    <td className="px-4 py-3 text-center text-slate-400">Ninguno</td>
                    <td className="px-4 py-3 text-center text-slate-400">NAS/Servidor</td>
                  </tr>
                  <tr className="bg-slate-900/50">
                    <td className="px-4 py-3 fi-text">Ubicación de datos</td>
                    <td className="px-4 py-3 text-center text-slate-400">Cloud seguro</td>
                    <td className="px-4 py-3 text-center text-slate-400">Tu infraestructura</td>
                  </tr>
                  <tr className="bg-slate-900/30">
                    <td className="px-4 py-3 fi-text">Mantenimiento</td>
                    <td className="px-4 py-3 text-center text-slate-400">Automático</td>
                    <td className="px-4 py-3 text-center text-slate-400">Manual</td>
                  </tr>
                  <tr className="bg-slate-900/50">
                    <td className="px-4 py-3 fi-text">Costo mensual (estimado)</td>
                    <td className="px-4 py-3 text-center text-slate-400">$49-199/mes</td>
                    <td className="px-4 py-3 text-center text-slate-400">Licencia única</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Technical Installation Guide (FI-Core only) */}
        <Card className="mb-8 bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-50">FI-Core Installation Guide</CardTitle>
            <CardDescription className="text-slate-400">
              Guía técnica de instalación para NAS (Synology, TrueNAS, QNAP) o simulación en PC.
              Requiere conocimientos de administración de sistemas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Services Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {SERVICES.map((service) => (
                <div
                  key={service.name}
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-700"
                >
                  <div>
                    <div className="text-sm font-medium fi-text">{service.name}</div>
                    <div className="fi-text-xs-muted">
                      {service.workers ? `${service.workers} workers` : "Single instance"}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono fi-text-success">:{service.port}</div>
                    <div className="fi-text-xs-muted">{service.memory}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tabs Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Panel: Table of Contents (Sticky) */}
          <div className="lg:col-span-3">
            <Card className="bg-slate-800/50 border-slate-700 sticky top-24">
              <CardHeader>
                <CardTitle className="text-sm text-slate-50">Installation Steps</CardTitle>
              </CardHeader>
              <CardContent>
                <nav className="space-y-2">
                  {[
                    { id: "real-nas", label: "Real NAS", icon: Server },
                    { id: "pc-simulation", label: "PC Simulation", icon: Laptop },
                    { id: "verification", label: "Verification", icon: CheckCircle2 },
                  ].map((item) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => setActiveTab(item.id)}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                          activeTab === item.id
                            ? "bg-emerald-500/20 fi-text-success font-medium"
                            : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </button>
                    );
                  })}
                </nav>
              </CardContent>
            </Card>
          </div>

          {/* Right Panel: Content */}
          <div className="lg:col-span-9">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3 bg-slate-800 border border-slate-700">
                <TabsTrigger value="real-nas" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:fi-text-success">
                  <Server className="h-4 w-4 mr-2" />
                  Real NAS
                </TabsTrigger>
                <TabsTrigger value="pc-simulation" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:fi-text-success">
                  <Laptop className="h-4 w-4 mr-2" />
                  PC Simulation
                </TabsTrigger>
                <TabsTrigger value="verification" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:fi-text-success">
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Verification
                </TabsTrigger>
              </TabsList>

              <TabsContent value="real-nas" className="mt-6">
                <RealNASTab />
              </TabsContent>

              <TabsContent value="pc-simulation" className="mt-6">
                <PCSimulationTab />
              </TabsContent>

              <TabsContent value="verification" className="mt-6">
                <VerificationTab />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </AppTemplate>
  );
}
