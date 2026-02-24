/**
 * PhysicianTab Component
 *
 * Physician information form fields.
 * Single Responsibility: physician data entry UI.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

"use client";

import type { PhysicianInfo } from "@/lib/api/prescriptions";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stethoscope } from "lucide-react";

interface PhysicianTabProps {
  physician: PhysicianInfo;
  onPhysicianChange: React.Dispatch<React.SetStateAction<PhysicianInfo>>;
}

export function PhysicianTab({
  physician,
  onPhysicianChange,
}: PhysicianTabProps) {
  const update = (patch: Partial<PhysicianInfo>) =>
    onPhysicianChange((prev) => ({ ...prev, ...patch }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="rx-section-title">
          <Stethoscope className="rx-section-icon" />
          Información del Médico
        </CardTitle>
      </CardHeader>
      <CardContent className="rx-field-group">
        <div className="rx-fields-2col">
          <div className="rx-field">
            <Label htmlFor="physician-name">
              Nombre Completo <span className="rx-required">*</span>
            </Label>
            <Input
              id="physician-name"
              value={physician.name}
              onChange={(e) => update({ name: e.target.value })}
              placeholder="Dr(a). Nombre Completo"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="physician-license">
              Cédula Profesional <span className="rx-required">*</span>
            </Label>
            <Input
              id="physician-license"
              value={physician.professional_license}
              onChange={(e) =>
                update({ professional_license: e.target.value })
              }
              placeholder="Número de cédula"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="physician-specialty">Especialidad</Label>
            <Input
              id="physician-specialty"
              value={physician.specialty ?? ""}
              onChange={(e) => update({ specialty: e.target.value })}
              placeholder="Ej: Medicina General"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="physician-specialty-license">
              Cédula de Especialidad
            </Label>
            <Input
              id="physician-specialty-license"
              value={physician.specialty_license ?? ""}
              onChange={(e) =>
                update({ specialty_license: e.target.value })
              }
              placeholder="Número de cédula de especialidad"
            />
          </div>
          <div className="rx-field-wide">
            <Label htmlFor="physician-institution">
              Institución / Consultorio
            </Label>
            <Input
              id="physician-institution"
              value={physician.institution ?? ""}
              onChange={(e) => update({ institution: e.target.value })}
              placeholder="Nombre del consultorio o institución"
            />
          </div>
          <div className="rx-field-wide">
            <Label htmlFor="physician-address">Dirección</Label>
            <Input
              id="physician-address"
              value={physician.address ?? ""}
              onChange={(e) => update({ address: e.target.value })}
              placeholder="Dirección del consultorio"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="physician-phone">Teléfono</Label>
            <Input
              id="physician-phone"
              value={physician.phone ?? ""}
              onChange={(e) => update({ phone: e.target.value })}
              placeholder="Teléfono de contacto"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="physician-email">Email</Label>
            <Input
              id="physician-email"
              type="email"
              value={physician.email ?? ""}
              onChange={(e) => update({ email: e.target.value })}
              placeholder="correo@ejemplo.com"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
