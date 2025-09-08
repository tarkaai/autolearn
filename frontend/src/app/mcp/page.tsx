"use client";

import MainLayout from "~/components/layouts/main-layout";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { apiClient } from "~/lib/api-client";
import { useWebSocketContext } from "~/lib/websocket";
import type { MCPUpdatedEvent } from "~/lib/websocket";
import { toast } from "sonner";

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { ssr: false }
);

export default function MCPPage() {
  const [mcpSpec, setMcpSpec] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  
  // Get WebSocket context for real-time updates
  const webSocket = useWebSocketContext();
  
  // Fetch MCP spec and set up WebSocket listeners
  useEffect(() => {
    fetchMCPSpec();
    
    // Listen for WebSocket events
    if (webSocket.socket) {
      // When the MCP spec is updated
      webSocket.socket.on("mcp_updated", (specData: MCPUpdatedEvent) => {
        toast.info("MCP specification updated");
        setMcpSpec(specData);
        setLastUpdated(new Date());
      });
    }
    
    return () => {
      // Clean up event listeners
      if (webSocket.socket) {
        webSocket.socket.off("mcp_updated");
      }
    };
  }, [webSocket.socket]);
  
  // Fetch MCP spec from API
  const fetchMCPSpec = async () => {
    try {
      setIsLoading(true);
      const spec = await apiClient.getMCPSpec();
      setMcpSpec(spec);
      setLastUpdated(new Date());
    } catch (error) {
      toast.error("Failed to load MCP specification");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold">MCP Specification</h2>
          <div className="text-sm text-muted-foreground">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>MCP Schema</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[70vh]">
              {isLoading ? (
                <div className="h-full flex items-center justify-center">
                  <p>Loading MCP specification...</p>
                </div>
              ) : mcpSpec ? (
                <MonacoEditor
                  height="100%"
                  language="json"
                  theme="vs-dark"
                  value={JSON.stringify(mcpSpec, null, 2)}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    fontSize: 14,
                  }}
                />
              ) : (
                <div className="h-full flex items-center justify-center">
                  <p>No MCP specification available</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
