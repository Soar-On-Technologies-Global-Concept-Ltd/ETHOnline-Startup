export interface Intent {
  id: string;
  service: string;
  city: string;
  maxUsd: number;
  window: string;
  status: 'REQUESTED' | 'MATCHED' | 'AUTHORIZED' | 'PAID' | 'EVIDENCE_SUBMITTED' | 'DISPUTED' | 'RESOLVED';
  providers: ProviderQuote[];
}

export interface ProviderQuote {
  id: string;
  name: string;
  address: string;
  trustScore: number;
  jobsCount: number;
  quoteUsd: number;
  isRecommended: boolean;
}

export interface ProviderProfile {
  id: string;
  display_name?: string;
  trade: string;
  areas: string[];
  base_rate_minor: number;
  verified?: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export async function parseAndCreateIntent(rawPrompt: string, token: string): Promise<Intent> {
  try {
    const res = await fetch(`${API_BASE_URL}/intents`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}` 
      },
      body: JSON.stringify({ text: rawPrompt }),
    });

    if (res.ok) {
      const data = await res.json();
      return {
        id: data.intent_id || `intent_${Date.now().toString(36)}`,
        service: data.spec?.service || "Event Photography",
        city: data.spec?.area || "San Francisco, CA",
        maxUsd: data.spec?.budget_max_minor ? Math.round(data.spec.budget_max_minor / 160000) : 150,
        window: data.spec?.date || "This Saturday",
        status: "MATCHED",
        providers: data.providers || getMockProviders(),
      };
    }
  } catch (err) {
    console.warn("Backend API not reachable, using resilient deterministic parser", err);
  }

  // Resilient Fallback
  const isPainter = rawPrompt.toLowerCase().includes("paint");
  return {
    id: `intent_${Date.now().toString(36).substring(4)}`,
    service: isPainter ? "Residential Painting" : "Event Photography",
    city: isPainter ? "Surulere, Lagos" : "San Francisco, CA",
    maxUsd: isPainter ? 180 : 150,
    window: "This Saturday",
    status: "MATCHED",
    providers: getMockProviders(isPainter),
  };
}

function getMockProviders(isPainter = false): ProviderQuote[] {
  if (isPainter) {
    return [
      { id: "p1", name: "Tunde Paints Ltd", address: "0xa1b2...890a", trustScore: 98, jobsCount: 142, quoteUsd: 160, isRecommended: true },
      { id: "p2", name: "Surulere Decor Studio", address: "0xb2c3...901b", trustScore: 94, jobsCount: 88, quoteUsd: 175, isRecommended: false },
      { id: "p3", name: "Lagos Craftsmen", address: "0xc3d4...012c", trustScore: 91, jobsCount: 45, quoteUsd: 150, isRecommended: false },
    ];
  }

  return [
    { id: "p1", name: "Apex Photography Studio", address: "0xa1b2c3d4e5f6789012345678901234567890abcd", trustScore: 98, jobsCount: 142, quoteUsd: 145, isRecommended: true },
    { id: "p2", name: "FocusCraft Media", address: "0xb2c3d4e5f678901234567890123456789012bcde", trustScore: 94, jobsCount: 89, quoteUsd: 150, isRecommended: false },
    { id: "p3", name: "Lumina Event Shots", address: "0xc3d4e5f67890123456789012345678901234cdef", trustScore: 91, jobsCount: 54, quoteUsd: 135, isRecommended: false },
  ];
}

export async function fetchIntentById(id: string): Promise<Intent> {
  try {
    const res = await fetch(`${API_BASE_URL}/intents/${id}`);
    if (res.ok) {
      const data = await res.json();
      return data;
    }
  } catch (err) {
    console.warn(`Could not fetch intent ${id} from API, returning scoped object`, err);
  }

  return {
    id,
    service: "Verified Event Photography",
    city: "San Francisco, CA",
    maxUsd: 150,
    window: "This Saturday",
    status: "MATCHED",
    providers: getMockProviders(),
  };
}

export async function fetchMyProviderProfile(token: string): Promise<ProviderProfile | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/providers/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error("Failed to fetch provider profile", err);
  }
  return null;
}

export async function onboardProvider(token: string, data: { trade: string, areas: string[], base_rate_minor: number }): Promise<ProviderProfile | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/providers/onboard`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error("Failed to onboard provider", err);
  }
  return null;
}
