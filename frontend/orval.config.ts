import { defineConfig } from "orval";

// The typed API contract, generated — never hand-written (models + a fetch client from the
// arvel OpenAPI document). Regenerate after backend changes:
//   make openapi   (arvel openapi:export frontend/openapi.json)
//   npm run api:generate
export default defineConfig({
  arvel: {
    input: "./openapi.json",
    output: {
      target: "./src/api/gen/endpoints.ts",
      schemas: "./src/api/gen/models",
      client: "fetch",
      mode: "single",
      baseUrl: "",
      override: {
        mutator: {
          path: "./src/api/http.ts",
          name: "apiFetch",
        },
      },
    },
  },
});
