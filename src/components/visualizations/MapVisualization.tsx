import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Map as MapIcon } from "lucide-react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup } from 'react-leaflet';
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface MapVisualizationProps {
  data: {
    line?: { lat: number; lon: number }[];
    start?: { lat: number; lon: number };
    end?: { lat: number; lon: number };
  };
}

const computeMapState = (line?: { lat: number; lon: number }[]) => {
  if (!line || line.length === 0) {
    return {
      center: [0, 0] as [number, number],
      zoom: 2,
      bounds: undefined as LatLngBoundsExpression | undefined,
    };
  }

  const lats = line.map((p) => p.lat);
  const lons = line.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const center: [number, number] = [(minLat + maxLat) / 2, (minLon + maxLon) / 2];
  const bounds: LatLngBoundsExpression = [
    [minLat, minLon],
    [maxLat, maxLon],
  ];

  return { center, zoom: 4, bounds };
};

// Helper to conditionally fit bounds using map's whenReady prop
const WhenReadyFitBounds: React.FC<{ bounds?: LatLngBoundsExpression }>
  = ({ bounds }) => null; // handled via MapContainer 'bounds' prop in react-leaflet v4

export const MapVisualization: React.FC<MapVisualizationProps> = ({ data }) => {
  const { line, start, end } = data;

  const mapState = useMemo(() => computeMapState(line), [line]);
  const pathCoords: LatLngExpression[] = useMemo(
    () => (line ? line.map((p) => [p.lat, p.lon]) : []),
    [line]
  );

  return (
    <Card className="border-accent/20">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MapIcon className="h-5 w-5 text-accent" />
            <span>Float Path Visualization</span>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <MapContainer
            center={mapState.center}
            zoom={mapState.zoom}
            bounds={mapState.bounds}
            className="w-full h-[400px] rounded-lg shadow-lg"
            style={{ minHeight: '400px' }}
            scrollWheelZoom
            worldCopyJump
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {pathCoords.length > 0 && (
              <Polyline positions={pathCoords} pathOptions={{ color: 'hsl(var(--accent))', weight: 3 }} />
            )}

            {start && (
              <CircleMarker
                center={[start.lat, start.lon]}
                radius={6}
                pathOptions={{ color: 'hsl(var(--success))', fillColor: 'hsl(var(--success))', fillOpacity: 1 }}
              >
                <Popup>
                  <strong>Start</strong><br />
                  Lat: {start.lat.toFixed(4)}<br />
                  Lon: {start.lon.toFixed(4)}
                </Popup>
              </CircleMarker>
            )}

            {end && (
              <CircleMarker
                center={[end.lat, end.lon]}
                radius={6}
                pathOptions={{ color: 'hsl(var(--destructive))', fillColor: 'hsl(var(--destructive))', fillOpacity: 1 }}
              >
                <Popup>
                  <strong>End</strong><br />
                  Lat: {end.lat.toFixed(4)}<br />
                  Lon: {end.lon.toFixed(4)}
                </Popup>
              </CircleMarker>
            )}

            <WhenReadyFitBounds bounds={mapState.bounds} />
          </MapContainer>

          {line && line.length > 0 && (
            <div className="absolute top-4 left-4 bg-background/90 backdrop-blur-sm rounded-lg border p-3 shadow-lg">
              <div className="text-sm space-y-1">
                <div className="font-semibold">{line.length} waypoints</div>
                {start && end && (
                  <>
                    <div className="flex items-center space-x-2 text-xs">
                      <div className="h-2 w-2 rounded-full bg-success"></div>
                      <span>Start: {start.lat.toFixed(2)}°, {start.lon.toFixed(2)}°</span>
                    </div>
                    <div className="flex items-center space-x-2 text-xs">
                      <div className="h-2 w-2 rounded-full bg-destructive"></div>
                      <span>End: {end.lat.toFixed(2)}°, {end.lon.toFixed(2)}°</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
