import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

interface Props {
  mode: "create" | "edit";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  transactionId?: number;
}

export function TransactionFormDialog({ open, onOpenChange }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle>Add transaction</DialogTitle>
        <p className="text-sm text-muted-foreground">
          (Form coming in Task 8.)
        </p>
      </DialogContent>
    </Dialog>
  );
}
