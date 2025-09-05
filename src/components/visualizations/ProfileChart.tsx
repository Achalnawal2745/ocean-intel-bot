import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart3, TrendingDown } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';

interface ProfileChartProps {
  data: any[];
  spec: {
    y: string;
    x_opts?: string[];
    x?: string;
    invert_y?: boolean;
    group_by?: string;
  };
}

export const ProfileChart: React.FC<ProfileChartProps> = ({ data, spec }) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <Card className="border-warning/20">
        <CardContent className="p-6 text-center text-muted-foreground">
          No profile data available for visualization
        </CardContent>
      </Card>
    );
  }

  const { y, x_opts = ["temperature"], x, invert_y = false, group_by } = spec;

  const palette = ["#10b981", "#3b82f6", "#ef4444", "#f59e0b", "#8b5cf6", "#14b8a6"];

  const groups = useMemo(() => {
    if (!group_by) return { all: data } as Record<string, any[]>;
    return data.reduce((acc, item) => {
      const key = String(item[group_by] ?? 'unknown');
      (acc[key] = acc[key] || []).push(item);
      return acc;
    }, {} as Record<string, any[]>);
  }, [data, group_by]);

  const computeDomain = (arr: number[]) => {
    let min = Infinity, max = -Infinity;
    for (const v of arr) {
      if (!Number.isFinite(v)) continue;
      if (v < min) min = v;
      if (v > max) max = v;
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 0];
    return [min, max] as [number, number];
  };

  const renderSingleChart = (groupKey: string, groupData: any[], param: string) => {
    const rows = groupData
      .filter(d => d && d[param] != null && d[y] != null)
      .map(d => ({ x: Number(d[param]), y: Number(d[y]) }))
      .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));

    if (rows.length === 0) return null;

    const yVals = rows.map(r => r.y);
    const [minY, maxY] = computeDomain(yVals);

    return (
      <div key={`${groupKey}-${param}`} className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium capitalize">{param}</h4>
          <Badge variant="secondary" className="text-xs">{rows.length} points</Badge>
        </div>
        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
              <XAxis type="number" dataKey="x" tick={{ fontSize: 12 }} />
              <YAxis type="number" dataKey="y" tick={{ fontSize: 12 }} domain={invert_y ? [maxY, minY] : [minY, maxY]} />
              <Tooltip formatter={(v: any, n) => [v, n === 'x' ? param : y]} />
              <Line type="monotone" dataKey="y" stroke={palette[0]} dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  const renderGroupedChart = (param: string) => {
    if (!group_by) return null;

    const seriesData = Object.entries(groups).map(([k, arr]) => {
      return arr
        .filter(d => d && d[param] != null && d[y] != null)
        .map(d => ({ group: k, x: Number(d[param]), y: Number(d[y]) }))
        .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
    });
    const flat = seriesData.flat();
    if (flat.length === 0) return null;
    const yVals = flat.map(r => r.y);
    const [minY, maxY] = computeDomain(yVals);

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium capitalize">{param} (by {group_by})</h4>
          <Badge variant="secondary" className="text-xs">{flat.length} points</Badge>
        </div>
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
              <XAxis type="number" dataKey="x" tick={{ fontSize: 12 }} />
              <YAxis type="number" dataKey="y" tick={{ fontSize: 12 }} domain={invert_y ? [maxY, minY] : [minY, maxY]} />
              <Tooltip />
              <Legend />
              {Object.entries(groups).map(([k, arr], idx) => {
                const data = arr
                  .filter(d => d && d[param] != null && d[y] != null)
                  .map(d => ({ x: Number(d[param]), y: Number(d[y]) }))
                  .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
                return (
                  <Line key={k} type="monotone" data={data} name={k} dataKey="y" stroke={palette[idx % palette.length]} dot={false} strokeWidth={2} />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  const paramsToRender = x ? [x] : x_opts;

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          <span>Ocean Profile Data</span>
          {invert_y && (
            <Badge variant="outline" className="text-xs">
              <TrendingDown className="h-3 w-3 mr-1" />
              Depth Profile
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {group_by
            ? paramsToRender.map((param) => (
                <div key={`grouped-${param}`}>{renderGroupedChart(param)}</div>
              ))
            : Object.entries(groups).map(([groupKey, groupData]) => (
                <div key={groupKey} className="space-y-4">
                  {paramsToRender.map((param) => renderSingleChart(groupKey, groupData, param))}
                </div>
              ))}
        </div>
      </CardContent>
    </Card>
  );
};
