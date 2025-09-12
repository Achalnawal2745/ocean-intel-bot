import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Activity, MapPin, Calendar, Building } from "lucide-react";
import { buildApiUrl, API_CONFIG } from "@/config/api";

interface FloatData {
  float_id: number;
  pi_name: string;
  institution: string;
  deployment_date: string;
  deployment_lat: number;
  deployment_lon: number;
  project_name: string;
  data_center: string;
}




export const FloatOverview = ({ connected = true }: { connected?: boolean }) => {
  const [floats, setFloats] = useState<FloatData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchFloats = async () => {
      if (!connected) {
        setFloats([]);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.FLOATS, { limit: '9' }));
        if (response.ok) {
          const data = await response.json();
          const rawFloats = Array.isArray(data.floats) ? data.floats : [];
          const baseFloats: FloatData[] = rawFloats.map((r: any) => ({
            float_id: r.float_id,
            pi_name: r.pi_name,
            institution: r.operating_institute,
            deployment_date: r.launch_date,
            deployment_lat: r.launch_latitude,
            deployment_lon: r.launch_longitude,
            project_name: r.project_name,
            data_center: r.float_owner,
          }));

          if (!cancelled) setFloats(baseFloats);
        }
      } catch (error: any) {
        console.error('Failed to fetch floats:', error);
        if (!cancelled) setError(error?.message || 'Failed to load floats');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchFloats();
    return () => { cancelled = true; };
  }, [connected]);


  if (!connected) {
    return (
      <Card className="shadow-ocean">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-primary" />
            <span>Float Network</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            Backend disconnected. Connect the backend to view floats.
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="shadow-ocean">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-primary" />
            <span>Float Network</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-destructive">{error}</div>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card className="shadow-ocean">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-primary" />
            <span>Float Network</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-ocean">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-primary" />
            <span>Float Network</span>
          </CardTitle>
          <Badge variant="secondary" className="text-lg px-3 py-1">
            {floats.length} Floats
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {floats.map((float_data, idx) => {
            const lat = float_data.deployment_lat;
            const lon = float_data.deployment_lon;
            const dateStr = float_data.deployment_date;
            const cardBorder = "border-l-muted";
            const key = `${float_data.float_id}-${idx}`;
            return (
              <Card key={key} className={`border-l-4 ${cardBorder} hover:shadow-glow transition-smooth`}>
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-lg">Float {float_data.float_id}</h3>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {float_data.project_name}
                      </Badge>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Building className="h-4 w-4" />
                      <span>{float_data.institution}</span>
                    </div>

                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <MapPin className="h-4 w-4" />
                      <span>
                        {Number.isFinite(lat) && Number.isFinite(lon) ? `${(lat as number).toFixed(2)}°, ${(lon as number).toFixed(2)}°` : 'Unknown'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>
                        {dateStr ? new Date(dateStr).toLocaleDateString() : 'Unknown'}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2">
                    <p className="text-sm font-medium">PI: {float_data.pi_name}</p>
                    <p className="text-xs text-muted-foreground">
                      Data Center: {float_data.data_center}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
