/**
 * Offline Store - Zustand store for offline state management
 */
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { offlineService, type OfflineDocument, type SyncQueueItem } from '@/services/offlineService';

interface OfflineState {
  // Connection status
  isOnline: boolean;
  setOnline: (online: boolean) => void;

  // Offline documents
  offlineDocuments: OfflineDocument[];
  loadOfflineDocuments: () => Promise<void>;
  markDocumentForOffline: (doc: OfflineDocument, fileBlob?: Blob) => Promise<void>;
  removeOfflineDocument: (id: string) => Promise<void>;
  isDocumentOffline: (id: string) => boolean;

  // Sync queue
  syncStatus: { pending: number; failed: number; total: number };
  loadSyncStatus: () => Promise<void>;
  queueChange: (item: Omit<SyncQueueItem, 'id' | 'timestamp' | 'retries' | 'status'>) => Promise<string>;
  processQueue: () => Promise<void>;
  isSyncing: boolean;

  // Storage
  storageStats: { documentsCount: number; filesSize: number; syncQueueCount: number };
  loadStorageStats: () => Promise<void>;
  clearOfflineData: () => Promise<void>;
}

export const useOfflineStore = create<OfflineState>()(
  persist(
    (set, get) => ({
      // Connection status
      isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,

      setOnline: (online) => {
        set({ isOnline: online });
        // Trigger sync when coming online
        if (online && get().syncStatus.pending > 0) {
          get().processQueue();
        }
      },

      // Offline documents
      offlineDocuments: [],

      loadOfflineDocuments: async () => {
        try {
          const docs = await offlineService.getAllDocuments();
          set({ offlineDocuments: docs });
        } catch (error) {
          console.error('Failed to load offline documents:', error);
        }
      },

      markDocumentForOffline: async (doc, fileBlob) => {
        try {
          await offlineService.saveDocument(doc, fileBlob);
          await get().loadOfflineDocuments();
          await get().loadStorageStats();
        } catch (error) {
          console.error('Failed to save document offline:', error);
          throw error;
        }
      },

      removeOfflineDocument: async (id) => {
        try {
          await offlineService.removeDocument(id);
          await get().loadOfflineDocuments();
          await get().loadStorageStats();
        } catch (error) {
          console.error('Failed to remove offline document:', error);
          throw error;
        }
      },

      isDocumentOffline: (id) => {
        return get().offlineDocuments.some((doc) => doc.id === id);
      },

      // Sync queue
      syncStatus: { pending: 0, failed: 0, total: 0 },
      isSyncing: false,

      loadSyncStatus: async () => {
        try {
          const status = await offlineService.getSyncStatus();
          set({ syncStatus: status });
        } catch (error) {
          console.error('Failed to load sync status:', error);
        }
      },

      queueChange: async (item) => {
        try {
          const id = await offlineService.queueChange(item);
          await get().loadSyncStatus();
          return id;
        } catch (error) {
          console.error('Failed to queue change:', error);
          throw error;
        }
      },

      processQueue: async () => {
        const state = get();
        if (state.isSyncing || !state.isOnline) return;

        set({ isSyncing: true });

        try {
          const pendingItems = await offlineService.getPendingSyncItems();

          for (const item of pendingItems) {
            try {
              // Mark as syncing
              await offlineService.updateSyncItemStatus(item.id, 'syncing');

              // Process based on type
              await processSyncItem(item);

              // Remove on success
              await offlineService.removeSyncItem(item.id);
            } catch (error) {
              console.error('Failed to sync item:', item.id, error);
              await offlineService.updateSyncItemStatus(item.id, 'failed', true);
            }
          }

          await get().loadSyncStatus();
        } catch (error) {
          console.error('Failed to process sync queue:', error);
        } finally {
          set({ isSyncing: false });
        }
      },

      // Storage
      storageStats: { documentsCount: 0, filesSize: 0, syncQueueCount: 0 },

      loadStorageStats: async () => {
        try {
          const stats = await offlineService.getStorageStats();
          set({ storageStats: stats });
        } catch (error) {
          console.error('Failed to load storage stats:', error);
        }
      },

      clearOfflineData: async () => {
        try {
          await offlineService.clearAll();
          set({
            offlineDocuments: [],
            syncStatus: { pending: 0, failed: 0, total: 0 },
            storageStats: { documentsCount: 0, filesSize: 0, syncQueueCount: 0 },
          });
        } catch (error) {
          console.error('Failed to clear offline data:', error);
          throw error;
        }
      },
    }),
    {
      name: 'alphha-offline',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist these values
        isOnline: state.isOnline,
      }),
    }
  )
);

// Process a sync queue item
async function processSyncItem(item: SyncQueueItem): Promise<void> {
  const baseUrl = import.meta.env.VITE_API_URL || '/api/v1';

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Get auth token from localStorage
  const authData = localStorage.getItem('auth-storage');
  if (authData) {
    try {
      const parsed = JSON.parse(authData);
      if (parsed?.state?.token) {
        headers['Authorization'] = `Bearer ${parsed.state.token}`;
      }
    } catch {
      // Ignore parsing errors
    }
  }

  switch (item.entity) {
    case 'document':
      if (item.type === 'CREATE') {
        // For document creation, we'd need to handle file upload
        // This is a simplified version
        throw new Error('Document creation sync not implemented');
      } else if (item.type === 'UPDATE' && item.entityId) {
        await fetch(`${baseUrl}/documents/${item.entityId}`, {
          method: 'PATCH',
          headers,
          body: JSON.stringify(item.data),
        });
      } else if (item.type === 'DELETE' && item.entityId) {
        await fetch(`${baseUrl}/documents/${item.entityId}`, {
          method: 'DELETE',
          headers,
        });
      }
      break;

    case 'tag':
      if (item.type === 'CREATE' && item.data.documentId) {
        await fetch(`${baseUrl}/tags/documents/${item.data.documentId}/tags`, {
          method: 'POST',
          headers,
          body: JSON.stringify(item.data),
        });
      } else if (item.type === 'DELETE' && item.entityId && item.data.documentId) {
        await fetch(`${baseUrl}/tags/documents/${item.data.documentId}/tags/${item.entityId}`, {
          method: 'DELETE',
          headers,
        });
      }
      break;

    case 'comment':
      // Handle comment sync
      break;
  }
}

// Initialize online/offline listeners
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    useOfflineStore.getState().setOnline(true);
  });

  window.addEventListener('offline', () => {
    useOfflineStore.getState().setOnline(false);
  });

  // Initialize on load
  offlineService.init().then(() => {
    useOfflineStore.getState().loadOfflineDocuments();
    useOfflineStore.getState().loadSyncStatus();
    useOfflineStore.getState().loadStorageStats();
  });
}

export default useOfflineStore;
