import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import styles from '../styles/dashboard.module.css'

export function CoachDashboard() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [activeTab, setActiveTab] = useState<'athletes' | 'sessions' | 'settings'>('athletes')

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>Panel de Entrenador</h1>
          <p>Gestiona tus deportistas y sesiones</p>
        </div>
        <div className={styles.userInfo}>
          <span>👨‍🏫 {user?.name}</span>
          <button onClick={logout} className={styles.logoutBtn}>
            Cerrar sesión
          </button>
        </div>
      </header>

      {/* Navigation */}
      <nav className={styles.nav}>
        <button
          className={`${styles.navBtn} ${activeTab === 'athletes' ? styles.active : ''}`}
          onClick={() => setActiveTab('athletes')}
        >
          👥 Deportistas
        </button>
        <button
          className={`${styles.navBtn} ${activeTab === 'sessions' ? styles.active : ''}`}
          onClick={() => setActiveTab('sessions')}
        >
          📋 Sesiones
        </button>
        <button
          className={`${styles.navBtn} ${activeTab === 'settings' ? styles.active : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          ⚙️ Configuración
        </button>
      </nav>

      {/* Content */}
      <main className={styles.main}>
        {activeTab === 'athletes' && (
          <section className={styles.section}>
            <h2>Mis Deportistas</h2>
            <div className={styles.emptyState}>
              <p>📭 No hay deportistas asignados aún</p>
              <button className={styles.primaryBtn}>+ Agregar Deportista</button>
            </div>
          </section>
        )}

        {activeTab === 'sessions' && (
          <section className={styles.section}>
            <h2>Sesiones Recientes</h2>
            <div className={styles.emptyState}>
              <p>📭 No hay sesiones registradas</p>
              <button className={styles.primaryBtn}>+ Nueva Sesión</button>
            </div>
          </section>
        )}

        {activeTab === 'settings' && (
          <section className={styles.section}>
            <h2>Configuración</h2>
            <div className={styles.settingsForm}>
              <div className={styles.formGroup}>
                <label>Nombre</label>
                <input type="text" defaultValue={user?.name} disabled />
              </div>
              <div className={styles.formGroup}>
                <label>Correo</label>
                <input type="email" defaultValue={user?.email} disabled />
              </div>
              <p className={styles.helpText}>
                Contacta al administrador para cambiar estos datos
              </p>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
