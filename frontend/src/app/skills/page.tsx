"use client";

import { useState, useEffect } from "react";
import MainLayout from "~/components/layouts/main-layout";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Button } from "~/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Textarea } from "~/components/ui/textarea";
import dynamic from "next/dynamic";
import { apiClient } from "~/lib/api-client";
import type { SkillMeta } from "~/lib/api-client";
import { useWebSocketContext } from "~/lib/websocket";
import type { SkillAddedEvent } from "~/lib/websocket";
import { toast } from "sonner";

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { ssr: false }
);

export default function SkillsPage() {
  // State for skills and selection
  const [skills, setSkills] = useState<SkillMeta[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSkillName, setSelectedSkillName] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillMeta | null>(null);
  const [skillCode, setSkillCode] = useState<string>("");
  const [editorCode, setEditorCode] = useState<string>("");
  const [isCodeLoading, setIsCodeLoading] = useState(false);
  const [isNewSkillDialogOpen, setIsNewSkillDialogOpen] = useState(false);
  const [isImproveSkillDialogOpen, setIsImproveSkillDialogOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isImproving, setIsImproving] = useState(false);
  const [newSkillForm, setNewSkillForm] = useState({
    name: "",
    description: "",
    prompt: ""
  });
  const [improvementPrompt, setImprovementPrompt] = useState("");

  // Get WebSocket context for real-time updates
  const webSocket = useWebSocketContext();

  // Fetch skills on component mount
  useEffect(() => {
    fetchSkills();
    
    // Listen for WebSocket events
    if (webSocket.socket) {
      // When a new skill is added, refresh the skills list
      webSocket.socket.on("skill_added", (skillData: SkillAddedEvent) => {
        toast.success(`New skill added: ${skillData.name}`);
        fetchSkills();
      });
    }

    return () => {
      // Clean up event listeners
      if (webSocket.socket) {
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
          fetchSkillCode(skillsList[0].name);
        }
      }
    } catch (error) {
      toast.error("Failed to load skills");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch code for a selected skill
  const fetchSkillCode = async (name: string) => {
    try {
      setIsCodeLoading(true);
      const response = await apiClient.getSkillCode(name);
      setSkillCode(response.code);
      setEditorCode(response.code);
    } catch (error) {
      toast.error(`Failed to load code for ${name}`);
      console.error(error);
    } finally {
      setIsCodeLoading(false);
    }
  };

  // Handle skill selection
  const handleSkillSelect = (name: string) => {
    const skill = skills.find(s => s.name === name);
    if (skill) {
      setSelectedSkillName(name);
      setSelectedSkill(skill);
      fetchSkillCode(name);
    }
  };

  // Handle code changes in the editor
  const handleCodeChange = (value: string | undefined) => {
    if (value !== undefined) {
      setEditorCode(value);
    }
  };

  // Handle saving edited code
  const handleSaveCode = async () => {
    if (!selectedSkill) return;
    
    try {
      setIsSaving(true);
      // Register the updated skill
      await apiClient.registerSkill({
        meta: selectedSkill,
        code: editorCode
      });
      
      // Update the stored code
      setSkillCode(editorCode);
      toast.success(`Skill ${selectedSkill.name} updated successfully`);
    } catch (error) {
      toast.error(`Failed to save skill: ${(error as Error).message}`);
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  // Reset editor to original code
  const handleResetCode = () => {
    setEditorCode(skillCode);
    toast.info("Code reset to original");
  };

  // Handle generating a new skill
  const handleNewSkillSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      // Generate skill using OpenAI
      const generateResponse = await apiClient.generateSkill({
        description: newSkillForm.prompt,
        name: newSkillForm.name || undefined
      });
      
      if (!generateResponse.success || !generateResponse.meta || !generateResponse.code) {
        throw new Error(generateResponse.error || "Failed to generate skill");
      }
      
      // Update the meta with user-provided description
      const metaWithDescription = {
        ...generateResponse.meta,
        description: newSkillForm.description || generateResponse.meta.description
      };
      
      // Register the generated skill
      await apiClient.registerSkill({
        code: generateResponse.code,
        meta: metaWithDescription
      });
      
      toast.success(`Skill ${metaWithDescription.name} created successfully`);
      
      // Reset form and close dialog
      setNewSkillForm({
        name: "",
        description: "",
        prompt: ""
      });
      setIsNewSkillDialogOpen(false);
      
      // Refresh skills list
      await fetchSkills();
    } catch (error) {
      toast.error(`Failed to create skill: ${(error as Error).message}`);
      console.error(error);
    }
  };

  // Handle improving a skill
  const handleImproveSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedSkill || !improvementPrompt.trim()) return;
    
    try {
      setIsImproving(true);
      
      // Call the improve skill API
      const improveResponse = await apiClient.improveSkill({
        skill_name: selectedSkill.name,
        current_code: skillCode,
        improvement_prompt: improvementPrompt
      });
      
      if (!improveResponse.success || !improveResponse.code) {
        throw new Error(improveResponse.error || "Failed to improve skill");
      }
      
      // Update the editor with the improved code
      setEditorCode(improveResponse.code);
      
      toast.success(`Skill ${selectedSkill.name} improved successfully! Review and save the changes.`);
      
      // Reset form and close dialog
      setImprovementPrompt("");
      setIsImproveSkillDialogOpen(false);
      
    } catch (error) {
      toast.error(`Failed to improve skill: ${(error as Error).message}`);
      console.error(error);
    } finally {
      setIsImproving(false);
    }
  };

  // Handle deleting a skill
  const handleDeleteSkill = async () => {
    if (!selectedSkill) return;
    
    if (confirm(`Are you sure you want to delete the skill "${selectedSkill.name}"?`)) {
      try {
        await apiClient.deleteSkill(selectedSkill.name);
        toast.success(`Skill ${selectedSkill.name} deleted successfully`);
        
        // Reset selected skill
        setSelectedSkill(null);
        setSelectedSkillName(null);
        setSkillCode("");
        setEditorCode("");
        
        // Refresh skills list
        await fetchSkills();
      } catch (error) {
        toast.error(`Failed to delete skill: ${(error as Error).message}`);
        console.error(error);
      }
    }
  };

  return (
    <MainLayout>
      <div className="h-[calc(100vh-8rem)] grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Skills List */}
        <div className="md:col-span-1">
          <Card className="h-full flex flex-col">
            <CardHeader className="flex flex-row justify-between items-center flex-shrink-0">
              <CardTitle>Skills</CardTitle>
              <Dialog open={isNewSkillDialogOpen} onOpenChange={setIsNewSkillDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm">New Skill</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create New Skill</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleNewSkillSubmit} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Name (Optional)</Label>
                      <Input 
                        id="name" 
                        value={newSkillForm.name} 
                        onChange={(e) => setNewSkillForm({...newSkillForm, name: e.target.value})}
                        placeholder="e.g., calculate_area (will be auto-generated if blank)"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="description">Description</Label>
                      <Input 
                        id="description" 
                        value={newSkillForm.description} 
                        onChange={(e) => setNewSkillForm({...newSkillForm, description: e.target.value})}
                        placeholder="e.g., Calculate area of geometric shapes"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="prompt">Natural Language Prompt</Label>
                      <Textarea 
                        id="prompt" 
                        value={newSkillForm.prompt} 
                        onChange={(e) => setNewSkillForm({...newSkillForm, prompt: e.target.value})}
                        placeholder="Create a function that calculates the area of different shapes like circles, rectangles, and triangles..."
                        rows={5}
                        required
                      />
                    </div>
                    <div className="flex justify-end">
                      <Button type="submit">Generate Skill</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="py-4 text-center text-muted-foreground">
                  Loading skills...
                </div>
              ) : skills.length === 0 ? (
                <div className="py-4 text-center text-muted-foreground">
                  No skills available. Create a new skill to get started.
                </div>
              ) : (
                <div className="space-y-2">
                  {skills.map((skill) => (
                    <div 
                      key={skill.name}
                      onClick={() => handleSkillSelect(skill.name)}
                      className={`p-3 rounded-md cursor-pointer ${
                        selectedSkillName === skill.name 
                          ? "bg-primary text-primary-foreground" 
                          : "bg-card hover:bg-muted"
                      }`}
                    >
                      <div className="font-medium">{skill.name}</div>
                      <div className="text-sm truncate">{skill.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Skill Editor */}
        <div className="md:col-span-3">
          <Card className="h-full flex flex-col">
            <CardHeader className="flex flex-row justify-between items-center flex-shrink-0">
              <div>
                <CardTitle>{selectedSkill?.name || "No skill selected"}</CardTitle>
                {selectedSkill && (
                  <p className="text-sm text-muted-foreground">{selectedSkill.description}</p>
                )}
              </div>
              {selectedSkill && (
                <div className="flex space-x-2">
                  <Dialog open={isImproveSkillDialogOpen} onOpenChange={setIsImproveSkillDialogOpen}>
                    <DialogTrigger asChild>
                      <Button 
                        variant="outline" 
                        size="sm"
                      >
                        Improve Skill
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>Improve Skill: {selectedSkill.name}</DialogTitle>
                      </DialogHeader>
                      <form onSubmit={handleImproveSkill} className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="improvement-prompt">How would you like to improve this skill?</Label>
                          <Textarea 
                            id="improvement-prompt" 
                            value={improvementPrompt} 
                            onChange={(e) => setImprovementPrompt(e.target.value)}
                            placeholder="e.g., Add error handling, support more file formats, improve performance, add validation..."
                            rows={6}
                            required
                          />
                        </div>
                        <div className="flex justify-end space-x-2">
                          <Button 
                            type="button" 
                            variant="outline" 
                            onClick={() => setIsImproveSkillDialogOpen(false)}
                          >
                            Cancel
                          </Button>
                          <Button type="submit" disabled={isImproving}>
                            {isImproving ? "Improving..." : "Improve Skill"}
                          </Button>
                        </div>
                      </form>
                    </DialogContent>
                  </Dialog>
                  <Button 
                    variant="destructive" 
                    size="sm" 
                    onClick={handleDeleteSkill}
                  >
                    Delete
                  </Button>
                </div>
              )}
            </CardHeader>
            <CardContent className="flex-1 min-h-0">
              {!selectedSkill ? (
                <div className="py-12 text-center text-muted-foreground">
                  Select a skill to view and edit
                </div>
              ) : (
                <Tabs defaultValue="code" className="w-full h-full flex flex-col">
                  <TabsList className="flex-shrink-0">
                    <TabsTrigger value="code">Code</TabsTrigger>
                    <TabsTrigger value="metadata">Metadata</TabsTrigger>
                  </TabsList>
                  <TabsContent value="code" className="h-[60vh] flex flex-col">
                    {isCodeLoading ? (
                      <div className="h-full flex items-center justify-center">
                        <p>Loading code...</p>
                      </div>
                    ) : (
                      <>
                        <div className="flex-1 min-h-0 border rounded-md overflow-hidden">
                          <MonacoEditor
                            height="100%"
                            language="python"
                            theme="vs-dark"
                            value={editorCode}
                            onChange={handleCodeChange}
                            options={{
                              minimap: { enabled: false },
                              scrollBeyondLastLine: false,
                              automaticLayout: true,
                              fontSize: 14,
                            }}
                          />
                        </div>
                        <div className="flex justify-end mt-4 space-x-2 flex-shrink-0">
                          <Button 
                            variant="outline" 
                            onClick={handleResetCode}
                            disabled={isSaving || editorCode === skillCode}
                          >
                            Reset
                          </Button>
                          <Button 
                            onClick={handleSaveCode}
                            disabled={isSaving || editorCode === skillCode}
                          >
                            {isSaving ? "Saving..." : "Save Changes"}
                          </Button>
                        </div>
                      </>
                    )}
                  </TabsContent>
                  <TabsContent value="metadata" className="flex-1 overflow-y-auto">
                    {selectedSkill && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Name</Label>
                            <Input value={selectedSkill.name} readOnly />
                          </div>
                          <div className="space-y-2">
                            <Label>Version</Label>
                            <Input value={selectedSkill.version} readOnly />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label>Description</Label>
                          <Textarea value={selectedSkill.description} rows={3} readOnly />
                        </div>
                        <div className="space-y-2">
                          <Label>Inputs</Label>
                          <div className="rounded-md border max-h-64 overflow-auto">
                            <pre className="p-4 text-sm">
                              {JSON.stringify(selectedSkill.inputs, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
