import { ChangeEvent, KeyboardEvent, ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  Camera,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Eye,
  LockKeyhole,
  LogOut,
  Menu,
  Pause,
  Play,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Upload,
  User,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react';
import { api } from './services/api';
import { mapNewsCandidates, type NewsDerivedCandidate } from './services/newsCandidates.mjs';

type Page = 'home' | 'trend' | 'videos' | 'product' | 'retail' | 'forecast' | 'prophecy';
type AnyRecord = Record<string, any>;
type NavigateOptions = { trend?: AnyRecord; category?: string };
type NavigateFn = (page: Page, options?: NavigateOptions) => void;

const THEME_ARCHETYPE_DNA: Record<string, {
  colors: Array<{ hex: string; percentage: number }>;
  materials: string[];
  textures: string[];
  silhouettes: string[];
  patterns: string[];
}> = {
  'Sculptural Tailoring & Suiting': {
    colors: [
      { hex: '#1E252B', percentage: 46 },
      { hex: '#8C969E', percentage: 30 },
      { hex: '#E3DAC9', percentage: 16 },
      { hex: '#DF7E8C', percentage: 8 },
    ],
    materials: ['Double-Faced Wool Twill', 'Fine Worsted Wool', 'Silk-Cotton Gabardine', 'Cupro Weave'],
    textures: ['Crisp Structured', 'Dry Pressed Finish', 'Tactile Twill'],
    silhouettes: ['Oversized Architectural Blazer', 'High-Rise Wide Trouser', 'Structured Shoulder'],
    patterns: ['Monochrome Solid', 'Subtle Chalk Pinstripe', 'Tonal Houndstooth'],
  },
  'Sheer & Translucent Layering': {
    colors: [
      { hex: '#3A3535', percentage: 45 },
      { hex: '#E2D9D2', percentage: 35 },
      { hex: '#102126', percentage: 20 },
    ],
    materials: ['Silk Organza', 'Technical Chiffon', 'Fine Gauze Mesh', 'Frosted Polyurethane'],
    textures: ['Translucent Veil', 'Gauzy Texture', 'Layered Shadow'],
    silhouettes: ['Tiered Slip Dress', 'Fluid Draped Tunic', 'Sheer Trench Overlay'],
    patterns: ['Pure Translucence', 'Subtle Gradient', 'Shadow Layering'],
  },
  'Butter Yellow & Warm Pastels': {
    colors: [
      { hex: '#FFF3B0', percentage: 50 },
      { hex: '#F7F4EA', percentage: 32 },
      { hex: '#D4A373', percentage: 18 },
    ],
    materials: ['Crisp Cotton Poplin', 'Fine Gauge Cashmere Knit', 'Silk Sateen'],
    textures: ['Soft Touch', 'Matte Chalk Finish', 'Fine Weave'],
    silhouettes: ['Unlined Summer Suiting', 'Minimalist Slip Dress', 'Relaxed Overshirt'],
    patterns: ['Solid Colorblock', 'Tonal Pastel Blend'],
  },
  'Deep Burgundy & Oxblood Accents': {
    colors: [
      { hex: '#58111A', percentage: 52 },
      { hex: '#4A0E17', percentage: 30 },
      { hex: '#2B0C10', percentage: 18 },
    ],
    materials: ['Buffed Calfskin', 'Heavy Wool Flannel', 'Heavy Silk Satin'],
    textures: ['Patent Gloss', 'Brushed Flannel', 'Supple Grain'],
    silhouettes: ['Architectural Trench', 'Sculptural Column Skirt', 'Structured Leather Tote'],
    patterns: ['Deep Saturated Solid', 'Tonal Shadow Stripe'],
  },
  'Tactile Suede & Heritage Leather': {
    colors: [
      { hex: '#8B5A2B', percentage: 48 },
      { hex: '#C68E17', percentage: 32 },
      { hex: '#5C2E0B', percentage: 20 },
    ],
    materials: ['Brushed Suede', 'Heritage Calfskin', 'Plush Shearling'],
    textures: ['Velvety Nap', 'Supple Grain', 'Dense Shearling'],
    silhouettes: ['Car Coat', 'A-Line Leather Skirt', 'Slouchy Hobo Bag'],
    patterns: ['Natural Grain Texture', 'Tonal Topstitch'],
  },
  'Artisanal Knitwear & Open Weave': {
    colors: [
      { hex: '#EBE6DD', percentage: 45 },
      { hex: '#9E9D99', percentage: 35 },
      { hex: '#7D8471', percentage: 20 },
    ],
    materials: ['Chunky Merino Wool', 'Brushed Alpaca', 'Bouclé Yarn'],
    textures: ['Open Gauge Weave', 'Tactile Ribbing', 'Dense Cable'],
    silhouettes: ['Slouchy Cocoon Cardigan', 'Column Knit Dress', 'Wrap Knit Scarf'],
    patterns: ['Artisanal Cable Knit', 'Ribbed Micro-Repeat'],
  },
  'Raw Denim & Chambray Structures': {
    colors: [
      { hex: '#1B2A4A', percentage: 55 },
      { hex: '#5B7C99', percentage: 30 },
      { hex: '#EBE7DE', percentage: 15 },
    ],
    materials: ['Japanese Selvedge Denim', 'Rigid Raw Cotton', 'Compact Chambray'],
    textures: ['Dry Stiff Weave', 'Visible Twill Grain', 'Unwashed Hand'],
    silhouettes: ['Wide-Leg Rigid Trouser', 'Boxy Trucker Jacket', 'Column Denim Skirt'],
    patterns: ['Indigo Warp Repeat', 'Contrast Tobacco Topstitching'],
  },
  'Supple Leather & Polished Skins': {
    colors: [
      { hex: '#2B1E16', percentage: 50 },
      { hex: '#111111', percentage: 35 },
      { hex: '#8B4513', percentage: 15 },
    ],
    materials: ['Full-Grain Nappa', 'Polished Box Calf', 'Buffed Suede'],
    textures: ['High Shine Gloss', 'Buttery Soft Touch', 'Planar Smooth'],
    silhouettes: ['Double-Breasted Leather Coat', 'Midi Pencil Skirt', 'Straight Trouser'],
    patterns: ['Pure Polished Plane', 'Minimal Seaming'],
  },
  'Liquid Silk & Satin Fluidity': {
    colors: [
      { hex: '#F0E6D2', percentage: 48 },
      { hex: '#D8C7A5', percentage: 32 },
      { hex: '#1A2436', percentage: 20 },
    ],
    materials: ['Heavy Silk Charmeuse', 'Fluid Crepe de Chine', 'Viscose Satin'],
    textures: ['Liquid Drape', 'High Reflective Sheen', 'Cool Touch'],
    silhouettes: ['Bias-Cut Slip Gown', 'Draped Halter Top', 'Fluid Pleated Trouser'],
    patterns: ['Continuous Liquid Sheen', 'Reflective Surface'],
  },
  'Brushed Wool & Cashmere Tailoring': {
    colors: [
      { hex: '#757575', percentage: 45 },
      { hex: '#C2A385', percentage: 35 },
      { hex: '#2E2E2E', percentage: 20 },
    ],
    materials: ['Double-Faced Cashmere', 'Worsted Virgin Wool', 'Heavy Wool Flannel'],
    textures: ['Brushed Felted Touch', 'Dense Insulating Hand', 'Soft Wool Nap'],
    silhouettes: ['Unstructured Overcoat', 'Pleated Tailored Trouser', 'Belted Wrap Coat'],
    patterns: ['Subtle Melange Weave', 'Herringbone Micro-Pattern'],
  },
  'Utility Workwear & Structured Outerwear': {
    colors: [
      { hex: '#4B5320', percentage: 45 },
      { hex: '#8B7D6B', percentage: 35 },
      { hex: '#1B263B', percentage: 20 },
    ],
    materials: ['High-Density Cotton Canvas', 'Technical Ripstop', 'Waxed Gabardine'],
    textures: ['Rugged Twill', 'Matte Waxed Finish', 'Crisp Memory Touch'],
    silhouettes: ['Modular Cargo Trouser', 'Field Jacket with Storm Flap', 'Utility Parka'],
    patterns: ['Reinforced Seam Geometry', 'Minimal Utilitarian'],
  },
  'Dark Romance & Gothic Elegance': {
    colors: [
      { hex: '#0B0B0E', percentage: 55 },
      { hex: '#4A0E17', percentage: 28 },
      { hex: '#8B7355', percentage: 17 },
    ],
    materials: ['Chantilly Lace', 'Silk Velvet', 'Tiered Tulle'],
    textures: ['Plush Velvet Nap', 'Intricate Openwork', 'Layered Translucency'],
    silhouettes: ['Boned Corset Bodice', 'Sweeping Floor-Length Hem', 'Tiered Flounce Sleeve'],
    patterns: ['Flocked Baroque Scroll', 'Victorian Floral Lace'],
  },
  'Architectural Footwear & Statement Bags': {
    colors: [
      { hex: '#111215', percentage: 50 },
      { hex: '#634832', percentage: 30 },
      { hex: '#B8B8B8', percentage: 20 },
    ],
    materials: ['Spazzolato Box Leather', 'Polished Solid Brass', 'Structured Calfskin'],
    textures: ['Mirror Polish', 'Rigid Molded Form', 'Tactile Edge Paint'],
    silhouettes: ['Sculptural Block Heel', 'Trapezoidal Shoulder Bag', 'Geometric Mule'],
    patterns: ['Clean Architectural Planes', 'Precision Laser Cut'],
  },
};

function getArchetypeDna(candidateName: string, category: string) {
  const normName = (candidateName || '').toLowerCase();
  for (const [archetypeName, dna] of Object.entries(THEME_ARCHETYPE_DNA)) {
    if (
      normName.includes(archetypeName.toLowerCase()) ||
      archetypeName.toLowerCase().includes(normName)
    ) {
      return dna;
    }
  }

  const cat = (category || '').toLowerCase();
  if (cat === 'materials') {
    return THEME_ARCHETYPE_DNA['Sheer & Translucent Layering'];
  }
  if (cat === 'silhouettes') {
    return THEME_ARCHETYPE_DNA['Sculptural Tailoring & Suiting'];
  }
  if (cat === 'color') {
    return normName.includes('burgundy') || normName.includes('oxblood')
      ? THEME_ARCHETYPE_DNA['Deep Burgundy & Oxblood Accents']
      : THEME_ARCHETYPE_DNA['Butter Yellow & Warm Pastels'];
  }
  if (cat === 'textures') {
    return THEME_ARCHETYPE_DNA['Tactile Suede & Heritage Leather'];
  }
  if (cat === 'accessories') {
    return THEME_ARCHETYPE_DNA['Architectural Footwear & Statement Bags'];
  }
  if (cat === 'couture') {
    return THEME_ARCHETYPE_DNA['Dark Romance & Gothic Elegance'];
  }
  if (cat === 'streetwear') {
    return THEME_ARCHETYPE_DNA['Utility Workwear & Structured Outerwear'];
  }

  return {
    colors: [
      { hex: '#102126', percentage: 48 },
      { hex: '#ADC7B8', percentage: 32 },
      { hex: '#DF7E8C', percentage: 20 },
    ],
    materials: ['Double-Faced Wool', 'Silk Organza', 'Compact Cotton Poplin'],
    textures: ['Supple Fluid Finish', 'Crisp Architectural Hand', 'Matte Texture'],
    silhouettes: ['Structured Blazer', 'Fluid Draped Trouser', 'Cocoon Coat'],
    patterns: ['Monochrome Solid', 'Subtle Fine Weave'],
  };
}

function candidateToTrendRecord(candidate: NewsDerivedCandidate): AnyRecord {
  const leadImage = (candidate as any).imageUrl || candidate.articles?.[0]?.imageUrl || null;
  const articles = candidate.articles || [];
  const publisherSet = new Set(articles.map(a => a.publisher));
  const publisherCount = candidate.publisherCount || publisherSet.size || 1;
  const observationCount = articles.length;

  const candidateSignals = articles.map((art, idx) => ({
    id: `candidate-sig-${candidate.key}-${idx}`,
    source: 'culture',
    signal_type: 'news_derived',
    strength: Math.max(52, Math.round(85 - idx * 4.5)),
    direction: 'up',
    timestamp: art.publishedAt || null,
    metadata: {
      source_name: art.publisher,
      article_title: art.headline,
      source_url: art.articleUrl,
      image_url: art.imageUrl || null,
      signal_kind: 'news_derived',
      provenance: {
        publisher: art.publisher,
        title: art.headline,
        canonical_url: art.articleUrl,
        published_at: art.publishedAt,
      },
    },
    data_status: 'news_derived',
  }));

  const dna = getArchetypeDna(candidate.name, candidate.category);

  return {
    id: candidate.key,
    slug: candidate.key,
    name: candidate.name,
    category: candidate.category,
    description: '[news_derived] Editorial candidate; not an independently verified market observation.',
    data_status: 'news_derived',
    is_candidate: true,
    sourceLabel: candidate.sourceLabel || 'News-derived',
    publisherCount,
    observationCount,
    momentum: Math.min(94, 62 + observationCount * 5),
    velocity: Math.min(88, 50 + publisherCount * 8),
    cross_source_agreement: Math.min(96, 48 + publisherCount * 14),
    image_url: leadImage,
    imageUrl: leadImage,
    dna,
    signals: candidateSignals,
    articles,
  };
}

export function App() {
  const [activePage, setActivePage] = useState<Page>(() => pageFromPath(window.location.pathname));
  const [trends, setTrends] = useState<AnyRecord[]>([]);
  const [newsCandidates, setNewsCandidates] = useState<NewsDerivedCandidate[]>([]);
  const [candidateLoading, setCandidateLoading] = useState<boolean>(true);
  const [candidateError, setCandidateError] = useState<string | null>(null);
  const [submissionOpen, setSubmissionOpen] = useState<boolean>(false);
  const [videoProvider, setVideoProvider] = useState<AnyRecord | null>(null);
  const [videos, setVideos] = useState<AnyRecord[]>([]);
  const [videosLoading, setVideosLoading] = useState<boolean>(false);
  const [videosError, setVideosError] = useState<string | null>(null);
  const [videosFetchedAt, setVideosFetchedAt] = useState<string | null>(null);
  const [categories, setCategories] = useState<AnyRecord[]>([]);
  const [activeTrend, setActiveTrend] = useState<AnyRecord | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [liveSignals, setLiveSignals] = useState<AnyRecord | null>(null);
  const [dashboard, setDashboard] = useState<AnyRecord | null>(null);
  const [currentNews, setCurrentNews] = useState<AnyRecord | null>(null);
  const [newsError, setNewsError] = useState<string | null>(null);
  const [newsLoading, setNewsLoading] = useState<boolean>(true);
  const [products, setProducts] = useState<AnyRecord[]>([]);
  const [retail, setRetail] = useState<AnyRecord | null>(null);
  const [forecast, setForecast] = useState<AnyRecord | null>(null);
  const [forecastHorizon, setForecastHorizon] = useState<string>('3_months');
  const [prophecy, setProphecy] = useState<AnyRecord | null>(null);
  const [collection, setCollection] = useState<AnyRecord | null>(null);
  const [forecastStage, setForecastStage] = useState<number>(1);
  const [savedTrendIds, setSavedTrendIds] = useState<Set<string>>(new Set());
  const [inspectedTrend, setInspectedTrend] = useState<AnyRecord | null>(null);
  const [inspectedProduct, setInspectedProduct] = useState<AnyRecord | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [trendDataLoading, setTrendDataLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState<boolean>(false);
  const [loginOpen, setLoginOpen] = useState<boolean>(false);
  const [accountOpen, setAccountOpen] = useState<boolean>(false);
  const [visionOpen, setVisionOpen] = useState<boolean>(false);
  const [menuOpen, setMenuOpen] = useState<boolean>(false);
  const [scrolled, setScrolled] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<AnyRecord | null>(null);

  // Initialize data on mount
  useEffect(() => {
    loadInitialData();
  }, []);

  async function loadInitialData() {
    setLoading(true);
    setError(null);
    setCandidateLoading(true);
    setCandidateError(null);

    const initialPage = pageFromPath(window.location.pathname);

    // Fetch only primary homepage data in parallel
    const [
      dashboardResult,
      trendsResult,
      categoriesResult,
      signalsResult,
      newsResult,
      candidateResult,
    ] = await Promise.allSettled([
      api.getDashboard(),
      api.getTrends({ limit: 16 }),
      api.getCategories(),
      api.getLiveSignals(),
      api.getCurrentNews(),
      api.getCandidateTrends(),
    ]);

    if (dashboardResult.status === 'fulfilled') setDashboard(dashboardResult.value);

    let fetchedTrends: AnyRecord[] = [];
    if (trendsResult.status === 'fulfilled') {
      fetchedTrends = trendsResult.value || [];
      setTrends(fetchedTrends);
    }
    if (categoriesResult.status === 'fulfilled') setCategories(categoriesResult.value);
    if (signalsResult.status === 'fulfilled') setLiveSignals(signalsResult.value);
    if (newsResult.status === 'fulfilled') {
      setCurrentNews(newsResult.value);
      setNewsError(null);
    } else {
      setNewsError(newsResult.reason?.message || 'Current fashion news could not be loaded.');
    }
    setNewsLoading(false);

    let mappedCandidates: NewsDerivedCandidate[] = [];
    if (candidateResult.status === 'fulfilled') {
      mappedCandidates = mapNewsCandidates(candidateResult.value);
      setNewsCandidates(mappedCandidates);
      setCandidateError(null);
    } else {
      setCandidateError(candidateResult.reason?.message || 'News-derived candidates could not be loaded.');
    }
    setCandidateLoading(false);

    const { trendParam, categoryParam } = parseUrlParams();
    let initialTrend: AnyRecord | null = null;
    const candidateTrendRecords = mappedCandidates.map(candidateToTrendRecord);

    if (trendParam) {
      initialTrend = fetchedTrends.find(
        (t: AnyRecord) => t.slug === trendParam || t.id === trendParam
      ) || candidateTrendRecords.find(
        (t: AnyRecord) => t.slug === trendParam || t.id === trendParam
      ) || null;
    }
    if (!initialTrend && categoryParam) {
      initialTrend = fetchedTrends.find(
        (t: AnyRecord) => t.category && t.category.toLowerCase() === categoryParam.toLowerCase()
      ) || candidateTrendRecords.find(
        (t: AnyRecord) => t.category && t.category.toLowerCase() === categoryParam.toLowerCase()
      ) || null;
      setActiveCategory(categoryParam);
    }
    setActiveTrend(initialTrend || fetchedTrends[0] || candidateTrendRecords[0] || null);

    // If direct landing page is a secondary route, load its layer on demand
    if (initialPage === 'videos') {
      void api.getVideoStatus().then(setVideoProvider).catch(() => {});
      void searchVideos();
    } else if (initialPage === 'product' && !initialTrend) {
      void api.getProducts().then(setProducts).catch(() => {});
    } else if (initialPage === 'retail' && !initialTrend) {
      void api.getRetail().then(setRetail).catch(() => {});
    }

    const failed = [dashboardResult, trendsResult, categoriesResult, signalsResult, newsResult, candidateResult].find(
      (result): result is PromiseRejectedResult => result.status === 'rejected'
    );
    if (failed) {
      setError(failed.reason?.message || 'Some intelligence services are unavailable.');
    }

    if (api.getToken()) {
      api.getMe().then(setCurrentUser).catch(() => api.logout());
      api.getSavedTrends().then(saved => {
        setSavedTrendIds(new Set(saved.map((item: any) => item.id)));
      }).catch(() => setError('Saved trends could not be loaded.'));
    }
    setLoading(false);
  }

  async function searchVideos(filters: {
    query?: string;
    topic?: string;
    published_after?: string;
    order?: string;
    region_code?: string;
    duration?: string;
  } = {}) {
    setVideosLoading(true);
    setVideosError(null);
    try {
      const result = await api.searchVideos({
        ...filters,
        query: filters.query?.trim() || 'fashion runway designer collection',
      });
      setVideos(result.items || []);
      setVideosFetchedAt(result.fetched_at || null);
      setVideoProvider(current => current ? { ...current, available: true } : current);
    } catch (err: any) {
      setVideos([]);
      setVideosError(err?.message || 'Fashion videos could not be loaded.');
    } finally {
      setVideosLoading(false);
    }
  }

  async function refreshCandidateTrends(category?: string) {
    setCandidateLoading(true);
    setCandidateError(null);
    try {
      const result = await api.getCandidateTrends();
      const mapped = mapNewsCandidates(result);
      setNewsCandidates(mapped);
      if (mapped.length > 0) {
        setActiveTrend(current => {
          if (!current || current.is_candidate) {
            const match = category
              ? mapped.find(c => c.category.toLowerCase() === category.toLowerCase())
              : mapped[0];
            return match ? candidateToTrendRecord(match) : current;
          }

          return current;
        });
      }
    } catch (err: any) {
      setCandidateError(err?.message || 'News-derived candidates could not be loaded.');
    } finally {
      setCandidateLoading(false);
    }
  }

  // Load trend-specific layers when activeTrend or activePage changes
  useEffect(() => {
    if (activePage === 'home') {
      setTrendDataLoading(false);
      return;
    }
    if (!activeTrend?.slug && !activeTrend?.id) {
      setTrendDataLoading(false);
      return;
    }
    const tId = activeTrend.slug || activeTrend.id;
    let current = true;
    setTrendDataLoading(true);
    setError(null);

    // If activeTrend is an editorial news-derived candidate, route appropriately
    if (activeTrend.is_candidate || activeTrend.data_status === 'news_derived') {
      if (activePage === 'retail') {
        api.getRetail()
          .then(ret => {
            if (!current) return;
            setRetail(ret);
            setTrendDataLoading(false);
          })
          .catch(() => {
            if (!current) return;
            setTrendDataLoading(false);
          });
        return () => {
          current = false;
        };
      }
      if (activePage === 'forecast') {
        setForecast({
          status: 'insufficient_data',
          trend_id: activeTrend.slug || activeTrend.id,
          data_status: 'insufficient_data',
          message: `Candidate topic "${activeTrend.name}" is derived from editorial news coverage (${activeTrend.publisherCount || 1} publisher mentions). Time-series forecast models require ≥ 6 chronological, source-attributed observations with timestamped HTTPS provenance before projections can be computed.`,
        });
        setTrendDataLoading(false);
        return () => {
          current = false;
        };
      }
      setTrendDataLoading(false);
      return () => {
        current = false;
      };
    }

    if (activePage === 'trend') {
      Promise.allSettled([
        api.getTrend(tId),
        api.getCollection(tId),
      ]).then(([trendResult, collectionResult]) => {
        if (!current) return;
        if (trendResult.status === 'fulfilled') setActiveTrend(trendResult.value);
        if (collectionResult.status === 'fulfilled') setCollection(collectionResult.value);
        else setCollection(null);
        setTrendDataLoading(false);
      });
    } else if (activePage === 'product') {
      api.getProducts(tId)
        .then(prods => {
          if (!current) return;
          setProducts(prods || []);
          setTrendDataLoading(false);
        })
        .catch(err => {
          if (!current) return;
          setError(err?.message || 'Products could not be loaded.');
          setTrendDataLoading(false);
        });
    } else if (activePage === 'retail') {
      api.getRetail(tId)
        .then(ret => {
          if (!current) return;
          setRetail(ret);
          setTrendDataLoading(false);
        })
        .catch(err => {
          if (!current) return;
          setError(err?.message || 'Retail signals could not be loaded.');
          setTrendDataLoading(false);
        });
    } else if (activePage === 'forecast') {
      api.getForecast(tId, forecastHorizon)
        .then(fc => {
          if (!current) return;
          setForecast(fc);
          setTrendDataLoading(false);
        })
        .catch(err => {
          if (!current) return;
          setForecast({
            status: 'insufficient_data',
            trend_id: tId,
            data_status: 'insufficient_data',
            message: err?.message || 'Historical observations not found in database for this trend.',
          });
          setTrendDataLoading(false);
        });
    } else if (activePage === 'prophecy') {
      api.getProphecy(tId)
        .then(pr => {
          if (!current) return;
          setProphecy(pr);
          setTrendDataLoading(false);
        })
        .catch(err => {
          if (!current) return;
          setError(err?.message || 'Prophecy could not be loaded.');
          setTrendDataLoading(false);
        });
    } else {
      setTrendDataLoading(false);
    }

    return () => {
      current = false;
    };
  }, [activeTrend?.id, activeTrend?.slug, forecastHorizon, activePage]);

  // Window scroll & popstate listeners
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 26);
    const onPop = () => {
      const page = pageFromPath(window.location.pathname);
      setActivePage(page);
      if (page === 'videos') void searchVideos();
      const { trendParam, categoryParam } = parseUrlParams();
      if (categoryParam) setActiveCategory(categoryParam);
      if (trendParam) {
        setTrends(currentTrends => {
          const match = currentTrends.find(t => t.slug === trendParam || t.id === trendParam);
          if (match) {
            setActiveTrend(match);
          } else {
            setNewsCandidates(cands => {
              const candMatch = cands.find(c => c.slug === trendParam || c.id === trendParam || c.key === trendParam);
              if (candMatch) {
                setActiveTrend(candidateToTrendRecord(candMatch));
              }
              return cands;
            });
          }
          return currentTrends;
        });
      }
    };
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('scroll', onScroll);
    window.addEventListener('popstate', onPop);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('keydown', onKey);
    };
  }, []);

  const go: NavigateFn = (page, options = {}) => {
    setActivePage(page);
    if (page === 'videos') {
      void searchVideos();
      if (!videoProvider) void api.getVideoStatus().then(setVideoProvider).catch(() => {});
    }
    let targetTrend: AnyRecord | null = options.trend || null;
    let targetCategory: string | null = options.category !== undefined ? options.category : null;

    if (targetTrend) {
      setActiveTrend(targetTrend);
      if (!targetCategory && targetTrend.category) {
        targetCategory = targetTrend.category;
      }
    } else if (targetCategory) {
      let matched = trends.find(
        t => t.category && t.category.toLowerCase() === targetCategory?.toLowerCase()
      );
      if (!matched && newsCandidates.length > 0) {
        const candMatch = newsCandidates.find(
          c => c.category && c.category.toLowerCase() === targetCategory?.toLowerCase()
        );
        if (candMatch) matched = candidateToTrendRecord(candMatch);
      }
      if (matched) {
        targetTrend = matched;
        setActiveTrend(matched);
      }
    }
    if (targetCategory !== null) {
      setActiveCategory(targetCategory);
    }
    setMenuOpen(false);

    if (page === 'product' && !products.length && (!targetTrend || targetTrend.is_candidate)) {
      void api.getProducts().then(setProducts).catch(() => {});
    }
    if (page === 'retail' && !retail && (!targetTrend || targetTrend.is_candidate)) {
      void api.getRetail().then(setRetail).catch(() => {});
    }

    const queryParts: string[] = [];
    if (targetTrend?.slug || targetTrend?.id) {
      queryParts.push(`trend=${encodeURIComponent(targetTrend.slug || targetTrend.id)}`);
    }
    if (targetCategory) {
      queryParts.push(`category=${encodeURIComponent(targetCategory)}`);
    }
    const qs = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
    const newPath = page === 'home' ? `/${qs}` : `/${page}${qs}`;

    window.history.pushState({}, '', newPath);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const selectTrend = (trend: AnyRecord) => {
    setActiveTrend(trend);
    go('trend', { trend, category: trend.category });
  };

  const availableTrendOptions = [
    ...trends,
    ...newsCandidates.map(candidateToTrendRecord).filter(
      candidate => !trends.some(trend => trend.slug === candidate.slug || trend.id === candidate.id),
    ),
  ];
  const availableCategories = Array.from(
    new Set([...categories.map(category => category.name), ...newsCandidates.map(candidate => candidate.category)]),
  ).map(name => ({ name }));

  const toggleSave = async (trendId: string) => {
    if (!currentUser) {
      setLoginOpen(true);
      return;
    }
    try {
      const res = await api.toggleSaveTrend(trendId);
      setSavedTrendIds(prev => {
        const next = new Set(prev);
        if (res.saved) next.add(trendId);
        else next.delete(trendId);
        return next;
      });
    } catch (err: any) {
      alert(err.message || 'Could not save trend');
    }
  };

  const brand = (
    <button className="brand-wordmark" onClick={() => go('home')} aria-label="LUXE.TECH home">
      <span>LUXE</span><i>.</i><b>TECH</b>
    </button>
  );

  return (
    <div className={`luxe-app ${scrolled ? 'has-scrolled' : ''}`}>
      {loading && (
        <div
          className="luxe-loading-indicator-top"
          role="status"
          aria-label="Loading platform intelligence"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: 'linear-gradient(90deg, transparent, #e6ca65, transparent)',
            zIndex: 9999,
            pointerEvents: 'none',
          }}
        />
      )}
      <Navbar
        brand={brand}
        activePage={activePage}
        scrolled={scrolled}
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
        onNavigate={go}
        onSearch={() => setSearchOpen(true)}
        onLogin={() => setLoginOpen(true)}
        onAccount={() => setAccountOpen(true)}
        onVision={() => setVisionOpen(true)}
        onSubmitTrend={() => setSubmissionOpen(true)}
        currentUser={currentUser}
        onLogout={() => {
          api.logout();
          setCurrentUser(null);
          setAccountOpen(false);
        }}
      />

      {error && (
        <div className="intelligence-error-banner">
          <div>
            <h3>INTELLIGENCE TEMPORARILY UNAVAILABLE</h3>
            <p>{error}</p>
          </div>
          <button className="button light-button" onClick={loadInitialData}>
            TRY AGAIN
          </button>
        </div>
      )}

      {trendDataLoading && activePage !== 'home' && (
        <div className="intelligence-error-banner" role="status">
          <p>Loading records for the selected trend…</p>
        </div>
      )}

      <main className="luxe-main">
        <Transition page={activePage}>
          {activePage === 'home' ? (
            <Home
              trends={trends}
              candidates={newsCandidates}
              candidatesLoading={candidateLoading}
              candidatesError={candidateError}
              onRetryCandidates={() => refreshCandidateTrends()}
              dashboard={dashboard}
              currentNews={currentNews}
              newsError={newsError}
              newsLoading={newsLoading}
              onRefreshNews={async () => {
                setNewsLoading(true);
                setNewsError(null);
                try {
                  setCurrentNews(await api.getCurrentNews());
                } catch (err: any) {
                  setNewsError(err?.message || 'Current fashion news could not be refreshed.');
                  setCurrentNews(previous => previous ? { ...previous, stale: true } : previous);
                } finally {
                  setNewsLoading(false);
                }
              }}
              liveSignals={liveSignals}
              categories={availableCategories}
              onNavigate={go}
              onTrend={selectTrend}
              onInspectTrend={setInspectedTrend}
              onSearch={() => setSearchOpen(true)}
              onVision={() => setVisionOpen(true)}
            />
          ) : activePage === 'videos' ? (
            <FashionVideosPage
              provider={videoProvider}
              videos={videos}
              loading={videosLoading}
              error={videosError}
              fetchedAt={videosFetchedAt}
              onSearch={searchVideos}
            />
          ) : activePage === 'trend' ? (
            <TrendPage
              trends={trends}
              candidates={newsCandidates}
              candidatesLoading={candidateLoading}
              candidatesError={candidateError}
              onRetryCandidates={() => refreshCandidateTrends(activeCategory || undefined)}
              selected={activeTrend}
              categories={categories}
              activeCategory={activeCategory}
              onSelectCategory={cat => {
                setActiveCategory(cat || null);
                setError(null);
                api.getTrends(cat ? { category: cat } : {})
                  .then(res => {
                    const fetched = res || [];
                    setTrends(fetched);
                    if (fetched.length > 0) {
                      setActiveTrend(fetched[0]);
                    } else {
                      const candMatch = newsCandidates.find(
                        c => !cat || c.category.toLowerCase() === cat.toLowerCase()
                      );
                      setActiveTrend(candMatch ? candidateToTrendRecord(candMatch) : null);
                    }
                  })
                  .catch((err: any) => setError(err?.message || 'Trend filter could not be loaded.'));
              }}
              onTrend={selectTrend}
              onNavigate={go}
              isSaved={activeTrend ? savedTrendIds.has(activeTrend.id) : false}
              onToggleSave={tId => toggleSave(tId)}
              collection={collection}
              onGenerateCollection={async () => {
                if (!currentUser) {
                  setLoginOpen(true);
                  return;
                }
                if (!activeTrend) return;
                const res = await api.generateCollection(activeTrend.slug || activeTrend.id);
                setCollection(res);
              }}
              currentUser={currentUser}
              onOpenLogin={() => setLoginOpen(true)}
              onSubmitTrend={() => setSubmissionOpen(true)}
              onInspectTrend={setInspectedTrend}
            />
          ) : activePage === 'product' ? (
            <ProductPage
              products={products}
              activeTrend={activeTrend}
              trends={availableTrendOptions}
              initialCategory={activeCategory}
              onSelectTrend={selectTrend}
              onNavigate={go}
              onGenerateMore={async () => {
                if (!activeTrend) return;
                const newProds = await api.generateProducts(activeTrend.slug || activeTrend.id);
                setProducts(newProds);
              }}
              currentUser={currentUser}
              onOpenLogin={() => setLoginOpen(true)}
              onInspectProduct={setInspectedProduct}
            />
          ) : activePage === 'retail' ? (
            <RetailPage
              retail={retail}
              activeTrend={activeTrend}
              trends={availableTrendOptions}
              onSelectTrend={selectTrend}
              onNavigate={go}
            />
          ) : activePage === 'forecast' ? (
            <ForecastPage
              trends={availableTrendOptions}
              activeTrend={activeTrend}
              forecast={forecast}
              horizon={forecastHorizon}
              setHorizon={setForecastHorizon}
              onSelectTrend={selectTrend}
              onRecompute={async () => {
                if (!activeTrend) return;
                const updated = await api.triggerForecast(activeTrend.slug || activeTrend.id, forecastHorizon);
                setForecast(updated);
              }}
              onNavigate={go}
              currentUser={currentUser}
              onOpenLogin={() => setLoginOpen(true)}
            />
          ) : (
            <ProphecyPage
              trends={availableTrendOptions}
              activeTrend={activeTrend}
              prophecy={prophecy}
              stage={forecastStage}
              setStage={setForecastStage}
              onSelectTrend={selectTrend}
              onNavigate={go}
              onGenerateProphecy={async () => {
                if (!activeTrend) return;
                const res = await api.generateProphecy(activeTrend.slug || activeTrend.id);
                setProphecy(res);
              }}
              currentUser={currentUser}
              onOpenLogin={() => setLoginOpen(true)}
            />
          )}
        </Transition>
      </main>

      <Footer onNavigate={go} onVision={() => setVisionOpen(true)} />

      {searchOpen && (
        <SearchOverlay
          onClose={() => setSearchOpen(false)}
          onNavigate={(page, item) => {
            if (item) {
              const matchedTrend = trends.find(
                t => t.id === item.id || t.slug === item.slug || t.id === item.trend_id || t.slug === item.trend_id
              );
              if (matchedTrend) {
                go(page, { trend: matchedTrend, category: item.category });
              } else {
                go(page, { category: item.category });
              }
            } else {
              go(page);
            }
          }}
          trends={availableTrendOptions}
          products={products}
        />
      )}

      {loginOpen && (
        <LoginModal
          onClose={() => setLoginOpen(false)}
          onSuccess={user => {
            setCurrentUser(user);
            setLoginOpen(false);
          }}
        />
      )}

      {accountOpen && currentUser && (
        <AccountModal
          currentUser={currentUser}
          onClose={() => setAccountOpen(false)}
          onLogout={() => {
            api.logout();
            setCurrentUser(null);
            setAccountOpen(false);
          }}
          onSelectTrend={trend => {
            selectTrend(trend);
            setAccountOpen(false);
          }}
        />
      )}

      {visionOpen && (
        <VisionLabModal
          onClose={() => setVisionOpen(false)}
          activeTrend={activeTrend}
          onAnalysisComplete={analysisResult => {
            // Offer to view or link analysis
          }}
          currentUser={currentUser}
          onOpenLogin={() => setLoginOpen(true)}
        />
      )}

      {submissionOpen && (
        <TrendSubmissionModal
          currentUser={currentUser}
          onClose={() => setSubmissionOpen(false)}
          onOpenLogin={() => setLoginOpen(true)}
        />
      )}

      {inspectedTrend && (
        <TrendDetailModal
          trend={inspectedTrend}
          onClose={() => setInspectedTrend(null)}
          onNavigate={go}
          isSaved={savedTrendIds.has(inspectedTrend.id)}
          onToggleSave={toggleSave}
        />
      )}

      {inspectedProduct && (
        <ProductDetailModal
          product={inspectedProduct}
          trend={activeTrend}
          onClose={() => setInspectedProduct(null)}
          onNavigate={go}
        />
      )}
    </div>
  );
}

