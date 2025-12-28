/**
 * MedicationForm Component
 *
 * Form for adding or editing a single medication in a prescription.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 */

"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
// Note: Using native textarea - no custom Textarea component exists
import {
  Medication,
  MedicationFrequency,
  MedicationRoute,
  FREQUENCY_LABELS,
  ROUTE_LABELS,
  DEFAULT_MEDICATION,
} from "@/lib/api/prescriptions";
import { Plus, Save, X } from "lucide-react";

interface MedicationFormProps {
  medication?: Medication;
  onSave: (medication: Medication) => void;
  onCancel?: () => void;
  isEditing?: boolean;
}

const FREQUENCY_OPTIONS = Object.entries(FREQUENCY_LABELS) as [
  MedicationFrequency,
  string
][];
const ROUTE_OPTIONS = Object.entries(ROUTE_LABELS) as [MedicationRoute, string][];

const COMMON_DOSAGE_FORMS = [
  "tableta",
  "cápsula",
  "jarabe",
  "suspensión",
  "crema",
  "gel",
  "gotas",
  "inyectable",
  "parche",
  "supositorio",
  "aerosol",
];

export function MedicationForm({
  medication,
  onSave,
  onCancel,
  isEditing = false,
}: MedicationFormProps) {
  const [formData, setFormData] = useState<Partial<Medication>>({
    ...DEFAULT_MEDICATION,
    ...medication,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (!formData.name?.trim()) {
      newErrors.name = "El nombre del medicamento es requerido";
    }
    if (!formData.dosage?.trim()) {
      newErrors.dosage = "La dosis es requerida";
    }
    if (
      formData.frequency === "custom" &&
      !formData.frequency_custom?.trim()
    ) {
      newErrors.frequency_custom =
        "Especifique la frecuencia personalizada";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();

      if (!validateForm()) {
        return;
      }

      onSave({
        name: formData.name!.trim(),
        dosage: formData.dosage!.trim(),
        dosage_form: formData.dosage_form || "tableta",
        frequency: formData.frequency || "every_8_hours",
        frequency_custom: formData.frequency_custom?.trim(),
        duration_days: formData.duration_days,
        duration_text: formData.duration_text?.trim(),
        route: formData.route || "oral",
        quantity: formData.quantity?.trim(),
        instructions: formData.instructions?.trim(),
        indication: formData.indication?.trim(),
        warnings: formData.warnings?.trim(),
        active_ingredient: formData.active_ingredient?.trim(),
      });

      // Reset form if not editing
      if (!isEditing) {
        setFormData({ ...DEFAULT_MEDICATION });
      }
    },
    [formData, validateForm, onSave, isEditing]
  );

  const updateField = useCallback(
    <K extends keyof Medication>(field: K, value: Medication[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
      // Clear error when field is updated
      if (errors[field]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[field];
          return next;
        });
      }
    },
    [errors]
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Medication Name */}
        <div className="space-y-2">
          <Label htmlFor="med-name" className="text-sm font-medium">
            Medicamento <span className="text-red-500">*</span>
          </Label>
          <Input
            id="med-name"
            value={formData.name || ""}
            onChange={(e) => updateField("name", e.target.value)}
            placeholder="Ej: Amoxicilina"
            className={errors.name ? "border-red-500" : ""}
          />
          {errors.name && (
            <p className="text-xs text-red-500">{errors.name}</p>
          )}
        </div>

        {/* Dosage */}
        <div className="space-y-2">
          <Label htmlFor="med-dosage" className="text-sm font-medium">
            Dosis <span className="text-red-500">*</span>
          </Label>
          <Input
            id="med-dosage"
            value={formData.dosage || ""}
            onChange={(e) => updateField("dosage", e.target.value)}
            placeholder="Ej: 500mg"
            className={errors.dosage ? "border-red-500" : ""}
          />
          {errors.dosage && (
            <p className="text-xs text-red-500">{errors.dosage}</p>
          )}
        </div>

        {/* Dosage Form */}
        <div className="space-y-2">
          <Label htmlFor="med-form" className="text-sm font-medium">
            Forma Farmacéutica
          </Label>
          <Select
            value={formData.dosage_form || "tableta"}
            onValueChange={(value) => updateField("dosage_form", value)}
          >
            <SelectTrigger id="med-form">
              <SelectValue placeholder="Seleccionar forma" />
            </SelectTrigger>
            <SelectContent>
              {COMMON_DOSAGE_FORMS.map((form) => (
                <SelectItem key={form} value={form}>
                  {form.charAt(0).toUpperCase() + form.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Route */}
        <div className="space-y-2">
          <Label htmlFor="med-route" className="text-sm font-medium">
            Vía de Administración
          </Label>
          <Select
            value={formData.route || "oral"}
            onValueChange={(value) =>
              updateField("route", value as MedicationRoute)
            }
          >
            <SelectTrigger id="med-route">
              <SelectValue placeholder="Seleccionar vía" />
            </SelectTrigger>
            <SelectContent>
              {ROUTE_OPTIONS.map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Frequency */}
        <div className="space-y-2">
          <Label htmlFor="med-frequency" className="text-sm font-medium">
            Frecuencia
          </Label>
          <Select
            value={formData.frequency || "every_8_hours"}
            onValueChange={(value) =>
              updateField("frequency", value as MedicationFrequency)
            }
          >
            <SelectTrigger id="med-frequency">
              <SelectValue placeholder="Seleccionar frecuencia" />
            </SelectTrigger>
            <SelectContent>
              {FREQUENCY_OPTIONS.map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Custom Frequency (conditional) */}
        {formData.frequency === "custom" && (
          <div className="space-y-2">
            <Label htmlFor="med-freq-custom" className="text-sm font-medium">
              Frecuencia Personalizada <span className="text-red-500">*</span>
            </Label>
            <Input
              id="med-freq-custom"
              value={formData.frequency_custom || ""}
              onChange={(e) => updateField("frequency_custom", e.target.value)}
              placeholder="Ej: Lunes, miércoles y viernes"
              className={errors.frequency_custom ? "border-red-500" : ""}
            />
            {errors.frequency_custom && (
              <p className="text-xs text-red-500">{errors.frequency_custom}</p>
            )}
          </div>
        )}

        {/* Duration */}
        <div className="space-y-2">
          <Label htmlFor="med-duration" className="text-sm font-medium">
            Duración (días)
          </Label>
          <Input
            id="med-duration"
            type="number"
            min={1}
            max={365}
            value={formData.duration_days || ""}
            onChange={(e) =>
              updateField(
                "duration_days",
                e.target.value ? parseInt(e.target.value) : undefined
              )
            }
            placeholder="Ej: 7"
          />
        </div>

        {/* Quantity */}
        <div className="space-y-2">
          <Label htmlFor="med-quantity" className="text-sm font-medium">
            Cantidad a Surtir
          </Label>
          <Input
            id="med-quantity"
            value={formData.quantity || ""}
            onChange={(e) => updateField("quantity", e.target.value)}
            placeholder="Ej: 21 tabletas"
          />
        </div>
      </div>

      {/* Instructions */}
      <div className="space-y-2">
        <Label htmlFor="med-instructions" className="text-sm font-medium">
          Instrucciones
        </Label>
        <textarea
          id="med-instructions"
          value={formData.instructions || ""}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => updateField("instructions", e.target.value)}
          placeholder="Ej: Tomar con alimentos para evitar molestias gástricas"
          rows={2}
          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            <X className="w-4 h-4 mr-1" />
            Cancelar
          </Button>
        )}
        <Button type="submit" variant="primary">
          {isEditing ? (
            <>
              <Save className="w-4 h-4 mr-1" />
              Guardar
            </>
          ) : (
            <>
              <Plus className="w-4 h-4 mr-1" />
              Agregar Medicamento
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
