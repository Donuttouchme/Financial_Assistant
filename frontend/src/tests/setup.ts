import "@testing-library/jest-dom/vitest";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";
import { handlers, resetTestState } from "./handlers";

// jsdom does not implement ResizeObserver; polyfill it for Radix UI components
// (Select, Dialog) that call it in useLayoutEffect.
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// jsdom does not implement scrollIntoView; polyfill it for Radix UI Select.
window.HTMLElement.prototype.scrollIntoView = function () {};

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetTestState();
});
afterAll(() => server.close());
