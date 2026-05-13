import { ChevronDown } from "lucide-react";
import { useState } from "react";

export function CsvHelpPanel() {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="border rounded-md p-3"
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="cursor-pointer flex items-center gap-2 font-medium select-none">
        <ChevronDown
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
        />
        What should my CSV look like?
      </summary>

      <div className="mt-3 space-y-4 text-sm">
        <div>
          <div className="font-medium mb-1">Layout A — single signed Amount</div>
          <table className="text-xs border w-full">
            <thead className="bg-muted">
              <tr>
                <th className="text-left p-1">Date</th>
                <th className="text-left p-1">Description</th>
                <th className="text-left p-1">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="p-1">03.05.26</td>
                <td className="p-1">COOP Zürich</td>
                <td className="p-1">
                  -45.30{" "}
                  <span className="text-muted-foreground">← expense</span>
                </td>
              </tr>
              <tr>
                <td className="p-1">03.05.26</td>
                <td className="p-1">Salary May</td>
                <td className="p-1">
                  +5200{" "}
                  <span className="text-muted-foreground">← income</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div>
          <div className="font-medium mb-1">
            Layout B — separate Debit / Credit
          </div>
          <table className="text-xs border w-full">
            <thead className="bg-muted">
              <tr>
                <th className="text-left p-1">Date</th>
                <th className="text-left p-1">Description</th>
                <th className="text-left p-1">Debit</th>
                <th className="text-left p-1">Credit</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="p-1">03.05.26</td>
                <td className="p-1">COOP Zürich</td>
                <td className="p-1">45.30</td>
                <td className="p-1"></td>
              </tr>
              <tr>
                <td className="p-1">03.05.26</td>
                <td className="p-1">Salary May</td>
                <td className="p-1"></td>
                <td className="p-1">5200</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}
