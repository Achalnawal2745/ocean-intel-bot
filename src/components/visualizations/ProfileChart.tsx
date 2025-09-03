import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart3, TrendingDown } from "lucide-react";

interface ProfileChartProps {
  data: any[];
  spec: {
    y: string;
    x_opts?: string[];
    invert_y?: boolean;
    group_by?: string;
  };
}

export const ProfileChart: React.FC<ProfileChartProps> = ({ data, spec }) => {
  const { y, x_opts = ["temperature"], invert_y = false, group_by } = spec;
  
  const groupedData = group_by 
    ? data.reduce((acc, item) => {
        const key = item[group_by];
        if (!acc[key]) acc[key] = [];
        acc[key].push(item);
        return acc;
      }, {} as Record<string, any[]>)
    : { all: data };

  const getStats = (values: number[]) => {
    if (values.length === 0) return { min: 0, max: 0, avg: 0 };
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    return { min, max, avg };
  };

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
          {Object.entries(groupedData).map(([groupKey, groupData]) => (
            <div key={groupKey} className="space-y-4">
              {group_by && groupKey !== 'all' && (
                <h3 className="font-semibold text-lg">Float {groupKey}</h3>
              )}
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {x_opts.map((param) => {
                  const values = (groupData as any[])
                    .filter(d => d[param] != null && d[y] != null)
                    .map(d => d[param]);
                  
                  if (values.length === 0) return null;
                  
                  const stats = getStats(values);
                  const pressureValues = (groupData as any[])
                    .filter(d => d[param] != null && d[y] != null)
                    .map(d => d[y]);
                  const depthRange = getStats(pressureValues);
                  
                  return (
                    <div key={`${groupKey}-${param}`} className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium capitalize">{param}</h4>
                        <Badge variant="secondary" className="text-xs">
                          {values.length} points
                        </Badge>
                      </div>
                      
                      <div className="bg-gradient-to-b from-accent/5 to-primary/5 rounded-lg p-4 min-h-[200px] relative overflow-hidden">
                        {/* Simulated profile visualization */}
                        <div className="absolute inset-4 border-l-2 border-b-2 border-muted-foreground/20">
                          <div className="absolute -bottom-6 -left-4 text-xs text-muted-foreground">
                            {y === 'pressure' ? `${depthRange.max.toFixed(0)} dbar` : '0'}
                          </div>
                          <div className="absolute -top-4 -left-4 text-xs text-muted-foreground">
                            {y === 'pressure' ? `${depthRange.min.toFixed(0)} dbar` : `${depthRange.max.toFixed(1)}`}
                          </div>
                          <div className="absolute -bottom-6 -right-4 text-xs text-muted-foreground">
                            {stats.max.toFixed(1)} {param === 'temperature' ? '°C' : 'psu'}
                          </div>
                          <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-muted-foreground">
                            {stats.avg.toFixed(1)}
                          </div>
                        </div>
                        
                        {/* Profile curve simulation */}
                        <div className="absolute inset-4 flex items-end">
                          <div className="w-full h-full relative">
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/20 to-transparent rounded-full blur-sm"></div>
                            <div className="absolute left-1/4 bottom-0 w-px h-3/4 bg-primary/40"></div>
                            <div className="absolute left-1/2 bottom-0 w-px h-4/5 bg-primary/60"></div>
                            <div className="absolute left-3/4 bottom-0 w-px h-2/3 bg-primary/40"></div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div className="text-center p-2 bg-success/5 rounded border border-success/20">
                          <div className="font-medium text-success">Min</div>
                          <div className="text-xs">{stats.min.toFixed(2)}</div>
                        </div>
                        <div className="text-center p-2 bg-primary/5 rounded border border-primary/20">
                          <div className="font-medium text-primary">Avg</div>
                          <div className="text-xs">{stats.avg.toFixed(2)}</div>
                        </div>
                        <div className="text-center p-2 bg-warning/5 rounded border border-warning/20">
                          <div className="font-medium text-warning">Max</div>
                          <div className="text-xs">{stats.max.toFixed(2)}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};