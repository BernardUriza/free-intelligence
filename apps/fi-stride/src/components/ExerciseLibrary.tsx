import React, { useState, useEffect } from 'react';
import { Exercise } from '../services/exerciseStorage';
import { EXERCISE_CATALOG } from '../data/exerciseCatalog';

interface ExerciseLibraryProps {
  onSelectExercise?: (exercise: Exercise) => void;
}

export function ExerciseLibrary({ onSelectExercise }: ExerciseLibraryProps) {
  const [exercises, setExercises] = useState<Exercise[]>(EXERCISE_CATALOG);
  const [selectedDifficulty, setSelectedDifficulty] = useState<'all' | 'easy' | 'medium' | 'hard'>('all');
  const [selectedAccessibility, setSelectedAccessibility] = useState<string>('all');
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');

  // Load favorites from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('exerciseFavorites');
    if (saved) {
      try {
        setFavorites(new Set(JSON.parse(saved)));
      } catch (e) {
        console.error('Failed to load favorites:', e);
      }
    }
  }, []);

  // Save favorites to localStorage
  useEffect(() => {
    localStorage.setItem('exerciseFavorites', JSON.stringify(Array.from(favorites)));
  }, [favorites]);

  const filterExercises = () => {
    let filtered = [...EXERCISE_CATALOG];

    // Difficulty filter
    if (selectedDifficulty !== 'all') {
      filtered = filtered.filter((ex) => ex.difficulty === selectedDifficulty);
    }

    // Accessibility filter
    if (selectedAccessibility !== 'all') {
      filtered = filtered.filter((ex) => {
        const key = selectedAccessibility as keyof Exercise['accessibility'];
        return ex.accessibility[key];
      });
    }

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(
        (ex) =>
          ex.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          ex.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
          ex.tags.some((tag) => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    setExercises(filtered);
  };

  useEffect(() => {
    filterExercises();
  }, [selectedDifficulty, selectedAccessibility, searchTerm]);

  const toggleFavorite = (id: string) => {
    const newFavorites = new Set(favorites);
    if (newFavorites.has(id)) {
      newFavorites.delete(id);
    } else {
      newFavorites.add(id);
    }
    setFavorites(newFavorites);
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">📚 Biblioteca de Ejercicios</h1>
        <p className="text-slate-400">
          {exercises.length} ejercicio{exercises.length !== 1 ? 's' : ''} disponible
          {exercises.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="🔍 Busca un ejercicio..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-3 bg-slate-700 text-white rounded-lg border border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <div>
          <label className="block text-sm font-semibold mb-2">Dificultad</label>
          <select
            value={selectedDifficulty}
            onChange={(e) => setSelectedDifficulty(e.target.value as any)}
            className="w-full px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600"
          >
            <option value="all">Todas</option>
            <option value="easy">Fácil</option>
            <option value="medium">Medio</option>
            <option value="hard">Difícil</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold mb-2">Accesibilidad</label>
          <select
            value={selectedAccessibility}
            onChange={(e) => setSelectedAccessibility(e.target.value)}
            className="w-full px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600"
          >
            <option value="all">Todas</option>
            <option value="spacereduced">Espacio Reducido</option>
            <option value="chair">En Silla</option>
            <option value="noEquipment">Sin Equipo</option>
            <option value="lowImpact">Bajo Impacto</option>
          </select>
        </div>

        <div className="col-span-2 md:col-span-1">
          <label className="block text-sm font-semibold mb-2">Estado</label>
          <button
            onClick={() => setSearchTerm('')}
            className="w-full px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Limpiar Filtros
          </button>
        </div>
      </div>

      {/* Exercise Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {exercises.map((exercise) => (
          <div
            key={exercise.id}
            className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden hover:border-blue-500 transition-colors cursor-pointer"
            onClick={() => onSelectExercise?.(exercise)}
          >
            {/* Exercise Card */}
            <div className="p-4">
              {/* Pictograms + Favorite */}
              <div className="flex justify-between items-start mb-3">
                <div className="flex gap-1 text-2xl">
                  {exercise.pictograms.slice(0, 2).map((p, i) => (
                    <span key={i}>{p}</span>
                  ))}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFavorite(exercise.id);
                  }}
                  className="text-2xl cursor-pointer"
                >
                  {favorites.has(exercise.id) ? '❤️' : '🤍'}
                </button>
              </div>

              {/* Title */}
              <h3 className="text-lg font-bold mb-2">{exercise.title}</h3>

              {/* Description */}
              <p className="text-sm text-slate-300 mb-3">{exercise.description}</p>

              {/* Duration + Difficulty */}
              <div className="flex gap-2 mb-3 text-sm">
                <span className="bg-blue-900 px-2 py-1 rounded">⏱️ {exercise.duration}s</span>
                <span
                  className={`px-2 py-1 rounded ${
                    exercise.difficulty === 'easy'
                      ? 'bg-green-900'
                      : exercise.difficulty === 'medium'
                        ? 'bg-yellow-900'
                        : 'bg-red-900'
                  }`}
                >
                  {exercise.difficulty === 'easy'
                    ? '🟢 Fácil'
                    : exercise.difficulty === 'medium'
                      ? '🟡 Medio'
                      : '🔴 Difícil'}
                </span>
              </div>

              {/* Accessibility Tags */}
              <div className="flex flex-wrap gap-2 text-xs">
                {exercise.accessibility.spacereduced && (
                  <span className="bg-slate-700 px-2 py-1 rounded">📏 Espacio reducido</span>
                )}
                {exercise.accessibility.chair && (
                  <span className="bg-slate-700 px-2 py-1 rounded">🪑 En silla</span>
                )}
                {exercise.accessibility.noEquipment && (
                  <span className="bg-slate-700 px-2 py-1 rounded">🆓 Sin equipo</span>
                )}
                {exercise.accessibility.lowImpact && (
                  <span className="bg-slate-700 px-2 py-1 rounded">💚 Bajo impacto</span>
                )}
              </div>

              {/* Download Button */}
              <button className="w-full mt-4 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors">
                ⬇️ Descargar para Offline
              </button>
            </div>
          </div>
        ))}
      </div>

      {exercises.length === 0 && (
        <div className="text-center py-12">
          <p className="text-2xl mb-2">😕 No hay ejercicios que coincidan</p>
          <p className="text-slate-400">Intenta cambiar los filtros de búsqueda</p>
        </div>
      )}
    </div>
  );
}
