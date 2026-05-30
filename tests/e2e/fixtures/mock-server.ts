/**
 * Mock BFF server for isolated E2E testing.
 * No external dependencies required — runs entirely in Node.js.
 */

import { createServer, Server } from "http";

interface MockResponse {
  status: number;
  body: unknown;
  delayMs?: number;
}

export class MockBffServer {
  private server: Server | null = null;
  private port: number;
  private routes: Map<string, MockResponse> = new Map();

  constructor(port: number = 9999) {
    this.port = port;
  }

  setRoute(path: string, response: MockResponse): void {
    this.routes.set(path, response);
  }

  start(): Promise<void> {
    return new Promise((resolve) => {
      this.server = createServer((req, res) => {
        const path = req.url || "/";
        const route = this.routes.get(path);

        if (!route) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: "Not found" }));
          return;
        }

        const send = () => {
          res.writeHead(route.status, { "Content-Type": "application/json" });
          res.end(JSON.stringify(route.body));
        };

        if (route.delayMs) {
          setTimeout(send, route.delayMs);
        } else {
          send();
        }
      });

      this.server.listen(this.port, () => resolve());
    });
  }

  stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => resolve());
      } else {
        resolve();
      }
    });
  }

  getUrl(): string {
    return `http://localhost:${this.port}`;
  }
}

/**
 * Pre-configured mock responses for common AI flows.
 */
export function createStandardMockServer(port?: number): MockBffServer {
  const server = new MockBffServer(port);

  server.setRoute("/api/bff/ai/health", {
    status: 200,
    body: { status: "ok", version: "1.0.0" },
  });

  server.setRoute("/api/bff/ai/agents", {
    status: 200,
    body: {
      success: true,
      data: [
        { id: "citizen", name: "Citizen Support" },
        { id: "merchant", name: "Merchant Assistant" },
        { id: "government", name: "Government Officer" },
      ],
    },
  });

  server.setRoute("/api/bff/ai/models", {
    status: 200,
    body: {
      success: true,
      data: [
        { id: "gpt-4", name: "GPT-4" },
        { id: "claude-3", name: "Claude 3" },
      ],
    },
  });

  server.setRoute("/api/bff/ai/chat", {
    status: 200,
    body: {
      success: true,
      data: {
        role: "assistant",
        content: "Dakkah CityOS offers smart city services including transportation, healthcare, governance, and commerce.",
      },
    },
    delayMs: 500,
  });

  server.setRoute("/api/bff/ai/voice/speak", {
    status: 200,
    body: {
      audioBase64: "//uQZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWgAAAA0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABw",
      format: "mp3",
    },
  });

  server.setRoute("/api/bff/ai/tools/execute", {
    status: 200,
    body: {
      success: true,
      data: { result: "Tool executed successfully" },
    },
  });

  return server;
}
