/**
 * Exercise Storage Service - IndexedDB persistence for offline access
 * Stores exercise data, videos, and metadata locally
 */

export interface Exercise {
  id: string;
  title: string;
  description: string;
  duration: number; // seconds
  difficulty: 'easy' | 'medium' | 'hard';
  videoUrl: string;
  pictograms: string[]; // emoji or image paths
  instructions: string[];
  safetyAlerts: string[];
  accessibility: {
    spacereduced: boolean;
    chair: boolean;
    noEquipment: boolean;
    lowImpact: boolean;
  };
  tags: string[];
  thumbnail?: string;
  isFavorite?: boolean;
  isDownloaded?: boolean;
}

const DB_NAME = 'FIStride';
const DB_VERSION = 1;
const EXERCISES_STORE = 'exercises';
const VIDEOS_STORE = 'videos';
const METADATA_STORE = 'metadata';

export class ExerciseStorageService {
  private db: IDBDatabase | null = null;

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Create object stores if they don't exist
        if (!db.objectStoreNames.contains(EXERCISES_STORE)) {
          db.createObjectStore(EXERCISES_STORE, { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains(VIDEOS_STORE)) {
          db.createObjectStore(VIDEOS_STORE, { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains(METADATA_STORE)) {
          db.createObjectStore(METADATA_STORE, { keyPath: 'key' });
        }
      };
    });
  }

  async saveExercise(exercise: Exercise): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([EXERCISES_STORE], 'readwrite');
      const store = transaction.objectStore(EXERCISES_STORE);
      const request = store.put(exercise);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async getExercise(id: string): Promise<Exercise | undefined> {
    if (!this.db) throw new Error('Database not initialized');

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([EXERCISES_STORE], 'readonly');
      const store = transaction.objectStore(EXERCISES_STORE);
      const request = store.get(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async getAllExercises(): Promise<Exercise[]> {
    if (!this.db) throw new Error('Database not initialized');

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([EXERCISES_STORE], 'readonly');
      const store = transaction.objectStore(EXERCISES_STORE);
      const request = store.getAll();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async saveVideo(id: string, blob: Blob): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([VIDEOS_STORE], 'readwrite');
      const store = transaction.objectStore(VIDEOS_STORE);
      const request = store.put({ id, blob, timestamp: Date.now() });

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async getVideo(id: string): Promise<Blob | undefined> {
    if (!this.db) throw new Error('Database not initialized');

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([VIDEOS_STORE], 'readonly');
      const store = transaction.objectStore(VIDEOS_STORE);
      const request = store.get(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const result = request.result;
        resolve(result?.blob);
      };
    });
  }

  async setFavorite(id: string, isFavorite: boolean): Promise<void> {
    const exercise = await this.getExercise(id);
    if (exercise) {
      exercise.isFavorite = isFavorite;
      await this.saveExercise(exercise);
    }
  }

  async getFavorites(): Promise<Exercise[]> {
    const all = await this.getAllExercises();
    return all.filter((ex) => ex.isFavorite);
  }

  async searchByTag(tag: string): Promise<Exercise[]> {
    const all = await this.getAllExercises();
    return all.filter((ex) => ex.tags.includes(tag));
  }

  async searchByAccessibility(filter: keyof Exercise['accessibility']): Promise<Exercise[]> {
    const all = await this.getAllExercises();
    return all.filter((ex) => ex.accessibility[filter]);
  }

  async clearAllData(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(
        [EXERCISES_STORE, VIDEOS_STORE, METADATA_STORE],
        'readwrite'
      );

      const exercisesStore = transaction.objectStore(EXERCISES_STORE);
      const videosStore = transaction.objectStore(VIDEOS_STORE);
      const metadataStore = transaction.objectStore(METADATA_STORE);

      exercisesStore.clear();
      videosStore.clear();
      metadataStore.clear();

      transaction.onerror = () => reject(transaction.error);
      transaction.oncomplete = () => resolve();
    });
  }

  async getStorageStats(): Promise<{ exerciseCount: number; estimatedSize: string }> {
    const exercises = await this.getAllExercises();
    // Rough estimate: each exercise ~5KB
    const estimatedSize = `${Math.round((exercises.length * 5) / 1024)}MB`;
    return { exerciseCount: exercises.length, estimatedSize };
  }
}

export const exerciseStorage = new ExerciseStorageService();
