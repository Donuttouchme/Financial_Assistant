import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { useHeartbeat } from "./hooks/useHeartbeat";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function App() {
  useHeartbeat();
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}
