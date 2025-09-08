"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Card, CardContent } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { 
  HomeIcon, 
  SparklesIcon, 
  TerminalIcon, 
  CodeIcon, 
  NetworkIcon,
  UserIcon 
} from "lucide-react";

export default function Navigation() {
  const pathname = usePathname();

  const navItems = [
    {
      href: "/",
      label: "System Demo",
      icon: TerminalIcon,
      description: "Original milestone 3 demo interface"
    },
    {
      href: "/user-mode",
      label: "User Mode",
      icon: UserIcon,
      description: "AI assistant that creates skills on demand",
      badge: "New"
    },
    {
      href: "/skills",
      label: "Skills",
      icon: CodeIcon,
      description: "View and manage skills"
    },
    {
      href: "/mcp",
      label: "MCP Spec",
      icon: NetworkIcon,
      description: "View MCP protocol specification"
    }
  ];

  return (
    <Card className="mb-6">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <SparklesIcon className="h-6 w-6 text-primary" />
          <h2 className="text-xl font-semibold">AutoLearn</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={isActive ? "default" : "outline"}
                  className="w-full h-auto p-4 flex flex-col items-start gap-2"
                >
                  <div className="flex items-center gap-2 w-full">
                    <Icon className="h-5 w-5" />
                    <span className="font-medium">{item.label}</span>
                    {item.badge && (
                      <Badge variant="secondary" className="text-xs">
                        {item.badge}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-left opacity-80">
                    {item.description}
                  </p>
                </Button>
              </Link>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
