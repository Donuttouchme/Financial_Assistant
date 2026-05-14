import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { useHeartbeat } from "./hooks/useHeartbeat";

export default function App() {
  useHeartbeat();
  return <RouterProvider router={router} />;
}
