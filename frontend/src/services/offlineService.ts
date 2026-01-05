/**
 * Offline Service - IndexedDB wrapper for offline document storage
 */

const DB_NAME = 'alphha-offline';
const DB_VERSION = 1;

// Store names
const STORES = {
  DOCUMENTS: 'documents',
  SYNC_QUEUE: 'syncQueue',
  METADATA: 'metadata',
  FILES: 'files',
} as const;

// Sync queue item types
export interface SyncQueueItem {
  id: string;
  type: 'CREATE' | 'UPDATE' | 'DELETE';
  entity: 'document' | 'tag' | 'comment';
  entityId?: string;
  data: Record<string, unknown>;
  timestamp: number;
  retries: number;
  status: 'pending' | 'syncing' | 'failed';
}

// Offline document metadata
export interface OfflineDocument {
  id: string;
  title: string;
  fileName: string;
  mimeType: string;
  fileSize: number;
  thumbnailUrl?: string;
  downloadedAt: number;
  lastAccessed: number;
  syncStatus: 'synced' | 'pending' | 'local';
}

// File blob storage
export interface OfflineFile {
  documentId: string;
  blob: Blob;
  storedAt: number;
}

class OfflineService {
  private db: IDBDatabase | null = null;
  private dbPromise: Promise<IDBDatabase> | null = null;

  /**
   * Initialize the IndexedDB database
   */
  async init(): Promise<IDBDatabase> {
    if (this.db) return this.db;
    if (this.dbPromise) return this.dbPromise;

    this.dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error('Failed to open IndexedDB:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve(request.result);
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Documents store
        if (!db.objectStoreNames.contains(STORES.DOCUMENTS)) {
          const docStore = db.createObjectStore(STORES.DOCUMENTS, { keyPath: 'id' });
          docStore.createIndex('syncStatus', 'syncStatus', { unique: false });
          docStore.createIndex('downloadedAt', 'downloadedAt', { unique: false });
        }

        // Sync queue store
        if (!db.objectStoreNames.contains(STORES.SYNC_QUEUE)) {
          const syncStore = db.createObjectStore(STORES.SYNC_QUEUE, { keyPath: 'id' });
          syncStore.createIndex('status', 'status', { unique: false });
          syncStore.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // Metadata store (for app state)
        if (!db.objectStoreNames.contains(STORES.METADATA)) {
          db.createObjectStore(STORES.METADATA, { keyPath: 'key' });
        }

        // Files store (binary blobs)
        if (!db.objectStoreNames.contains(STORES.FILES)) {
          const fileStore = db.createObjectStore(STORES.FILES, { keyPath: 'documentId' });
          fileStore.createIndex('storedAt', 'storedAt', { unique: false });
        }
      };
    });

