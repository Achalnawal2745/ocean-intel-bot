import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Map as MapIcon } from "lucide-react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup } from 'react-leaflet';
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface MapVisualizationProps {
  data: {
    line?: { lat: number; lon: number }[];
    points?: { lat: number; lon: number; float_id?: number }[];
    start?: { lat: number; lon: number };
    end?: { lat: number; lon: number };
  };
}

const computeMapState = (
  line?: { lat: number; lon: number }[],
  points?: { lat: number; lon: number }[]
) => {
  const coords = [
    ...(line ?? []),
    ...(points ?? [])
  ];
  if (coords.length === 0) {
    return {
      center: [0, 0] as [number, number],
      zoom: 2,
      bounds: undefined as LatLngBoundsExpression | undefined,
    };
  }

  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLon = Infinity;
  let maxLon = -Infinity;
  for (const p of coords) {
    const lat = Number(p.lat);
    const lon = Number(p.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
    if (lon < minLon) minLon = lon;
    if (lon > maxLon) maxLon = lon;
  }
  if (!Number.isFinite(minLat) || !Number.isFinite(minLon) || !Number.isFinite(maxLat) || !Number.isFinite(maxLon)) {
    return {
      center: [0, 0] as [number, number],
      zoom: 2,
      bounds: undefined as LatLngBoundsExpression | undefined,
    };
  }
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
  const { line, points, start, end } = data;

  const mapState = useMemo(() => computeMapState(line, points), [line, points]);
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

            {points && points.map((pt, idx) => (
              <CircleMarker
                key={`${pt.lat}-${pt.lon}-${idx}`}
                center={[pt.lat, pt.lon]}
                radius={5}
                pathOptions={{ color: 'hsl(var(--primary))', fillColor: 'hsl(var(--primary))', fillOpacity: 0.9 }}
              >
                <Popup>
                  <div className="text-sm">
                    {pt.float_id ? (<div><strong>Float</strong>: {pt.float_id}</div>) : null}
                    <div>Lat: {pt.lat.toFixed(4)}</div>
                    <div>Lon: {pt.lon.toFixed(4)}</div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            <WhenReadyFitBounds bounds={mapState.bounds} />
          </MapContainer>

          {(line && line.length > 0) && (
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

          {points && points.length > 0 && (
            <div className="absolute top-4 right-4 bg-background/90 backdrop-blur-sm rounded-lg border p-3 shadow-lg">
              <div className="text-sm space-y-1">
                <div className="font-semibold">{points.length} positions</div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
