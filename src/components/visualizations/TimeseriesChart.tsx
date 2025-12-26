import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Calendar } from "lucide-react";
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

interface TimeseriesChartProps {
  data: any[];
  spec: {
    x: string;
    y: string;
  };
}

export const TimeseriesChart: React.FC<TimeseriesChartProps> = ({ data, spec }) => {
  const { x, y } = spec;

  const rows = useMemo(() => (
    (data || [])
      .filter(d => d && d[x] != null && d[y] != null)
      .map(d => ({ t: new Date(d[x]), v: Number(d[y]) }))
      .filter(d => d.t.toString() !== 'Invalid Date' && Number.isFinite(d.v))
      .sort((a, b) => a.t.getTime() - b.t.getTime())
  ), [data, x, y]);

  if (rows.length === 0) {
    return (
      <Card className="border-warning/20">
        <CardContent className="p-6 text-center text-muted-foreground">
          No valid timeseries data available
        </CardContent>
      </Card>
    );
  }

  let minValue = Infinity, maxValue = -Infinity, sum = 0;
  for (const r of rows) { if (r.v < minValue) minValue = r.v; if (r.v > maxValue) maxValue = r.v; sum += r.v; }
  const avgValue = sum / rows.length;
  const firstDate = rows[0].t;
  const lastDate = rows[rows.length - 1].t;
  const duration = Math.abs(lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24);

  const getUnit = (param: string) => {
    switch (param) {
      case 'temperature': return '°C';
      case 'salinity': return 'psu';
      case 'pressure': return 'dbar';
      default: return '';
    }
  };

  return (
    <Card className="border-success/20">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <TrendingUp className="h-5 w-5 text-success" />
          <span className="capitalize">{y} Timeseries</span>
          <Badge variant="outline" className="text-xs">
            <Calendar className="h-3 w-3 mr-1" />
            {duration.toFixed(0)} days
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-primary/5 rounded-lg border border-primary/20">
              <div className="text-sm font-medium text-primary">Points</div>
              <div className="text-lg font-bold">{rows.length}</div>
            </div>
            <div className="text-center p-3 bg-success/5 rounded-lg border border-success/20">
              <div className="text-sm font-medium text-success">Min</div>
              <div className="text-lg font-bold">{minValue.toFixed(2)} {getUnit(y)}</div>
            </div>
            <div className="text-center p-3 bg-accent/5 rounded-lg border border-accent/20">
              <div className="text-sm font-medium text-accent">Avg</div>
              <div className="text-lg font-bold">{avgValue.toFixed(2)} {getUnit(y)}</div>
            </div>
            <div className="text-center p-3 bg-warning/5 rounded-lg border border-warning/20">
              <div className="text-sm font-medium text-warning">Max</div>
              <div className="text-lg font-bold">{maxValue.toFixed(2)} {getUnit(y)}</div>
            </div>
          </div>

          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                <XAxis dataKey={(d) => (d as any).t} type="number" scale="time" tickFormatter={(v) => new Date(v).toLocaleDateString()} tick={{ fontSize: 12 }} />
                <YAxis dataKey="v" tick={{ fontSize: 12 }} />
                <Tooltip labelFormatter={(v) => new Date(v as number).toLocaleString()} formatter={(val) => [`${val} ${getUnit(y)}`, y]} />
                <Legend />
                <Line type="monotone" dataKey="v" name={y} stroke="#3b82f6" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="flex justify-between items-center text-sm text-muted-foreground">
            <span>Start: {firstDate.toLocaleString()}</span>
            <span>End: {lastDate.toLocaleString()}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default TimeseriesChart;
