import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Activity, MapPin, Calendar, Building } from "lucide-react";

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

export const FloatOverview = () => {
  const [floats, setFloats] = useState<FloatData[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    const fetchFloats = async () => {
      try {
        const response = await fetch('/api/floats?limit=6');
        if (response.ok) {
          const data = await response.json();
          setFloats(data.floats || []);
          
          // Get total count
          const countResponse = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: "how many floats" })
          });
          if (countResponse.ok) {
            const countData = await countResponse.json();
            setTotalCount(countData.data_count || 0);
          }
        }
      } catch (error) {
        console.error('Failed to fetch floats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchFloats();
  }, []);

  if (loading) {
    return (
      <Card className="shadow-ocean">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-primary" />
            <span>Active Float Network</span>
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
            <span>Active Float Network</span>
          </CardTitle>
          <Badge variant="secondary" className="text-lg px-3 py-1">
            {totalCount} Total Floats
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {floats.map((float_data) => (
            <Card key={float_data.float_id} className="border-l-4 border-l-primary hover:shadow-glow transition-smooth">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-lg">Float {float_data.float_id}</h3>
                  <Badge variant="outline" className="text-xs">
                    {float_data.project_name}
                  </Badge>
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex items-center space-x-2 text-muted-foreground">
                    <Building className="h-4 w-4" />
                    <span>{float_data.institution}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2 text-muted-foreground">
                    <MapPin className="h-4 w-4" />
                    <span>
                      {float_data.deployment_lat?.toFixed(2)}°, {float_data.deployment_lon?.toFixed(2)}°
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2 text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>
                      {float_data.deployment_date ? 
                        new Date(float_data.deployment_date).toLocaleDateString() : 
                        'Unknown'
                      }
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
          ))}
        </div>
      </CardContent>
    </Card>
  );
};