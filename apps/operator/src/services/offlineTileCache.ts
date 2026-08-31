/**
 * AeroGuard Offline Map Tile Caching & Connectivity State Management Engine.
 *
 * Implements bounded IndexedDB map tile storage, quota management, and network state classification
 * (LIVE, DEGRADED, STALE, OFFLINE) for disconnected operator field stations.
 */

export enum NetworkConnectionMode {
  LIVE = 'LIVE',
  DEGRADED = 'DEGRADED',
  STALE = 'STALE',
  OFFLINE = 'OFFLINE',
}

export interface MapTileRecord {
  tileKey: string; // e.g. "z/x/y"
  blob: Blob;
  timestamp: number;
}

const DB_NAME = 'aeroguard_tile_cache';
const STORE_NAME = 'tiles';
const MAX_CACHED_TILES = 500;
const TILE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

class OfflineTileCache {
  private dbPromise: Promise<IDBDatabase | null> | null = null;
  private currentMode: NetworkConnectionMode = NetworkConnectionMode.LIVE;

  constructor() {
    if (typeof window !== 'undefined' && 'indexedDB' in window) {
      this.initDB();
    }
  }

  private initDB(): Promise<IDBDatabase | null> {
    if (this.dbPromise) return this.dbPromise;

    this.dbPromise = new Promise((resolve) => {
      try {
        const req = indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains(STORE_NAME)) {
            const store = db.createObjectStore(STORE_NAME, { keyPath: 'tileKey' });
            store.createIndex('timestamp', 'timestamp', { unique: false });
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });

    return this.dbPromise;
  }

  public getConnectionMode(): NetworkConnectionMode {
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return NetworkConnectionMode.OFFLINE;
    }
    return this.currentMode;
  }

  public setConnectionMode(mode: NetworkConnectionMode): void {
    this.currentMode = mode;
  }

  public async getCachedTile(tileKey: string): Promise<Blob | null> {
    const db = await this.initDB();
    if (!db) return null;

    return new Promise((resolve) => {
      try {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const req = tx.objectStore(STORE_NAME).get(tileKey);
        req.onsuccess = () => {
          const rec = req.result as MapTileRecord | undefined;
          if (rec && Date.now() - rec.timestamp < TILE_TTL_MS) {
            resolve(rec.blob);
          } else {
            resolve(null);
          }
        };
        req.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
  }

  public async cacheTile(tileKey: string, blob: Blob): Promise<boolean> {
    const db = await this.initDB();
    if (!db) return false;

    return new Promise((resolve) => {
      try {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const record: MapTileRecord = {
          tileKey,
          blob,
          timestamp: Date.now(),
        };
        store.put(record);
        tx.oncomplete = () => {
          this.enforceQuota(db);
          resolve(true);
        };
        tx.onerror = () => resolve(false);
      } catch {
        resolve(false);
      }
    });
  }

  private async enforceQuota(db: IDBDatabase): Promise<void> {
    try {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const countReq = store.count();
      countReq.onsuccess = () => {
        if (countReq.result > MAX_CACHED_TILES) {
          const index = store.index('timestamp');
          const cursorReq = index.openCursor();
          let deleted = 0;
          const toDelete = countReq.result - MAX_CACHED_TILES;
          cursorReq.onsuccess = () => {
            const cursor = cursorReq.result;
            if (cursor && deleted < toDelete) {
              cursor.delete();
              deleted++;
              cursor.continue();
            }
          };
        }
      };
    } catch {
      // Ignore quota enforcement errors
    }
  }
}

export const offlineTileCache = new OfflineTileCache();