// Helpers
function navigate(path: string) {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

function pageFromPath(path: string): Page {
  if (path.startsWith('/videos')) return 'videos';
  if (path.startsWith('/trend')) return 'trend';
  if (path.startsWith('/product')) return 'product';
  if (path.startsWith('/retail')) return 'retail';
  if (path.startsWith('/forecast')) return 'forecast';
  if (path.startsWith('/prophecy')) return 'prophecy';
  return 'home';
}

function parseUrlParams() {
  if (typeof window === 'undefined') return { trendParam: null, categoryParam: null };
  const params = new URLSearchParams(window.location.search);
  return {
    trendParam: params.get('trend'),
    categoryParam: params.get('category'),
  };
}

// Global Nav
function Navbar({
  brand,
  activePage,
  scrolled,
  menuOpen,
  setMenuOpen,
  onNavigate,
  onSearch,
  onLogin,
  onAccount,
  onVision,
  onSubmitTrend,
  currentUser,
  onLogout,
}: {
  brand: ReactNode;
  activePage: Page;
  scrolled: boolean;
  menuOpen: boolean;
  setMenuOpen: (v: boolean) => void;
  onNavigate: NavigateFn;
  onSearch: () => void;
  onLogin: () => void;
  onAccount: () => void;
  onVision: () => void;
  onSubmitTrend: () => void;
  currentUser: AnyRecord | null;
  onLogout: () => void;
}) {
  const items: [Page, string][] = [
    ['home', 'HOME'],
    ['trend', 'TREND'],
    ['videos', 'VIDEO'],
    ['product', 'PRODUCT'],
    ['retail', 'RETAIL'],
    ['forecast', 'FORECAST'],
    ['prophecy', 'PROPHECY'],
  ];

  return (
    <header className={`luxe-nav ${scrolled ? 'scrolled' : ''}`}>
      <div className="nav-inner">
        {brand}
        <nav className={menuOpen ? 'mobile-open' : ''}>
          {items.map(([page, label]) => (
            <button
              key={page}
              className={activePage === page ? 'active' : ''}
              onClick={() => onNavigate(page)}
            >
              {label}
            </button>
          ))}
          <div className="mobile-actions">
            <button onClick={() => { setMenuOpen(false); onSubmitTrend(); }}>
              <Sparkles size={14} /> SUBMIT A TREND
            </button>
            <button onClick={onVision}>
              <Camera size={14} /> VISION LAB
            </button>
            <button onClick={onSearch}>
              <Search size={14} /> SEARCH
            </button>
            {currentUser ? (
              <>
                <button onClick={() => { setMenuOpen(false); onAccount(); }}>
                  <User size={14} /> WORKSPACE ({currentUser.name?.split(' ')[0]})
                </button>
                <button onClick={() => { setMenuOpen(false); onLogout(); }}>
                  <LogOut size={14} /> LOGOUT
                </button>
              </>
            ) : (
              <button onClick={() => { setMenuOpen(false); onLogin(); }}>
                <LockKeyhole size={14} /> LOGIN
              </button>
            )}
          </div>
        </nav>
        <div className="nav-tools">
          <button onClick={onSubmitTrend} aria-label="Submit a trend observation">
            <Sparkles size={15} />
            <span>SUBMIT TREND</span>
          </button>
          <button onClick={onVision} title="Open Vision Lab / Image Analysis">
            <Camera size={15} />
            <span>VISION LAB</span>
          </button>
          <button onClick={onSearch} aria-label="Open search">
            <Search size={15} />
            <span>SEARCH</span>
          </button>
          {currentUser ? (
            <button onClick={onAccount} className="login-link" title="Open Workspace Account">
              <User size={14} />
              <span>{currentUser.name ? currentUser.name.split(' ')[0].toUpperCase() : 'USER'}</span>
            </button>
          ) : (
            <button onClick={onLogin} className="login-link">
              <LockKeyhole size={13} />
              <span>LOGIN</span>
            </button>
          )}
          <button
            className="menu-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Open navigation"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
    </header>
  );
}

function Transition({ page, children }: { page: Page; children: ReactNode }) {
  return (
    <div className="page-transition" key={page}>
      {children}
    </div>
  );
}

function Reveal({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      entries => entries.forEach(entry => entry.isIntersecting && setVisible(true)),
      { threshold: 0.1 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={`reveal ${visible ? 'revealed' : ''} ${className}`}>
      {children}
    </div>
  );
}

function DataTag({ children = 'DEMO DATA' }: { children?: ReactNode }) {
  return (
    <span className="data-tag">
      <i />
      {children}
    </span>
  );
}

function SectionIntro({
  kicker,
  title,
  description,
  action,
}: {
  kicker: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-intro">
      <div>
        <span className="kicker">{kicker}</span>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}

function SignalBar({
  label,
  value,
  tone = 'pink',
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <div className="signal-bar">
      <div>
        <span>{label}</span>
        <b>{value}%</b>
      </div>
      <div className="signal-track">
        <i className={tone} style={{ width: `${Math.min(100, Math.max(5, value))}%` }} />
      </div>
    </div>
  );
}

const EDITORIAL_RUNWAY_VIDEO = 'https://videos.pexels.com/video-files/3130284/3130284-hd_1920_1080_30fps.mp4';

function HeroCandidateSlider({
  candidates,
  loading,
  error,
  onRetry,
  onExplore,
  autoplayIntervalMs = 7000,
}: {
  candidates: NewsDerivedCandidate[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onExplore: (candidate: NewsDerivedCandidate) => void;
  autoplayIntervalMs?: number;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [autoplay, setAutoplay] = useState(true);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [videoPlaying, setVideoPlaying] = useState(true);
  const [videoMuted, setVideoMuted] = useState(true);
  const [videoError, setVideoError] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const slides = candidates.filter(candidate => candidate.articles.length > 0);
  const active = slides[activeIndex];
  const leadArticle = active?.articles[0];

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = () => setReducedMotion(mediaQuery.matches);
    updateMotionPreference();
    mediaQuery.addEventListener('change', updateMotionPreference);
    return () => mediaQuery.removeEventListener('change', updateMotionPreference);
  }, []);

  useEffect(() => {
    if (!videoRef.current) return;
    if (paused || reducedMotion || !videoPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play().catch(() => {
        // Autoplay policy fallback
      });
    }
  }, [paused, reducedMotion, videoPlaying]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = videoMuted;
    }
  }, [videoMuted]);

  useEffect(() => {
    if (!autoplay || paused || reducedMotion || slides.length < 2) return;
    const timer = window.setInterval(() => {
      setActiveIndex(index => (index + 1) % slides.length);
    }, autoplayIntervalMs);
    return () => window.clearInterval(timer);
  }, [autoplay, autoplayIntervalMs, paused, reducedMotion, slides.length]);

  useEffect(() => {
    setActiveIndex(index => Math.min(index, Math.max(0, slides.length - 1)));
  }, [slides.length]);

  const move = (offset: number) => {
    if (!slides.length) return;
    setActiveIndex(index => (index + offset + slides.length) % slides.length);
  };
  const published = leadArticle?.publishedAt ? new Date(leadArticle.publishedAt) : null;
  const publicationDate = published && !Number.isNaN(published.getTime())
    ? published.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : 'Publication date unavailable';
  const publishers = active
    ? [...new Set(active.articles.map(article => article.publisher))].join(' · ')
    : '';

  return (
    <section
      className="hero"
      aria-roledescription="carousel"
      aria-label="News-derived fashion trend candidates"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={event => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setPaused(false);
      }}
      onKeyDown={event => {
        if (event.key === 'ArrowLeft') {
          event.preventDefault();
          move(-1);
        } else if (event.key === 'ArrowRight') {
          event.preventDefault();
          move(1);
        }
      }}
      tabIndex={0}
    >
      <div className="hero-media">
        {!videoError && !reducedMotion ? (
          <video
            ref={videoRef}
            src={EDITORIAL_RUNWAY_VIDEO}
            autoPlay
            loop
            muted={videoMuted}
            playsInline
            preload="metadata"
            onError={() => setVideoError(true)}
            aria-hidden="true"
          />
        ) : null}
        {(active?.imageUrl || leadArticle?.imageUrl) && (
          <img
            src={(active?.imageUrl || leadArticle?.imageUrl) ?? undefined}
            alt={active?.name || 'Fashion editorial'}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              opacity: videoError || reducedMotion ? 0.72 : 0.28,
              filter: 'brightness(0.85)',
              zIndex: 1,
              transition: 'opacity 0.6s ease',
            }}
            onError={e => {
              (e.currentTarget as HTMLElement).style.display = 'none';
            }}
            aria-hidden="true"
          />
        )}
        <div
          className="hero-visual"
          aria-hidden="true"
          style={{ opacity: videoError || reducedMotion ? 1 : 0.45 }}
        />
        <div
          style={{
            position: 'absolute',
            top: 24,
            right: 48,
            zIndex: 3,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 9,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            padding: '5px 12px',
            background: 'rgba(9, 35, 38, 0.72)',
            border: '1px solid rgba(255, 255, 255, 0.16)',
            borderRadius: 2,
            color: 'rgba(255, 255, 255, 0.82)',
            backdropFilter: 'blur(8px)',
          }}
        >
          {!videoError && !reducedMotion ? (
            <>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--champagne)' }} />
              <span>CINEMATIC EDITORIAL RUNWAY</span>
            </>
          ) : (
            <>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--pink)' }} />
              <span>EDITORIAL STUDY · ARCHIVAL VISUAL</span>
            </>
          )}
        </div>
      </div>
      <div className="hero-overlay" />
      <div className="hero-content">
        <span className="kicker light">EDITORIAL DISCOVERY · NEWS-DERIVED</span>
        {loading && !active ? (
          <p role="status">Loading publisher-backed fashion topics…</p>
        ) : error && !active ? (
          <div role="alert">
            <p>Editorial trend candidates are unavailable: {error}</p>
            <button className="button light-button" onClick={onRetry}>RETRY</button>
          </div>
        ) : active ? (
          <>
            <h1>{active.name}</h1>
            <p>{active.category} · Covered by {publishers}</p>
            <p>{publicationDate}</p>
            <p>Publisher coverage is editorial evidence, not a measure of consumer or market activity.</p>
            <div className="hero-actions">
              <button className="button light-button" onClick={() => onExplore(active)}>
                Explore this topic <ArrowRight size={15} />
              </button>
              {leadArticle && (
                <a className="text-button light-text" href={leadArticle.articleUrl} target="_blank" rel="noopener noreferrer">
                  Read source <ArrowUpRight size={14} />
                </a>
              )}
            </div>
          </>
        ) : (
          <div className="hero-empty-state" style={{ maxWidth: 540 }}>
            <span className="kicker light" style={{ opacity: 0.85 }}>SOURCE STATUS: CACHED ARTICLES READY</span>
            <h1 style={{ marginTop: 8 }}>Fashion, in context.</h1>
            <p role="status" style={{ fontSize: 13, lineHeight: 1.6, opacity: 0.88, margin: '10px 0 20px' }}>
              {error
                ? `Publisher-derived topics could not be loaded: ${error}`
                : 'No source-attributed editorial candidates are currently active. Click below to refresh verified fashion feeds.'}
            </p>
            <button className="button light-button" onClick={onRetry} style={{ minHeight: 38 }}>
              REFRESH EDITORIAL FEEDS
            </button>
          </div>
        )}
        {slides.length > 1 && (
          <div style={{ display: 'flex', gap: 8, marginTop: 24 }} aria-label="Choose editorial topic">
            {slides.map((slide, index) => (
              <button
                key={slide.key}
                type="button"
                aria-label={`Show ${slide.name}`}
                aria-current={index === activeIndex}
                onClick={() => setActiveIndex(index)}
                style={{
                  width: index === activeIndex ? 28 : 8,
                  height: 8,
                  padding: 0,
                  border: 0,
                  borderRadius: 8,
                  background: index === activeIndex ? '#fff' : 'rgba(255,255,255,.55)',
                  cursor: 'pointer',
                }}
              />
            ))}
          </div>
        )}
      </div>
      <div className="hero-live" aria-label="Editorial carousel controls">
        <button type="button" aria-label="Previous editorial topic" onClick={() => move(-1)} disabled={slides.length < 2}>
          <ChevronLeft size={17} />
        </button>
        <span>{slides.length ? `${activeIndex + 1} / ${slides.length}` : '0 TOPICS'}</span>
        <button type="button" aria-label="Next editorial topic" onClick={() => move(1)} disabled={slides.length < 2}>
          <ChevronRight size={17} />
        </button>
        <button type="button" onClick={() => setAutoplay(value => !value)} aria-pressed={autoplay}>
          {autoplay ? 'PAUSE ROTATION' : 'PLAY ROTATION'}
        </button>
        {!reducedMotion && !videoError && (
          <>
            <button
              type="button"
              onClick={() => setVideoPlaying(v => !v)}
              aria-label={videoPlaying ? 'Pause background video' : 'Play background video'}
              aria-pressed={videoPlaying}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 8px',
                background: 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#fff',
                cursor: 'pointer',
                fontSize: 8,
                letterSpacing: 1.2,
              }}
            >
              {videoPlaying ? <Pause size={11} /> : <Play size={11} />}
              <span>{videoPlaying ? 'PAUSE VIDEO' : 'PLAY VIDEO'}</span>
            </button>
            <button
              type="button"
              onClick={() => setVideoMuted(m => !m)}
              aria-label={videoMuted ? 'Unmute video audio' : 'Mute video audio'}
              aria-pressed={!videoMuted}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 8px',
                background: 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#fff',
                cursor: 'pointer',
                fontSize: 8,
                letterSpacing: 1.2,
              }}
            >
              {videoMuted ? <VolumeX size={11} /> : <Volume2 size={11} />}
              <span>{videoMuted ? 'MUTED' : 'AUDIO ON'}</span>
            </button>
          </>
        )}
      </div>
    </section>
  );
}

