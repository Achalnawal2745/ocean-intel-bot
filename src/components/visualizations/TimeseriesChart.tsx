import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Calendar } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface TimeseriesChartProps {
  data: any[];
  spec: {
    x: string;
    y: string;
  };
}

export const TimeseriesChart: React.FC<TimeseriesChartProps> = ({ data, spec }) => {
  const { x, y } = spec;
  
  // Process and validate data
  const validData = data.filter(d => d[x] && d[y] != null && !isNaN(parseFloat(d[y])))
    .map(d => ({
      timestamp: new Date(d[x]).getTime(),
      [y]: parseFloat(d[y]),
      date: new Date(d[x]).toLocaleDateString()
    }))
    .sort((a, b) => a.timestamp - b.timestamp);
  
  if (validData.length === 0) {
    return (
      <Card className="border-warning/20">
        <CardContent className="p-6 text-center text-muted-foreground">
          No valid timeseries data available
        </CardContent>
      </Card>
    );
  }

  const values = validData.map(d => parseFloat(d[y] as string));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const avgValue = values.reduce((a, b) => a + b, 0) / values.length;
  
  const firstDate = new Date(validData[0].timestamp);
  const lastDate = new Date(validData[validData.length - 1].timestamp);
  const duration = Math.abs(lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24);

  const getUnit = (param: string) => {
    switch (param) {
      case 'temperature': return '°C';
      case 'salinity': return 'psu';
      case 'pressure': return 'dbar';
      default: return '';
    }
  };

  const formatDate = (tickItem: number) => {
    return new Date(tickItem).toLocaleDateString();
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
          {/* Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-primary/5 rounded-lg border border-primary/20">
              <div className="text-sm font-medium text-primary">Points</div>
              <div className="text-lg font-bold">{validData.length}</div>
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

          {/* Interactive Chart */}
          <div className="bg-background rounded-lg p-4 border">
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={validData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  type="number"
                  scale="time"
                  dataKey="timestamp"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={formatDate}
                  label={{ value: 'Time', position: 'insideBottom', offset: -5 }}
                />
                <YAxis 
                  domain={['dataMin', 'dataMax']}
                  label={{ value: `${y} (${getUnit(y)})`, angle: -90, position: 'insideLeft' }}
                />
                <Tooltip 
                  formatter={(value) => [`${typeof value === 'number' ? value.toFixed(2) : value} ${getUnit(y)}`, y]}
                  labelFormatter={(label) => `Date: ${new Date(label).toLocaleString()}`}
                />
                <Line 
                  type="monotone" 
                  dataKey={y} 
                  stroke="hsl(var(--success))" 
                  strokeWidth={2}
                  dot={{ fill: 'hsl(var(--success))', strokeWidth: 1, r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Date Range Info */}
          <div className="flex justify-between items-center text-sm text-muted-foreground">
            <span>Start: {firstDate.toLocaleString()}</span>
            <span>End: {lastDate.toLocaleString()}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};