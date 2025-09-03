import React from "react";
import { Waves, Activity, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Header = () => {
  return (
    <header className="ocean-gradient shadow-ocean">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Waves className="h-10 w-10 text-primary-foreground" />
              <div className="absolute -top-1 -right-1 h-4 w-4 bg-accent rounded-full animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-primary-foreground">
                ARGO Explorer
              </h1>
              <p className="text-sm text-primary-foreground/80">
                Oceanographic Data Platform
              </p>
            </div>
          </div>
          
          <nav className="flex items-center space-x-2">
            <Button variant="ghost" size="sm" className="text-primary-foreground hover:bg-primary-foreground/10">
              <Activity className="h-4 w-4 mr-2" />
              Live Data
            </Button>
            <Button variant="ghost" size="sm" className="text-primary-foreground hover:bg-primary-foreground/10">
              <Upload className="h-4 w-4 mr-2" />
              Upload
            </Button>
          </nav>
        </div>
      </div>
    </header>
  );
};