import React, { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Activity, MapPin, Calendar, Building } from "lucide-react";
import { buildApiUrl, API_CONFIG, getApiBaseUrl } from "@/config/api";

interface FloatData {
  float_id: number;
  pi_name: string;
  institution: string;
  deployment_date: string;
  deployment_lat: number;
  deployment_lon: number;
  project_name: string;
  data_center: string;
  latest_lat?: number;
  latest_lon?: number;
  latest_date?: string;
  is_active?: boolean;
}

const extractLatest = (details: any) => {
  const toNum = (v: any): number | undefined => {
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string") {
      const n = parseFloat(v);
      if (Number.isFinite(n)) return n;
    }
    return undefined;
  };
  const pickNum = (o: any, keys: string[]): number | undefined => {
    for (const k of keys) {
      const v = o?.[k];
      const n = toNum(v);
      if (n != null) return n;
    }
    return undefined;
  };
  const pickDate = (o: any, keys: string[]): string | undefined => {
    for (const k of keys) {
      const v = o?.[k];
      if (typeof v === "string" && !Number.isNaN(Date.parse(v))) return v;
      if (typeof v === "number") {
        const d = new Date(v);
        if (!Number.isNaN(+d)) return d.toISOString();
      }
    }
    return undefined;
  };

  const nestedPositions = [
    "position",
    "latest_position",
    "last_position",
    "current_position",
    "most_recent",
    "last_known_position"
  ];

  // Top-level picks, including direct lat/lon/latitude/longitude
  let lat = pickNum(details, ["current_lat", "latest_lat", "last_lat", "lat", "latitude"]);
  let lon = pickNum(details, ["current_lon", "latest_lon", "last_lon", "lon", "longitude"]);

  for (const np of nestedPositions) {
    if (lat == null) lat = pickNum(details?.[np], ["lat", "latitude"]);
    if (lon == null) lon = pickNum(details?.[np], ["lon", "longitude"]);
  }

  let date = pickDate(details, ["latest_date", "last_profile_date", "last_observation_date", "date"]);
  for (const np of nestedPositions) {
    if (!date) date = pickDate(details?.[np], ["date", "time", "timestamp"]);
  }

  // Fallback: positions array (use last)
  if ((lat == null || lon == null || !date) && Array.isArray(details?.positions) && details.positions.length) {
    const last = details.positions[details.positions.length - 1];
    if (lat == null) lat = pickNum(last, ["lat", "latitude"]);
    if (lon == null) lon = pickNum(last, ["lon", "longitude"]);
    if (!date) date = pickDate(last, ["date", "time", "timestamp"]);
  }

  // Fallback: profiles array (pick most recent by date)
  if ((lat == null || lon == null || !date) && Array.isArray(details?.profiles)) {
    const candidates = details.profiles
      .map((p: any) => p?.date || p?.time || p?.timestamp)
      .filter((d: any) => (typeof d === "string" && !Number.isNaN(Date.parse(d))) || typeof d === "number");
    if (candidates.length) {
      const normalized = candidates.map((d: any) => (typeof d === "number" ? new Date(d).toISOString() : d));
      const maxDate = normalized.reduce((a: string, b: string) => (new Date(a) > new Date(b) ? a : b));
      date = date || maxDate;
      const latestProfile = details.profiles.find((p: any) => (p?.date || p?.time || p?.timestamp) === maxDate) || details.profiles[0];
      if (lat == null) lat = pickNum(latestProfile, ["lat", "latitude"]);
      if (lon == null) lon = pickNum(latestProfile, ["lon", "longitude"]);
    }
  }

  return { lat, lon, date } as { lat?: number; lon?: number; date?: string };
};

const sameDay = (a?: string, b?: string) => {
  if (!a || !b) return false;
  const da = new Date(a);
  const db = new Date(b);
  if (isNaN(+da) || isNaN(+db)) return false;
  return da.getUTCFullYear() === db.getUTCFullYear() && da.getUTCMonth() === db.getUTCMonth() && da.getUTCDate() === db.getUTCDate();
};

const moved = (aLat?: number, aLon?: number, bLat?: number, bLon?: number) => {
  if (![aLat, aLon, bLat, bLon].every((v) => typeof v === "number" && Number.isFinite(v as number))) return false;
  const dLat = Math.abs((aLat as number) - (bLat as number));
  const dLon = Math.abs((aLon as number) - (bLon as number));
  return dLat > 1e-4 || dLon > 1e-4;
};

