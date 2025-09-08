import type { FC, ReactNode } from "react";
import Link from "next/link";
import { Button } from "~/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { usePathname, useRouter } from "next/navigation";

interface MainLayoutProps {
  children: ReactNode;
}

const MainLayout: FC<MainLayoutProps> = ({ children }) => {
  const pathname = usePathname();
  const router = useRouter();

  const handleTabChange = (value: string) => {
    router.push(value);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border px-4 py-3 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <Link href="/" className="flex items-center space-x-2">
            <span className="font-bold text-lg">AutoLearn</span>
          </Link>
          <nav>
            <Tabs value={pathname} onValueChange={handleTabChange}>
              <TabsList>
                <TabsTrigger value="/">Chat</TabsTrigger>
                <TabsTrigger value="/skills">Skills</TabsTrigger>
                <TabsTrigger value="/mcp">MCP Spec</TabsTrigger>
                <TabsTrigger value="/execute">Execute</TabsTrigger>
              </TabsList>
            </Tabs>
          </nav>
          <div>
            <Button variant="outline" size="sm">
              Settings
            </Button>
          </div>
        </div>
      </header>
      <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full">
        {children}
      </main>
      <footer className="border-t border-border px-4 py-3 text-center text-sm text-muted-foreground">
        <p>AutoLearn - Dynamic skill creation for AI agents</p>
      </footer>
    </div>
  );
};

export default MainLayout;
