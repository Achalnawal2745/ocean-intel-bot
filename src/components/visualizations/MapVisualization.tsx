import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Map, Navigation, Key } from "lucide-react";

interface MapVisualizationProps {
  data: {
    line?: { lat: number; lon: number }[];
    start?: { lat: number; lon: number };
    end?: { lat: number; lon: number };
  };
}

export const MapVisualization: React.FC<MapVisualizationProps> = ({ data }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapboxToken, setMapboxToken] = useState<string>('');
  const [tokenInput, setTokenInput] = useState<string>('');
  const [showTokenInput, setShowTokenInput] = useState<boolean>(true);
  
  const { line, start, end } = data;

  const initializeMap = (token: string) => {
    if (!mapContainer.current || !token) return;

    mapboxgl.accessToken = token;
    
    // Calculate bounds if we have path data
    let bounds: mapboxgl.LngLatBoundsLike | undefined;
    let center: [number, number] = [0, 0];
    let zoom = 2;
    
    if (line && line.length > 0) {
      const lngs = line.map(point => point.lon);
      const lats = line.map(point => point.lat);
      const minLng = Math.min(...lngs);
      const maxLng = Math.max(...lngs);
      const minLat = Math.min(...lats);
      const maxLat = Math.max(...lats);
      
      bounds = [[minLng, minLat], [maxLng, maxLat]];
      center = [(minLng + maxLng) / 2, (minLat + maxLat) / 2];
      zoom = 4;
    }

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: center,
      zoom: zoom,
      projection: 'globe' as any
    });

    // Add navigation controls
    map.current.addControl(
      new mapboxgl.NavigationControl({
        visualizePitch: true,
      }),
      'top-right'
    );

    map.current.on('style.load', () => {
      // Add atmosphere and fog effects
      map.current?.setFog({
        color: 'rgb(255, 255, 255)',
        'high-color': 'rgb(200, 200, 225)',
        'horizon-blend': 0.2,
      });

      // Add path line if we have data
      if (line && line.length > 0) {
        const coordinates = line.map(point => [point.lon, point.lat]);
        
        map.current?.addSource('route', {
          'type': 'geojson',
          'data': {
            'type': 'Feature',
            'properties': {},
            'geometry': {
              'type': 'LineString',
              'coordinates': coordinates
            }
          }
        });

        map.current?.addLayer({
          'id': 'route',
          'type': 'line',
          'source': 'route',
          'layout': {
            'line-join': 'round',
            'line-cap': 'round'
          },
          'paint': {
            'line-color': 'hsl(var(--accent))',
            'line-width': 3
          }
        });

        // Add start marker
        if (start) {
          new mapboxgl.Marker({ color: 'hsl(var(--success))' })
            .setLngLat([start.lon, start.lat])
            .setPopup(new mapboxgl.Popup().setHTML(`<strong>Start</strong><br>Lat: ${start.lat.toFixed(4)}<br>Lon: ${start.lon.toFixed(4)}`))
            .addTo(map.current);
        }

        // Add end marker
        if (end) {
          new mapboxgl.Marker({ color: 'hsl(var(--destructive))' })
            .setLngLat([end.lon, end.lat])
            .setPopup(new mapboxgl.Popup().setHTML(`<strong>End</strong><br>Lat: ${end.lat.toFixed(4)}<br>Lon: ${end.lon.toFixed(4)}`))
            .addTo(map.current);
        }

        // Fit to bounds if we calculated them
        if (bounds) {
          map.current?.fitBounds(bounds, { padding: 50 });
        }
      }
    });

    // Cleanup
    return () => {
      map.current?.remove();
    };
  };

  const handleTokenSubmit = () => {
    if (tokenInput.trim()) {
      setMapboxToken(tokenInput.trim());
      setShowTokenInput(false);
      localStorage.setItem('mapbox_token', tokenInput.trim());
    }
  };

  useEffect(() => {
    // Check for saved token first
    const savedToken = localStorage.getItem('mapbox_token');
    if (savedToken) {
      setMapboxToken(savedToken);
      setShowTokenInput(false);
    }
  }, []);

  useEffect(() => {
    if (mapboxToken && !showTokenInput) {
      initializeMap(mapboxToken);
    }
    
    return () => {
      map.current?.remove();
    };
  }, [mapboxToken, showTokenInput, line, start, end]);

  if (showTokenInput) {
    return (
      <Card className="border-accent/20">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Map className="h-5 w-5 text-accent" />
            <span>Float Path Visualization</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-warning/10 rounded-lg border border-warning/20">
              <div className="flex items-center space-x-2 mb-2">
                <Key className="h-4 w-4 text-warning" />
                <h3 className="font-semibold text-warning">Mapbox Token Required</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                To display the interactive map, please enter your Mapbox public token. 
                You can get one free at <a href="https://mapbox.com/" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">mapbox.com</a>
              </p>
              <div className="flex space-x-2">
                <Input
                  type="text"
                  placeholder="pk.eyJ1IjoieW91cnVzZXJuYW1lIiwiYSI6IklEX0hlcmUifQ..."
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  className="font-mono text-xs"
                />
                <Button onClick={handleTokenSubmit} disabled={!tokenInput.trim()}>
                  Load Map
                </Button>
              </div>
            </div>
            
            {/* Show path info even without map */}
            {line && line.length > 0 && (
              <div className="p-4 bg-background/80 rounded-lg border border-accent/20">
                <h3 className="font-semibold mb-2">Float Trajectory Data</h3>
                <p className="text-sm text-muted-foreground mb-2">
                  Path with {line.length} waypoints ready to display
                </p>
                
                {start && end && (
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center space-x-2">
                      <Navigation className="h-3 w-3 text-success" />
                      <span>Start: {start.lat.toFixed(4)}°, {start.lon.toFixed(4)}°</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="h-3 w-3 rounded-full bg-destructive"></div>
                      <span>End: {end.lat.toFixed(4)}°, {end.lon.toFixed(4)}°</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-accent/20">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Map className="h-5 w-5 text-accent" />
            <span>Float Path Visualization</span>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setShowTokenInput(true)}
            className="text-xs"
          >
            Change Token
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <div 
            ref={mapContainer} 
            className="w-full h-[400px] rounded-lg shadow-lg"
            style={{ minHeight: '400px' }}
          />
          
          {/* Path stats overlay */}
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