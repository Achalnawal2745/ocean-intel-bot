import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Map, Navigation } from "lucide-react";

interface MapVisualizationProps {
  data: {
    line?: { lat: number; lon: number }[];
    start?: { lat: number; lon: number };
    end?: { lat: number; lon: number };
  };
}

export const MapVisualization: React.FC<MapVisualizationProps> = ({ data }) => {
  const { line, start, end } = data;

  return (
    <Card className="border-accent/20">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Map className="h-5 w-5 text-accent" />
          <span>Float Path Visualization</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative bg-gradient-to-br from-accent/5 to-primary/5 rounded-lg p-6 min-h-[300px] flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="p-4 bg-background/80 rounded-lg border border-accent/20">
              <Map size={48} className="mx-auto text-accent mb-3" />
              <h3 className="font-semibold mb-2">Interactive Map</h3>
              <p className="text-sm text-muted-foreground">
                Float trajectory with {line?.length || 0} waypoints
              </p>
              
              {start && end && (
                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex items-center justify-center space-x-2">
                    <Navigation className="h-3 w-3 text-success" />
                    <span>Start: {start.lat.toFixed(2)}°, {start.lon.toFixed(2)}°</span>
                  </div>
                  <div className="flex items-center justify-center space-x-2">
                    <div className="h-3 w-3 rounded-full bg-destructive"></div>
                    <span>End: {end.lat.toFixed(2)}°, {end.lon.toFixed(2)}°</span>
                  </div>
                </div>
              )}
            </div>
            
            <p className="text-sm text-muted-foreground">
              Interactive map would be rendered here with float trajectory
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};