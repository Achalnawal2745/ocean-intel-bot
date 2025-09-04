import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Map } from "lucide-react";

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
    const lngs = line.map(point => point.lon);
    const lats = line.map(point => point.lat);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    
    bounds = [[minLat, minLng], [maxLat, maxLng]];
    center = [(minLat + maxLat) / 2, (minLng + maxLng) / 2];
    zoom = 6;
  }

  if (!line || line.length === 0) {
    return (
      <Card className="border-warning/20">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Map className="h-5 w-5 text-warning" />
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

  // Fit map to bounds once when available
  const FitBounds: React.FC<{ bounds: [[number, number], [number, number]] }> = ({ bounds }) => {
    const map = useMap();
    useEffect(() => {
      map.fitBounds(bounds as any, { padding: [50, 50] });
    }, [map, bounds]);
    return null;
  };

  return (
    <Card className="border-accent/20">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Map className="h-5 w-5 text-accent" />
          <span>Float Path Visualization</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <MapContainer 
            center={center} 
            zoom={zoom} 
            className="w-full h-[400px] rounded-lg shadow-lg z-0"
            style={{ minHeight: '400px' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            
            {/* Float path */}
            <Polyline 
              positions={pathCoordinates} 
              color="#3b82f6" 
              weight={3}
              opacity={0.7}
            />
            
            {/* Start marker */}
            {start && (
              <Marker position={[start.lat, start.lon]} icon={startIcon}>
                <Popup>
                  <div>
                    <strong>Start Position</strong><br/>
                    Lat: {start.lat.toFixed(4)}°<br/>
                    Lon: {start.lon.toFixed(4)}°
                  </div>
                </Popup>
              </Marker>
            )}
            
            {/* End marker */}
            {end && (
              <Marker position={[end.lat, end.lon]} icon={endIcon}>
                <Popup>
                  <div>
                    <strong>End Position</strong><br/>
                    Lat: {end.lat.toFixed(4)}°<br/>
                    Lon: {end.lon.toFixed(4)}°
                  </div>
                </Popup>
              </Marker>
            )}
            {bounds && <FitBounds bounds={bounds} />} 
          </MapContainer>
          
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