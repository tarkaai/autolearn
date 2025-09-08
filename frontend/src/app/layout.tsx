import "~/styles/globals.css";

import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { Toaster } from "~/components/ui/sonner";

import { TRPCReactProvider } from "~/trpc/react";
import { WebSocketProvider } from "~/lib/websocket";

export const metadata: Metadata = {
	title: "AutoLearn",
	description: "Dynamic skill creation for AI agents",
	icons: [{ rel: "icon", url: "/favicon.ico" }],
};

const geist = Geist({
	subsets: ["latin"],
	variable: "--font-geist-sans",
});

export default function RootLayout({
	children,
}: Readonly<{ children: React.ReactNode }>) {
	return (
		<html lang="en" className={`${geist.variable}`}>
			<body className="min-h-screen bg-background">
				<TRPCReactProvider>
					<WebSocketProvider>
						{children}
						<Toaster />
					</WebSocketProvider>
				</TRPCReactProvider>
			</body>
		</html>
	);
}
