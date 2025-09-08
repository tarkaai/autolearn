"use client";

import { useState, useEffect } from "react";
import MainLayout from "~/components/layouts/main-layout";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "~/components/ui/card";
import { Label } from "~/components/ui/label";
import { Input } from "~/components/ui/input";
import { Button } from "~/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import dynamic from "next/dynamic";
import { apiClient } from "~/lib/api-client";
import type { SkillMeta, RunResponse } from "~/lib/api-client";
import { useWebSocketContext } from "~/lib/websocket";
import type { SkillExecutedEvent } from "~/lib/websocket";
import { toast } from "sonner";

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { ssr: false }
);

interface ExecutionResult {
  id: string;
  skill: string;
  inputs: Record<string, any>;
  output: any;
  error?: string;
  timestamp: Date;
}

export default function ExecutePage() {
  const [skills, setSkills] = useState<SkillMeta[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSkillName, setSelectedSkillName] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillMeta | null>(null);
  const [inputs, setInputs] = useState<Record<string, any>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [results, setResults] = useState<ExecutionResult[]>([]);
  
  // Get WebSocket context for real-time updates
  const webSocket = useWebSocketContext();
  
  // Fetch skills and set up WebSocket listeners
  useEffect(() => {
    fetchSkills();
    
    // Listen for WebSocket events
    if (webSocket.socket) {
      // When a skill is executed
      webSocket.socket.on("skill_executed", (executionData: SkillExecutedEvent) => {
        // Add the execution result to our history
        const result: ExecutionResult = {
          id: new Date().toISOString(),
          skill: executionData.skill,
          inputs: executionData.args,
          output: executionData.result,
          timestamp: new Date(executionData.timestamp)
        };
        
        setResults(prev => [result, ...prev]);
      });
      
      // When a new skill is added
      webSocket.socket.on("skill_added", () => {
        // Refresh the skills list
        fetchSkills();
      });
    }
    
    return () => {
      // Clean up event listeners
      if (webSocket.socket) {
        webSocket.socket.off("skill_executed");
        webSocket.socket.off("skill_added");
      }
    };
  }, [webSocket.socket]);
  
  // Fetch skills list from API
  const fetchSkills = async () => {
    try {
      setIsLoading(true);
      const skillsList = await apiClient.listTools();
      setSkills(skillsList);
      
      // Select the first skill by default if available
      if (skillsList.length > 0 && !selectedSkillName) {
        if (skillsList[0]) {
          setSelectedSkillName(skillsList[0].name);
          setSelectedSkill(skillsList[0]);
          setInputs({});
        }
      }
    } catch (error) {
      toast.error("Failed to load skills");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSkillSelect = (skillName: string) => {
    const skill = skills.find(s => s.name === skillName);
    if (skill) {
      setSelectedSkillName(skillName);
      setSelectedSkill(skill);
      setInputs({});
    }
  };
  
  const handleInputChange = (name: string, value: any) => {
    setInputs(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleExecute = async () => {
    if (!selectedSkill) return;
    
    setIsExecuting(true);
    
    // Validate inputs
    const formattedInputs: Record<string, any> = {};
    for (const [key, type] of Object.entries(selectedSkill.inputs)) {
      if (type === "number" && inputs[key]) {
        formattedInputs[key] = Number(inputs[key]);
      } else {
        formattedInputs[key] = inputs[key];
      }
    }
    
    try {
      // Execute the skill through the API
      const response = await apiClient.runSkill({
        name: selectedSkill.name,
        args: formattedInputs
      });
      
      // Add result to history
      const result: ExecutionResult = {
        id: new Date().toISOString(),
        skill: selectedSkill.name,
        inputs: formattedInputs,
        output: response.result,
        error: response.error,
        timestamp: new Date()
      };
      
      setResults(prev => [result, ...prev]);
      
      if (response.success) {
        toast.success(`Skill ${selectedSkill.name} executed successfully`);
      } else {
        toast.error(`Skill execution failed: ${response.error}`);
      }
    } catch (error) {
      toast.error(`Failed to execute skill: ${(error as Error).message}`);
      console.error(error);
      
      // Add error result
      const result: ExecutionResult = {
        id: new Date().toISOString(),
        skill: selectedSkill.name,
        inputs: formattedInputs,
        output: null,
        error: (error as Error).message,
        timestamp: new Date()
      };
      
      setResults(prev => [result, ...prev]);
    } finally {
      setIsExecuting(false);
    }
  };
  
  return (
    <MainLayout>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Execution Form */}
        <Card>
          <CardHeader>
            <CardTitle>Execute Skill</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <div className="py-4 text-center text-muted-foreground">
                Loading skills...
              </div>
            ) : skills.length === 0 ? (
              <div className="py-4 text-center text-muted-foreground">
                No skills available. Create a skill first.
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="skill">Skill</Label>
                  <Select
                    value={selectedSkillName || ""}
                    onValueChange={handleSkillSelect}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a skill" />
                    </SelectTrigger>
                    <SelectContent>
                      {skills.map(skill => (
                        <SelectItem key={skill.name} value={skill.name}>
                          {skill.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedSkill && (
                    <p className="text-sm text-muted-foreground">
                      {selectedSkill.description}
                    </p>
                  )}
                </div>
                
                {selectedSkill && (
                  <div className="border-t pt-4">
                    <h3 className="font-medium mb-2">Input Parameters</h3>
                    <div className="space-y-3">
                      {Object.entries(selectedSkill.inputs).map(([name, type]) => (
                        <div key={name} className="space-y-2">
                          <Label htmlFor={name}>
                            {name} ({type})
                          </Label>
                          <Input
                            id={name}
                            type={type === "number" ? "number" : "text"}
                            value={inputs[name] || ""}
                            onChange={(e) => handleInputChange(name, e.target.value)}
                            placeholder={`Enter ${name}`}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
          <CardFooter>
            <Button 
              onClick={handleExecute} 
              disabled={isLoading || isExecuting || !selectedSkill}
              className="w-full"
            >
              {isExecuting ? "Executing..." : "Execute Skill"}
            </Button>
          </CardFooter>
        </Card>
        
        {/* Results View */}
        <Card>
          <CardHeader>
            <CardTitle>Execution Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 max-h-[calc(100vh-16rem)] overflow-y-auto">
              {results.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  No execution results yet. Execute a skill to see results here.
                </div>
              ) : (
                results.map(result => (
                  <Card key={result.id} className="overflow-hidden">
                    <CardHeader className="bg-muted py-2 px-4">
                      <div className="flex justify-between items-center">
                        <div className="font-medium">{result.skill}</div>
                        <div className="text-xs text-muted-foreground">
                          {result.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="grid grid-cols-2">
                        <div className="p-3 border-r">
                          <div className="text-xs font-medium mb-1">Inputs</div>
                          <div className="rounded bg-muted/50 p-2">
                            <pre className="text-xs whitespace-pre-wrap">
                              {JSON.stringify(result.inputs, null, 2)}
                            </pre>
                          </div>
                        </div>
                        <div className="p-3">
                          <div className="text-xs font-medium mb-1">
                            {result.error ? "Error" : "Output"}
                          </div>
                          <div 
                            className={`rounded p-2 ${
                              result.error 
                                ? "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300" 
                                : "bg-muted/50"
                            }`}
                          >
                            <pre className="text-xs whitespace-pre-wrap">
                              {result.error 
                                ? result.error 
                                : JSON.stringify(result.output, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
