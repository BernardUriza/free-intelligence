/**
 * Patient Form Validation Tests
 *
 * Unit tests for validatePatientField and validatePatientForm.
 * These are pure functions with no React dependencies.
 */

import {
  validatePatientField,
  validatePatientForm,
  validateCURP,
} from '../usePatientFormValidation';

describe('validateCURP', () => {
  it('should return true for empty CURP (optional field)', () => {
    expect(validateCURP('')).toBe(true);
  });

  it('should return true for valid male CURP', () => {
    // CURP format: 4 letters + 6 digits + H/M + 5 letters + alphanumeric + digit
    expect(validateCURP('GAML800101HDFRRS09')).toBe(true);
  });

  it('should return true for valid female CURP', () => {
    expect(validateCURP('GARM850215MDFRRL05')).toBe(true);
  });

  it('should return false for too short CURP', () => {
    expect(validateCURP('GAML80010')).toBe(false);
  });

  it('should return false for invalid format', () => {
    expect(validateCURP('123456789012345678')).toBe(false);
    expect(validateCURP('AAAA000000XAAAAA00')).toBe(false); // X instead of H/M
  });

  it('should handle lowercase input', () => {
    expect(validateCURP('gaml800101hdfrrs09')).toBe(true);
  });
});

describe('validatePatientField', () => {
  describe('nombre', () => {
    it('should return error for empty nombre', () => {
      expect(validatePatientField('nombre', '')).toBe('Nombre es requerido');
      expect(validatePatientField('nombre', '   ')).toBe('Nombre es requerido');
    });

    it('should return error for nombre too short', () => {
      expect(validatePatientField('nombre', 'A')).toBe(
        'Nombre debe tener al menos 2 caracteres'
      );
    });

    it('should return error for nombre with numbers', () => {
      expect(validatePatientField('nombre', 'María123')).toBe(
        'Nombre solo puede contener letras'
      );
    });

    it('should accept valid nombres', () => {
      expect(validatePatientField('nombre', 'María')).toBeUndefined();
      expect(validatePatientField('nombre', 'José Luis')).toBeUndefined();
      expect(validatePatientField('nombre', "María del Carmen O'Brien")).toBeUndefined();
    });

    it('should accept nombres with accents', () => {
      expect(validatePatientField('nombre', 'José')).toBeUndefined();
      expect(validatePatientField('nombre', 'Ángela')).toBeUndefined();
      expect(validatePatientField('nombre', 'Nuño')).toBeUndefined();
    });
  });

  describe('apellido', () => {
    it('should return error for empty apellido', () => {
      expect(validatePatientField('apellido', '')).toBe('Apellido es requerido');
    });

    it('should return error for apellido too short', () => {
      expect(validatePatientField('apellido', 'G')).toBe(
        'Apellido debe tener al menos 2 caracteres'
      );
    });

    it('should accept valid apellidos', () => {
      expect(validatePatientField('apellido', 'García')).toBeUndefined();
      expect(validatePatientField('apellido', 'García López')).toBeUndefined();
      expect(validatePatientField('apellido', "O'Connor")).toBeUndefined();
    });
  });

  describe('fecha_nacimiento', () => {
    it('should return error for empty fecha', () => {
      expect(validatePatientField('fecha_nacimiento', '')).toBe(
        'Fecha de nacimiento es requerida'
      );
    });

    it('should return error for invalid date format', () => {
      expect(validatePatientField('fecha_nacimiento', 'not-a-date')).toBe(
        'Fecha no válida'
      );
    });

    it('should return error for future date', () => {
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 1);
      expect(validatePatientField('fecha_nacimiento', futureDate.toISOString())).toBe(
        'Fecha no puede ser en el futuro'
      );
    });

    it('should return error for impossibly old date', () => {
      expect(validatePatientField('fecha_nacimiento', '1800-01-01')).toBe(
        'Fecha de nacimiento no válida'
      );
    });

    it('should accept valid dates', () => {
      expect(validatePatientField('fecha_nacimiento', '1990-05-15')).toBeUndefined();
      expect(validatePatientField('fecha_nacimiento', '2000-12-31')).toBeUndefined();
    });
  });

  describe('curp', () => {
    it('should return undefined for empty CURP (optional)', () => {
      expect(validatePatientField('curp', '')).toBeUndefined();
      expect(validatePatientField('curp', null)).toBeUndefined();
      expect(validatePatientField('curp', undefined)).toBeUndefined();
    });

    it('should return error for wrong length', () => {
      expect(validatePatientField('curp', 'GAML80010')).toBe(
        'CURP debe tener 18 caracteres'
      );
    });

    it('should return error for invalid format', () => {
      expect(validatePatientField('curp', '123456789012345678')).toBe(
        'Formato de CURP inválido'
      );
    });

    it('should accept valid CURP', () => {
      expect(validatePatientField('curp', 'GAML800101HDFRRS09')).toBeUndefined();
    });
  });

  describe('genero', () => {
    it('should return undefined for any genero value (optional field)', () => {
      expect(validatePatientField('genero', '')).toBeUndefined();
      expect(validatePatientField('genero', 'MASCULINO')).toBeUndefined();
      expect(validatePatientField('genero', 'FEMENINO')).toBeUndefined();
      expect(validatePatientField('genero', null)).toBeUndefined();
    });
  });
});

describe('validatePatientForm', () => {
  const validData = {
    nombre: 'María',
    apellido: 'García',
    fecha_nacimiento: '1990-05-15',
  };

  it('should return isValid true for valid data', () => {
    const result = validatePatientForm(validData);
    expect(result.isValid).toBe(true);
    expect(result.errors).toEqual({});
  });

  it('should return isValid false with errors for invalid data', () => {
    const result = validatePatientForm({
      nombre: '',
      apellido: 'G',
      fecha_nacimiento: '',
    });

    expect(result.isValid).toBe(false);
    expect(result.errors.nombre).toBeDefined();
    expect(result.errors.apellido).toBeDefined();
    expect(result.errors.fecha_nacimiento).toBeDefined();
  });

  it('should validate CURP when includeCurp option is true', () => {
    const result = validatePatientForm(
      {
        ...validData,
        curp: 'invalid',
      },
      { includeCurp: true }
    );

    expect(result.isValid).toBe(false);
    expect(result.errors.curp).toBeDefined();
  });

  it('should not validate CURP when includeCurp option is false', () => {
    const result = validatePatientForm(
      {
        ...validData,
        curp: 'invalid',
      },
      { includeCurp: false }
    );

    expect(result.isValid).toBe(true);
    expect(result.errors.curp).toBeUndefined();
  });

  it('should handle full valid form with all fields', () => {
    const result = validatePatientForm(
      {
        nombre: 'María José',
        apellido: 'García López',
        fecha_nacimiento: '1990-05-15',
        genero: 'FEMENINO',
        curp: 'GARM900515MDFRRL05',
      },
      { includeCurp: true }
    );

    expect(result.isValid).toBe(true);
    expect(result.errors).toEqual({});
  });
});
