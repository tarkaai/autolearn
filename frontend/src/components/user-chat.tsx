"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { ScrollArea } from "~/components/ui/scroll-area";
import { Separator } from "~/components/ui/separator";
import { 
  apiClient, 
  type ChatResponse, 
  type SkillSuggestion,
  type ConversationHistoryResponse 
} from "~/lib/api-client";
import { toast } from "sonner";
import { 
  SendIcon, 
  BotIcon, 
  UserIcon, 
  SparklesIcon, 
  LightbulbIcon,
  LoaderIcon 
} from "lucide-react";

interface AgentMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  suggestions?: SkillSuggestion[];
  actions?: Array<Record<string, any>>;
  needs_skill_generation?: boolean;
}

interface UserChatProps {
  onSkillGenerated?: (skill: any) => void;
  onSkillUsed?: (skillName: string) => void;
}

export default function UserChat({ onSkillGenerated, onSkillUsed }: UserChatProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SkillSuggestion[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load session from localStorage on mount, or create new one
  useEffect(() => {
    const savedSessionId = localStorage.getItem('autolearn_session_id');
    if (savedSessionId) {
      restoreSession(savedSessionId);
    } else {
      initializeSession();
    }
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const initializeSession = async () => {
    try {
      const response = await apiClient.startAgentSession();
      setSessionId(response.session_id);
      
      // Save session ID to localStorage
      localStorage.setItem('autolearn_session_id', response.session_id);
      
      // Add welcome message
      setMessages([{
        role: "assistant",
        content: "Hi! I'm AutoLearn. I can help you by using existing skills or creating new ones when needed. What would you like to do today?",
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      toast.error("Failed to start conversation session");
      console.error("Session initialization error:", error);
    }
  };

  const restoreSession = async (sessionId: string) => {
    try {
      // Try to get the conversation history from the consumer agent
      const history = await apiClient.getConversationHistory(sessionId);
      if (history && history.messages.length > 0) {
        setSessionId(sessionId);
        
        // Convert backend messages to frontend format, filtering out system messages
        const restoredMessages: AgentMessage[] = history.messages
          .filter(msg => msg.role !== "system") // Filter out system instructions
          .map(msg => ({
            role: msg.role as "user" | "assistant" | "system",
            content: msg.content,
            timestamp: msg.timestamp,
            suggestions: [],
            actions: [],
            needs_skill_generation: false
          }));
        
        // If there are no non-system messages, add the intro message
        if (restoredMessages.length === 0) {
          restoredMessages.push({
            role: "assistant",
            content: "Hi! I'm AutoLearn. I can help you by using existing skills or creating new ones when needed. What would you like to do today?",
            timestamp: new Date().toISOString()
          });
        }
        
        setMessages(restoredMessages);
        toast.success("Restored previous conversation");
      } else {
        // Session doesn't exist or is empty, start a new one
        localStorage.removeItem('autolearn_session_id');
        initializeSession();
      }
    } catch (error) {
      console.error("Session restoration error:", error);
      // Session doesn't exist, start a new one
      localStorage.removeItem('autolearn_session_id');
      initializeSession();
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: AgentMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    const messageText = input.trim();
    setInput("");
    setIsLoading(true);

    try {
      // Send to consumer agent
      const response = await apiClient.chatWithAgent({
        message: messageText,
        session_id: sessionId || undefined
      });

      // Update session ID if we got a new one
      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
      }

      // Add agent response
      const agentMessage: AgentMessage = {
        role: "assistant",
        content: response.message,
        timestamp: new Date().toISOString(),
        suggestions: response.suggestions,
        actions: response.actions,
        needs_skill_generation: response.needs_skill_generation
      };

      setMessages(prev => [...prev, agentMessage]);
      setSuggestions(response.suggestions);

      // If skill generation is needed, show special UI
      if (response.needs_skill_generation) {
        toast.info("The agent thinks a new skill might be needed for this task");
      }

      // Notify parent of any actions
      if (response.actions && response.actions.length > 0) {
        const skillsUsed = response.actions.filter(action => action.type === "skill_used");
        const skillsImproved = response.actions.filter(action => action.type === "skill_improved");
        const skillsGenerated = response.actions.filter(action => action.type === "skill_generated");
        
        if (skillsUsed.length > 0) {
          toast.success(`Successfully executed ${skillsUsed.length} skill${skillsUsed.length > 1 ? 's' : ''}: ${skillsUsed.map(a => a.skill_name).join(', ')}`);
        }
        
        if (skillsImproved.length > 0) {
          toast.success(`Successfully improved ${skillsImproved.length} skill${skillsImproved.length > 1 ? 's' : ''}: ${skillsImproved.map(a => a.current_skill).join(', ')}`);
        }
        
        if (skillsGenerated.length > 0) {
          toast.success(`Successfully generated ${skillsGenerated.length} new skill${skillsGenerated.length > 1 ? 's' : ''}: ${skillsGenerated.map(a => a.skill_name || a.skill?.name).join(', ')}`);
        }
        
        response.actions.forEach(action => {
          if (action.type === "skill_used" && onSkillUsed) {
            onSkillUsed(action.skill_name);
          }
          if (action.type === "skill_generated" && onSkillGenerated) {
            onSkillGenerated(action.skill);
          }
          if (action.type === "skill_improved" && onSkillUsed) {
            onSkillUsed(action.current_skill);
          }
        });
      }

    } catch (error) {
      toast.error("Failed to send message");
      console.error("Chat error:", error);
      
      // Add error message
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "I'm sorry, I encountered an error processing your message. Please try again.",
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = async (suggestion: SkillSuggestion) => {
    const message = `I'd like to use the "${suggestion.skill_name}" skill. ${suggestion.description}`;
    setInput(message);
  };

  const requestSkillGeneration = async (description: string) => {
    if (!sessionId) {
      toast.error("No active session");
      return;
    }

    try {
      setIsLoading(true);
      const response = await apiClient.requestSkillGeneration({
        description,
        session_id: sessionId
      });

      if (response.success) {
        toast.success(response.message);
        
        // Add system message about skill generation
        setMessages(prev => [...prev, {
          role: "system",
          content: `🎉 ${response.message}`,
          timestamp: new Date().toISOString()
        }]);

        if (response.skill && onSkillGenerated) {
          onSkillGenerated(response.skill);
        }
      } else {
        toast.error(response.error || "Failed to generate skill");
      }
    } catch (error) {
      toast.error("Failed to request skill generation");
      console.error("Skill generation error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !isLoading) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewSession = () => {
    // Clear current session
    setSessionId(null);
    setMessages([]);
    setSuggestions([]);
    
    // Remove from localStorage
    localStorage.removeItem('autolearn_session_id');
    
    // Start new session
    initializeSession();
    toast.success("Started new conversation");
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BotIcon className="h-5 w-5" />
            AI Assistant Chat
            {sessionId && (
              <Badge variant="secondary" className="text-xs">
                Session: {sessionId.slice(-8)}
              </Badge>
            )}
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={startNewSession}
            disabled={isLoading}
            className="text-xs"
          >
            New Session
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-4 p-4 min-h-0">
        {/* Messages */}
        <ScrollArea className="flex-1 pr-4 min-h-0">
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div key={index} className="space-y-2">
                <div className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  {message.role !== "user" && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      {message.role === "system" ? (
                        <SparklesIcon className="h-4 w-4 text-primary" />
                      ) : (
                        <BotIcon className="h-4 w-4 text-primary" />
                      )}
                    </div>
                  )}
                  
                  <div className={`max-w-[80%] rounded-lg p-3 ${
                    message.role === "user" 
                      ? "bg-primary text-primary-foreground ml-auto" 
                      : message.role === "system"
                      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                      : "bg-muted"
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    {message.timestamp && (
                      <p className="text-xs opacity-70 mt-1">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                    )}
                  </div>

                  {message.role === "user" && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                      <UserIcon className="h-4 w-4" />
                    </div>
                  )}
                </div>

                {/* Actions/Skills executed */}
                {message.actions && message.actions.length > 0 && (
                  <div className="ml-11 space-y-2">
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <SparklesIcon className="h-3 w-3" />
                      Skills executed:
                    </p>
                    <div className="space-y-1">
                      {message.actions.map((action, idx) => (
                        action.type === "skill_used" && (
                          <div key={idx} className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary" className="text-xs bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                                ✅ {action.skill_name}
                              </Badge>
                              {action.inputs && (
                                <span className="text-xs text-muted-foreground">
                                  ({Object.entries(action.inputs).map(([key, value]) => `${key}: ${value}`).join(', ')})
                                </span>
                              )}
                            </div>
                            {action.result && (
                              <div className="mt-1 text-xs text-green-700 dark:text-green-300 font-mono">
                                Result: {typeof action.result === 'object' ? JSON.stringify(action.result) : action.result}
                              </div>
                            )}
                          </div>
                        )
                      ))}
                      {message.actions.map((action, idx) => (
                        action.type === "skill_improved" && (
                          <div key={idx} className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">
                                🔧 {action.current_skill}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                Improved
                              </span>
                            </div>
                            {action.improvements && (
                              <div className="mt-1 text-xs text-blue-700 dark:text-blue-300">
                                Improvements: {action.improvements}
                              </div>
                            )}
                          </div>
                        )
                      ))}
                      {message.actions.map((action, idx) => (
                        action.type === "skill_generated" && (
                          <div key={idx} className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary" className="text-xs bg-purple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-100">
                                🎉 {action.skill_name || action.skill?.name}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                Generated
                              </span>
                            </div>
                            {action.description && (
                              <div className="mt-1 text-xs text-purple-700 dark:text-purple-300">
                                {action.description}
                              </div>
                            )}
                          </div>
                        )
                      ))}
                    </div>
                  </div>
                )}

                {/* Skill suggestions - only show if no skills were executed and suggestions are highly relevant */}
                {message.suggestions && message.suggestions.length > 0 && 
                 (!message.actions || message.actions.length === 0) &&
                 message.suggestions.some(s => s.relevance_score > 0.6) && (
                  <div className="ml-11 space-y-2">
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <LightbulbIcon className="h-3 w-3" />
                      Suggested skills:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {message.suggestions
                        .filter(s => s.relevance_score > 0.6)
                        .slice(0, 3)
                        .map((suggestion, idx) => (
                        <Button
                          key={idx}
                          variant="outline"
                          size="sm"
                          onClick={() => handleSuggestionClick(suggestion)}
                          className="text-xs"
                        >
                          {suggestion.skill_name}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Skill generation indicator */}
                {message.needs_skill_generation && (
                  <div className="ml-11">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => requestSkillGeneration(message.content)}
                      className="text-xs"
                      disabled={isLoading}
                    >
                      <SparklesIcon className="h-3 w-3 mr-1" />
                      Generate New Skill
                    </Button>
                  </div>
                )}
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <LoaderIcon className="h-4 w-4 text-primary animate-spin" />
                </div>
                <div className="ml-3 bg-muted rounded-lg p-3 max-w-[80%]">
                  <p className="text-sm text-muted-foreground">Agent is thinking...</p>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        <div className="flex-shrink-0">
          <Separator />

          {/* Current suggestions - only show high-quality suggestions */}
          {suggestions.length > 0 && suggestions.some(s => s.relevance_score > 0.7) && (
            <div className="space-y-2 mt-4">
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <LightbulbIcon className="h-3 w-3" />
                Relevant skills:
              </p>
              <div className="flex flex-wrap gap-2">
                {suggestions
                  .filter(s => s.relevance_score > 0.7)
                  .slice(0, 3)
                  .map((suggestion, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="text-xs"
                    title={suggestion.reason}
                  >
                    {suggestion.skill_name}
                    <Badge variant="secondary" className="ml-1 text-[10px]">
                      {Math.round(suggestion.relevance_score * 100)}%
                    </Badge>
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="flex gap-2 mt-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything... I can use skills, improve on them, and even create new ones!"
              disabled={isLoading}
              className="flex-1"
            />
            <Button 
              onClick={sendMessage} 
              disabled={isLoading || !input.trim()}
              size="icon"
            >
              {isLoading ? (
                <LoaderIcon className="h-4 w-4 animate-spin" />
              ) : (
                <SendIcon className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
