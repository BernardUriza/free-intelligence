import { useState } from 'react'
import styles from '../styles/privacy.module.css'

export function Privacy() {
  const [activeSection, setActiveSection] = useState<string | null>(null)

  const sections = [
    {
      id: 'privacy-policy',
      title: '🔒 Política de Privacidad',
      content: `
Nosotros en FI-Stride respetamos tu privacidad.

**Qué datos recopilamos:**
- Tu nombre y correo electrónico
- Información sobre tus sesiones de entrenamiento
- Datos de tu progreso en ejercicios

**Cómo usamos tus datos:**
- Para mejorar tu experiencia
- Para personalizar recomendaciones
- Para análisis anónimo de uso

**Tus derechos:**
- Puedes acceder a tus datos en cualquier momento
- Puedes solicitar la eliminación de tus datos
- Puedes exportar tus datos

**Cómo contactarnos:**
Email: privacidad@fi-stride.com
      `,
    },
    {
      id: 'data-security',
      title: '🛡️ Seguridad de Datos',
      content: `
Protegemos tu información con:

**Encriptación:**
- Todos los datos se transmiten con SSL/TLS
- Los datos en reposo están encriptados

**Acceso:**
- Solo tú puedes ver tus datos
- Los profesionales ven solo lo que autorizas

**Copias de seguridad:**
- Realizamos copias automáticas diarias
- Mantenemos múltiples copias en ubicaciones seguras

**Cumplimiento:**
- Cumplimos con GDPR y leyes locales
- Auditorías de seguridad regulares
      `,
    },
    {
      id: 'data-deletion',
      title: '🗑️ Eliminar Mis Datos',
      content: `
Entendemos que quizás desees eliminar tu cuenta y datos.

**Proceso de eliminación:**
1. Solicita la eliminación desde tu perfil
2. Te pediremos confirmar tu contraseña
3. Tus datos se eliminarán en 30 días (período de gracia)
4. Recibirás un email de confirmación

**Qué se elimina:**
- Tu perfil y cuenta
- Todas tus sesiones de entrenamiento
- Tus datos personales

**Qué NO se elimina:**
- Datos anónimos usados para mejorar la app
- Copias en archivos históricamente necesarios

**Contacto:**
Si tienes dudas: derechos@fi-stride.com
      `,
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>🔐 Privacidad y Seguridad</h1>
        <p>Tu información está segura con nosotros</p>
      </div>

      <div className={styles.content}>
        {sections.map((section) => (
          <div key={section.id} className={styles.section}>
            <button
              className={styles.sectionHeader}
              onClick={() =>
                setActiveSection(activeSection === section.id ? null : section.id)
              }
            >
              <span>{section.title}</span>
              <span className={styles.toggle}>
                {activeSection === section.id ? '▼' : '▶'}
              </span>
            </button>

            {activeSection === section.id && (
              <div className={styles.sectionBody}>
                {section.content.split('\n').map((line, idx) => (
                  <p key={idx} className={line.startsWith('**') ? styles.bold : ''}>
                    {line.replace(/\*\*/g, '')}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Consent Form */}
      <div className={styles.consent}>
        <h2>✅ Acepto los términos</h2>
        <div className={styles.checkboxGroup}>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" defaultChecked />
            <span>He leído la política de privacidad</span>
          </label>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" defaultChecked />
            <span>Autorizo el procesamiento de mis datos</span>
          </label>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" />
            <span>Autorizo el envío de recomendaciones</span>
          </label>
        </div>

        <button className={styles.saveBtn}>💾 Guardar Preferencias</button>
      </div>
    </div>
  )
}