    return this.dbPromise;
  }

  /**
   * Get the database instance
   */
  private async getDB(): Promise<IDBDatabase> {
    if (this.db) return this.db;
    return this.init();
  }

  // ============ Document Operations ============

  /**
   * Save a document for offline access
   */
  async saveDocument(doc: OfflineDocument, fileBlob?: Blob): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORES.DOCUMENTS, STORES.FILES], 'readwrite');

      transaction.onerror = () => reject(transaction.error);
      transaction.oncomplete = () => resolve();

      // Save document metadata
      const docStore = transaction.objectStore(STORES.DOCUMENTS);
      docStore.put({
        ...doc,
        downloadedAt: Date.now(),
        lastAccessed: Date.now(),
      });

      // Save file blob if provided
      if (fileBlob) {
        const fileStore = transaction.objectStore(STORES.FILES);
        fileStore.put({
          documentId: doc.id,
          blob: fileBlob,
          storedAt: Date.now(),
        });
      }
    });
  }

  /**
   * Get an offline document by ID
   */
  async getDocument(id: string): Promise<OfflineDocument | null> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.DOCUMENTS, 'readonly');
      const store = transaction.objectStore(STORES.DOCUMENTS);
      const request = store.get(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const doc = request.result;
        if (doc) {
          // Update last accessed time
          this.updateLastAccessed(id);
        }
        resolve(doc || null);
      };
    });
  }

  /**
   * Get the file blob for a document
   */
  async getDocumentFile(documentId: string): Promise<Blob | null> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.FILES, 'readonly');
      const store = transaction.objectStore(STORES.FILES);
      const request = store.get(documentId);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const file = request.result as OfflineFile | undefined;
        resolve(file?.blob || null);
      };
    });
  }

  /**
   * Get all offline documents
   */
  async getAllDocuments(): Promise<OfflineDocument[]> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.DOCUMENTS, 'readonly');
      const store = transaction.objectStore(STORES.DOCUMENTS);
      const request = store.getAll();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  /**
   * Remove a document from offline storage
   */
  async removeDocument(id: string): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORES.DOCUMENTS, STORES.FILES], 'readwrite');

      transaction.onerror = () => reject(transaction.error);
      transaction.oncomplete = () => resolve();

      const docStore = transaction.objectStore(STORES.DOCUMENTS);
      docStore.delete(id);

      const fileStore = transaction.objectStore(STORES.FILES);
      fileStore.delete(id);
    });
  }

  /**
   * Update last accessed time
   */
  private async updateLastAccessed(id: string): Promise<void> {
    const db = await this.getDB();
    const doc = await this.getDocument(id);
    if (!doc) return;

    const transaction = db.transaction(STORES.DOCUMENTS, 'readwrite');
    const store = transaction.objectStore(STORES.DOCUMENTS);
    store.put({ ...doc, lastAccessed: Date.now() });
  }

  /**
   * Check if a document is available offline
   */
  async isAvailableOffline(id: string): Promise<boolean> {
    const doc = await this.getDocument(id);
    return doc !== null;
  }

  // ============ Sync Queue Operations ============

  /**
   * Add an item to the sync queue
   */
  async queueChange(item: Omit<SyncQueueItem, 'id' | 'timestamp' | 'retries' | 'status'>): Promise<string> {
    const db = await this.getDB();
    const id = `sync-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.SYNC_QUEUE, 'readwrite');
      const store = transaction.objectStore(STORES.SYNC_QUEUE);

      const queueItem: SyncQueueItem = {
        ...item,
        id,
        timestamp: Date.now(),
        retries: 0,
        status: 'pending',
      };

      const request = store.add(queueItem);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(id);
    });
  }

  /**
   * Get all pending sync items
   */
  async getPendingSyncItems(): Promise<SyncQueueItem[]> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.SYNC_QUEUE, 'readonly');
      const store = transaction.objectStore(STORES.SYNC_QUEUE);
      const index = store.index('status');
      const request = index.getAll('pending');

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  /**
   * Update sync item status
   */
  async updateSyncItemStatus(id: string, status: SyncQueueItem['status'], incrementRetry = false): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.SYNC_QUEUE, 'readwrite');
      const store = transaction.objectStore(STORES.SYNC_QUEUE);
      const getRequest = store.get(id);

      getRequest.onerror = () => reject(getRequest.error);
      getRequest.onsuccess = () => {
        const item = getRequest.result as SyncQueueItem;
        if (!item) {
          resolve();
          return;
        }

        item.status = status;
        if (incrementRetry) {
          item.retries++;
        }

        const putRequest = store.put(item);
        putRequest.onerror = () => reject(putRequest.error);
        putRequest.onsuccess = () => resolve();
      };
    });
  }

  /**
   * Remove a sync item
   */
  async removeSyncItem(id: string): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.SYNC_QUEUE, 'readwrite');
      const store = transaction.objectStore(STORES.SYNC_QUEUE);
      const request = store.delete(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  /**
   * Get sync queue status
   */
  async getSyncStatus(): Promise<{ pending: number; failed: number; total: number }> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.SYNC_QUEUE, 'readonly');
      const store = transaction.objectStore(STORES.SYNC_QUEUE);
      const request = store.getAll();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const items = request.result as SyncQueueItem[];
        resolve({
          pending: items.filter((i) => i.status === 'pending').length,
          failed: items.filter((i) => i.status === 'failed').length,
          total: items.length,
        });
      };
    });
  }

  // ============ Metadata Operations ============

  /**
   * Save metadata
   */
  async setMetadata(key: string, value: unknown): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.METADATA, 'readwrite');
      const store = transaction.objectStore(STORES.METADATA);
      const request = store.put({ key, value, updatedAt: Date.now() });

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  /**
   * Get metadata
   */
  async getMetadata<T>(key: string): Promise<T | null> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.METADATA, 'readonly');
      const store = transaction.objectStore(STORES.METADATA);
      const request = store.get(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const result = request.result;
        resolve(result?.value ?? null);
      };
    });
  }

  // ============ Storage Management ============

  /**
   * Get storage usage stats
   */
  async getStorageStats(): Promise<{
    documentsCount: number;
    filesSize: number;
    syncQueueCount: number;
  }> {
    const documents = await this.getAllDocuments();
    const syncStatus = await this.getSyncStatus();

    // Calculate total file size
    let filesSize = 0;
    for (const doc of documents) {
      filesSize += doc.fileSize || 0;
    }

    return {
      documentsCount: documents.length,
      filesSize,
      syncQueueCount: syncStatus.total,
    };
  }

  /**
   * Clear all offline data
   */
  async clearAll(): Promise<void> {
    const db = await this.getDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(
        [STORES.DOCUMENTS, STORES.FILES, STORES.SYNC_QUEUE, STORES.METADATA],
        'readwrite'
      );

      transaction.onerror = () => reject(transaction.error);
      transaction.oncomplete = () => resolve();

      transaction.objectStore(STORES.DOCUMENTS).clear();
      transaction.objectStore(STORES.FILES).clear();
      transaction.objectStore(STORES.SYNC_QUEUE).clear();
      transaction.objectStore(STORES.METADATA).clear();
    });
  }

  /**
   * Cleanup old documents (LRU eviction)
   */
  async cleanupOldDocuments(maxDocuments: number = 50): Promise<number> {
    const documents = await this.getAllDocuments();

    if (documents.length <= maxDocuments) {
      return 0;
    }

    // Sort by last accessed (oldest first)
    documents.sort((a, b) => a.lastAccessed - b.lastAccessed);

    // Remove oldest documents
    const toRemove = documents.slice(0, documents.length - maxDocuments);
    for (const doc of toRemove) {
      await this.removeDocument(doc.id);
    }

    return toRemove.length;
  }
}

// Export singleton instance
export const offlineService = new OfflineService();
export default offlineService;