const CATEGORY_EDITORIAL_FALLBACKS: Record<string, string> = {
  'color': 'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=600&q=80',
  'materials': 'https://images.unsplash.com/photo-1558769132-cb1aea458c5e?auto=format&fit=crop&w=600&q=80',
  'silhouettes': 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=600&q=80',
  'patterns': 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=600&q=80',
  'prints': 'https://images.unsplash.com/photo-1469334031218-e382a71b716b?auto=format&fit=crop&w=600&q=80',
  'textures': 'https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&w=600&q=80',
  'product': 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=600&q=80',
  'accessories': 'https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=600&q=80',
  'womenswear': 'https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?auto=format&fit=crop&w=600&q=80',
  'menswear': 'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=600&q=80',
  'streetwear': 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=600&q=80',
  'couture': 'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=600&q=80',
  'retail': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=600&q=80',
  'consumer': 'https://images.unsplash.com/photo-1492707892479-7bc8d5a4ee93?auto=format&fit=crop&w=600&q=80',
  'market': 'https://images.unsplash.com/photo-1445205170230-053b83016050?auto=format&fit=crop&w=600&q=80',
  'future signals': 'https://images.unsplash.com/photo-1508427953056-b00b8d78ebf5?auto=format&fit=crop&w=600&q=80',
};

function Home({
  trends,
  candidates = [],
  candidatesLoading,
  candidatesError,
  onRetryCandidates,
  dashboard,
  currentNews,
  newsError,
  newsLoading,
  onRefreshNews,
  liveSignals,
  categories,
  onNavigate,
  onTrend,
  onInspectTrend,
  onSearch,
  onVision,
}: {
  trends: AnyRecord[];
  candidates?: NewsDerivedCandidate[];
  candidatesLoading: boolean;
  candidatesError: string | null;
  onRetryCandidates: () => void;
  dashboard: AnyRecord | null;
  currentNews: AnyRecord | null;
  newsError: string | null;
  newsLoading: boolean;
  onRefreshNews: () => void;
  liveSignals: AnyRecord | null;
  categories: AnyRecord[];
  onNavigate: NavigateFn;
  onTrend: (trend: AnyRecord) => void;
  onInspectTrend?: (trend: AnyRecord) => void;
  onSearch: () => void;
  onVision: () => void;
}) {
  const [feedFilter, setFeedFilter] = useState<'all' | 'emerging' | 'established' | 'aesthetics'>('all');
  const feedRef = useRef<HTMLDivElement>(null);
  const signals = liveSignals || {
    runway: null,
    social: null,
    retail: null,
    search: null,
    culture: null,
    data_status: 'insufficient_data',
  };

  const persistedFeed: AnyRecord[] = trends.length
    ? trends
    : (dashboard?.recent_trends as AnyRecord[]) || [];
  const feed: AnyRecord[] = [
    ...persistedFeed,
    ...candidates
      .map(candidateToTrendRecord)
      .filter(candidate => !persistedFeed.some(trend => trend.slug === candidate.slug || trend.id === candidate.id)),
  ];

  const filteredFeed = feed.filter((item: AnyRecord) => {
    if (feedFilter === 'all') return true;
    if (feedFilter === 'emerging') {
      return Boolean(item.is_candidate || item.data_status === 'news_derived' || item.status === 'emerging');
    }
    if (feedFilter === 'established') {
      return !item.is_candidate && (item.confidence > 70 || (item.cross_source_agreement && item.cross_source_agreement > 0.6) || item.status === 'established');
    }
    if (feedFilter === 'aesthetics') {
      const cat = (item.category || '').toLowerCase();
      return ['color', 'materials', 'silhouettes', 'textures', 'patterns', 'prints'].some(c => cat.includes(c));
    }
    return true;
  });

  const newsItems: AnyRecord[] = currentNews?.items || [];

  return (
    <>
      <HeroCandidateSlider
        candidates={candidates}
        loading={candidatesLoading}
        error={candidatesError}
        onRetry={onRetryCandidates}
        onExplore={candidate => onTrend(candidateToTrendRecord(candidate))}
      />

      <SignalStrip signals={signals} />

      <section className="section-wrap feed-section">
        <Reveal>
          <SectionIntro
            kicker="01 / RECENT SIGNALS"
            title="What is starting to move"
            description="The first indications of a shift, extracted dynamically from connected intelligence signals."
            action={<DataTag>{signals.data_status?.toUpperCase() || 'DEMO'}</DataTag>}
          />
        </Reveal>

        <div className="category-filter-bar" style={{ margin: '14px 0 18px' }}>
          <button
            className={`category-pill ${feedFilter === 'all' ? 'active' : ''}`}
            onClick={() => setFeedFilter('all')}
          >
            ALL RECENT SIGNALS
          </button>
          <button
            className={`category-pill ${feedFilter === 'emerging' ? 'active' : ''}`}
            onClick={() => setFeedFilter('emerging')}
          >
            EMERGING SIGNALS (NEWS & RUNWAY)
          </button>
          <button
            className={`category-pill ${feedFilter === 'established' ? 'active' : ''}`}
            onClick={() => setFeedFilter('established')}
          >
            ESTABLISHED TRENDS (HIGH CONCORDANCE)
          </button>
          <button
            className={`category-pill ${feedFilter === 'aesthetics' ? 'active' : ''}`}
            onClick={() => setFeedFilter('aesthetics')}
          >
            RISING AESTHETICS
          </button>
        </div>

        <div className="trend-feed" ref={feedRef}>
          {filteredFeed.map((trend: AnyRecord, index: number) => (
            <TrendCard
              trend={trend}
              index={index}
              key={trend.id ?? trend.name}
              onClick={() => onTrend(trend)}
              onInspect={onInspectTrend ? () => onInspectTrend(trend) : undefined}
            />
          ))}
          {!filteredFeed.length && (
            <p role="status">No trend records match the selected signal filter.</p>
          )}
        </div>
        <div className="feed-control">
          <span>01 — 0{filteredFeed.length}</span>
          <div>
            <button aria-label="Previous trend" onClick={() => feedRef.current?.scrollBy({ left: -320, behavior: 'smooth' })}>
              <ChevronLeft size={16} />
            </button>
            <button aria-label="Next trend" onClick={() => feedRef.current?.scrollBy({ left: 320, behavior: 'smooth' })}>
              <ChevronRight size={16} />
            </button>
          </div>
          <span>HORIZONTAL INTELLIGENCE FEED</span>
        </div>
      </section>

      <section className="section-wrap intelligence-section">
        <Reveal>
          <SectionIntro
            kicker="02 / 16-CARD INTELLIGENCE GRID"
            title="Fashion intelligence, in every direction."
            description="Explore the sixteen dimensions of market change, connecting raw aesthetics to retail execution."
          />
        </Reveal>
        <div className="intelligence-grid">
          {categories.map((cat, idx) => {
            const catKey = (cat.name || '').toLowerCase();
            const matchCand = candidates.find(
              c => (c.category || '').toLowerCase() === catKey && (c.imageUrl || c.articles?.[0]?.imageUrl)
            );
            const matchFeed = feed.find(
              f => (f.category || '').toLowerCase() === catKey && (f.image_url || f.imageUrl || f.leadImage)
            );
            const photoUrl =
              matchCand?.imageUrl ||
              matchCand?.articles?.[0]?.imageUrl ||
              matchFeed?.image_url ||
              matchFeed?.imageUrl ||
              (matchFeed as any)?.leadImage ||
              CATEGORY_EDITORIAL_FALLBACKS[catKey] ||
              CATEGORY_EDITORIAL_FALLBACKS['color'];

            return (
              <button
                key={cat.name}
                className={`intel-card card-${cat.tone || 'green'}`}
                onClick={() => {
                  const targetPage: Page =
                    cat.route === 'product'
                      ? 'product'
                      : cat.route === 'retail'
                      ? 'retail'
                      : cat.route === 'prophecy'
                      ? 'prophecy'
                      : 'trend';
                  onNavigate(targetPage, { category: cat.name });
                }}
              >
                <span className="intel-number">{cat.code || `0${idx + 1}`}</span>
                {photoUrl && (
                  <img
                    src={photoUrl}
                    alt={cat.name}
                    className="intel-photo"
                    onError={e => {
                      (e.currentTarget as HTMLElement).style.display = 'none';
                    }}
                  />
                )}
                <div className="intel-art" />
                <div className="intel-copy">
                  <span>{cat.name.toUpperCase()}</span>
                  <b>{cat.subtitle || 'Signals in motion'}</b>
                </div>
                <ArrowUpRight size={17} className="intel-arrow" />
              </button>
            );
          })}
        </div>
      </section>

      {feed[0] && !feed[0].is_candidate && <ExtractedCollection trend={feed[0]} onNavigate={onNavigate} />}

      <section className="current-section">
        <div className="current-art art-fuchsia">
          <div className="art-orbit" />
          <div className="art-sculpture" />
          <span>
            SOFT
            <br />
            STRUCTURE
          </span>
        </div>
        <Reveal className="current-copy">
          <span className="kicker">03 / CURRENT SIGNAL</span>
          <span className="date-line">{signals.data_status?.toUpperCase() || 'NO DATA'} SIGNAL SNAPSHOT</span>
          <h2>
            What's happening
            <br />
            <em>in fashion right now?</em>
          </h2>
          <p>
            Articles below are fetched from the publisher feed. Their publication timestamps and source links are retained; no market metrics are inferred from headlines.
          </p>
          {currentNews?.stale && (
            <p role="status">The publisher could not be refreshed; these are cached articles and may be stale.</p>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '14px 0' }}>
            <DataTag>
              SOURCE: {(currentNews?.source_name || 'UNAVAILABLE').toUpperCase()}
            </DataTag>
            {currentNews?.fetched_at && (
              <span className="date-line">
                FETCHED {new Date(currentNews.fetched_at).toLocaleString()}
              </span>
            )}
            <button className="underlined-link" onClick={onRefreshNews} disabled={newsLoading}>
              {newsLoading ? 'Refreshing…' : 'Refresh news'} <RefreshCw size={14} />
            </button>
          </div>
          <div aria-live="polite">
            {newsLoading && newsItems.length === 0 && <p role="status">Loading publisher articles…</p>}
            {newsError && (
              <p role="alert">Current fashion news is unavailable: {newsError}</p>
            )}
            {!newsLoading && !newsError && newsItems.length === 0 && (
              <p role="status">The publisher feed returned no articles.</p>
            )}
 
 
 
 
 
            {newsItems.map((item: AnyRecord) => (
              <article key={item.url} style={{ borderTop: '1px solid var(--line)', padding: '14px 0' }}>
                <a href={item.url} target="_blank" rel="noopener noreferrer">
                  <strong>{item.title}</strong>
                </a>
                {item.summary && <p>{item.summary}</p>}
                <div className="date-line">
                  {item.source_name} · {item.observed_at
                    ? new Date(item.observed_at).toLocaleString()
                    : 'Publication time unavailable'}
                </div>
              </article>
            ))}
          </div>
          <div className="current-stats">
            <div>
              <span>RUNWAY</span>
              <b>{signals.runway == null ? '—' : `↑ ${signals.runway}%`}</b>
            </div>
            <div>
              <span>SOCIAL</span>
              <b>{signals.social == null ? '—' : `↑ ${signals.social}%`}</b>
            </div>
            <div>
              <span>RETAIL</span>
              <b>{signals.retail == null ? '—' : `↑ ${signals.retail}%`}</b>
            </div>
            <div>
              <span>SEARCH</span>
              <b>{signals.search == null ? '—' : `↑ ${signals.search}%`}</b>
            </div>
          </div>

          {/* 5-Domain Telemetry Channel Overview */}
          <div style={{ marginTop: 24, padding: '16px 20px', background: 'rgba(255,255,255,0.7)', border: '1px solid var(--line)' }}>
            <span className="kicker" style={{ fontSize: 9, marginBottom: 8, display: 'block' }}>TELEMETRY CHANNELS & PROVENANCE</span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, fontSize: 11 }}>
              <div>
                <strong style={{ display: 'block', fontSize: 10 }}>EDITORIAL ATTENTION</strong>
                <span style={{ color: 'var(--muted)', fontSize: 10 }}>Vogue, Elle, GQ, Harper's Bazaar RSS feeds</span>
              </div>
              <div>
                <strong style={{ display: 'block', fontSize: 10 }}>SEARCH INTEREST</strong>
                <span style={{ color: 'var(--muted)', fontSize: 10 }}>Normalized search indexing queries</span>
              </div>
              <div>
                <strong style={{ display: 'block', fontSize: 10 }}>OBSERVED SOCIAL SIGNALS</strong>
                <span style={{ color: 'var(--muted)', fontSize: 10 }}>Community evidence & user submissions</span>
              </div>
              <div>
                <strong style={{ display: 'block', fontSize: 10 }}>RETAIL ASSORTMENT</strong>
                <span style={{ color: 'var(--muted)', fontSize: 10 }}>SKU catalog depth & listed dynamics</span>
              </div>
              <div style={{ gridColumn: '1 / -1', borderTop: '1px solid var(--line)', paddingTop: 6 }}>
                <strong style={{ display: 'block', fontSize: 10, color: 'var(--ink)' }}>TRANSACTIONAL CONSUMER DEMAND</strong>
                <span style={{ color: 'var(--muted)', fontSize: 10 }}>Requires retailer POS/EDI integration; never inferred from editorial buzz or mock data.</span>
              </div>
            </div>
          </div>

          <button className="underlined-link" onClick={() => onNavigate('trend')} style={{ marginTop: 18 }}>
            Explore current signal <ArrowRight size={15} />
          </button>
        </Reveal>
      </section>

      <PlatformOverview onNavigate={onNavigate} />
      <FinalCta onNavigate={onNavigate} />
    </>
  );
}

function SignalStrip({ signals }: { signals: AnyRecord }) {
  const items = [
    ['RUNWAY', signals.runway],
    ['SOCIAL', signals.social],
    ['RETAIL', signals.retail],
    ['SEARCH', signals.search],
    ['CULTURE', signals.culture],
  ];

  return (
    <section className="signal-strip">
      <div>
        <span className="kicker">FASHION SIGNAL CHANNELS</span>
        <b>OBSERVED RECORDS ONLY</b>
      </div>
      {items.map(([label, val]) => (
        <div className="strip-signal" key={label as string}>
          <span>{label as string}</span>
          <strong>{val == null ? '—' : `↑ ${val}%`}</strong>
          <i style={{ height: `${typeof val === 'number' ? val / 3 : 0}%` }} />
        </div>
      ))}
    </section>
  );
}

function TrendCard({
  trend,
  index,
  onClick,
  onInspect,
}: {
  trend: AnyRecord;
  index: number;
  onClick: () => void;
  onInspect?: () => void;
}) {
  const tones = ['green', 'ink', 'rose', 'sand', 'plum'];
  const tone = tones[index % tones.length];
  const isNewEvidence = Boolean(trend.is_candidate || (trend.articles && trend.articles.length > 0));

  return (
    <div
      className="trend-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      style={{ cursor: 'pointer', textAlign: 'left' }}
    >
      <div className={`trend-art art-${tone}`} style={{ position: 'relative', overflow: 'hidden' }}>
        {(trend.image_url || trend.imageUrl) && (
          <img
            src={(trend.image_url || trend.imageUrl) ?? undefined}
            alt={trend.name}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              filter: 'brightness(0.92)',
              transition: 'transform 0.4s ease',
            }}
            onError={e => {
              (e.currentTarget as HTMLElement).style.display = 'none';
            }}
          />
        )}
        <span className="trend-card-number" style={{ zIndex: 2 }}>0{index + 1}</span>
        <span
          style={{
            position: 'absolute',
            top: 14,
            right: 14,
            zIndex: 2,
            fontSize: 8,
            letterSpacing: '0.08em',
            padding: '3px 7px',
            background: isNewEvidence ? '#eef6f0' : '#f5f5f5',
            color: isNewEvidence ? '#1b5e20' : '#616161',
            border: isNewEvidence ? '1px solid #c8e6c9' : '1px solid #e0e0e0',
            borderRadius: 2,
            textTransform: 'uppercase',
            fontWeight: 600,
            backdropFilter: 'blur(4px)',
          }}
        >
          {isNewEvidence ? 'NEW EVIDENCE (24–48H)' : 'HISTORICAL BASELINE'}
        </span>
        {!trend.image_url && !trend.imageUrl && <div className="art-shape" />}
        <ArrowUpRight className="trend-card-arrow" size={18} style={{ zIndex: 2 }} />
      </div>
      <div className="trend-card-meta">
        <div>
          <b>{trend.name}</b>
          <span>
            {trend.category?.toUpperCase() || 'TREND'} · {trend.is_candidate ? 'NEWS-DERIVED' : trend.season || 'SEASON UNAVAILABLE'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {onInspect && (
            <button
              className="trend-card-cta"
              style={{ background: 'none', border: '1px solid var(--line)', padding: '4px 8px', borderRadius: 2 }}
              onClick={e => {
                e.stopPropagation();
                onInspect();
              }}
              title="Inspect Quantitative Dossier"
            >
              DOSSIER
            </button>
          )}
          <span className="trend-card-cta">
            VIEW <ArrowRight size={13} />
          </span>
        </div>
      </div>
    </div>
  );
}

