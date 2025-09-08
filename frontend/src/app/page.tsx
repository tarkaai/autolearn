"use client";

import { useEffect, useRef, useState } from "react";
import MainLayout from "~/components/layouts/main-layout";
import Navigation from "~/components/navigation";
import { useWebSocketContext } from "~/lib/websocket";
import { apiClient, type ChatMessage, type ChatSession } from "~/lib/api-client";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Button } from "~/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { toast } from "sonner";
import { PlusIcon, SendIcon } from "lucide-react";

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { socket, isConnected } = useWebSocketContext();

  // Fetch sessions on load
  useEffect(() => {
    fetchSessions();
  }, []);

  // When socket connects or skill is added, update the sessions and messages
  useEffect(() => {
    if (socket) {
      socket.on("skill_added", (skill) => {
        toast.success(`New skill added: ${skill.name}`);
        // Refresh the current session to get any new messages
        if (currentSession) {
          fetchSession(currentSession.id);
        }
      });
    }

    return () => {
      if (socket) {
        socket.off("skill_added");
      }
    };
  }, [socket, currentSession]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch all sessions
  const fetchSessions = async () => {
    try {
      const fetchedSessions = await apiClient.listSessions();
      setSessions(fetchedSessions);
      
      // If we have sessions but no current session, set the first one
      if (fetchedSessions.length > 0 && !currentSession) {
        const firstSession = fetchedSessions[0];
        setCurrentSession(firstSession);
        setMessages(firstSession.messages);
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
      toast.error("Failed to load chat sessions");
    }
  };

  // Fetch a specific session
  const fetchSession = async (sessionId: string) => {
    try {
      const session = await apiClient.getSession(sessionId);
      setCurrentSession(session);
      setMessages(session.messages);
    } catch (error) {
      console.error("Error fetching session:", error);
      toast.error("Failed to load chat session");
    }
  };

  // Create a new session
  const createNewSession = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.createSession({
        name: `Chat ${new Date().toLocaleString()}`
      });
      
      setSessions([...sessions, response.session]);
      setCurrentSession(response.session);
      setMessages(response.session.messages);
      toast.success("New chat session created");
    } catch (error) {
      console.error("Error creating session:", error);
      toast.error("Failed to create new chat session");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle session change
  const handleSessionChange = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSession(session);
      setMessages(session.messages);
    }
  };

  // Send a message
  const handleSendMessage = async () => {
    if (!currentSession || !input.trim()) return;

    try {
      setIsLoading(true);
      const response = await apiClient.addMessage(currentSession.id, {
        role: "user",
        content: input
      });
      
      // Refresh the session to get all messages including the assistant response
      await fetchSession(currentSession.id);
      
      setInput("");
      
      // If a skill was generated, show a notification
      if (response.skill_generated) {
        toast.success(`Created new skill: ${response.skill_generated.name}`);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Failed to send message");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <MainLayout>
      <div className="container mx-auto p-6">
        <Navigation />
        
        <div className="flex flex-col h-[calc(100vh-20rem)]">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold">System Demo Chat</h1>
          <div className="flex items-center space-x-2">
            <Select 
              value={currentSession?.id} 
              onValueChange={handleSessionChange}
              disabled={isLoading}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select a session" />
              </SelectTrigger>
              <SelectContent>
                {sessions.map((session) => (
                  <SelectItem key={session.id} value={session.id}>
                    {session.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button 
              size="icon"
              variant="outline"
              onClick={createNewSession}
              disabled={isLoading}
              title="New chat session"
            >
              <PlusIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <Card className="flex-1 flex flex-col">
          <CardHeader className="py-3">
            <CardTitle className="text-xl">
              {currentSession?.name || "Select a session"}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                {currentSession ? "No messages yet" : "Select or create a chat session"}
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : msg.role === "system"
                          ? "bg-muted text-muted-foreground"
                          : "bg-secondary text-secondary-foreground"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                      <div className="text-xs opacity-70 mt-1">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </CardContent>
          <CardFooter className="p-4 pt-2">
            <div className="flex w-full items-center space-x-2">
              <Input
                placeholder="Type a message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={!currentSession || isLoading}
                className="flex-1"
              />
              <Button
                size="icon"
                onClick={handleSendMessage}
                disabled={!currentSession || !input.trim() || isLoading}
              >
                <SendIcon className="h-4 w-4" />
              </Button>
            </div>
          </CardFooter>
        </Card>
        
          {!isConnected && (
            <div className="mt-2 text-sm text-orange-500 dark:text-orange-400">
              WebSocket disconnected. Some features may be unavailable.
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
