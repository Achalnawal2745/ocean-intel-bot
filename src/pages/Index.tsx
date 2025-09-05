import React, { useState } from "react";
import { Header } from "@/components/Header";
import { QueryInterface } from "@/components/QueryInterface";
import { DataVisualization } from "@/components/DataVisualization";
import { FloatOverview } from "@/components/FloatOverview";
import { UploadSection } from "@/components/UploadSection";
import { ConnectionStatus } from "@/components/ConnectionStatus";

const Index = () => {
  const [queryResult, setQueryResult] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string>("");
  const [connected, setConnected] = useState<boolean>(true);

  const handleQueryResult = (result: any) => {
    setQueryResult(result);
    if (result.session_id) {
      setSessionId(result.session_id);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-6 py-8 space-y-8">
        {/* Hero Section */}
        <section className="text-center py-12">
          <h1 className="text-5xl font-bold text-gradient mb-6">
            ARGO Ocean Explorer
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Discover the depths of our oceans through autonomous profiling floats.
            Query oceanographic data with natural language and explore temperature,
            salinity, and pressure profiles from around the globe.
          </p>
        </section>

        {/* Connection Status */}
        <ConnectionStatus onStatusChange={setConnected} />

        {/* Query Interface */}
        <QueryInterface
          onQueryResult={handleQueryResult}
          sessionId={sessionId}
          connected={connected}
        />

        {/* Data Visualization */}
        {queryResult && (
          <DataVisualization
            result={queryResult}
          />
        )}

        {/* Float Overview */}
        <FloatOverview />

        {/* Upload Section */}
        <UploadSection />
      </main>
    </div>
  );
};

export default Index;
