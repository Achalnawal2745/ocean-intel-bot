import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { buildApiUrl, API_CONFIG } from "@/config/api";
import { Upload, File, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export const UploadSection = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "success" | "error">("idle");
  const [uploadAvailable, setUploadAvailable] = useState<boolean | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    let cancelled = false;
    const checkEndpoint = async () => {
      try {
        const url = buildApiUrl(API_CONFIG.ENDPOINTS.UPLOAD_NETCDF);
        const resp = await fetch(url, { method: 'OPTIONS' });
        if (!cancelled) {
          // Treat 404 as unavailable; 200/204/405 likely means route exists or server responds
          setUploadAvailable(resp.status !== 404);
        }
      } catch {
        if (!cancelled) setUploadAvailable(false);
      }
    };
    checkEndpoint();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleFileSelect = () => {
    if (uploadAvailable === false) return;
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.nc')) {
      toast({
        title: "Invalid file type",
        description: "Please select a NetCDF (.nc) file.",
        variant: "destructive",
      });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadStatus("idle");

    try {
      const formData = new FormData();
      formData.append('file', file);

      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.UPLOAD_NETCDF), {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.ok) {
        const result = await response.json();
        setUploadStatus("success");
        toast({
          title: "Upload successful",
          description: `Float ${result.float_id} data uploaded with ${result.profiles_ingested} profiles.`,
        });
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      setUploadStatus("error");
      toast({
        title: "Upload failed",
        description: "There was an error uploading your NetCDF file.",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
      setTimeout(() => {
        setUploadProgress(0);
        setUploadStatus("idle");
      }, 3000);
    }
  };

  const getStatusIcon = () => {
    switch (uploadStatus) {
      case "success":
        return <CheckCircle className="h-5 w-5 text-success" />;
      case "error":
        return <AlertCircle className="h-5 w-5 text-destructive" />;
      default:
        return <Upload className="h-5 w-5" />;
    }
  };

  const getStatusColor = () => {
    switch (uploadStatus) {
      case "success":
        return "border-success/20 bg-success/5";
      case "error":
        return "border-destructive/20 bg-destructive/5";
      default:
        return "border-dashed border-muted-foreground/25 hover:border-primary/50";
    }
  };

  return (
    <Card className="shadow-ocean">
      <CardHeader>
        <CardTitle className="flex items-center space-x-3">
          <Upload className="h-6 w-6 text-primary" />
          <span>Upload NetCDF Data</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {uploadAvailable === false && (
          <div className="p-4 rounded-lg border border-warning/30 bg-warning/5 text-sm">
            NetCDF upload is disabled because the backend does not expose an upload endpoint. If needed, ingest data via the backend's /ingest_metadata API.
          </div>
        )}

        <div
          className={`border-2 rounded-lg p-8 text-center transition-smooth ${uploadAvailable === false ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${getStatusColor()}`}
          onClick={handleFileSelect}
        >
          <div className="space-y-4">
            <div className="flex justify-center">
              {isUploading ? (
                <Loader2 className="h-12 w-12 text-primary animate-spin" />
              ) : (
                <div className="p-3 rounded-full bg-primary/10">
                  {getStatusIcon()}
                </div>
              )}
            </div>

            <div>
              <h3 className="text-lg font-semibold">
                {isUploading ? "Uploading..." : "Drop NetCDF files here"}
              </h3>
              <p className="text-muted-foreground">
                {uploadAvailable === false
                  ? "Upload unavailable on current backend"
                  : isUploading
                    ? "Processing your oceanographic data..."
                    : "Click to browse or drag and drop NetCDF (.nc) files"
                }
              </p>
            </div>

            {isUploading && (
              <div className="max-w-xs mx-auto">
                <Progress value={uploadProgress} className="h-2" />
                <p className="text-sm text-muted-foreground mt-2">
                  {uploadProgress}% complete
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <File className="h-4 w-4 text-muted-foreground" />
            <span>NetCDF format only</span>
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
            <span>Automatic validation</span>
          </div>
          <div className="flex items-center space-x-2">
            <Upload className="h-4 w-4 text-muted-foreground" />
            <span>Max file size: 100MB</span>
          </div>
        </div>

        <Input
          ref={fileInputRef}
          type="file"
          accept=".nc"
          onChange={handleFileUpload}
          className="hidden"
        />
      </CardContent>
    </Card>
  );
};

export default UploadSection;
