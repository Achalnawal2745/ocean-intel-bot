import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart3, TrendingDown } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

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
  // Early return for invalid data
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <Card className="border-warning/20">
        <CardContent className="p-6 text-center text-muted-foreground">
          No profile data available for visualization
        </CardContent>
      </Card>
    );
  }

  const { y, x_opts = ["temperature"], invert_y = false, group_by } = spec;
  
  const groupedData = group_by 
    ? data.reduce((acc, item) => {
        const key = item[group_by];
        if (!acc[key]) acc[key] = [];
        acc[key].push(item);
        return acc;
      }, {} as Record<string, any[]>)
    : { all: data };

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
              
              <div className="grid grid-cols-1 gap-6">
                {x_opts.filter(param => param && typeof param === 'string').map((param) => {
                  // Filter and validate data
                  const validData = (groupData as any[]).filter(d => 
                    d && 
                    typeof d === 'object' && 
                    d[param] != null && 
                    d[y] != null &&
                    !isNaN(parseFloat(d[param])) &&
                    !isNaN(parseFloat(d[y]))
                  ).map(d => ({
                    [param]: parseFloat(d[param]),
                    [y]: parseFloat(d[y])
                  })).sort((a, b) => a[y] - b[y]); // Sort by pressure/depth
                  
                  if (validData.length === 0) return null;
                  
                  const getUnit = (parameter: string) => {
                    switch (parameter) {
                      case 'temperature': return '°C';
                      case 'salinity': return 'psu';
                      case 'pressure': return 'dbar';
                      default: return '';
                    }
                  };
                  
                  return (
                    <div key={`${groupKey}-${param}`} className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium capitalize">
                          {param} vs {y} Profile
                        </h4>
                        <Badge variant="secondary" className="text-xs">
                          {validData.length} measurements
                        </Badge>
                      </div>
                      
                      <div className="bg-background rounded-lg p-4 border">
                        <ResponsiveContainer width="100%" height={400}>
                          <LineChart data={validData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis 
                              type="number"
                              dataKey={param}
                              domain={['dataMin', 'dataMax']}
                              label={{ value: `${param} (${getUnit(param)})`, position: 'insideBottom', offset: -5 }}
                            />
                            <YAxis 
                              type="number"
                              dataKey={y}
                              domain={['dataMin', 'dataMax']}
                              reversed={invert_y}
                              label={{ value: `${y} (${getUnit(y)})`, angle: -90, position: 'insideLeft' }}
                            />
                            <Tooltip 
                              formatter={(value, name) => [`${typeof value === 'number' ? value.toFixed(2) : value} ${getUnit(name.toString())}`, name]}
                              labelFormatter={(label) => `${y}: ${label} ${getUnit(y)}`}
                            />
                            <Line 
                              type="monotone" 
                              dataKey={param} 
                              stroke="hsl(var(--primary))" 
                              strokeWidth={2}
                              dot={{ fill: 'hsl(var(--primary))', strokeWidth: 1, r: 3 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
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