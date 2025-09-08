"use client";

import { useState } from "react";
import MainLayout from "~/components/layouts/main-layout";
import UserChat from "~/components/user-chat";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Badge } from "~/components/ui/badge";
import { BotIcon, CodeIcon, NetworkIcon, SparklesIcon } from "lucide-react";

export default function UserModePage() {
  const [generatedSkills, setGeneratedSkills] = useState<any[]>([]);
  const [usedSkills, setUsedSkills] = useState<string[]>([]);

  const handleSkillGenerated = (skill: any) => {
    setGeneratedSkills(prev => [...prev, skill]);
  };

  const handleSkillUsed = (skillName: string) => {
    setUsedSkills(prev => {
      if (!prev.includes(skillName)) {
        return [...prev, skillName];
      }
      return prev;
    });
  };

  return (
    <MainLayout>
      <div className="container mx-auto p-6 h-screen flex flex-col">
        <div className="mb-6">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <SparklesIcon className="h-8 w-8 text-primary" />
            AutoLearn User Mode
          </h1>
          <p className="text-muted-foreground mt-2">
            Chat with an AI agent that can use existing skills and create new ones on demand
          </p>
        </div>

        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Chat Interface */}
          <div className="lg:col-span-2">
            <UserChat 
              onSkillGenerated={handleSkillGenerated}
              onSkillUsed={handleSkillUsed}
            />
          </div>

          {/* Sidebar with Skills Info */}
          <div className="space-y-6">
            {/* Generated Skills */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CodeIcon className="h-5 w-5" />
                  Generated Skills
                  <Badge variant="secondary">{generatedSkills.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {generatedSkills.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No skills generated yet. Ask the AI to help you with a task it can't do!
                  </p>
                ) : (
                  <div className="space-y-2">
                    {generatedSkills.map((skill, index) => (
                      <div key={index} className="p-2 border rounded-lg">
                        <div className="font-medium text-sm">{skill.name || `Skill ${index + 1}`}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {skill.description || "No description"}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Used Skills */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <NetworkIcon className="h-5 w-5" />
                  Used Skills
                  <Badge variant="secondary">{usedSkills.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {usedSkills.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No skills used yet. The AI will automatically use relevant skills for your requests.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {usedSkills.map((skillName, index) => (
                      <Badge key={index} variant="outline">
                        {skillName}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Status/Help */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <BotIcon className="h-5 w-5" />
                  How it Works
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
                  <p>Ask the AI assistant to help you with any task</p>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5 flex-shrink-0" />
                  <p>It will use existing skills when possible</p>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
                  <p>For new tasks, it will generate skills automatically</p>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-orange-500 mt-1.5 flex-shrink-0" />
                  <p>Generated skills become available for future use</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
