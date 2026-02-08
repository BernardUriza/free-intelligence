"use client";

/**
 * NAS Installer Page
 * Card: FI-INFRA-STR-014
 *
 * Interactive installation guide for NAS deployment and PC simulation
 * Philosophy: Visible instruction = reliable action
 */

import { useState } from "react";
import { Server, Laptop, CheckCircle2, Check } from "lucide-react";
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
      <div className="nas-page-container">
        {/* Cloud vs Self-Hosted Comparison */}
        <Card className="nas-compare-card">
          <CardHeader>
            <CardTitle className="nas-compare-title">FI-Cloud vs FI-Core: Elige tu Despliegue</CardTitle>
            <CardDescription className="fi-text">
              Free Intelligence está disponible como servicio en la nube (FI-Cloud) o auto-hospedado (FI-Core).
              Elige según tus necesidades de control y escalabilidad.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="nas-compare-grid">
              {/* FI-Cloud */}
              <div className="nas-cloud-card">
                <div className="nas-card-header">
                  <div className="fi-icon-box-blue">
                    <svg className="nas-cloud-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="nas-cloud-title">FI-Cloud</h3>
                    <p className="fi-text-xs">Servicio gestionado · Listo en 30 segundos</p>
                  </div>
                </div>

                <ul className="nas-feature-list">
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Cero configuración</strong> – Funciona inmediatamente</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Datos encriptados</strong> – AES-256 en reposo</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Actualizaciones automáticas</strong> – Nuevas features cada semana</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Cumple HIPAA</strong> – Infraestructura certificada</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Soporte incluido</strong> – Chat en vivo + email</span>
                  </li>
                </ul>

                <div className="nas-ideal-section">
                  <p className="nas-ideal-label">Ideal para:</p>
                  <div className="nas-tag-list">
                    <span className="nas-tag-blue">Médicos individuales</span>
                    <span className="nas-tag-blue">Clínicas pequeñas</span>
                    <span className="nas-tag-blue">Startups</span>
                  </div>
                </div>

                <Button
                  onClick={() => window.location.href = '/chat'}
                  variant="primary"
                  fullWidth
                  size="sm"
                  className="nas-cta-margin"
                >
                  Probar FI-Cloud ahora →
                </Button>
              </div>

              {/* FI-Core */}
              <div className="nas-core-card">
                <div className="nas-card-header">
                  <div className="fi-icon-box-emerald">
                    <Server className="nas-core-icon" />
                  </div>
                  <div>
                    <h3 className="nas-core-title">FI-Core</h3>
                    <p className="fi-text-xs">Self-hosted · Control total</p>
                  </div>
                </div>

                <ul className="nas-feature-list">
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">100% on-premise</strong> – Datos nunca salen de tu red</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Air-gapped compatible</strong> – Funciona sin internet</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">White-label</strong> – Personaliza marca y dominio</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Cumplimiento regulatorio</strong> – Datos bajo tu jurisdicción</span>
                  </li>
                  <li className="nas-feature-item">
                    <Check className="nas-check-icon" strokeWidth={1.5} aria-hidden="true" />
                    <span><strong className="nas-strong">Sin límites</strong> – Usuarios/pacientes ilimitados</span>
                  </li>
                </ul>

                <div className="nas-ideal-section">
                  <p className="nas-ideal-label">Ideal para:</p>
                  <div className="nas-tag-list">
                    <span className="nas-tag-emerald">Hospitales</span>
                    <span className="nas-tag-emerald">Redes de clínicas</span>
                    <span className="nas-tag-emerald">Gobiernos</span>
                  </div>
                </div>

                <Button
                  onClick={() => setActiveTab("real-nas")}
                  variant="success"
                  fullWidth
                  size="sm"
                  className="nas-cta-margin"
                >
                  Instalar FI-Core →
                </Button>
              </div>
            </div>

            {/* Quick Comparison Table */}
            <div className="nas-table-wrap">
              <table className="nas-table">
                <thead className="nas-table-head">
                  <tr>
                    <th className="nas-th-left">Feature</th>
                    <th className="nas-th-blue">FI-Cloud</th>
                    <th className="nas-th-emerald">FI-Core</th>
                  </tr>
                </thead>
                <tbody className="nas-table-body">
                  <tr className="nas-row-dark">
                    <td className="nas-td">Tiempo de setup</td>
                    <td className="nas-td-center">30 segundos</td>
                    <td className="nas-td-center">1-2 horas</td>
                  </tr>
                  <tr className="nas-row-light">
                    <td className="nas-td">Hardware requerido</td>
                    <td className="nas-td-center">Ninguno</td>
                    <td className="nas-td-center">NAS/Servidor</td>
                  </tr>
                  <tr className="nas-row-dark">
                    <td className="nas-td">Ubicación de datos</td>
                    <td className="nas-td-center">Cloud seguro</td>
                    <td className="nas-td-center">Tu infraestructura</td>
                  </tr>
                  <tr className="nas-row-light">
                    <td className="nas-td">Mantenimiento</td>
                    <td className="nas-td-center">Automático</td>
                    <td className="nas-td-center">Manual</td>
                  </tr>
                  <tr className="nas-row-dark">
                    <td className="nas-td">Costo mensual (estimado)</td>
                    <td className="nas-td-center">$49-199/mes</td>
                    <td className="nas-td-center">Licencia única</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Technical Installation Guide (FI-Core only) */}
        <Card className="nas-install-card">
          <CardHeader>
            <CardTitle className="nas-install-title">FI-Core Installation Guide</CardTitle>
            <CardDescription className="nas-install-desc">
              Guía técnica de instalación para NAS (Synology, TrueNAS, QNAP) o simulación en PC.
              Requiere conocimientos de administración de sistemas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Services Overview */}
            <div className="nas-services-grid">
              {SERVICES.map((service) => (
                <div
                  key={service.name}
                  className="nas-service-card"
                >
                  <div>
                    <div className="nas-service-name">{service.name}</div>
                    <div className="fi-text-xs-muted">
                      {service.workers ? `${service.workers} workers` : "Single instance"}
                    </div>
                  </div>
                  <div className="nas-service-right">
                    <div className="nas-service-port">:{service.port}</div>
                    <div className="fi-text-xs-muted">{service.memory}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tabs Layout */}
        <div className="nas-layout-grid">
          {/* Left Panel: Table of Contents (Sticky) */}
          <div className="nas-sidebar">
            <Card className="nas-sidebar-card">
              <CardHeader>
                <CardTitle className="nas-sidebar-title">Installation Steps</CardTitle>
              </CardHeader>
              <CardContent>
                <nav className="nas-nav-list">
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
                        className={activeTab === item.id
                          ? "nas-nav-btn-active"
                          : "nas-nav-btn-inactive"
                        }
                      >
                        <Icon className="nas-nav-icon" />
                        {item.label}
                      </button>
                    );
                  })}
                </nav>
              </CardContent>
            </Card>
          </div>

          {/* Right Panel: Content */}
          <div className="nas-content">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="nas-tabs-list">
                <TabsTrigger value="real-nas" className="nas-tab-trigger">
                  <Server className="nas-tab-icon" />
                  Real NAS
                </TabsTrigger>
                <TabsTrigger value="pc-simulation" className="nas-tab-trigger">
                  <Laptop className="nas-tab-icon" />
                  PC Simulation
                </TabsTrigger>
                <TabsTrigger value="verification" className="nas-tab-trigger">
                  <CheckCircle2 className="nas-tab-icon" />
                  Verification
                </TabsTrigger>
              </TabsList>

              <TabsContent value="real-nas" className="nas-tab-content">
                <RealNASTab />
              </TabsContent>

              <TabsContent value="pc-simulation" className="nas-tab-content">
                <PCSimulationTab />
              </TabsContent>

              <TabsContent value="verification" className="nas-tab-content">
                <VerificationTab />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </AppTemplate>
  );
}
