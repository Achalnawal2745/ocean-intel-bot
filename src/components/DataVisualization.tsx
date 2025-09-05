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
      const xOpts: string[] = result.viz.spec?.x_opts || (result.viz.spec?.x ? [result.viz.spec.x] : []);
      setProfileParam(result.viz.spec?.x || xOpts[0]);
      setInvertY(result.viz.spec?.invert_y ?? false);
    }
    if (result.viz.kind === "timeseries" || result.viz.kind === "temporal") {
      if (tsBounds) {
        setTsStart(tsBounds.minStr);
        setTsEnd(tsBounds.maxStr);
      } else {
        setTsStart("");
        setTsEnd("");
      }
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
      const start = tsStart ? new Date(tsStart) : null;
      const end = tsEnd ? new Date(tsEnd) : null;
      return result.data.filter((d: any) => {
        const t = new Date(d[xKey]);
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
    const base = result.viz.spec || {};
    const xOpts: string[] = base.x_opts || (base.x ? [base.x] : []);
    return {
      ...base,
      x_opts: xOpts,
      x: profileParam || base.x || xOpts[0],
      invert_y: invertY ?? base.invert_y,
    } as any;
  }, [result, profileParam, invertY]);

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
                  <Select value={profileParam} onValueChange={setProfileParam}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select parameter" />
                    </SelectTrigger>
                    <SelectContent>
                      {(result.viz.spec?.x_opts || (result.viz.spec?.x ? [result.viz.spec.x] : [])).map((opt: string) => (
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
        {result.viz && (
          <div className="space-y-4">
            {result.viz.kind === "map" && (
              <MapVisualization data={result.viz.spec} />
            )}
            {result.viz.kind === "profile" && profileSpec && (
              <ProfileChart data={filteredData} spec={profileSpec} />
            )}
            {result.viz.kind === "profile_comparison" && profileSpec && (
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
            {(result.viz.kind === "timeseries" || result.viz.kind === "temporal") && (
              <TimeseriesChart data={filteredData} spec={result.viz.spec} />
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
