import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { SessionDesigner } from './SessionDesigner'
import styles from '../styles/dashboard.module.css'

interface CoachStats {
  activeAthletes: number
  sessionsThisWeek: number
  avgCompletionRate: number
}

export function CoachDashboard() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [activeTab, setActiveTab] = useState<'overview' | 'athletes' | 'sessions' | 'designer' | 'settings'>('overview')

  // Mock stats - en producción vendrían del backend
  const stats: CoachStats = {
    activeAthletes: 12,
    sessionsThisWeek: 8,
    avgCompletionRate: 87,
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>👨‍🏫 Panel de Entrenador</h1>
          <p>Gestiona tus deportistas y sesiones</p>
        </div>
        <div className={styles.userInfo}>
          <span>Hola, {user?.name}</span>
          <button onClick={logout} className={styles.logoutBtn}>
            Cerrar sesión
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className={styles.nav}>
        <button
          className={`${styles.navBtn} ${activeTab === 'overview' ? styles.active : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📊 Overview
        </button>
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
          className={`${styles.navBtn} ${activeTab === 'designer' ? styles.active : ''}`}
          onClick={() => setActiveTab('designer')}
        >
          ✏️ Diseñador
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
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '30px' }}>
            {/* KPI Card 1 */}
            <div className={styles.section} style={{ borderLeft: '4px solid #667eea' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <p style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#666', fontWeight: 500 }}>Deportistas Activos</p>
                  <p style={{ margin: 0, fontSize: '2rem', fontWeight: 700, color: '#333' }}>{stats.activeAthletes}</p>
                </div>
                <span style={{ fontSize: '2.5rem' }}>👥</span>
              </div>
              <p style={{ margin: '15px 0 0 0', fontSize: '0.85rem', color: '#999' }}>Monitoreando progreso en tiempo real</p>
            </div>

            {/* KPI Card 2 */}
            <div className={styles.section} style={{ borderLeft: '4px solid #48bb78' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <p style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#666', fontWeight: 500 }}>Sesiones Esta Semana</p>
                  <p style={{ margin: 0, fontSize: '2rem', fontWeight: 700, color: '#333' }}>{stats.sessionsThisWeek}</p>
                </div>
                <span style={{ fontSize: '2.5rem' }}>📋</span>
              </div>
              <p style={{ margin: '15px 0 0 0', fontSize: '0.85rem', color: '#999' }}>Completadas y en progreso</p>
            </div>

            {/* KPI Card 3 */}
            <div className={styles.section} style={{ borderLeft: '4px solid #9f7aea' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <p style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#666', fontWeight: 500 }}>Tasa de Completitud</p>
                  <p style={{ margin: 0, fontSize: '2rem', fontWeight: 700, color: '#333' }}>{stats.avgCompletionRate}%</p>
                </div>
                <span style={{ fontSize: '2.5rem' }}>⭐</span>
              </div>
              <div style={{ marginTop: '15px', height: '6px', background: '#e0e0e0', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', background: '#9f7aea', width: `${stats.avgCompletionRate}%`, transition: 'width 0.3s' }}></div>
              </div>
            </div>
          </div>
        )}

        {/* Sessions Table - shown in Overview */}
        {activeTab === 'overview' && (
          <div className={styles.section}>
            <h2>Sesiones Recientes</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e0e0e0', background: '#f9f9f9' }}>
                  <th style={{ textAlign: 'left', padding: '12px', fontWeight: 600, fontSize: '0.85rem', color: '#666' }}>Deportista</th>
                  <th style={{ textAlign: 'left', padding: '12px', fontWeight: 600, fontSize: '0.85rem', color: '#666' }}>Tipo</th>
                  <th style={{ textAlign: 'left', padding: '12px', fontWeight: 600, fontSize: '0.85rem', color: '#666' }}>Duración</th>
                  <th style={{ textAlign: 'left', padding: '12px', fontWeight: 600, fontSize: '0.85rem', color: '#666' }}>Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #e0e0e0' }}>
                  <td style={{ padding: '12px', color: '#333' }}>Juan García</td>
                  <td style={{ padding: '12px', color: '#666' }}>Fuerza</td>
                  <td style={{ padding: '12px', color: '#666' }}>45 min</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ background: '#c6f6d5', color: '#22543d', padding: '4px 12px', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 600 }}>✅ Completada</span>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #e0e0e0' }}>
                  <td style={{ padding: '12px', color: '#333' }}>María López</td>
                  <td style={{ padding: '12px', color: '#666' }}>Resistencia</td>
                  <td style={{ padding: '12px', color: '#666' }}>30 min</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ background: '#feebc8', color: '#7c2d12', padding: '4px 12px', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 600 }}>⏳ En Progreso</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* Athletes Tab */}
        {activeTab === 'athletes' && (
          <section className={styles.section}>
            <h2>Mis Deportistas</h2>
            <div className={styles.emptyState}>
              <p>📭 No hay deportistas asignados aún</p>
              <button className={styles.primaryBtn}>+ Agregar Deportista</button>
            </div>
          </section>
        )}

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <section className={styles.section}>
            <h2>Sesiones Recientes</h2>
            <div className={styles.emptyState}>
              <p>📭 No hay sesiones registradas</p>
              <button className={styles.primaryBtn}>+ Nueva Sesión</button>
            </div>
          </section>
        )}

        {/* Session Designer Tab */}
        {activeTab === 'designer' && (
          <SessionDesigner />
        )}

        {/* Settings Tab */}
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
              <button onClick={logout} className={styles.primaryBtn} style={{ marginTop: '20px', width: '100%' }}>
                Cerrar sesión
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
