import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="text-center py-16">
      <h2 className="text-2xl font-semibold mb-2">Page not found</h2>
      <Link to="/dashboard" className="text-sm underline">Back to Dashboard</Link>
    </div>
  );
}
