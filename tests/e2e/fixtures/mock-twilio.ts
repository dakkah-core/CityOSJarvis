/**
 * Mock Twilio server for voice E2E testing.
 * Simulates Twilio webhook endpoints without requiring real Twilio credentials.
 */

import { createServer, Server, IncomingMessage, ServerResponse } from "http";

interface TwilioCall {
  CallSid: string;
  From: string;
  To: string;
  SpeechResult?: string;
  Confidence?: number;
}

export class MockTwilioServer {
  private server: Server | null = null;
  private port: number;
  private calls: TwilioCall[] = [];
  private responses: Map<string, string> = new Map();

  constructor(port: number = 15020) {
    this.port = port;
  }

  setResponse(path: string, twiml: string): void {
    this.responses.set(path, twiml);
  }

  getCalls(): TwilioCall[] {
    return [...this.calls];
  }

  start(): Promise<void> {
    return new Promise((resolve) => {
      this.server = createServer((req: IncomingMessage, res: ServerResponse) => {
        const path = req.url || "/";
        const method = req.method || "GET";

        // CORS
        res.setHeader("Access-Control-Allow-Origin", "*");
        res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        res.setHeader("Access-Control-Allow-Headers", "Content-Type");

        if (method === "OPTIONS") {
          res.writeHead(200);
          res.end();
          return;
        }

        // Parse body for POST requests
        if (method === "POST") {
          let body = "";
          req.on("data", (chunk) => {
            body += chunk;
          });
          req.on("end", () => {
            const params = new URLSearchParams(body);
            const call: TwilioCall = {
              CallSid: params.get("CallSid") || `mock-${Date.now()}`,
              From: params.get("From") || "+966501234567",
              To: params.get("To") || "+966501111111",
              SpeechResult: params.get("SpeechResult") || undefined,
              Confidence: params.get("Confidence") ? parseFloat(params.get("Confidence")!) : undefined,
            };
            this.calls.push(call);

            const twiml = this.responses.get(path) || this._defaultVoiceResponse();
            res.writeHead(200, { "Content-Type": "text/xml" });
            res.end(twiml);
          });
          return;
        }

        // GET requests return call log
        if (path === "/calls") {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify(this.calls));
          return;
        }

        const twiml = this.responses.get(path) || this._defaultVoiceResponse();
        res.writeHead(200, { "Content-Type": "text/xml" });
        res.end(twiml);
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

  private _defaultVoiceResponse(): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Welcome to Dakkah CityOS voice assistant.</Say>
  <Gather input="speech" timeout="5">
    <Say>How can I help you?</Say>
  </Gather>
</Response>`;
  }

  getUrl(): string {
    return `http://localhost:${this.port}`;
  }
}

/**
 * Pre-configured mock Twilio with standard responses.
 */
export function createStandardMockTwilio(port?: number): MockTwilioServer {
  const server = new MockTwilioServer(port);

  server.setResponse(
    "/api/voice/twilio",
    `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="ar-SA">مرحباً بك في مساعد دكّة الصوتي</Say>
  <Gather input="speech" language="ar-SA" timeout="5">
    <Say>كيف يمكنني مساعدتك؟</Say>
  </Gather>
</Response>`
  );

  server.setResponse(
    "/api/voice/webhook",
    `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Processing your request.</Say>
  <Redirect>/api/voice/twilio</Redirect>
</Response>`
  );

  return server;
}
