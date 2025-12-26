import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface QuerySectionProps {
    onQueryResult: (result: any) => void;
    onLoadingChange: (loading: boolean) => void;
}

const QuerySection = ({ onQueryResult, onLoadingChange }: QuerySectionProps) => {
    const [query, setQuery] = useState("");
    const { toast } = useToast();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!query.trim()) {
            toast({
                title: "Empty Query",
                description: "Please enter a query",
                variant: "destructive",
            });
            return;
        }

        onLoadingChange(true);

        try {
            const response = await fetch("http://127.0.0.1:8000/query", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ query: query.trim() }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            onQueryResult(data);

            toast({
                title: "Query Successful",
                description: "Your query has been processed",
            });
        } catch (error) {
            console.error("Query error:", error);
            toast({
                title: "Query Failed",
                description: error instanceof Error ? error.message : "Failed to process query",
                variant: "destructive",
            });
        } finally {
            onLoadingChange(false);
        }
    };

    return (
        <Card className="shadow-depth">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Send className="h-5 w-5" />
                    Ask a Question
                </CardTitle>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <Textarea
                        placeholder="e.g., Show me temperature data for float 2902296..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="min-h-[100px]"
                    />
                    <Button type="submit" className="w-full">
                        <Send className="mr-2 h-4 w-4" />
                        Submit Query
                    </Button>
                </form>
            </CardContent>
        </Card>
    );
};

export default QuerySection;
