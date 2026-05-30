/**
 * E2E staging environment configuration for CityOSJarvis.
 * Used by Playwright tests when running against staging.
 */

export const stagingConfig = {
  baseURL: process.env.STAGING_URL || "https://jarvis-staging.dakkah.city",
  apiBaseURL: process.env.STAGING_API_URL || "https://jarvis-staging.dakkah.city/api/bff/ai",
  
  // Authentication
  auth: {
    keycloakUrl: process.env.KEYCLOAK_URL || "https://auth-staging.dakkah.city",
    realm: process.env.KEYCLOAK_REALM || "cityos",
    clientId: process.env.KEYCLOAK_CLIENT_ID || "cityosjarvis-e2e",
    // Test credentials (rotate after each run)
    username: process.env.E2E_USERNAME || "e2e-test-user",
    password: process.env.E2E_PASSWORD || "",
  },

  // Test tenant
  tenant: {
    id: process.env.E2E_TENANT_ID || "e2e-test-tenant",
    nodePath: process.env.E2E_NODE_PATH || "global.sa.dakkah.test",
  },

  // Timeouts
  timeouts: {
    navigation: 15000,
    apiRequest: 30000,
    streamingChunk: 5000,
    voiceSynthesis: 10000,
  },

  // Feature flags
  features: {
    enableStreaming: true,
    enableVoice: true,
    enableTTS: true,
    enableTools: true,
  },

  // Retry config
  retries: process.env.CI ? 2 : 0,
};

export default stagingConfig;
