// LUXE.TECH — Centralized Fashion Intelligence API Client
// All requests flow through this client layer.

export const API_BASE = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' ? '/api' : 'http://127.0.0.1:8000/api');

export interface RequestOptions extends RequestInit {
  forceRefresh?: boolean;
}

class ApiClient {
  private token: string | null = null;
  private inFlightRequests: Map<string, Promise<any>> = new Map();
  private responseCache: Map<string, { timestamp: number; data: any }> = new Map();
  private cacheTtlMs: number = 30000; // 30s cache TTL

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('luxe_auth_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    this.responseCache.clear();
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('luxe_auth_token', token);
      } else {
        localStorage.removeItem('luxe_auth_token');
      }
    }
  }

  getToken(): string | null {
    return this.token;
  }

  clearCache() {
    this.responseCache.clear();
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const isGet = !options.method || options.method.toUpperCase() === 'GET';
    const cacheKey = `${options.method || 'GET'}:${path}`;

    if (isGet && !options.forceRefresh) {
      const cached = this.responseCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < this.cacheTtlMs) {
        return cached.data as T;
      }

      const pending = this.inFlightRequests.get(cacheKey);
      if (pending) {
        return pending as Promise<T>;
      }
    }

    const execPromise = (async () => {
      const url = `${API_BASE}${path}`;
      const headers = new Headers(options.headers || {});

      if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }

      if (this.token) {
        headers.set('Authorization', `Bearer ${this.token}`);
      }

      try {
        const response = await fetch(url, {
          ...options,
          headers,
        });

        const body = await response.json().catch(() => null);

        if (!response.ok) {
          const message = body?.error?.message ?? body?.detail;
          const errorMsg = typeof message === 'string'
            ? message
            : message && typeof message === 'object' && typeof message.message === 'string'
              ? message.message
              : `HTTP error ${response.status}`;
          throw new Error(errorMsg);
        }

        // Check standard LUXE.TECH ApiResponse envelope
        let data: T;
        if (body && typeof body === 'object' && 'success' in body) {
          if (body.success === false) {
            throw new Error(body.error?.message || 'Intelligence request failed');
          }
          data = body.data as T;
        } else {
          data = body as T;
        }

        if (isGet) {
          this.responseCache.set(cacheKey, { timestamp: Date.now(), data });
        } else {
          this.responseCache.clear();
        }

        return data;
      } catch (err: any) {
        console.warn(`[LUXE.TECH API] ${path} error:`, err.message);
        throw err;
      } finally {
        if (isGet) {
          this.inFlightRequests.delete(cacheKey);
        }
      }
    })();

    if (isGet) {
      this.inFlightRequests.set(cacheKey, execPromise);
    }

    return execPromise;
  }

  // 1. Dashboard
  async getDashboard() {
    return this.request<any>('/dashboard');
  }

  async getCurrentNews() {
    return this.request<any>('/news/current');
  }

  async getNewsStatus() {
    return this.request<any>('/news/status');
  }

  async getNewsArticles(params?: { category?: string; publisher?: string; limit?: number }) {
    const query = new URLSearchParams();
    if (params?.category) query.set('category', params.category);
    if (params?.publisher) query.set('publisher', params.publisher);
    if (params?.limit) query.set('limit', String(params.limit));
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any[]>(`/news/articles${qs}`);
  }

  async getCandidateTrends(params?: { category?: string }) {
    const query = new URLSearchParams();
    if (params?.category) query.set('category', params.category);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any[]>(`/news/candidate-trends${qs}`);
  }

  async triggerNewsIngest() {
    return this.request<any>('/news/ingest', {
      method: 'POST',
    });
  }

  async getVideoStatus() {
    return this.request<any>('/videos/status');
  }

  async searchVideos(params?: {
    query?: string;
    topic?: string;
    published_after?: string;
    order?: string;
    region_code?: string;
    duration?: string;
    limit?: number;
  }) {
    const query = new URLSearchParams();
    if (params?.query) query.set('query', params.query);
    if (params?.topic) query.set('topic', params.topic);
    if (params?.published_after) query.set('published_after', params.published_after);
    if (params?.order) query.set('order', params.order);
    if (params?.region_code) query.set('region_code', params.region_code);
    if (params?.duration) query.set('duration', params.duration);
    if (params?.limit) query.set('limit', String(params.limit));
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any>(`/videos/search${qs}`);
  }

  async createTrendSubmission(form: FormData) {
    return this.request<any>('/submissions', {
      method: 'POST',
      body: form,
    });
  }

  async getMySubmissions() {
    return this.request<any[]>('/submissions/mine');
  }

  // 2. Trends
  async getTrends(params?: { sort?: string; category?: string; limit?: number; include_candidates?: boolean }) {
    const query = new URLSearchParams();
    if (params?.sort) query.set('sort', params.sort);
    if (params?.category) query.set('category', params.category);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.include_candidates) query.set('include_candidates', 'true');
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any[]>(`/trends${qs}`);
  }

  async getTrend(slug: string) {
    return this.request<any>(`/trends/${encodeURIComponent(slug)}`);
  }

  async getCategories() {
    return this.request<any[]>('/trends/categories');
  }

  async createTrend(data: any) {
    return this.request<any>('/trends', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async toggleSaveTrend(trendId: string) {
    return this.request<any>(`/trends/${encodeURIComponent(trendId)}/save`, {
      method: 'POST',
    });
  }

  async getSavedTrends() {
    return this.request<any[]>('/trends/saved');
  }

  // 3. Signals
  async getLiveSignals() {
    return this.request<any>('/signals/live');
  }

  async getSignals(trendId: string) {
    return this.request<any[]>(`/signals/${encodeURIComponent(trendId)}`);
  }

  // 4. Collections
  async getCollection(trendId: string) {
    return this.request<any>(`/collections/${encodeURIComponent(trendId)}`);
  }

  async generateCollection(trendId: string) {
    return this.request<any>('/collections/generate', {
      method: 'POST',
      body: JSON.stringify({ trend_id: trendId }),
    });
  }

  // 5. Products
  async getProducts(trendId?: string, category?: string) {
    if (trendId) {
      return this.request<any[]>(`/products/trend/${encodeURIComponent(trendId)}`);
    }
    const query = new URLSearchParams();
    if (category) query.set('category', category);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any[]>(`/products${qs}`);
  }

  async getProduct(id: string) {
    return this.request<any>(`/products/${encodeURIComponent(id)}`);
  }

  async generateProducts(trendId: string, category?: string, targetConsumer?: string) {
    return this.request<any[]>('/products/generate', {
      method: 'POST',
      body: JSON.stringify({
        trend_id: trendId,
        category,
        target_consumer: targetConsumer,
      }),
    });
  }

  // 6. Retail
  async getRetail(trendId?: string) {
    if (trendId) {
      return this.request<any>(`/retail/trend/${encodeURIComponent(trendId)}`);
    }
    return this.request<any>('/retail');
  }

  async getRetailRegions() {
    return this.request<any[]>('/retail/regions');
  }

  async getRetailCategories() {
    return this.request<any[]>('/retail/categories');
  }

  // 7. Forecasts
  async getForecast(trendId: string, horizon: string = '3_months') {
    return this.request<any>(`/forecast/${encodeURIComponent(trendId)}?horizon=${horizon}`);
  }

  async triggerForecast(trendId: string, horizon: string = '3_months') {
    return this.request<any>(`/forecast/${encodeURIComponent(trendId)}?horizon=${horizon}`, {
      method: 'POST',
    });
  }

  // 8. Prophecy
  async getProphecy(trendId: string) {
    return this.request<any>(`/prophecy/${encodeURIComponent(trendId)}`);
  }

  async generateProphecy(trendId: string) {
    return this.request<any>(`/prophecy/${encodeURIComponent(trendId)}`, {
      method: 'POST',
    });
  }

  // 9. Search
  async search(query: string) {
    if (!query || query.trim().length < 2) {
      return { trends: [], products: [], collections: [], retail: [], prophecy: [] };
    }
    return this.request<any>(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  // 10. Image Analysis & Vision Lab
  async analyzeImage(file: File, trendId?: string) {
    const formData = new FormData();
    formData.append('file', file);
    if (trendId) {
      formData.append('trend_id', trendId);
    }
    return this.request<any>('/images/analyze', {
      method: 'POST',
      body: formData,
    });
  }

  async getImages(params?: { trendId?: string; mine?: boolean }) {
    const query = new URLSearchParams();
    if (params?.trendId) query.set('trend_id', params.trendId);
    if (params?.mine) query.set('mine', 'true');
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any[]>(`/images${qs}`);
  }

  async getImage(id: string) {
    return this.request<any>(`/images/${encodeURIComponent(id)}`);
  }

  async deleteImage(id: string) {
    return this.request<any>(`/images/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
  }

  // 11. Auth
  async login(email: string, password: string) {
    const data = await this.request<any>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data?.token) {
      this.setToken(data.token);
    }
    return data;
  }

  async register(email: string, password: string, name: string) {
    const data = await this.request<any>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });
    if (data?.token) {
      this.setToken(data.token);
    }
    return data;
  }

  async getMe() {
    return this.request<any>('/auth/me');
  }

  logout() {
    this.setToken(null);
  }
}

export const api = new ApiClient();

// Standalone function exports matching Master Prompt specifications
export const getDashboard = () => api.getDashboard();
export const getTrends = (params?: any) => api.getTrends(params);
export const getTrend = (slug: string) => api.getTrend(slug);
export const getSignals = (trendId: string) => api.getSignals(trendId);
export const getCollection = (trendId: string) => api.getCollection(trendId);
export const getProducts = (trendId?: string) => api.getProducts(trendId);
export const getRetail = (trendId?: string) => api.getRetail(trendId);
export const getForecast = (trendId: string) => api.getForecast(trendId);
export const getProphecy = (trendId: string) => api.getProphecy(trendId);
export const search = (query: string) => api.search(query);
export const analyzeImage = (file: File, trendId?: string) => api.analyzeImage(file, trendId);
export const getImages = (params?: { trendId?: string; mine?: boolean }) => api.getImages(params);
export const getImage = (id: string) => api.getImage(id);
export const deleteImage = (id: string) => api.deleteImage(id);
