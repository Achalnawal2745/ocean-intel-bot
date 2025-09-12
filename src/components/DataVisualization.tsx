import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapVisualization } from "./visualizations/MapVisualization";
import { ProfileChart } from "./visualizations/ProfileChart";
import { TimeseriesChart } from "./visualizations/TimeseriesChart";
import { DataTable } from "./visualizations/DataTable";
import { TrendingUp, Map, BarChart3, Database } from "lucide-react";
import { buildApiUrl } from "@/config/api";
import { useToast } from "@/hooks/use-toast";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface DataVisualizationProps {
  result: any;
}

export const DataVisualization: React.FC<DataVisualizationProps> = ({ result }) => {
  const { toast } = useToast();

  // Filters state
  const [tsStart, setTsStart] = useState<string>("");
  const [tsEnd, setTsEnd] = useState<string>("");
  const [profileParam, setProfileParam] = useState<string | undefined>(undefined);
  const [invertY, setInvertY] = useState<boolean | undefined>(undefined);

  // Compute timeseries bounds
  const tsBounds = useMemo(() => {
    if (!result?.viz || !(result.viz.kind === 'timeseries' || result.viz.kind === 'temporal')) return null as null | { min: Date; max: Date; minStr: string; maxStr: string };
    const xKey = result.viz.spec?.x || 'timestamp';
    let min = new Date(8640000000000000);
    let max = new Date(-8640000000000000);
    for (const d of Array.isArray(result.data) ? result.data : []) {
      const t = new Date(d?.[xKey]);
      if (t.toString() === 'Invalid Date') continue;
      if (t < min) min = t;
      if (t > max) max = t;
    }
    if (max < min) return null;
    const toStr = (dt: Date) => dt.toISOString().slice(0, 10);
    return { min, max, minStr: toStr(min), maxStr: toStr(max) };
  }, [result]);

  // Initialize/refresh filters when result changes
  useEffect(() => {
    if (!result?.viz) return;
    if (result.viz.kind === "profile" || result.viz.kind === "profile_comparison") {
      const rows = Array.isArray(result.data) ? result.data : [];
      const first = rows.find((r: any) => r && typeof r === 'object') || {};
      const keys = Object.keys(first);
      const yGuess = result.viz.spec?.y || (keys.includes('depth_m') ? 'depth_m' : keys.includes('pressure') ? 'pressure' : (keys.find(k => /depth|press/i.test(k)) || 'depth_m'));
      const preferred = ['temperature','salinity','pressure'];
      const numericKeys = keys.filter(k => typeof first[k] === 'number' || (rows.some((r:any)=> Number.isFinite(Number(r?.[k])))));
      const ordered = [...preferred.filter(k => keys.includes(k)), ...numericKeys.filter(k => !preferred.includes(k))].filter(k => k !== yGuess);
      const xOpts: string[] = result.viz.spec?.x_opts || ordered;
      const initialParam = result.viz.spec?.x || xOpts[0];
      setProfileParam(initialParam);
      const invertDefault = result.viz.spec?.invert_y ?? (yGuess === 'depth_m' || /depth|press/i.test(String(yGuess)));
      setInvertY(invertDefault);
      // Patch result.viz.spec to include inferred y/x_opts for downstream renderers
      (result.viz.spec ||= {}).y = yGuess;
      (result.viz.spec ||= {}).x_opts = xOpts;
      if (initialParam) (result.viz.spec ||= {}).x = initialParam;
    }
    if (result.viz.kind === "timeseries" || result.viz.kind === "temporal") {
      if (tsBounds) {
        setTsStart(tsBounds.minStr);
        setTsEnd(tsBounds.maxStr);
      } else {
        setTsStart("");
        setTsEnd("");
      }
      // Infer x/y if missing
      const rows = Array.isArray(result.data) ? result.data : [];
      const first = rows.find((r: any) => r && typeof r === 'object') || {};
      const keys = Object.keys(first);
      const timePrefs = ['profile_date','date','timestamp','time','datetime'];
      const valuePrefs = ['avg_temperature','avg_temp','temperature','avg_salinity','avg_sal','salinity','value'];
      const xKey = result.viz.spec?.x || timePrefs.find(k => keys.includes(k)) || (keys.find(k => /date|time/i.test(k)) || 'timestamp');
      // pick first numeric-like key not equal to x
      const numericKeys = keys.filter(k => k !== xKey && (typeof first[k] === 'number' || rows.some((r:any)=> Number.isFinite(Number(r?.[k])))));
      const yKey = result.viz.spec?.y || valuePrefs.find(k => keys.includes(k)) || numericKeys[0];
      (result.viz.spec ||= {}).x = xKey;
      (result.viz.spec ||= {}).y = yKey;
    }
  }, [result, tsBounds]);

  const handleExport = async (format: string, endpoint: string | unknown) => {
    try {
      if (typeof endpoint !== 'string') return;
      const url = buildApiUrl(endpoint);
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Export failed (${res.status})`);

      const cd = res.headers.get('content-disposition') || '';
      const guessedName = cd.match(/filename=\"?([^\";]+)\"?/i)?.[1] || `export.${format}`;
      const ct = res.headers.get('content-type') || '';

      if (ct.includes('application/json')) {
        const json = await res.json();
        if (json && json.content) {
          const blob = new Blob([json.content], { type: 'text/csv;charset=utf-8' });
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = json.filename || guessedName;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(a.href);
          toast({ title: 'Export ready', description: `${format.toUpperCase()} downloaded` });
          return;
        }
      }

      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = guessedName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      toast({ title: 'Export ready', description: `${format.toUpperCase()} downloaded` });
    } catch (e: any) {
      toast({ title: 'Export failed', description: e?.message || 'Unable to download', variant: 'destructive' });
    }
  };

  const getIntentIcon = (intent: string) => {
    switch (intent) {
      case "profile_path":
        return <Map className="h-5 w-5" />;
      case "profile_data":
        return <BarChart3 className="h-5 w-5" />;
      case "profile_timeseries":
        return <TrendingUp className="h-5 w-5" />;
      default:
        return <Database className="h-5 w-5" />;
    }
  };

  const getIntentColor = (intent: string) => {
    switch (intent) {
      case "profile_path":
        return "bg-accent/10 text-accent border-accent/20";
      case "profile_data":
        return "bg-primary/10 text-primary border-primary/20";
      case "profile_timeseries":
        return "bg-success/10 text-success border-success/20";
      default:
        return "bg-secondary/10 text-secondary-foreground border-secondary/20";
    }
  };

  // Build filtered data depending on visualization kind
  const filteredData = useMemo(() => {
    if (!result?.data || !Array.isArray(result.data)) return [] as any[];

    if (result.viz?.kind === "timeseries" || result.viz?.kind === "temporal") {
      const xKey = result.viz.spec?.x || 'timestamp';
      if (!xKey) return [];
      const start = tsStart ? new Date(tsStart) : null;
      const end = tsEnd ? new Date(tsEnd) : null;
      return result.data.filter((d: any) => {
        const tVal = d?.[xKey];
        const t = new Date(tVal);
        if (t.toString() === 'Invalid Date') return false;
        if (start && t < start) return false;
        if (end) {
          const endOfDay = new Date(end);
          endOfDay.setHours(23,59,59,999);
          if (t > endOfDay) return false;
        }
        return true;
      });
    }

    if (result.viz?.kind === "profile" || result.viz?.kind === "profile_comparison") {
      return result.data;
    }

    return result.data;
  }, [result, tsStart, tsEnd]);

  // Build spec overrides for profile charts
  const profileSpec = useMemo(() => {
    if (!result?.viz || (result.viz.kind !== 'profile' && result.viz.kind !== 'profile_comparison')) return undefined;
    const rows = Array.isArray(result.data) ? result.data : [];
    const first = rows.find((r: any) => r && typeof r === 'object') || {};
    const keys = Object.keys(first);
    const base = result.viz.spec || {};
    const yGuess = base.y || (keys.includes('depth_m') ? 'depth_m' : keys.includes('pressure') ? 'pressure' : (keys.find(k => /depth|press/i.test(k)) || 'depth_m'));
    const preferred = ['temperature','salinity','pressure'];
    const numericKeys = keys.filter(k => typeof first[k] === 'number' || (rows.some((r:any)=> Number.isFinite(Number(r?.[k])))));
    const ordered = [...preferred.filter(k => keys.includes(k)), ...numericKeys.filter(k => !preferred.includes(k))].filter(k => k !== yGuess);
    const xOpts: string[] = base.x_opts || ordered;
    return {
      y: yGuess,
      ...base,
      x_opts: xOpts,
      x: profileParam || base.x || xOpts[0],
      invert_y: invertY ?? base.invert_y ?? (yGuess === 'depth_m' || /depth|press/i.test(String(yGuess))),
    } as any;
  }, [result, profileParam, invertY]);

  // Derive map points from result.data when available
  const derivedMapSpec = useMemo(() => {
    const rows = Array.isArray(result?.data) ? result.data : [];
    if (!rows.length) return null as null | { points: any[] };
    const firstObj = rows.find((r: any) => r && typeof r === 'object');
    if (!firstObj) return null as null | { points: any[] };
    const keys = Object.keys(firstObj);

    const chooseLatKey = (ks: string[]) => {
      const lower = ks.map(k => k.toLowerCase());
      const exacts = ["latitude", "lat"];
      for (const ex of exacts) { const idx = lower.indexOf(ex); if (idx !== -1) return ks[idx]; }
      const containsLatitude = ks.find(k => /latitude/i.test(k)); if (containsLatitude) return containsLatitude;
      const containsLat = ks.find(k => /(^|[^a-z])lat([^a-z]|$)/i.test(k)); if (containsLat) return containsLat;
      return undefined;
    };
    const chooseLonKey = (ks: string[]) => {
      const lower = ks.map(k => k.toLowerCase());
      const exacts = ["longitude", "lon", "lng"];
      for (const ex of exacts) { const idx = lower.indexOf(ex); if (idx !== -1) return ks[idx]; }
      const containsLongitude = ks.find(k => /longitude/i.test(k)); if (containsLongitude) return containsLongitude;
      const containsLon = ks.find(k => /(^|[^a-z])(lon|lng)([^a-z]|$)/i.test(k)); if (containsLon) return containsLon;
      return undefined;
    };

    const latKey = chooseLatKey(keys);
    const lonKey = chooseLonKey(keys);
    if (!latKey || !lonKey) return null as null | { points: any[] };

    const toNum = (v: any) => {
      if (typeof v === 'number') return Number.isFinite(v) ? v : null;
      if (typeof v === 'string') { const n = parseFloat(v); return Number.isFinite(n) ? n : null; }
      return null;
    };
    const inRange = (lat: number | null, lon: number | null) => {
      if (lat === null || lon === null) return false;
      return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
    };

    const points = rows
      .map((r: any) => ({ lat: toNum(r?.[latKey]), lon: toNum(r?.[lonKey]), float_id: r?.float_id || r?.id }))
      .filter((p: any) => inRange(p.lat, p.lon));

    return points.length ? { points } : null;
  }, [result]);

  return (
    <Card className="shadow-depth">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-3">
            {getIntentIcon(result.intent)}
            <span>Query Results</span>
          </CardTitle>
          {result.intent && (
            <Badge className={getIntentColor(result.intent)}>
              {result.intent.replace(/_/g, ' ')}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Analysis Text */}
        <div className="p-4 surface-gradient rounded-lg border">
          <p className="text-foreground leading-relaxed">
            {result.rag_analysis}
          </p>
          {result.data_count && (
            <p className="text-sm text-muted-foreground mt-2">
              Found {result.data_count} data points
            </p>
          )}
        </div>

        {/* Filters */}
        {result.viz && (
          <div className="p-4 rounded-lg border bg-muted/5 space-y-3">
            <div className="text-sm font-medium text-muted-foreground">Filters</div>
            {(result.viz.kind === 'timeseries' || result.viz.kind === 'temporal') && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                <div>
                  <Label htmlFor="ts-start">Start date</Label>
                  <Input id="ts-start" type="date" value={tsStart} min={tsBounds?.minStr} max={tsBounds?.maxStr} onChange={(e) => setTsStart(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="ts-end">End date</Label>
                  <Input id="ts-end" type="date" value={tsEnd} min={tsBounds?.minStr} max={tsBounds?.maxStr} onChange={(e) => setTsEnd(e.target.value)} />
                </div>
                <div className="text-xs text-muted-foreground">
                  Range: {tsBounds ? `${tsBounds.minStr} to ${tsBounds.maxStr}` : 'n/a'}. Filters update the graph instantly.
                </div>
              </div>
            )}

            {(result.viz.kind === 'profile' || result.viz.kind === 'profile_comparison') && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                <div>
                  <Label>Parameter</Label>
                  <Select value={profileParam} onValueChange={setProfileParam} disabled={!profileSpec?.x_opts?.length}>
                    <SelectTrigger>
                      <SelectValue placeholder={profileSpec?.x_opts?.length ? "Select parameter" : "No parameters available"} />
                    </SelectTrigger>
                    <SelectContent>
                      {(profileSpec?.x_opts && profileSpec.x_opts.length ? profileSpec.x_opts : []).map((opt: string) => (
                        <SelectItem key={opt} value={opt} className="capitalize">{opt}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center space-x-3 pt-6">
                  <Switch id="invert-y" checked={!!invertY} onCheckedChange={setInvertY} />
                  <Label htmlFor="invert-y">Invert depth (show depth increasing downward)</Label>
                </div>
                <div className="text-xs text-muted-foreground">
                  Choose x-axis parameter and depth orientation for profile charts.
                </div>
              </div>
            )}
          </div>
        )}

        {/* Visualizations */}
        {(result.viz || derivedMapSpec) && (
          <div className="space-y-4">
            {(result.viz?.kind === "map" || derivedMapSpec) && (
              <MapVisualization data={(function(){
                const base = (result.viz?.spec as any) || {};
                const withRows = { ...base, rows: Array.isArray(result.data) ? result.data : [] };
                if (Array.isArray(base.points) && base.points.length) return withRows;
                if (derivedMapSpec?.points?.length) return { ...withRows, points: derivedMapSpec.points };
                return withRows;
              })()} />
            )}
            {result.viz?.kind === "profile" && profileSpec && (
              <ProfileChart data={filteredData} spec={profileSpec} />
            )}
            {result.viz?.kind === "profile_comparison" && profileSpec && (
              <ProfileChart
                data={filteredData}
                spec={{
                  y: profileSpec.y,
                  x_opts: [profileSpec.x],
                  invert_y: profileSpec.invert_y,
                  group_by: profileSpec.group_by,
                }}
              />
            )}
            {(result.viz?.kind === "timeseries" || result.viz?.kind === "temporal") && (
              <TimeseriesChart data={filteredData} spec={{ x: result.viz.spec?.x, y: result.viz.spec?.y }} />
            )}
          </div>
        )}

        {/* Data Table */}
        {filteredData && Array.isArray(filteredData) && filteredData.length > 0 && (
          <DataTable data={filteredData} />
        )}

        {/* Semantic Search Results */}
        {result.semantic_results && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Similar Floats</h3>
            {result.semantic_results.map((item: any, index: number) => (
              <Card key={index} className="border-l-4 border-l-accent">
                <CardContent className="p-4">
                  <p className="text-sm">{item.text}</p>
                  {item.meta && (
                    <div className="mt-2 text-xs text-muted-foreground">
                      ID: {item.id}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Export Options */}
        {result.export_options && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Export Data</h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(result.export_options).map(([format, url]) => (
                <Badge
                  key={format}
                  variant="outline"
                  className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-smooth"
                  onClick={() => handleExport(format, url)}
                >
                  {format.toUpperCase()}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
