import React, { useState } from "react";
import { Send, Loader2, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";

interface QueryInterfaceProps {
  onQueryResult: (result: any) => void;
  sessionId: string;
}

export const QueryInterface: React.FC<QueryInterfaceProps> = ({ 
  onQueryResult, 
  sessionId 
}) => {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([
    "How many floats are in the Arabian Sea?",
    "Show me temperature profiles for float 2902094",
    "Find floats near latitude 15.0, longitude 60.0"
  ]);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          session_id: sessionId
        }),
      });

      if (!response.ok) {
        throw new Error('Query failed');
      }

      const result = await response.json();
      onQueryResult(result);
      
      if (result.suggestions) {
        setSuggestions(result.suggestions);
      }
      
      setQuery("");
      
      toast({
        title: "Query processed",
        description: "Your oceanographic data query has been completed.",
      });
    } catch (error) {
      toast({
        title: "Query failed",
        description: "Please check your connection and try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
  };

  return (
    <Card className="shadow-ocean">
      <CardContent className="p-6">
        <div className="space-y-6">
          <div className="flex items-center space-x-3 mb-4">
            <MessageCircle className="h-6 w-6 text-primary" />
            <h2 className="text-2xl font-semibold">Natural Language Query</h2>
          </div>
          
          <form onSubmit={handleSubmit} className="flex space-x-3">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about ARGO floats... e.g., 'Show temperature data for float 2902094'"
              className="flex-1 text-base"
              disabled={isLoading}
            />
            <Button 
              type="submit" 
              disabled={!query.trim() || isLoading}
              className="ocean-gradient hover:shadow-glow transition-smooth"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>

          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">
              Suggested Queries:
            </h3>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion, index) => (
                <Badge
                  key={index}
                  variant="secondary"
                  className="cursor-pointer transition-smooth hover:bg-primary hover:text-primary-foreground"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};