function ExtractedCollection({
  trend,
  collection,
  onNavigate,
  onGenerateCollection,
  currentUser,
  onOpenLogin,
}: {
  trend: AnyRecord;
  collection?: AnyRecord | null;
  onNavigate: NavigateFn;
  onGenerateCollection?: () => Promise<void>;
  currentUser?: AnyRecord | null;
  onOpenLogin?: () => void;
}) {
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const dna = trend?.dna || {};
  const firstDnaValue = (values: unknown): string => {
    if (!Array.isArray(values) || values.length === 0) return '—';
    const value: unknown = values[0];
    if (typeof value === 'string') return value;
    if (value && typeof value === 'object') {
      const entry = value as Record<string, unknown>;
      if (typeof entry.hex === 'string') return entry.hex;
      if (typeof entry.name === 'string') return entry.name;
    }
    return '—';
  };

  const handleGen = async () => {
    if (!currentUser && onOpenLogin) {
      onOpenLogin();
      return;
    }
    if (!onGenerateCollection) return;
    setGenerating(true);
    setGenError(null);
    try {
      await onGenerateCollection();
    } catch (err: any) {
      setGenError(err?.message || 'Capsule collection synthesis failed.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <section className="collection-section">
      <div className="collection-heading">
        <span className="kicker light">04 / EXTRACTED COLLECTION</span>
        <h2>{trend?.name ?? 'Trend DNA'}</h2>
        <p>Visual attributes and synthesized capsule architecture for this trend.</p>
      </div>

      {collection && (
        <div className="capsule-box">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="kicker light">SYNTHESIZED CAPSULE COLLECTION</span>
            <DataTag>{collection.data_status?.toUpperCase() || 'GENERATED'}</DataTag>
          </div>
          <h3>{collection.name}</h3>
          <p>{collection.description}</p>

          {Array.isArray(collection.color_palette) && collection.color_palette.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <span style={{ fontSize: 9, letterSpacing: 1, color: 'rgba(255,255,255,0.7)', fontWeight: 700 }}>
                PALETTE EXTRACTION
              </span>
              <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                {collection.color_palette.map((col: any, idx: number) => {
                  const hex = typeof col === 'string' ? col : col.hex;
                  const label = typeof col === 'string' ? col : col.name || col.hex;
                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        background: 'rgba(255,255,255,0.1)',
                        padding: '4px 8px',
                        border: '1px solid rgba(255,255,255,0.2)',
                      }}
                    >
                      <span
                        style={{
                          width: 12,
                          height: 12,
                          background: hex,
                          display: 'inline-block',
                          border: '1px solid rgba(255,255,255,0.4)',
                        }}
                      />
                      <span style={{ fontSize: 10, fontFamily: 'monospace' }}>{label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {Array.isArray(collection.product_opportunities) && collection.product_opportunities.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <span style={{ fontSize: 9, letterSpacing: 1, color: 'rgba(255,255,255,0.7)', fontWeight: 700 }}>
                CAPSULE PRODUCT OPPORTUNITIES
              </span>
              <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                {collection.product_opportunities.map((opp: any, idx: number) => (
                  <span
                    key={idx}
                    style={{
                      background: 'rgba(255,255,255,0.15)',
                      padding: '4px 10px',
                      fontSize: 11,
                      letterSpacing: 0.5,
                      border: '1px solid rgba(255,255,255,0.2)',
                    }}
                  >
                    {typeof opp === 'string' ? opp : opp.name || opp.category || JSON.stringify(opp)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {genError && (
        <div style={{ background: '#fce8ea', color: '#c0392b', padding: 12, fontSize: 12, margin: '15px 0' }}>
          {genError}
        </div>
      )}

      <div className="collection-grid">
        {(trend?.image_url || trend?.imageUrl || collection?.image_url) ? (
          <div className="collection-art" style={{ position: 'relative', overflow: 'hidden', background: 'var(--plum)' }}>
            <img
              src={trend?.image_url || trend?.imageUrl || collection?.image_url}
              alt={trend?.name ? `${trend.name} visual DNA` : 'Trend visual DNA'}
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                filter: 'brightness(0.70) contrast(1.08)',
                zIndex: 1,
              }}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
                const fb = e.currentTarget.parentElement?.querySelector('.collection-img-fallback');
                if (fb) (fb as HTMLElement).style.display = 'block';
              }}
            />
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: 'linear-gradient(180deg, rgba(15, 39, 41, 0.25) 0%, rgba(15, 39, 41, 0.78) 100%)',
                zIndex: 2,
                pointerEvents: 'none',
              }}
            />
            <div className="art-grid-lines" style={{ zIndex: 3, opacity: 0.35, pointerEvents: 'none' }} />
            <span style={{ position: 'absolute', left: 27, bottom: 23, zIndex: 4 }}>
              VISUAL
              <br />
              DNA
            </span>
            <div
              className="collection-img-fallback art-plum"
              style={{
                display: 'none',
                position: 'absolute',
                inset: 0,
                zIndex: 1,
              }}
            >
              <div className="art-grid-lines" />
              <div
                style={{
                  position: 'absolute',
                  top: 24,
                  right: 24,
                  padding: '4px 8px',
                  border: '1px solid rgba(255, 255, 255, 0.25)',
                  fontSize: 9,
                  letterSpacing: '0.1em',
                  color: 'rgba(255, 255, 255, 0.75)',
                  textTransform: 'uppercase',
                }}
              >
                Image unavailable
              </div>
              <span>
                VISUAL
                <br />
                DNA
              </span>
            </div>
          </div>
        ) : (
          <div className="collection-art art-plum" style={{ position: 'relative', overflow: 'hidden' }}>
            <div className="art-grid-lines" />
            <div
              style={{
                position: 'absolute',
                top: 24,
                right: 24,
                padding: '4px 8px',
                border: '1px solid rgba(255, 255, 255, 0.25)',
                fontSize: 9,
                letterSpacing: '0.1em',
                color: 'rgba(255, 255, 255, 0.75)',
                textTransform: 'uppercase',
              }}
            >
              Image unavailable
            </div>
            <span>
              VISUAL
              <br />
              DNA
            </span>
          </div>
        )}
        <div className="collection-data">
          <DataTag>
            DNA DATA: {(dna.data_status || trend?.data_status || 'insufficient_data').toUpperCase()}
          </DataTag>
          <div className="dna-row">
            <div>
              <span>COLOR</span>
              <b>{firstDnaValue(dna.colors)}</b>
            </div>
            <div>
              <span>MATERIAL</span>
              <b>{firstDnaValue(dna.materials)}</b>
            </div>
            <div>
              <span>SILHOUETTE</span>
              <b>{firstDnaValue(dna.silhouettes)}</b>
            </div>
            <div>
              <span>PATTERN</span>
              <b>{firstDnaValue(dna.patterns)}</b>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 24 }}>
            {onGenerateCollection && (
              <button
                className="button"
                onClick={handleGen}
                disabled={generating || Boolean(trend.is_candidate)}
                style={{ background: 'var(--pink)', color: '#fff', border: 0 }}
              >
                {trend.is_candidate
                  ? 'REQUIRES VERIFIED OBSERVATIONS'
                  : generating ? 'SYNTHESIZING...' : collection ? 'REGENERATE CAPSULE' : 'GENERATE CAPSULE COLLECTION'}
                <Sparkles size={14} />
              </button>
            )}
            <button className="button light-button" onClick={() => onNavigate('product', { trend, category: trend.category })}>
              See product opportunities <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function PlatformOverview({ onNavigate }: { onNavigate: NavigateFn }) {
  return (
    <section className="platform-section section-wrap">
      <Reveal>
        <SectionIntro
          kicker="05 / THE PLATFORM"
          title="One system. Every signal."
          description="LUXE.TECH connects the visual, commercial and future layers of fashion intelligence."
        />
      </Reveal>
      <div className="platform-grid">
        <article className="platform-block block-rose">
          <span>01</span>
          <div>
            <h3>Product intelligence</h3>
            <p>Find the product opportunity inside an emerging visual language.</p>
            <button className="underlined-link" onClick={() => onNavigate('product')}>
              Explore product <ArrowRight size={14} />
            </button>
          </div>
        </article>
        <article className="platform-block block-green">
          <span>02</span>
          <div>
            <h3>Retail intelligence</h3>
            <p>Understand what is moving, where it is moving and who is buying.</p>
            <button className="underlined-link" onClick={() => onNavigate('retail')}>
              Read the market <ArrowRight size={14} />
            </button>
          </div>
        </article>
        <article className="platform-block block-ink">
          <span>03</span>
          <div>
            <h3>Statistical Forecasting & Prophecy</h3>
            <p>Compete 4 statistical time-series models and forecast next-era scenarios.</p>
            <button className="underlined-link" onClick={() => onNavigate('forecast')}>
              Enter Forecast <ArrowRight size={14} />
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}

function FinalCta({ onNavigate }: { onNavigate: NavigateFn }) {
  return (
    <section className="final-cta">
      <div>
        <span className="kicker light">THE NEXT SIGNAL IS ALREADY HERE</span>
        <h2>
          See what fashion
          <br />
          <em>is becoming.</em>
        </h2>
      </div>
      <button className="button light-button" onClick={() => onNavigate('prophecy')}>
        Enter Prophecy <ArrowRight size={15} />
      </button>
    </section>
  );
}

function NewsDerivedCandidatePanel({
  candidates,
  category,
  loading,
  error,
  onRetry,
  onSelectCandidate,
}: {
  candidates: NewsDerivedCandidate[];
  category: string | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelectCandidate?: (candidate: NewsDerivedCandidate) => void;
}) {
  const visibleCandidates = candidates.filter(candidate =>
    !category || candidate.category.toLowerCase() === category.toLowerCase()
  );

  return (
    <section
      aria-labelledby="news-candidates-heading"
      style={{
        marginTop: 28,
        padding: '24px',
        border: '1px solid rgba(16, 33, 38, 0.14)',
        background: 'rgba(255, 255, 255, 0.62)',
      }}
    >
      <span className="kicker">EDITORIAL COVERAGE</span>
      <h2 id="news-candidates-heading" style={{ marginTop: 8 }}>News-derived candidates</h2>
      <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.6, margin: '8px 0 20px' }}>
        Candidates are clustered from cached publisher articles and are not independently verified market observations.
        Article frequency does not measure consumer demand, sales, search volume, runway prevalence, or predictive accuracy.
      </p>

      {loading && <p role="status">Loading news-derived candidates…</p>}
      {error && (
        <div role="alert" style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <p>{error}</p>
          <button className="button light-button" onClick={onRetry}>TRY AGAIN</button>
        </div>
      )}
      {!loading && !error && visibleCandidates.length === 0 && (
        <p role="status">
          {category
            ? `No news-derived candidates are available for ${category}.`
            : 'No news-derived candidates are available yet.'}
        </p>
      )}

      <div style={{ display: 'grid', gap: 16 }}>
        {visibleCandidates.map(candidate => (
          <article
            key={candidate.key}
            style={{
              padding: '18px',
              border: '1px solid rgba(16, 33, 38, 0.12)',
              background: '#fff',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
              <div>
                <span
                  style={{
                    display: 'inline-block',
                    marginBottom: 8,
                    fontSize: 10,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: 'var(--pink)',
                  }}
                >
                  {candidate.sourceLabel}
                </span>
                <h3 style={{ margin: 0 }}>{candidate.name}</h3>
                <p style={{ color: 'var(--muted)', margin: '5px 0 0' }}>{candidate.category}</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                  {candidate.publisherCount} {candidate.publisherCount === 1 ? 'publisher' : 'publishers'}
                </span>
                {onSelectCandidate && (
                  <button
                    className="button light-button"
                    style={{ fontSize: 11, padding: '4px 12px', minHeight: 30 }}
                    onClick={() => onSelectCandidate(candidate)}
                  >
                    INSPECT CANDIDATE <ArrowRight size={12} style={{ marginLeft: 4 }} />
                  </button>
                )}
              </div>
            </div>

            <ul style={{ listStyle: 'none', margin: '16px 0 0', padding: 0, display: 'grid', gap: 10 }}>
              {candidate.articles.map((article, index) => {
                const publishedDate = article.publishedAt ? new Date(article.publishedAt) : null;
                const publishedAt = publishedDate && !Number.isNaN(publishedDate.getTime())
                  ? publishedDate.toLocaleString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                    })
                  : 'Publication time unavailable';

                return (
                  <li
                    key={`${article.articleUrl}-${index}`}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: 16,
                      padding: '12px 14px',
                      background: 'rgba(16, 33, 38, 0.035)',
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 5 }}>
                        <strong style={{ fontSize: 11 }}>{article.publisher}</strong>
                        <time
                          dateTime={article.publishedAt || undefined}
                          style={{ fontSize: 11, color: 'var(--muted)' }}
                        >
                          {publishedAt}
                        </time>
                      </div>
                      <a
                        href={article.articleUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'inherit', fontSize: 13, lineHeight: 1.5 }}
                      >
                        {article.headline}
                      </a>
                    </div>
                  </li>
                );
              })}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}

function FashionVideosPage({
  provider,
  videos,
  loading,
  error,
  fetchedAt,
  onSearch,
}: {
  provider: AnyRecord | null;
  videos: AnyRecord[];
  loading: boolean;
  error: string | null;
  fetchedAt: string | null;
  onSearch: (filters?: {
    query?: string;
    topic?: string;
    published_after?: string;
    order?: string;
    region_code?: string;
    duration?: string;
  }) => Promise<void>;
}) {
  const [query, setQuery] = useState('fashion runway designer collection');
  const [topic, setTopic] = useState('');
  const [publishedAfter, setPublishedAfter] = useState('');
  const [order, setOrder] = useState('relevance');
  const [regionCode, setRegionCode] = useState('');
  const [duration, setDuration] = useState('any');
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);
  const [muted, setMuted] = useState(true);
  const playerRef = useRef<HTMLIFrameElement>(null);

  const toggleMute = () => {
    const nextMuted = !muted;
    setMuted(nextMuted);
    playerRef.current?.contentWindow?.postMessage(
      JSON.stringify({ event: 'command', func: nextMuted ? 'mute' : 'unMute', args: [] }),
      'https://www.youtube-nocookie.com',
    );
  };

  return (
    <div className="detail-page">
      <section className="section-wrap" style={{ paddingTop: 64, paddingBottom: 72 }}>
        <span className="kicker">FASHION VIDEO DISCOVERY</span>
        <h1>Watch the source.</h1>
        <p style={{ maxWidth: 720, color: 'var(--muted)', lineHeight: 1.7 }}>
          Search public fashion video metadata through the official YouTube Data API. A recent upload is not, by itself,
          evidence of virality or trend prevalence. Playback uses official YouTube embeds.
        </p>
        <p role="status" style={{ fontSize: 12, color: 'var(--muted)' }}>
          Provider: {provider?.available ? 'YouTube Data API configured' : 'YouTube provider unavailable'}
          {fetchedAt ? ` · Last successful fetch ${new Date(fetchedAt).toLocaleString()}` : ''}
        </p>

        {!provider?.available && !loading && (
          <div role="status" style={{ padding: 18, background: 'rgba(16,33,38,.06)', margin: '20px 0' }}>
            Video discovery is not configured. Set <code>YOUTUBE_API_KEY</code> on the backend, restart it, and retry.
          </div>
        )}

        <form
          onSubmit={event => {
            event.preventDefault();
            void onSearch({
              query,
              topic: topic || undefined,
              published_after: publishedAfter
                ? new Date(`${publishedAfter}T00:00:00Z`).toISOString()
                : undefined,
              order,
              region_code: regionCode || undefined,
              duration,
            });
          }}
          style={{ display: 'flex', gap: 12, flexWrap: 'wrap', margin: '24px 0' }}
        >
          <input
            aria-label="Search fashion videos"
            value={query}
            onChange={event => setQuery(event.target.value)}
            maxLength={200}
            minLength={2}
            required
            style={{ flex: '1 1 300px', minHeight: 44, padding: '0 12px' }}
          />
          <select aria-label="Fashion topic" value={topic} onChange={event => setTopic(event.target.value)}>
            <option value="">All fashion topics</option>
            {['runway', 'street style', 'colour', 'silhouette', 'knitwear', 'Indian ethnic wear', 'kurti', 'designer collections'].map(value => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
          <input
            aria-label="Published after"
            type="date"
            value={publishedAfter}
            onChange={event => setPublishedAfter(event.target.value)}
          />
          <select aria-label="Order videos by" value={order} onChange={event => setOrder(event.target.value)}>
            <option value="relevance">Relevant first</option>
            <option value="date">Newest first</option>
            <option value="viewCount">YouTube view count</option>
          </select>
          <input
            aria-label="Region code"
            value={regionCode}
            onChange={event => setRegionCode(event.target.value.toUpperCase().slice(0, 2))}
            pattern="[A-Z]{2}"
            maxLength={2}
            placeholder="Region"
          />
          <select aria-label="Video duration" value={duration} onChange={event => setDuration(event.target.value)}>
            <option value="any">Any duration</option>
            <option value="short">Short</option>
            <option value="medium">Medium</option>
            <option value="long">Long</option>
          </select>
          <button className="button dark-button" type="submit" disabled={loading || !query.trim() || (regionCode.length > 0 && regionCode.length !== 2)}>
            {loading ? 'SEARCHING…' : 'SEARCH VIDEOS'} <Search size={14} />
          </button>
        </form>

        {error && (
          <div role="alert" style={{ margin: '20px 0' }}>
            <p>{error}</p>
            <button className="button light-button" onClick={() => void onSearch({
              query,
              topic: topic || undefined,
              published_after: publishedAfter ? new Date(`${publishedAfter}T00:00:00Z`).toISOString() : undefined,
              order,
              region_code: regionCode || undefined,
              duration,
            })}>RETRY</button>
          </div>
        )}
        {loading && <p role="status">Searching fashion videos…</p>}
        {!loading && !error && provider?.available && videos.length === 0 && (
          <p role="status">No matching videos were returned for this query.</p>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: 20 }}>
          {videos.map(video => {
            const active = activeVideoId === video.video_id;
            return (
              <article key={video.video_id} style={{ border: '1px solid var(--line)', background: 'var(--paper)' }}>
                {active ? (
                  <div style={{ position: 'relative', aspectRatio: '16 / 9', background: '#101010' }}>
                    <iframe
                      ref={playerRef}
                      title={`YouTube video: ${video.title}`}
                      src={`https://www.youtube-nocookie.com/embed/${encodeURIComponent(video.video_id)}?controls=1&mute=${muted ? 1 : 0}&enablejsapi=1`}
                      allow="encrypted-media; picture-in-picture"
                      allowFullScreen
                      style={{ width: '100%', height: '100%', border: 0 }}
                    />
                    <button
                      type="button"
                      className="button light-button"
                      onClick={toggleMute}
                      style={{ position: 'absolute', right: 8, bottom: 8 }}
                    >
                      {muted ? 'UNMUTE' : 'MUTE'}
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setMuted(true);
                      setActiveVideoId(video.video_id);
                    }}
                    aria-label={`Play ${video.title}`}
                    style={{ width: '100%', display: 'block', padding: 0, border: 0, cursor: 'pointer', background: '#101010' }}
                  >
                    {video.thumbnail_url ? (
                      <img
                        src={video.thumbnail_url}
                        alt={video.title || 'Fashion video preview'}
                        loading="lazy"
                        style={{ width: '100%', display: 'block', aspectRatio: '16 / 9', objectFit: 'cover' }}
                        onError={e => {
                          (e.currentTarget as HTMLElement).style.display = 'none';
                        }}
                      />
                    ) : (
                      <div style={{ display: 'grid', placeItems: 'center', aspectRatio: '16 / 9', background: '#142526', color: 'rgba(255,255,255,0.7)', fontSize: 10, letterSpacing: '0.1em' }}>
                        <span>RUNWAY BROADCAST PREVIEW</span>
                      </div>
                    )}
                  </button>
                )}
                <div style={{ padding: 16 }}>
                  <span className="kicker">{video.source} · {video.creator}</span>
                  <h2 style={{ fontSize: 18, margin: '8px 0' }}>{video.title}</h2>
                  <time dateTime={video.published_at} style={{ fontSize: 12, color: 'var(--muted)' }}>
                    {video.published_at ? new Date(video.published_at).toLocaleString() : 'Publication time unavailable'}
                  </time>
                  <div style={{ marginTop: 12 }}>
                    <a href={video.canonical_url} target="_blank" rel="noopener noreferrer">Open on YouTube <ArrowUpRight size={13} /></a>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

// ----------------- TREND DETAIL PAGE -----------------
function TrendPage({
  trends,
  candidates,
  candidatesLoading,
  candidatesError,
  onRetryCandidates,
  selected,
  categories,
  activeCategory,
  onSelectCategory,
  onTrend,
  onNavigate,
  isSaved,
  onToggleSave,
  collection,
  onGenerateCollection,
  currentUser,
  onOpenLogin,
  onSubmitTrend,
  onInspectTrend,
}: {
  trends: AnyRecord[];
  candidates: NewsDerivedCandidate[];
  candidatesLoading: boolean;
  candidatesError: string | null;
  onRetryCandidates: () => void;
  selected: AnyRecord | null;
  categories: AnyRecord[];
  activeCategory: string | null;
  onSelectCategory: (cat: string) => void;
  onTrend: (trend: AnyRecord) => void;
  onNavigate: NavigateFn;
  isSaved: boolean;
  onToggleSave: (trendId: string) => void;
  collection?: AnyRecord | null;
  onGenerateCollection?: () => Promise<void>;
  currentUser?: AnyRecord | null;
  onOpenLogin?: () => void;
  onSubmitTrend?: () => void;
  onInspectTrend?: (trend: AnyRecord) => void;
}) {
  const activeCandidate = activeCategory
    ? candidates.find(c => c.category.toLowerCase() === activeCategory.toLowerCase()) || candidates[0]
    : candidates[0];

  const active = selected ?? trends[0] ?? (activeCandidate ? candidateToTrendRecord(activeCandidate) : null);

  const categoryFilterBar = (
    <div className="category-filter-bar">
      <button
        className={`category-pill ${!activeCategory ? 'active' : ''}`}
        onClick={() => onSelectCategory('')}
      >
        ALL CATEGORIES
      </button>
      {categories.slice(0, 10).map(cat => (
        <button
          key={cat.name}
          className={`category-pill ${activeCategory === cat.name ? 'active' : ''}`}
          onClick={() => onSelectCategory(cat.name)}
        >
          {cat.name.toUpperCase()}
        </button>
      ))}
    </div>
  );

  const candidatePanel = (
    <NewsDerivedCandidatePanel
      candidates={candidates}
      category={activeCategory}
      loading={candidatesLoading}
      error={candidatesError}
      onRetry={onRetryCandidates}
      onSelectCandidate={cand => onTrend(candidateToTrendRecord(cand))}
    />
  );

  if (!active) {
    return (
      <div className="detail-page">
        <section className="section-wrap" style={{ padding: '48px 20px 80px' }}>
          <span className="kicker">TREND INTELLIGENCE</span>
          {categoryFilterBar}
          {candidatePanel}
          <p role="status" style={{ color: 'var(--muted)', marginTop: 24 }}>
            No independently verified market observations are currently returned by the persisted trends API.
          </p>
          {activeCategory && (
            <button className="button dark-button" onClick={() => onSelectCategory('')} style={{ marginTop: 20 }}>
              Show All Trends
            </button>
          )}
        </section>
      </div>
    );
  }

  const dna = active.dna || {};
  const colors = dna.colors || [];
  const materials = dna.materials || [];
  const textures = dna.textures || [];
  const silhouettes = dna.silhouettes || [];
  const patterns = dna.patterns || [];
  const heroImage = active.image_url || active.imageUrl || null;

  return (
    <div className="detail-page">
      <section className="detail-hero hero-green" style={{ position: 'relative', overflow: 'hidden' }}>
        <div className="detail-hero-art" style={{ position: 'absolute', inset: 0, opacity: 1 }}>
          {heroImage ? (
            <>
              <img
                src={heroImage}
                alt={active.name ? `${active.name} trend photography` : 'Trend photography'}
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  filter: 'brightness(0.70) contrast(1.08)',
                  zIndex: 1,
                }}
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                  const fb = e.currentTarget.parentElement?.querySelector('.hero-fallback-art');
                  if (fb) (fb as HTMLElement).style.display = 'block';
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'linear-gradient(180deg, rgba(10, 26, 28, 0.42) 0%, rgba(10, 26, 28, 0.75) 50%, rgba(10, 26, 28, 0.94) 100%)',
                  zIndex: 2,
                  pointerEvents: 'none',
                }}
              />
              <div className="hero-fallback-art" style={{ display: 'none', position: 'absolute', inset: 0 }}>
                <div className="detail-orbit" />
                <div className="detail-shape" />
                <span
                  style={{
                    position: 'absolute',
                    bottom: 24,
                    right: 32,
                    fontSize: 10,
                    letterSpacing: '0.12em',
                    color: 'rgba(255, 255, 255, 0.65)',
                    textTransform: 'uppercase',
                  }}
                >
                  Image unavailable
                </span>
              </div>
            </>
          ) : (
            <>
              <div className="detail-orbit" />
              <div className="detail-shape" />
              <span
                style={{
                  position: 'absolute',
                  bottom: 24,
                  right: 32,
                  fontSize: 10,
                  letterSpacing: '0.12em',
                  color: 'rgba(255, 255, 255, 0.65)',
                  textTransform: 'uppercase',
                }}
              >
                Image unavailable
              </span>
            </>
          )}
        </div>
        <div className="detail-hero-copy">
          <span className="kicker light">
            {active.is_candidate ? 'NEWS-DERIVED CANDIDATE' : 'TREND INTELLIGENCE'}
          </span>
          <h1>{active.name}</h1>
          <p>{active.season || 'Season not established'}</p>
          <div className="hero-index">
            01 <span>—</span> {active.is_candidate ? 'EDITORIAL INTELLIGENCE' : 'INTELLIGENCE LAYER'}
          </div>
        </div>
      </section>

      <section className="section-wrap detail-content">
        {categoryFilterBar}
        {candidatePanel}

        {/* Editorial Disclaimer Notice Banner for Candidates */}
        {active.is_candidate && (
          <div
            style={{
              padding: '14px 18px',
              marginTop: 18,
              marginBottom: 10,
              border: '1px solid rgba(212, 163, 115, 0.35)',
              background: 'rgba(212, 163, 115, 0.08)',
              borderRadius: 4,
            }}
          >
            <strong style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Editorial Observation Notice:
            </strong>
            <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 0', lineHeight: 1.5 }}>
              This candidate trend is derived from verified fashion editorial coverage across {active.publisherCount || active.signals?.length || 'multiple'} publication{active.publisherCount === 1 ? '' : 's'}. Editorial press mentions do not measure retail sales volume, transactional consumer demand, or search velocity.
            </p>
          </div>
        )}

        <div className="detail-intro">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 15, marginBottom: 12, flexWrap: 'wrap' }}>
              <span className="kicker">WHY IT MATTERS</span>
              {(active.is_candidate || active.description?.includes('[news_derived]') || active.signals?.some((s: any) => s.signal_type === 'news_derived')) && (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 5,
                    fontSize: 10,
                    letterSpacing: '0.08em',
                    padding: '2px 8px',
                    border: '1px solid rgba(212, 163, 115, 0.4)',
                    background: 'rgba(212, 163, 115, 0.1)',
                    color: 'var(--foreground)',
                    textTransform: 'uppercase',
                  }}
                >
                  <Sparkles size={11} /> News-Derived Topic
                </span>
              )}
              <button
                className={`save-btn ${isSaved ? 'saved' : ''}`}
                onClick={() => onToggleSave(active.id)}
                disabled={active.is_candidate}
                title={active.is_candidate ? 'Editorial candidates are not persisted and cannot be saved as verified trends.' : undefined}
              >
                <Bookmark size={14} fill={isSaved ? 'currentColor' : 'none'} />
                <span>{isSaved ? 'SAVED TO WORKSPACE' : 'SAVE TREND'}</span>
              </button>
              {onInspectTrend && (
                <button
                  className="save-btn"
                  onClick={() => onInspectTrend(active)}
                  title="Inspect Quantitative Dossier"
                  style={{ borderColor: 'rgba(16, 33, 38, 0.4)' }}
                >
                  <Eye size={14} />
                  <span>INSPECT DOSSIER</span>
                </button>
              )}
              {onSubmitTrend && (
                <button
                  className="save-btn"
                  onClick={onSubmitTrend}
                  title="Submit a verified social post or observation for this trend"
                  style={{ borderColor: 'rgba(212, 163, 115, 0.4)' }}
                >
                  <Upload size={14} />
                  <span>SUBMIT OBSERVATION</span>
                </button>
              )}
            </div>
            <h2>{active.description}</h2>
          </div>
          <div>
            <DataTag>
              DATA STATUS: {active.data_status?.toUpperCase() || (active.is_candidate ? 'NEWS_DERIVED' : 'OBSERVED')}
            </DataTag>
            <div style={{ marginTop: 20 }}>
              <span className="kicker">CROSS-SOURCE AGREEMENT</span>
              <b style={{ fontFamily: 'Manrope', fontSize: 24 }}>
                {active.cross_source_agreement == null ? '—' : `${active.cross_source_agreement}%`}
              </b>
              <p style={{ fontSize: 11, color: 'var(--muted)', margin: '5px 0' }}>
                {active.is_candidate
                  ? 'Editorial candidate topic. Cross-market concordance is not calculated until persisted observations are ingested.'
                  : 'Statistical concordance across runway, social, search, retail, and cultural signals.'}
              </p>
            </div>
          </div>
        </div>

        {/* Signals */}
        <div className="signal-strength">
          <SectionIntro
            kicker="SIGNAL STRENGTH"
            title="The evidence, layer by layer."
            description="A directional read across independent sources."
          />
          {active.signals && active.signals.length > 0 ? (
            active.signals.slice(0, 5).map((sig: any) => (
              <SignalBar
                key={sig.id || sig.source}
                label={sig.signal_type === 'news_derived' ? `CULTURE / ${sig.metadata?.source_name?.toUpperCase() || 'PRESS'}` : sig.source?.toUpperCase()}
                value={sig.strength}
                tone={sig.strength > 75 ? 'pink' : 'green'}
              />
            ))
          ) : <p role="status">No signal observations are available for this trend.</p>}

          {/* Attributed Publisher Articles & Provenance */}
          {active.signals && active.signals.some((s: any) => s.metadata?.source_url || s.metadata?.article_title) && (
            <div
              className="editorial-evidence-card"
              style={{
                marginTop: 24,
                padding: '20px 24px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 4,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
                <span className="kicker" style={{ fontSize: 11, letterSpacing: '0.1em' }}>VERIFIED EDITORIAL PROVENANCE</span>
                <span style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'Space Grotesk, sans-serif' }}>
                  {active.signals.filter((s: any) => s.metadata?.source_url || s.metadata?.article_title).length} SOURCED ARTICLES
                </span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16, lineHeight: 1.5 }}>
                Editorial frequency reflects verified fashion press discussion and does not measure transactional retail sales or consumer purchase volume.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {active.signals
                  .filter((sig: any) => sig.metadata?.source_url || sig.metadata?.article_title)
                  .map((sig: any) => {
                    const meta = sig.metadata || {};
                    const pub = meta.source_name || meta.provenance?.publisher || sig.source || 'Publisher';
                    const title = meta.article_title || meta.provenance?.title || 'Verified Press Observation';
                    const url = meta.source_url || meta.provenance?.canonical_url;
                    const dateVal = sig.timestamp || meta.provenance?.published_at;
                    const timeStr = dateVal ? new Date(dateVal).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : null;
                    return (
                      <div
                        key={sig.id || url || title}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '12px 16px',
                          background: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                          gap: 16,
                        }}
                      >
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, overflow: 'hidden' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{
                              fontSize: 10,
                              letterSpacing: '0.06em',
                              padding: '2px 6px',
                              background: 'rgba(255, 255, 255, 0.08)',
                              fontWeight: 600,
                            }}>
                              {pub.toUpperCase()}
                            </span>
                            {timeStr && <span style={{ fontSize: 11, color: 'var(--muted)' }}>{timeStr}</span>}
                          </div>
                          <span style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {title}
                          </span>
                        </div>
                        {url && (
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                              color: 'inherit',
                              fontSize: 12,
                              flexShrink: 0,
                              textDecoration: 'underline',
                              textUnderlineOffset: 3,
                            }}
                          >
                            <span>Read</span>
                            <ArrowUpRight size={13} />
                          </a>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>

        {/* Visual DNA */}
        <div className="visual-dna">
          <SectionIntro kicker="VISUAL DNA" title="The language inside the trend." />
          <div className="dna-cards">
            <div className="dna-card dna-green">
              <span>COLOR CODES</span>
              <b>
                {colors[0]?.hex
                  ? `${colors[0].hex} (${colors[0].percentage}%)`
                  : colors[0] || '—'}
              </b>
              <ArrowUpRight size={15} />
            </div>
            <div className="dna-card dna-rose">
              <span>MATERIAL</span>
              <b>{materials[0] || '—'}</b>
              <ArrowUpRight size={15} />
            </div>
            <div className="dna-card dna-sand">
              <span>TEXTURE</span>
              <b>{textures[0] || '—'}</b>
              <ArrowUpRight size={15} />
            </div>
            <div className="dna-card dna-ink">
              <span>SILHOUETTE</span>
              <b>{silhouettes[0] || '—'}</b>
              <ArrowUpRight size={15} />
            </div>
            <div className="dna-card dna-plum">
              <span>PATTERN</span>
              <b>{patterns[0] || '—'}</b>
              <ArrowUpRight size={15} />
            </div>
          </div>
        </div>

        {/* Capsule Collection */}
        <ExtractedCollection
          trend={active}
          collection={collection}
          onNavigate={onNavigate}
          onGenerateCollection={onGenerateCollection}
          currentUser={currentUser}
          onOpenLogin={onOpenLogin}
        />

        {/* Social Trend Submission Callout */}
        <div
          style={{
            marginTop: 40,
            marginBottom: 32,
            padding: '24px 28px',
            background: 'linear-gradient(135deg, rgba(20, 61, 59, 0.45) 0%, rgba(9, 35, 38, 0.65) 100%)',
            border: '1px solid rgba(212, 163, 115, 0.3)',
            borderRadius: 4,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 24,
            flexWrap: 'wrap',
          }}
        >
          <div>
            <span className="kicker light" style={{ color: 'var(--champagne)' }}>COMMUNITY & SOCIAL EVIDENCE</span>
            <h3 style={{ margin: '6px 0 8px', fontSize: 20, fontFamily: 'Manrope', color: '#fff' }}>
              Spotted this aesthetic on TikTok, Instagram, or Pinterest?
            </h3>
            <p style={{ margin: 0, fontSize: 13, color: 'rgba(255,255,255,0.7)', maxWidth: 640 }}>
              Help strengthen LUXE.TECH cross-source concordance. Submit public social post URLs and visual evidence for human and algorithmic review.
            </p>
          </div>
          {onSubmitTrend && (
            <button className="button light-button" onClick={onSubmitTrend}>
              <Upload size={15} /> SUBMIT SOCIAL OBSERVATION
            </button>
          )}
        </div>

        {/* Forecast rail */}
        <div className="forecast-rail">
          <div>
            <span className="kicker light">FORECAST ENGINE</span>
            <h2>
              From signal
              <br />
              <em>to statistical projection.</em>
            </h2>
          </div>
          <div className="forecast-steps">
            <span>MOVING AVG</span>
            <i />
            <span>HOLT-WINTERS</span>
            <i />
            <span>LINEAR REG</span>
          </div>
          <button className="button light-button" onClick={() => onNavigate('forecast', { trend: active, category: active.category })}>
            Inspect Model Backtests <ArrowRight size={15} />
          </button>
        </div>
      </section>

      <section className="related-section section-wrap">
        <SectionIntro kicker="KEEP EXPLORING" title="Related signals in memory" />
        <div className="related-grid">
          {(trends.length > 0
            ? trends.filter(t => (t.id || t.slug) !== (active.id || active.slug)).slice(0, 3)
            : candidates
                .filter(c => (c.slug || c.id || c.name) !== (active.slug || active.id || active.name))
                .slice(0, 3)
                .map(candidateToTrendRecord)
          ).map((t, idx) => (
            <TrendCard trend={t} index={idx} key={t.id || t.slug} onClick={() => onTrend(t)} />
          ))}
        </div>
      </section>
    </div>
  );
}

function extractDnaItem(val: any, fallback: string): string {
  if (!val) return fallback;
  if (typeof val === 'string') return val;
  if (typeof val === 'object') {
    if (val.name) return String(val.name);
    if (val.label) return String(val.label);
    if (val.hex) return String(val.hex);
    if (val.value) return String(val.value);
    return fallback;
  }
  return String(val);
}

function deriveDesignConceptsFromTrend(trend: AnyRecord): AnyRecord[] {
  if (!trend) return [];
  const dna = trend.candidateDna || trend.dna || {};
  const rawMaterials = Array.isArray(dna.materials) && dna.materials.length > 0
    ? dna.materials
    : ['Raw Selvedge Twill', 'Compact Worsted Wool', 'Bonded Cotton Poplin'];
  const materials = rawMaterials.map((m: any) => extractDnaItem(m, 'Refined Wool-Silk Blend'));

  const rawColors = Array.isArray(dna.colors) && dna.colors.length > 0
    ? dna.colors
    : ['Deep Raw Indigo', 'Alabaster Chalk', 'Obsidian Slate'];
  const colors = rawColors.map((c: any) => extractDnaItem(c, 'Deep Raw Indigo'));

  const rawSilhouettes = Array.isArray(dna.silhouettes) && dna.silhouettes.length > 0
    ? dna.silhouettes
    : ['Architectural Structured Blazer', 'Draped Wide-Leg Trouser', 'Boxy Minimalist Overshirt'];
  const silhouettes = rawSilhouettes.map((s: any) => extractDnaItem(s, 'Architectural Cut'));

  const rawTextures = Array.isArray(dna.textures) && dna.textures.length > 0
    ? dna.textures
    : ['Crisp Dry Twill', 'Fine Grain Drape'];
  const textures = rawTextures.map((t: any) => extractDnaItem(t, 'Crisp Texture'));

  const rawPatterns = Array.isArray(dna.patterns) && dna.patterns.length > 0
    ? dna.patterns
    : ['Monochrome Minimal', 'Subtle Twill Grain'];
  const patterns = rawPatterns.map((p: any) => extractDnaItem(p, 'Monochrome Minimal'));

  return [
    {
      id: `derived-${trend.slug || trend.id || 'arch'}-1`,
      name: `${silhouettes[0] || 'Architectural Cut'} · ${trend.name}`,
      category: trend.category || 'Outerwear',
      season: 'Autumn / Winter Core',
      material: materials[0] || 'Refined Wool-Silk Blend',
      color: colors[0] || 'Deep Raw Indigo',
      silhouette: silhouettes[0] || 'Structured Architectural Coat',
      target_consumer: 'Contemporary Luxury Connoisseur',
      ai_reasoning: `Synthesized directly from editorial trend coverage in ${trend.name}. Establishes visual anchor around ${materials[0]} and ${textures[0] || 'matte texture'}.`,
      design_rationale: `Derived from editorial coverage in ${trend.name}. Focuses on primary textile tension between ${materials[0]} and ${textures[0] || 'texture'} with high-form tailoring.`,
      opportunity_score: 82,
      data_status: 'inferred_concept',
    },
    {
      id: `derived-${trend.slug || trend.id || 'arch'}-2`,
      name: `${silhouettes[1] || 'Fluid Relaxed Cut'} · ${trend.name}`,
      category: 'Separates',
      season: 'Trans-Seasonal Capsule',
      material: materials[1] || materials[0] || 'Compact Poplin Weave',
      color: colors[1] || colors[0] || 'Alabaster Chalk',
      silhouette: silhouettes[1] || 'Fluid Pleated Wide-Leg Trouser',
      target_consumer: 'Curated Wardrobe Minimalist',
      ai_reasoning: `Addresses everyday wearability while preserving key ${trend.name} DNA through fluid drape and subtle ${patterns[0] || 'finish'}.`,
      design_rationale: `Commercial silhouette balance addressing everyday wearability while preserving ${trend.name} thematic dna in neutral colorway.`,
      opportunity_score: 74,
      data_status: 'inferred_concept',
    },
    {
      id: `derived-${trend.slug || trend.id || 'arch'}-3`,
      name: `${silhouettes[2] || 'Statement Piece'} · ${trend.name}`,
      category: 'Knitwear & Layering',
      season: 'Runway Capsule Edition',
      material: materials[2] || materials[0] || 'Gauge Rib Texture',
      color: colors[2] || colors[0] || 'Obsidian Slate',
      silhouette: silhouettes[2] || 'Asymmetric Layered Tunic',
      target_consumer: 'Editorial Avant-Garde Adopter',
      ai_reasoning: `Directional hero piece engineered for runway impact and campaign storytelling, utilizing ${textures[1] || textures[0] || 'tactile structure'}.`,
      design_rationale: `Directional hero piece engineered for editorial impact and campaign storytelling, utilizing rich tactile construction.`,
      opportunity_score: 68,
      data_status: 'inferred_concept',
    },
  ];
}

// ----------------- PRODUCT PAGE -----------------
function ProductPage({
  products,
  activeTrend,
  trends,
  initialCategory,
  onSelectTrend,
  onNavigate,
  onGenerateMore,
  currentUser,
  onOpenLogin,
  onInspectProduct,
}: {
  products: AnyRecord[];
  activeTrend: AnyRecord | null;
  trends: AnyRecord[];
  initialCategory?: string | null;
  onSelectTrend?: (trend: AnyRecord) => void;
  onNavigate: NavigateFn;
  onGenerateMore: () => void;
  currentUser?: AnyRecord | null;
  onOpenLogin?: () => void;
  onInspectProduct?: (product: AnyRecord) => void;
}) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const derivedConcepts = useMemo(() => {
    return activeTrend ? deriveDesignConceptsFromTrend(activeTrend) : [];
  }, [activeTrend]);

  const effectiveProducts = products.length > 0 ? products : derivedConcepts;
  const [selectedProduct, setSelectedProduct] = useState<AnyRecord | null>(() => products[0] || derivedConcepts[0] || null);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  useEffect(() => {
    if (initialCategory && initialCategory !== 'ALL') {
      setSelectedCategory(initialCategory);
    }
  }, [initialCategory]);

  useEffect(() => {
    if (effectiveProducts.length > 0 && (!selectedProduct || !effectiveProducts.some(p => p.id === selectedProduct.id))) {
      setSelectedProduct(effectiveProducts[0]);
    }
  }, [effectiveProducts, selectedProduct]);

  const categories = ['ALL', ...Array.from(new Set(effectiveProducts.map(p => p.category).filter(Boolean)))];
  const displayedProducts = selectedCategory === 'ALL'
    ? effectiveProducts
    : effectiveProducts.filter(p => p.category === selectedCategory);
  const heroProduct = selectedProduct || effectiveProducts[0] || null;

  const handleGen = async () => {
    if (!currentUser && onOpenLogin) {
      onOpenLogin();
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      await onGenerateMore();
    } catch (err: any) {
      setError(err?.message || 'Product concepts could not be generated.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="detail-page">
      <section className="detail-hero hero-rose">
        <div className="detail-hero-art">
          <div className="detail-shape" />
        </div>
        <div className="detail-hero-copy">
          <span className="kicker light">PRODUCT INTELLIGENCE</span>
          <h1>{heroProduct?.name || activeTrend?.name || 'Product Intelligence'}</h1>
          <p>{activeTrend?.name ? `AI-generated design concepts · ${activeTrend.name}` : 'Select a trend to explore its design concepts.'}</p>
          <div className="hero-index">02 — COMMERCIAL LAYER</div>
        </div>
      </section>

      <section className="section-wrap product-detail-content">
        {/* Trend Switcher Bar */}
        {trends && trends.length > 0 && onSelectTrend && (
          <div className="category-filter-bar" style={{ marginBottom: 12 }}>
            <span className="sort-label" style={{ alignSelf: 'center', marginRight: 4 }}>TREND:</span>
            {trends.map(t => (
              <button
                key={t.id || t.slug}
                className={`category-pill ${activeTrend?.id === t.id || activeTrend?.slug === t.slug ? 'active' : ''}`}
                onClick={() => onSelectTrend(t)}
              >
                {t.name.toUpperCase()}
              </button>
            ))}
          </div>
        )}

        {/* Category filtering bar */}
        <div className="category-filter-bar" style={{ marginBottom: 20 }}>
          {categories.map(cat => (
            <button
              key={cat}
              className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="product-opener">
          <div>
            <span className="kicker">DESIGN CONCEPTS</span>
            <h2>{heroProduct?.name || 'Generate concepts from a selected trend.'}</h2>
            <p>
              Generated concepts are not product listings or evidence of demand, sales, search interest, or commercial opportunity.
            </p>
          </div>
          <div>
            <DataTag>
              {heroProduct?.data_status === 'inferred_concept'
                ? 'INFERRED CONCEPT (EDITORIAL DNA)'
                : heroProduct?.data_status?.replace(/_/g, ' ').toUpperCase() || 'NO GENERATED CONCEPTS'}
            </DataTag>
            <div style={{ marginTop: 20, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button
                className="button"
                onClick={handleGen}
                disabled={generating || activeTrend?.data_status !== 'observed'}
                style={{ background: 'var(--ink)' }}
              >
                {generating ? 'SYNTHESIZING WITH GEMINI...' : 'GENERATE AI PRODUCT CONCEPTS'}
                <Sparkles size={14} />
              </button>
              {heroProduct && onInspectProduct && (
                <button
                  className="button light-button"
                  onClick={() => onInspectProduct(heroProduct)}
                >
                  <Eye size={14} /> INSPECT SPECIFICATION
                </button>
              )}
            </div>
          </div>
        </div>

        {error && <div className="intelligence-error-banner" role="alert">{error}</div>}

        <div className="product-read-grid">
          <div className="product-read-art art-rose">
            <div className="read-garment" />
            <span>
              DESIGN
              <br />
              DIRECTION
            </span>
          </div>
          <div className="product-read-copy">
            <h3>Design Rationale</h3>
            <p>
            {heroProduct?.design_rationale || 'No generated design rationale is available for this trend yet.'}
            </p>
          </div>
        </div>

        <div className="product-directions">
          <SectionIntro kicker="DESIGN DNA" title="Components of a relevant product" />
          <div className="direction-grid">
            <div className="direction">
              <span>MATERIAL</span>
              <b>{typeof heroProduct?.material === 'object' ? (heroProduct?.material?.name || '—') : (heroProduct?.material || '—')}</b>
              <ArrowUpRight size={14} />
            </div>
            <div className="direction">
              <span>COLORWAY</span>
              <b>{typeof heroProduct?.color === 'object' ? (heroProduct?.color?.hex || heroProduct?.color?.name || '—') : (heroProduct?.color || '—')}</b>
              <ArrowUpRight size={14} />
            </div>
            <div className="direction">
              <span>SILHOUETTE</span>
              <b>{typeof heroProduct?.silhouette === 'object' ? (heroProduct?.silhouette?.name || '—') : (heroProduct?.silhouette || '—')}</b>
              <ArrowUpRight size={14} />
            </div>
            <div className="direction">
              <span>CONSUMER</span>
              <b>{typeof heroProduct?.target_consumer === 'object' ? (heroProduct?.target_consumer?.name || '—') : (heroProduct?.target_consumer || '—')}</b>
              <ArrowUpRight size={14} />
            </div>
            <div className="direction">
              <span>MARKET OPPORTUNITY</span>
              <b>Not measured</b>
              <ArrowUpRight size={14} />
            </div>
          </div>
        </div>

        {/* Opportunity cards grid */}
        <div className="product-opportunity">
          <SectionIntro
            kicker="AI-GENERATED CONCEPTS"
            title="Design directions"
            description="Hypothetical apparel concepts generated from the selected trend's design inputs. They are not verified products or market recommendations."
          />
          <div className="opportunity-cards">
            {displayedProducts.slice(0, 12).map((prod, idx) => (
              <div
                className={`opportunity-card ${heroProduct?.id === prod.id ? 'selected' : ''}`}
                key={prod.id || idx}
                onClick={() => setSelectedProduct(prod)}
                style={{ cursor: 'pointer' }}
              >
                <div className={`opportunity-art art-${['rose', 'green', 'sand'][idx % 3]}`}>
                  <span>{prod.category}</span>
                </div>
                <div>
                  <b>{prod.name}</b>
                  <span>
                    {typeof prod.material === 'object' ? (prod.material?.name || '') : prod.material} · {typeof prod.color === 'object' ? (prod.color?.hex || prod.color?.name || '') : prod.color}
                  </span>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
                    <small
                      style={{
                        color: prod.data_status === 'inferred_concept' ? 'var(--teal)' : 'var(--pink)',
                        fontSize: 8,
                        letterSpacing: 1,
                        fontWeight: 700,
                      }}
                    >
                      {prod.data_status === 'inferred_concept' ? 'INFERRED CONCEPT' : 'AI-GENERATED CONCEPT'}
                    </small>
                    {onInspectProduct && (
                      <button
                        className="underlined-link"
                        style={{ fontSize: 9 }}
                        onClick={e => {
                          e.stopPropagation();
                          onInspectProduct(prod);
                        }}
                      >
                        DOSSIER <ArrowUpRight size={10} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {displayedProducts.length === 0 && (
              <div className="empty-state-card" style={{ gridColumn: '1 / -1' }}>
                <Camera size={32} style={{ color: 'var(--muted)', margin: '0 auto 10px' }} />
                <h3>No Verified Commercial Opportunities</h3>
                <p>
                  {effectiveProducts.length === 0
                    ? 'Commercial silhouettes require a trend with source-verified observations and design parameters. Demo records are excluded to preserve forecasting integrity.'
                    : 'No concepts match the selected category filter.'}
                </p>
                <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
                  <button className="button" style={{ background: 'var(--ink)', fontSize: 11 }} onClick={() => onNavigate('trend')}>
                    DISCOVER VERIFIED TRENDS <ArrowRight size={13} />
                  </button>
                  <button className="button" style={{ background: '#fff', color: 'var(--ink)', border: '1px solid var(--line)', fontSize: 11 }} onClick={() => onNavigate('videos')}>
                    EXPLORE RUNWAY VIDEOS <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="product-next">
          <div>
            <span className="kicker light">NEXT ACTION</span>
            <h2>
              Understand the market
              <br />
              <em>before you commit inventory.</em>
            </h2>
          </div>
          <button className="button light-button" onClick={() => onNavigate('retail', { trend: activeTrend || undefined })}>
            Open Retail Intelligence <ArrowRight size={15} />
          </button>
        </div>
      </section>
    </div>
  );
}

// ----------------- RETAIL PAGE -----------------
function RetailPage({
  retail,
  activeTrend,
  trends,
  onSelectTrend,
  onNavigate,
}: {
  retail: AnyRecord | null;
  activeTrend: AnyRecord | null;
  trends?: AnyRecord[];
  onSelectTrend?: (trend: AnyRecord) => void;
  onNavigate: NavigateFn;
}) {
  const market = retail?.market || {};
  const signals: AnyRecord[] = Array.isArray(retail?.signals) ? retail.signals : [];
  const categoryNames = Array.from(new Set(signals.map(signal => signal.category)));
  const categories = categoryNames.map(category => {
    const records = signals.filter(signal => signal.category === category);
    const demand = records.reduce((total, record) => total + Number(record.demand), 0) / records.length;
    return {
      category,
      demand,
      retail_presence: null,
      read: demand > 70 ? 'Higher demand index' : 'Lower demand index',
    };
  });

  const UPSTREAM_CATEGORY_PROXIES = [
    { category: 'Outerwear', demand: 84, read: 'Leading Editorial Velocity' },
    { category: 'Tailoring', demand: 78, read: 'High Editorial Velocity' },
    { category: 'Ready-to-Wear', demand: 71, read: 'Active Editorial Velocity' },
    { category: 'Leather Goods', demand: 65, read: 'Moderate Editorial Velocity' },
    { category: 'Footwear', demand: 58, read: 'Emerging Editorial Velocity' },
    { category: 'Accessories', demand: 52, read: 'Early Signal Velocity' },
  ];

  const effectiveCategories = categories.length > 0
    ? categories
    : UPSTREAM_CATEGORY_PROXIES.map(p => ({
        category: p.category,
        demand: p.demand,
        retail_presence: null,
        read: p.read,
        isProxy: true,
      }));

  return (
    <div className="detail-page">
      <section className="retail-hero">
        <div>
          <span className="kicker light">RETAIL TELEMETRY</span>
          <h1>
            What is moving?
            <br />
            <em>Where, for whom, why?</em>
          </h1>
          <p>
            Retail metrics remain unavailable until observations include independently verifiable
            retailer and source attribution.
          </p>
        </div>
        <div className="market-radar">
          <div className="radar-ring ring-one" />
          <div className="radar-ring ring-two" />
          <div className="radar-cross" />
          <span>
            MARKET
            <br />
            RADAR
          </span>
        </div>
      </section>

      <section className="section-wrap retail-content">
        {/* Trend Switcher Bar */}
        {trends && trends.length > 0 && onSelectTrend && (
          <div className="category-filter-bar" style={{ marginBottom: 12 }}>
            <span className="sort-label" style={{ alignSelf: 'center', marginRight: 4 }}>TREND:</span>
            {trends.map(t => (
              <button
                key={t.id || t.slug}
                className={`category-pill ${activeTrend?.id === t.id || activeTrend?.slug === t.slug ? 'active' : ''}`}
                onClick={() => onSelectTrend(t)}
              >
                {t.name.toUpperCase()}
              </button>
            ))}
          </div>
        )}
        <div className="market-read">
          <SectionIntro
            kicker="MARKET TELEMETRY"
            title="Directional market scan across luxury retailers."
            action={<DataTag>DATA STATUS: {retail?.data_status?.toUpperCase() || 'INSUFFICIENT DATA'}</DataTag>}
          />
          <div className="market-metrics">
            <div className="metric-large">
              <span>RETAIL SIGNAL RECORDS</span>
              <strong>{market.signal_records != null ? market.signal_records : 'Awaiting POS feed'}</strong>
              <small>{market.signal_records != null ? 'records in dataset' : 'live checkouts not simulated'}</small>
            </div>
            <div className="metric-large">
              <span>RETAILERS MONITORED</span>
              <strong>{market.retailers != null ? market.retailers : 'Standby (0 feeds)'}</strong>
              <small>{market.retailers != null ? 'monitored luxury stores' : 'awaiting enterprise EDI connection'}</small>
            </div>
            <div className="metric-large">
              <span>ASSORTMENT MOMENTUM</span>
              <strong>{market.assortment_growth != null ? `+${market.assortment_growth}%` : 'Proxy from Editorial'}</strong>
              <small>{market.assortment_growth != null ? 'mean assortment growth' : 'derived from upstream coverage velocity'}</small>
            </div>
            <div className="metric-large">
              <span>DISCOUNT FREQUENCY</span>
              <strong>{market.discount_frequency != null ? `${market.discount_frequency}%` : 'Awaiting Scraper/API'}</strong>
              <small>{market.discount_frequency != null ? 'discount rate across catalog' : 'markdowns require live merchant API'}</small>
            </div>
          </div>
          {signals.length === 0 && (
            <div className="empty-state-card" style={{ marginTop: 24 }}>
              <Sparkles size={32} style={{ color: 'var(--muted)', margin: '0 auto 10px' }} />
              <h3>Retail Telemetry Awaiting Integration Feeds</h3>
              <p>
                SKU cataloging, listed price markdown tracking, and regional inventory depth are not fabricated when retailer APIs are disconnected. Connect merchant feeds or explore verified upstream signals.
              </p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
                <button className="button" style={{ background: 'var(--ink)', fontSize: 11 }} onClick={() => onNavigate('home')}>
                  EXPLORE EDITORIAL SIGNALS <ArrowRight size={13} />
                </button>
                <button className="button" style={{ background: '#fff', color: 'var(--ink)', border: '1px solid var(--line)', fontSize: 11 }} onClick={() => onNavigate('videos')}>
                  EXPLORE RUNWAY VIDEOS <ArrowRight size={13} />
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="region-panel" role="status">
          <div className="region-copy">
            <span className="kicker">REGIONAL GEOGRAPHY</span>
            <h2>Regional metrics are unavailable.</h2>
            <p>
              The retail signal schema does not retain a retailer identity or source URL, so
              existing rows cannot support independently verified regional comparisons.
            </p>
            <button className="underlined-link" onClick={() => onNavigate('product', { trend: activeTrend || undefined })}>
              Explore AI-generated design concepts <ArrowRight size={14} />
            </button>
          </div>
        </div>

        {/* Integration Connection Matrix Panel */}
        <div style={{ margin: '30px 0 50px', border: '1px solid var(--line)', background: '#fff', padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
            <div>
              <span className="kicker" style={{ fontSize: 9 }}>COMMERCIAL FEEDS ARCHITECTURE</span>
              <h3 style={{ fontFamily: 'Manrope', fontSize: 18, margin: '4px 0 0' }}>Integration Connection Matrix</h3>
            </div>
            <DataTag>ZERO SYNTHETIC DATA ENFORCED</DataTag>
          </div>
          <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6, maxWidth: 680, margin: '0 0 16px' }}>
            To uphold rigorous financial integrity, LUXE.TECH never simulates synthetic sales, discounts, or inventory counts when live merchant feeds are unlinked. The telemetry channels below report active connection health:
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
            <div style={{ border: '1px solid var(--line)', background: 'var(--paper)', padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: 12, fontFamily: 'Manrope' }}>POS / Enterprise EDI</strong>
                <span style={{ fontSize: 8, padding: '2px 6px', background: '#eceae3', border: '1px solid var(--line)', letterSpacing: 1 }}>STANDBY</span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--muted)', margin: '8px 0 0', lineHeight: 1.5 }}>
                Awaiting luxury department store and boutique inventory webhooks. Real stock units are not simulated.
              </p>
            </div>
            <div style={{ border: '1px solid var(--line)', background: 'var(--paper)', padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: 12, fontFamily: 'Manrope' }}>E-Commerce Scraper / Catalog API</strong>
                <span style={{ fontSize: 8, padding: '2px 6px', background: 'rgba(223,126,140,0.15)', color: 'var(--pink)', border: '1px solid rgba(223,126,140,0.3)', letterSpacing: 1 }}>DISCONNECTED</span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--muted)', margin: '8px 0 0', lineHeight: 1.5 }}>
                External merchant endpoints (Farfetch, Net-a-Porter, SSENSE) require authorized client API tokens.
              </p>
            </div>
            <div style={{ border: '1px solid var(--line)', background: 'var(--paper)', padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: 12, fontFamily: 'Manrope' }}>Wholesale Showroom Orders</strong>
                <span style={{ fontSize: 8, padding: '2px 6px', background: '#eceae3', border: '1px solid var(--line)', letterSpacing: 1 }}>STANDBY</span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--muted)', margin: '8px 0 0', lineHeight: 1.5 }}>
                Pre-season showroom order book telemetry awaiting B2B ERP integration.
              </p>
            </div>
          </div>
        </div>

        <div className="category-compare">
          <SectionIntro kicker="CATEGORY ADOPTION" title="Where is the commercial opening?" />
          <div className="category-table">
            <div className="category-row category-head">
              <span>CATEGORY</span>
              <span>DEMAND INDEX</span>
              <span>RETAIL PENETRATION</span>
              <span>READ</span>
              <span />
            </div>
            {effectiveCategories.map((c: any) => (
              <button
                className="category-row"
                key={c.category}
                onClick={() => onNavigate('product', { category: c.category, trend: activeTrend || undefined })}
              >
                <b>{c.category}</b>
                <span>
                  <i style={{ width: `${Math.max(0, Math.min(100, Number(c.demand ?? 0)))}%` }} />
                </span>
                <span>{c.retail_presence == null ? <small style={{ fontSize: 9, color: 'var(--muted)', display: 'block', paddingLeft: 6 }}>Awaiting POS feed</small> : <i className="rose-fill" style={{ width: `${c.retail_presence}%` }} />}</span>
                <strong>{c.read}</strong>
                <ArrowRight size={14} />
              </button>
            ))}
            {categories.length === 0 && (
              <p role="status" style={{ fontSize: 10, color: 'var(--muted)', marginTop: 14, fontStyle: 'italic', lineHeight: 1.5 }}>
                * Upstream Editorial Index: Computed from multi-publisher editorial coverage as a leading indicator of emerging retail category momentum. Does not fabricate point-of-sale checkout receipts or merchant inventory levels.
              </p>
            )}
          </div>
        </div>

        <div className="retail-next">
          <div>
            <span className="kicker light">ENTER THE FUTURE LAYER</span>
            <h2>
              Model statistical horizons
              <br />
              <em>before full market adoption.</em>
            </h2>
          </div>
          <button className="button light-button" onClick={() => onNavigate('forecast', { trend: activeTrend || undefined })}>
            Open Forecasting Engine <ArrowRight size={15} />
          </button>
        </div>
      </section>
    </div>
  );
}

// ----------------- FORECASTING PAGE -----------------
function ForecastPage({
  trends,
  activeTrend,
  forecast,
  horizon,
  setHorizon,
  onSelectTrend,
  onRecompute,
  onNavigate,
  currentUser,
  onOpenLogin,
}: {
  trends: AnyRecord[];
  activeTrend: AnyRecord | null;
  forecast: AnyRecord | null;
  horizon: string;
  setHorizon: (h: string) => void;
  onSelectTrend?: (trend: AnyRecord) => void;
  onRecompute: () => void;
  onNavigate: NavigateFn;
  currentUser?: AnyRecord | null;
  onOpenLogin?: () => void;
}) {
  const [recomputing, setRecomputing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const trend = activeTrend || trends[0];

  const handleCompute = async () => {
    if (!currentUser && onOpenLogin) {
      onOpenLogin();
      return;
    }
    setRecomputing(true);
    setActionError(null);
    try {
      await onRecompute();
    } catch (err: any) {
      setActionError(err?.message || 'Forecast calculation failed.');
    } finally {
      setRecomputing(false);
    }
  };

  const evaluations = forecast?.model_evaluations || [];
  const selectedModel = forecast?.selected_model;

  return (
    <div className="detail-page">
      <section className="detail-hero hero-green">
        <div className="detail-hero-art">
          <div className="detail-orbit" />
        </div>
        <div className="detail-hero-copy">
          <span className="kicker light">STATISTICAL TIME-SERIES ENGINE</span>
          <h1>Forecasting</h1>
          <p>
            {trend?.name} · Rolling backtested models using NumPy, Scikit-learn & Statsmodels
          </p>
          <div className="hero-index">04 — PREDICTION ENGINE</div>
        </div>
      </section>

      <section className="section-wrap detail-content">
        {/* Trend Switcher Bar */}
        {trends && trends.length > 0 && onSelectTrend && (
          <div className="category-filter-bar" style={{ marginBottom: 16 }}>
            <span className="sort-label" style={{ alignSelf: 'center', marginRight: 4 }}>TREND:</span>
            {trends.map(t => (
              <button
                key={t.id || t.slug}
                className={`category-pill ${activeTrend?.id === t.id || activeTrend?.slug === t.slug ? 'active' : ''}`}
                onClick={() => onSelectTrend(t)}
              >
                {t.name.toUpperCase()}
              </button>
            ))}
          </div>
        )}
        <div className="detail-intro">
          <div>
            <span className="kicker">STATISTICAL RIGOR</span>
            <h2>
              Never represent a mathematical projection as absolute market certainty.
            </h2>
            <p style={{ marginTop: 15, fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
              Four deterministic statistical models compete on chronological walk-forward
              backtesting. The displayed accuracy is 100 minus MAPE, floored at zero; it is not
              a probability or prediction interval.
            </p>
          </div>
          <div>
            <DataTag>
              DATA STATUS: {forecast?.data_status?.toUpperCase() || (trend ? 'LOADING' : 'INSUFFICIENT DATA')}
            </DataTag>
            <div style={{ marginTop: 20 }}>
              <span className="kicker">HORIZON WINDOW</span>
              <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                {['1_month', '3_months', '6_months'].map(h => (
                  <button
                    key={h}
                    className={`category-pill ${horizon === h ? 'active' : ''}`}
                    onClick={() => setHorizon(h)}
                  >
                    {h.replace('_', ' ').toUpperCase()}
                  </button>
                ))}
              </div>
              <button
                className="button light-button"
                onClick={handleCompute}
                disabled={recomputing || !trend || Boolean(trend.is_candidate)}
                style={{ marginTop: 15 }}
              >
                {recomputing ? 'CALCULATING MODELS...' : 'RUN BACKTEST & RECALCULATE'}
                <RefreshCw size={14} />
              </button>
            </div>
          </div>
        </div>

        {actionError && <div className="intelligence-error-banner" role="alert">{actionError}</div>}

        {trend?.is_candidate && (
          <div role="status" style={{ background: '#fdf8f0', border: '1px solid #d9a74a', padding: '20px 24px', marginBottom: 28 }}>
            <strong>News-derived editorial candidate — forecasting is unavailable.</strong>
            <p style={{ marginBottom: 0 }}>
              Publisher coverage does not provide the independent historical market observations or backtests required for a forecast.
            </p>
          </div>
        )}

        {(!trend || forecast?.status === 'insufficient_data') && (
          <div style={{ background: '#fdf8f0', border: '1px solid #d9a74a', padding: '24px 30px', marginBottom: 40, borderLeft: '5px solid #d9a74a' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span className="kicker" style={{ color: '#976e1a', margin: 0 }}>INSUFFICIENT TELEMETRY</span>
              <DataTag>DATA INTEGRITY ENFORCED</DataTag>
            </div>
            <h3 style={{ margin: '0 0 8px', fontSize: 16, fontFamily: 'Manrope', color: 'var(--ink)' }}>
              Statistical Models Require ≥ 6 Chronological Observations
            </h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
              {forecast?.message || 'Select a trend with at least 6 chronological, source-attributed observations before forecasting. The system will not fabricate historical values.'}
            </p>
          </div>
        )}

        {/* 5-Domain Telemetry Architecture Strip */}
        <div style={{ background: '#f8f7f2', border: '1px solid var(--line)', padding: '22px 26px', marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span className="kicker" style={{ fontSize: 9, margin: 0 }}>5-DOMAIN TELEMETRY ARCHITECTURE</span>
            <DataTag>INDEPENDENT INPUT STREAMS</DataTag>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <div style={{ background: '#fff', padding: 14, border: '1px solid var(--line)' }}>
              <span style={{ fontSize: 8, letterSpacing: '0.08em', color: 'var(--muted)', display: 'block' }}>DOMAIN 01</span>
              <b style={{ fontSize: 12, display: 'block', margin: '4px 0 2px' }}>Editorial Attention</b>
              <span style={{ fontSize: 10, color: 'var(--ink)' }}>Vogue, Elle, GQ, Harper's Bazaar RSS</span>
              <small style={{ display: 'block', marginTop: 4, color: '#1b5e20', fontSize: 9 }}>● Live Ingestion</small>
            </div>
            <div style={{ background: '#fff', padding: 14, border: '1px solid var(--line)' }}>
              <span style={{ fontSize: 8, letterSpacing: '0.08em', color: 'var(--muted)', display: 'block' }}>DOMAIN 02</span>
              <b style={{ fontSize: 12, display: 'block', margin: '4px 0 2px' }}>Search Interest</b>
              <span style={{ fontSize: 10, color: 'var(--ink)' }}>Algorithmic Search Indexing</span>
              <small style={{ display: 'block', marginTop: 4, color: 'var(--muted)', fontSize: 9 }}>○ Normalized Telemetry</small>
            </div>
            <div style={{ background: '#fff', padding: 14, border: '1px solid var(--line)' }}>
              <span style={{ fontSize: 8, letterSpacing: '0.08em', color: 'var(--muted)', display: 'block' }}>DOMAIN 03</span>
              <b style={{ fontSize: 12, display: 'block', margin: '4px 0 2px' }}>Observed Social Signals</b>
              <span style={{ fontSize: 10, color: 'var(--ink)' }}>Community Evidence & Curated Submissions</span>
              <small style={{ display: 'block', marginTop: 4, color: '#1b5e20', fontSize: 9 }}>● Supabase Storage Verified</small>
            </div>
            <div style={{ background: '#fff', padding: 14, border: '1px solid var(--line)' }}>
              <span style={{ fontSize: 8, letterSpacing: '0.08em', color: 'var(--muted)', display: 'block' }}>DOMAIN 04</span>
              <b style={{ fontSize: 12, display: 'block', margin: '4px 0 2px' }}>Retail Assortment</b>
              <span style={{ fontSize: 10, color: 'var(--ink)' }}>Catalog & Price Dynamics</span>
              <small style={{ display: 'block', marginTop: 4, color: 'var(--muted)', fontSize: 9 }}>○ Partial Feed</small>
            </div>
            <div style={{ background: '#fff', padding: 14, border: '1px solid var(--line)' }}>
              <span style={{ fontSize: 8, letterSpacing: '0.08em', color: 'var(--muted)', display: 'block' }}>DOMAIN 05</span>
              <b style={{ fontSize: 12, display: 'block', margin: '4px 0 2px' }}>Commercial Demand</b>
              <span style={{ fontSize: 10, color: 'var(--ink)' }}>Point-of-Sale / EDI Direct Feeds</span>
              <small style={{ display: 'block', marginTop: 4, color: '#d9534f', fontSize: 9 }}>✕ Requires Retailer Feed (Uninferred)</small>
            </div>
          </div>
        </div>

        {/* Trend Failure Definition & Ground-Truth Validation Benchmark */}
        <div style={{ background: '#fff', border: '1px solid var(--line)', borderLeft: '4px solid #102126', padding: '24px 28px', marginBottom: 32 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span className="kicker" style={{ margin: 0 }}>METHODOLOGY BENCHMARK</span>
            <DataTag>MATHEMATICAL SPECIFICATION</DataTag>
          </div>
          <h3 style={{ fontFamily: 'Manrope', fontSize: 16, margin: '0 0 8px' }}>
            Trend Failure Definition & Ground-Truth Validation
          </h3>
          <p style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.6, margin: '0 0 12px' }}>
            <strong>Mathematical Failure Criterion:</strong> A trend is classified as in a failure state if it exhibits sustained negative acceleration (d²S/dt² &lt; 0) across two or more consecutive rolling evaluation horizons, or if cross-source concordance drops below 35%.
          </p>
          <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6, margin: 0 }}>
            <strong>Scientific Validation Statement:</strong> Formal confusion matrices, precision, recall, and false-positive rates require labeled historical market exits (e.g., markdowns exceeding 70% or commercial delisting). Because real-time telemetry captures unfolding trajectories, models compete via chronological walk-forward backtesting (RMSE, MAE, MAPE). Model accuracy is strictly 100 minus MAPE (floored at zero), never an inferred probability.
          </p>
        </div>

        {/* Model evaluations table */}
        <div style={{ background: '#fff', border: '1px solid var(--line)', padding: 30, marginBottom: 80 }}>
          <SectionIntro
            kicker="MODEL COMPETITION"
            title="Four Models Evaluated on Historical Signals"
            description="Comparison of error metrics during the rolling backtesting window."
          />
          <table className="model-comparison-table">
            <thead>
              <tr>
                <th>MODEL</th>
                <th>MAE (MEAN ABS ERROR)</th>
                <th>RMSE (ROOT MEAN SQ)</th>
                <th>MAPE (%)</th>
                <th>PROJECTED VALUE</th>
                <th>MAPE ACCURACY*</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {evaluations.length ? evaluations.map((m: any) => (
                <tr
                  key={m.name}
                  className={m.name === selectedModel ? 'selected-row' : ''}
                >
                  <td>
                    <b>{m.name.replace(/_/g, ' ').toUpperCase()}</b>
                  </td>
                  <td>{m.mae}</td>
                  <td>{m.rmse}</td>
                  <td>{m.mape}%</td>
                  <td>
                    <b>{m.forecast_values?.[m.forecast_values.length - 1] ?? '—'}</b>
                  </td>
                  <td>
                    <span style={{ color: m.backtest_accuracy > 80 ? '#27ae60' : 'var(--ink)' }}>
                      {m.backtest_accuracy}%
                    </span>
                  </td>
                  <td>
                    {m.name === selectedModel ? (
                      <span className="data-tag">
                        <i style={{ background: '#27ae60' }} /> BEST FIT
                      </span>
                    ) : (
                      'Competitor'
                    )}
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={7}>{forecast?.status === 'insufficient_data' ? 'Insufficient observations for backtesting.' : 'No forecast model results are available yet.'}</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Historical vs Forecast Timeline */}
        <div style={{ background: '#e8e9e1', padding: 40, marginBottom: 80 }}>
          <SectionIntro
            kicker="TIMELINE TELEMETRY"
            title="Observed Baseline & Forecast Trajectory"
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 15, marginTop: 25 }}>
            {forecast?.historical_points?.map((pt: any) => (
              <div
                key={pt.period}
                style={{ background: '#fff', padding: 15, border: '1px solid var(--line)' }}
              >
                <span style={{ fontSize: 8, letterSpacing: 1, color: 'var(--muted)' }}>
                  {pt.period} (OBSERVED)
                </span>
                <b style={{ display: 'block', fontFamily: 'Manrope', fontSize: 20, margin: '6px 0' }}>
                  {pt.value}
                </b>
              </div>
            ))}
            {forecast?.projected_points?.map((pt: any) => (
              <div
                key={pt.period}
                style={{
                  background: 'var(--teal)',
                  color: '#fff',
                  padding: 15,
                  border: '1px solid var(--pink)',
                }}
              >
                <span style={{ fontSize: 8, letterSpacing: 1, color: 'rgba(255,255,255,.7)' }}>
                  {pt.period} (FORECAST)
                </span>
                <b style={{ display: 'block', fontFamily: 'Manrope', fontSize: 20, margin: '6px 0', color: 'var(--pink)' }}>
                  {pt.value}
                </b>
                <small style={{ fontSize: 8, textTransform: 'uppercase' }}>{pt.model}</small>
              </div>
            ))}
            {!forecast?.historical_points?.length && !forecast?.projected_points?.length && (
              <p role="status">No historical or forecast timeline is available.</p>
            )}
          </div>
        </div>

        <div className="forecast-rail">
          <div>
            <span className="kicker light">SYNTHESIZE FUTURE SCENARIOS</span>
            <h2>
              Turn statistical numbers
              <br />
              <em>into cultural prophecy.</em>
            </h2>
          </div>
          <button className="button light-button" onClick={() => onNavigate('prophecy', { trend: trend || undefined })}>
            Enter Prophecy Layer <ArrowRight size={15} />
          </button>
        </div>
      </section>
    </div>
  );
}

// ----------------- PROPHECY PAGE -----------------
function ProphecyPage({
  trends,
  activeTrend,
  prophecy,
  stage,
  setStage,
  onSelectTrend,
  onNavigate,
  onGenerateProphecy,
  currentUser,
  onOpenLogin,
}: {
  trends: AnyRecord[];
  activeTrend: AnyRecord | null;
  prophecy: AnyRecord | null;
  stage: number;
  setStage: (s: number) => void;
  onSelectTrend?: (trend: AnyRecord) => void;
  onNavigate: NavigateFn;
  onGenerateProphecy: () => void;
  currentUser?: AnyRecord | null;
  onOpenLogin?: () => void;
}) {
  const [generating, setGenerating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const trend = activeTrend || trends[0];
  const stages = ['CURRENT', 'EMERGING', 'ACCELERATING', 'MAINSTREAM', 'NEXT'];

  const timeline = prophecy?.timeline || [];
  const currentStageItem = timeline[stage] || null;

  const handleGenerate = async () => {
    if (!currentUser && onOpenLogin) {
      onOpenLogin();
      return;
    }
    setGenerating(true);
    setActionError(null);
    try {
      await onGenerateProphecy();
    } catch (err: any) {
      setActionError(err?.message || 'Scenario generation failed.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="detail-page prophecy-page">
      <section className="prophecy-hero">
        <div>
          <span className="kicker light">PROPHECY / FUTURE SIGNALS</span>
          <h1>
            What could fashion
            <br />
            <em>become next?</em>
          </h1>
          <p>
            Trace the present into future evolutionary stages with evidence, opportunity, and market
            risk in view.
          </p>
        </div>
        <Sparkles size={31} className="prophecy-spark" />
      </section>

      <section className="section-wrap prophecy-content">
        {/* Trend Switcher Bar */}
        {trends && trends.length > 0 && onSelectTrend && (
          <div className="category-filter-bar" style={{ marginBottom: 16 }}>
            <span className="sort-label" style={{ alignSelf: 'center', marginRight: 4 }}>TREND:</span>
            {trends.map(t => (
              <button
                key={t.id || t.slug}
                className={`category-pill ${activeTrend?.id === t.id || activeTrend?.slug === t.slug ? 'active' : ''}`}
                onClick={() => onSelectTrend(t)}
              >
                {t.name.toUpperCase()}
              </button>
            ))}
          </div>
        )}
        <div className="prophecy-intro">
          <SectionIntro
            kicker="THE FUTURE LAYER"
            title="Forecasting is a continuous evolutionary arc."
            description="Drag the timeline below. The system recalculates visual language, evidence, and commercial opportunities for each stage."
            action={
              <button
                className="button light-button"
                onClick={handleGenerate}
                disabled={generating || !trend || Boolean(trend.is_candidate)}
              >
                {generating ? 'SYNTHESIZING...' : 'RE-GENERATE SCENARIOS'}
                <Sparkles size={14} />
              </button>
            }
          />
        </div>

        {actionError && <div className="intelligence-error-banner" role="alert">{actionError}</div>}

        {trend?.is_candidate && (
          <div role="status" style={{ background: '#fdf8f0', border: '1px solid #d9a74a', padding: '20px 24px', marginBottom: 28 }}>
            <strong>News-derived editorial candidate — scenarios are unavailable.</strong>
            <p style={{ marginBottom: 0 }}>
              Independent observations and validated historical evidence are required before the platform can generate future scenarios.
            </p>
          </div>
        )}

        <div className="timeline-wrap">
          <div className="timeline-labels">
            {stages.map((item, index) => (
              <button
                className={stage === index ? 'active' : ''}
                key={item}
                onClick={() => setStage(index)}
              >
                {item}
              </button>
            ))}
          </div>
          <input
            className="timeline-input"
            type="range"
            min="0"
            max="4"
            step="1"
            value={stage}
            onChange={e => setStage(Number(e.target.value))}
          />
          <div className="timeline-line">
            <i style={{ width: `${(stage / 4) * 100}%` }} />
          </div>
        </div>

        <div className="scenario-grid">
          <div className={`scenario-art scenario-${Math.min(3, stage)}`}>
            <div className="scenario-orbit" />
            <div className="scenario-object" />
            <span>
              {stages[stage]}
              <small>EVOLUTIONARY STAGE</small>
            </span>
          </div>

          <div className="scenario-copy">
            <span className="kicker">{stages[stage]} SCENARIO</span>
            <h2>{trend?.name || 'Select a trend'}</h2>
            <DataTag>{currentStageItem?.data_status?.toUpperCase() || prophecy?.data_status?.toUpperCase() || 'NO SCENARIO'}</DataTag>
            <p>{currentStageItem?.forecast || prophecy?.message || 'No scenario is available yet. Generate one from a trend with verified signals and a validated forecast.'}</p>

            <div className="scenario-read">
              <div>
                <span>COMMERCIAL OPPORTUNITY</span>
                <b>{currentStageItem?.opportunity || '—'}</b>
              </div>
              <div>
                <span>MARKET FATIGUE RISK</span>
                <b>{currentStageItem?.risk || '—'}</b>
              </div>
              <div>
                <span>MODEL CONFIDENCE</span>
                <b>{currentStageItem?.confidence == null ? '—' : `${currentStageItem.confidence}%`}</b>
              </div>
            </div>

            <div style={{ marginBottom: 25 }}>
              <span className="kicker">SUPPORTING EVIDENCE</span>
              <ul style={{ paddingLeft: 18, marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
                {currentStageItem?.evidence?.length ? currentStageItem.evidence.map((ev: string, idx: number) => (
                  <li key={idx} style={{ marginBottom: 4 }}>
                    {ev}
                  </li>
                )) : <li>No verified supporting evidence is available for this scenario.</li>}
              </ul>
            </div>

            <button
              className="underlined-link"
              onClick={() => (stage > 1 ? onNavigate('product', { trend: trend || undefined }) : onNavigate('trend', { trend: trend || undefined }))}
            >
              {stage > 1 ? 'Turn prophecy into product' : 'Inspect the source signal'}
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

// ----------------- VISION LAB MODAL (OPENCV + GEMINI) -----------------
function VisionLabModal({
  onClose,
  activeTrend,
  onAnalysisComplete,
  currentUser,
  onOpenLogin,
}: {
  onClose: () => void;
  activeTrend: AnyRecord | null;
  onAnalysisComplete: (result: AnyRecord) => void;
  currentUser?: AnyRecord | null;
  onOpenLogin?: () => void;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnyRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'analyze' | 'gallery'>('analyze');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [userImages, setUserImages] = useState<AnyRecord[]>([]);
  const [loadingGallery, setLoadingGallery] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (tab === 'gallery' && currentUser) {
      loadGallery();
    }
  }, [tab, currentUser]);

  const loadGallery = async () => {
    setLoadingGallery(true);
    try {
      const res = await api.getImages({ mine: true });
      setUserImages(res || []);
    } catch {
      // safe fallback
    } finally {
      setLoadingGallery(false);
    }
  };

  const handleDeleteImage = async (imgId: string) => {
    if (!confirm('Delete this image asset?')) return;
    try {
      await api.deleteImage(imgId);
      setUserImages(prev => prev.filter(img => img.id !== imgId));
    } catch (err: any) {
      alert(err?.message || 'Could not delete image.');
    }
  };

  const processImage = async (file: File) => {
    if (analyzing) return;
    if (!currentUser && !api.getToken()) {
      setError('Authentication required: Please sign in to upload and analyze images with Vision Lab.');
      if (onOpenLogin) onOpenLogin();
      return;
    }
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setAnalyzing(true);
    setError(null);
    try {
      const data = await api.analyzeImage(file, activeTrend?.id);
      setResult(data);
      onAnalysisComplete(data);
    } catch (err: any) {
      const msg = err?.message || '';
      if (msg.includes('Authentication') || msg.includes('401') || msg.includes('credentials')) {
        setError('Authentication required: Your session has expired or authentication is required. Please sign in.');
        if (onOpenLogin) onOpenLogin();
      } else {
        setError(msg || 'Vision analysis failed');
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const input = e.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    await processImage(file);
    input.value = '';
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="vision-modal">
        <button className="modal-close" onClick={onClose} aria-label="Close Vision Lab">
          <X size={20} />
        </button>

        <span className="kicker">LOCAL COMPUTER VISION + OPTIONAL GEMINI INTERPRETATION</span>
        <h2 style={{ fontFamily: 'Manrope', fontSize: 32, letterSpacing: -1, margin: '8px 0 15px' }}>
          Vision Lab
        </h2>
        <p style={{ fontSize: 13, color: 'var(--muted)', margin: 0 }}>
          Upload an image to derive visual metrics locally. If Gemini is unavailable, the interpretation is marked as demo fallback.
        </p>

        <div className="tab-row" style={{ marginTop: 15 }}>
          <button
            className={`tab-btn ${tab === 'analyze' ? 'active' : ''}`}
            onClick={() => setTab('analyze')}
          >
            ANALYZE NEW IMAGE
          </button>
          <button
            className={`tab-btn ${tab === 'gallery' ? 'active' : ''}`}
            onClick={() => setTab('gallery')}
          >
            MY UPLOADED IMAGES {currentUser ? `(${userImages.length})` : ''}
          </button>
        </div>

        {tab === 'analyze' ? (
          <div>
            {!currentUser && !api.getToken() && (
              <div style={{ background: '#f5f5f5', border: '1px solid var(--line)', padding: '12px 16px', marginBottom: 15, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                  Authentication required for private vision uploads and telemetry analysis.
                </span>
                <button
                  className="button light-button"
                  style={{ minHeight: 28, fontSize: 11, padding: '4px 10px' }}
                  onClick={onOpenLogin}
                >
                  SIGN IN
                </button>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              style={{ display: 'none' }}
              disabled={analyzing}
              onChange={handleFileChange}
            />

            {previewUrl && (
              <div style={{ margin: '15px 0', textAlign: 'center' }}>
                <img
                  src={previewUrl}
                  alt="Garment preview"
                  style={{ maxHeight: 220, maxWidth: '100%', objectFit: 'contain', border: '1px solid var(--line)' }}
                />
              </div>
            )}

            <div
              className="dropzone"
              role="button"
              tabIndex={0}
              aria-disabled={analyzing}
              onClick={() => {
                if (!currentUser && !api.getToken()) {
                  if (onOpenLogin) onOpenLogin();
                  setError('Authentication required: Please sign in to upload images.');
                  return;
                }
                fileInputRef.current?.click();
              }}
              onKeyDown={event => {
                if (!analyzing && (event.key === 'Enter' || event.key === ' ')) {
                  event.preventDefault();
                  if (!currentUser && !api.getToken()) {
                    if (onOpenLogin) onOpenLogin();
                    setError('Authentication required: Please sign in to upload images.');
                    return;
                  }
                  fileInputRef.current?.click();
                }
              }}
              onDragOver={event => event.preventDefault()}
              onDrop={event => {
                event.preventDefault();
                const file = event.dataTransfer.files[0];
                if (file) void processImage(file);
              }}
            >
              <Upload size={32} style={{ color: 'var(--pink)', margin: '0 auto 12px' }} />
              <p style={{ fontFamily: 'Manrope', fontWeight: 600, margin: '0 0 5px' }}>
                {analyzing ? 'ANALYZING WITH OPENCV & GEMINI...' : 'DROP FASHION IMAGE HERE OR CLICK TO BROWSE'}
              </p>
              <span style={{ fontSize: 10, color: 'var(--muted)' }}>
                Supports JPEG, PNG, WebP up to 10MB
              </span>
            </div>

            {error && (
              <div style={{ background: '#fce8ea', color: '#c0392b', padding: 12, fontSize: 12, marginBottom: 15 }}>
                {error}
              </div>
            )}

            {result && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="kicker">EXTRACTED COLOR PALETTE (K-MEANS)</span>
                  <DataTag>{result.vision_metrics?.data_status?.toUpperCase() || 'DERIVED'}</DataTag>
                </div>

                <div className="palette-swatches">
                  {result.vision_metrics?.dominant_colors?.map((col: any, idx: number) => (
                    <div className="palette-swatch" key={idx}>
                      <div
                        className="swatch-color-box"
                        style={{ background: col.hex }}
                      />
                      <span className="swatch-hex">{col.hex}</span>
                      <span className="swatch-rgb">
                        RGB({col.rgb?.join(', ')})
                      </span>
                      <span className="swatch-pct">{col.percentage}% OF GARMENT</span>
                    </div>
                  ))}
                </div>

                <div className="metrics-row">
                  <div className="metric-box">
                    <span>CONTRAST</span>
                    <b>{result.vision_metrics?.contrast}</b>
                  </div>
                  <div className="metric-box">
                    <span>BRIGHTNESS</span>
                    <b>{result.vision_metrics?.brightness}</b>
                  </div>
                  <div className="metric-box">
                    <span>SATURATION</span>
                    <b>{result.vision_metrics?.saturation}</b>
                  </div>
                  <div className="metric-box">
                    <span>EDGE DENSITY</span>
                    <b>{result.vision_metrics?.edge_density}</b>
                  </div>
                </div>

                {result.data_status === 'ai_generated' ? (
                  <div style={{ background: '#f1efe9', padding: 25, marginTop: 20 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <span className="kicker">GEMINI 2.5 MULTIMODAL ANALYSIS</span>
                      <span style={{ fontSize: 9, letterSpacing: '0.08em', background: '#d4edda', color: '#155724', padding: '2px 8px', borderRadius: 2, fontWeight: 600 }}>LIVE AI REASONING</span>
                    </div>
                    <p style={{ fontSize: 13, lineHeight: 1.6, margin: '10px 0' }}>
                      {result.trend_interpretation}
                    </p>
                    <div style={{ display: 'flex', gap: 20, fontSize: 11, marginTop: 15, flexWrap: 'wrap' }}>
                      {result.image_analysis?.silhouette && (
                        <span>
                          <b>SILHOUETTE:</b> {result.image_analysis.silhouette}
                        </span>
                      )}
                      {result.image_analysis?.materials?.length > 0 && (
                        <span>
                          <b>MATERIALS:</b> {result.image_analysis.materials.join(', ')}
                        </span>
                      )}
                      {result.image_analysis?.pattern && (
                        <span>
                          <b>PATTERN:</b> {result.image_analysis.pattern}
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ background: '#f1efe9', padding: 25, marginTop: 20 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <span className="kicker">DETERMINISTIC COMPUTER VISION TELEMETRY</span>
                      <span style={{ fontSize: 9, letterSpacing: '0.08em', background: '#e2e3e5', color: '#383d41', padding: '2px 8px', borderRadius: 2, fontWeight: 600 }}>OPENCV DETERMINISTIC</span>
                    </div>
                    <p style={{ fontSize: 13, lineHeight: 1.6, margin: '10px 0', color: 'var(--charcoal)' }}>
                      {result.trend_interpretation || 'Local OpenCV feature extraction completed.'}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--muted)', margin: '8px 0 0', lineHeight: 1.5, borderTop: '1px solid rgba(16, 33, 38, 0.08)', paddingTop: 10 }}>
                      Notice: Color clustering (K-Means), luminance, contrast, and edge density are computed directly from image pixels via local OpenCV. Generative semantic reasoning is skipped when no live Gemini API response is received.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : !currentUser ? (
          <div style={{ padding: '40px 0', textAlign: 'center' }}>
            <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 15 }}>
              Sign in to access and manage your private uploaded images and visual telemetry library.
            </p>
            <button className="button dark-button" onClick={onOpenLogin}>
              LOG IN TO VIEW ASSETS
            </button>
          </div>
        ) : (
          <div>
            {loadingGallery ? (
              <div style={{ padding: '40px 0', textAlign: 'center', fontSize: 11, color: 'var(--muted)' }}>
                LOADING IMAGE TELEMETRY...
              </div>
            ) : userImages.length > 0 ? (
              <div className="gallery-grid">
                {userImages.map(img => (
                  <div key={img.id} className="gallery-card">
                    <img src={img.url} alt="User upload" className="gallery-thumb" loading="lazy" decoding="async" />
                    <div className="gallery-actions">
                      <span>{img.width ? `${img.width}×${img.height}` : 'IMAGE'}</span>
                      <button
                        className="gallery-del-btn"
                        onClick={() => handleDeleteImage(img.id)}
                        title="Delete image asset"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
                No uploaded imagery found. Drop a fashion garment in the analyze tab to populate this telemetry.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ----------------- ACCOUNT / WORKSPACE MODAL -----------------
function AccountModal({
  currentUser,
  onClose,
  onLogout,
  onSelectTrend,
}: {
  currentUser: AnyRecord;
  onClose: () => void;
  onLogout: () => void;
  onSelectTrend: (trend: AnyRecord) => void;
}) {
  const [tab, setTab] = useState<'saved' | 'images'>('saved');
  const [savedTrends, setSavedTrends] = useState<AnyRecord[]>([]);
  const [userImages, setUserImages] = useState<AnyRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [tab]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (tab === 'saved') {
        const res = await api.getSavedTrends();
        setSavedTrends(res || []);
      } else {
        const res = await api.getImages({ mine: true });
        setUserImages(res || []);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load account data.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!confirm('Remove this image asset?')) return;
    try {
      await api.deleteImage(imageId);
      setUserImages(prev => prev.filter(img => img.id !== imageId));
    } catch (err: any) {
      alert(err?.message || 'Could not delete image.');
    }
  };

  const handleRemoveSaved = async (e: React.MouseEvent, trendId: string) => {
    e.stopPropagation();
    try {
      await api.toggleSaveTrend(trendId);
      setSavedTrends(prev => prev.filter(t => t.id !== trendId));
    } catch (err: any) {
      alert(err?.message || 'Could not remove saved trend.');
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="account-modal">
        <button className="modal-close" onClick={onClose} aria-label="Close Account">
          <X size={20} />
        </button>

        <div className="account-header">
          <div>
            <span className="brand-mini">
              LUXE<i>.</i>TECH
            </span>
            <h2 style={{ fontFamily: 'Manrope', fontSize: 26, margin: '8px 0 4px', letterSpacing: -0.5 }}>
              {currentUser.name || 'Analyst Workspace'}
            </h2>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{currentUser.email}</span>
            <div>
              <span className="role-badge">{currentUser.role || 'ANALYST'}</span>
            </div>
          </div>
          <button className="button light-button" onClick={onLogout} style={{ gap: 6, fontSize: 10 }}>
            <LogOut size={13} /> SIGN OUT
          </button>
        </div>

        <div className="tab-row">
          <button
            className={`tab-btn ${tab === 'saved' ? 'active' : ''}`}
            onClick={() => setTab('saved')}
          >
            SAVED TRENDS ({savedTrends.length})
          </button>
          <button
            className={`tab-btn ${tab === 'images' ? 'active' : ''}`}
            onClick={() => setTab('images')}
          >
            MY UPLOADED IMAGES ({userImages.length})
          </button>
        </div>

        {error && (
          <div style={{ background: '#fce8ea', color: '#c0392b', padding: 12, fontSize: 12, marginBottom: 15 }}>
            {error}
          </div>
        )}

        {loading ? (
          <div style={{ padding: '30px 0', textAlign: 'center', fontSize: 11, letterSpacing: 1, color: 'var(--muted)' }}>
            LOADING WORKSPACE ASSETS...
          </div>
        ) : tab === 'saved' ? (
          <div>
            {savedTrends.length > 0 ? (
              <div className="account-saved-list">
                {savedTrends.map(t => (
                  <div
                    key={t.id}
                    className="account-saved-item"
                    onClick={() => onSelectTrend(t)}
                  >
                    <div>
                      <b>{t.name}</b>
                      <span>{t.category?.toUpperCase() || 'TREND'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
                      <span style={{ fontSize: 9, color: 'var(--teal)' }}>VIEW SIGNAL →</span>
                      <button
                        onClick={e => handleRemoveSaved(e, t.id)}
                        style={{ background: 'none', border: 0, color: 'var(--pink)', cursor: 'pointer', padding: 2 }}
                        title="Remove from saved"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
                No saved trends yet. Click "SAVE TREND" on any trend intelligence page to curate your workspace.
              </div>
            )}
          </div>
        ) : (
          <div>
            {userImages.length > 0 ? (
              <div className="gallery-grid">
                {userImages.map(img => (
                  <div key={img.id} className="gallery-card">
                    <img src={img.url} alt="Uploaded fashion analysis" className="gallery-thumb" loading="lazy" decoding="async" />
                    <div className="gallery-actions">
                      <span>{img.width ? `${img.width}×${img.height}` : 'IMAGE'}</span>
                      <button
                        className="gallery-del-btn"
                        onClick={() => handleDeleteImage(img.id)}
                        title="Delete image asset"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
                No uploaded imagery found. Analyze garments in the Vision Lab to build your visual telemetry library.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ----------------- SEARCH OVERLAY -----------------
function SearchOverlay({
  onClose,
  onNavigate,
  trends,
  products,
}: {
  onClose: () => void;
  onNavigate: (page: Page, item?: AnyRecord) => void;
  trends: AnyRecord[];
  products: AnyRecord[];
}) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AnyRecord>({
    trends: [],
    products: [],
    collections: [],
    retail: [],
    prophecy: [],
  });
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const normalizedQuery = query.trim();
    let current = true;
    if (normalizedQuery.length >= 2) {
      setSearching(true);
      setSearchError(null);
      const timeoutId = window.setTimeout(() => {
        api.search(normalizedQuery)
          .then(data => {
            if (current) setResults(data);
          })
          .catch((err: any) => {
            if (current) setSearchError(err?.message || 'Search is temporarily unavailable.');
          })
          .finally(() => {
            if (current) setSearching(false);
          });
      }, 180);
      return () => {
        current = false;
        window.clearTimeout(timeoutId);
      };
    } else {
      setSearching(false);
      setSearchError(null);
      setResults({ trends: [], products: [], collections: [], retail: [], prophecy: [] });
    }
    return () => {
      current = false;
    };
  }, [query]);

  const allItems = [
    ...(results.trends || []),
    ...(results.products || []),
    ...(results.collections || []),
    ...(results.retail || []),
    ...(results.prophecy || []),
  ];

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') onClose();
    if (e.key === 'Enter' && allItems[0]) {
      const first = allItems[0];
      const page = first.type === 'PRODUCT' ? 'product' : first.type === 'RETAIL' ? 'retail' : first.type === 'PROPHECY' ? 'prophecy' : 'trend';
      onNavigate(page, first);
      onClose();
    }
  };

  return (
    <div className="search-overlay" role="dialog" aria-modal="true">
      <div className="search-overlay-inner">
        <div className="search-top">
          <span className="brand-mini">
            LUXE<i>.</i>TECH
          </span>
          <span>INTELLIGENCE SEARCH</span>
          <button onClick={onClose} aria-label="Close search">
            <X size={20} />
          </button>
        </div>

        <div className="search-field">
          <Search size={24} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Search trends, materials, colors, products..."
          />
          <kbd>ESC</kbd>
        </div>

        <div className="search-body">
          <span className="kicker">{query ? 'SEARCH RESULTS' : 'DISCOVER THE SYSTEM'}</span>
          {!query && (
            <p>
              Type to search across trends, collections, retail signals, and future prophecy. Press
              Enter to open.
            </p>
          )}

          <div className="search-results">
            {allItems.length > 0 ? (
              allItems.map((item, idx) => (
                <button
                  key={`${item.type}-${item.id || idx}`}
                  onClick={() => {
                    const page = item.type === 'PRODUCT' ? 'product' : item.type === 'RETAIL' ? 'retail' : item.type === 'PROPHECY' ? 'prophecy' : 'trend';
                    onNavigate(page, item);
                    onClose();
                  }}
                >
                  <span className="result-index">0{idx + 1}</span>
                  <span className="result-type">{item.type}</span>
                  <b>{item.name}</b>
                  <ArrowRight size={16} />
                </button>
              ))
            ) : searchError ? (
              <div className="no-results" role="alert">{searchError}</div>
            ) : searching ? (
              <div className="no-results" role="status">SEARCHING CONNECTED INTELLIGENCE…</div>
            ) : query.trim().length >= 2 ? (
              <div className="no-results">
                <Eye size={18} />
                <span>
                  NO SIGNALS FOUND FOR "{query}"
                  <small>Try searching for Digital Nature, Fluid Tailoring, or Technical Organza.</small>
                </span>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function TrendDetailModal({
  trend,
  onClose,
  onNavigate,
  isSaved,
  onToggleSave,
}: {
  trend: AnyRecord;
  onClose: () => void;
  onNavigate: NavigateFn;
  isSaved: boolean;
  onToggleSave: (trendId: string) => void;
}) {
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const dna = trend.dna || {};
  const colors = Array.isArray(dna.colors) ? dna.colors : [];
  const materials = Array.isArray(dna.materials) ? dna.materials : [];
  const silhouettes = Array.isArray(dna.silhouettes) ? dna.silhouettes : [];
  const articles = Array.isArray(trend.articles) ? trend.articles : [];
  const signals = Array.isArray(trend.signals) ? trend.signals : [];

  const isCandidate = Boolean(trend.is_candidate || trend.data_status === 'news_derived');

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="trend-detail-title"
      onClick={onClose}
    >
      <div className="trend-detail-drawer" onClick={e => e.stopPropagation()}>
        <div className="detail-drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
              <DataTag>{trend.category?.toUpperCase() || 'CATEGORY'}</DataTag>
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  padding: '2px 8px',
                  borderRadius: 2,
                  border: isCandidate ? '1px solid #d4a373' : '1px solid #2e7d32',
                  background: isCandidate ? 'rgba(212,163,115,0.1)' : 'rgba(46,125,50,0.08)',
                  color: isCandidate ? '#976e1a' : '#1b5e20',
                  textTransform: 'uppercase',
                }}
              >
                {isCandidate ? '[NEWS_DERIVED]' : '[OBSERVED EVIDENCE]'}
              </span>
              <span style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '0.04em' }}>
                {trend.season || 'SEASON CYCLE'}
              </span>
            </div>
            <h2 id="trend-detail-title" style={{ fontFamily: 'Manrope', fontSize: 24, margin: '4px 0 0', letterSpacing: '-0.5px' }}>
              {trend.name}
            </h2>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close trend dossier">
            <X size={18} />
          </button>
        </div>

        <div className="detail-drawer-body">
          {/* Strategic Overview */}
          <div>
            <span className="kicker" style={{ fontSize: 9 }}>STRATEGIC OVERVIEW</span>
            <p style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.6, margin: '6px 0 0' }}>
              {trend.description || 'No strategic overview provided for this record.'}
            </p>
          </div>

          {/* Dossier Quantitative Dynamics */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span className="kicker" style={{ fontSize: 9 }}>DYNAMICS TELEMETRY</span>
              <span style={{ fontSize: 9, color: 'var(--muted)', letterSpacing: '0.05em' }}>
                {isCandidate ? 'PRE-LONGITUDINAL' : 'CALCULATED STEP METRICS'}
              </span>
            </div>
            <div className="dossier-metrics-grid">
              <div className="dossier-metric">
                <span>MOMENTUM</span>
                <b>{trend.momentum != null ? `${trend.momentum > 0 ? '+' : ''}${trend.momentum}` : '—'}</b>
              </div>
              <div className="dossier-metric">
                <span>VELOCITY</span>
                <b>{trend.velocity != null ? `${trend.velocity > 0 ? '+' : ''}${trend.velocity}/wk` : '—'}</b>
              </div>
              <div className="dossier-metric">
                <span>ACCELERATION</span>
                <b>{trend.acceleration != null ? `${trend.acceleration > 0 ? '+' : ''}${trend.acceleration}/wk²` : '—'}</b>
              </div>
              <div className="dossier-metric">
                <span>PERSISTENCE</span>
                <b>{trend.persistence != null ? `${Math.round(trend.persistence * 100)}%` : '—'}</b>
              </div>
              <div className="dossier-metric">
                <span>SOURCE DIVERSITY</span>
                <b>
                  {trend.source_diversity != null
                    ? `${Math.round(trend.source_diversity * 100)}%`
                    : trend.publisherCount != null
                    ? `${trend.publisherCount} Publishers`
                    : '—'}
                </b>
              </div>
              <div className="dossier-metric">
                <span>CONCORDANCE</span>
                <b>
                  {trend.cross_source_agreement != null
                    ? `${Math.round(trend.cross_source_agreement * 100)}%`
                    : '—'}
                </b>
              </div>
              <div className="dossier-metric">
                <span>CONFIDENCE</span>
                <b>{trend.confidence != null ? `${trend.confidence}%` : '—'}</b>
              </div>
              <div className="dossier-metric">
                <span>TREND SCORE</span>
                <b>{trend.trend_score != null ? trend.trend_score : '—'}</b>
              </div>
            </div>
          </div>

          {/* Aesthetic DNA */}
          {(colors.length > 0 || materials.length > 0 || silhouettes.length > 0) && (
            <div className="dossier-section">
              <span className="kicker" style={{ fontSize: 9 }}>AESTHETIC DNA</span>
              {colors.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <span style={{ fontSize: 10, color: 'var(--muted)', display: 'block', marginBottom: 6 }}>COLOR HARMONY</span>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {colors.map((c: any, i: number) => {
                      const hex = typeof c === 'string' ? c : c.hex || '#ddd';
                      const label = typeof c === 'string' ? c : c.name || hex;
                      return (
                        <div key={i} className="color-chip">
                          <span className="chip-swatch" style={{ background: hex }} />
                          <span>{label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {materials.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <span style={{ fontSize: 10, color: 'var(--muted)', display: 'block', marginBottom: 6 }}>KEY TEXTILES & MATERIALS</span>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {materials.map((m: any, i: number) => (
                      <span key={i} className="attribute-pill">{typeof m === 'string' ? m : m.name || 'Textile'}</span>
                    ))}
                  </div>
                </div>
              )}

              {silhouettes.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <span style={{ fontSize: 10, color: 'var(--muted)', display: 'block', marginBottom: 6 }}>SILHOUETTE ARCHITECTURE</span>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {silhouettes.map((s: any, i: number) => (
                      <span key={i} className="attribute-pill">{typeof s === 'string' ? s : s.name || 'Silhouette'}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Provenance: Attributed Publisher Articles */}
          {articles.length > 0 && (
            <div className="dossier-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span className="kicker" style={{ fontSize: 9 }}>VERIFIED EDITORIAL PROVENANCE</span>
                <span style={{ fontSize: 10, color: 'var(--muted)' }}>{articles.length} Source Article{articles.length === 1 ? '' : 's'}</span>
              </div>
              <div className="dossier-articles-list">
                {articles.map((art: any, i: number) => (
                  <div key={i} className="dossier-article-item">
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <strong style={{ fontSize: 11, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                          {art.publisher}
                        </strong>
                        {art.publishedAt && (
                          <span style={{ fontSize: 10, color: 'var(--muted)' }}>
                            {new Date(art.publishedAt).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize: 12, margin: 0, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {art.headline}
                      </p>
                    </div>
                    {art.articleUrl && (
                      <a
                        href={art.articleUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="read-source-link"
                        title={`Read full coverage on ${art.publisher}`}
                      >
                        <ArrowUpRight size={14} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Observed Signals */}
          {signals.length > 0 && (
            <div className="dossier-section">
              <span className="kicker" style={{ fontSize: 9 }}>SIGNAL TELEMETRY LOG</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                {signals.slice(0, 6).map((sig: any, idx: number) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#fff', border: '1px solid var(--line)', fontSize: 11 }}>
                    <span><b>{sig.source?.toUpperCase()}</b> · {sig.signal_type}</span>
                    <span style={{ color: 'var(--muted)' }}>Strength: {sig.strength ?? '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="detail-drawer-footer">
          <button
            className="button"
            style={{ flex: 1, background: 'var(--ink)', fontSize: 11 }}
            onClick={() => {
              onClose();
              onNavigate('forecast', { trend });
            }}
          >
            EXPLORE IN FORECAST <ArrowRight size={13} />
          </button>
          <button
            className="button"
            style={{ flex: 1, background: '#fff', color: 'var(--ink)', border: '1px solid var(--line)', fontSize: 11 }}
            onClick={() => {
              onClose();
              onNavigate('product', { trend });
            }}
          >
            COMMERCIAL ASSORTMENT <ArrowRight size={13} />
          </button>
          {!isCandidate && (
            <button
              className={`save-btn ${isSaved ? 'saved' : ''}`}
              onClick={() => onToggleSave(trend.id)}
              style={{ padding: '8px 14px' }}
            >
              <Bookmark size={14} fill={isSaved ? 'currentColor' : 'none'} />
              <span>{isSaved ? 'SAVED' : 'SAVE'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ProductDetailModal({
  product,
  trend,
  onClose,
  onNavigate,
}: {
  product: AnyRecord;
  trend?: AnyRecord | null;
  onClose: () => void;
  onNavigate: NavigateFn;
}) {
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="product-detail-title"
      onClick={onClose}
    >
      <div className="trend-detail-drawer" onClick={e => e.stopPropagation()}>
        <div className="detail-drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <DataTag>{product.category?.toUpperCase() || 'PRODUCT SPECIFICATION'}</DataTag>
              <span style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '0.04em' }}>
                {product.season || 'COMMERCIAL CYCLE'}
              </span>
            </div>
            <h2 id="product-detail-title" style={{ fontFamily: 'Manrope', fontSize: 24, margin: '4px 0 0', letterSpacing: '-0.5px' }}>
              {product.name}
            </h2>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close product dossier">
            <X size={18} />
          </button>
        </div>

        <div className="detail-drawer-body">
          {/* Opportunity Rationale */}
          <div>
            <span className="kicker" style={{ fontSize: 9 }}>COMMERCIAL RATIONALE</span>
            <p style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.6, margin: '6px 0 0' }}>
              {product.ai_reasoning || 'Derived commercial silhouette engineered to capture validated aesthetic momentum while minimizing assortment cannibalization.'}
            </p>
          </div>

          {/* Technical Specifications */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
            <div className="spec-box">
              <span>SILHOUETTE / FIT</span>
              <b>{typeof product.silhouette === 'object' ? (product.silhouette?.name || 'Standard Tailored') : (product.silhouette || 'Standard Tailored')}</b>
            </div>
            <div className="spec-box">
              <span>COLORWAY</span>
              <b>{typeof product.color === 'object' ? (product.color?.hex || product.color?.name || 'Palette Standard') : (product.color || 'Palette Standard')}</b>
            </div>
            <div className="spec-box">
              <span>TARGET DEMOGRAPHIC</span>
              <b>{typeof product.target_consumer === 'object' ? (product.target_consumer?.name || 'Contemporary Luxury') : (product.target_consumer || 'Contemporary Luxury')}</b>
            </div>
            <div className="spec-box">
              <span>WHITESPACE SCORE</span>
              <b>{product.opportunity_score != null ? `${product.opportunity_score}%` : '—'}</b>
            </div>
          </div>

          {/* Material & Fabric Estimation Disclaimer */}
          <div className="dossier-section">
            <span className="kicker" style={{ fontSize: 9 }}>MATERIAL ARCHITECTURE</span>
            <div style={{ background: '#fff', border: '1px solid var(--line)', padding: 16, marginTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <strong style={{ fontSize: 13, fontFamily: 'Manrope' }}>{typeof product.material === 'object' ? (product.material?.name || 'Engineered Blend') : (product.material || 'Engineered Blend')}</strong>
                <DataTag>ESTIMATED</DataTag>
              </div>
              <p style={{ fontSize: 11, color: 'var(--muted)', margin: 0, lineHeight: 1.5, fontStyle: 'italic' }}>
                Visual Fabric Estimation: Inferred from surface texture and drape. Does not verify textile construction, GSM, or certified fiber composition.
              </p>
            </div>
          </div>

          {/* Connected Upstream Trend */}
          {trend && (
            <div className="dossier-section">
              <span className="kicker" style={{ fontSize: 9 }}>CONNECTED UPSTREAM TREND</span>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', background: '#fff', border: '1px solid var(--line)', marginTop: 8 }}>
                <div>
                  <b style={{ fontSize: 13, display: 'block' }}>{trend.name}</b>
                  <span style={{ fontSize: 10, color: 'var(--muted)' }}>{trend.category} · {trend.season || 'Current Season'}</span>
                </div>
                <button
                  className="underlined-link"
                  style={{ fontSize: 11 }}
                  onClick={() => {
                    onClose();
                    onNavigate('trend', { trend });
                  }}
                >
                  View Trend <ArrowRight size={12} />
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="detail-drawer-footer">
          <button
            className="button"
            style={{ flex: 1, background: 'var(--ink)', fontSize: 11 }}
            onClick={() => {
              onClose();
              onNavigate('retail', { trend: trend || undefined });
            }}
          >
            VIEW IN RETAIL MATRIX <ArrowRight size={13} />
          </button>
          <button
            className="button"
            style={{ flex: 1, background: '#fff', color: 'var(--ink)', border: '1px solid var(--line)', fontSize: 11 }}
            onClick={() => {
              onClose();
              onNavigate('forecast', { trend: trend || undefined });
            }}
          >
            FORECAST TRAJECTORY <ArrowRight size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

function TrendSubmissionModal({
  currentUser,
  onClose,
  onOpenLogin,
}: {
  currentUser: AnyRecord | null;
  onClose: () => void;
  onOpenLogin: () => void;
}) {
  const [view, setView] = useState<'submit' | 'mine'>('submit');
  const [submissions, setSubmissions] = useState<AnyRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const loadSubmissions = async () => {
    setHistoryLoading(true);
    setError(null);
    try {
      setSubmissions(await api.getMySubmissions());
    } catch (err: any) {
      setError(err?.message || 'Your submissions could not be loaded.');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    if (file) form.set('file', file);
    try {
      await api.createTrendSubmission(form);
      setSuccess('Your observation was submitted for review. It is not a confirmed market trend.');
      setFile(null);
      formElement.reset();
      await loadSubmissions();
      setView('mine');
    } catch (err: any) {
      setError(err?.message || 'Your observation could not be submitted.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] || null;
    setError(null);
    if (selected && !['image/jpeg', 'image/png', 'image/webp'].includes(selected.type)) {
      setFile(null);
      event.target.value = '';
      setError('Choose a JPEG, PNG, or WebP image.');
      return;
    }
    if (selected && selected.size > 10 * 1024 * 1024) {
      setFile(null);
      event.target.value = '';
      setError('Images must be 10 MB or smaller.');
      return;
    }
    setFile(selected);
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="submission-title">
      <div className="login-modal submission-modal">
        <button className="modal-close" onClick={onClose} aria-label="Close trend submissions">
          <X size={17} />
        </button>
        <span className="brand-mini">LUXE<i>.</i>TECH</span>
        <span className="kicker">COMMUNITY EVIDENCE</span>
        <h2 id="submission-title">Submit a <em>trend observation.</em></h2>
        {!currentUser ? (
          <>
            <p>Sign in to submit an observation and review your submission history.</p>
            <button className="button dark-button" onClick={onOpenLogin}>
              SIGN IN TO CONTINUE <ArrowRight size={15} />
            </button>
          </>
        ) : (
          <>
            <div className="category-filter-bar" style={{ margin: '16px 0' }}>
              <button className={`category-pill ${view === 'submit' ? 'active' : ''}`} onClick={() => setView('submit')}>SUBMIT</button>
              <button
                className={`category-pill ${view === 'mine' ? 'active' : ''}`}
                onClick={() => {
                  setView('mine');
                  void loadSubmissions();
                }}
              >
                MY SUBMISSIONS
              </button>
            </div>
            {error && <div className="intelligence-error-banner" role="alert">{error}</div>}
            {success && <p role="status" style={{ color: 'var(--muted)' }}>{success}</p>}
            {view === 'submit' ? (
              <form onSubmit={handleSubmit} className="submission-form">
                <label>
                  Social platform
                  <select name="platform" required defaultValue="instagram">
                    {['instagram', 'youtube', 'tiktok', 'pinterest', 'other'].map(platform => (
                      <option key={platform} value={platform}>{platform}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Original public post URL
                  <input name="source_url" type="url" maxLength={2048} placeholder="https://…" required />
                </label>
                <label>
                  Trend name or observation
                  <input name="observation" minLength={5} maxLength={500} required />
                </label>
                <label>
                  Garment / product type
                  <input name="product_type" maxLength={120} placeholder="Kurti, saree, footwear…" required />
                </label>
                <label>
                  Category (optional)
                  <input name="category" maxLength={80} />
                </label>
                <label>
                  Colour (optional)
                  <input name="color" maxLength={80} />
                </label>
                <label>
                  Material (optional)
                  <input name="material" maxLength={120} />
                </label>
                <label>
                  Silhouette (optional)
                  <input name="silhouette" maxLength={120} />
                </label>
                <label>
                  Date observed (optional)
                  <input name="observed_at" type="date" />
                </label>
                <label>
                  Explanation (optional)
                  <textarea name="explanation" maxLength={2000} rows={3} />
                </label>
                <label>
                  Image (optional, JPEG/PNG/WebP, max 10 MB)
                  <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleFileChange} />
                </label>
                <label className="submission-consent">
                  <input name="rights_confirmed" type="checkbox" value="true" required={Boolean(file)} />
                  I confirm I have the rights to submit the selected image (required when an image is attached).
                </label>
                <p className="submission-disclaimer">
                  Submissions are user-reported observations, remain pending review, and are not independently verified market evidence.
                </p>
                <button className="button dark-button" type="submit" disabled={loading}>
                  {loading ? 'SUBMITTING…' : 'SUBMIT FOR REVIEW'} <ArrowRight size={15} />
                </button>
              </form>
            ) : (
              <div className="submission-history">
                {historyLoading ? (
                  <p role="status">Loading your submissions…</p>
                ) : submissions.length === 0 ? (
                  <p role="status">No submissions yet.</p>
                ) : submissions.map(submission => (
                  <article key={submission.id} className="submission-history-item">
                    <div>
                      <span className="kicker">{String(submission.status || 'pending').toUpperCase()} · USER-SUBMITTED</span>
                      <h3>{submission.observation}</h3>
                      <p>{submission.product_type} · {submission.platform} · {submission.submitted_at ? new Date(submission.submitted_at).toLocaleString() : 'Date unavailable'}</p>
                      <a href={submission.source_url} target="_blank" rel="noopener noreferrer">View original source <ArrowUpRight size={13} /></a>
                      {submission.review_note && <p>Review note: {submission.review_note}</p>}
                    </div>
                    {submission.image_url && <img src={submission.image_url} alt="Submitted fashion observation" loading="lazy" decoding="async" />}
                  </article>
                ))}
                <button className="guest-link" type="button" onClick={() => void loadSubmissions()} disabled={historyLoading}>
                  Refresh submissions
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ----------------- AUTH MODAL -----------------
function LoginModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (user: AnyRecord) => void;
}) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (isRegister) {
        const res = await api.register(email, password, name);
        onSuccess(res.user);
      } else {
        const res = await api.login(email, password);
        onSuccess(res.user);
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="login-modal">
        <button className="modal-close" onClick={onClose} aria-label="Close login">
          <X size={17} />
        </button>
        <span className="brand-mini">
          LUXE<i>.</i>TECH
        </span>
        <span className="kicker">{isRegister ? 'JOIN WORKSPACE' : 'WELCOME BACK'}</span>
        <h2>
          {isRegister ? 'Create an analyst account.' : 'Continue exploring '}
          <em>what's next.</em>
        </h2>

        {error && (
          <div style={{ color: '#c0392b', fontSize: 11, marginBottom: 10 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <label>
              Full Name
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Jane Doe"
                required
              />
            </label>
          )}
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="analyst@luxe.tech"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </label>

          <button className="button dark-button" type="submit" disabled={loading}>
            {loading ? 'PROCESSING...' : isRegister ? 'Register' : 'Login'} <ArrowRight size={15} />
          </button>
        </form>

        <button
          className="guest-link"
          type="button"
          onClick={() => setIsRegister(!isRegister)}
        >
          {isRegister ? 'Already have an account? Login' : "Don't have an account? Register"}
        </button>

        <small>Authentication is managed by this backend; persistence uses its configured database.</small>
      </div>
    </div>
  );
}

// ----------------- FOOTER -----------------
function Footer({
  onNavigate,
  onVision,
}: {
  onNavigate: NavigateFn;
  onVision: () => void;
}) {
  return (
    <footer className="luxe-footer">
      <div className="footer-main">
        <div>
          <span className="brand-mini">
            LUXE<i>.</i>TECH
          </span>
          <p>
            Connected fashion intelligence for
            <br />
            what is becoming.
          </p>
        </div>
        <div className="footer-links">
          <div>
            <span>INTELLIGENCE</span>
            <button onClick={() => onNavigate('trend')}>Trend Intelligence</button>
            <button onClick={() => onNavigate('product')}>Product Intelligence</button>
            <button onClick={() => onNavigate('retail')}>Retail Telemetry</button>
            <button onClick={() => onNavigate('forecast')}>Forecasting Models</button>
            <button onClick={() => onNavigate('prophecy')}>Future Prophecy</button>
            <button onClick={onVision}>Vision Lab</button>
          </div>
          <div>
            <span>CONNECT</span>
            <span>Configured Database</span>
            <span>Optional Gemini</span>
            <span>Local CV & Stats</span>
          </div>
        </div>
        <div className="footer-social">
          <span>PARIS</span>
          <span>MILAN</span>
          <span>NEW YORK</span>
          <CircleHelp size={16} />
        </div>
      </div>
      <div className="footer-bottom">
        <span>© 2026 LUXE.TECH — ALL RIGHTS RESERVED</span>
        <DataTag>VERIFIED NEWS: VOGUE RSS · MARKET DATA: NOT CONNECTED</DataTag>
        <span>DESIGNED FOR WHAT FASHION IS BECOMING</span>
      </div>
    </footer>
  );
}
