import { useMemo } from "react";
import type React from "react";
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
    rows?: any[];
    trajectories?: {
      float_id: number;
      points: { lat: number; lon: number;[key: string]: any }[];
      color?: string;
    }[];
  };
}

const computeMapState = (
  line?: { lat: number; lon: number }[],
  points?: { lat: number; lon: number }[],
  trajectories?: { points: { lat: number; lon: number }[] }[]
) => {
  const coords = [
    ...(line ?? []),
    ...(points ?? []),
    ...(trajectories?.flatMap(t => t.points) ?? [])
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
    const lat = Number(p.lat ?? (p as any).latitude);
    const lon = Number(p.lon ?? (p as any).longitude);
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
  const { line, points, start, end, rows, trajectories } = data as any;

  const toNum = (v: any) => {
    if (typeof v === 'number') return Number.isFinite(v) ? v : null;
    if (typeof v === 'string') {
      const n = parseFloat(v);
      return Number.isFinite(n) ? n : null;
    }
    return null;
  };

  const deriveFromRows = (rowsIn: any[] | undefined) => {
    const rowsArr = Array.isArray(rowsIn) ? rowsIn : [];
    if (!rowsArr.length) return [] as { lat: number; lon: number; float_id?: number }[];
    const first = rowsArr.find((r) => r && typeof r === 'object');
    if (!first) return [] as { lat: number; lon: number; float_id?: number }[];
    const keys = Object.keys(first);
    const lower = keys.map(k => k.toLowerCase());
    const pickKey = (candidates: string[], fallbackRegex: RegExp) => {
      for (const c of candidates) { const i = lower.indexOf(c); if (i !== -1) return keys[i]; }
      return keys.find(k => fallbackRegex.test(k)) as string | undefined;
    };
    const latKey = pickKey(["latitude", "lat"], /(^|[^a-z])lat([^a-z]|$)/i);
    const lonKey = pickKey(["longitude", "lon", "lng"], /(^|[^a-z])(lon|lng)([^a-z]|$)/i);
    const idKey = pickKey(["float_id", "id", "float id"], /id/i);
    if (!latKey || !lonKey) return [] as { lat: number; lon: number; float_id?: number }[];
    const inRange = (lat: number | null, lon: number | null) => lat !== null && lon !== null && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
    return rowsArr.map((r: any) => ({ lat: toNum(r?.[latKey]), lon: toNum(r?.[lonKey]), float_id: r?.[idKey as string] }))
      .filter((p) => inRange(p.lat, p.lon)) as { lat: number; lon: number; float_id?: number }[];
  };

  const safeLine = useMemo(
    () => (line ?? [])
      .map((p: any) => {
        const lat = toNum(p?.lat ?? (Array.isArray(p) ? p[0] : undefined));
        const lon = toNum(p?.lon ?? (Array.isArray(p) ? p[1] : undefined));
        return { lat, lon };
      })
      .filter((p) => p.lat !== null && p.lon !== null) as { lat: number; lon: number }[],
    [line]
  );

  const validPoints = useMemo(
    () => {
      const supplied = (points ?? [])
        .map((p: any) => {
          const lat = toNum(p?.lat ?? (Array.isArray(p) ? p[0] : undefined));
          const lon = toNum(p?.lon ?? (Array.isArray(p) ? p[1] : undefined));
          return { lat, lon, float_id: p?.float_id };
        })
        .filter((p) => p.lat !== null && p.lon !== null) as { lat: number; lon: number; float_id?: number }[];
      if (supplied.length) return supplied;
      return deriveFromRows(rows);
    },
    [points, rows]
  );

  const mapState = useMemo(() => computeMapState(safeLine, validPoints, trajectories), [safeLine, validPoints, trajectories]);
  const pathCoords: LatLngExpression[] = useMemo(
    () => safeLine.map((p) => [p.lat, p.lon] as [number, number]),
    [safeLine]
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

            {trajectories && trajectories.map((traj: any, idx: number) => (
              <Polyline
                key={traj.float_id || idx}
                positions={traj.points.map((p: any) => [p.lat ?? p.latitude, p.lon ?? p.longitude])}
                pathOptions={{ color: traj.color || 'hsl(var(--accent))', weight: 3 }}
              >
                <Popup>Float {traj.float_id}</Popup>
              </Polyline>
            ))}

            {start && Number.isFinite(Number(start.lat)) && Number.isFinite(Number(start.lon)) && (
              <CircleMarker
                center={[Number(start.lat), Number(start.lon)]}
                radius={6}
                pathOptions={{ color: 'hsl(var(--success))', fillColor: 'hsl(var(--success))', fillOpacity: 1 }}
              >
                <Popup>
                  <strong>Start</strong><br />
                  Lat: {Number(start.lat).toFixed(4)}<br />
                  Lon: {Number(start.lon).toFixed(4)}
                </Popup>
              </CircleMarker>
            )}

            {end && Number.isFinite(Number(end.lat)) && Number.isFinite(Number(end.lon)) && (
              <CircleMarker
                center={[Number(end.lat), Number(end.lon)]}
                radius={6}
                pathOptions={{ color: 'hsl(var(--destructive))', fillColor: 'hsl(var(--destructive))', fillOpacity: 1 }}
              >
                <Popup>
                  <strong>End</strong><br />
                  Lat: {Number(end.lat).toFixed(4)}<br />
                  Lon: {Number(end.lon).toFixed(4)}
                </Popup>
              </CircleMarker>
            )}

            {validPoints.map((pt, idx) => (
              <CircleMarker
                key={`${pt.lat}-${pt.lon}-${idx}`}
                center={[pt.lat, pt.lon]}
                radius={5}
                pathOptions={{ color: 'hsl(var(--primary))', fillColor: 'hsl(var(--primary))', fillOpacity: 0.9 }}
              >
                <Popup>
                  <div className="text-sm">
                    {pt.float_id ? (<div><strong>Float</strong>: {pt.float_id}</div>) : null}
                    <div>Lat: {Number(pt.lat).toFixed(4)}</div>
                    <div>Lon: {Number(pt.lon).toFixed(4)}</div>
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
                {start && end && Number.isFinite(Number(start.lat)) && Number.isFinite(Number(start.lon)) && Number.isFinite(Number(end.lat)) && Number.isFinite(Number(end.lon)) && (
                  <>
                    <div className="flex items-center space-x-2 text-xs">
                      <div className="h-2 w-2 rounded-full bg-success"></div>
                      <span>Start: {Number(start.lat).toFixed(2)}°, {Number(start.lon).toFixed(2)}°</span>
                    </div>
                    <div className="flex items-center space-x-2 text-xs">
                      <div className="h-2 w-2 rounded-full bg-destructive"></div>
                      <span>End: {Number(end.lat).toFixed(2)}°, {Number(end.lon).toFixed(2)}°</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {validPoints.length > 0 && (
            <div className="absolute top-4 right-4 bg-background/90 backdrop-blur-sm rounded-lg border p-3 shadow-lg">
              <div className="text-sm space-y-1">
                <div className="font-semibold">{validPoints.length} positions</div>
              </div>
            </div>
          )}

          {trajectories && trajectories.length > 0 && (
            <div className="absolute top-4 right-4 bg-background/90 backdrop-blur-sm rounded-lg border p-3 shadow-lg">
              <div className="text-sm space-y-1">
                <div className="font-semibold">{trajectories.length} floats</div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default MapVisualization;
