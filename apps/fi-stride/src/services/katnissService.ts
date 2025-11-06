/**
 * KATNISS Service
 * Keeper Artificial Trainer Nurturing Intelligence Sportive Spark
 *
 * Integración con Ollama para análisis post-sesión
 */

export interface SessionData {
  duration: number // minutos
  rpe: number // 1-10 Rate of Perceived Exertion
  emotionalCheckIn: 'happy' | 'neutral' | 'tired'
  notes?: string
  athleteName?: string
}

export interface KATNISSResponse {
  motivation: string
  nextSuggestion: string
  dayRecommended: string
  timestamp: Date
}

class KatnissService {
  private ollamaBaseUrl: string

  constructor(baseUrl: string = 'http://localhost:11434') {
    this.ollamaBaseUrl = baseUrl
  }

  /**
   * Analiza datos de sesión y genera feedback con Ollama
   */
  async analyzeSession(sessionData: SessionData): Promise<KATNISSResponse> {
    try {
      const prompt = this.buildPrompt(sessionData)

      // Llamar a Ollama local
      const response = await fetch(`${this.ollamaBaseUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'qwen2:7b', // o mistral, neural-chat, etc
          prompt,
          stream: false,
          temperature: 0.7
        })
      })

      if (!response.ok) {
        throw new Error(`Ollama error: ${response.statusText}`)
      }

      const data = await response.json()
      return this.parseResponse(data.response, sessionData)
    } catch (error) {
      console.error('KATNISS analysis error:', error)
      // Fallback response si Ollama falla
      return this.getFallbackResponse(sessionData)
    }
  }

  /**
   * Construye el prompt para Ollama
   */
  private buildPrompt(sessionData: SessionData): string {
    const emotionalMap = {
      happy: '¡Excelente!',
      neutral: 'Bien',
      tired: 'Cansado'
    }

    return `Eres KATNISS, un entrenador de IA empático para personas con T21 (síndrome de Down).

El deportista ${sessionData.athleteName || 'has'} completado una sesión de entrenamiento con estos datos:
- Duración: ${sessionData.duration} minutos
- Esfuerzo percibido (RPE): ${sessionData.rpe}/10
- Estado emocional: ${emotionalMap[sessionData.emotionalCheckIn]}
${sessionData.notes ? `- Notas: ${sessionData.notes}` : ''}

Genera en formato JSON VÁLIDO (sin markdown, sin explicaciones extras):
{
  "motivation": "Una frase corta y motivadora (máx 15 palabras, en español simple, sin PHI)",
  "nextSuggestion": "Sugerencia concisa para próxima sesión (máx 12 palabras)",
  "dayRecommended": "Ej: 'mañana' o 'en 2 días' (recomendación de cuándo entrenar next)"
}

IMPORTANTE:
- Usa lenguaje accesible (T21-friendly, simple, directo)
- Sé empático y motivador
- Responde SOLO el JSON, nada más`
  }

  /**
   * Parsea la respuesta de Ollama
   */
  private parseResponse(responseText: string, sessionData: SessionData): KATNISSResponse {
    try {
      // Limpia la respuesta de posibles espacios/caracteres extras
      const jsonMatch = responseText.match(/\{[\s\S]*\}/)
      if (!jsonMatch) {
        throw new Error('No JSON found in response')
      }

      const parsed = JSON.parse(jsonMatch[0])
      return {
        motivation: parsed.motivation || 'Great session!',
        nextSuggestion: parsed.nextSuggestion || 'Keep training regularly',
        dayRecommended: parsed.dayRecommended || 'tomorrow',
        timestamp: new Date()
      }
    } catch (error) {
      console.error('Failed to parse KATNISS response:', error)
      return this.getFallbackResponse(sessionData)
    }
  }

  /**
   * Respuesta por defecto si Ollama no está disponible
   */
  private getFallbackResponse(sessionData: SessionData): KATNISSResponse {
    const motivations = [
      '¡Lo hiciste increíble!',
      '¡Sigue adelante!',
      '¡Eres muy fuerte!',
      '¡Excelente trabajo!',
      '¡Puedes con todo!'
    ]

    const suggestions = [
      'Descansa bien hoy',
      'Toma mucha agua',
      'Come frutas saludables',
      'Duerme 8 horas',
      'Sigue practicando'
    ]

    const days = ['mañana', 'en 2 días', 'el fin de semana', 'cuando quieras']

    return {
      motivation: motivations[Math.floor(Math.random() * motivations.length)],
      nextSuggestion: suggestions[Math.floor(Math.random() * suggestions.length)],
      dayRecommended: days[Math.floor(Math.random() * days.length)],
      timestamp: new Date()
    }
  }
}

export default new KatnissService()
