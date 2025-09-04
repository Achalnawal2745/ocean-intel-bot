import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Map as MapIcon } from "lucide-react";

// Fix Leaflet default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface MapVisualizationProps {
  data: {
    line?: { lat: number; lon: number }[];
    start?: { lat: number; lon: number };
    end?: { lat: number; lon: number };
  };
}

export const MapVisualization: React.FC<MapVisualizationProps> = ({ data }) => {
  const { line, start, end } = data;

  // Calculate bounds and center if we have path data
  let bounds: [[number, number], [number, number]] | undefined;
  let center: [number, number] = [0, 0];
  let zoom = 2;
  
  if (line && line.length > 0) {
    let minLng = line[0].lon;
    let maxLng = line[0].lon;
    let minLat = line[0].lat;
    let maxLat = line[0].lat;
    for (const p of line) {
      if (p.lon < minLng) minLng = p.lon;
      if (p.lon > maxLng) maxLng = p.lon;
      if (p.lat < minLat) minLat = p.lat;
      if (p.lat > maxLat) maxLat = p.lat;
    }
    
    bounds = [[minLat, minLng], [maxLat, maxLng]];
    center = [(minLat + maxLat) / 2, (minLng + maxLng) / 2];
    zoom = 6;
  }

  const boundsKey = bounds ? `${bounds[0][0]}:${bounds[0][1]}:${bounds[1][0]}:${bounds[1][1]}` : '';
  if (!line || line.length === 0) {
    return (
      <Card className="border-warning/20">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <MapIcon className="h-5 w-5 text-warning" />
            <span>Float Path Visualization</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-warning/10 rounded-lg border border-warning/20 text-center">
            <p className="text-muted-foreground">No path data available for visualization</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Convert path data to Leaflet format
  const pathCoordinates: [number, number][] = line.map(point => [point.lat, point.lon]);
  
  // Create custom icons
  const startIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  const endIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const vectorsRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize map once
    if (!mapRef.current) {
      mapRef.current = L.map(containerRef.current, {
        center: [0, 0],
        zoom: 2,
        worldCopyJump: true,
      });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
      }).addTo(mapRef.current);
      vectorsRef.current = L.layerGroup().addTo(mapRef.current);
    }

    // Update vector layers
    const v = vectorsRef.current!;
    v.clearLayers();

    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
    const routeColor = accent ? `hsl(${accent})` : '#3b82f6';

    const poly = L.polyline(pathCoordinates, { color: routeColor, weight: 3, opacity: 0.7 }).addTo(v);

    if (start) {
      L.marker([start.lat, start.lon], { icon: startIcon })
        .addTo(v)
        .bindPopup(`<strong>Start</strong><br/>Lat: ${start.lat.toFixed(4)}<br/>Lon: ${start.lon.toFixed(4)}`);
    }
    if (end) {
      L.marker([end.lat, end.lon], { icon: endIcon })
        .addTo(v)
        .bindPopup(`<strong>End</strong><br/>Lat: ${end.lat.toFixed(4)}<br/>Lon: ${end.lon.toFixed(4)}`);
    }

    if (bounds) {
      mapRef.current!.fitBounds(poly.getBounds(), { padding: [50, 50] });
    }
  }, [boundsKey]);

  useEffect(() => {
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
      vectorsRef.current = null;
    };
  }, []);

  return (
    <Card className="border-accent/20">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <MapIcon className="h-5 w-5 text-accent" />
          <span>Float Path Visualization</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <div 
            ref={containerRef}
            className="w-full h-[400px] rounded-lg shadow-lg z-0"
            style={{ minHeight: '400px' }}
          />
          
          {/* Path stats overlay */}
          <div className="absolute top-4 left-4 bg-background/90 backdrop-blur-sm rounded-lg border p-3 shadow-lg z-10">
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
        </div>
      </CardContent>
    </Card>
  );
};