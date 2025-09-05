import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapVisualization } from "./visualizations/MapVisualization";
import { ProfileChart } from "./visualizations/ProfileChart";
import { TimeseriesChart } from "./visualizations/TimeseriesChart";
import { DataTable } from "./visualizations/DataTable";
import { TrendingUp, Map, BarChart3, Database } from "lucide-react";
import { buildApiUrl } from "@/config/api";
import { useToast } from "@/hooks/use-toast";

interface DataVisualizationProps {
  result: any;
}

export const DataVisualization: React.FC<DataVisualizationProps> = ({ result }) => {
  const { toast } = useToast();

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

        {/* Visualizations */}
        {result.viz && (
          <div className="space-y-4">
            {result.viz.kind === "map" && (
              <MapVisualization data={result.viz.spec} />
            )}
            {result.viz.kind === "profile" && (
              <ProfileChart data={result.data} spec={result.viz.spec} />
            )}
            {result.viz.kind === "profile_comparison" && (
              <ProfileChart
                data={result.data}
                spec={{
                  y: result.viz.spec.y,
                  x_opts: [result.viz.spec.x],
                  invert_y: result.viz.spec.invert_y,
                  group_by: result.viz.spec.group_by,
                }}
              />
            )}
            {(result.viz.kind === "timeseries" || result.viz.kind === "temporal") && (
              <TimeseriesChart data={result.data} spec={result.viz.spec} />
            )}
          </div>
        )}

        {/* Data Table */}
        {result.data && Array.isArray(result.data) && result.data.length > 0 && (
          <DataTable data={result.data} />
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
