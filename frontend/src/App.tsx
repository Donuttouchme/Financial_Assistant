import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { useHeartbeat } from "./hooks/useHeartbeat";
import { V11MigrationToast } from "./components/V11MigrationToast";

export default function App() {
  useHeartbeat();
  return (
    <>
      <V11MigrationToast />
      <RouterProvider router={router} />
    </>
  );
}
