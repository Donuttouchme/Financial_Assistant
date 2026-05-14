import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function EmptyAppState() {
  return (
    <Card>
      <CardContent className="py-12 flex flex-col items-center text-center gap-4">
        <h3 className="text-xl font-semibold">Welcome to Financial Assistant</h3>
        <p className="text-muted-foreground max-w-md">
          Start by creating a few categories — income, expense, and savings buckets you
          want to track. Once you have at least one, you can add transactions and set budgets.
        </p>
        <Button asChild>
          <Link to="/categories">Create your first category</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