const tryFetchDetails = async (floatId: number) => {
  const base = getApiBaseUrl().replace(/\/$/, "");
  const candidates = [
    `${base}${API_CONFIG.ENDPOINTS.FLOAT_DETAILS}/${floatId}`,
    buildApiUrl(API_CONFIG.ENDPOINTS.FLOAT_DETAILS, { float_id: String(floatId) }),
    `${base}${API_CONFIG.ENDPOINTS.FLOATS}/${floatId}`,
    buildApiUrl(API_CONFIG.ENDPOINTS.FLOATS, { float_id: String(floatId) }),
    buildApiUrl(API_CONFIG.ENDPOINTS.FLOATS, { id: String(floatId) }),
  ];
  for (const url of candidates) {
    try {
      const r = await fetch(url);
      if (r.ok) return await r.json();
    } catch {}
  }
  return null;
};

export const FloatOverview = () => {
  const [floats, setFloats] = useState<FloatData[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    const fetchFloats = async () => {
      try {
        const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.FLOATS, { limit: '6' }));
        if (response.ok) {
          const data = await response.json();
          const baseFloats: FloatData[] = data.floats || [];

          const enriched = await Promise.all(
            baseFloats.map(async (f) => {
              try {
                const details = await tryFetchDetails(f.float_id);
                const latest = details ? extractLatest(details || {}) : {};
                const latest_lat = (latest as any).lat ?? f.deployment_lat;
                const latest_lon = (latest as any).lon ?? f.deployment_lon;
                const latest_date = (latest as any).date ?? f.deployment_date;

                const active = Boolean(
                  (latest_date && !sameDay(latest_date, f.deployment_date)) ||
                  moved(latest_lat, latest_lon, f.deployment_lat, f.deployment_lon)
                );

                return {
                  ...f,
                  latest_lat,
                  latest_lon,
                  latest_date,
                  is_active: active,
                } as FloatData;
              } catch {
                return { ...f, is_active: false } as FloatData;
              }
            })
          );

          setFloats(enriched);
          
          const countResponse = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.QUERY), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: "how many floats" })
          });
          if (countResponse.ok) {
            const countData = await countResponse.json();
            setTotalCount(countData.data_count || 0);
          }
        }
      } catch (error) {
        console.error('Failed to fetch floats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchFloats();
  }, []);

  const activeFloats = useMemo(() => floats.filter(f => f.is_active), [floats]);

  if (loading) {
    return (
      <Card className="shadow-ocean">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-primary" />
            <span>Active Float Network</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-ocean">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-primary" />
            <span>Active Float Network</span>
          </CardTitle>
          <Badge variant="secondary" className="text-lg px-3 py-1">
            {activeFloats.length} Active • {totalCount} Total
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {floats.map((float_data) => {
            const lat = float_data.latest_lat ?? float_data.deployment_lat;
            const lon = float_data.latest_lon ?? float_data.deployment_lon;
            const dateStr = float_data.latest_date || float_data.deployment_date;
            const cardBorder = float_data.is_active ? "border-l-success" : "border-l-muted";
            return (
              <Card key={float_data.float_id} className={`border-l-4 ${cardBorder} hover:shadow-glow transition-smooth`}>
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-lg">Float {float_data.float_id}</h3>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {float_data.project_name}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={`text-xs ${float_data.is_active ? "border-success text-success" : "border-muted-foreground text-muted-foreground"}`}
                      >
                        {float_data.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Building className="h-4 w-4" />
                      <span>{float_data.institution}</span>
                    </div>

                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <MapPin className="h-4 w-4" />
                      <span>
                        {Number.isFinite(lat) && Number.isFinite(lon) ? `${(lat as number).toFixed(2)}°, ${(lon as number).toFixed(2)}°` : 'Unknown'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>
                        {dateStr ? new Date(dateStr).toLocaleDateString() : 'Unknown'}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2">
                    <p className="text-sm font-medium">PI: {float_data.pi_name}</p>
                    <p className="text-xs text-muted-foreground">
                      Data Center: {float_data.data_center}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
