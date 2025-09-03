import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Calendar } from "lucide-react";

interface TimeseriesChartProps {
  data: any[];
  spec: {
    x: string;
    y: string;
  };
}

export const TimeseriesChart: React.FC<TimeseriesChartProps> = ({ data, spec }) => {
  const { x, y } = spec;
  
  const validData = data.filter(d => d[x] && d[y] != null);
  
  if (validData.length === 0) {
    return (
      <Card className="border-warning/20">
        <CardContent className="p-6 text-center text-muted-foreground">
          No valid timeseries data available
        </CardContent>
      </Card>
    );
  }

  const values = validData.map(d => parseFloat(d[y]));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const avgValue = values.reduce((a, b) => a + b, 0) / values.length;
  
  const firstDate = new Date(validData[0][x]);
  const lastDate = new Date(validData[validData.length - 1][x]);
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

          {/* Simulated Chart Area */}
          <div className="bg-gradient-to-br from-success/5 to-accent/5 rounded-lg p-6 min-h-[300px] relative overflow-hidden">
            <div className="absolute inset-4 border-l-2 border-b-2 border-muted-foreground/20">
              {/* Y-axis labels */}
              <div className="absolute -left-12 top-0 text-xs text-muted-foreground">
                {maxValue.toFixed(1)}
              </div>
              <div className="absolute -left-12 top-1/2 text-xs text-muted-foreground">
                {avgValue.toFixed(1)}
              </div>
              <div className="absolute -left-12 bottom-0 text-xs text-muted-foreground">
                {minValue.toFixed(1)}
              </div>
              
              {/* X-axis labels */}
              <div className="absolute -bottom-8 left-0 text-xs text-muted-foreground">
                {firstDate.toLocaleDateString()}
              </div>
              <div className="absolute -bottom-8 right-0 text-xs text-muted-foreground">
                {lastDate.toLocaleDateString()}
              </div>
            </div>
            
            {/* Simulated timeseries line */}
            <div className="absolute inset-4 flex items-end">
              <div className="w-full h-full relative">
                {/* Background grid */}
                <div className="absolute inset-0 opacity-10">
                  <div className="h-full w-full bg-gradient-to-r from-transparent via-muted-foreground to-transparent"></div>
                </div>
                
                {/* Data visualization simulation */}
                <div className="absolute inset-0 flex items-end space-x-1">
                  {Array.from({ length: 20 }, (_, i) => {
                    const height = 20 + Math.sin(i * 0.5) * 30 + Math.random() * 20;
                    return (
                      <div 
                        key={i}
                        className="flex-1 bg-gradient-to-t from-success to-accent rounded-t opacity-60"
                        style={{ height: `${height}%` }}
                      />
                    );
                  })}
                </div>
                
                {/* Trend line */}
                <div className="absolute inset-0 bg-gradient-to-r from-success/30 via-primary/30 to-accent/30 rounded-full blur-lg opacity-50"></div>
              </div>
            </div>
            
            <div className="absolute top-4 right-4 text-xs text-muted-foreground bg-background/80 px-2 py-1 rounded">
              Interactive chart would be rendered here
            </div>
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